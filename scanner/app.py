from flask import Flask, render_template, request, redirect, url_for, jsonify, flash, Response, stream_with_context, session
import os
import subprocess
import re
import mimetypes
from pathlib import Path
import logging
import json
from datetime import datetime, timedelta
from functools import wraps
import hashlib
import csv
import fnmatch
import yaml

# Import our error handling module (same package, direct import)
from .error_handling import (
    ErrorCategory, ErrorSeverity, ErrorContext, ScannerError,
    ValidationError, NetworkError, GitOperationError, FileSystemError,
    ProcessingError, SystemError, ErrorHandler, RetryConfig,
    with_error_handling, error_context, safe_operation
)

from . import fragments

# --- Frozen app detection (PyInstaller bundles) ---
import sys
if getattr(sys, 'frozen', False):
    _base = sys._MEIPASS
    _template_folder = os.path.join(_base, 'scanner', 'templates')
    _static_folder = os.path.join(_base, 'scanner', 'static')
    app = Flask(__name__, template_folder=_template_folder, static_folder=_static_folder)
else:
    app = Flask(__name__)

app.logger.setLevel(logging.INFO)  # INFO for our logs

# --- Data directory ---
# CLI sets TODOSCOPE_DATA_DIR; Docker/dev uses scanner/ relative paths as fallback.
_DATA_DIR = os.environ.get('TODOSCOPE_DATA_DIR', '')


def _load_secret_key():
    """SECRET_KEY env wins. With a data dir, persist a generated key so
    sessions survive restarts. Otherwise fall back to per-process random."""
    env_key = os.environ.get('SECRET_KEY')
    if env_key:
        return env_key
    if _DATA_DIR:
        key_path = os.path.join(_DATA_DIR, '.secret_key')
        try:
            if os.path.exists(key_path):
                with open(key_path, 'rb') as f:
                    key = f.read()
                if key:
                    return key
            key = os.urandom(24)
            os.makedirs(_DATA_DIR, exist_ok=True)
            fd = os.open(key_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(fd, 'wb') as f:
                f.write(key)
            return key
        except OSError:
            pass  # unwritable data dir: per-process key
    return os.urandom(24)


app.secret_key = _load_secret_key()
app.permanent_session_lifetime = timedelta(days=30)  # "Remember me" horizon

# --- Access key auth ---
if _DATA_DIR:
    ACCESS_KEYS_FILE = os.path.join(_DATA_DIR, "access_keys.csv")
else:
    ACCESS_KEYS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "access_keys.csv")
# Routes that must stay public for MCP discovery, auth itself, and shell readiness probes
_PUBLIC_ROUTES = {'/api/mcpo/manifest', '/api/mcpo/openapi.json', '/login', '/resources', '/health'}


@app.route('/health')
def health():
    """Readiness probe for the desktop shell. Public: no auth, no side effects.
    `auth` lets the shell refuse network sharing while no access key exists."""
    from scanner import __version__
    return jsonify({'status': 'ok', 'app': 'todoscope', 'version': __version__,
                    'auth': _auth_enabled()})

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
    from flask import has_request_context
    if not has_request_context():
        return False  # background fragment rendering (live.py)
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
_PUBLIC_REPO_PREFIXES = ('/scan_stream/', '/stream_data/', '/events/', '/api/repo_fingerprint/', '/api/todo_files/')


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
        return jsonify({'error': 'Valid access key required', 'hint': 'Pass ?key=<your-key> or Authorization: Bearer <key>'}), 401
    return redirect(url_for('login', next=request.url))

# Initialize the centralized error handler
app.error_handler = ErrorHandler(app.logger)

# Configure base repository path
_APP_DIR = os.path.dirname(os.path.abspath(__file__))
_OLD_REPO_PATH = os.path.join(_APP_DIR, "repositories")

if _DATA_DIR:
    BASE_REPO_PATH = os.path.join(_DATA_DIR, "repositories")
    # Auto-migrate: if old scanner/repositories/ exists and new dir is empty, move contents
    if os.path.isdir(_OLD_REPO_PATH) and os.listdir(_OLD_REPO_PATH):
        os.makedirs(BASE_REPO_PATH, exist_ok=True)
        if not os.listdir(BASE_REPO_PATH):
            import shutil
            for item in os.listdir(_OLD_REPO_PATH):
                src = os.path.join(_OLD_REPO_PATH, item)
                dst = os.path.join(BASE_REPO_PATH, item)
                shutil.move(src, dst)
            app.logger.info(f"Migrated repositories from {_OLD_REPO_PATH} → {BASE_REPO_PATH}")
else:
    BASE_REPO_PATH = _OLD_REPO_PATH

# Local repos config — maps safe display names to metadata dicts (never exposed to web)
# When running via CLI/binary, persist to ~/.todoscope/ so data survives restarts.
if _DATA_DIR:
    LOCAL_REPOS_YAML = os.path.join(_DATA_DIR, "local_repos.yaml")
    LOCAL_REPOS_JSON = os.path.join(_DATA_DIR, "local_repos.json")
    SCAN_STATE_DIR = os.path.join(_DATA_DIR, "scan_state")
