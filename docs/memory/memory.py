"""
@file memory.py
@brief Append-only project memory: what was tried, what worked, what did not.
@details The problem this solves: every fresh agent session re-derives context
         that a previous session already paid for, and re-attempts approaches
         that were already proven not to work. Prose documentation rots because
         updating it is expensive. This makes writing one entry a single command
         and makes reading automatic (AGENTS.md startup step 2).

         `ledger.jsonl` is the SOURCE OF TRUTH — one JSON object per line,
         append-only, never edited in place. `LEDGER.md` is a generated view,
         rewritten from the JSONL on every append. Never hand-edit LEDGER.md;
         your changes will be overwritten on the next `add`.

         Correction happens by SUPERSEDING, never by deleting — a new entry
         points at the old one, the old one is retained and annotated. This
         matches the project's historical-preservation red line in AGENTS.md.

         Confidence labels mirror Technical Editor Protocol v5.4 §III:
           VERIFIED  - confirmed against a primary source (code, query, filing)
           DERIVED   - computed or inferred from verified data
           RECALLED  - from memory or conversation; verify before acting

@usage  python docs/memory/memory.py add --kind failure --status validated \\
            --confidence VERIFIED --title "..." --detail "..." \\
            --evidence "..." --tags edge,velocity
        python docs/memory/memory.py list --kind failure
        python docs/memory/memory.py list --tag edge --status open
        python docs/memory/memory.py supersede 7 --by 21
        python docs/memory/memory.py render
        python docs/memory/memory.py seed --file seed.json   # bulk import

@version 1.0.0
@date 2026-08-29
"""

import argparse
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional

HERE = Path(__file__).resolve().parent
LEDGER_JSONL = HERE / 'ledger.jsonl'
LEDGER_MD = HERE / 'LEDGER.md'

KINDS = ('finding', 'failure', 'decision', 'fix', 'question')
STATUSES = ('validated', 'refuted', 'open', 'superseded')
CONFIDENCE = ('VERIFIED', 'DERIVED', 'RECALLED')

#: Order sections appear in LEDGER.md. Failures and open questions come first
#: because they are what a fresh session most needs before acting.
SECTIONS = [
    ('question', 'Open questions', 'Unresolved. Do not assume an answer.'),
    ('failure', 'What does not work',
     'Tried and failed, or measured and found harmful. Do not repeat these.'),
    ('finding', 'Validated findings', 'Measured results with evidence attached.'),
    ('fix', 'Fixes applied', 'Defects found and corrected, with what proved them.'),
    ('decision', 'Decisions', 'Choices made, with the reasoning that would reverse them.'),
]


def _read() -> List[Dict[str, Any]]:
    """
    @brief Load every entry from the JSONL source of truth.
    @return List of entry dicts in insertion order
    """
    if not LEDGER_JSONL.exists():
        return []
    out = []
    for line in LEDGER_JSONL.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if line:
            out.append(json.loads(line))
    return out


def _append(entry: Dict[str, Any]) -> None:
    """@brief Append one entry to the JSONL. Never rewrites existing lines."""
    with LEDGER_JSONL.open('a', encoding='utf-8') as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + '\n')


def _next_id(entries: List[Dict[str, Any]]) -> int:
    """@brief Next sequential id (ids are stable and never reused)."""
    # Correction and annotation records carry id=None; skip them, or max()
    # compares None against int and raises.
    return max((e['id'] for e in entries if e.get('id') is not None), default=0) + 1


def add(args) -> int:
    """
    @brief Append a new entry and regenerate the rendered ledger.
    @param args Parsed CLI namespace
    @return Process exit code
    """
    entries = _read()
    entry = {
        'id': _next_id(entries),
        'date': args.date or date.today().isoformat(),
        'kind': args.kind,
        'status': args.status,
        'confidence': args.confidence,
        'title': args.title.strip(),
        'detail': (args.detail or '').strip(),
        'evidence': (args.evidence or '').strip(),
        'tags': [t.strip() for t in (args.tags or '').split(',') if t.strip()],
        'applies_to': [a.strip() for a in (args.applies_to or '').split(',') if a.strip()],
        'sample_n': args.sample_n,
        'retest_when': (args.retest_when or '').strip(),
        'blocks': bool(args.blocks),
        'supersedes': args.supersedes,
        'superseded_by': None,
    }
    _append(entry)
    if args.supersedes:
        _mark_superseded(args.supersedes, entry['id'])
    render(None)
    print(f"added #{entry['id']}: [{entry['kind']}/{entry['status']}] {entry['title']}")
    return 0


def _mark_superseded(old_id: int, new_id: int) -> None:
    """
    @brief Record that an older entry has been replaced.
    @param old_id Entry being superseded
    @param new_id Entry that replaces it
    @details Appends a correction record rather than editing the original line,
             so the JSONL stays strictly append-only. The renderer folds these
             corrections in when it builds LEDGER.md.
    """
    _append({'id': None, 'correction_of': old_id, 'superseded_by': new_id,
             'date': date.today().isoformat()})


