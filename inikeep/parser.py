"""Round-trip INI parsing: edit values, keep everything else untouched.

configparser (the stdlib option) reads an INI file into a dict and forgets
the source text entirely, so writing it back out reorders sections,
drops comments, and reformats every line. That's fine for config that's
only ever read, but it makes configparser unusable for tools that need to
edit one value in a file a human maintains by hand. IniDocument keeps the
file as an ordered list of lines and only rewrites the ones you touch.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Optional, Union

_SECTION_RE = re.compile(r"^\[(?P<name>.+)\]\s*$")
_COMMENT_CHARS = (";", "#")
_ENTRY_RE = re.compile(
    r"^(?P<indent>\s*)(?P<key>[^=:\s][^=:]*?)\s*(?P<sep>[=:])\s*(?P<value>.*)$"
)


class IniError(Exception):
    """Raised when a document cannot be parsed or an edit is invalid."""


def _split_inline_comment(value: str) -> tuple[str, Optional[str]]:
    """Split "8080 ; note" into ("8080", "; note").

    A comment char only starts an inline comment if it's preceded by
    whitespace, so it doesn't misfire on values like a URL fragment
    (`http://example.com/#frag`) that just happen to contain '#'.
    """
    for i, ch in enumerate(value):
        if i > 0 and ch in _COMMENT_CHARS and value[i - 1].isspace():
            return value[:i].rstrip(), value[i:]
    return value.rstrip(), None


@dataclass
class _Line:
    raw: str
    kind: str  # "blank", "comment", "section", "entry"
    section: Optional[str] = None
    key: Optional[str] = None
    sep: str = "="
    value: Optional[str] = None
    indent: str = ""
    inline_comment: Optional[str] = None


class IniDocument:
    """An INI file kept as an ordered list of lines.

    Parsing an untouched document and writing it back out reproduces it
    exactly (aside from a trailing newline). Only lines you change
    through set()/remove()/add_section() get rewritten.
    """

    def __init__(self) -> None:
        self._lines: list[_Line] = []

    # -- construction --------------------------------------------------

    @classmethod
    def parse(cls, text: str) -> "IniDocument":
        doc = cls()
        section: Optional[str] = None
        for raw in text.splitlines():
            stripped = raw.strip()
            if not stripped:
                doc._lines.append(_Line(raw, "blank"))
                continue
            if stripped[0] in _COMMENT_CHARS:
                doc._lines.append(_Line(raw, "comment"))
                continue
            match = _SECTION_RE.match(stripped)
            if match:
                section = match.group("name")
                doc._lines.append(_Line(raw, "section", section=section))
                continue
            match = _ENTRY_RE.match(raw)
            if not match:
                raise IniError(f"could not parse line: {raw!r}")
            value, inline_comment = _split_inline_comment(match.group("value"))
            doc._lines.append(
                _Line(
                    raw,
                    "entry",
                    section=section,
                    key=match.group("key"),
                    sep=match.group("sep"),
                    value=value,
                    indent=match.group("indent"),
                    inline_comment=inline_comment,
                )
            )
        return doc

    @classmethod
    def load(cls, path: Union[str, Path]) -> "IniDocument":
        return cls.parse(Path(path).read_text())

    def save(self, path: Union[str, Path]) -> None:
        Path(path).write_text(str(self))

    # -- reading ---------------------------------------------------------

    def sections(self) -> list[str]:
        seen: list[str] = []
        for line in self._lines:
            if line.kind == "section" and line.section not in seen:
                seen.append(line.section)
        return seen

    def has_section(self, section: str) -> bool:
        return section in self.sections()

    def options(self, section: str) -> list[str]:
        return [
            line.key
            for line in self._lines
            if line.kind == "entry" and line.section == section
        ]

    def get(self, section: str, key: str, fallback=None):
        for line in self._lines:
            if line.kind == "entry" and line.section == section and line.key == key:
                return line.value
        return fallback

    # -- writing -----------------------------------------------------------

    def set(self, section: str, key: str, value: str) -> None:
        for line in self._lines:
            if line.kind == "entry" and line.section == section and line.key == key:
                line.value = value
                if line.inline_comment:
                    line.raw = (
                        f"{line.indent}{line.key} {line.sep} {value} "
                        f"{line.inline_comment}"
                    )
                else:
                    line.raw = f"{line.indent}{line.key} {line.sep} {value}"
                return
        self._append_entry(section, key, value)

    def remove(self, section: str, key: str) -> bool:
        for i, line in enumerate(self._lines):
            if line.kind == "entry" and line.section == section and line.key == key:
                del self._lines[i]
                return True
        return False

    def add_section(self, section: str) -> None:
        if self.has_section(section):
            raise IniError(f"section already exists: {section}")
        if self._lines and self._lines[-1].kind != "blank":
            self._lines.append(_Line("", "blank"))
        self._lines.append(_Line(f"[{section}]", "section", section=section))

    def _append_entry(self, section: str, key: str, value: str) -> None:
        if not self.has_section(section):
            self.add_section(section)
        insert_at = len(self._lines)
        in_section = False
        for i, line in enumerate(self._lines):
            if line.kind == "section":
                if in_section:
                    insert_at = i
                    break
                in_section = line.section == section
            elif in_section:
                insert_at = i + 1
        self._lines.insert(
            insert_at,
            _Line(
                f"{key} = {value}",
                "entry",
                section=section,
                key=key,
                sep="=",
                value=value,
            ),
        )

    def __str__(self) -> str:
        return "\n".join(line.raw for line in self._lines) + "\n"

    def __iter__(self) -> Iterator[str]:
        return iter(self.sections())
