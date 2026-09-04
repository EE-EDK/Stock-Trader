"""
@file guard.py
@brief Enforcement layer over the memory ledger — makes recorded failures binding.
@details A ledger only helps if someone reads it. That assumption fails exactly
         when it matters most: mid-task, under momentum, when the instruction is
         "just run it". This module turns entries tagged `blocks` into a check the
         pipeline can call before acting, so "do not trade velocity_spike long" is
         enforced by code rather than by an agent remembering to read a file.

         Targets are namespaced strings matched exactly against an entry's
         `applies_to` list:

             trigger:velocity_spike     a signal trigger
             action:buy                 an order side
             action:live_trade          any real-money execution
             env:container              an execution environment
             tool:yfinance              a specific dependency

         Matching is a CONJUNCTION: every target an entry names must appear in
         the query for it to apply. An entry about 'velocity_spike + buy' does
         not fire on an unrelated buy. A matching entry with `blocks` set BLOCKS;
         any other matching entry is returned as an advisory.

@usage  from docs.memory.guard import check
        v = check('trigger:velocity_spike', 'action:buy')
        if v.blocked:
            raise RuntimeError(v.explain())

        # or from the shell / CI:
        python docs/memory/guard.py trigger:velocity_spike action:buy

@warning A clean verdict means "nothing recorded forbids this", NOT "this is a
         good idea". The ledger only knows what has already been measured.
@version 1.0.0
@date 2026-08-29
"""

import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent))
from memory import load  # noqa: E402


@dataclass
class Verdict:
    """
    @brief Result of a guard check.
    @details `blocked` is the only field callers must branch on. `advisories`
             are relevant but non-fatal — surface them, do not stop for them.
    """
    targets: List[str] = field(default_factory=list)
    blocking: List[Dict[str, Any]] = field(default_factory=list)
    advisories: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def blocked(self) -> bool:
        """@return True if any recorded, validated failure forbids this action."""
        return bool(self.blocking)

    def explain(self) -> str:
        """@return Human-readable reason, citing entry ids so it can be audited."""
        if not self.blocking and not self.advisories:
            return f"No ledger entry applies to {', '.join(self.targets)}."
        out = []
        for e in self.blocking:
            n = f" (n={e['sample_n']})" if e.get('sample_n') else ''
            out.append(f"BLOCKED by #{e['id']}: {e['title']}{n}")
            if e.get('retest_when'):
                out.append(f"    re-test when: {e['retest_when']}")
        for e in self.advisories:
            out.append(f"advisory #{e['id']}: {e['title']}")
        return '\n'.join(out)


def check(*targets: str) -> Verdict:
    """
    @brief Test a proposed action against everything the ledger has recorded.
    @param targets Namespaced target strings, e.g. 'trigger:velocity_spike'
    @return Verdict; branch on .blocked, surface .advisories
    @pre The ledger exists at docs/memory/ledger.jsonl
    @post Never raises on an empty or missing ledger — returns a clean verdict
    """
    wanted = {t.strip() for t in targets if t and t.strip()}
    v = Verdict(targets=sorted(wanted))
    for e in load():
        if e.get('status') in ('superseded', 'refuted'):
            continue
        applies = set(e.get('applies_to') or [])
        # Conjunction, not intersection: an entry describes ONE situation, so
        # every target it names must be present in the query. Otherwise an entry
        # about 'velocity_spike + buy' would fire on any buy at all.
        if not applies or not applies.issubset(wanted):
            continue
        if e.get('blocks') and e.get('status') == 'validated':
            v.blocking.append(e)
        else:
            v.advisories.append(e)
    return v


def require(*targets: str) -> None:
    """
    @brief Assert that no recorded failure forbids this action.
    @param targets Namespaced target strings
    @throws RuntimeError if a blocking entry applies
    @details Convenience wrapper for call sites that should simply refuse to
             proceed. Use check() instead when the caller wants to decide.
    """
    v = check(*targets)
    if v.blocked:
        raise RuntimeError(v.explain())


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__.strip().split('@usage')[1].split('@warning')[0])
        return 2
    v = check(*sys.argv[1:])
    print(v.explain())
    return 1 if v.blocked else 0


if __name__ == '__main__':
    sys.exit(main())
