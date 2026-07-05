"""Inconsistency detection over dictionary entries.

Rules are small functions ``(entry, tags, rows) -> Issue | None`` operating on
the *expanded* form/tag rows (so shorthands are resolved exactly as the build
resolves them). Add a rule by appending a function to ``RULES``.
"""

from dataclasses import dataclass, asdict

from editor.dictlogic import expand_line, validate_line


@dataclass
class Issue:
    rule: str
    severity: str        # "error" | "warning"
    message: str
    lemma: str
    file: str
    line_no: int

    def to_dict(self):
        return asdict(self)


def _expanded(entry):
    """Return (set_of_tags, rows) for an entry, or ({}, []) if it won't expand."""
    try:
        rows = expand_line(entry.logical_line)
    except Exception:
        return set(), []
    return {t for _, _, t, _ in rows}, rows


def rule_uncountable_with_plural(entry, tags, rows):
    # NN:U means "always uncountable"; an NNS plural contradicts it.
    # NN:UN ("sometimes countable") + NNS is allowed and not flagged.
    if "NN:U" in tags and "NNS" in tags:
        return Issue("uncountable-with-plural", "warning",
                     "NN:U noun also has an NNS plural form",
                     entry.lemma_field, entry.file, entry.line_no)
    return None


def rule_orphan_plural(entry, tags, rows):
    has_singular_common_noun = any(
        t.startswith("NN") and t != "NNS" and not t.startswith("NNP")
        for t in tags
    )
    if "NNS" in tags and not has_singular_common_noun:
        return Issue("orphan-plural", "warning",
                     "NNS plural with no singular NN form",
                     entry.lemma_field, entry.file, entry.line_no)
    return None


RULES = [rule_uncountable_with_plural, rule_orphan_plural]


def scan_entry(entry):
    if entry.suppressed or not entry.tags:
        return []
    issues = []
    for problem in validate_line(entry.logical_line):
        issues.append(Issue("validation", "error", problem,
                            entry.lemma_field, entry.file, entry.line_no))
    tags, rows = _expanded(entry)
    for rule in RULES:
        issue = rule(entry, tags, rows)
        if issue:
            issues.append(issue)
    return issues


def scan_entries(entries):
    all_issues = []
    for entry in entries:
        all_issues.extend(scan_entry(entry))
    return all_issues
