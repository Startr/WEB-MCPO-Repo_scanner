from flask import Flask, render_template, request, redirect, url_for, jsonify, flash, Response, stream_with_context, session
import os
import subprocess
import re
import mimetypes
from pathlib import Path
import logging
import json
from datetime import datetime
from functools import wraps
import hashlib
import csv
import fnmatch
import yaml

# Import our robust error handling system - now import directly since we're in the scanner package
from .error_handling import (
    ErrorCategory, ErrorSeverity, ErrorContext, ScannerError,
    ValidationError, NetworkError, GitOperationError, FileSystemError,
    ProcessingError, SystemError, ErrorHandler, RetryConfig,
    with_error_handling, error_context, safe_operation
)

app = Flask(__name__)
app.logger.setLevel(logging.INFO)  # Ensure INFO level is set for our logs
app.secret_key = os.environ.get('SECRET_KEY') or os.urandom(24)

# --- Access key auth ---
ACCESS_KEYS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "access_keys.csv")
# Routes that must stay public for MCP discovery and auth itself
_PUBLIC_ROUTES = {'/api/mpco/manifest', '/api/mpco/openapi.json', '/login', '/resources'}

def load_access_keys():
    """Return set of valid keys from access_keys.csv. Empty set = auth disabled."""
    if not os.path.exists(ACCESS_KEYS_FILE):
        return set()
    keys = set()
    with open(ACCESS_KEYS_FILE, newline='') as f:
        for row in csv.DictReader(f):
            k = (row.get('key') or '').strip()
            if k:
                keys.add(k)
    return keys

def _auth_enabled():
    return bool(load_access_keys())

def _is_authenticated():
    keys = load_access_keys()
    if not keys:
        return True  # No keys file → open access
    if session.get('authed_key') in keys:
        return True
    if request.args.get('key') in keys:
        return True
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer ') and auth_header[7:] in keys:
        return True
    return False

@app.context_processor
def inject_auth_status():
    return {'auth_enabled': _auth_enabled(), 'is_authenticated': _is_authenticated()}

# Read-only route prefixes that public repos expose without auth
_PUBLIC_REPO_PREFIXES = ('/scan_stream/', '/stream_data/', '/api/repo_fingerprint/', '/api/todo_files/')


def _is_public_repo_route():
    """Check if this request targets a public repo's read-only route."""
    path = request.path
    for prefix in _PUBLIC_REPO_PREFIXES:
        if path.startswith(prefix):
            repo_name = path[len(prefix):]
            if is_repo_public(repo_name):
                return True
    return False


@app.before_request
def require_auth():
    if request.path in _PUBLIC_ROUTES or request.path.startswith('/static') or request.path.startswith('/api/badge/'):
        return
    if request.path.startswith('/api/webhook/'):
        return  # Webhook routes use their own HMAC verification
    if _is_public_repo_route():
        return
    if _is_authenticated():
        return
    # API clients get 401 JSON; browsers get redirected to /login
    if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
        return jsonify({'error': 'Unauthorized', 'hint': 'Pass ?key=<your-key> or Authorization: Bearer <key>'}), 401
    return redirect(url_for('login', next=request.url))

# Initialize the centralized error handler
app.error_handler = ErrorHandler(app.logger)

# Configure base repository path
BASE_REPO_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "repositories")

# Local repos config — maps safe display names to metadata dicts (never exposed to web)
_APP_DIR = os.path.dirname(os.path.abspath(__file__))
LOCAL_REPOS_YAML = os.path.join(_APP_DIR, "local_repos.yaml")
LOCAL_REPOS_JSON = os.path.join(_APP_DIR, "local_repos.json")  # legacy, auto-migrated


def _normalize_repo_meta(value):
    """Ensure a repo entry is a full metadata dict, not a bare path string."""
    if isinstance(value, str):
        return {'path': value, 'public': False, 'webhook_secret': None}
    # Fill in missing keys for older dicts
    value.setdefault('public', False)
    value.setdefault('webhook_secret', None)
    return value


def load_local_repos():
    """Load registered repos as {name: {path, public, webhook_secret}}.

    Reads local_repos.yaml.  If it doesn't exist but local_repos.json does,
    auto-migrates (reads JSON, writes YAML, preserves the old file).
    Bare-string values are normalised to full metadata dicts on read.
    """
    if os.path.exists(LOCAL_REPOS_YAML):
        with open(LOCAL_REPOS_YAML, 'r', encoding='utf-8') as f:
            raw = yaml.safe_load(f) or {}
    elif os.path.exists(LOCAL_REPOS_JSON):
        with open(LOCAL_REPOS_JSON, 'r', encoding='utf-8') as f:
            raw = json.load(f)
        # Auto-migrate: write YAML so we never read JSON again
        normalised = {k: _normalize_repo_meta(v) for k, v in raw.items()}
        save_local_repos(normalised)
        return normalised
    else:
        return {}
    return {k: _normalize_repo_meta(v) for k, v in raw.items()}


def save_local_repos(repos):
    """Persist repos to local_repos.yaml (human-readable)."""
    tmp = LOCAL_REPOS_YAML + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        yaml.dump(repos, f, default_flow_style=False, allow_unicode=True, sort_keys=True)
    os.replace(tmp, LOCAL_REPOS_YAML)


def get_repo_meta(repo_name):
    """Return the metadata dict for a registered repo, or None."""
    return load_local_repos().get(repo_name)


def is_repo_public(repo_name):
    """Return True if repo_name is flagged as public."""
    meta = get_repo_meta(repo_name)
    return bool(meta and meta.get('public', False))


def get_webhook_secret(repo_name):
    """Return the webhook secret for a repo, or None."""
    meta = get_repo_meta(repo_name)
    return meta.get('webhook_secret') if meta else None

def load_exclusions(repo_path):
    """Read .todoscope-exclude.csv from the repo root.
    Returns list of dicts: [{'path': str, 'reason': str}, ...]
    Missing or unreadable file silently returns [].
    """
    if not repo_path:
        return []
    csv_path = os.path.join(repo_path, '.todoscope-exclude.csv')
    if not os.path.exists(csv_path):
        return []
    exclusions = []
    try:
        with open(csv_path, newline='', encoding='utf-8') as f:
            for row in csv.DictReader(f):
                p = (row.get('path') or '').strip()
                r = (row.get('reason') or '').strip()
                if p:
                    exclusions.append({'path': p, 'reason': r})
    except Exception as e:
        app.logger.warning(f"Could not read .todoscope-exclude.csv in {repo_path}: {e}")
    return exclusions


def is_excluded(rel_path, exclusions):
    """Return the first matching exclusion dict, or None.
    Prefix match handles directory subtrees; fnmatch handles glob patterns.
    Paths are normalised to forward-slash for cross-platform consistency.
    """
    if not exclusions:
        return None
    norm = rel_path.replace(os.sep, '/')
    for exc in exclusions:
        pat = exc['path'].replace(os.sep, '/')
        if norm == pat or norm.startswith(pat + '/'):
            return exc
        if fnmatch.fnmatch(norm, pat):
            return exc
    return None