else:
    LOCAL_REPOS_YAML = os.path.join(_APP_DIR, "local_repos.yaml")
    LOCAL_REPOS_JSON = os.path.join(_APP_DIR, "local_repos.json")  # legacy, auto-migrated
    SCAN_STATE_DIR = os.path.join(_APP_DIR, "scan_state")

SCAN_STATE_SCHEMA = 1  # bump on incompatible cache format change → invalidates old caches


def _normalize_repo_meta(value):
    """Normalize a repo entry: a metadata dict, not a bare path string."""
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
    """Route a scanner error to JSON or the index page."""
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
    """Wrap a 500 in a SystemError and run it through the normal path."""
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
    """Make the directory if it's missing."""
    try:
        os.makedirs(path, exist_ok=True)
    except OSError as e:
        raise FileSystemError(f"Failed to create directory {path}", path=path, original_exception=e)

@safe_operation(default_return=None)
def sanitize_for_llm(text):
    """Normalize quote characters so text survives LLM parsing."""
    if text is None:
        return None
        
    # Replace triple quotes with single quotes
    sanitized = text.replace('"""', '"')
    sanitized = sanitized.replace("'''", "'")
    
    return sanitized

@with_error_handling("git_validation", "repository_manager", RetryConfig(max_attempts=1))
def is_valid_git_repo(path_to_check: str) -> bool:
    """True if the path is a git working tree."""
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
        # Run git command to get the remote origin URL.
        # `git config --get` exits 1 when the key is absent — for a pure-local
        # repo that is a normal state, not an error, so return '' (callers fall
        # back to the registered path / editor links) instead of raising into
        # the retry machinery.
        result = subprocess.run(
            ['git', '-C', repo_path, 'config', '--get', 'remote.origin.url'],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 1 and not result.stdout.strip():
            return ''
        if result.returncode != 0:
            raise subprocess.CalledProcessError(
                result.returncode, 'git config', result.stdout, result.stderr)
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

# ---------------------------------------------------------------------------
# Git blame — author attribution for TODO items
# ---------------------------------------------------------------------------

def _parse_blame_porcelain(output, wanted_lines):
    """Parse git blame --porcelain output, return {line_num: {author, date}} for wanted lines."""
    from datetime import datetime, timezone
    result = {}
    commit_cache = {}  # sha -> {author, date}
    current_sha = None
    current_line = None
    current_author = None
    current_time = None

    for raw_line in output.split('\n'):
        # New blame block: 40-char SHA followed by line numbers
        parts = raw_line.split()
        if (len(parts) >= 3 and len(parts[0]) == 40
                and all(c in '0123456789abcdef' for c in parts[0])):
            current_sha = parts[0]
            current_line = int(parts[2])  # final line number in current file
            current_author = None
            current_time = None
        elif raw_line.startswith('author '):
            current_author = raw_line[7:]
        elif raw_line.startswith('author-time '):
            try:
                current_time = int(raw_line[12:])
            except ValueError:
                current_time = None
        elif raw_line.startswith('\t'):
            # End of block — cache commit info, store result if wanted
            if current_sha and current_author:
                date_str = ''
                if current_time:
                    date_str = datetime.fromtimestamp(current_time, tz=timezone.utc).strftime('%Y-%m-%d')
                commit_cache[current_sha] = {'author': current_author, 'date': date_str}
            if current_line in wanted_lines and current_sha in commit_cache:
                info = commit_cache[current_sha]
                if info['author'] != 'Not Committed Yet':
                    result[current_line] = info

    return result


def git_blame_file(repo_path, rel_path, line_numbers):
    """Run git blame --porcelain on a file, return {line_num: {author, date}} for requested lines.

    Returns empty dict on any failure — blame is best-effort enrichment.
    """
    if not line_numbers:
        return {}
    try:
        result = subprocess.run(
            ['git', '-C', repo_path, 'blame', '--porcelain', '--', rel_path],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode != 0:
            return {}
        return _parse_blame_porcelain(result.stdout, set(line_numbers))
    except subprocess.TimeoutExpired:
        app.logger.warning(f"Blame timeout for {rel_path}")
        return {}
    except Exception as e:
        app.logger.warning(f"Blame failed for {rel_path}: {e}")
        return {}


def collect_blame_data(repo_path, cards):
    """Group cards by file, run blame once per file, return flat blame dict.

    Returns dict keyed as "file_path:line_num" -> {"author": str, "date": str}.
    Stops early if total blame time exceeds 30 seconds.
    """
    import time

    # Group cards by file_path -> set of line_nums
    file_lines = {}
    for card in cards:
        if card.file_path and card.line_num:
            file_lines.setdefault(card.file_path, set()).add(card.line_num)
            # Also include child line numbers (for TODO.md subtasks)
            for child in getattr(card, 'children', []):
                ln = child.get('line_num')
                if ln:
                    file_lines[card.file_path].add(ln)

    blame_result = {}
    start = time.monotonic()

    for file_path, line_nums in file_lines.items():
        if time.monotonic() - start > 30:
            app.logger.info("Blame time budget exceeded, stopping early")
            break
        file_blame = git_blame_file(repo_path, file_path, line_nums)
        for line_num, info in file_blame.items():
            blame_result[f"{file_path}:{line_num}"] = info

    return blame_result


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

# File-view URL templates per host kind.
# Placeholders: {host} {owner} {repo} {branch} {path} {line}
_HOST_TEMPLATES = {
    'github':    'https://vscode.dev/github/{owner}/{repo}/blob/{branch}/{path}#L{line}',
    'gitlab':    'https://{host}/{owner}/{repo}/-/blob/{branch}/{path}#L{line}',
    'gitea':     'https://{host}/{owner}/{repo}/src/branch/{branch}/{path}#L{line}',
    'bitbucket': 'https://bitbucket.org/{owner}/{repo}/src/{branch}/{path}#lines-{line}',
    'sourcehut': 'https://git.sr.ht/~{owner}/{repo}/tree/{branch}/item/{path}#L{line}',
}

_ORIGIN_RE = re.compile(
    r'^(?:https?://(?:[^@/]+@)?|git@|ssh://(?:[^@/]+@)?)'  # https://, git@, ssh:// (optional user)
    r'(?P<host>[^:/]+)'                                    # host
    r'[:/]~?(?P<owner>[^/]+)/'                             # :owner/  or  /owner/  (strip sr.ht's ~)
    r'(?P<repo>[^/]+?)(?:\.git)?/?$'                       # repo (strip .git, optional trailing /)
)

def parse_git_origin(url):
    """Return {kind, host, owner, repo} for a known git host, else None.
    Accepts https://, ssh://, and git@host:owner/repo forms.
    """
    if not url:
        return None
    m = _ORIGIN_RE.match(url.strip())
    if not m:
        return None
    host = m.group('host').lower()
    if host == 'github.com':
        kind = 'github'
    elif host == 'gitlab.com' or host.startswith('gitlab.'):
        kind = 'gitlab'
    elif host == 'bitbucket.org':
        kind = 'bitbucket'
    elif host == 'codeberg.org':
        kind = 'gitea'
    elif host == 'git.sr.ht':
        kind = 'sourcehut'
    else:
        return None
    return {'kind': kind, 'host': host, 'owner': m.group('owner'), 'repo': m.group('repo')}

def build_web_file_url_template(parts, branch='HEAD'):
    """Return a file-view URL template with {path} and {line} left unsubstituted,
    suitable for the frontend to fill in per TODO. None if host kind is unknown.
    """
    if not parts:
        return None
    tmpl = _HOST_TEMPLATES.get(parts['kind'])
    if not tmpl:
        return None
    # Substitute everything except {path} and {line} so the frontend just string-replaces.
    return tmpl.format(
        host=parts['host'], owner=parts['owner'], repo=parts['repo'],
        branch=branch, path='{path}', line='{line}',
    )

def build_web_repo_url(parts):
    """Return a repo-root web URL for the host, or None if unknown."""
    if not parts:
        return None
    kind = parts['kind']
    owner = parts['owner']
    repo = parts['repo']
    host = parts['host']
    if kind == 'github':
        return f"https://vscode.dev/github/{owner}/{repo}"
    if kind == 'sourcehut':
        return f"https://git.sr.ht/~{owner}/{repo}"
    # gitlab, gitea, bitbucket all share host/owner/repo at the root.
    return f"https://{host}/{owner}/{repo}"

def _last_scanned_str(repo_name, repo_path=None):
    """Local-time display string for the repo's last scan, or None if never
    scanned (or the scan state is unreadable).

    Scan state is keyed by the directory basename (what stream_data uses), not
    the display name — pass repo_path for registered repos whose display name
    differs from their folder, or the lookup misses and reports "never".
    """
    if repo_path:
        repo_name = os.path.basename(os.path.normpath(repo_path))
    state = load_scan_state(repo_name)
    iso = (state or {}).get('scanned_at')
    if not iso:
        return None
    try:
        dt = datetime.fromisoformat(iso.replace('Z', '+00:00')).astimezone()
        return dt.strftime('%Y-%m-%d %H:%M')
    except ValueError:
        return None


@with_error_handling("list_repositories", "repository_manager")
def list_local_repositories():
    """List all repositories: registered local repos + cloned repos.
    Never exposes filesystem paths — only names and origin URLs.
    """
    repos = []
    seen_names = set()

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
                    'web_view_url': build_web_repo_url(parse_git_origin(origin_url)),
                    'source': 'local',
                    'public': meta.get('public', False),
                    'webhook_secret': bool(meta.get('webhook_secret')),
                    'last_scanned_str': _last_scanned_str(name, repo_path=path),
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
                        'web_view_url': build_web_repo_url(parse_git_origin(origin_url)),
                        'source': 'cloned',
                        'last_scanned_str': _last_scanned_str(item),
                    })
            except Exception as e:
                app.logger.warning(f"Error processing repository {item}: {e}")

    repos.sort(key=lambda x: x['last_modified'], reverse=True)
    return repos

