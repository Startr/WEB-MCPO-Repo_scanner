# TODO Scanner

[![GitHub](https://img.shields.io/badge/View%20on-GitHub-brightgreen)](https://github.com/Startr/WEB-MCPO-Repo_scanner)

**A straightforward and efficient tool designed to meticulously scan your Git repositories for TODO comments, bringing them to your attention so nothing gets overlooked.**

The code is open. The project evolves. Get involved.

![Sage_repo-TODOs.gif](Sage_repo-TODOs.gif)

## What It Does

In the fast-paced world of software development, it's easy for small tasks and reminders, often marked as TODOs within the codebase, to get lost or forgotten. TODO Scanner addresses this by:

*   **Cloning Repositories:** Provide a Git repository URL, and the scanner will clone it locally.
*   **Comprehensive Scanning:** It meticulously searches through all text files within the repository.
*   **Pattern Recognition:** Identifies common TODO patterns (e.g., `TODO:`, `# TODO`, `// TODO`) in comments.
*   **Clear Reporting:** Presents the found TODO items in a clean, user-friendly web interface, showing the file path, line number, and the TODO text itself.
*   **Streaming Results:** Offers a real-time streaming view of TODOs as they are found during a scan.
*   **Local Repository Management:** Keeps track of previously scanned repositories for quick re-scans and updates.

## Why It Matters

Developers often leave notes for future improvements, bug fixes, or pending tasks directly in the code. While convenient, these TODOs can accumulate and become difficult to track across a growing codebase. This tool brings visibility to these hidden tasks, helping teams:

*   **Maintain Code Quality:** By ensuring that reminders for refactoring or fixes are not forgotten.
*   **Improve Project Management:** By providing a clear overview of pending micro-tasks.
*   **Enhance Collaboration:** By making it easier for team members to see and address outstanding items.

## Key Features

*   **Web Interface:** Intuitive and easy-to-use UI for scanning and viewing results.
*   **API Access:** A simple REST API for programmatic scanning and integration into CI/CD pipelines or other tools.
*   **Model Context Protocol (MCP) Compliant:** Implements the MCP standard with a dynamic OpenAPI specification, allowing AI assistants and other services to interact with it seamlessly.
*   **Cloudflare Tunnel Integration:** Includes a script to easily expose the local scanner via a public Cloudflare Quick Tunnel for demos or remote team access.
*   **.gitignore Aware:** Respects `.gitignore` rules to avoid scanning irrelevant files.
*   **Efficient Streaming:** Results can be streamed in real-time, providing immediate feedback on large repositories.

## How It Works

1.  **Input:** Provide a Git repository URL via the web interface or API.
2.  **Clone:** The application clones the repository into a local `repositories` directory.
3.  **Scan:** It traverses the repository, reading text files and looking for predefined TODO patterns.
4.  **Display/Return:** TODOs are displayed in the web UI or returned as JSON via the API.

## Installation

Ensure you have Python 3.x and Git installed.

```bash
git clone https://github.com/Startr/WEB-MCPO-Repo_scanner.git # Or your fork
cd repo_scanner
pip install -r requirements.txt # Assuming requirements.txt is present or use Pipfile
# If using Pipfile:
# pip install pipenv
# pipenv install
# pipenv shell
```
*(Note: The original README mentioned `requirements.txt`. If you are primarily using `Pipfile`, you might want to adjust these instructions or ensure `requirements.txt` is kept up-to-date via `pipenv lock -r > requirements.txt`)*

## Usage

### Web Interface

Start the Flask development server:

```bash
python app.py
```
Or, if you used `pipenv`:
```bash
pipenv run python app.py
```

Navigate to `http://localhost:5000` (or the port specified) in your web browser.
*   Enter a Git repository URL to scan.
*   View results, stream scans, or manage previously scanned local repositories.

### Cloudflare Quick Tunnels

To temporarily share your local scanner instance:

```bash
./run_with_cloudflared.sh
```
This script will start the application and create a Cloudflare tunnel, providing a public URL. The tunnel closes when the script is stopped.

### API Endpoints

The scanner provides a RESTful API. Key endpoints include:

*   **Scan Repository:**
    ```bash
    curl -X POST http://localhost:5000/api/mpco/scan_repository \
      -H "Content-Type: application/json" \
      -d '{"repo_url": "https://github.com/username/repository.git"}'
    ```
*   **List Local Repositories:**
    ```bash
    curl -X GET http://localhost:5000/api/mpco/list_repositories
    ```
*   **Pull Repository Updates:**
    ```bash
    curl -X POST http://localhost:5000/api/mpco/pull_repository \
      -H "Content-Type: application/json" \
      -d '{"repo_name": "repository_name_from_list"}'
    ```

#### Example API Output (Scan Repository)

```json
{
  "repo_url": "https://github.com/username/repository.git",
  "repo_name": "repository",
  "todo_count": 42,
  "todos": [
    {
      "file_path": "src/main.py",
      "line_num": 24,
      "todo_text": "# TODO: Fix this hack when we have time",
      "next_line": "def temporary_solution():"
    }
    // ... more TODOs
  ],
  "web_url": "http://localhost:5000/scan/https://github.com/username/repository.git"
}
```

## Model Context Protocol (MCP) & OpenAPI

This tool adheres to the Model Context Protocol, making it discoverable and usable by AI agents and other MCP-compatible services.

*   **Manifest:** `GET /api/mpco/manifest`
    *   Provides metadata about the tool for service discovery.
*   **OpenAPI Specification:** `GET /api/mpco/openapi.json`
    *   Offers a dynamically generated OpenAPI 3.0.x specification of the API, ensuring that the documentation always matches the current API capabilities.

## Project TODOs

This project, while dedicated to finding TODOs, has its own list of desired enhancements and features. Contributions are welcome!

<!-- BEGIN PROJECT TODOS -->
<!-- This section is automatically generated from TODO.md. Edits here will be overwritten. -->
## High Priority
- [ ] Broaden TODO pattern recognition (e.g., FIXME, BUG, NOTE). #core #parser
- [ ] Implement priority inference from TODO comments. #core #parser
- [ ] Enable streaming of API results for improved responsiveness. #api #performance

## Medium Priority
- [ ] Add detection for language-specific comment syntax. #core #parser #enhancement
- [ ] Develop a dashboard to visualize TODO metrics across projects. #reporting #ux
- [ ] Offer report downloads in multiple formats (CSV, JSON, PDF). #reporting #feature
- [ ] Integrate with GitHub webhooks for automated repository scanning. #integration #automation
- [ ] Enhance TODO file processing: #feature #core
    - [ ] Recognize diverse TODO filenames (e.g., TODO.md, todo.txt). #detection
    - [ ] Scan TODO files located in the project root directory. #discovery
    - [ ] Extend scanning to TODO files within subdirectories. #discovery
    - [ ] Display content from identified TODO files. #rendering #ux

## Low Priority
- [ ] Introduce user authentication for secure access. #security #auth
- [ ] Design a plugin system to extend scanner functionality. #architecture #extensibility
- [ ] Facilitate integration with task managers (Jira, Asana, Trello). #integration #external
- [ ] Create a command-line interface (CLI) for versatile use. #cli #accessibility
- [ ] Improve visibility of scrollable local repositories list on the main page. #ux #frontend

## Completed
- [x] Honor .gitignore patterns during repository scans.
- [x] Stream scan results efficiently in the web UI.
- [x] Ensure proper HTML escaping for multi-line display.
<!-- END PROJECT TODOS -->

## License

Copyright © 2025 Startr LLC.

Released under the GNU Affero General Public License v3.0 (AGPL-3.0).

Use it. Share it. Make it better. But keep it open. The full license text is available in the `LICENSE` file.

## Contribution

Contributions are highly encouraged! If you have an idea for improvement or a bug fix, please:

1.  Fork the repository.
2.  Create a new branch for your feature or fix.
3.  Make your changes.
4.  Submit a pull request with a clear description of your changes.

Let's work together to make this tool even better and help keep our codebases clean and manageable!