def resolve_repo_path(name):
    """Resolve a repo display name to its filesystem path.
    Checks registered local repos first, then BASE_REPO_PATH.
    Returns None if not found.
    """
    # Check registered local repos
    local_repos = load_local_repos()
    if name in local_repos:
        path = local_repos[name]['path']
        if os.path.isdir(path):
            return path
    # Check cloned repos in BASE_REPO_PATH
    cloned_path = os.path.join(BASE_REPO_PATH, name)
    if os.path.isdir(cloned_path):
        return cloned_path
    return None

# Flask error handlers for different error types
@app.errorhandler(ScannerError)
def handle_scanner_error(error: ScannerError):
    """Handle custom scanner errors"""
    app.error_handler.handle_error(error)
    
    if request.path.startswith('/api/'):
        return jsonify({
            "status": "error",
            "error_id": error.error_id,
            "message": error.user_message,
            "category": error.category.value,
            "recoverable": error.recoverable
        }), 500
    else:
        return render_template('index.html', 
                             error=error.user_message,
                             error_id=error.error_id,
                             local_repos=list_local_repositories()), 500

@app.errorhandler(500)
def handle_internal_error(error):
    """Handle unexpected internal errors"""
    scanner_error = SystemError(
        "An unexpected internal error occurred",
        original_exception=error,
        context=ErrorContext("internal_error", "flask_app")
    )
    return handle_scanner_error(scanner_error)

class TodoItem:
    def __init__(self, file_path, line_num, todo_text, next_line=None):
        self.file_path = file_path
        self.line_num = line_num
        self.todo_text = todo_text
        self.next_line = next_line
    
    def to_dict(self):
        return {
            'file_path': self.file_path,
            'line_num': self.line_num,
            'todo_text': sanitize_for_llm(self.todo_text),
            'next_line': sanitize_for_llm(self.next_line)
        }

@safe_operation(default_return=None)
def ensure_dir_exists(path):
    """Ensure the directory exists, creating it if necessary."""
    try:
        os.makedirs(path, exist_ok=True)
    except OSError as e:
        raise FileSystemError(f"Failed to create directory {path}", path=path, original_exception=e)

@safe_operation(default_return=None)
def sanitize_for_llm(text):
    """Sanitize text to avoid issues with LLM processing."""
    if text is None:
        return None
        
    # Replace triple quotes with single quotes
    sanitized = text.replace('"""', '"')
    sanitized = sanitized.replace("'''", "'")
    
    return sanitized

@with_error_handling("git_validation", "repository_manager", RetryConfig(max_attempts=1))
def is_valid_git_repo(path_to_check: str) -> bool:
    """Checks if the given path is a valid Git repository work tree."""
    if not path_to_check:
        raise ValidationError("Repository path cannot be empty", field="path")
    
    if not os.path.isdir(path_to_check):
        app.logger.debug(f"Path {path_to_check} is not a directory, skipping git check.")
        return False

    try:
        # This command checks if the path is within a git working tree.
        process = subprocess.run(
            ['git', '-C', path_to_check, 'rev-parse', '--is-inside-work-tree'],
            capture_output=True, text=True, check=False, timeout=5
        )
        
        if process.returncode == 0 and process.stdout.strip() == 'true':
            app.logger.debug(f"Path {path_to_check} is a valid git work tree.")
            return True
        else:
            app.logger.debug(
                f"Path {path_to_check} is not recognized as a git work tree by 'rev-parse --is-inside-work-tree'. "
                f"Return Code: {process.returncode}, Stdout: '{process.stdout.strip()}', Stderr: '{process.stderr.strip()}'"
            )
            return False
            
    except subprocess.TimeoutExpired as e:
        raise GitOperationError(f"Timeout checking if {path_to_check} is a git repo", 
                               git_command="git rev-parse", original_exception=e)
    except FileNotFoundError as e:
        raise SystemError("Git command not found. Please ensure Git is installed", original_exception=e)
    except Exception as e:
        raise GitOperationError(f"Unexpected error checking git status for {path_to_check}", 
                               git_command="git rev-parse", original_exception=e)

