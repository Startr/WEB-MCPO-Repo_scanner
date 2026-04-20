# scanner/kanban.py — Generates an Obsidian KANBAN.canvas from TODO data.
#
# The canvas is a JSON Canvas 1.0 file (https://jsoncanvas.org/spec/1.0/).
# It gets regenerated every time a scan runs — the code is the source of
# truth, the board is just a view.
#
# Usage:
#   From scan hooks (app.py):  build_kanban(todo_md_files, todo_items)
#   From CLI:                  python -m scanner.kanban [/path/to/repo]

import hashlib
import json
import os
import re


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Reuse the same regex patterns proven in tools/sync_readme_todos.py
ITEM_RE = re.compile(r'^- \[[ x]\]')           # top-level checkbox line
NEST_RE = re.compile(r'^\s+- \[')               # indented child line
TAG_RE  = re.compile(r'\s+#[\w][\w-]*(?:\s+#[\w][\w-]*)*\s*$')  # trailing hashtags
CHECKED_RE = re.compile(r'^- \[x\]', re.IGNORECASE)  # completed checkbox

# Extract the keyword (TODO/FIXME/BUG/NOTE) from an inline comment
KEYWORD_RE = re.compile(r'(?:TODO|FIXME|BUG|NOTE)', re.IGNORECASE)

# Map TODO.md section headers to kanban columns.
# Matching is case-insensitive substring — "## High Priority" hits "high priority".
# Multiple aliases per column so authors can use whatever feels natural.
SECTION_MAP = {
    'in progress':      'in_progress',
    'doing':            'in_progress',
    'wip':              'in_progress',
    'high priority':    'in_progress',
    'medium priority':  'todo',
    'low priority':     'backlog',
    'backlog':          'backlog',
    'completed':        'done',
    'done':             'done',
    'tech debt':        'todo',
    'bugs':             'bugs',
    'bug':              'bugs',
}

# Map inline comment keywords to kanban columns.
# NOTE is intentionally absent — notes are observations, not work items.
KEYWORD_MAP = {
    'TODO':  'todo',
    'FIXME': 'in_progress',
    'BUG':   'bugs',
}

# Functional tag rules — tags that affect board behavior.
# Tags describe the kind of work.  Section headers and inline keywords
# determine which column a card lands in.  These two tags are exceptions:
#   #bug      → moves card to the Bugs column
#   #critical → elevates card to the top of its column
# No other tag affects placement.
TAG_RULES = {
    '#bug':      {'column': 'bugs'},
    '#critical': {'elevate': True},
}

# Column definitions — fixed order, left to right.
# color values are JSON Canvas 1.0 presets: 1=red 2=orange 3=yellow 4=green 5=cyan 6=purple
COLUMNS = [
    {'key': 'backlog',     'label': 'Backlog',     'color': '4'},   # green — good to go when you have time
    {'key': 'todo',        'label': 'TODO',         'color': None},  # no color — neutral work queue
    {'key': 'in_progress', 'label': 'In Progress',  'color': '5'},   # cyan/blue — like a hot fire
    {'key': 'bugs',        'label': 'Bugs',         'color': '1'},   # red — danger
    {'key': 'done',        'label': 'Done',         'color': '6'},   # purple — cool, parked
]

# Layout dimensions (pixels).  Obsidian renders these faithfully.
COL_WIDTH   = 300
COL_GAP     = 50
CARD_WIDTH  = 280
CARD_HEIGHT = 80
CARD_GAP    = 10
HEADER_PAD  = 60   # vertical space at top of column for the label
COL_PAD     = 10   # inner padding inside group node
MIN_COL_H   = 200  # minimum column height even if empty


# ---------------------------------------------------------------------------
# Data holder
# ---------------------------------------------------------------------------

class KanbanCard:
    """One card on the Kanban board.  Deliberately flat — no inheritance."""

    def __init__(self, text, source, column,
                 file_path=None, line_num=None, tags=None, children=None):
        self.text = text            # human-readable TODO text
        self.source = source        # 'todo_md' or 'inline'
        self.column = column        # key from COLUMNS
        self.file_path = file_path  # relative path (inline) or 'TODO.md'
        self.line_num = line_num    # line number in source file
        self.tags = tags or []      # hashtags like ['#brand', '#api']
        self.children = children or []  # child dicts: {text, checked, tags}
        self.elevated = False       # True if #critical tag → sort to top


# ---------------------------------------------------------------------------
# Parse TODO.md content into cards
# ---------------------------------------------------------------------------

def _strip_tags(text):
    """Remove trailing hashtags from a line, return (clean_text, [tags])."""
    match = TAG_RE.search(text)
    if match:
        tags = [t.strip() for t in match.group().split() if t.startswith('#')]
        return text[:match.start()].rstrip(), tags
    return text.rstrip(), []


