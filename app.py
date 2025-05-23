from flask import Flask, render_template, request, redirect, url_for, jsonify, flash
import os
import subprocess
import re
import mimetypes
from pathlib import Path
import logging
import json
from datetime import datetime
from functools import wraps
from datetime import datetime

# Import our robust error handling system
from error_handling import (
    ErrorCategory, ErrorSeverity, ErrorContext, ScannerError,
    ValidationError, NetworkError, GitOperationError, FileSystemError,
    ProcessingError, SystemError, ErrorHandler, RetryConfig,
    with_error_handling, error_context, safe_operation
)

app = Flask(__name__)
app.logger.setLevel(logging.INFO)  # Ensure INFO level is set for our logs
app.secret_key = os.urandom(24)  # Required for flash messages

# Initialize the centralized error handler
app.error_handler = ErrorHandler(app.logger)

# Configure base repository path
BASE_REPO_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "repositories")

# Register recovery strategies for different error types
def git_recovery_strategy(error: ScannerError):
    """Recovery strategy for git operation failures"""
    if isinstance(error, GitOperationError):
        app.logger.info(f"Attempting git recovery for {error.error_id}")
        # Could implement strategies like:
        # - Retry with different credentials
        # - Fall back to different git methods
        # - Clean up corrupted repositories

def network_recovery_strategy(error: ScannerError):
    """Recovery strategy for network failures"""
    if isinstance(error, NetworkError):
        app.logger.info(f"Attempting network recovery for {error.error_id}")
        # Could implement strategies like:
        # - Switch to backup servers
        # - Adjust timeout settings
        # - Use different network protocols

app.error_handler.register_recovery_strategy(ErrorCategory.GIT_OPERATION, git_recovery_strategy)
app.error_handler.register_recovery_strategy(ErrorCategory.NETWORK, network_recovery_strategy)

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
                             local_repos=safe_list_local_repositories()), 500

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
def clone_repository(repo_url):
    """Clone the repository if it doesn't exist."""
    if not repo_url:
        raise ValidationError("Repository URL cannot be empty", field="repo_url")
    
    if not repo_url.startswith(('http://', 'https://', 'git@')):
        raise ValidationError("Invalid repository URL format", field="repo_url")
    
    repo_name = os.path.basename(repo_url)
    if repo_name.endswith('.git'):
        repo_name = repo_name[:-4]
    
    repo_path = os.path.join(BASE_REPO_PATH, repo_name)
    
    if not os.path.isdir(repo_path):
        with error_context("clone_repository", "git_operations", repo_url=repo_url):
            app.logger.info(f"Cloning repository: {repo_url}")
            ensure_dir_exists(os.path.dirname(repo_path))
            
            try:
                result = subprocess.run(
                    ['git', 'clone', repo_url, repo_path], 
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

@safe_operation(default_return=[], log_errors=True)
def safe_list_local_repositories():
    """Safe wrapper for list_local_repositories that won't crash the app"""
    return list_local_repositories()

@with_error_handling("list_repositories", "repository_manager")
def list_local_repositories():
    """List all local repositories that have been cloned."""
    repos = []
    
    with error_context("list_repositories", "repository_manager", base_path=BASE_REPO_PATH):
        app.logger.info(f"Listing local repositories from: {BASE_REPO_PATH}")
        
        ensure_dir_exists(BASE_REPO_PATH)
        
        try:
            items_in_base_path = os.listdir(BASE_REPO_PATH)
        except OSError as e:
            raise FileSystemError(f"Cannot access repository directory {BASE_REPO_PATH}", 
                                 path=BASE_REPO_PATH, original_exception=e)
        
        app.logger.info(f"Items found in BASE_REPO_PATH: {items_in_base_path}")

        for item in items_in_base_path:
            full_path = os.path.join(BASE_REPO_PATH, item)
            app.logger.info(f"Processing item: {item} at full_path: {full_path}")

            try:
                if is_valid_git_repo(full_path):
                    app.logger.info(f"Item {item} at {full_path} is identified as a valid git repo.")
                    
                    try:
                        last_modified = os.path.getmtime(full_path)
                        origin_url = get_repo_origin_url(full_path)
                    except Exception as e:
                        app.logger.warning(f"Error getting metadata for {item}: {e}")
                        continue
                    
                    app.logger.info(f"Origin URL for {item}: {origin_url}")
                    
                    repos.append({
                        'name': item,
                        'path': full_path,
                        'last_modified': last_modified,
                        'last_modified_str': datetime.fromtimestamp(last_modified).strftime('%Y-%m-%d %H:%M:%S'),
                        'origin_url': origin_url or ""
                    })
                    app.logger.info(f"Added {item} to repositories list.")
                else:
                    app.logger.info(f"Skipping {item} at {full_path} as it's not identified as a valid git repo.")
            except Exception as e:
                app.logger.warning(f"Error processing repository {item}: {e}")
                continue
        
        repos.sort(key=lambda x: x['last_modified'], reverse=True)
    
    app.logger.info(f"Final list of repository names to be returned: {[repo['name'] for repo in repos]}")
    return repos

@with_error_handling("find_todos", "file_processor")
def find_todos(repo_path):
    """Find TODO comments in all text files in the repository."""
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
    
    with error_context("find_todos", "file_processor", repo_path=repo_path):
        for root, _, files in os.walk(repo_path):
            for file in files:
                if file.startswith('.git'):
                    continue
                    
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, repo_path)
                
                try:
                    # Skip files that are ignored by git
                    if is_git_ignored(repo_path, file_path):
                        app.logger.debug(f"Skipping git-ignored file: {rel_path}")
                        continue
                        
                    if not is_text_file(file_path):
                        continue
                        
                    app.logger.info(f"Processing file: {rel_path}")
                    
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

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        repo_url = request.form.get('repo_url')
        if not repo_url:
            return render_template('index.html', error="Repository URL is required")
        
        return redirect(url_for('scan_repo', repo_url=repo_url))
    
    # Get list of local repositories to display
    local_repos = list_local_repositories()
    
    return render_template('index.html', local_repos=local_repos)

