"""Run the frozen sheet policy with its verified redundant-strip constructor."""
import hashlib
import importlib.util
from pathlib import Path

SOURCE = Path(__file__).resolve().parent
REPAIR_SHA256 = 'cf269edbf3cc4954d74085b8af24ecdcae86945e3a3e7bba7e3c53bc259d5a5d'
CONSTRUCTOR_SHA256 = '5047b9393408104fe704697a1fc35a9fe18cadc0a8d98fac5f176a409ef5c646'


def _load(name, expected):
    path = SOURCE/(name+'.py')
    if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        raise ValueError('A frozen incremental-repair dependency changed')
    spec = importlib.util.spec_from_file_location('carrier_incremental_repair_'+name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_BASE = _load('continuous_combinatorial_interfaces', REPAIR_SHA256)
_CONSTRUCTOR = _load('redundant_strip_interfaces', CONSTRUCTOR_SHA256)
_BASE._CONSTRUCTION = _CONSTRUCTOR
_BASE.CONSTRUCTION_SHA256 = CONSTRUCTOR_SHA256
repair = _BASE.repair