@with_error_handling("get_origin_url", "repository_manager")
def get_repo_origin_url(repo_path):
    """Get the remote origin URL of a git repository."""
    if not repo_path:
        raise ValidationError("Repository path cannot be empty", field="repo_path")
    
    try:
        # Run git command to get the remote origin URL
        result = subprocess.run(
            ['git', '-C', repo_path, 'config', '--get', 'remote.origin.url'],
            capture_output=True, text=True, check=True, timeout=10
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        raise GitOperationError(f"Failed to get origin URL for repo at {repo_path}", 
                               git_command="git config", original_exception=e)
    except subprocess.TimeoutExpired as e:
        raise GitOperationError(f"Timeout getting origin URL for {repo_path}", 
                               git_command="git config", original_exception=e)

def get_repo_branch(repo_path):
    """Get the current branch name of a git repository. Returns 'HEAD' on failure."""
    try:
        result = subprocess.run(
            ['git', '-C', repo_path, 'rev-parse', '--abbrev-ref', 'HEAD'],
            capture_output=True, text=True, check=True, timeout=10
        )
        return result.stdout.strip() or 'HEAD'
    except Exception:
        return 'HEAD'

@with_error_handling("pull_repository", "repository_manager", RetryConfig(max_attempts=2))
def pull_repository(repo_path):
    """Pull the latest changes from the remote repository."""
    if not repo_path:
        raise ValidationError("Repository path cannot be empty", field="repo_path")
    
    with error_context("pull_repository", "git_operations", repo_path=repo_path):
        app.logger.info(f"Pulling latest changes for repository at {repo_path}")
        
        # Check if the repository exists locally
        if not os.path.isdir(repo_path):
            raise FileSystemError(f"Repository directory does not exist: {repo_path}", path=repo_path)
        
        if not os.path.isdir(os.path.join(repo_path, '.git')):
            raise GitOperationError(f"Not a valid git repository: {repo_path}", git_command="git pull")
        
        # Run git pull
        try:
            result = subprocess.run(
                ['git', '-C', repo_path, 'pull'],
                capture_output=True, text=True, timeout=30
            )
            
            if result.returncode == 0:
                # Update the modification time of the directory after a successful pull
                current_time = datetime.now().timestamp()
                os.utime(repo_path, (current_time, current_time))
                
                return {
                    "success": True,
                    "message": "Successfully pulled latest changes",
                    "details": sanitize_for_llm(result.stdout.strip())
                }
            else:
                raise GitOperationError(
                    f"Git pull failed with return code {result.returncode}",
                    git_command="git pull",
                    context=ErrorContext("pull_repository", "git_operations", 
                                        additional_data={"stderr": result.stderr.strip()})
                )
                
        except subprocess.TimeoutExpired as e:
            raise GitOperationError("Git pull operation timed out", 
                                   git_command="git pull", original_exception=e)

def get_full_origin_url():
    """Get the full origin URL including protocol and hostname."""
    
    # Check for X-Forwarded-Proto and X-Forwarded-Host headers (used by proxies and Cloudflare)
    proto = request.headers.get('X-Forwarded-Proto') or request.scheme
    host = request.headers.get('X-Forwarded-Host') or request.headers.get('Host') or request.host
    
    # Build and return the full origin URL
    return f"{proto}://{host}"

@with_error_handling("clone_repository", "repository_manager", RetryConfig(max_attempts=2))
def clone_repository(repo_url, shallow=False):
    """Clone the repository if it doesn't exist or return the path to an existing local repository.
    Set shallow=True for --depth 1 clones (faster, less disk, sufficient for scanning).
    """
    if not repo_url:
        raise ValidationError("Repository URL cannot be empty", field="repo_url")

    # Check registered local repos first (name->path mapping, path never exposed)
    resolved = resolve_repo_path(repo_url)
    if resolved:
        app.logger.info(f"Using resolved repository: {repo_url}")
        if is_valid_git_repo(resolved):
            # Auto-pull if the repo is stale (last modified > 5 minutes ago)
            age_seconds = datetime.now().timestamp() - os.path.getmtime(resolved)
            if age_seconds > 300:
                app.logger.info(f"Repo stale ({int(age_seconds)}s old), auto-pulling: {repo_url}")
                try:
                    pull_repository(resolved)
                except Exception as e:
                    app.logger.warning(f"Auto-pull failed, using cached repo: {e}")
            return resolved
        else:
            raise GitOperationError(f"Not a valid git repository: {repo_url}",
                                   git_command="git check")
    
    # If not a local repository, validate it's a proper git URL
    if not repo_url.startswith(('http://', 'https://', 'git@')):
        raise ValidationError("Invalid repository URL format. Must be a valid git URL (http://, https://, git@) or an existing local repository name.", 
                             field="repo_url")
    
    repo_name = os.path.basename(repo_url)
    if repo_name.endswith('.git'):
        repo_name = repo_name[:-4]
    
    repo_path = os.path.join(BASE_REPO_PATH, repo_name)
    
    if os.path.isdir(repo_path):
        # Repo exists from a previous clone — auto-pull if stale (> 5 min)
        age_seconds = datetime.now().timestamp() - os.path.getmtime(repo_path)
        if age_seconds > 300:
            app.logger.info(f"Repo stale ({int(age_seconds)}s old), auto-pulling: {repo_path}")
            try:
                pull_repository(repo_path)
            except Exception as e:
                app.logger.warning(f"Auto-pull failed, using cached repo: {e}")
    else:
        with error_context("clone_repository", "git_operations", repo_url=repo_url):
            app.logger.info(f"Cloning repository: {repo_url}")
            ensure_dir_exists(os.path.dirname(repo_path))
            
            try:
                # --depth 1 fetches only the latest commit (faster, less disk)
                clone_cmd = ['git', 'clone']
                if shallow:
                    clone_cmd += ['--depth', '1']
                clone_cmd += [repo_url, repo_path]
                result = subprocess.run(
                    clone_cmd,
                    check=True, capture_output=True, text=True, timeout=120
                )
            except subprocess.CalledProcessError as e:
                raise GitOperationError(
                    f"Failed to clone repository {repo_url}",
                    git_command="git clone",
                    original_exception=e,
                    context=ErrorContext("clone_repository", "git_operations", 
                                        additional_data={"stderr": e.stderr})
                )
            except subprocess.TimeoutExpired as e:
                raise GitOperationError(
                    f"Git clone operation timed out for {repo_url}",
                    git_command="git clone",
                    original_exception=e
                )
    
    return repo_path

@with_error_handling("git_ignore_check", "file_processor")
def is_git_ignored(repo_path, file_path):
    """Check if a file is ignored by git."""
    if not repo_path or not file_path:
        return False
        
    try:
        # Convert to relative path if absolute
        if os.path.isabs(file_path):
            file_path = os.path.relpath(file_path, repo_path)
            
        # Use git check-ignore to determine if the file is ignored
        result = subprocess.run(
            ['git', '-C', repo_path, 'check-ignore', '-q', file_path],
            capture_output=True, timeout=5
        )
        # Return code 0 means the file is ignored
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        app.logger.warning(f"Timeout checking git ignore status for {file_path}")
        return False
    except Exception as e:
        raise ProcessingError(f"Error checking if file is ignored: {file_path}", original_exception=e)

@with_error_handling("file_type_check", "file_processor")
def is_text_file(file_path):
    """Check if a file is a text file using the file command."""
    if not file_path or not os.path.exists(file_path):
        return False
        
    try:
        mime_type = mimetypes.guess_type(file_path)[0]
        if mime_type is None:
            # If mime type can't be guessed from extension, use file command
            result = subprocess.run(
                ['file', '--brief', '--mime', file_path], 
                capture_output=True, text=True, check=True, timeout=5
            )
            return result.stdout.strip().startswith('text/')
        return mime_type.startswith('text/')
    except subprocess.TimeoutExpired:
        app.logger.warning(f"Timeout checking file type for {file_path}")
        return False
    except Exception as e:
        raise ProcessingError(f"Error checking file type: {file_path}", original_exception=e)

@with_error_handling("list_repositories", "repository_manager")
def list_local_repositories():
    """List all repositories: registered local repos + cloned repos.
    Never exposes filesystem paths — only names and origin URLs.
    """
    repos = []
    seen_names = set()

    def _code_dev_url(origin_url):
        m = re.match(r'.*github\.com[:/]([^/]+)/([^/.]+?)(?:\.git)?$', origin_url or "")
        return f"https://vscode.dev/github/{m.group(1)}/{m.group(2)}" if m else None

    # 1. Registered local repos (name->meta mapping, paths stay server-side)
    for name, meta in load_local_repos().items():
        path = meta['path']
        try:
            if os.path.isdir(path) and is_valid_git_repo(path):
                last_modified = os.path.getmtime(path)
                origin_url = get_repo_origin_url(path)
                repos.append({
                    'name': name,
                    'last_modified': last_modified,
                    'last_modified_str': datetime.fromtimestamp(last_modified).strftime('%Y-%m-%d %H:%M:%S'),
                    'origin_url': origin_url or "",
                    'code_dev_url': _code_dev_url(origin_url),
                    'source': 'local',
                    'public': meta.get('public', False),
                    'webhook_secret': bool(meta.get('webhook_secret')),
                })
                seen_names.add(name)
        except Exception as e:
            app.logger.warning(f"Error listing registered repo {name}: {e}")

    # 2. Cloned repos in BASE_REPO_PATH
    with error_context("list_repositories", "repository_manager", base_path=BASE_REPO_PATH):
        ensure_dir_exists(BASE_REPO_PATH)
        try:
            items_in_base_path = os.listdir(BASE_REPO_PATH)
        except OSError as e:
            raise FileSystemError(f"Cannot access repository directory {BASE_REPO_PATH}",
                                 path=BASE_REPO_PATH, original_exception=e)

        for item in items_in_base_path:
            if item in seen_names:
                continue  # Registered local repo takes precedence
            full_path = os.path.join(BASE_REPO_PATH, item)
            try:
                if is_valid_git_repo(full_path):
                    last_modified = os.path.getmtime(full_path)
                    origin_url = get_repo_origin_url(full_path)
                    repos.append({
                        'name': item,
                        'last_modified': last_modified,
                        'last_modified_str': datetime.fromtimestamp(last_modified).strftime('%Y-%m-%d %H:%M:%S'),
                        'origin_url': origin_url or "",
                        'code_dev_url': _code_dev_url(origin_url),
                        'source': 'cloned'
                    })
            except Exception as e:
                app.logger.warning(f"Error processing repository {item}: {e}")

    repos.sort(key=lambda x: x['last_modified'], reverse=True)
    return repos

@with_error_handling("find_todos", "file_processor")
def find_todos(repo_path, exclusions=None, skipped=None):
    """Find TODO comments in all text files in the repository.

    exclusions: list of {'path', 'reason'} dicts from load_exclusions()
    skipped: optional mutable list; matched paths are appended as {'path', 'reason'}
    """
    if not repo_path:
        raise ValidationError("Repository path cannot be empty", field="repo_path")

    if not os.path.isdir(repo_path):
        raise FileSystemError(f"Repository path does not exist: {repo_path}", path=repo_path)

    # Expanded pattern to match more comment styles and annotation types
    # This includes TODO, FIXME, BUG, and NOTE in various comment formats
    todo_pattern = re.compile(
        r'(?:#+|//|/\*|<!--|;)\s*(?:TODO|FIXME|BUG|NOTE)(?:\s*:|(?:\s+))',
        re.IGNORECASE
    )

    # Directories to skip entirely (version control, IDE/editor state, dependency caches)
    SKIP_DIRS = {'.git', '.obsidian', 'node_modules', '__pycache__', '.venv', 'venv'}
    # Files handled separately by find_todo_files() — don't scan for inline comments
    SKIP_FILES = {'todo.md', 'todo.txt'}
    # Never scan repos we manage — avoids recursing into cloned repos when this
    # project itself is registered as a local repo to track.
    _base_repo_real = os.path.realpath(BASE_REPO_PATH)

    with error_context("find_todos", "file_processor", repo_path=repo_path):
        for root, dirs, files in os.walk(repo_path):
            # Prune noisy directories so os.walk never descends into them,
            # skip the managed-repos directory, and honour .todoscope-exclude.csv.
            dirs[:] = [
                d for d in dirs
                if d not in SKIP_DIRS
                and os.path.commonpath([os.path.realpath(os.path.join(root, d)), _base_repo_real]) != _base_repo_real
                and not is_excluded(os.path.relpath(os.path.join(root, d), repo_path), exclusions)
            ]
            for file in files:
                if file.lower() in SKIP_FILES:
                    continue

                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, repo_path)

                # Honour .todoscope-exclude.csv exclusions
                exc = is_excluded(rel_path, exclusions)
                if exc:
                    if skipped is not None:
                        skipped.append({'path': rel_path, 'reason': exc['reason']})
                    continue

                try:
                    # Skip files that are ignored by git
                    if is_git_ignored(repo_path, file_path):
                        app.logger.debug(f"Skipping git-ignored file: {rel_path}")
                        continue

                    if not is_text_file(file_path):
                        continue
                        
                    app.logger.debug(f"Processing file: {rel_path}")
                    
                    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                        lines = f.readlines()
                        
                    for i, line in enumerate(lines):
                        # Look for expanded TODO patterns
                        if todo_pattern.search(line):
                            todo_text = line.strip()
                            next_line_text = lines[i+1].strip() if i+1 < len(lines) else None
                            # Yield the TodoItem as it's found instead of accumulating them
                            yield TodoItem(rel_path, i+1, todo_text, next_line_text)
                            
                except ProcessingError:
                    # Re-raise processing errors
                    raise
                except Exception as e:
                    # Convert other exceptions to ProcessingError
                    raise ProcessingError(f"Error processing file {rel_path}", original_exception=e)

