"""
Golden-file check for the JSON refactoring (review step E).

Runs sdl_metadata_generator.py on every fixture folder in tests/fixtures/
and compares the result with tests/expected/<fixture>.json.

The comparison is done on the parsed JSON (json.load), so whitespace,
key order and line endings do not matter - list order does.

Usage: run this file (from any working directory).
Exit code 0 = all fixtures identical, 1 = at least one difference/error.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURES_DIR = REPO_ROOT / "tests" / "fixtures"
EXPECTED_DIR = REPO_ROOT / "tests" / "expected"
OUTPUT_DIR = REPO_ROOT / "metadata"
MAX_DIFFS = 10


def find_differences(expected, actual, path="$"):
    """Yield readable descriptions of where two JSON values differ."""
    if isinstance(expected, dict) and isinstance(actual, dict):
        for key in sorted(expected.keys() - actual.keys()):
            yield f"{path}.{key}: missing in new output"
        for key in sorted(actual.keys() - expected.keys()):
            yield f"{path}.{key}: only in new output"
        for key in sorted(expected.keys() & actual.keys()):
            yield from find_differences(expected[key], actual[key], f"{path}.{key}")
    elif isinstance(expected, list) and isinstance(actual, list):
        if len(expected) != len(actual):
            yield f"{path}: list length {len(expected)} -> {len(actual)}"
        for i, (exp_item, act_item) in enumerate(zip(expected, actual)):
            yield from find_differences(exp_item, act_item, f"{path}[{i}]")
    elif expected != actual or type(expected) is not type(actual):
        yield f"{path}: {expected!r} -> {actual!r}"


def run_generator(fixture: Path, output_name: str) -> subprocess.CompletedProcess:
    """Run the generator like the reference run did: same relative --path,
    UTF-8 mode, and 'n' as answer to every interactive question."""
    env = dict(os.environ, PYTHONUTF8="1")
    return subprocess.run(
        [sys.executable, "sdl_metadata_generator.py",
         "--path", str(fixture.relative_to(REPO_ROOT)),
         "--output_file", output_name],
        cwd=REPO_ROOT,
        env=env,
        input="n\n" * 1000,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )


def check_fixture(fixture: Path):
    """Return True (identical), False (different/error) or None (skipped)."""
    name = fixture.name
    expected_file = EXPECTED_DIR / f"{name}.json"
    output_name = f"_check_{name}.json"
    output_file = OUTPUT_DIR / output_name

    if not expected_file.exists():
        print(f"[SKIP]  {name}: no reference file tests/expected/{name}.json")
        return None

    # remove a leftover from an earlier run, otherwise the generator asks
    # whether to overwrite it
    output_file.unlink(missing_ok=True)

    result = run_generator(fixture, output_name)
    warnings = [line for line in result.stderr.splitlines() if line.startswith("WARNING")]

    if result.returncode != 0 or not output_file.exists():
        print(f"[ERROR] {name}: generator failed (exit code {result.returncode})")
        print(result.stderr)
        return False

    try:
        actual = json.loads(output_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as err:
        print(f"[FAIL]  {name}: output is not valid JSON ({err})")
        return False
    expected = json.loads(expected_file.read_text(encoding="utf-8"))

    if actual == expected:
        print(f"[OK]    {name}")
        output_file.unlink()
        ok = True
    else:
        print(f"[FAIL]  {name}: differs from reference - output kept in metadata/{output_name}")
        for i, diff in enumerate(find_differences(expected, actual)):
            if i == MAX_DIFFS:
                print("        ... (more differences)")
                break
            print(f"        {diff}")
        ok = False

    for warning in warnings:
        print(f"        {warning}")
    return ok


def main() -> int:
    fixtures = sorted(p for p in FIXTURES_DIR.iterdir() if p.is_dir())
    results = [check_fixture(f) for f in fixtures]
    failed = results.count(False)
    print(f"\n{len(fixtures)} fixture(s) checked, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())