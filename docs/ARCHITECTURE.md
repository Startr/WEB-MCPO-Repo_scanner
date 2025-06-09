# Architecture Overview

## System Architecture

Our Repo TODO Scanner follows a modular architecture with clear separation of concerns:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Client    │    │   API Client    │    │   CLI Client    │
│   (Browser)     │    │   (HTTP/JSON)   │    │   (Planned)     │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          └──────────────────────┼──────────────────────┘
                                 │
                    ┌─────────────▼───────────────┐
                    │     Flask Application       │
                    │   (Web + API Routes)        │
                    └─────────────┬───────────────┘
                                  │
                    ┌─────────────▼───────────────┐
                    │     Core Scanner Logic      │
                    │  (Repository Management)    │
                    └─────────────┬───────────────┘
                                  │
          ┌───────────────────────┼───────────────────────┐
          │                       │                       │
    ┌─────▼─────┐       ┌─────────▼─────────┐      ┌──────▼──────┐
    │   Git     │       │   Pattern         │      │   Error     │
    │ Operations│       │  Recognition      │      │  Handling   │
    └───────────┘       └───────────────────┘      └─────────────┘
          │                       │                       │
    ┌─────▼─────┐       ┌─────────▼─────────┐      ┌──────▼──────┐
    │ Local     │       │   File System     │      │  Logging &  │
    │Repository │       │    Scanner        │      │ Monitoring  │
    │ Storage   │       └───────────────────┘      └─────────────┘
    └───────────┘
