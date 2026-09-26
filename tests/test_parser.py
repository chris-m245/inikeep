from inikeep import IniDocument


def test_round_trip_is_byte_identical():
    text = "[a]\nx = 1\n; note\ny = 2\n"
    doc = IniDocument.parse(text)
    assert str(doc) == text


def test_get_and_set_existing_key():
    doc = IniDocument.parse("[db]\nhost = localhost\nport = 5432\n")
    assert doc.get("db", "port") == "5432"
    doc.set("db", "port", "5433")
    assert doc.get("db", "port") == "5433"
    assert "5433" in str(doc)


def test_set_new_key_appends_within_section():
    doc = IniDocument.parse("[db]\nhost = localhost\n\n[other]\nx = 1\n")
    doc.set("db", "port", "5432")
    assert doc.options("db") == ["host", "port"]
    assert doc.get("other", "x") == "1"


def test_set_new_section_created_on_demand():
    doc = IniDocument.parse("[a]\nx = 1\n")
    doc.set("b", "y", "2")
    assert doc.sections() == ["a", "b"]
    assert doc.get("b", "y") == "2"


def test_remove_key():
    doc = IniDocument.parse("[a]\nx = 1\ny = 2\n")
    assert doc.remove("a", "x") is True
    assert doc.remove("a", "x") is False
    assert doc.options("a") == ["y"]


def test_comments_and_blank_lines_survive_edits():
    doc = IniDocument.parse("[a]\n; keep me\nx = 1\n\ny = 2\n")
    doc.set("a", "x", "99")
    text = str(doc)
    assert "; keep me" in text
    assert "\n\n" in text


def test_inline_comment_is_split_from_value():
    doc = IniDocument.parse("[server]\nport = 8080 ; default, override in prod\n")
    assert doc.get("server", "port") == "8080"


def test_inline_comment_with_hash():
    doc = IniDocument.parse("[a]\nx = 1 # trailing note\n")
    assert doc.get("a", "x") == "1"


def test_unchanged_inline_comment_line_round_trips_exactly():
    text = "[server]\nport = 8080 ; default, override in prod\n"
    doc = IniDocument.parse(text)
    assert str(doc) == text


def test_set_preserves_inline_comment():
    doc = IniDocument.parse("[server]\nport = 8080 ; default, override in prod\n")
    doc.set("server", "port", "9090")
    text = str(doc)
    assert "port = 9090 ; default, override in prod" in text
    assert doc.get("server", "port") == "9090"


def test_comment_char_without_leading_space_is_kept_in_value():
    doc = IniDocument.parse("[a]\nurl = http://example.com/#frag\n")
    assert doc.get("a", "url") == "http://example.com/#frag"