@app.route('/scan/<path:repo_url>')
def scan_repo(repo_url):
    """Scan a repository for TODOs."""
    try:
        repo_path = clone_repository(repo_url)
        todos = list(find_todos(repo_path))
        repo_name = os.path.basename(repo_path)
        
        # Get the repository's origin URL
        origin_url = get_repo_origin_url(repo_path) or repo_url
        
        return render_template('results.html', 
                              repo_url=origin_url,
                              repo_name=repo_name,
                              todos=todos,
                              count=len(todos))
    
    except Exception as e:
        app.logger.error(f"Error scanning repository: {e}")
        return render_template('index.html', error=f"Error scanning repository: {str(e)}")

@app.route('/stream_data/<path:repo_url>')
def stream_data(repo_url):
    """Stream the scan results for a repository."""
    def generate():
        try:
            repo_path = clone_repository(repo_url)
            repo_name = os.path.basename(repo_path)
            origin_url = get_repo_origin_url(repo_path) or repo_url
            
            # Send initial metadata about the repository
            yield f"data: {json.dumps({'type': 'init', 'repo_name': repo_name, 'repo_url': origin_url})}\n\n"
            
            # Counter for todos
            todo_count = 0
            
            # Stream each TODO as it's found
            for todo in find_todos(repo_path):
                todo_count += 1
                yield f"data: {json.dumps({'type': 'todo', 'todo': todo.to_dict(), 'count': todo_count})}\n\n"
            
            # Send completion event
            yield f"data: {json.dumps({'type': 'complete', 'count': todo_count})}\n\n"
            
        except Exception as e:
            app.logger.error(f"Error streaming scan: {str(e)}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
    
    return app.response_class(
        generate(),
        mimetype='text/event-stream'
    )

@app.route('/scan_stream/<path:repo_url>')
def scan_stream(repo_url):
    """Render the streaming scan page for a repository."""
    return render_template('stream_results.html', repo_url=repo_url)

@app.route('/pull/<path:repo_name>')
def pull_repo(repo_name):
    """Pull the latest changes for a repository and redirect to the scan page."""
    try:
        repo_path = os.path.join(BASE_REPO_PATH, repo_name)
        
        # Pull the latest changes
        result = pull_repository(repo_path)
        
        if result["success"]:
            flash_message = f"Successfully pulled latest changes: {result.get('details', '')}"
            return redirect(url_for('scan_repo', repo_url=repo_name))
        else:
            error_message = f"Failed to pull latest changes: {result.get('details', '')}"
            return render_template('index.html', error=error_message, local_repos=list_local_repositories())
        
    except Exception as e:
        app.logger.error(f"Error pulling repository: {e}")
        return render_template('index.html', error=f"Error pulling repository: {str(e)}", local_repos=list_local_repositories())

@app.template_filter('highlight_todo')
def highlight_todo(text):
    """Highlight the TODO, FIXME, BUG, and NOTE keywords in the text."""
    return re.sub(
        r'(#+\s*(TODO|FIXME|BUG|NOTE)|//\s*(TODO|FIXME|BUG|NOTE)|/\*\s*(TODO|FIXME|BUG|NOTE)|<!--\s*(TODO|FIXME|BUG|NOTE)|;\s*(TODO|FIXME|BUG|NOTE)|(TODO|FIXME|BUG|NOTE):)',
        r'<span class="highlight">\1</span>',
        text, 
        flags=re.IGNORECASE
    )

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
    
    try:
        repo_path = clone_repository(repo_url)
        todos = list(find_todos(repo_path))
        repo_name = os.path.basename(repo_path)
        
        # Convert TodoItem objects to dictionaries
        todo_dicts = [todo.to_dict() for todo in todos]
        
        # Get original repository URL from git config
        origin_url = get_repo_origin_url(repo_path) or repo_url
        
        # Get full server origin URL for web links
        web_base_url = get_full_origin_url()
        
        return {
            "repo_url": origin_url,
            "repo_name": repo_name,
            "todo_count": len(todos),
            "todos": todo_dicts,
            "web_url": f"{web_base_url}/scan/{repo_url}"
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

if __name__ == '__main__':
    # Create the repositories directory if it doesn't exist
    ensure_dir_exists(BASE_REPO_PATH)
    
    # Run the Flask application
    app.run(debug=True, host='0.0.0.0', port=5000)