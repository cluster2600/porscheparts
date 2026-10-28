"""Compare the pinned 935 level-(3 4) and level-(4 4) native mesh trials."""

from pathlib import Path
import sys

from compare_surface_level import run


CHILD_SHA = "693ad93790eb576a1dc3f786bd83483968cc6cebc5d879abb8ae0d95b332b48b"
CHILD_WALL_SHA = "5d20a9d7e781098c0d0bb256b62cf89155550b95c07676d972d2d1767173a43a"


if __name__ == "__main__":
    if len(sys.argv) != 5:
        raise SystemExit("usage: compare_surface_level4.py PARENT_ARCHIVE CHILD_ARCHIVE PARENT_WALL_GZ NEW_PRIVATE_REPORT")
    run(*(Path(item) for item in sys.argv[1:]),
        child_sha=CHILD_SHA, child_wall_sha=CHILD_WALL_SHA,
        child_name="level44-case", child_level="level (4 4);",
        status="rejected_uniform_level4_no_CFD")
