"""Verify the FFIEC pipeline wrote nothing outside ffiec/ and changed no shared file.

    python ffiec/verify_isolation.py [--base main] [--allow-sync]

Diffs the working tree and HEAD against the merge-base with the base branch (default: the `upstream/main`
if that remote exists, else `main`) and lists every changed path outside ffiec/. Exit 1 if any.
Sync merges from upstream legitimately bring in FDIC-side changes; with --allow-sync, paths whose content in
HEAD equals upstream's (i.e. arrived by sync, not edited here) are not counted.
"""
import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ALLOWED_PREFIX = "ffiec/"


def git(*args):
    return subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True, check=True).stdout


def default_base():
    remotes = git("remote").split()
    return "upstream/main" if "upstream" in remotes else "main"


def changed_outside(base, allow_sync=False):
    mb = git("merge-base", "HEAD", base).strip()
    paths = set(git("diff", "--name-only", mb).splitlines())                 # HEAD and working tree vs merge-base
    paths |= set(git("ls-files", "--others", "--exclude-standard").splitlines())
    bad = sorted(p for p in paths if not p.startswith(ALLOWED_PREFIX))
    if allow_sync and bad:
        up = subprocess.run(["git", "-C", str(ROOT), "diff", "--name-only", base, "--", *bad],
                            capture_output=True, text=True).stdout.split()
        bad = sorted(set(up))
    return mb, bad


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--base")
    ap.add_argument("--allow-sync", action="store_true")
    a = ap.parse_args(argv)
    base = a.base or default_base()
    mb, bad = changed_outside(base, a.allow_sync)
    print(f"base {base} merge-base {mb[:10]}; changed outside ffiec/: {len(bad)}")
    for p in bad:
        print("  ", p)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
