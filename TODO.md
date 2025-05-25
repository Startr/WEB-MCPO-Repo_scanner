# TODO List for Repo Scanner

<!-- All content below this line has been revised for clarity, conciseness, vigorous language, tagging, and DRY principles. Uncompleted items from the original '''Completed''' section have been moved to '''Medium Priority'''. -->

## High Priority
- [x] Fix the MAJOR issue with existing repositories not working. #core #bug
- [x] Implement a robust error handling mechanism for the scanner. #core #error-handling
- [x] Broaden TODO pattern recognition (e.g., FIXME, BUG, NOTE). #core #parser
- [x] DRY Makefile targets. (Allow passing args to targets?) #development #testing
- [x] Enable streaming of API results for improved responsiveness. #api #performance
- [ ] Migrate Python files and dependencies to subdirectory structure. #development #structure
    - [x] Create scanner subdirectory. #development #structure
    - [x] Implement __init__.py for the subdirectory. #development #structure
    - [x] Move error_handling.py to scanner subdirectory. #development #structure
    - [x] Update imports in app.py. #development #structure
    - [x] Move remaining Python files (test files) to scanner/tests. #development #structure
    - [x] Move Pipfile and Pipfile.lock to scanner subdirectory. #development #structure
    - [ ] Test and update the Makefile accordingly. #development #testing



## Medium Priority
- [ ] Add detection of TODO.md and TODO.txt files. #feature #core (no capitalization needed)
- [ ] Implement a user-friendly web interface for displaying TODO files. #ux #frontend
- [ ] Include the option to look at the TODO files with our MCPo Api. #api #integration
- [ ] Add summary from repo readme files to the web interface. (optioanlly the top 20lines) #ux #frontend
- [ ] Implement a search feature for TODO comments. #search #ux
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
- [ ] Implement priority inference from TODO comments. #core #parser
- [ ] Design a plugin system to extend scanner functionality. #architecture #extensibility
- [ ] Facilitate integration with task managers (Jira, Asana, Trello). #integration #external
- [ ] Create a command-line interface (CLI) for versatile use. #cli #accessibility
- [ ] Improve visibility of scrollable local repositories list on the main page. #ux #frontend

## Completed
- [x] Implement comprehensive error handling with custom exceptions, retries, and recovery strategies. #core #error-handling
- [x] Create testing infrastructure with unit and integration tests. #core #testing
- [x] Add Makefile targets and test runner for easy test execution. #development #testing
- [x] Honor .gitignore patterns during repository scans. #core
- [x] Stream scan results efficiently in the web UI. #ux #frontend
- [x] Ensure proper HTML escaping for multi-line display. #security #rendering
- [x] Broaden TODO pattern recognition to include FIXME, BUG, and NOTE in various comment formats. #core #parser
