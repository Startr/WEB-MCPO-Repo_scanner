# API Reference

## Base URL
```
http://localhost:5000/api/mpco
```

## Authentication
Currently no authentication required. Authentication features are planned for future versions.

## Response Format
All API responses follow the MCP (Model Context Protocol) standard format:

### Success Response
```json
{
  "content": [
    {
      "type": "text",
      "text": "Response content here"
    }
  ]
}
```

### Error Response
```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable error message",
    "error_id": "unique_error_identifier"
  }
}
```

## Endpoints

### Scan Repository
Scans a git repository for TODO comments and returns structured results.

**Endpoint:** `POST /scan_repository`

**Request Body:**
```json
{
  "repo_url": "https://github.com/username/repository.git"
}
```

**Response:**
```json
{
  "content": [
    {
      "type": "text",
      "text": "{\n  \"repository\": {\n    \"name\": \"repository\",\n    \"url\": \"https://github.com/username/repository.git\",\n    \"last_commit\": \"abc123...\",\n    \"scan_date\": \"2025-06-09T12:00:00Z\"\n  },\n  \"todos\": [\n    {\n      \"file_path\": \"src/main.py\",\n      \"line_num\": 42,\n      \"todo_text\": \"TODO: Implement error handling\",\n      \"next_line\": \"def process_data():\"\n    }\n  ],\n  \"summary\": {\n    \"total_todos\": 1,\n    \"files_with_todos\": 1,\n    \"todo_types\": {\n      \"TODO\": 1,\n      \"FIXME\": 0,\n      \"BUG\": 0,\n      \"NOTE\": 0\n    }\n  }\n}"
    }
  ]
}
```

**Error Responses:**
- `400 Bad Request`: Missing or invalid repo_url
- `404 Not Found`: Repository not accessible
- `500 Internal Server Error`: Scanning failed

### List Repositories
Lists all locally cloned and scanned repositories.

**Endpoint:** `GET /list_repositories`

**Response:**
```json
{
  "content": [
    {
      "type": "text", 
      "text": "{\n  \"repositories\": [\n    {\n      \"name\": \"repository_name\",\n      \"last_modified\": \"2025-06-09T12:00:00Z\",\n      \"scan_url\": \"/scan/repository_name\",\n      \"todo_count\": 15\n    }\n  ],\n  \"count\": 1\n}"
    }
  ]
}
```

### Pull Repository Updates
Updates a local repository with the latest changes from remote.

**Endpoint:** `POST /pull_repository`

**Request Body:**
```json
{
  "repo_name": "repository_name"
}
```

**Response:**
```json
{
  "content": [
    {
      "type": "text",
      "text": "{\n  \"repository\": \"repository_name\",\n  \"status\": \"updated\",\n  \"changes\": {\n    \"commits_pulled\": 3,\n    \"files_changed\": 5\n  },\n  \"message\": \"Repository updated successfully\"\n}"
    }
  ]
}
```

### Get Repository Scan
Retrieves cached scan results for a specific repository.

**Endpoint:** `GET /scan/{repo_name}`

**Parameters:**
- `repo_name` (path): Name of the repository

**Response:**
Same as scan_repository endpoint, but returns cached results.

### Stream Repository Scan  
Real-time streaming of scan results as they are discovered.

**Endpoint:** `GET /stream/{repo_name}`

**Parameters:**
- `repo_name` (path): Name of the repository

**Response:**
Server-sent events stream with JSON chunks:
```
data: {"type": "file_start", "file_path": "src/main.py"}
data: {"type": "todo_found", "todo": {...}}
data: {"type": "file_complete", "file_path": "src/main.py", "todo_count": 3}
data: {"type": "scan_complete", "summary": {...}}
```

## OpenAPI Specification

The API provides a dynamic OpenAPI specification at:

**Endpoint:** `GET /openapi.json`

This endpoint returns the complete OpenAPI 3.0 specification for all available endpoints, including request/response schemas and examples.

## Rate Limiting

Currently no rate limiting is implemented. This will be added in future versions along with authentication.

## Error Codes

| Code | Description |
|------|-------------|
| `INVALID_REQUEST` | Request body is malformed or missing required fields |
| `REPOSITORY_NOT_FOUND` | Repository URL is not accessible or does not exist |
| `CLONE_FAILED` | Failed to clone repository (network, permissions, etc.) |
| `SCAN_FAILED` | Error occurred during TODO scanning process |
| `INTERNAL_ERROR` | Unexpected server error |

## Usage Examples

### cURL Examples

**Scan a repository:**
```bash
curl -X POST http://localhost:5000/api/mpco/scan_repository \
  -H "Content-Type: application/json" \
  -d '{"repo_url": "https://github.com/username/repo.git"}'
```

**List repositories:**
```bash
curl http://localhost:5000/api/mpco/list_repositories
```

**Pull repository updates:**
```bash
curl -X POST http://localhost:5000/api/mpco/pull_repository \
  -H "Content-Type: application/json" \
  -d '{"repo_name": "repo"}'
```

### Python Example

```python
import requests

# Scan repository
response = requests.post(
    'http://localhost:5000/api/mpco/scan_repository',
    json={'repo_url': 'https://github.com/username/repo.git'}
)

if response.status_code == 200:
    result = response.json()
    todos = result['content'][0]['text']
    print(f"Found TODOs: {todos}")
else:
    error = response.json()
    print(f"Error: {error['error']['message']}")
```

## Future API Features

Planned for upcoming releases:
- Authentication and API keys
- Rate limiting
- Webhook support for automated scanning
- Batch repository operations
- TODO priority inference
- Integration with external task management systems
