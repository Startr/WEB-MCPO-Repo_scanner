"""Inline TODO comments must not render as markdown headings.

A `#` comment marker is also markdown for <h1>, so the raw comment line
`# TODO: fix this` used to paint as a giant heading on the board. The card
text now carries the comment syntax stripped.
"""
import pytest

from scanner.app import TodoItem
from scanner.kanban import inline_todo_to_card


@pytest.mark.parametrize('raw,expected', [
    ('# TODO: idempotency key so retries do not double-charge',
     'TODO: idempotency key so retries do not double-charge'),
    ('    # FIXME: expired codes still apply on retry',
     'FIXME: expired codes still apply on retry'),
    ('// TODO: swap the polling loop for a webhook',
     'TODO: swap the polling loop for a webhook'),
    ('/* BUG: partial refunds ignore shipping */',
     'BUG: partial refunds ignore shipping'),
    ('<!-- TODO: alt text on every image -->',
     'TODO: alt text on every image'),
    ('; TODO: assembler comment form',
     'TODO: assembler comment form'),
    ('-- TODO: sql comment form',
     'TODO: sql comment form'),
])
def test_comment_syntax_stripped_from_card_text(raw, expected):
    card = inline_todo_to_card(TodoItem('src/x.py', 3, raw, None))
    assert card is not None
    assert card.text == expected
    assert not card.text.startswith('#')


def test_column_routing_survives_stripping():
    cases = [('# TODO: a', 'todo'), ('# FIXME: b', 'in_progress'), ('# BUG: c', 'bugs')]
    for raw, column in cases:
        card = inline_todo_to_card(TodoItem('src/x.py', 1, raw, None))
        assert card.column == column, raw


def test_note_still_produces_no_card():
    assert inline_todo_to_card(TodoItem('src/x.py', 1, '# NOTE: just an observation', None)) is None


def test_bare_comment_marker_keeps_original_text():
    """Stripping must never empty a card."""
    card = inline_todo_to_card(TodoItem('src/x.py', 1, '# TODO:', None))
    assert card.text.strip()