# Shared regex used by find_todos() and rescan_files(). Module-level so both
# code paths use identical pattern semantics.
_TODO_PATTERN = re.compile(
    r'(?:#+|//|/\*|<!--|;)\s*(?:TODO|FIXME|BUG|NOTE)(?:\s*:|(?:\s+))',
    re.IGNORECASE,
)

# Filenames handled separately by find_todo_files() — never scan for inline comments.
# todo.md/todo.txt are handled by the TODO-file pass, not the inline scanner.
# KANBAN.canvas is the scanner's own output — scanning it would re-ingest todo
# text as JSON (today it survives only because `file` calls it application/json).
_SKIP_FILE_NAMES = {'todo.md', 'todo.txt', 'kanban.canvas', 'kanban.canvas.tmp'}
# Directories pruned from os.walk (version control, IDE state, dep caches).
_SKIP_DIR_NAMES = {'.git', '.obsidian', 'node_modules', '__pycache__', '.venv', 'venv'}


def _scan_file_for_todos(repo_path, rel_path):
    """Parse one file for inline TODO comments. Returns [] when the file should
    be skipped (binary / git-ignored / unreadable / TODO.md handled elsewhere).
    Used by both find_todos() (os.walk) and rescan_files() (explicit list).
    """
    if os.path.basename(rel_path).lower() in _SKIP_FILE_NAMES:
        return []
    file_path = os.path.join(repo_path, rel_path)
    if not os.path.isfile(file_path):
        return []
    try:
        if is_git_ignored(repo_path, file_path):
            return []
        if not is_text_file(file_path):
            return []
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
    except Exception as e:
        app.logger.warning(f"Could not read {rel_path}: {e}")
        return []
    items = []
    for i, line in enumerate(lines):
        if _TODO_PATTERN.search(line):
            todo_text = line.strip()
            next_line_text = lines[i + 1].strip() if i + 1 < len(lines) else None
            items.append(TodoItem(rel_path, i + 1, todo_text, next_line_text))
    return items