@with_error_handling("find_todo_files", "file_processor")
def find_todo_files(repo_path, exclusions=None, skipped=None):
    """Find standalone TODO.md/TODO.txt files in the repository.
    Returns list of dicts: [{'file_path': str, 'content': str|None}, ...]
    Distinct from find_todos() which scans inline code comments.

    exclusions: list of {'path', 'reason'} dicts from load_exclusions()
    skipped: optional mutable list; matched paths are appended as {'path', 'reason'}
    """
    if not repo_path or not os.path.isdir(repo_path):
        return []
    TODO_FILENAMES = {'todo.md', 'todo.txt'}
    results = []
    _base_repo_real = os.path.realpath(BASE_REPO_PATH)
    with error_context("find_todo_files", "file_processor", repo_path=repo_path):
        for root, dirs, files in os.walk(repo_path):
            # Prune .git dirs, the managed-repos directory, and .todoscope-exclude.csv entries.
            dirs[:] = [
                d for d in dirs
                if not d.startswith('.git')
                and os.path.commonpath([os.path.realpath(os.path.join(root, d)), _base_repo_real]) != _base_repo_real
                and not is_excluded(os.path.relpath(os.path.join(root, d), repo_path), exclusions)
            ]
            for filename in files:
                if filename.lower() in TODO_FILENAMES:
                    file_path = os.path.join(root, filename)
                    rel_path = os.path.relpath(file_path, repo_path)
                    exc = is_excluded(rel_path, exclusions)
                    if exc:
                        if skipped is not None:
                            skipped.append({'path': rel_path, 'reason': exc['reason']})
                        continue
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                        results.append({'file_path': rel_path, 'content': content})
                    except Exception as e:
                        app.logger.warning(f"Could not read TODO file {rel_path}: {e}")
                        results.append({'file_path': rel_path, 'content': None})
    return results

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        key = request.form.get('key', '').strip()
        if key in load_access_keys():
            session['authed_key'] = key
            return redirect(request.args.get('next') or url_for('index'))
        return render_template('login.html', error='Invalid key.', auth_enabled=_auth_enabled())
    return render_template('login.html', error=None, auth_enabled=_auth_enabled())

@app.route('/logout')
def logout():
    session.pop('authed_key', None)
    return redirect(url_for('login'))

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        repo_url = request.form.get('repo_url')
        if not repo_url:
            return render_template('index.html', error="Repository URL is required")
        shallow = '1' if request.form.get('shallow') == 'on' else ''
        return redirect(url_for('scan_stream', repo_url=repo_url, shallow=shallow))
    
    # Get list of local repositories to display
    local_repos = list_local_repositories()
    
    return render_template('index.html', local_repos=local_repos)

@app.route('/setup/add_key', methods=['POST'])
def setup_add_key():
    """Write a new key+label row to access_keys.csv (bootstrap flow when auth is not yet enabled)."""
    if _auth_enabled():
        return jsonify({'error': 'Auth already configured. Edit access_keys.csv directly.'}), 403
    key = request.form.get('key', '').strip()
    key_confirm = request.form.get('key_confirm', '').strip()
    label = request.form.get('label', 'default').strip()
    if not key:
        return render_template('index.html', local_repos=list_local_repositories(),
                               setup_error="Key cannot be empty.")
    if key != key_confirm:
        return render_template('index.html', local_repos=list_local_repositories(),
                               setup_error="Keys do not match — please try again.")
    write_header = not os.path.exists(ACCESS_KEYS_FILE)
    with open(ACCESS_KEYS_FILE, 'a', newline='') as f:
        writer = csv.writer(f)
        if write_header:
            writer.writerow(['key', 'label'])
        writer.writerow([key, label])
    session['authed_key'] = key
    return redirect(url_for('index'))

