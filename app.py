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

app = Flask(__name__)
app.logger.setLevel(logging.INFO)  # Ensure INFO level is set for our logs
app.secret_key = os.urandom(24)  # Required for flash messages

# Configure base repository path
BASE_REPO_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "repositories")

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

def ensure_dir_exists(path):
    """Ensure the directory exists, creating it if necessary."""
    os.makedirs(path, exist_ok=True)

def sanitize_for_llm(text):
    """Sanitize text to avoid issues with LLM processing.
    
    Replaces triple quotes with single quotes to prevent confusion in LLM contexts.
    Also handles other potential problematic patterns for LLMs.
    """
    if text is None:
        return None
        
    # Replace triple quotes with single quotes
    sanitized = text.replace('"""', '"')
    sanitized = sanitized.replace("'''", "'")
    
    # Additional sanitization if needed
    # sanitized = sanitized.replace(..., ...)
    
    return sanitized

def is_valid_git_repo(path_to_check: str) -> bool:
    """Checks if the given path is a valid Git repository work tree."""
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
            
    except subprocess.TimeoutExpired:
        app.logger.error(f"Timeout checking if {path_to_check} is a git repo.")
        return False
    except FileNotFoundError:
        app.logger.error(f"Git command not found. Cannot check if {path_to_check} is a git repo.")
        return False
    except Exception as e:
        app.logger.error(f"Unexpected error checking git status for {path_to_check}: {e}")
        return False