```

## Core Components

### 1. Flask Application (`scanner/app.py`)
- **Web Interface**: Serves HTML templates for user interaction
- **API Endpoints**: RESTful API following MCP (Model Context Protocol)
- **Request Routing**: Handles both web and API requests
- **Response Formatting**: Converts internal data to appropriate formats

### 2. Scanner Engine (`scanner/app.py`)
- **Repository Cloning**: Git operations for repository management
- **Pattern Recognition**: Multi-pattern TODO detection (TODO, FIXME, BUG, NOTE)
- **File Processing**: Recursive directory traversal with .gitignore support
- **Result Aggregation**: Structures findings into meaningful reports

### 3. Error Handling (`scanner/error_handling.py`)
- **Exception Management**: Custom exception classes for specific errors
- **Recovery Strategies**: Automatic retry mechanisms for transient failures
- **Error Tracking**: Unique error IDs for debugging and monitoring
- **Graceful Degradation**: Continues operation when possible

### 4. Web Interface (`scanner/templates/`)
- **Progressive Enhancement**: Works without JavaScript, enhanced with it
- **Real-time Updates**: Server-sent events for streaming scan results
- **Responsive Design**: Mobile-friendly interface
- **Accessibility**: Screen reader compatible

## Data Flow

### Repository Scanning Process
1. **Input Validation**: Validate repository URL and parameters
2. **Repository Cloning**: Clone or update local repository copy
3. **File Discovery**: Traverse directory structure respecting .gitignore
4. **Pattern Matching**: Search files for TODO patterns using regex
5. **Result Collection**: Aggregate findings with file paths, line numbers, and context
6. **Response Generation**: Format results for web display or API consumption

### Error Handling Flow
1. **Error Detection**: Catch exceptions at operation boundaries
2. **Error Classification**: Determine error type and severity
3. **Recovery Attempt**: Try alternative approaches or retry if appropriate
4. **User Notification**: Provide meaningful error messages with unique IDs
5. **Logging**: Record error details for debugging and monitoring

## API Architecture

### MCP Compliance
The API follows Model Context Protocol standards:
- **Structured Responses**: Consistent response format across endpoints
- **Error Handling**: Standardized error response format
- **Content Types**: Support for multiple content types
- **Schema Validation**: Dynamic OpenAPI specification generation

### Endpoint Design
```
/api/mpco/
├── scan_repository     (POST) - Scan new repository
├── list_repositories   (GET)  - List cached repositories  
├── pull_repository     (POST) - Update repository
├── scan/{repo_name}    (GET)  - Get cached scan results
├── stream/{repo_name}  (GET)  - Stream scan results
└── openapi.json        (GET)  - API specification
```

### Streaming Architecture
- **Server-Sent Events**: Real-time progress updates
- **Chunked Processing**: Process files incrementally
- **Backpressure Handling**: Manage client connection state
- **Error Recovery**: Handle connection drops gracefully

## File Organization

```
repo_scanner/
├── app.py                    # Legacy entry point (to be deprecated)
├── scanner/                  # Main application package
│   ├── __init__.py          # Package initialization
│   ├── app.py               # Core Flask application
│   ├── error_handling.py    # Error management utilities
│   ├── Pipfile              # Python dependencies
│   ├── Pipfile.lock         # Dependency lock file
│   ├── templates/           # Jinja2 HTML templates
│   │   ├── base.html        # Base template with common elements
│   │   ├── index.html       # Main interface
│   │   ├── results.html     # Scan results display
│   │   └── stream_results.html # Real-time results
│   ├── repositories/        # Local repository storage
│   └── tests/               # Test suite
│       ├── test_error_handling.py
│       └── test_pattern_recognition.py
├── docs/                    # Documentation
│   ├── API_REFERENCE.md     # API documentation
│   ├── ARCHITECTURE.md      # This file
│   └── DEVELOPMENT_WORKFLOW.md # Development guide
├── tools/                   # Development and deployment tools
│   ├── run_tests.sh         # Test execution script
│   ├── run_with_cloudflared.sh # Tunnel setup
│   └── sync_readme_todos.sh # Documentation sync
├── Dockerfile               # Container build configuration
├── Makefile                 # Build and development tasks
└── TODO.md                  # Project planning and task tracking
```

## Technology Stack

### Backend
- **Python 3.12+**: Modern Python with type hints
- **Flask**: Lightweight web framework
- **GitPython**: Git repository operations
- **Jinja2**: Template engine for HTML generation
- **Pipenv**: Dependency management and virtual environments

### Frontend  
- **HTML5**: Semantic markup
- **CSS3**: Modern styling with flexbox/grid
- **Vanilla JavaScript**: Progressive enhancement
- **Server-Sent Events**: Real-time updates

### Development Tools
- **Make**: Build automation and task running
- **pytest**: Test framework
- **Docker**: Containerization
- **Cloudflared**: Secure tunneling for development

## Security Considerations

### Current Security Measures
- **Input Validation**: Sanitize repository URLs and user inputs
- **Path Traversal Protection**: Prevent access outside repository directories
- **HTML Escaping**: Prevent XSS in web interface
- **Git Operations**: Isolated repository operations

### Future Security Enhancements
- **Authentication**: User accounts and API keys
- **Authorization**: Role-based access control
- **Rate Limiting**: Prevent abuse and DoS attacks
- **Audit Logging**: Track user actions and system events
- **Content Security Policy**: Enhanced XSS protection

## Performance Characteristics

### Scalability
- **Single-threaded**: Current implementation is single-process
- **I/O Bound**: Performance limited by file system and git operations
- **Memory Efficient**: Streaming results to avoid memory accumulation
- **Disk Usage**: Local repository storage grows with usage

### Performance Optimizations
- **Lazy Loading**: Process files on-demand
- **Streaming Responses**: Avoid buffering large results
- **Gitignore Respect**: Skip irrelevant files
- **Caching**: Store scan results for repeat access

## Future Architecture Plans

### Microservices Architecture
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Service   │    │  Scanner Service │    │  Storage Service│
│   (Frontend)    │    │   (Processing)   │    │   (Database)    │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          └──────────────────────┼──────────────────────┘
                                 │
                    ┌─────────────▼───────────────┐
                    │     Message Queue           │
                    │   (Async Processing)        │
                    └─────────────────────────────┘
```

### Planned Improvements
- **Database Integration**: PostgreSQL for persistent storage
- **Queue System**: Redis/RabbitMQ for background processing
- **Caching Layer**: Redis for scan result caching
- **Load Balancing**: Multiple scanner instances
- **Monitoring**: Prometheus metrics and Grafana dashboards
- **Container Orchestration**: Kubernetes deployment
