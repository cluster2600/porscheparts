#!/usr/bin/env python3
"""Refuse to run the check suite from a WSL DrvFs or other non-native mount.

AGENTS.md ("Repository location") records why: authoring in
tests/test_917_parametric_layout_master_f30.py publishes through POSIX
operations relative to a directory descriptor (staging directory, atomic
rename) that DrvFs does not serve correctly, so the suite fails closed for an
environment reason, and runs about six times slower. Stop before that.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

# 9p/v9fs/drvfs serve Windows drives inside WSL; none provides the POSIX
# directory-descriptor semantics the authoring tests rely on.
NON_NATIVE = {'9p', 'v9fs', 'drvfs'}


def unescape(field: str) -> str:
    return field.encode().decode('unicode_escape') if '\\' in field else field


def mount_for(path: Path, mountinfo: str) -> tuple[str, str]:
    """Return (mount point, file-system type) of the mount holding path."""
    best = ('/', 'unknown')
    target = str(path)
    for line in mountinfo.splitlines():
        left, sep, right = line.partition(' - ')
        if not sep:
            continue
        mount_point = unescape(left.split()[4])
        fstype = right.split()[0]
        inside = target == mount_point or target.startswith(mount_point.rstrip('/') + '/')
        if inside and len(mount_point) >= len(best[0]):
            best = (mount_point, fstype)
    return best


def verdict(path: Path, mountinfo: str) -> str | None:
    mount_point, fstype = mount_for(path, mountinfo)
    if fstype in NON_NATIVE:
        return (f'{path} is on a {fstype} mount ({mount_point}), which is a WSL DrvFs '
                'or other non-native file system.')
    return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('path', nargs='?', default='.')
    parser.add_argument('--mountinfo', default='/proc/self/mountinfo')
    args = parser.parse_args(argv)
    path = Path(os.path.realpath(args.path))
    try:
        mountinfo = Path(args.mountinfo).read_text()
    except OSError:
        return 0  # No mount table (e.g. macOS): nothing to judge.
    problem = verdict(path, mountinfo)
    if problem:
        print(f'make check refused: {problem}\n'
              'Clone the repository onto a native Linux file system, for example '
              '/home/<user>/porscheparts, and run make check there.\n'
              'See AGENTS.md, "Repository location": authoring tests fail closed '
              'on DrvFs (directory-descriptor rename) and the suite runs ~6x slower.',
              file=sys.stderr)
        return 2
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