def scan_state_path(repo_name):
    """Absolute path to the per-repo scan-state JSON file."""
    safe = re.sub(r'[^A-Za-z0-9._-]', '_', repo_name or '')
    return os.path.join(SCAN_STATE_DIR, f"{safe}.json")


def load_scan_state(repo_name):
    """Load the per-repo scan state. Returns None if missing, corrupt, or
    written by a different schema version.
    """
    path = scan_state_path(repo_name)
    if not os.path.isfile(path):
        return None
    try:
        with open(path, 'r', encoding='utf-8') as f:
            state = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        app.logger.warning(f"Discarding corrupt scan state {path}: {e}")
        return None
    if state.get('schema') != SCAN_STATE_SCHEMA:
        return None
    return state


def save_scan_state(repo_name, state):
    """Atomic write via sibling .tmp + os.replace. Best-effort — logs on failure."""
    try:
        ensure_dir_exists(SCAN_STATE_DIR)
        path = scan_state_path(repo_name)
        tmp = path + '.tmp'
        with open(tmp, 'w', encoding='utf-8') as f:
            json.dump(state, f)
        os.replace(tmp, path)
    except OSError as e:
        app.logger.warning(f"Could not persist scan state for {repo_name}: {e}")


def exclusions_hash(exclusions):
    """Stable md5 over sorted (path, reason) tuples — None-safe."""
    items = sorted((e.get('path', ''), e.get('reason', '')) for e in (exclusions or []))
    return hashlib.md5(repr(items).encode()).hexdigest()[:12]


def _git_head_sha(repo_path):
    """Return the current HEAD SHA, or None if the repo has no commits / isn't a git repo."""
    try:
        r = subprocess.run(
            ['git', '-C', repo_path, 'rev-parse', 'HEAD'],
            capture_output=True, text=True, timeout=5,
        )
        if r.returncode != 0:
            return None
        return r.stdout.strip() or None
    except (subprocess.SubprocessError, OSError):
        return None


def git_changed_paths(repo_path, last_sha):
    """Return (changed, deleted) sets of repo-relative paths since last_sha.

    Combines:
      - `git diff --name-status <last_sha>..HEAD`  → committed changes since last scan
      - `git status --porcelain=v1`                → untracked + modified working tree

    Returns (None, None) if last_sha is unreachable (force-push, shallow horizon)
    or any git command fails — caller should fall back to a full scan.
    """
    if not last_sha:
        return None, None
    try:
        # Is the recorded SHA still reachable? Force-push or shallow-clone past
        # the boundary makes the diff meaningless.
        chk = subprocess.run(
            ['git', '-C', repo_path, 'merge-base', '--is-ancestor', last_sha, 'HEAD'],
            capture_output=True, text=True, timeout=5,
        )
        if chk.returncode != 0:
            return None, None

        changed, deleted = set(), set()

        diff = subprocess.run(
            ['git', '-C', repo_path, 'diff', '--name-status', f'{last_sha}..HEAD'],
            capture_output=True, text=True, timeout=10,
        )
        if diff.returncode != 0:
            return None, None
        for line in diff.stdout.splitlines():
            parts = line.split('\t')
            if len(parts) < 2:
                continue
            status, path = parts[0], parts[-1]  # rename emits "R100  old  new" → take new
            if status.startswith('D'):
                deleted.add(path)
            else:
                changed.add(path)
            # Renames: old path is gone too
            if status.startswith('R') and len(parts) == 3:
                deleted.add(parts[1])

        status = subprocess.run(
            ['git', '-C', repo_path, 'status', '--porcelain=v1', '--untracked-files=all'],
            capture_output=True, text=True, timeout=10,
        )
        if status.returncode != 0:
            return None, None
        for line in status.stdout.splitlines():
            if len(line) < 4:
                continue
            xy, path = line[:2], line[3:]
            # Rename in working tree: "R  old -> new"
            if ' -> ' in path:
                old, new = path.split(' -> ', 1)
                deleted.add(old)
                changed.add(new)
            elif 'D' in xy:
                deleted.add(path)
            else:
                changed.add(path)
        return changed, deleted
    except (subprocess.SubprocessError, OSError):
        return None, None