def annotate(args) -> int:
    """
    @brief Add targeting/falsifiability metadata to an existing entry.
    @param args Parsed CLI namespace
    @return Process exit code
    @details Appends an annotation record rather than editing the original line,
             so the JSONL stays strictly append-only. Use this to attach
             applies_to / sample_n / retest_when to entries written before those
             fields existed, or to record a re-measurement.
    """
    entries = _resolve(_read())
    if args.entry_id not in {e['id'] for e in entries}:
        print(f"ERROR: no entry #{args.entry_id}")
        return 1
    patch: Dict[str, Any] = {}
    if args.applies_to:
        patch['applies_to'] = [a.strip() for a in args.applies_to.split(',') if a.strip()]
    if args.sample_n is not None:
        patch['sample_n'] = args.sample_n
    if args.retest_when:
        patch['retest_when'] = args.retest_when.strip()
    if args.blocks is not None:
        patch['blocks'] = bool(args.blocks)
    if not patch:
        print("ERROR: nothing to annotate")
        return 1
    _append({'id': None, 'annotates': args.entry_id, 'patch': patch,
             'date': date.today().isoformat()})
    render(None)
    print(f"annotated #{args.entry_id}: {patch}")
    return 0


def _resolve(entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    @brief Fold correction records into the entries they annotate.
    @param entries Raw JSONL rows
    @return Real entries only, with superseded_by/status applied
    """
    corrections = {e['correction_of']: e['superseded_by']
                   for e in entries if e.get('correction_of') is not None}
    real = [dict(e) for e in entries if e.get('id') is not None]
    for e in real:
        e.setdefault('applies_to', [])
        e.setdefault('sample_n', None)
        e.setdefault('retest_when', '')
        e.setdefault('blocks', False)
        for ann in entries:                      # annotations applied in order
            if ann.get('annotates') == e['id']:
                e.update(ann['patch'])
        if e['id'] in corrections:
            e['superseded_by'] = corrections[e['id']]
            e['status'] = 'superseded'
    return real


def load() -> List[Dict[str, Any]]:
    """
    @brief Public read API for other modules (see guard.py).
    @return Fully resolved entries with corrections and annotations applied
    """
    return _resolve(_read())


def _fmt(e: Dict[str, Any]) -> str:
    """@brief Render one entry as a markdown block."""
    head = f"#### `#{e['id']}` {e['title']}"
    if e.get('superseded_by'):
        head += f"  — **SUPERSEDED by #{e['superseded_by']}**"
    meta = f"*{e['date']} · {e['confidence']} · {e['status']}*"
    if e.get('tags'):
        meta += ' · ' + ' '.join(f'`{t}`' for t in e['tags'])
    parts = [head, '', meta, '']
    if e.get('detail'):
        parts += [e['detail'], '']
    if e.get('evidence'):
        parts += [f"**Evidence:** {e['evidence']}", '']
    if e.get('sample_n') or e.get('retest_when'):
        bits = []
        if e.get('sample_n'):
            bits.append(f"measured at n={e['sample_n']}")
        if e.get('retest_when'):
            bits.append(f"**re-test when:** {e['retest_when']}")
        parts += ['*' + ' · '.join(bits) + '*', '']
    if e.get('blocks') and e.get('applies_to'):
        parts += [f"**ENFORCED** — blocks: {', '.join(f'`{a}`' for a in e['applies_to'])}", '']
    return '\n'.join(parts)


def render(_args) -> int:
    """
    @brief Regenerate LEDGER.md from the JSONL.
    @return Process exit code
    @warning Overwrites LEDGER.md entirely. Never hand-edit that file.
    """
    entries = _resolve(_read())
    live = [e for e in entries if e['status'] != 'superseded']
    dead = [e for e in entries if e['status'] == 'superseded']

    out = [
        '# Project Memory — Ledger',
        '',
        '> **Generated file. Do not edit.** Written by `docs/memory/memory.py`.',
        '> Source of truth is `ledger.jsonl`. Add entries with '
        '`python docs/memory/memory.py add ...`.',
        '',
        f'**{len(live)} live entries · {len(dead)} superseded · '
        f'last updated {date.today().isoformat()}**',
        '',
        '## Read this first',
        '',
    ]

    blockers = [e for e in live if e['kind'] == 'question']
    dont = [e for e in live if e['kind'] == 'failure']
    if dont:
        out.append('**Do not repeat these:**')
        out += [f"- `#{e['id']}` {e['title']}" for e in dont]
        out.append('')
    if blockers:
        out.append('**Unresolved:**')
        out += [f"- `#{e['id']}` {e['title']}" for e in blockers]
        out.append('')

    out += ['---', '']
    for kind, heading, blurb in SECTIONS:
        rows = [e for e in live if e['kind'] == kind]
        if not rows:
            continue
        out += [f'## {heading}', '', f'*{blurb}*', '']
        out += [_fmt(e) for e in sorted(rows, key=lambda x: -x['id'])]
        out += ['---', '']

    if dead:
        out += ['## Superseded', '',
                '*Retained per the historical-preservation rule. '
                'Read the superseding entry instead.*', '']
        out += [_fmt(e) for e in sorted(dead, key=lambda x: -x['id'])]

    LEDGER_MD.write_text('\n'.join(out), encoding='utf-8')
    return 0


def list_entries(args) -> int:
    """
    @brief Print entries to stdout, optionally filtered.
    @param args Parsed CLI namespace (kind, status, tag, id)
    @return Process exit code
    """
    entries = _resolve(_read())
    if args.id:
        entries = [e for e in entries if e['id'] == args.id]
    if args.kind:
        entries = [e for e in entries if e['kind'] == args.kind]
    if args.status:
        entries = [e for e in entries if e['status'] == args.status]
    if args.tag:
        entries = [e for e in entries if args.tag in e.get('tags', [])]
    if not entries:
        print('(no matching entries)')
        return 0
    for e in sorted(entries, key=lambda x: -x['id']):
        flag = f" SUPERSEDED->#{e['superseded_by']}" if e.get('superseded_by') else ''
        print(f"#{e['id']:<3} [{e['kind']:<8}/{e['status']:<9}] {e['confidence']:<8} "
              f"{e['date']}{flag}\n     {e['title']}")
        if args.full and e.get('detail'):
            print(f"     {e['detail']}")
        if args.full and e.get('evidence'):
            print(f"     evidence: {e['evidence']}")
    return 0


def supersede(args) -> int:
    """@brief Mark an entry superseded by a newer one."""
    entries = _resolve(_read())
    ids = {e['id'] for e in entries}
    if args.old_id not in ids or args.by not in ids:
        print(f"ERROR: unknown id (have {sorted(ids)})")
        return 1
    _mark_superseded(args.old_id, args.by)
    render(None)
    print(f"#{args.old_id} superseded by #{args.by}")
    return 0


def seed(args) -> int:
    """
    @brief Bulk-import entries from a JSON array file (idempotent by title).
    @param args Parsed CLI namespace with .file
    @return Process exit code
    """
    payload = json.loads(Path(args.file).read_text(encoding='utf-8'))
    existing = {e['title'] for e in _resolve(_read())}
    n = 0
    for raw in payload:
        if raw['title'] in existing:
            continue
        entries = _read()
        entry = {
            'id': _next_id(entries),
            'date': raw.get('date', date.today().isoformat()),
            'kind': raw['kind'], 'status': raw['status'],
            'confidence': raw['confidence'], 'title': raw['title'],
            'detail': raw.get('detail', ''), 'evidence': raw.get('evidence', ''),
            'tags': raw.get('tags', []), 'supersedes': raw.get('supersedes'),
            'superseded_by': None,
        }
        _append(entry)
        n += 1
    render(None)
    print(f"seeded {n} new entries ({len(payload) - n} already present)")
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description='Append-only project memory ledger')
    sub = p.add_subparsers(dest='cmd', required=True)

    a = sub.add_parser('add', help='append an entry')
    a.add_argument('--kind', required=True, choices=KINDS)
    a.add_argument('--status', required=True, choices=STATUSES)
    a.add_argument('--confidence', required=True, choices=CONFIDENCE)
    a.add_argument('--title', required=True)
    a.add_argument('--detail', default='')
    a.add_argument('--evidence', default='')
    a.add_argument('--tags', default='')
    a.add_argument('--date', default=None)
    a.add_argument('--supersedes', type=int, default=None)
    a.add_argument('--applies-to', dest='applies_to', default='',
                   help='comma-separated targets, e.g. trigger:velocity_spike,action:buy')
    a.add_argument('--sample-n', dest='sample_n', type=int, default=None,
                   help='sample size the claim was measured at')
    a.add_argument('--retest-when', dest='retest_when', default='',
                   help='condition that should trigger re-measurement')
    a.add_argument('--blocks', action='store_true',
                   help='guard.py hard-blocks actions matching applies_to')
    a.set_defaults(func=add)

    an = sub.add_parser('annotate', help='append metadata to an existing entry')
    an.add_argument('entry_id', type=int)
    an.add_argument('--applies-to', dest='applies_to', default='')
    an.add_argument('--sample-n', dest='sample_n', type=int, default=None)
    an.add_argument('--retest-when', dest='retest_when', default='')
    an.add_argument('--blocks', type=int, choices=[0, 1], default=None)
    an.set_defaults(func=annotate)

    l = sub.add_parser('list', help='print entries')
    l.add_argument('--kind', choices=KINDS)
    l.add_argument('--status', choices=STATUSES)
    l.add_argument('--tag')
    l.add_argument('--id', type=int)
    l.add_argument('--full', action='store_true')
    l.set_defaults(func=list_entries)

    s = sub.add_parser('supersede', help='mark an entry replaced')
    s.add_argument('old_id', type=int)
    s.add_argument('--by', type=int, required=True)
    s.set_defaults(func=supersede)

    r = sub.add_parser('render', help='regenerate LEDGER.md')
    r.set_defaults(func=render)

    sd = sub.add_parser('seed', help='bulk import from a JSON array')
    sd.add_argument('--file', required=True)
    sd.set_defaults(func=seed)

    args = p.parse_args()
    return args.func(args)


if __name__ == '__main__':
    sys.exit(main())
