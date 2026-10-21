# Published hypothetical constitutive witnesses

This is a **software-verification checkpoint**, using a hypothetical 1 × 2 ×
10 mm bar. It contains no cylinder-head solution, physical alloy card, heat
transport, deposition, calibrated process or manufacturing approval.

Both original native solves are retained: 140 elastic and 154 plastic field
comparisons pass at seven times, with six converged equilibrium solves per case.
E(T), Poisson ratio(T), mean CTE(T) and the perfect-J2 yield stress Y(T) vary as
stated in the hypothetical card. The complete frozen histories and tolerances
are reproduced byte-for-byte from the pre-native contract. The analytical
semantics and pinned primary-source links are in the
[source README](../../../source/physics_witness/README.md).

The checker was hardened after execution. Current assessments enforce the
frozen histories/tolerances, native input hashes, immutable native outputs and
exclusive output. Neither solve was repeated. The initial assessor digest in
the contract and the current checker digest are deliberately separate.

The CSVs and native logs are unchanged. Logs were screened for private host and
user paths; only the generic sandbox path `/tmp/work` appears. Runtime JSON is
an explicit whitelist projection of the original receipts, retaining numeric
limits, input/binary/log hashes and relative solver arguments. Raw command and
native receipts contain host paths and remain local. Original receipt digests
are published as provenance anchors, not as a way to reproduce omitted bytes.

The original-capture manifest retains all captured artifact hashes, including
Exodus files that remain local. Complete original SSH capture reconstruction
was checked locally: reconstructing the returned JSON, including the native
artifact bytes, exactly matched each original stdout digest. That complete
check requires the private receipts. The public check below verifies published
hashes and field/reference agreement; it does not independently reconstruct
those omitted receipts or establish a trusted timestamp for the local freeze.

From the repository root, this standard-library check needs neither a solver
nor any file from `work/`:

```sh
python3 -B - <<'PYVERIFY'
import hashlib
import importlib.util
import json
from pathlib import Path

bundle = Path("twins/962-cylinder-head-f0/derived/engineering/constitutive-witnesses")
manifest = json.loads((bundle / "files.json").read_text())
for name, expected in manifest["sha256"].items():
    path = (bundle / name).resolve()
    assert path.is_relative_to(bundle.resolve()), name
    assert hashlib.sha256(path.read_bytes()).hexdigest() == expected, name
source = bundle.parents[2] / "source/physics_witness/assess.py"
spec = importlib.util.spec_from_file_location("published_witness_check", source)
checker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checker)
summary = json.loads((bundle / "summary.json").read_text())
assert hashlib.sha256(source.read_bytes()).hexdigest() == summary["checker_source_sha256"]
card = json.loads((bundle / "hypothetical-material.json").read_text())
contract = json.loads((bundle / "predeclared-contract.json").read_text())
for mode, stem in (("elastic", "variable-thermoelastic"), ("plastic", "variable-yield")):
    result = checker.assess(bundle / (mode + "-001") / (stem + "_out.csv"),
                            card, contract, plastic=mode == "plastic")
    assert result["passed"], mode
    print(mode, result["checks_count"], "frozen field comparisons passed")
PYVERIFY
```

This verifies exported extrema, not every quadrature value. No measured
material, head stress, fatigue, LPBF process or manufacturing result follows
from this witness. Further physical work remains open.
