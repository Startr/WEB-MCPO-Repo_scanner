#!/usr/bin/env python3
# Summarises TODO.md into the marked section of README.md.
# Called by: make sync_todos
#
# Replaces everything between:
#   <!-- BEGIN PROJECT TODOS -->
#   <!-- END PROJECT TODOS -->
# in README.md with a clean summary: section headers + top-level checklist
# items only. Nested sub-items, prose paragraphs, and #tags are omitted.

import re
import sys

TODO_FILE  = "TODO.md"
README_FILE = "README.md"

BEGIN_MARKER      = "<!-- BEGIN PROJECT TODOS -->"
END_MARKER        = "<!-- END PROJECT TODOS -->"
GENERATED_COMMENT = "<!-- This section is automatically generated from TODO.md. Edits here will be overwritten. -->"
TODO_START_MARKER = "<!-- All content below this line has been revised"

TAG_RE  = re.compile(r'\s+#[\w][\w-]*(?:\s+#[\w][\w-]*)*\s*$')
ITEM_RE = re.compile(r'^- \[[ x]\]')
NEST_RE = re.compile(r'^\s+- \[')


def strip_tags(text: str) -> str:
    return TAG_RE.sub('', text).rstrip()


def summarise(lines: list[str]) -> str:
    """Return a summarised version of TODO.md lines suitable for a README."""
    out = []
    prev_blank = False

    for raw in lines:
        line = raw.rstrip()

        # Section headers — keep, strip tags
        if line.startswith('#'):
            out.append(strip_tags(line))
            prev_blank = False
            continue

        # Top-level checklist items — keep, strip tags
        if ITEM_RE.match(line):
            out.append(strip_tags(line))
            prev_blank = False
            continue

        # Indented / nested items — skip
        if NEST_RE.match(line):
            continue

        # Blank lines — keep at most one in a row
        if line == '':
            if not prev_blank:
                out.append('')
            prev_blank = True
            continue

        # Everything else (prose, HTML comments, etc.) — skip

    # Trim leading/trailing blank lines
    while out and out[0] == '':
        out.pop(0)
    while out and out[-1] == '':
        out.pop()

    return '\n'.join(out) + '\n'


# --- Read TODO.md ---
with open(TODO_FILE, encoding='utf-8') as f:
    todo_lines = f.readlines()

start_idx = None
for i, line in enumerate(todo_lines):
    if line.strip().startswith(TODO_START_MARKER):
        start_idx = i + 1
        break

if start_idx is None:
    sys.exit(f'Error: start marker not found in {TODO_FILE}')

summary = summarise(todo_lines[start_idx:])

# --- Splice into README.md ---
with open(README_FILE, encoding='utf-8') as f:
    readme_lines = f.readlines()

out = []
inside  = False
inserted = False
for line in readme_lines:
    stripped = line.strip()
    if stripped == BEGIN_MARKER:
        out.append(line)
        out.append(GENERATED_COMMENT + '\n')
        out.append(summary)
        inside   = True
        inserted = True
        continue
    if stripped == END_MARKER:
        inside = False
    if not inside:
        out.append(line)

if not inserted:
    sys.exit(f"Error: '{BEGIN_MARKER}' not found in {README_FILE}")

with open(README_FILE, 'w', encoding='utf-8') as f:
    f.writelines(out)

print(f'Successfully summarised {TODO_FILE} → {README_FILE}.')
