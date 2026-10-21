"""One bounded selected-runtime import check. No saved scientific data access."""
import hashlib
import json
from pathlib import Path
import resource
import sys

resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
resource.setrlimit(resource.RLIMIT_CPU, (10, 10))
assert sys.version_info[:3] == (3, 12, 11)
assert sys.flags.isolated and sys.dont_write_bytecode
expected = Path('/Users/maxime/.local/share/uv/python/cpython-3.12.11-macos-aarch64-none/bin/python3.12')
assert Path(sys.executable).resolve(strict=True) == expected

import numpy
import scipy
from scipy.io import netcdf_file

assert callable(netcdf_file) and netcdf_file.__name__ == 'netcdf_file'
assert netcdf_file.__module__.startswith('scipy.io.')
assert numpy.dtype('float64').itemsize == 8
site = (Path(sys.prefix) / 'lib/python3.12/site-packages').resolve(strict=True)
decoder = sys.modules[netcdf_file.__module__]
paths = {Path(m.__file__).resolve(strict=True) for m in (numpy, scipy, decoder)}
for name, module in list(sys.modules.items()):
    filename = getattr(module, '__file__', None)
    if name.startswith(('numpy.', 'scipy.')) and filename and Path(filename).suffix in ('.so', '.dylib'):
        paths.add(Path(filename).resolve(strict=True))
assert 3 <= len(paths) <= 64
records = []
total = 0
for path in sorted(paths):
    assert path.is_relative_to(site) and path.is_file() and not path.is_symlink()
    data = path.read_bytes()
    total += len(data)
    assert total <= 256 * 1024**2
    records.append(dict(path=str(path), sha256=hashlib.sha256(data).hexdigest(), bytes=len(data)))
report = dict(
    schema='962-raw-displacement-selected-decoder-runtime/v1',
    status='SELECTED_IMPORTS_AND_MODULE_PINS_CAPTURED',
    python=dict(executable=sys.executable, resolved_executable=str(expected), version=list(sys.version_info[:3])),
    numpy_version=numpy.__version__, scipy_version=scipy.__version__,
    decoder=dict(module=netcdf_file.__module__, name=netcdf_file.__name__, path=str(Path(decoder.__file__).resolve(strict=True))),
    selected_module_records=records, selected_module_bytes=total,
    selected_module_scope='Three entrypoint sources and loaded NumPy/SciPy extension modules; not complete transitive Python/library ABI closure.',
    saved_scientific_data_access=False, target_assessor_or_parser_import=False,
    source_or_installed_ABI_equivalence=False, field_or_physics_acceptance=False,
)
encoded = (json.dumps(report, indent=2, allow_nan=False) + '\n').encode()
assert len(encoded) <= 128 * 1024
sys.stdout.buffer.write(encoded)