def get_repo_origin_url(repo_path):
    """Get the remote origin URL of a git repository."""
    try:
        # Run git command to get the remote origin URL
        result = subprocess.run(
            ['git', '-C', repo_path, 'config', '--get', 'remote.origin.url'],
            capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        app.logger.error(f"Failed to get origin URL for repo at {repo_path}")
        return None

def pull_repository(repo_path):
    """Pull the latest changes from the remote repository.
    
    Args:
        repo_path: The local path to the repository
        
    Returns:
        dict: Status of the pull operation with details
    """
    try:
        app.logger.info(f"Pulling latest changes for repository at {repo_path}")
        
        # Check if the repository exists locally
        if not os.path.isdir(repo_path) or not os.path.isdir(os.path.join(repo_path, '.git')):
            return {"success": False, "message": "Not a valid git repository"}
        
        # Run git pull
        result = subprocess.run(
            ['git', '-C', repo_path, 'pull'],
            capture_output=True, text=True
        )
        
        if result.returncode == 0:
            # Update the modification time of the directory after a successful pull
            # This ensures the "Last Updated" timestamp is refreshed
            current_time = datetime.now().timestamp()
            os.utime(repo_path, (current_time, current_time))
            
            return {
                "success": True,
                "message": "Successfully pulled latest changes",
                "details": sanitize_for_llm(result.stdout.strip())
            }
        else:
            return {
                "success": False,
                "message": "Failed to pull latest changes",
                "details": sanitize_for_llm(result.stderr.strip())
            }
    except Exception as e:
        app.logger.error(f"Error pulling repository: {str(e)}")
        return {"success": False, "message": f"Error: {str(e)}"}

def get_full_origin_url():
    """Get the full origin URL including protocol and hostname."""
    
    # Check for X-Forwarded-Proto and X-Forwarded-Host headers (used by proxies and Cloudflare)
    proto = request.headers.get('X-Forwarded-Proto') or request.scheme
    host = request.headers.get('X-Forwarded-Host') or request.headers.get('Host') or request.host
    
    # Build and return the full origin URL
    return f"{proto}://{host}"

def clone_repository(repo_url):
    """Clone the repository if it doesn't exist."""
    repo_name = os.path.basename(repo_url)
    if repo_name.endswith('.git'):
        repo_name = repo_name[:-4]
    
    repo_path = os.path.join(BASE_REPO_PATH, repo_name)
    
    if not os.path.isdir(repo_path):
        app.logger.info(f"Cloning repository: {repo_url}")
        ensure_dir_exists(os.path.dirname(repo_path))
        subprocess.run(['git', 'clone', repo_url, repo_path], check=True)
    
    return repo_path

def is_git_ignored(repo_path, file_path):
    """Check if a file is ignored by git.
    
    Args:
        repo_path: The path to the git repository
        file_path: The path to the file to check (relative or absolute)
        
    Returns:
        bool: True if the file is ignored by git, False otherwise
    """
    try:
        # Convert to relative path if absolute
        if os.path.isabs(file_path):
            file_path = os.path.relpath(file_path, repo_path)
            
        # Use git check-ignore to determine if the file is ignored
        result = subprocess.run(
            ['git', '-C', repo_path, 'check-ignore', '-q', file_path],
            capture_output=True
        )
        # Return code 0 means the file is ignored
        return result.returncode == 0
    except Exception as e:
        app.logger.error(f"Error checking if file is ignored: {e}")
        return False

def is_text_file(file_path):
    """Check if a file is a text file using the file command."""
    try:
        mime_type = mimetypes.guess_type(file_path)[0]
        if mime_type is None:
            # If mime type can't be guessed from extension, use file command
            result = subprocess.run(['file', '--brief', '--mime', file_path], 
                                    capture_output=True, text=True, check=True)
            return result.stdout.strip().startswith('text/')
        return mime_type.startswith('text/')
    except Exception as e:
        app.logger.error(f"Error checking file type: {e}")
        return False

def list_local_repositories():
    """List all local repositories that have been cloned."""
    repos = []
    app.logger.info(f"Listing local repositories from: {BASE_REPO_PATH}")
    
    try:
        ensure_dir_exists(BASE_REPO_PATH)
        
        items_in_base_path = os.listdir(BASE_REPO_PATH)
        app.logger.info(f"Items found in BASE_REPO_PATH: {items_in_base_path}")

        for item in items_in_base_path:
            full_path = os.path.join(BASE_REPO_PATH, item)
            app.logger.info(f"Processing item: {item} at full_path: {full_path}")

            if is_valid_git_repo(full_path):  # Using new robust check
                app.logger.info(f"Item {item} at {full_path} is identified as a valid git repo.")
                last_modified = os.path.getmtime(full_path)
                origin_url = get_repo_origin_url(full_path)
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
                app.logger.info(f"Skipping {item} at {full_path} as it's not identified as a valid git repo by is_valid_git_repo.")
        
        repos.sort(key=lambda x: x['last_modified'], reverse=True)
        
    except Exception as e:
        app.logger.error(f"Error listing repositories: {e}", exc_info=True)
    
    app.logger.info(f"Final list of repository names to be returned: {[repo['name'] for repo in repos]}")
    return repos

def find_todos(repo_path):
    """Find TODO comments in all text files in the repository.
    
    This is now a generator function that yields TodoItem objects as they're found,
    allowing for streaming results as the scan progresses.
    """
    
    for root, _, files in os.walk(repo_path):
        for file in files:
            if file.startswith('.git'):
                continue
                
            file_path = os.path.join(root, file)
            rel_path = os.path.relpath(file_path, repo_path)
            
            # Skip files that are ignored by git
            if is_git_ignored(repo_path, file_path):
                app.logger.debug(f"Skipping git-ignored file: {rel_path}")
                continue
                
            if not is_text_file(file_path):
                continue
                
            app.logger.info(f"Processing file: {rel_path}")
            
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
                    
                for i, line in enumerate(lines):
                    # Look for common TODO patterns
                    if re.search(r'#+\s*TODO|//\s*TODO|TODO:', line, re.IGNORECASE):
                        todo_text = line.strip()
                        next_line_text = lines[i+1].strip() if i+1 < len(lines) else None
                        # Yield the TodoItem as it's found instead of accumulating them
                        yield TodoItem(rel_path, i+1, todo_text, next_line_text)
            except Exception as e:
                app.logger.error(f"Error processing file {rel_path}: {e}")

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
    """Highlight the TODO keyword in the text."""
    return re.sub(r'(#+\s*TODO|//\s*TODO|TODO:)', r'<span class="highlight">\1</span>', text, flags=re.IGNORECASE)

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
    
    return result

if __name__ == '__main__':
    # Create the repositories directory if it doesn't exist
    ensure_dir_exists(BASE_REPO_PATH)
    
    # Run the Flask application
    app.run(debug=True, host='0.0.0.0', port=5000)