@app.route('/add_local', methods=['POST'])
def add_local_repo():
    """Register a local repository path. The path is stored server-side only
    and never exposed to the web — only the display name is visible.
    """
    local_path = request.form.get('local_path', '').strip()
    display_name = request.form.get('display_name', '').strip()
    local_repos = list_local_repositories()

    if not local_path:
        return render_template('index.html', error="Path is required", local_repos=local_repos)

    if not os.path.isdir(local_path):
        return render_template('index.html', error="Path does not exist on this machine", local_repos=local_repos)

    if not is_valid_git_repo(local_path):
        return render_template('index.html', error="Path is not a git repository", local_repos=local_repos)

    # Default display name to directory basename
    if not display_name:
        display_name = os.path.basename(os.path.normpath(local_path))

    repos = load_local_repos()
    repos[display_name] = {'path': os.path.abspath(local_path), 'public': False, 'webhook_secret': None}
    save_local_repos(repos)
    app.logger.info(f"Registered local repo: {display_name}")

    return redirect(url_for('index'))

@app.route('/remove_local/<path:repo_name>')
def remove_local_repo(repo_name):
    """Unregister a local repository. Only removes the mapping — never deletes files."""
    repos = load_local_repos()
    repos.pop(repo_name, None)
    save_local_repos(repos)
    app.logger.info(f"Unregistered local repo: {repo_name}")
    return redirect(url_for('index'))


@app.route('/remove_repo/<path:repo_name>', methods=['POST'])
def remove_repo(repo_name):
    """Remove any repository — unregister local repos, delete cloned repos."""
    import shutil

    # Check if it's a registered local repo first
    repos = load_local_repos()
    if repo_name in repos:
        repos.pop(repo_name)
        save_local_repos(repos)
        app.logger.info(f"Unregistered local repo: {repo_name}")
        return redirect(url_for('index'))

    # Otherwise it's a cloned repo — delete the directory
    cloned_path = os.path.join(BASE_REPO_PATH, repo_name)
    real_cloned = os.path.realpath(cloned_path)
    real_base = os.path.realpath(BASE_REPO_PATH)
    if not real_cloned.startswith(real_base + os.sep):
        app.logger.warning(f"Refusing to remove repo outside base path: {repo_name}")
        return redirect(url_for('index'))

    if os.path.isdir(cloned_path):
        shutil.rmtree(cloned_path)
        app.logger.info(f"Deleted cloned repo: {cloned_path}")

    return redirect(url_for('index'))


@app.route('/toggle_public/<path:repo_name>', methods=['POST'])
def toggle_public(repo_name):
    """Toggle a repo's public visibility flag."""
    repos = load_local_repos()
    if repo_name not in repos:
        return redirect(url_for('index'))
    repos[repo_name]['public'] = not repos[repo_name].get('public', False)
    save_local_repos(repos)
    app.logger.info(f"Toggled public flag for {repo_name}: {repos[repo_name]['public']}")
    return redirect(url_for('index'))


@app.route('/webhook_secret/<path:repo_name>', methods=['POST'])
def manage_webhook_secret(repo_name):
    """Generate, set, or remove a webhook secret for a repo."""
    repos = load_local_repos()
    if repo_name not in repos:
        return jsonify({'error': 'Repo not found'}), 404
    action = request.form.get('action', 'generate')
    if action == 'remove':
        repos[repo_name]['webhook_secret'] = None
    else:
        # Generate a secure random secret
        repos[repo_name]['webhook_secret'] = hashlib.sha256(os.urandom(32)).hexdigest()
    save_local_repos(repos)
    return redirect(url_for('index'))


# Webhook rate limiter — in-memory timestamp per repo (30s minimum between triggers)
_webhook_last_triggered = {}


@app.route('/api/webhook/<path:repo_name>', methods=['POST'])
def webhook_trigger(repo_name):
    """Webhook endpoint for GitHub/GitLab push events.

    Verifies HMAC-SHA256 (GitHub X-Hub-Signature-256), GitLab token
    (X-Gitlab-Token), or Bearer header. Rate-limited to 30s between triggers.
    Runs pull + kanban rebuild and returns a JSON acknowledgment.
    """
    import hmac as _hmac
    import time

    secret = get_webhook_secret(repo_name)
    if not secret:
        return jsonify({'error': 'No webhook configured for this repo'}), 404

    # --- Verify signature ---
    verified = False

    # GitHub: X-Hub-Signature-256
    gh_sig = request.headers.get('X-Hub-Signature-256', '')
    if gh_sig.startswith('sha256='):
        expected = _hmac.new(secret.encode(), request.get_data(), 'sha256').hexdigest()
        if _hmac.compare_digest(gh_sig[7:], expected):
            verified = True

    # GitLab: X-Gitlab-Token
    gl_token = request.headers.get('X-Gitlab-Token', '')
    if gl_token and _hmac.compare_digest(gl_token, secret):
        verified = True

    # Bearer token fallback
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer ') and _hmac.compare_digest(auth_header[7:], secret):
        verified = True

    if not verified:
        return jsonify({'error': 'Invalid signature'}), 403

    # --- Rate limit ---
    now = time.time()
    last = _webhook_last_triggered.get(repo_name, 0)
    if now - last < 30:
        return jsonify({'error': 'Rate limited', 'retry_after': int(30 - (now - last))}), 429
    _webhook_last_triggered[repo_name] = now

    # --- Pull + rebuild ---
    repo_path = resolve_repo_path(repo_name)
    if not repo_path:
        return jsonify({'error': 'Repo not found'}), 404

    pull_result = pull_repository(repo_path)

    from .kanban import build_kanban, write_canvas
    exclusions = load_exclusions(repo_path)
    todo_md_files = find_todo_files(repo_path, exclusions=exclusions)
    todos = list(find_todos(repo_path, exclusions=exclusions))
    canvas = build_kanban(todo_md_files, todos)
    write_canvas(repo_path, canvas)

    card_count = sum(1 for n in canvas['nodes'] if n['type'] == 'text')
    return jsonify({
        'ok': True,
        'pull': pull_result.get('message', ''),
        'cards': card_count,
    })


@app.route('/scan/<path:repo_url>')
def scan_repo(repo_url):
    """Redirect legacy /scan/ URLs to the streaming view."""
    return redirect(url_for('scan_stream', repo_url=repo_url, shallow=request.args.get('shallow', '')))

