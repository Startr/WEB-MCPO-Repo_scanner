from flask import Flask, render_template, request, redirect, url_for, jsonify
import os
import subprocess
import re
import mimetypes
from pathlib import Path
import logging
import json
from functools import wraps

app = Flask(__name__)
app.logger.setLevel(logging.INFO)

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
            'todo_text': self.todo_text,
            'next_line': self.next_line
        }

def ensure_dir_exists(path):
    """Ensure the directory exists, creating it if necessary."""
    os.makedirs(path, exist_ok=True)

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

def find_todos(repo_path):
    """Find TODO comments in all text files in the repository."""
    todos = []
    
    for root, _, files in os.walk(repo_path):
        for file in files:
            if file.startswith('.git'):
                continue
                
            file_path = os.path.join(root, file)
            rel_path = os.path.relpath(file_path, repo_path)
            
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
                        todos.append(TodoItem(rel_path, i+1, todo_text, next_line_text))
            except Exception as e:
                app.logger.error(f"Error processing file {rel_path}: {e}")
    
    return todos

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        repo_url = request.form.get('repo_url')
        if not repo_url:
            return render_template('index.html', error="Repository URL is required")
        
        return redirect(url_for('scan_repo', repo_url=repo_url))
    
    return render_template('index.html')

@app.route('/scan/<path:repo_url>')
def scan_repo(repo_url):
    try:
        repo_path = clone_repository(repo_url)
        todos = find_todos(repo_path)
        repo_name = os.path.basename(repo_path)
        
        return render_template('results.html', 
                              repo_url=repo_url,
                              repo_name=repo_name,
                              todos=todos,
                              count=len(todos))
    
    except Exception as e:
        app.logger.error(f"Error scanning repository: {e}")
        return render_template('index.html', error=f"Error scanning repository: {str(e)}")

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

@app.route('/api/mpco/openapi.json', methods=['GET'])
def mpco_openapi():
    """Return the OpenAPI specification for the MPCO endpoints."""
    return jsonify({
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
        "paths": {
            "/scan_repository": {
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
                                                "items": {
                                                    "type": "object",
                                                    "properties": {
                                                        "file_path": {"type": "string"},
                                                        "line_num": {"type": "integer"},
                                                        "todo_text": {"type": "string"},
                                                        "next_line": {"type": "string"}
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    })

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
        todos = find_todos(repo_path)
        repo_name = os.path.basename(repo_path)
        
        # Convert TodoItem objects to dictionaries
        todo_dicts = [todo.to_dict() for todo in todos]
        
        return {
            "repo_url": repo_url,
            "repo_name": repo_name,
            "todo_count": len(todos),
            "todos": todo_dicts,
            "web_url": f"{request.url_root}scan/{repo_url}"
        }
        
    except Exception as e:
        app.logger.error(f"Error in API scan: {str(e)}")
        raise

if __name__ == '__main__':
    # Create the repositories directory if it doesn't exist
    ensure_dir_exists(BASE_REPO_PATH)
    
    # Run the Flask application
    app.run(debug=True, host='0.0.0.0', port=5000)