def rescan_files(repo_path, rel_paths, exclusions=None):
    """Re-parse the given files. Returns dict[rel_path -> list[TodoItem-dict]].

    Files that no longer exist or are excluded yield an empty list (caller
    should drop them from the cache). The watch-mode path (Phase 2) will call
    this same helper from a watchdog Observer.
    """
    out = {}
    for rel in rel_paths:
        if os.path.basename(rel).lower() in _SKIP_FILE_NAMES:
            continue  # TODO.md is handled by find_todo_files
        if is_excluded(rel, exclusions):
            out[rel] = []
            continue
        items = _scan_file_for_todos(repo_path, rel)
        out[rel] = [
            {'line_num': t.line_num, 'todo_text': t.todo_text, 'next_line': t.next_line}
            for t in items
        ]
    return out


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

    # Never scan repos we manage — avoids recursing into cloned repos when this
    # project itself is registered as a local repo to track.
    _base_repo_real = os.path.realpath(BASE_REPO_PATH)

    with error_context("find_todos", "file_processor", repo_path=repo_path):
        for root, dirs, files in os.walk(repo_path):
            # Prune noisy directories so os.walk never descends into them,
            # skip the managed-repos directory, and honour .todoscope-exclude.csv.
            dirs[:] = [
                d for d in dirs
                if d not in _SKIP_DIR_NAMES
                and os.path.commonpath([os.path.realpath(os.path.join(root, d)), _base_repo_real]) != _base_repo_real
                and not is_excluded(os.path.relpath(os.path.join(root, d), repo_path), exclusions)
            ]
            for file in files:
                if file.lower() in _SKIP_FILE_NAMES:
                    continue

                rel_path = os.path.relpath(os.path.join(root, file), repo_path)

                # Honour .todoscope-exclude.csv exclusions
                exc = is_excluded(rel_path, exclusions)
                if exc:
                    if skipped is not None:
                        skipped.append({'path': rel_path, 'reason': exc['reason']})
                    continue

                for item in _scan_file_for_todos(repo_path, rel_path):
                    yield item

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
            session.permanent = bool(request.form.get('remember'))
            return redirect(request.args.get('next') or url_for('index'))
        return render_template('login.html', error="That key doesn't match. Check it and try again.", auth_enabled=_auth_enabled())
    return render_template('login.html', error=None, auth_enabled=_auth_enabled())

@app.route('/logout')
def logout():
    session.pop('authed_key', None)
    return redirect(url_for('login'))

def _classify_repo_input(value):
    """'path' when the input reads as a filesystem path, else 'url'.
    Mirrors the client-side hint chip in index.html — keep the two in sync.
    Prefix-based on purpose: deterministic, so the hint never lies about
    what submit will do.
    """
    if '://' in value or value.startswith('git@'):
        return 'url'
    if value.startswith(('/', '~', '.')):
        return 'path'
    return 'url'


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        repo_url = (request.form.get('repo_url') or '').strip()
        if not repo_url:
            return render_template('index.html', error="Enter a repo URL or a local path to scan",
                                   local_repos=list_local_repositories())
        if _classify_repo_input(repo_url) == 'path':
            return _register_local_path(os.path.expanduser(repo_url),
                                        (request.form.get('display_name') or '').strip(),
                                        then_scan=True)
        shallow = '1' if request.form.get('shallow') == 'on' else ''
        return redirect(url_for('scan_stream', repo_url=repo_url, shallow=shallow))

    # Get list of local repositories to display
    local_repos = list_local_repositories()

    return render_template('index.html', local_repos=local_repos)

@app.route('/connect')
def connect():
    """Step-by-step guide for pointing an AI agent at this server."""
    return render_template('connect.html')


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
    session.permanent = True  # bootstrap happens on the owner's machine
    return redirect(url_for('index'))

def _register_local_path(local_path, display_name, then_scan=False):
    """Validate and register a local repository path. Shared by the unified
    dashboard input and the /add_local route. Paths stay server-side only —
    the web sees display names, never filesystem locations.
    """
    if not local_path:
        return render_template('index.html', error="Path is required",
                               local_repos=list_local_repositories())

    if not os.path.isdir(local_path):
        return render_template('index.html', error="Path does not exist on this machine",
                               local_repos=list_local_repositories())

    if not is_valid_git_repo(local_path):
        return render_template('index.html', error="Path is not a git repository",
                               local_repos=list_local_repositories())

    # Default display name to directory basename
    if not display_name:
        display_name = os.path.basename(os.path.normpath(local_path))

    repos = load_local_repos()
    repos[display_name] = {'path': os.path.abspath(local_path), 'public': False, 'webhook_secret': None}
    save_local_repos(repos)
    app.logger.info(f"Registered local repo: {display_name}")

    if then_scan:
        return redirect(url_for('scan_stream', repo_url=display_name))
    return redirect(url_for('index'))


