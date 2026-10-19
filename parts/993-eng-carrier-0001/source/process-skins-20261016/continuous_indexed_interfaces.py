"""Run the frozen continuous-sheet policy with its exact source-line index."""
import hashlib
import importlib.util
from pathlib import Path

SOURCE = Path(__file__).resolve().parent
REPAIR_SHA256 = 'cf269edbf3cc4954d74085b8af24ecdcae86945e3a3e7bba7e3c53bc259d5a5d'
INDEX_SHA256 = '0302ac46796b2dab08484873370ab1f4d5eff6319c752f966641825a34aba2bd'


def _load(name, expected):
    path = SOURCE/(name+'.py')
    if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        raise ValueError('A frozen indexed-repair dependency changed')
    spec = importlib.util.spec_from_file_location('carrier_indexed_repair_'+name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_BASE = _load('continuous_combinatorial_interfaces', REPAIR_SHA256)
_INDEX = _load('indexed_combinatorial_interfaces', INDEX_SHA256)
_BASE._CONSTRUCTION = _INDEX
repair = _BASE.repair
