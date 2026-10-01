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

Inline comments after a value are split out, not treated as part of it:

```python
doc = IniDocument.parse("[server]\nport = 8080 ; default, override in prod\n")
doc.get("server", "port")   # "8080"
doc.set("server", "port", "9090")
print(doc)   # port = 9090 ; default, override in prod
```

The comment char only starts a comment when it's preceded by whitespace,
so a value like a URL containing `#` isn't mistaken for one.

Typed accessors take the same `fallback` argument as `get()`. A missing key
returns the fallback; a value that can't be converted raises `ValueError`.
`getboolean` accepts `1/yes/true/on` and `0/no/false/off`, any case, the
same as `configparser`.

```python
doc = IniDocument.parse("[server]\nport = 8080\ndebug = Yes\n")
doc.getint("server", "port")                  # 8080
doc.getboolean("server", "debug")             # True
doc.getfloat("server", "timeout", fallback=2.5)  # 2.5
```

Reading and writing files directly:

```python
doc = IniDocument.load("app.ini")
doc.set("server", "port", "9090")
doc.save("app.ini")
```

## What it does not do (yet)

- `get()` and `set()` deal in strings only; use `getint`, `getfloat` and
  `getboolean` to convert on read.
- No `%(interpolation)s` support.
- Duplicate keys within a section: `get()` returns the first match.

## Install

Not published anywhere yet. For now, clone it and install locally:

```
pip install -e .
```

Requires Python 3.9+. No third-party dependencies.

## License

MIT, see LICENSE.
