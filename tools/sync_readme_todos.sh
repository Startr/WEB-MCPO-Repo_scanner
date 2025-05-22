#!/bin/bash

# This script syncs content from TODO.md to a specified section in README.md.
# It's designed to be called by the Makefile.

set -e # Exit immediately if a command exits with a non-zero status.

# Relative paths from the project root (where Makefile is located)
TODO_FILE="TODO.md"
README_FILE="README.md"
TEMP_README_FILE="README.md.tmp"

# Markers in README.md that define the section to be replaced
BEGIN_MARKER="<!-- BEGIN PROJECT TODOS -->"
END_MARKER="<!-- END PROJECT TODOS -->"
GENERATED_COMMENT="<!-- This section is automatically generated from TODO.md. Edits here will be overwritten. -->"

# The specific comment line in TODO.md from which to start copying content.
# Ensure this pattern exactly matches the line in TODO.md.
TODO_START_MARKER_PATTERN="<!-- All content below this line has been revised for clarity, conciseness, vigorous language, tagging, and DRY principles. Uncompleted items from the original 'Completed' section have been moved to 'Medium Priority'. -->"

# Extract relevant content from TODO.md starting from the marker line
# The sed command copies from the line matching TODO_START_MARKER_PATTERN to the end of the file.
TODO_CONTENT=$(sed -n "/^${TODO_START_MARKER_PATTERN}\$/,\$p" "${TODO_FILE}")

# Check if TODO_CONTENT was successfully extracted
if [ -z "$TODO_CONTENT" ]; then
    echo "Error: Could not extract content from '$TODO_FILE' using the marker:" >&2
    echo "Marker pattern: /^${TODO_START_MARKER_PATTERN}\$/" >&2
    exit 1
fi

# Use awk to replace the content between BEGIN_MARKER and END_MARKER in README_FILE
awk -v begin_marker="$BEGIN_MARKER" \\
    -v end_marker="$END_MARKER" \\
    -v generated_comment="$GENERATED_COMMENT" \\
    -v todo_data="$TODO_CONTENT" \\
    '
    BEGIN { printing_outside_markers = 1 } # By default, print lines from README.md
    $0 ~ begin_marker {
        print $0; # Print the begin_marker line itself
        print generated_comment; # Print the auto-generation notice
        printf "%s", todo_data; # Print the extracted TODO_CONTENT. printf avoids adding an extra newline if todo_data already has one.
        printing_outside_markers = 0; # Stop printing original README lines until end_marker is found
        next; # Skip to the next line of README.md
    }
    $0 ~ end_marker {
        printing_outside_markers = 1; # Resume printing original README lines
        # The end_marker line itself will be printed by the block below
    }
    printing_outside_markers { print $0 } # Print lines that are outside the markers or after the end_marker
    ' "${README_FILE}" > "${TEMP_README_FILE}"

# Check if awk command was successful (basic check)
if [ $? -eq 0 ] && [ -s "${TEMP_README_FILE}" ]; then
    mv "${TEMP_README_FILE}" "${README_FILE}"
    echo "Successfully synced '$TODO_FILE' to '$README_FILE'."
else
    echo "Error: awk processing failed or produced an empty temp file. '$README_FILE' not updated." >&2
    rm -f "${TEMP_README_FILE}" # Clean up temp file on error
    exit 1
fi

# Make the script executable from the Makefile if needed, or ensure it has execute permissions.
# chmod +x tools/sync_readme_todos.sh