@app.route('/add_local', methods=['POST'])
def add_local_repo():
    """Register a local repository path. The path is stored server-side only
    and never exposed to the web — only the display name is visible.
    """
    return _register_local_path(request.form.get('local_path', '').strip(),
                                request.form.get('display_name', '').strip())

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
    canvas, _cards = build_kanban(todo_md_files, todos)
    write_canvas(repo_path, canvas)

    card_count = sum(1 for n in canvas['nodes'] if n['type'] == 'text')

    # Push fresh fragments to any subscribed live clients
    from . import live
    live.notify_change(repo_name)

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
    # refresh=1 → manual full rescan: ignore the incremental cache entirely.
    force_full = request.args.get('refresh') == '1'
    # Captured here because the generator may outlive the request context.
    # Anonymous viewers of public repos must not see server filesystem paths.
    viewer_authed = _is_authenticated()
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
                parts = parse_git_origin(origin_url)
                init_payload = {
                    'type': 'init', 'repo_name': repo_name, 'repo_url': origin_url, 'branch': branch,
                    'host_kind': parts['kind'] if parts else None,
                    'host':      parts['host'] if parts else None,
                    'owner':     parts['owner'] if parts else None,
                    'repo':      parts['repo'] if parts else None,
                    'web_file_url_template': build_web_file_url_template(parts, branch or 'HEAD'),
                }
                # Local repos expose their path for local editor URIs (vscode://,
                # cursor://) — authed viewers only. Public-repo anonymous viewers
                # get no path: the files aren't on their machine anyway.
                if repo_url in load_local_repos() and viewer_authed:
                    init_payload['local_path'] = existing_path
                yield f"data: {json.dumps(init_payload)}\n\n"
                # Instant-load: render the previous board (marked stale) while the scan runs
                if cached_canvas:
                    prev_state = load_scan_state(repo_name)
                    stale_html = fragments.render_kanban_html(
                        cached_canvas, (prev_state or {}).get('blame'), stale=True)
                    yield f"data: {json.dumps({'type': 'kanban', 'html': stale_html})}\n\n"
                todo_md_files = find_todo_files(existing_path, exclusions=exclusions, skipped=skipped)
                if todo_md_files:
                    md_html = fragments.render_todo_md_files_html(todo_md_files)
                    yield f"data: {json.dumps({'type': 'todo_md_files', 'count': len(todo_md_files), 'html': md_html})}\n\n"

                if repo_url in load_local_repos():
                    # Local working copies are the truth — nothing to pull.
                    # Freshness is the live channel's job, not page load's.
                    repo_path = existing_path
                else:
                    # Cloned repo: the cached board is already painted; pull
                    # behind it and let the fresh fragments morph in changes.
                    yield f"data: {json.dumps({'type': 'status', 'message': 'Checking for new commits...'})}\n\n"
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
                parts = parse_git_origin(origin_url)
                init_payload = {
                    'type': 'init', 'repo_name': repo_name, 'repo_url': origin_url, 'branch': branch,
                    'host_kind': parts['kind'] if parts else None,
                    'host':      parts['host'] if parts else None,
                    'owner':     parts['owner'] if parts else None,
                    'repo':      parts['repo'] if parts else None,
                    'web_file_url_template': build_web_file_url_template(parts, branch or 'HEAD'),
                }
                yield f"data: {json.dumps(init_payload)}\n\n"
                todo_md_files = find_todo_files(repo_path, exclusions=exclusions, skipped=skipped)
                if todo_md_files:
                    md_html = fragments.render_todo_md_files_html(todo_md_files)
                    yield f"data: {json.dumps({'type': 'todo_md_files', 'count': len(todo_md_files), 'html': md_html})}\n\n"

            # --- Decide incremental vs full scan ---
            # Incremental: re-parse only files changed since the last scan's HEAD
            # (plus uncommitted/untracked). Falls back to full scan on any mismatch
            # so the cache can never produce stale results.
            state = None if force_full else load_scan_state(repo_name)
            current_head = _git_head_sha(repo_path)
            exc_hash = exclusions_hash(exclusions)
            changed, deleted = (None, None)
            if state and state.get('last_head') and state.get('exclusions_hash') == exc_hash:
                changed, deleted = git_changed_paths(repo_path, state['last_head'])

            todo_count = 0
            todos_collected = []

            # --- The law: no change → no scan ---
            # KANBAN.canvas is written by the scanner itself and never counts
            # as a repo change.
            effective_changed = None
            if changed is not None:
                effective_changed = {
                    p for p in changed
                    if os.path.basename(p) not in ('KANBAN.canvas', 'KANBAN.canvas.tmp')
                }

            if effective_changed is not None and not effective_changed and not deleted:
                yield f"data: {json.dumps({'type': 'status', 'message': 'No changes since last scan — serving cached results.'})}\n\n"
                blame_data = state.get('blame') or {}
                for rel_path, items in (state.get('todos') or {}).items():
                    for item in items:
                        todos_collected.append(TodoItem(rel_path, item['line_num'], item['todo_text'], item['next_line']))
                todo_count = len(todos_collected)
                from .kanban import build_kanban
                canvas, _cards = build_kanban(todo_md_files, todos_collected)
                md_sources = {f['file_path']: f['content'] for f in todo_md_files if f.get('content')}
                todos_html = fragments.render_todos_list_html(
                    [t.to_dict() for t in todos_collected], blame_data)
                yield f"data: {json.dumps({'type': 'todos_list', 'count': todo_count, 'html': todos_html})}\n\n"
                yield f"data: {json.dumps({'type': 'kanban', 'html': fragments.render_kanban_html(canvas, blame_data, md_sources=md_sources)})}\n\n"
                source = 'local' if repo_url in load_local_repos() else 'cloned'
                yield f"data: {json.dumps({'type': 'complete', 'count': todo_count, 'repo_name': repo_name, 'source': source})}\n\n"
                return

            if changed is not None:
                # --- Incremental path ---
                # effective_changed: the scanner's own KANBAN.canvas writes are
                # not repo changes — keep them out of the count and the rescan.
                short = (state.get('last_head') or '')[:7]
                yield f"data: {json.dumps({'type': 'status', 'message': f'Incremental scan — {len(effective_changed)} file(s) changed since {short}...'})}\n\n"
                cached_todos = dict(state.get('todos') or {})
                for path in deleted:
                    cached_todos.pop(path, None)
                fresh = rescan_files(repo_path, effective_changed, exclusions)
                cached_todos.update(fresh)
                for rel_path, items in cached_todos.items():
                    for item in items:
                        todo = TodoItem(rel_path, item['line_num'], item['todo_text'], item['next_line'])
                        todo_count += 1
                        todos_collected.append(todo)
                todos_html = fragments.render_todos_list_html([t.to_dict() for t in todos_collected])
                yield f"data: {json.dumps({'type': 'todos_list', 'count': todo_count, 'html': todos_html})}\n\n"
            else:
                # --- Full-scan path (today's behavior) ---
                yield f"data: {json.dumps({'type': 'status', 'message': 'Scanning code for inline TODOs...'})}\n\n"
                for todo in find_todos(repo_path, exclusions=exclusions, skipped=skipped):
                    todo_count += 1
                    todos_collected.append(todo)
                    yield f"data: {json.dumps({'type': 'todo', 'count': todo_count, 'html': fragments.render_todo_item_html(todo.to_dict())})}\n\n"

            # Report excluded paths before completion so the client can render them
            if skipped:
                yield f"data: {json.dumps({'type': 'excluded', 'items': skipped})}\n\n"

            # Generate KANBAN.canvas — the board is a view of the code.
            # Emitted before 'complete' because the client closes the stream on complete.
            from .kanban import build_kanban, write_canvas
            canvas, cards = build_kanban(todo_md_files, todos_collected)
            write_canvas(repo_path, canvas)
            md_sources = {f['file_path']: f['content'] for f in todo_md_files if f.get('content')}
            yield f"data: {json.dumps({'type': 'kanban', 'html': fragments.render_kanban_html(canvas, md_sources=md_sources)})}\n\n"

            # Git blame attribution — runs after kanban so the board appears immediately.
            # Best-effort: blame failure never blocks the scan.
            blame_data = collect_blame_data(repo_path, cards)
            if blame_data:
                yield f"data: {json.dumps({'type': 'kanban', 'html': fragments.render_kanban_html(canvas, blame_data, md_sources=md_sources)})}\n\n"
                todos_html = fragments.render_todos_list_html(
                    [t.to_dict() for t in todos_collected], blame_data)
                yield f"data: {json.dumps({'type': 'todos_list', 'count': todo_count, 'html': todos_html})}\n\n"

            # Persist scan state for next-time incremental scan. Best-effort —
            # failure here just means the next scan falls back to full.
            if current_head:
                todos_by_file = {}
                for t in todos_collected:
                    todos_by_file.setdefault(t.file_path, []).append({
                        'line_num': t.line_num,
                        'todo_text': t.todo_text,
                        'next_line': t.next_line,
                    })
                save_scan_state(repo_name, {
                    'schema': SCAN_STATE_SCHEMA,
                    'last_head': current_head,
                    'exclusions_hash': exc_hash,
                    'scanned_at': datetime.utcnow().isoformat() + 'Z',
                    'todos': todos_by_file,
                    'blame': blame_data or {},
                })

            # Send completion event with repo_name for fingerprint polling
            # Tell the client whether this is a local or cloned repo (for refresh behavior)
            source = 'local' if repo_url in load_local_repos() else 'cloned'
            yield f"data: {json.dumps({'type': 'complete', 'count': todo_count, 'repo_name': repo_name, 'source': source})}\n\n"

        except Exception as e:
            app.logger.error(f"Error streaming scan: {str(e)}")
            yield f"data: {json.dumps({'type': 'error', 'message': f'Scan stopped: {e}'})}\n\n"
    
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
    refresh = request.args.get('refresh', '')
    return render_template('stream_results.html', repo_url=repo_url, shallow=shallow,
                           refresh=refresh)


