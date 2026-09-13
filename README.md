# inikeep

A small INI parser that only rewrites the lines you actually change.

## The problem

`configparser` in the standard library reads an INI file into a dict-like
structure and forgets the original text. That's fine if you only ever
read config, but if a tool needs to flip one value in a file that a human
edits by hand, `configparser` will reorder sections, drop comments, and
reformat every remaining line when it writes the file back out. The diff
for a one-line change ends up touching the whole file.

`inikeep` keeps the document as an ordered list of lines. Parsing a file
and writing it straight back out reproduces it exactly. Editing a value
rewrites only that line.

## Usage

```python
from inikeep import IniDocument

text = """\
; deployment config, edited by hand and by our release script
[server]
host = localhost
port = 8080

[logging]
level = info
"""

doc = IniDocument.parse(text)

doc.get("server", "port")          # "8080"
doc.sections()                     # ["server", "logging"]
doc.options("logging")             # ["level"]

doc.set("server", "port", "9090")  # rewrites only that one line
doc.set("logging", "format", "json")  # appended at the end of [logging]

print(doc)
```

Output:

```ini
; deployment config, edited by hand and by our release script
[server]
host = localhost
port = 9090

[logging]
level = info
format = json
```

The comment, the blank line, and the untouched `host` line come through
unchanged.

Reading and writing files directly:

```python
doc = IniDocument.load("app.ini")
doc.set("server", "port", "9090")
doc.save("app.ini")
```

## What it does not do (yet)

- No value type coercion (`getint`, `getboolean`, etc.) — everything is a
  string, same as raw text in the file.
- No `%(interpolation)s` support.
- Duplicate keys within a section: `get()` returns the first match.
- Inline comments after a value (`key = value ; note`) are kept as part
  of the value rather than split out.

## Install

Not published anywhere yet. For now, clone it and install locally:

```
pip install -e .
```

Requires Python 3.9+. No third-party dependencies.

## License

MIT, see LICENSE.
