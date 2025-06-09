# Contributor Guide

Welcome to the TODO Scanner project! This guide will help you get started contributing to our codebase.

## Getting Started

### Prerequisites
- Python 3.12 or higher
- Git
- pipenv (install with `pip install pipenv`)

### Development Setup

1. **Fork and Clone**
   ```bash
   git clone https://github.com/Startr/WEB-MCPO-Repo_scanner.git
   cd repo_scanner
   ```

2. **Set up Development Environment**
   ```bash
   cd scanner
   pipenv install --dev
   pipenv shell
   ```

3. **Verify Setup**
   ```bash
   make test
   make run
   ```

4. **Visit Application**
   Open http://localhost:5000 to verify the application is running

## Development Workflow

We follow the **Plan-Document-Execute-Verify** cycle outlined in [CONVENTION.instructions.md](../CONVENTION.instructions.md).

### Before Starting Work

**ALWAYS** add your task to [TODO.md](../TODO.md) first:

```markdown
## [Category] TODOs
- [ ] **[Your Task Name]**: Brief description #relevant #tags
  - [ ] Subtask 1
  - [ ] Subtask 2
  - [ ] Write tests
  - [ ] Update documentation
```

### Making Changes

1. **Create a Branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Follow Code Standards** (see below)

3. **Write Tests**
   - Add unit tests in `scanner/tests/`
   - Test your changes: `make test`

4. **Update Documentation**
   - Update docstrings
   - Update relevant markdown files
   - Update API documentation if needed

5. **Commit Changes**
   ```bash
   git add .
   git commit -m "feat: add your feature description"
   ```

## Code Standards

### Python Style Guide

We follow PEP 8 with these specific guidelines:

#### Imports
```python
# Standard library imports first
import os
import sys
from typing import List, Dict, Optional

# Third-party imports
import flask
from git import Repo

# Local imports
from .error_handling import safe_operation, RepositoryError
```

#### Function Documentation
```python
def scan_repository(repo_url: str, patterns: Optional[List[str]] = None) -> Dict:
    """
    Scan a repository for TODO comments and return structured results.
    
    Args:
        repo_url: URL of the git repository to scan
        patterns: Optional list of patterns to search for (defaults to TODO, FIXME, BUG, NOTE)
        
    Returns:
        Dictionary containing repository info and found TODOs
        
    Raises:
        RepositoryError: If repository cannot be cloned or accessed
        ValueError: If repo_url is invalid or empty
        
    Example:
        >>> results = scan_repository("https://github.com/user/repo.git")
        >>> print(f"Found {len(results['todos'])} TODOs")
    """
    # Implementation here
```

#### Class Documentation
```python
class TodoItem:
    """
    Represents a TODO item found in a source code file.
    
    Attributes:
        file_path: Relative path to the file containing the TODO
        line_num: Line number where the TODO was found (1-indexed)
        todo_text: The actual TODO comment text
        next_line: Optional context line following the TODO
        
    Example:
        >>> todo = TodoItem("src/main.py", 42, "TODO: Fix this bug", "def broken_function():")
        >>> print(f"TODO at {todo.file_path}:{todo.line_num}")
    """
    
    def __init__(self, file_path: str, line_num: int, todo_text: str, next_line: Optional[str] = None):
        self.file_path = file_path
        self.line_num = line_num
        self.todo_text = todo_text
        self.next_line = next_line
```

#### Error Handling
Always use our error handling decorators:

```python
from .error_handling import safe_operation, mpco_response

@safe_operation
def risky_operation():
    """Operation that might fail."""
    # This will automatically handle exceptions and provide user-friendly errors
    pass

@app.route('/api/mpco/endpoint', methods=['POST'])
@mpco_response
def api_endpoint():
    """API endpoint with standardized response format."""
    # This will format responses according to MCP standards
    return {"result": "success"}
```

### HTML/CSS Standards

#### Template Structure
```html
{% extends "base.html" %}

{% block title %}Page Title{% endblock %}

{% block content %}
<main class="container">
    <section class="section">
        <h1>Semantic Heading</h1>
        <!-- Content here -->
    </section>
</main>
{% endblock %}

{% block scripts %}
<script>
    // Page-specific JavaScript
</script>
{% endblock %}
```

#### CSS Organization
- Use semantic class names: `.todo-list`, `.scan-results`
- Follow BEM methodology where appropriate: `.block__element--modifier`
- Use CSS custom properties for theming: `var(--primary-color)`
- Mobile-first responsive design

### Testing Standards

