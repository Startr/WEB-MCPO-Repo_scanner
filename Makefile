SHELL := /bin/bash

.PHONY: sync-todos

sync-todos:
	@echo "Syncing TODO.md to README.md..."
	@# Extract the content from TODO.md
	@TODO_CONTENT=$$(sed -n '/<!-- All content below this line has been revised for clarity, conciseness, vigorous language, tagging, and DRY principles. Uncompleted items from the original ''''''Completed'''''' section have been moved to ''''''Medium Priority''''''. -->/,$ p' TODO.md)
	@# Prepare the start and end markers for sed
	@START_MARKER="<!-- BEGIN PROJECT TODOS -->"
	@END_MARKER="<!-- END PROJECT TODOS -->"
	@# Escape special characters in TODO_CONTENT for sed
	@# First, escape backslashes, then ampersands, then forward slashes, then newlines
	@ESCAPED_TODO_CONTENT=$$(echo "$$TODO_CONTENT" | sed -e 's/\\/\\\\/g' -e 's/&/\\&/g' -e 's/\//\\\//g' | awk 'BEGIN{ORS="\\n"} {print}')
	@# Use awk to replace the content between markers in README.md
	@awk -v start="$$START_MARKER" -v end="$$END_MARKER" -v content="$$ESCAPED_TODO_CONTENT" \
	'BEGIN {printing=1} \
	$$0 ~ start {print; print "<!-- This section is automatically generated from TODO.md. Edits here will be overwritten. -->"; print content; printing=0} \
	$$0 ~ end {printing=1} \
	printing {print}' README.md > README.md.tmp && mv README.md.tmp README.md
	@echo "Sync complete. README.md updated with content from TODO.md."

# Note on two-way sync:
# True two-way synchronization is complex to implement reliably in a Makefile due to:
# 1. Timestamp comparisons: Make typically relies on file modification times. If README.md is edited manually
#    in the TODO section, its timestamp might become newer than TODO.md, leading to potential data loss
#    if not handled carefully.
# 2. Conflict resolution: If both files are edited in the TODO section simultaneously, a Makefile rule
#    cannot easily resolve these conflicts.
# 3. Parsing structured content: Markdown is not as rigidly structured as data formats like JSON or XML,
#    making it harder to parse and merge changes bidirectionally without errors.
#
# For these reasons, this Makefile implements a one-way sync from TODO.md to README.md.
# The README.md section is clearly marked as auto-generated to discourage direct edits there.
# If you need two-way sync, consider a dedicated script or tool that can better handle content merging and conflict resolution.