def _strip_checkbox(text):
    """Remove the leading '- [ ] ' or '- [x] ' prefix from a line."""
    return re.sub(r'^-\s*\[[ x]\]\s*', '', text, flags=re.IGNORECASE)


def _section_to_column(section_name):
    """Map a TODO.md section header to a kanban column key."""
    lower = section_name.lower()
    for keyword, column in SECTION_MAP.items():
        if keyword in lower:
            return column
    # Anything not explicitly mapped goes to TODO — if someone wrote
    # a detailed section with sub-tasks, they intend to do the work.
    return 'todo'


def _apply_tag_rules(card):
    """Apply functional tag rules to a card.  Mutates card in place.

    #bug overrides column placement to Bugs.
    #critical elevates the card to the top of its column.
    """
    for tag in card.tags:
        rule = TAG_RULES.get(tag.lower())
        if rule:
            if 'column' in rule:
                card.column = rule['column']
            if rule.get('elevate'):
                card.elevated = True


def parse_todo_md(content, file_path='TODO.md'):
    """Parse TODO.md markdown content into a list of KanbanCards.

    Args:
      content:   raw markdown string
      file_path: relative path to the TODO.md file (for repos with
                 multiple TODO.md files in subdirectories)

    Rules:
      - ## headers set the current section (mapped to a column)
      - Top-level '- [ ]' lines become cards in the section's column
      - Top-level '- [x]' lines become cards in Done (checkbox overrides section)
      - Indented children become sub-bullets on the parent card
      - Hashtags are extracted and stored as metadata
      - Line numbers are tracked for write-back and blame
    """
    cards = []
    current_section = 'todo'  # default if no section header seen yet
    current_parent = None

    for line_idx, line in enumerate(content.splitlines(), start=1):
        stripped = line.rstrip()

        # Section headers — update column mapping
        if stripped.startswith('## '):
            section_text = stripped.lstrip('#').strip()
            current_section = _section_to_column(section_text)
            current_parent = None
            continue

        # Sub-section headers (###) — ignored for column mapping
        if stripped.startswith('#'):
            continue

        # Indented child item — append to parent card
        if NEST_RE.match(line):
            if current_parent is not None:
                raw = stripped.strip()
                checked = bool(CHECKED_RE.match(raw))
                child_text = _strip_checkbox(raw)
                child_text, child_tags = _strip_tags(child_text)
                current_parent.children.append({
                    'text': child_text,
                    'checked': checked,
                    'tags': child_tags,
                    'line_num': line_idx,
                })
            continue

        # Top-level checkbox item — new card
        if ITEM_RE.match(stripped):
            text = _strip_checkbox(stripped)
            text, tags = _strip_tags(text)

            # Checked items always go to Done, regardless of section
            is_done = bool(CHECKED_RE.match(stripped))
            column = 'done' if is_done else current_section

            card = KanbanCard(
                text=text,
                source='todo_md',
                column=column,
                file_path=file_path,
                line_num=line_idx,
                tags=tags,
            )
            _apply_tag_rules(card)
            cards.append(card)
            current_parent = card
            continue

        # Everything else (prose, HTML comments, blank lines) — skip

    return cards


# ---------------------------------------------------------------------------
# Convert inline TodoItems to cards
# ---------------------------------------------------------------------------

def inline_todo_to_card(todo_item):
    """Convert a TodoItem (from find_todos) to a KanbanCard.

    The keyword in the comment text determines the column:
      TODO → todo, FIXME → in_progress, BUG → bugs
    Returns None for NOTE comments — observations, not work items.
    """
    match = KEYWORD_RE.search(todo_item.todo_text)
    keyword = match.group().upper() if match else 'TODO'
    if keyword == 'NOTE':
        return None
    column = KEYWORD_MAP.get(keyword, 'todo')

    return KanbanCard(
        text=todo_item.todo_text,
        source='inline',
        column=column,
        file_path=todo_item.file_path,
        line_num=todo_item.line_num,
    )


# ---------------------------------------------------------------------------
# Generate JSON Canvas 1.0 from cards
# ---------------------------------------------------------------------------

def _card_id(card):
    """Deterministic ID so regeneration is idempotent.  Same input = same ID."""
    raw = f"{card.source}:{card.file_path}:{card.line_num}:{card.text}"
    return hashlib.md5(raw.encode()).hexdigest()[:16]


def _card_text(card):
    """Render a card's display text as Markdown for the canvas node."""
    lines = []

    if card.source == 'inline':
        # Inline cards show the raw comment + file location
        lines.append(card.text)
        lines.append(f'`{card.file_path}:{card.line_num}`')
    else:
        # TODO.md cards show cleaned-up title + GFM task list children + tags + location
        title = re.sub(r'\*{2,}', '', card.text).strip()
        lines.append(f'**{title}**')
        for child in card.children:
            mark = 'x' if child['checked'] else ' '
            tag_suffix = ' ' + ' '.join(child['tags']) if child['tags'] else ''
            lines.append(f'- [{mark}] {child["text"]}{tag_suffix}')
        # Blank line after the task list so Marked closes the <ul> before
        # rendering tags and location as their own <p> elements.
        if card.children and (card.tags or card.line_num):
            lines.append('')
        if card.tags:
            lines.append(' '.join(f'`{t}`' for t in card.tags))
        if card.line_num:
            lines.append(f'`{card.file_path}:L{card.line_num}`')

    return '\n'.join(lines)