#### Unit Tests
```python
import pytest
from scanner.app import TodoItem, find_todos

class TestTodoItem:
    """Test TodoItem class functionality."""
    
    def test_todo_item_creation(self):
        """Test creating a TodoItem with all parameters."""
        todo = TodoItem("test.py", 1, "TODO: Test", "next line")
        assert todo.file_path == "test.py"
        assert todo.line_num == 1
        assert todo.todo_text == "TODO: Test"
        assert todo.next_line == "next line"
    
    def test_todo_item_without_next_line(self):
        """Test creating a TodoItem without next_line parameter."""
        todo = TodoItem("test.py", 1, "TODO: Test")
        assert todo.next_line is None

class TestFindTodos:
    """Test TODO finding functionality."""
    
    def test_find_todos_in_file(self, tmp_path):
        """Test finding TODOs in a sample file."""
        # Create temporary file with TODOs
        test_file = tmp_path / "test.py"
        test_file.write_text("# TODO: This is a test\nprint('hello')")
        
        todos = find_todos(str(tmp_path))
        assert len(todos) == 1
        assert "TODO: This is a test" in todos[0].todo_text
```

#### Integration Tests
```python
def test_api_scan_repository(client):
    """Test the scan repository API endpoint."""
    response = client.post('/api/mpco/scan_repository', 
                          json={'repo_url': 'https://github.com/test/repo.git'})
    assert response.status_code == 200
    data = response.get_json()
    assert 'content' in data
```

## Pull Request Process

### Before Submitting

1. **Update TODO.md**
   - Mark completed items as done: `- [x]`
   - Add any new tasks discovered during development

2. **Run Full Test Suite**
   ```bash
   make test
   make lint  # If linting is available
   ```

3. **Update Documentation**
   - API changes: Update `docs/API_REFERENCE.md`
   - Architecture changes: Update `docs/ARCHITECTURE.md`
   - New features: Update `README.md`

4. **Self-Review**
   - Check that all TODO items in your branch are completed
   - Verify code follows style guidelines
   - Ensure all tests pass

### Pull Request Template

When creating a pull request, include:

```markdown
## Description
Brief description of what this PR accomplishes.

## Changes Made
- [ ] Feature/fix implemented
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] TODO.md updated

## Testing
- [ ] All existing tests pass
- [ ] New tests added for new functionality
- [ ] Manual testing completed

## TODO Items Completed
Link to the TODO items this PR addresses:
- Closes #123 (if using GitHub issues)
- Completes TODO item: "Implement XYZ feature"

## Screenshots (if applicable)
Include screenshots for UI changes.
```

### Review Process

1. **Automated Checks**
   - Tests must pass
   - Code style checks (if implemented)

2. **Code Review**
   - At least one maintainer review required
   - Address all feedback before merging

3. **Final Verification**
   - Verify TODO.md is updated
   - Confirm documentation is current
   - Check that the change follows our conventions

## Commit Message Guidelines

We use Conventional Commits:

- `feat: add new TODO pattern recognition`
- `fix: resolve repository cloning timeout`
- `docs: update API documentation`
- `test: add unit tests for error handling`
- `refactor: simplify scanner logic`
- `style: fix PEP 8 violations`
- `chore: update dependencies`

### Commit Message Format
```
type(scope): description

Optional longer description explaining the change.

Closes #123
```

## Issue Reporting

### Bug Reports
Include:
- Steps to reproduce
- Expected vs actual behavior
- Environment details (Python version, OS)
- Error messages and stack traces
- Relevant TODO.md items if applicable

### Feature Requests
Include:
- Clear description of desired functionality
- Use cases and benefits
- Proposed implementation approach
- Willingness to contribute the implementation

## Getting Help

### Resources
- [Development Workflow](DEVELOPMENT_WORKFLOW.md)
- [Architecture Overview](ARCHITECTURE.md)
- [API Reference](API_REFERENCE.md)
- [Project README](../README.md)

### Communication
- Check existing [TODO.md](../TODO.md) for known issues
- Review closed pull requests for similar changes
- Open an issue for questions or clarifications

### Common Development Tasks

#### Running Tests
```bash
# Run all tests
make test

# Run specific test file
python -m pytest scanner/tests/test_error_handling.py

# Run with coverage
python -m pytest --cov=scanner
```

#### Adding New Dependencies
```bash
# Add runtime dependency
pipenv install package_name

# Add development dependency  
pipenv install --dev package_name

# Update lock file
pipenv lock
```

#### Database Migrations (Future)
```bash
# When database is added
flask db init
flask db migrate -m "Description"
flask db upgrade
```

## Code of Conduct

- Be respectful and inclusive
- Follow the established conventions
- Help maintain code quality
- Document your changes thoroughly
- Test your code before submitting

Thank you for contributing to TODO Scanner! 🚀
