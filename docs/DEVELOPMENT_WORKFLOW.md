# Development Workflow

## Setup Development Environment

### 1. Clone and Setup
```bash
git clone https://github.com/Startr/WEB-MCPO-Repo_scanner.git
cd repo_scanner
cd scanner
pipenv install --dev
pipenv shell
```

### 2. Run Tests
```bash
make test
```

### 3. Start Development Server
```bash
make run
```

## Adding New Features

Follow the **Plan-Document-Execute-Verify** cycle from [CONVENTION.instructions.md](../CONVENTION.instructions.md):

### 1. Plan (Add to TODO.md)
Before any work, add to [TODO.md](../TODO.md):
```markdown
- [ ] **Feature Name**: Brief description #tag1 #tag2
  - [ ] Implement core functionality
  - [ ] Add unit tests
  - [ ] Update API documentation
  - [ ] Update README if needed
```

### 2. Document (Update relevant docs)
- Update docstrings for new functions
- Update API schema if adding endpoints
- Update README for user-facing changes
- Update this workflow if process changes

### 3. Execute (Follow coding standards)
- Use error handling decorators from [`error_handling.py`](../scanner/error_handling.py)
- Follow existing patterns in [`app.py`](../scanner/app.py)
- Add comprehensive logging
- Use type hints where possible
- Follow PEP 8 styling

### 4. Verify (Test and validate)
- Run existing tests: `make test`
- Test API endpoints manually
- Test web interface functionality
- Update TODO.md to mark items complete

## Code Standards

### Python Standards
- Use type hints where possible
- Follow PEP 8 styling
- Use the `@safe_operation` decorator for operations that might fail
- All API endpoints should use `@mpco_response` decorator
- Add comprehensive docstrings to all functions and classes

### Error Handling
- Use custom exceptions from `error_handling.py`
- Always provide meaningful error messages
- Include error IDs for tracking
- Handle edge cases gracefully

### Testing
- Write unit tests for all new functions
- Include integration tests for API endpoints
- Test error conditions and edge cases
- Maintain test coverage above 80%

## File Organization

```
repo_scanner/
├── app.py                    # Main application entry point (legacy)
├── scanner/                  # Main package directory
│   ├── __init__.py          # Package initialization
│   ├── app.py               # Flask application and core logic
│   ├── error_handling.py    # Error handling utilities
│   ├── Pipfile              # Python dependencies
│   ├── templates/           # HTML templates
│   └── tests/               # Test files
├── docs/                    # Documentation
├── tools/                   # Development tools and scripts
└── TODO.md                  # Project planning and tasks
```

## Git Workflow

### Commit Messages
Follow conventional commits:
- `feat: add new feature`
- `fix: resolve bug`
- `docs: update documentation`
- `test: add or update tests`
- `refactor: improve code structure`

### Branch Strategy
- `main`: Production-ready code
- `develop`: Integration branch
- `feature/task-name`: Individual features
- `hotfix/issue-name`: Critical fixes

## Deployment

### Local Development
```bash
cd scanner
pipenv shell
python app.py
```

### Docker Deployment
```bash
docker build -t repo-scanner .
docker run -p 5000:5000 repo-scanner
```

## Troubleshooting

### Common Issues
1. **Dependencies not installing**: Ensure pipenv is installed and Python 3.12+ is available
2. **Tests failing**: Check if all dependencies are installed with `pipenv install --dev`
3. **API not responding**: Verify Flask app is running and port 5000 is available

### Getting Help
1. Check existing [TODO.md](../TODO.md) for known issues
2. Review error logs in the console
3. Run tests to isolate the problem: `make test`
4. Check the [README.md](../README.md) for usage examples
