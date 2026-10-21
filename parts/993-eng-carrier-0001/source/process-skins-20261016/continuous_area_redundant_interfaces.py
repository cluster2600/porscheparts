"""Reuse exact cycle areas in a private instance of the frozen5047 policy."""
import hashlib
import importlib.util
from pathlib import Path

SOURCE = Path(__file__).resolve().parent
POLICY_SHA256 = 'a2a1dc92a638ed3d901bcf058ac25bb8a368d9bdd8b023355e8f2448eb5dac4b'
AREA_SHA256 = '2230847e5862b3d6668a900c2774ebb82cb3f12555486747fb06dfe8d5a90341'


def _load(name, expected):
    path = SOURCE/(name+'.py')
    if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
        raise ValueError('A frozen area-reuse repair dependency changed')
    spec = importlib.util.spec_from_file_location('_private_area_reuse_repair_'+name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_POLICY = _load('continuous_redundant_interfaces', POLICY_SHA256)
_AREA = _load('incremental_combinatorial_interfaces_area', AREA_SHA256)
_POLICY._CONSTRUCTOR._IDS._OLD._Assembly = _AREA._Assembly
repair = _POLICY.repair
