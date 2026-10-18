"""Run the frozen sheet policy with its verified lossless incremental constructor."""
import hashlib
import importlib.util
from pathlib import Path

SOURCE = Path(__file__).resolve().parent
REPAIR_SHA256 = 'cf269edbf3cc4954d74085b8af24ecdcae86945e3a3e7bba7e3c53bc259d5a5d'
CONSTRUCTOR_SHA256 = '81422bc8ce95beab8039e33f70a9d1274083be1ce1426c778c700a06a8b21df8'


def _load(name, expected):
    path = SOURCE/(name+'.py')
    if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        raise ValueError('A frozen incremental-repair dependency changed')
    spec = importlib.util.spec_from_file_location('carrier_incremental_repair_'+name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_BASE = _load('continuous_combinatorial_interfaces', REPAIR_SHA256)
_CONSTRUCTOR = _load('incremental_combinatorial_interfaces_ids', CONSTRUCTOR_SHA256)
_BASE._CONSTRUCTION = _CONSTRUCTOR
repair = _BASE.repair
