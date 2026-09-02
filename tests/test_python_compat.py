"""
Guard: source files must not use syntax newer than the minimum Python version
declared in pyproject.toml (requires-python).

Why this exists: syntax newer than the declared floor is invisible to a test suite
running on a newer interpreter. The modules using it are never imported by the tests,
so the suite stays green while the shipped product dies at import time for every user
on a supported-but-older interpreter.

Measured instance this catches: a backslash inside an f-string *expression* part
(`f"{'\\033[92m' if x else ''}"`) is only valid on Python 3.12+ (PEP 701), while these
packages declare 3.9+. On a real Python 3.11.9 this raises
`SyntaxError: f-string expression part cannot include a backslash`.

Scope limit, stated plainly: `ast.parse(..., feature_version=(3, 9))` does NOT catch
this class, because PEP 701 lifted a *tokenizer* restriction and feature_version does
not restore the old tokenizer. So this module walks the AST and inspects f-string
expression source directly. The authoritative guard remains the CI matrix, which runs
the suite on every declared interpreter.
"""

import ast
import pathlib
import re

MIN_VERSION = (3, 9)
REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
PACKAGES = ("loopgraph", "antigravity_optimizer")


def _iter_source_files():
    for package in PACKAGES:
        package_dir = REPO_ROOT / package
        if not package_dir.is_dir():
            continue  # the optimizer is a separate project; absent in a loopgraph-only checkout
        for path in sorted(package_dir.rglob("*.py")):
            if "__pycache__" not in path.parts:
                yield path


def _declared_minimum():
    """Read the floor from the manifest so this guard tracks pyproject.toml instead of
    holding a copy that can silently drift out of sync with it."""
    pyproject = REPO_ROOT / "pyproject.toml"
    if not pyproject.exists():
        return None
    match = re.search(
        r'requires-python\s*=\s*["\']>=\s*(\d+)\.(\d+)', pyproject.read_text(encoding="utf-8")
    )
    return (int(match.group(1)), int(match.group(2))) if match else None


def _backslashes_in_fstring_expressions(source: str, tree: ast.AST):
    """Return the f-string expression sources that contain a backslash."""
    offenders = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.JoinedStr):
            continue
        for part in node.values:
            if not isinstance(part, ast.FormattedValue):
                continue
            segment = ast.get_source_segment(source, part.value)
            if segment and "\\" in segment:
                offenders.append((part.lineno, segment))
    return offenders


def test_declared_minimum_matches_this_guard():
    declared = _declared_minimum()
    assert declared is not None, "requires-python not found in pyproject.toml"
    assert declared == MIN_VERSION, (
        f"pyproject.toml declares Python {declared[0]}.{declared[1]} but this guard checks "
        f"{MIN_VERSION[0]}.{MIN_VERSION[1]}; update MIN_VERSION to match."
    )


def test_no_backslash_inside_fstring_expressions():
    """Valid only on Python 3.12+; these packages declare 3.9+."""
    offenders = []
    for path in _iter_source_files():
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
        for lineno, segment in _backslashes_in_fstring_expressions(source, tree):
            offenders.append(f"{path.relative_to(REPO_ROOT)}:{lineno}: {segment.strip()[:70]}")

    assert not offenders, (
        "A backslash inside an f-string expression requires Python 3.12+, but this "
        f"project supports {MIN_VERSION[0]}.{MIN_VERSION[1]}+. Move the escape into a "
        "named constant outside the f-string:\n  " + "\n  ".join(offenders)
    )


def test_guard_detects_a_known_offender():
    """The guard must reject real offending source, otherwise a green result above
    would prove nothing (a check that cannot fail is not a check).

    The rejection takes a different form depending on the interpreter running the tests:
    below 3.12 the offending source does not even parse (the interpreter itself is the
    guard), while on 3.12+ it parses cleanly and only the AST walk can catch it. Both
    outcomes are a detection; silently accepting the source is not.
    """
    offending = "x = True\n" 'y = f"{chr(92) if x else 0}"\n'.replace("chr(92)", "'\\033[92m'")

    try:
        tree = ast.parse(offending)
    except SyntaxError:
        return  # interpreter predates PEP 701 and rejected it outright

    assert _backslashes_in_fstring_expressions(offending, tree), (
        "the guard failed to flag source that a real Python 3.11 rejects"
    )


def test_all_sources_parse():
    """Every source file must at least be syntactically valid Python."""
    broken = []
    for path in _iter_source_files():
        try:
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError as exc:
            broken.append(f"{path.relative_to(REPO_ROOT)}: {exc.msg} (line {exc.lineno})")
    assert not broken, "syntax errors:\n  " + "\n  ".join(broken)