@app.route('/stream_data/<path:repo_url>')
def stream_data(repo_url):
    """Stream the scan results for a repository."""
    shallow = request.args.get('shallow') == '1'
    def generate():
        try:
            # Flush padding — forces proxies (Cloudflare, nginx) to send the stream immediately
            yield ": padding\n\n"

            # Try to resolve an existing repo path BEFORE clone/pull so we can
            # show TODO.md instantly while the heavier operations run after
            existing_path = resolve_repo_path(repo_url)

            skipped = []

            if existing_path:
                repo_name = os.path.basename(os.path.normpath(existing_path))
                origin_url = get_repo_origin_url(existing_path) or repo_url

                # Load exclusions before the first scan so the fast TODO.md pass is filtered too
                exclusions = load_exclusions(existing_path)

                # Send repo metadata and TODO.md immediately — no waiting
                branch = get_repo_branch(existing_path)
                # Instant-load: include the previous KANBAN.canvas so the board
                # appears immediately (marked stale) while the scan runs.
                cached_canvas = None
                canvas_path = os.path.join(existing_path, 'KANBAN.canvas')
                if os.path.isfile(canvas_path):
                    try:
                        with open(canvas_path, 'r', encoding='utf-8') as _cf:
                            cached_canvas = json.load(_cf)
                    except (json.JSONDecodeError, OSError):
                        pass
                init_payload = {'type': 'init', 'repo_name': repo_name, 'repo_url': origin_url, 'branch': branch}
                if cached_canvas:
                    init_payload['cached_canvas'] = cached_canvas
                # Local repos expose their path for local editor URIs (vscode://, cursor://)
                if repo_url in load_local_repos():
                    init_payload['local_path'] = existing_path
                yield f"data: {json.dumps(init_payload)}\n\n"
                todo_md_files = find_todo_files(existing_path, exclusions=exclusions, skipped=skipped)
                if todo_md_files:
                    yield f"data: {json.dumps({'type': 'todo_md_files', 'files': todo_md_files})}\n\n"

                # Now pull/refresh in the background (user already sees TODO.md)
                yield f"data: {json.dumps({'type': 'status', 'message': 'Updating repository...'})}\n\n"
                repo_path = clone_repository(repo_url, shallow=shallow)
                # Reload exclusions in case the pull updated .todoscope-exclude.csv
                exclusions = load_exclusions(repo_path)
            else:
                # New repo — must clone first
                yield f"data: {json.dumps({'type': 'status', 'message': 'Cloning repository...'})}\n\n"
                repo_path = clone_repository(repo_url, shallow=shallow)
                repo_name = os.path.basename(repo_path)
                origin_url = get_repo_origin_url(repo_path) or repo_url
                exclusions = load_exclusions(repo_path)

                branch = get_repo_branch(repo_path)
                yield f"data: {json.dumps({'type': 'init', 'repo_name': repo_name, 'repo_url': origin_url, 'branch': branch})}\n\n"
                todo_md_files = find_todo_files(repo_path, exclusions=exclusions, skipped=skipped)
                if todo_md_files:
                    yield f"data: {json.dumps({'type': 'todo_md_files', 'files': todo_md_files})}\n\n"

            yield f"data: {json.dumps({'type': 'status', 'message': 'Scanning code for inline TODOs...'})}\n\n"

            # Stream each TODO as it's found, collecting them for kanban generation
            todo_count = 0
            todos_collected = []
            for todo in find_todos(repo_path, exclusions=exclusions, skipped=skipped):
                todo_count += 1
                todos_collected.append(todo)
                yield f"data: {json.dumps({'type': 'todo', 'todo': todo.to_dict(), 'count': todo_count})}\n\n"

            # Report excluded paths before completion so the client can render them
            if skipped:
                yield f"data: {json.dumps({'type': 'excluded', 'items': skipped})}\n\n"

            # Generate KANBAN.canvas — the board is a view of the code.
            # Emitted before 'complete' because the client closes the stream on complete.
            from .kanban import build_kanban, write_canvas
            canvas = build_kanban(todo_md_files, todos_collected)
            write_canvas(repo_path, canvas)
            yield f"data: {json.dumps({'type': 'kanban', 'canvas': canvas})}\n\n"

            # Send completion event with repo_name for fingerprint polling
            # Tell the client whether this is a local or cloned repo (for refresh behavior)
            source = 'local' if repo_url in load_local_repos() else 'cloned'
            yield f"data: {json.dumps({'type': 'complete', 'count': todo_count, 'repo_name': repo_name, 'source': source})}\n\n"

        except Exception as e:
            app.logger.error(f"Error streaming scan: {str(e)}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
    
    # Use Response directly with headers that disable all buffering layers
    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache, no-transform',
            'X-Accel-Buffering': 'no',
            'Connection': 'keep-alive',
        }
    )

@app.route('/scan_stream/<path:repo_url>')
def scan_stream(repo_url):
    """Render the streaming scan page for a repository."""
    shallow = request.args.get('shallow', '')
    return render_template('stream_results.html', repo_url=repo_url, shallow=shallow)

@app.route('/api/badge/todos/<path:repo_name>')
def badge_todos(repo_name):
    """shields.io endpoint badge — returns live TODO count for a repo.
    Public route (no auth required) — returns a count only, no code content.
    Usage: https://img.shields.io/endpoint?url=https://YOUR_HOST/api/badge/todos/<repo_name>
    """
    repo_path = resolve_repo_path(repo_name)
    if not repo_path:
        return jsonify({
            "schemaVersion": 1,
            "label": "TODOs",
            "message": "repo not found",
            "color": "lightgrey"
        })
    try:
        count = sum(1 for _ in find_todos(repo_path))
        color = "brightgreen" if count == 0 else "yellow" if count < 10 else "orange" if count < 50 else "red"
        return jsonify({
            "schemaVersion": 1,
            "label": "TODOs",
            "message": str(count),
            "color": color
        })
    except Exception as e:
        app.logger.error(f"Badge scan error for {repo_name}: {e}")
        return jsonify({
            "schemaVersion": 1,
            "label": "TODOs",
            "message": "error",
            "color": "lightgrey"
        })

@app.route('/api/repo_fingerprint/<path:repo_name>')
def repo_fingerprint(repo_name):
    """Return a lightweight fingerprint of the repo's current state.
    Combines HEAD commit hash + working tree dirty flag so the client
    can detect local edits or new commits without rescanning.
    """
    repo_path = resolve_repo_path(repo_name)
    if not repo_path:
        return jsonify({'fingerprint': '', 'dirty': False})
    try:
        result = subprocess.run(
            ['git', '-C', repo_path, 'status', '--porcelain=v1'],
            capture_output=True, text=True, timeout=5
        )
        dirty = len(result.stdout.strip()) > 0
        head = subprocess.run(
            ['git', '-C', repo_path, 'rev-parse', '--short', 'HEAD'],
            capture_output=True, text=True, timeout=5
        )
        # Hash TODO.md content so the client can detect TODO-only changes
        todo_files = find_todo_files(repo_path)
        todo_content = ''.join(f.get('content', '') or '' for f in todo_files)
        todo_hash = hashlib.md5(todo_content.encode()).hexdigest()[:8]
        return jsonify({'fingerprint': head.stdout.strip(), 'dirty': dirty, 'todo_hash': todo_hash})
    except Exception:
        return jsonify({'fingerprint': '', 'dirty': False, 'todo_hash': ''})

@app.route('/api/todo_files/<path:repo_name>')
def api_todo_files(repo_name):
    """Return just the TODO.md/TODO.txt content for live refresh.
    Lightweight — no code scanning, just reads the TODO files.
    """
    repo_path = resolve_repo_path(repo_name)
    if not repo_path:
        return jsonify({'files': []})
    return jsonify({'files': find_todo_files(repo_path)})

