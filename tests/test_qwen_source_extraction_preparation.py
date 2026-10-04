"""Expose only the bounded source-extraction preparation suite to repository CI."""
import importlib.util
from pathlib import Path
import sys


def load_tests(loader, tests, pattern):
    directory = Path(__file__).resolve().parents[1] / "training/qwen-source-extraction-preparation-20261004"
    old_path = list(sys.path)
    try:
        sys.path.insert(0, str(directory))
        spec = importlib.util.spec_from_file_location(
            "qwen_source_extraction_specific_tests", directory / "test_parser_validator.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return loader.loadTestsFromModule(module)
    finally:
        sys.path[:] = old_path