@app.route('/events/<path:repo_name>')
def live_events(repo_name):
    """Persistent SSE channel — pushes freshly rendered board/list fragments
    whenever the repo changes (watchdog for local repos, git poll for clones).
    The client subscribes after its initial scan completes and morphs the
    fragments in place; no reload, no client-side polling.
    """
    repo_path = resolve_repo_path(repo_name)
    if not repo_path:
        return jsonify({'error': 'Unknown repository'}), 404

    from . import live
    is_local = repo_name in load_local_repos()
    q = live.subscribe(repo_name, repo_path, is_local)

    def generate():
        try:
            yield ": connected\n\n"
            while True:
                try:
                    event = q.get(timeout=15)
                except live.Empty:
                    yield ": ping\n\n"   # heartbeat keeps proxies from closing us
                    continue
                yield f"data: {json.dumps(event)}\n\n"
        finally:
            live.unsubscribe(repo_name, q)

    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache, no-transform',
            'X-Accel-Buffering': 'no',
            'Connection': 'keep-alive',
        }
    )

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

@app.route('/api/todo_toggle/<path:repo_name>', methods=['POST'])
def api_todo_toggle(repo_name):
    """Flip a task checkbox in a TODO file — write-back from the web UI.

    Local repos only (the file is the real working copy). Guarded by a
    per-line content hash so a view that predates an editor save can never
    clobber a changed line — stale writes get 409 and the next live morph
    shows the viewer reality. The file write itself triggers the watchdog,
    which rescans and pushes fresh fragments to every subscriber.
    """
    local_repos = load_local_repos()
    if repo_name not in local_repos:
        return jsonify({'error': 'Write-back is only available for registered local repositories'}), 403
    repo_path = local_repos[repo_name]['path']

    data = request.get_json(silent=True) or {}
    rel_path = data.get('file_path') or ''
    line_num = data.get('line_num')
    line_hash = data.get('line_hash') or ''
    checked = bool(data.get('checked'))

    target = os.path.realpath(os.path.join(repo_path, rel_path))
    if not target.startswith(os.path.realpath(repo_path) + os.sep):
        return jsonify({'error': 'Invalid path'}), 400
    if os.path.basename(target).lower() not in ('todo.md', 'todo.txt'):
        return jsonify({'error': 'Not a TODO file'}), 400

    try:
        with open(target, 'r', encoding='utf-8') as f:
            lines = f.read().splitlines(True)
    except OSError as e:
        return jsonify({'error': f'Cannot read file: {e}'}), 404

    if not isinstance(line_num, int) or not (1 <= line_num <= len(lines)):
        return jsonify({'error': 'Line out of range'}), 409
    raw = lines[line_num - 1]
    body = raw.rstrip('\r\n')
    ending = raw[len(body):]
    if hashlib.md5(body.rstrip().encode()).hexdigest()[:8] != line_hash:
        return jsonify({'error': 'Line changed since render'}), 409
    m = re.match(r'^(\s*[-*+] )\[( |x|X)\](.*)$', body)
    if not m:
        return jsonify({'error': 'Not a task line'}), 409

    lines[line_num - 1] = f"{m.group(1)}[{'x' if checked else ' '}]{m.group(3)}{ending}"
    tmp = target + '.td-tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    os.replace(tmp, target)
    return jsonify({'ok': True, 'line': line_num, 'checked': checked})


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