@app.route('/pull/<path:repo_name>')
def pull_repo(repo_name):
    """Pull the latest changes for a repository and redirect to the scan page."""
    try:
        repo_path = resolve_repo_path(repo_name)
        if not repo_path:
            return render_template('index.html', error=f"Repository not found: {repo_name}",
                                 local_repos=list_local_repositories())
        result = pull_repository(repo_path)
        if result["success"]:
            return redirect(url_for('scan_stream', repo_url=repo_name))
        return render_template('index.html',
                               error=f"Failed to pull latest changes: {result.get('details', '')}",
                               local_repos=list_local_repositories())
    except Exception as e:
        app.logger.error(f"Error pulling repository: {e}")
        return render_template('index.html', error=f"Error pulling repository: {str(e)}",
                               local_repos=list_local_repositories())

@app.template_filter('highlight_todo')
def highlight_todo(text):
    """Highlight the TODO, FIXME, BUG, and NOTE keywords in the text."""
    return re.sub(
        r'(#+\s*(TODO|FIXME|BUG|NOTE)|//\s*(TODO|FIXME|BUG|NOTE)|/\*\s*(TODO|FIXME|BUG|NOTE)|<!--\s*(TODO|FIXME|BUG|NOTE)|;\s*(TODO|FIXME|BUG|NOTE)|(TODO|FIXME|BUG|NOTE):)',
        r'<span class="highlight">\1</span>',
        text, 
        flags=re.IGNORECASE
    )

@app.route('/resources')
def resources():
    """Curated Kanban resources — public, no auth required."""
    return render_template('resources.html')


# ----- MPCO API Endpoints -----