def generate_canvas(cards):
    """Lay out cards into a JSON Canvas 1.0 spec dict.

    Returns a dict with 'nodes' and 'edges' keys, ready for json.dump.
    Columns are group nodes; cards are text nodes positioned inside them.
    """
    # Bucket cards by column
    buckets = {col['key']: [] for col in COLUMNS}
    for card in cards:
        bucket = buckets.get(card.column)
        if bucket is not None:
            bucket.append(card)

    # Sort each bucket: elevated (#critical) cards float to top
    for bucket in buckets.values():
        bucket.sort(key=lambda c: (not c.elevated,))

    nodes = []

    for col_idx, col in enumerate(COLUMNS):
        col_x = col_idx * (COL_WIDTH + COL_GAP)
        col_cards = buckets[col['key']]
        col_height = max(
            MIN_COL_H,
            HEADER_PAD + len(col_cards) * (CARD_HEIGHT + CARD_GAP) + COL_PAD
        )

        # Group node (column container) — rendered below cards (lower z-index)
        group_id = f'col-{col["key"]}'
        group_node = {
            'id': group_id,
            'type': 'group',
            'x': col_x,
            'y': 0,
            'width': COL_WIDTH,
            'height': col_height,
            'label': col['label'],
        }
        if col['color']:
            group_node['color'] = col['color']
        nodes.append(group_node)

        # Card nodes — stacked vertically inside the column
        for card_idx, card in enumerate(col_cards):
            card_x = col_x + COL_PAD
            card_y = HEADER_PAD + card_idx * (CARD_HEIGHT + CARD_GAP)
            card_node = {
                'id': _card_id(card),
                'type': 'text',
                'text': _card_text(card),
                'x': card_x,
                'y': card_y,
                'width': CARD_WIDTH,
                'height': CARD_HEIGHT,
                # Extra metadata for web renderers (ignored by Obsidian)
                'file_path': card.file_path,
                'source': card.source,
                'tags': card.tags,
            }
            if card.line_num:
                card_node['line_num'] = card.line_num
            if card.children:
                card_node['children'] = card.children
            nodes.append(card_node)

    return {'nodes': nodes, 'edges': []}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_kanban(todo_md_files, todo_items):
    """Pure function: build a kanban canvas from scan results.

    Args:
        todo_md_files: list of {'file_path': str, 'content': str|None}
                       (from find_todo_files)
        todo_items:    list of TodoItem objects (from find_todos)

    Returns:
        dict — JSON Canvas 1.0 spec, ready for json.dump or API response.
    """
    cards = []

    # 1. Parse TODO.md files into cards
    for todo_file in (todo_md_files or []):
        if todo_file.get('content'):
            cards.extend(parse_todo_md(todo_file['content'], file_path=todo_file.get('file_path', 'TODO.md')))

    # 2. Convert inline TODO/FIXME/BUG comments into cards (NOTEs skipped)
    for item in (todo_items or []):
        card = inline_todo_to_card(item)
        if card is not None:
            cards.append(card)

    # 3. Generate the canvas layout
    return generate_canvas(cards)


def write_canvas(repo_path, canvas):
    """Atomic write — Obsidian never sees a partial file.

    Writes to KANBAN.canvas.tmp first, then replaces the real file.
    Returns the path written.
    """
    target = os.path.join(repo_path, 'KANBAN.canvas')
    tmp = target + '.tmp'
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(canvas, f, indent=2, sort_keys=True)
    os.replace(tmp, target)
    return target


# ---------------------------------------------------------------------------
# CLI entry point:  python -m scanner.kanban [/path/to/repo]
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    import sys

    repo_path = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else os.getcwd())

    # Deferred imports — only needed for standalone CLI mode
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from scanner.app import find_todos, find_todo_files, load_exclusions

    exclusions = load_exclusions(repo_path)
    todo_md_files = find_todo_files(repo_path, exclusions=exclusions)
    todo_items = list(find_todos(repo_path, exclusions=exclusions))

    canvas = build_kanban(todo_md_files, todo_items)
    path = write_canvas(repo_path, canvas)

    card_count = sum(1 for n in canvas['nodes'] if n['type'] == 'text')
    col_count = sum(1 for n in canvas['nodes'] if n['type'] == 'group')
    print(f'Wrote {card_count} cards across {col_count} columns to {path}')
