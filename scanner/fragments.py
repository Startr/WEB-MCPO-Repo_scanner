"""Server-rendered HTML fragments — the single source of truth for what a
card, TODO item, or board looks like.

The browser receives these fragments over SSE and morphs them in with
idiomorph. It never builds board/card DOM from JSON.
"""

import hashlib
import re

from flask import render_template
from markupsafe import Markup, escape

# markdown-it-py matches the GFM semantics of the old client-side marked
# renderer (lists interrupting paragraphs, 2-space task-list nesting)
try:
    from markdown_it import MarkdownIt
    from mdit_py_plugins.tasklists import tasklists_plugin
    _MD = MarkdownIt('commonmark').enable(['table', 'strikethrough']).use(tasklists_plugin)
except ImportError:  # stripped-down builds — degrade to <pre>
    _MD = None

# Matches the client-side highlightTodo() this module replaces
_HIGHLIGHT_RE = re.compile(r'(#+\s*TODO|//\s*TODO|TODO:)', re.IGNORECASE)
# Matches the parseMd() list-width shim from the old client renderer
_LIST_STYLE_RE = re.compile(r'<(ul|ol)(\s|>)')
# Trailing `file:line` / `file:L42` code line appended by kanban._card_text —
# stripped so the template can render the location as a real editor link
_LOCATION_LINE_RE = re.compile(r'`[^`\n]+:L?\d+`\s*$')

_COLOR_CLASSES = {'1', '2', '3', '4', '5', '6'}

# Task-list checkbox write-back: each rendered checkbox carries the file,
# line number, and a hash of that line so /api/todo_toggle can verify the
# line is still what the viewer saw before flipping it.
_TASK_LINE_RE = re.compile(r'^\s*[-*+] \[( |x|X)\] ')
_CHECKBOX_INPUT_RE = re.compile(r'<input class="task-list-item-checkbox"[^>]*>')


def _line_hash(raw_line):
    return hashlib.md5(raw_line.rstrip().encode()).hexdigest()[:8]


def _annotate_inputs(html, targets):
    """Stamp data-td-* attrs onto rendered checkboxes, in document order.
    targets: iterable of (file_path, line_num, raw_line) — None entries skip."""
    it = iter(targets)

    def repl(m):
        try:
            target = next(it)
        except StopIteration:
            return m.group(0)
        if not target:
            return m.group(0)
        file_path, line_num, raw = target
        return (m.group(0)[:-1]
                + ' data-td-file="%s" data-td-line="%d" data-td-hash="%s">'
                % (escape(file_path), line_num, _line_hash(raw)))

    return Markup(_CHECKBOX_INPUT_RE.sub(repl, html))


def _task_lines(content):
    """(line_num, raw_line) for every task-list line, skipping fenced code."""
    result = []
    in_fence = False
    for i, line in enumerate(content.splitlines(), start=1):
        stripped = line.lstrip()
        if stripped.startswith('```') or stripped.startswith('~~~'):
            in_fence = not in_fence
            continue
        if not in_fence and _TASK_LINE_RE.match(line):
            result.append((i, line))
    return result


def render_markdown(text):
    """Markdown → safe HTML, matching the old client-side marked output."""
    if not text:
        return Markup('')
    if _MD is None:
        return Markup('<pre>%s</pre>' % escape(text))
    html = _MD.render(text)
    html = _LIST_STYLE_RE.sub(r'<\1 style="--w: max-content;"\2', html)
    return Markup(html)


def highlight_todo(text):
    """Escape raw comment text and wrap TODO markers in highlight spans."""
    escaped = str(escape(text or ''))
    return Markup(_HIGHLIGHT_RE.sub(r'<span class="highlight">\1</span>', escaped))


def _short_id(*parts):
    raw = ':'.join(str(p) for p in parts)
    return hashlib.md5(raw.encode()).hexdigest()[:12]


def canvas_to_columns(canvas, blame=None, md_sources=None):
    """Assign JSON Canvas cards to their columns — mirrors the layout
    contract in kanban.generate_canvas (x-range containment, y order).

    md_sources: {file_path: content} of the scanned TODO files — used to
    stamp write-back attrs on card checkboxes (children carry line numbers;
    the hash comes from the real source line)."""
    if not canvas or not canvas.get('nodes'):
        return []
    blame = blame or {}
    md_sources = md_sources or {}
    groups = sorted((n for n in canvas['nodes'] if n.get('type') == 'group'),
                    key=lambda g: g['x'])
    cards = [n for n in canvas['nodes'] if n.get('type') == 'text']

    columns = []
    for g in groups:
        in_col = sorted((c for c in cards
                         if g['x'] <= c['x'] < g['x'] + g['width']),
                        key=lambda c: c['y'])
        col_cards = []
        for c in in_col:
            file_path = c.get('file_path')
            line_num = c.get('line_num')
            text = c.get('text') or ''
            if file_path and line_num:
                # Location renders as its own element with an editor link
                text = _LOCATION_LINE_RE.sub('', text).rstrip()
            author = blame.get(f'{file_path}:{line_num}') if file_path and line_num else None
            html = render_markdown(text)
            content = md_sources.get(file_path)
            children = c.get('children') or []
            if content and children:
                lines = content.splitlines()
                targets = []
                for ch in children:
                    ln = ch.get('line_num')
                    if ln and 0 < ln <= len(lines) and _TASK_LINE_RE.match(lines[ln - 1]):
                        targets.append((file_path, ln, lines[ln - 1]))
                    else:
                        targets.append(None)
                html = _annotate_inputs(html, targets)
            col_cards.append({
                'id': c.get('id') or _short_id(file_path, line_num, text),
                'html': html,
                'inline': c.get('source') == 'inline',
                'file_path': file_path,
                'line_num': line_num,
                'author': author,
            })
        color = str(g.get('color')) if g.get('color') else None
        columns.append({
            'label': g.get('label') or 'Untitled',
            'color_class': f'kanban-col-{color}' if color in _COLOR_CLASSES else 'kanban-col-none',
            'cards': col_cards,
        })
    return columns


def render_kanban_html(canvas, blame=None, stale=False, md_sources=None):
    return render_template('partials/kanban_board.html',
                           columns=canvas_to_columns(canvas, blame, md_sources),
                           stale=stale)


def _todo_item_ctx(todo_dict, blame=None):
    blame = blame or {}
    key = f"{todo_dict.get('file_path')}:{todo_dict.get('line_num')}"
    return {
        'todo': todo_dict,
        'tid': _short_id(todo_dict.get('file_path'), todo_dict.get('line_num')),
        'highlighted': highlight_todo(todo_dict.get('todo_text')),
        'author': blame.get(key),
    }


def render_todo_item_html(todo_dict, blame=None):
    return render_template('partials/todo_item.html', **_todo_item_ctx(todo_dict, blame))


def render_todos_list_html(todo_dicts, blame=None):
    items = [_todo_item_ctx(t, blame) for t in todo_dicts or []]
    return render_template('partials/todos_list.html', items=items)


def render_todo_md_files_html(files):
    rendered = []
    for f in files or []:
        content = f.get('content')
        html = None
        if content:
            html = render_markdown(content)
            html = _annotate_inputs(html, [
                (f['file_path'], ln, raw) for ln, raw in _task_lines(content)
            ])
        rendered.append({
            'tid': _short_id(f.get('file_path')),
            'file_path': f.get('file_path'),
            'html': html,
        })
    return render_template('partials/todo_md_files.html', files=rendered)