def mpco_response(f):
    """Decorator for MPCO tool endpoints."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            result = f(*args, **kwargs)
            return jsonify({
                "status": "success",
                "result": result
            })
        except Exception as e:
            app.logger.error(f"MPCO error: {str(e)}")
            return jsonify({
                "status": "error",
                "error": str(e)
            }), 500
    return decorated_function

@app.route('/api/mpco/manifest', methods=['GET'])
def mpco_manifest():
    """Return the MPCO tool manifest."""
    return jsonify({
        "schema_version": "v1",
        "name_for_human": "TODO Scanner",
        "name_for_model": "todo_scanner",
        "description_for_human": "Scans git repositories for TODO comments in code",
        "description_for_model": "Use this tool to scan git repositories for TODO comments. Input a git repository URL and get back a list of TODO comments found in the code.",
        "authentication": {
            "type": "none"
        },
        "api": {
            "type": "openapi",
            "url": f"{request.url_root}api/mpco/openapi.json"
        }
    })

def get_api_schema():
    """Generate the API schema based on actual API endpoints."""
    # Define the schema for the TodoItem
    todo_item_schema = {
        "type": "object",
        "properties": {
            "file_path": {"type": "string"},
            "line_num": {"type": "integer"},
            "todo_text": {"type": "string"},
            "next_line": {"type": "string", "nullable": True}
        }
    }
    
    # Define the schema for Repository item
    repo_item_schema = {
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "last_modified": {"type": "string"},
            "scan_url": {"type": "string"}
        }
    }
    
    # Generate the base specification
    spec = {
        "openapi": "3.0.1",
        "info": {
            "title": "TODO Scanner API",
            "description": "API for scanning git repositories for TODO comments",
            "version": "v1"
        },
        "servers": [
            {
                "url": f"{request.url_root}api"
            }
        ],
        "paths": {}
    }
    
    # Add list_repositories endpoint
    spec["paths"]["/list_repositories"] = {
        "get": {
            "operationId": "listRepositories",
            "summary": "List all local repositories that have been scanned",
            "responses": {
                "200": {
                    "description": "List of repositories available locally",
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "repositories": {
                                        "type": "array",
                                        "items": repo_item_schema
                                    },
                                    "count": {"type": "integer"}
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    
    # Add pull_repository endpoint
    spec["paths"]["/pull_repository"] = {
        "post": {
            "operationId": "pullRepository",
            "summary": "Pull the latest changes for a repository",
            "requestBody": {
                "required": True,
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "required": ["repo_name"],
                            "properties": {
                                "repo_name": {
                                    "type": "string",
                                    "description": "Name of the repository to pull updates for"
                                }
                            }
                        }
                    }
                }
            },
            "responses": {
                "200": {
                    "description": "Result of the pull operation",
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "success": {"type": "boolean"},
                                    "message": {"type": "string"},
                                    "details": {"type": "string"},
                                    "repo_name": {"type": "string"},
                                    "origin_url": {"type": "string"},
                                    "last_modified": {"type": "string"},
                                    "scan_url": {"type": "string"}
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    
    # Add scan_repository endpoint
    spec["paths"]["/scan_repository"] = {
        "post": {
            "operationId": "scanRepository",
            "summary": "Scan a git repository for TODO comments",
            "requestBody": {
                "required": True,
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "required": ["repo_url"],
                            "properties": {
                                "repo_url": {
                                    "type": "string",
                                    "description": "URL of the git repository to scan (e.g., https://github.com/username/repo.git)"
                                }
                            }
                        }
                    }
                }
            },
            "responses": {
                "200": {
                    "description": "TODO items found in the repository",
                    "content": {
                        "application/json": {
                            "schema": {
                                "type": "object",
                                "properties": {
                                    "repo_url": {"type": "string"},
                                    "repo_name": {"type": "string"},
                                    "todo_count": {"type": "integer"},
                                    "todos": {
                                        "type": "array",
                                        "items": todo_item_schema
                                    },
                                    "web_url": {"type": "string"}
                                }
                            }
                        }
                    }
                }
            }
        }
    }
    
    # Add scan_repository_stream endpoint
    spec["paths"]["/scan_repository_stream"] = {
        "post": {
            "operationId": "scanRepositoryStream",
            "summary": "Stream the scanning of a git repository for TODO comments",
            "description": "Returns a newline-delimited JSON stream of repository scan results in real-time",
            "requestBody": {
                "required": True,
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "required": ["repo_url"],
                            "properties": {
                                "repo_url": {
                                    "type": "string",
                                    "description": "URL of the git repository to scan (e.g., https://github.com/username/repo.git)"
                                }
                            }
                        }
                    }
                }
            },
            "responses": {
                "200": {
                    "description": "Stream of JSON objects representing TODO items as they are found",
                    "content": {
                        "application/x-ndjson": {
                            "schema": {
                                "type": "object",
                                "oneOf": [
                                    {
                                        "type": "object",
                                        "properties": {
                                            "type": {"type": "string", "enum": ["init"]},
                                            "status": {"type": "string", "enum": ["success"]},
                                            "repo_name": {"type": "string"},
                                            "repo_url": {"type": "string"},
                                            "web_url": {"type": "string"}
                                        }
                                    },
                                    {
                                        "type": "object",
                                        "properties": {
                                            "type": {"type": "string", "enum": ["todo"]},
                                            "status": {"type": "string", "enum": ["success"]},
                                            "todo": todo_item_schema,
                                            "count": {"type": "integer"}
                                        }
                                    },
                                    {
                                        "type": "object",
                                        "properties": {
                                            "type": {"type": "string", "enum": ["complete"]},
                                            "status": {"type": "string", "enum": ["success"]},
                                            "count": {"type": "integer"},
                                            "repo_name": {"type": "string"},
                                            "repo_url": {"type": "string"},
                                            "web_url": {"type": "string"}
                                        }
                                    },
                                    {
                                        "type": "object",
                                        "properties": {
                                            "type": {"type": "string", "enum": ["error"]},
                                            "status": {"type": "string", "enum": ["error"]},
                                            "error": {"type": "string"},
                                            "error_id": {"type": "string", "nullable": True}
                                        }
                                    }
                                ]
                            }
                        }
                    }
                }
            }
        }
    }
    
    return spec

@app.route('/api/mpco/openapi.json', methods=['GET'])
def mpco_openapi():
    """Return the OpenAPI specification for the MPCO endpoints."""
    return jsonify(get_api_schema())

@app.route('/api/mpco/scan_repository', methods=['POST'])
@mpco_response
def api_scan_repository():
    """API endpoint to scan a repository for TODOs."""
    data = request.json
    
    if not data or 'repo_url' not in data:
        raise ValueError("Repository URL is required")
    
    repo_url = data['repo_url']
    shallow = data.get('shallow', False)

    try:
        repo_path = clone_repository(repo_url, shallow=shallow)
        exclusions = load_exclusions(repo_path)
        skipped = []
        todos = list(find_todos(repo_path, exclusions=exclusions, skipped=skipped))
        repo_name = os.path.basename(repo_path)

        # Convert TodoItem objects to dictionaries
        todo_dicts = [todo.to_dict() for todo in todos]

        # Get original repository URL from git config
        origin_url = get_repo_origin_url(repo_path) or repo_url

        # Get full server origin URL for web links
        web_base_url = get_full_origin_url()

        todo_md_files = find_todo_files(repo_path, exclusions=exclusions)

        # Generate KANBAN.canvas — the board is a view of the code
        from .kanban import build_kanban, write_canvas
        canvas = build_kanban(todo_md_files, todos)
        write_canvas(repo_path, canvas)

        return {
            "repo_url": origin_url,
            "repo_name": repo_name,
            "todo_count": len(todos),
            "todos": todo_dicts,
            "todo_md_files": todo_md_files,
            "excluded": skipped,
            "web_url": f"{web_base_url}/scan/{repo_url}",
            "kanban_canvas": canvas
        }

    except Exception as e:
        app.logger.error(f"Error in API scan: {str(e)}")
        raise

@app.route('/api/mpco/list_repositories', methods=['GET'])
@mpco_response
def api_list_repositories():
    """API endpoint to list all local repositories."""
    repos = list_local_repositories()
    
    # Format the response
    origin_url = get_full_origin_url()
    return {
        "repositories": [
            {
                "name": repo["name"],
                "last_modified": repo["last_modified_str"],
                "origin_url": repo["origin_url"],
                "scan_url": f"{origin_url}/scan/{repo['name']}"
            }
            for repo in repos
        ],
        "count": len(repos)
    }

@app.route('/api/mpco/pull_repository', methods=['POST'])
@mpco_response
def api_pull_repository():
    """API endpoint to pull the latest changes for a repository."""
    data = request.json
    
    if not data or 'repo_name' not in data:
        raise ValueError("Repository name is required")
    
    repo_name = data['repo_name']
    repo_path = os.path.join(BASE_REPO_PATH, repo_name)
    
    # Pull the latest changes
    result = pull_repository(repo_path)
    
    # Include additional repository info in the response
    if os.path.isdir(repo_path):
        origin_url = get_repo_origin_url(repo_path) or ""
        last_modified = os.path.getmtime(repo_path)
        result.update({
            "repo_name": repo_name,
            "origin_url": origin_url,
            "last_modified": datetime.fromtimestamp(last_modified).strftime('%Y-%m-%d %H:%M:%S'),
            "scan_url": f"{get_full_origin_url()}/scan/{repo_name}"
        })
    else:
        raise FileSystemError(f"Repository path does not exist after pull: {repo_path}", path=repo_path)

    return result

@app.route('/api/mpco/scan_repository_stream', methods=['POST'])
def api_scan_repository_stream():
    """Streaming API endpoint to scan a repository for TODOs.
    
    Returns a JSON stream where each line is a complete JSON object
    containing either metadata, a TODO item, or completion status.
    """
    data = request.json
    
    if not data or 'repo_url' not in data:
        return jsonify({
            "status": "error",
            "error": "Repository URL is required"
        }), 400
    
    repo_url = data['repo_url']
    shallow = data.get('shallow', False)

    def generate():
        try:
            # Clone the repository first
            repo_path = clone_repository(repo_url, shallow=shallow)
            repo_name = os.path.basename(repo_path)
            origin_url = get_repo_origin_url(repo_path) or repo_url
            web_base_url = get_full_origin_url()
            exclusions = load_exclusions(repo_path)
            skipped = []

            # Send initial metadata
            yield json.dumps({
                "type": "init",
                "status": "success",
                "repo_name": repo_name,
                "repo_url": origin_url,
                "web_url": f"{web_base_url}/scan/{repo_url}"
            }) + "\n"

            # Send standalone TODO.md/TODO.txt files before code comments
            todo_md_files = find_todo_files(repo_path, exclusions=exclusions, skipped=skipped)
            if todo_md_files:
                yield json.dumps({
                    "type": "todo_md_files",
                    "status": "success",
                    "files": todo_md_files
                }) + "\n"

            # Stream each TODO as it's found, collecting for kanban generation
            todo_count = 0
            todos_collected = []

            for todo in find_todos(repo_path, exclusions=exclusions, skipped=skipped):
                todo_count += 1
                todos_collected.append(todo)
                yield json.dumps({
                    "type": "todo",
                    "status": "success",
                    "todo": todo.to_dict(),
                    "count": todo_count
                }) + "\n"

            # Report excluded paths before completion
            if skipped:
                yield json.dumps({
                    "type": "excluded",
                    "status": "success",
                    "items": skipped
                }) + "\n"

            # Generate KANBAN.canvas — the board is a view of the code.
            # Emitted before 'complete' so clients that close on complete still receive it.
            from .kanban import build_kanban, write_canvas
            canvas = build_kanban(todo_md_files, todos_collected)
            write_canvas(repo_path, canvas)
            yield json.dumps({
                "type": "kanban",
                "status": "success",
                "canvas": canvas
            }) + "\n"

            # Send completion event
            yield json.dumps({
                "type": "complete",
                "status": "success",
                "count": todo_count,
                "repo_name": repo_name,
                "repo_url": origin_url,
                "web_url": f"{web_base_url}/scan/{repo_url}"
            }) + "\n"

        except Exception as e:
            app.logger.error(f"Error in streaming API scan: {str(e)}")
            error_message = str(e)
            error_id = getattr(e, 'error_id', None) if isinstance(e, ScannerError) else None
            yield json.dumps({
                "type": "error",
                "status": "error",
                "error": error_message,
                "error_id": error_id
            }) + "\n"
    
    return Response(
        stream_with_context(generate()),
        mimetype='application/x-ndjson'  # Newline-delimited JSON
    )

if __name__ == '__main__':
    # Create the repositories directory if it doesn't exist
    ensure_dir_exists(BASE_REPO_PATH)
    
    # Run the Flask application
    debug = os.environ.get('FLASK_DEBUG', '0') == '1'
    app.run(debug=debug, host='0.0.0.0', port=5000)