def mcpo_response(f):
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

@app.route('/api/mcpo/manifest', methods=['GET'])
def mcpo_manifest():
    """Return the MPCO tool manifest."""
    return jsonify({
        "schema_version": "v1",
        "name_for_human": "TodoScope",
        "name_for_model": "todo_scanner",
        "description_for_human": "Scans git repositories for TODO comments in code",
        "description_for_model": "Use this tool to scan git repositories for TODO comments. Input a git repository URL and get back a list of TODO comments found in the code.",
        "authentication": {
            "type": "none"
        },
        "api": {
            "type": "openapi",
            "url": f"{request.url_root}api/mcpo/openapi.json"
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
            "title": "TodoScope API",
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

@app.route('/api/mcpo/openapi.json', methods=['GET'])
def mcpo_openapi():
    """Return the OpenAPI specification for the MPCO endpoints."""
    return jsonify(get_api_schema())

@app.route('/api/mcpo/scan_repository', methods=['POST'])
@mcpo_response
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
        canvas, _cards = build_kanban(todo_md_files, todos)
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

@app.route('/api/mcpo/list_repositories', methods=['GET'])
@mcpo_response
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

@app.route('/api/mcpo/pull_repository', methods=['POST'])
@mcpo_response
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

@app.route('/api/mcpo/scan_repository_stream', methods=['POST'])
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
            canvas, _cards = build_kanban(todo_md_files, todos_collected)
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