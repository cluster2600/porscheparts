"""Optional test dependencies, declared instead of endured.

`make check` must give a clean green on a bare Python. This is not cosmetic: a
suite that always fails in twenty-three ways no longer signals anything, and
every run must then be compared with a list of known failures to know whether
something was just broken. That is exactly what had to be done during the
reorganization of 2026-09-09.

A few tests call scripts that need numpy, matplotlib or jq. These tools are not
dependencies of the repository: `scripts/` does without them on principle. The
affected tests therefore **skip** explicitly when the tool is missing, naming
it, rather than falling over with an ImportError.

A skip stays visible: unittest counts and displays them. A skipped test is not a
passing test, and the number of skips measures what the environment does not
cover.

    from _deps import require_modules, require_commands

    require_modules("numpy")
"""
import importlib.util
import shutil
import unittest


def require_modules(*modules: str) -> None:
    """Skip the test module if one of the named packages is missing."""
    for name in modules:
        if importlib.util.find_spec(name) is None:
            raise unittest.SkipTest(
                f"{name} absent : ce test appelle un script qui en depend. "
                f"Installer {name} pour le couvrir."
            )


def require_commands(*commands: str) -> None:
    """Skip the test module if one of the named executables is missing."""
    for name in commands:
        if shutil.which(name) is None:
            raise unittest.SkipTest(
                f"{name} absent du PATH : ce test l'invoque. "
                f"Installer {name} pour le couvrir."
            )
