"""
Repo Scanner - Main Application Entry Point

This file serves as an entry point for the Repo Scanner application,
delegating to the actual implementation in the scanner package.
"""

from scanner.app import app

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)