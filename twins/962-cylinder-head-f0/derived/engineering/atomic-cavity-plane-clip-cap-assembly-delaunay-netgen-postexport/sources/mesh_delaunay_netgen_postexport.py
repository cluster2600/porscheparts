"""One bounded Netgen optimizer on the saved default-optimized Delaunay head; no generation.

The frozen controller supplies admission, claims, source capture and kill/reap.
The cube is software evidence only. Native head execution needs separate authority.
"""
import argparse
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import platform
import sys
import time

WRAPPER_PATH = Path(__file__).resolve()
ROOT = WRAPPER_PATH.parents[3]
CORE_PATH = ROOT / "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-delaunay-prep-001/mesh_assembled_delaunay.py"
CORE_SHA256 = "a3268687edc90b0149775cf5d80a89df82175cc982bbf5d7184b6ea8935be8a4"
PYTHON_SHA256 = "72956ad35cff7691dfed9e04c9593de825ffd5b2fa7e8bc9ae96ce9a1af65621"
DEADLINE = 1200
INPUT = ROOT / "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-volume-delaunay-default-postexport-001/head-volume.msh"
INPUT_WORKER = "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-volume-delaunay-default-postexport-001/worker-report.json"
INPUT_RECEIPT = "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-volume-delaunay-default-postexport-001/receipt.json"
INPUT_READBACK = "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-delaunay-optimized-diagnosis-001/readback-report.json"
ADMISSION = ROOT / "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-surface-admission-001/surface-admission.json"
ADMISSION_SHA256 = "035c45d02357c9b7375a8e7795f7c1915d7e015ee2b63b576cf181965c96d962"
OUTPUT = ROOT / "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-volume-delaunay-netgen-postexport-001"
OPTIONS = {"General.NumThreads":2, "Mesh.MaxNumThreads3D":2, "Mesh.Renumber":0,
    "Mesh.Optimize":0, "Mesh.OptimizeNetgen":0, "Mesh.OptimizeThreshold":.3,
    "Mesh.Binary":1, "Mesh.SaveAll":1, "Mesh.MshFileVersion":4.1}
INPUT_HASHES = {
    "twins/962-cylinder-head-f0/source/audit_quality_head.py": "a298270aa00b1536314a07629b935500c68883ca0d3bd1a179d71b49a8e73991",
    "twins/962-cylinder-head-f0/source/audit_quality_patch.py": "3532a172b2bce3a8ead7c8b11b712a2b55891377726fa1b6d847e84f0eed3912",
    "twins/962-cylinder-head-f0/source/mesh_head.py": "69c8012e99057e384d44d6971d41f0e2cc7197a978120a7c566b0ad5a6477da5",
    "twins/962-cylinder-head-f0/source/prepare_head_analysis.py": "cda8f7155a8c22ab66898f07d1ad452ba5384ad7f75a1f012606685cd8a12dc3",
    "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-001/candidate.bin": "9d62eac6e2cd7b6a9ecb4a7ea5b632685820369b5c4ede379acc34238f50d7b4",
    "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-admission-evidence-map-001/evidence-map.json": "8b9138e3926b67ba0a9aa194343c6bc03f9d6d802c8d50e66403437922d7c642",
    "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-delaunay-default-postexport-prep-001/held-preparation.json": "d69426982c70aa5cc752ef7b789083e5ef9746bd7c118ca32fcb8b1a44bace4b",
    "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-delaunay-default-postexport-prep-001/mesh_delaunay_postexport.py": "ebb1f1ba8e7c0b032a4eb0178bbf8c332c68070816e6626f4a3f4788ed638527",
    "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-delaunay-default-postexport-prep-001/source-delta.json": "dae70175aee97477a7d05d0ce1af764cecd9a5935299cb8f6b3b398dc491f76b",
    "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-delaunay-optimized-diagnosis-001/execution-receipt.json": "34f889f05dba39c4e77156da2c5a79503849c8c5d8b79bfd24e6492634935c59",
    "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-delaunay-optimized-diagnosis-001/readback-report.json": "7025fa9460b566d01dfa197e887e133c24cd494fd2bc2ad789ddd0a372041822",
    "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-delaunay-optimized-diagnosis-result-peer-001/review.json": "62e7a92f94ed18dc4be493273f19ed0b360b994f920561b14aff2f8314dec317",
    "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-delaunay-optimized-diagnosis-root-execution-001/execution.json": "2d4c66a3c50255e29220748f784737304600346822618e35915675781a6b740a",
    "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-delaunay-prep-001/METHOD.md": "00291518ca550fdf4b4445935f5681b36d08bc7ca71917275479ac007de358bc",
    "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-delaunay-prep-001/hxt-to-delaunay.diff": "4e67682e699884dc824683bfb9d754f5c79fe8404b87802ed597c221e1ac00d5",
    "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-delaunay-prep-001/mesh_assembled_delaunay.py": "a3268687edc90b0149775cf5d80a89df82175cc982bbf5d7184b6ea8935be8a4",
    "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-delaunay-prep-001/source-delta.json": "313eff8c23448e105e71e7ea4133df6c4d520ecd53a789745c7a168f2a05b213",
    "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-distance-001/original-changed-to-complete-assembled/worker-report.json": "d89d132bc66889456aee27b399314ad3ac25bf862669272b8fd27c2b0b56cf77",
    "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-distance-cgal-assessment-001/assessment.json": "c6efca4861fe60774ad0a2421ebc4ea087474554181144a9f91ed2f92d9d9a46",
    "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-distance-cgal-assessment-001/execution.json": "0531952f508dce0577e5842f5e59fc67638c00ebbb29c3d1a7b8fd436d3372d4",
    "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-distance-cgal-assessment-execution-prep-001/actual-contract-001.json": "d0e3f4de54a1822e76495286b926ae0d2dd8bf294dae0b32034e08092e12600a",
    "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-distance-cgal-assessment-prep-001/held-preparation.json": "d669384396939f76d78c421c46bb88acbaba43801d2b5753a9399c275c4b3016",
    "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-distance-cgal-assessment-result-peer-001/review.json": "5815f2a62c7aa5dfd83b6a4d9aa5eb763184bd14245e80c2c621889c5ebc9255",
    "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-distance-cgal-cap-001/assembled-cap-to-complete-original/report.json": "44171f8cd47576405cf252746a609ebf234cc08aadeae00e1ba98e1265852610",
    "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-distance-cgal-noncap-001/assembled-noncap-to-complete-original/report.json": "a41b6a2eb07ebcea8356da7034a2bf6126cd768fc8b643689e7ca6a38d601e02",
    "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-feature-continuity-001/report.json": "502d89596fc38114625eab0c4cd89eb9f62a624744d234987d57cbe67ed356ab",
    "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-feature-continuity-result-peer-001/review.json": "16739cf5338d16f9a32ae9d56551be0716544ea0f60edab0b1465f00642fb115",
    "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-feature-continuity-root-result-001/review.json": "5ea562be46118da206644c8578b48b9876d166409aa60bdea90009f1f38a372c",
    "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-hxt-prep-002/held-contract.json": "4109be3e882e626e6db4bcd90ee70a8b52e124f6a4454e44c0b21227b0aec210",
    "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-hxt-prep-002/mesh_assembled_hxt.py": "b7d3de89c6ed166bb5d0df5c5d41ddd77b8deee9c36775b4e40b205722a2587e",
    "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-hxt-prep-002/test_hxt_guards.py": "6a6743e7c98579d8411b38505bf722cbb7f79e97d5e414bc588d4bc4b36d1b95",
    "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-hxt-root-source-002/guard-tests.log": "5efcf82c784dd8402a511fa688bf2c7c103f9a26af77283d7e2432d4b63f2258",
    "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-hxt-root-source-002/review.json": "d382320f903b4735d0f0a4b1baf1a2fee49c1c888550d0a3c756f15d11982f86",
    "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-hxt-runtime-preflight-001/preflight.json": "eb6998bb376b1c3e7f214e29b14a26170c3284727bd73e36d6e7ba5b5aa2a0ed",
    "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-netgen-capability-001/preflight-failure.json": "8e354ac996ade54f1538d415f58421ff3a51c2c4000fddbf812b0a8eea845393",
    "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-netgen-capability-002/capability.json": "1bd1b8da7a059c33b63ca2c9f17331203266956ba63f3d0950cd497619dcfec5",
    "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-netgen-cube-fixture-001/arrays.json": "ea9e6ccdc8d735c3fde2401dfba56f3c29ceece8c6945438bebb611b2f0287f6",
    "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-netgen-cube-fixture-001/cube.msh": "0db89b0cf7b4e57af1c6a091d999a7f521cd365f052f699a1798f05ba75eb92d",
    "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-netgen-cube-fixture-001/execution-receipt.json": "b129d3204391d4f84c8eefa33ab64009ab08b869381006551d874c97fe300219",
    "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-netgen-cube-fixture-001/fixture-report.json": "7d6f638b20388348810ea564e6fa7ffcdd2c5555fcbdc6d0d2c792e3d42defb7",
    "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-netgen-cube-fixture-001/frozen-contract.json": "fa329ed86bfb1e431987485f13307759001b09ac66fc8602a93fba9e4d0885b8",
    "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-netgen-cube-fixture-001/native.log": "3e8b937194c6b94ca3ec18f800a45d3dfbd2133b3766e5e279a7a1943bcf07c3",
    "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-netgen-cube-fixture-001/reader.py": "97b7e9fc7d17defa84594c50dac1d4e09cd39bb47ef2059e00b6ac07fe8c029b",
    "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-netgen-cube-fixture-001/run_readback.py": "f7165620ac95b9095969b21ae912e87d491019e295a62155abbf33c2eb3b2944",
    "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-netgen-cube-prep-002/METHOD.md": "6fe769f42f54ac50fdf2f2ba5d280003e4602fbb2f367139aa937e4f418fb390",
    "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-netgen-cube-prep-002/fixture-tests001-to002.diff": "98456dc8d343b3cf0d551f6a89db6367aa5247fbde77bbfe9bb6bc704493980e",
    "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-netgen-cube-prep-002/held-contract.json": "d3abc4ee9cda1d978b02ce7713aee2cd9a391616f67ea3f997f512a48b3ba570",
    "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-netgen-cube-prep-002/inspect-source.diff": "a52bb77d173ad1e07753ad8ee0c1a1a6e9d21f354234d8e71cf66582f2f29df1",
    "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-netgen-cube-prep-002/inspect-transform.json": "42c265f53b6e3417088c0ae6c3030acacf3829adb558d46f45575d33514f90b0",
    "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-netgen-cube-prep-002/reader.py": "97b7e9fc7d17defa84594c50dac1d4e09cd39bb47ef2059e00b6ac07fe8c029b",
    "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-netgen-cube-prep-002/reader001-to002.diff": "7c1d6e6dc60146f51c7a8958167da6ea13dd351a8ccbbd5c2679a2fd9e103fc8",
    "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-netgen-cube-prep-002/run_readback.py": "f7165620ac95b9095969b21ae912e87d491019e295a62155abbf33c2eb3b2944",
    "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-netgen-cube-prep-002/runner-source.diff": "65a83c80ef150ddc4170951ea8ddb71201abd64e3c4c0d62420a774fd67f7bc5",
    "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-netgen-cube-prep-002/runner-tests-transform.json": "9648c884d37a406b138958767fd239ebab881564091d66d4f76c898dd3148d9e",
    "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-netgen-cube-prep-002/runner-tests.diff": "8c138012f5bc1389c5bc4786d069c755051e9bf1a5f3ce4bb8dd068d1aed1652",
    "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-netgen-cube-prep-002/runner-transform.json": "a5454ddc09b42fb04367c94516a2f8df814430ce4f8715f172cbecbf7d9c3f26",
    "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-netgen-cube-prep-002/source-delta.json": "90be2a50f206a74f80f68dae5c06c89004cc0fa79c6807ead56ef20438fa97ec",
    "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-netgen-cube-prep-002/test_fixture_guards.py": "6884045c3e39ee2d9222d97ba82e9b244e16281c2029021f96fa5171d02961c0",
    "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-netgen-cube-prep-002/test_runner_guards.py": "da7af8d29cd24a092b5f33bd4ccc402b1e57a8334738a4c917cdd72fe494140b",
    "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-netgen-cube-result-peer-001/review.json": "cc1e1c3b830d0a735161045b755fc0eaa01036a20b09731f9cad8a28e3c83b0c",
    "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-netgen-cube-root-execution-001/controller.log": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-netgen-cube-root-execution-001/execution.json": "d1046708e9c0917f073252b45fb4ee3d243207a5753f2d2d387050c10a5c3158",
    "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-netgen-cube-root-execution-001/launch-guard.json": "938fc5069b83aa752ae76b3cd5ef99bf84aed97588609b6604931f74e4a73432",
    "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-netgen-cube-root-execution-001/preexec.json": "040054ca64d8b16a45b1fa1c806ac05901b07068465a102e2e6e6fdf03d5cea5",
    "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-netgen-cube-root-source-002/review.json": "c43e99ecec0034e7df9719a4914ac9e35d967c422a1e9def9c0f7178da00b404",
    "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-netgen-cube-root-source-002/test_fixture_guards.log": "2d5a18dc307eff4ca392dc277d73153d69105835866a09848621635d761fb7fa",
    "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-netgen-cube-root-source-002/test_runner_guards.log": "83f54c6a1a1521e255d1edc41cdb4ea5cec8de31290df0d0e74485797b7d2ad6",
    "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-netgen-cube-source-peer-001/review.json": "f5400679465373b9f21de18831bdf19095688cdda2fc460048ea6d9e87760811",
    "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-netgen-cube-source-peer-002/review.json": "a48b75dc9e92fde375f91ec823fa90f4c534b726c20c328e42f57fd3452e7136",
    "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-netgen-route-study-001/NOTE.md": "8c7e3885f6b89942fd1211c7bdf8a69a9a8b2b4748c8f76daed250065e1c7e71",
    "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-netgen-route-study-001/sources.json": "f71182583a3684383410120794c31954a620d48abc119f46fa6bada1459cbf44",
    "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-openings-001/worker-report.json": "77b120533dfab6f9631b3e74cabf81ece1bdc9227eb3bde4d1bcf40b7075679a",
    "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-openings-result-peer-001/review.json": "2ebe8b95119c501e9cd9457ea273626f3bdda28f3d9a3ed5fbf8ef985787a861",
    "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-openings-root-result-001/review.json": "cfdbb5cf2608d0ef81b733c5e444bf8017663f44f3e999dbe7857f942200829e",
    "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-publication-prep-001/payload-final-001/provenance.json": "4fca9349958c12657da46020da0be90de5804075d6a3f9aa22976eb885dbcb1c",
    "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-publication-prep-001/payload-final-001/receipt.json": "06129545751bcce517fce11dfc0ec6e8bfd79926ce0217578fe6b22558e3cd95",
    "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-publication-prep-001/payload-final-001/status.json": "d91e474f0c3d014321d5fee368b2111e957a6cdf514e5c992b35f1c48f1d65cb",
    "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-result-peer-001/review.json": "4498c149823907ddd46830f7dc582dc65b935d39f25b2b5053393eb34770c0ca",
    "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-surface-admission-001/surface-admission.json": "035c45d02357c9b7375a8e7795f7c1915d7e015ee2b63b576cf181965c96d962",
    "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-topology-001/worker-report.json": "c94abc0968927a622d88dfe4a3f957533159f8a9dd67b7326b1f6400a9b781e6",
    "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-topology-result-peer-001/review.json": "46555605376ad11923f716e84d11ac74ddc8c7c36a567a5acf9c26d28b7e5e18",
    "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-volume-delaunay-default-postexport-001/head-volume.msh": "e32ef35be1171ec55477e921dd75def0066f9f1e21bd2821dfbe363270354522",
    "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-volume-delaunay-default-postexport-001/receipt.json": "4f74e8688434df5032c1c5a050593e0f6d6e965010921a9f881a66b300e6f64d",
    "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-volume-delaunay-default-postexport-001/source-snapshots/audit_quality_head.py": "a298270aa00b1536314a07629b935500c68883ca0d3bd1a179d71b49a8e73991",
    "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-volume-delaunay-default-postexport-001/source-snapshots/audit_quality_patch.py": "3532a172b2bce3a8ead7c8b11b712a2b55891377726fa1b6d847e84f0eed3912",
    "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-volume-delaunay-default-postexport-001/source-snapshots/mesh_assembled_delaunay.py": "a3268687edc90b0149775cf5d80a89df82175cc982bbf5d7184b6ea8935be8a4",
    "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-volume-delaunay-default-postexport-001/source-snapshots/mesh_delaunay_postexport.py": "ebb1f1ba8e7c0b032a4eb0178bbf8c332c68070816e6626f4a3f4788ed638527",
    "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-volume-delaunay-default-postexport-001/source-snapshots/mesh_head.py": "69c8012e99057e384d44d6971d41f0e2cc7197a978120a7c566b0ad5a6477da5",
    "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-volume-delaunay-default-postexport-001/source-snapshots/prepare_head_analysis.py": "cda8f7155a8c22ab66898f07d1ad452ba5384ad7f75a1f012606685cd8a12dc3",
    "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-volume-delaunay-default-postexport-001/surface-admission.json": "035c45d02357c9b7375a8e7795f7c1915d7e015ee2b63b576cf181965c96d962",
    "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-volume-delaunay-default-postexport-001/worker-report.json": "655156e62ab6b7a13dca690a8c7523b09dbe81c591ebdef0e608e43bd769e7d9",
    "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-volume-hxt-001/receipt.json": "90fa2fc6e5a9a393a5a65464b2b2ac3ecc7c6ccf6e44000873d2dcb5a7ea3d6a",
    "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-volume-hxt-001/worker-report.json": "9a648b8082e84361759b38be30fcbf641417dbc5ccb0bf77b4d22254a7818bd7",
    "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-volume-poorcell-diagnosis-001/readback-report.json": "43152e18bc2b8de81b88f0677425f6254ec2d47496da5aad0e024a23fbeac3db",
    "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-volume-poorcell-diagnosis-root-execution-001/execution.json": "725e5b870c5eda2065157148bdec5836092bd3598463690b2e30d5504484fb23",
    "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-volume-readback-001/readback-report.json": "29546d1f4002f9c81d6b32d9f942493b27d2723fafc488f859e9c8dbf1471b00",
    "work/962-engineering/atomic-cavity-plane-clip-cap-assembly-volume-readback-result-peer-001/review.json": "80f6dc3171c4add180aa73b28f7f25b90384c23a3ec9e474b27d95d8cbf436a9",
    "work/962-engineering/atomic-cavity-plane-clip-cap-census-001/readback-report.json": "f246f1ef38a7657bd9eefc2349391cb31ab4a2147656743bb99c790c12d52a7d",
    "work/962-engineering/atomic-cavity-plane-clip-cap-census-result-peer-001/review.json": "fa5b363375236fb24ba8c9382bcf61da44ca39b63549a96ab0bd7b559a1b57c3",
    "work/962-engineering/atomic-cavity-plane-clip-cap-native-quality-head-001/assembled-head/report.json": "325d5d33e1c01a9ace216cc08472c157219e0fbda5efa9e12d7bd5b77c19ebb1",
    "work/962-engineering/atomic-cavity-plane-clip-cap-native-quality-head-result-peer-001/review.json": "9f2a2196b131e2f97ad61f3b280fc109bc70cd0ff62301c717eb2bbc13608e4d",
    "work/962-engineering/atomic-cavity-plane-clip-cap-native-quality-head-root-001/review.json": "dab4410a69ad0f4a2c994d7fa073278eafc6b257039dd05ea29d24aa74b3ca4e",
    "work/962-engineering/indexed-volume-001/native.log": "97d3449e730851fa782346bbc63d74832fca109faab9f83a0e795a0677ff79c8",
    "work/962-engineering/indexed-volume-001/receipt.json": "f0d66023544ae7bfed42b9e913d188b5f018ad8f7b6221a65c7b5bc64ade3d33",
    "work/962-engineering/indexed-volume-001/source-executed.py": "80a6b8527ba407afe4879ace2f4bed3e2f60595c3670cc934178ec6927b8182b",
    "work/962-engineering/indexed-volume-001/worker-report.json": "56946223af63e4eb8b09992e3d3417f968c9384e5d7a6b654e4e0ac5de12d363"
}


def require_inputs():
    if not INPUT_HASHES:
        raise ValueError("Complete fixed head and cube evidence bindings required")
    for name, expected in INPUT_HASHES.items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest() != expected:
            raise ValueError("Bound head optimizer input or software evidence changed")


def configure_core():
    if hashlib.sha256(CORE_PATH.read_bytes()).hexdigest() != CORE_SHA256:
        raise ValueError("Exact reviewed frozen quality-volume controller required")
    require_inputs()
    spec=importlib.util.spec_from_file_location("_962_frozen_postexport_core",CORE_PATH)
    core=importlib.util.module_from_spec(spec);spec.loader.exec_module(core)
    sources=tuple(core.source_files());original_save=core.save;original_admission=core.require_admission
    if len(sources)!=5 or sources[0]!=CORE_PATH:
        raise ValueError("Original controller and its four source imports required")
    def require_bound_admission(path,digest):
        require_inputs()
        if path.resolve()!=ADMISSION.resolve() or digest!=ADMISSION_SHA256:
            raise ValueError("The fixed original surface-admission receipt is required")
        return original_admission(path,digest)
    def save_postexport(path,report):
        report["postexport_companion"]=dict(frozen_core_sha256=CORE_SHA256,
            wrapper_source_sha256=hashlib.sha256(WRAPPER_PATH.read_bytes()).hexdigest(),
            input_sha256s=INPUT_HASHES,optimization=dict(method="Netgen",force=True),
            geometry_creation_dim_tags=[[3,1]],volume_only_geometry_flag=True,
            interior_recreation_and_retagging_permitted=True,
            interior_ancestry_or_physical_topology_change_inferred=False,
            stronger_Mesh2_admitted=False,
            mesh_generation_called=False,API_niter_limits_backend=False,
            cache_refresh="rebuildElementCache(False): lookup repair, no geometry change",
            Gamma_threshold_is_not_SICN=True,actual_minimum_SICN_gate_unchanged=.1,
            cube_success_is_not_head_acceptance=True)
        original_save(path,report)
    core.__file__=str(WRAPPER_PATH)  # Both controller and worker re-enter this wrapper.
    core.source_files=lambda:[WRAPPER_PATH,*sources]
    core.OUTPUT=OUTPUT;core.OPTIONS=dict(OPTIONS);core.DEADLINE=DEADLINE
    core.require_admission=require_bound_admission;core.save=save_postexport
    core.worker=lambda args:worker(core,args)
    return core


def classifications(core,gmsh,node_tags,boundary_count):
    np=core.np;dimensions=np.full(len(node_tags),-1,dtype=np.int8)
    entity_tags=np.zeros(len(node_tags),dtype=np.int64);periodic=[]
    for dim,tag in gmsh.model.getEntities():
        if dim in (1,2):
            masters=gmsh.model.mesh.getPeriodic(dim,[tag])
            master,nodes,node_masters,transform=gmsh.model.mesh.getPeriodicNodes(dim,tag,True)
            if list(masters)!=[tag] or master!=tag or len(nodes) or len(node_masters) or len(transform):
                raise ValueError("Curve/surface periodic mappings are forbidden")
            periodic.append([dim,tag])
        tags=np.asarray(gmsh.model.mesh.getNodes(dim,tag,False,False)[0])
        indices=np.searchsorted(node_tags,tags)
        if (len(np.unique(tags))!=len(tags) or np.any(indices>=len(node_tags))
                or not np.array_equal(node_tags[indices],tags) or np.any(dimensions[indices]!=-1)):
            raise ValueError("Unique complete node classification required")
        dimensions[indices]=dim;entity_tags[indices]=tag
    boundary=node_tags<=boundary_count
    if (np.any(dimensions<0) or np.count_nonzero(boundary)!=boundary_count
            or np.any(dimensions[boundary]>=3) or np.any(dimensions[~boundary]!=3)):
        raise ValueError("Fixed boundary nodes must classify below dim3 and interior nodes at dim3")
    return dict(node_classification_dimensions_sha256=core.array_sha(dimensions),
        node_classification_entity_tags_sha256=core.array_sha(entity_tags),
        boundary_node_classification_dimensions_sha256=core.array_sha(dimensions[boundary]),
        boundary_node_classification_entity_tags_sha256=core.array_sha(entity_tags[boundary]),
        node_counts_by_classification_dimension={str(d):int(np.count_nonzero(dimensions==d)) for d in range(4)},
        no_curve_or_surface_periodic_mapping=True,periodic_query_dimensions=[1,2],periodic_entities_checked=periodic)


def array_identity(core,state):
    return dict(zip(("sorted_coordinates_sha256","sorted_node_tags_sha256",
        "sorted_tetra_tags_sha256","tagged_tetra_connectivity_sha256"),map(core.array_sha,state)))


def current_after_proof(worker,receipt,diagnosis,candidate_sha):
    """The sole current optimized worker.after plus its completed saved-file diagnosis."""
    if (receipt.get("returncode")!=2 or receipt.get("stop_reason") is not None
            or receipt.get("bound_inputs_unchanged") is not True or receipt.get("worker_report")!=worker
            or worker.get("optimizer_returned") is not True or worker.get("element_cache_refresh_completed") is not True
            or worker.get("saved_mesh_identity_exact") is not True or worker.get("bound_inputs_unchanged") is not True
            or receipt.get("mesh_sha256")!=INPUT_HASHES[str(INPUT.relative_to(ROOT))]
            or worker.get("mesh_sha256")!=receipt.get("mesh_sha256")
            or receipt.get("mesh_bytes")!=243246094 or worker.get("mesh_bytes")!=243246094
            or worker.get("candidate_sha256")!=candidate_sha
            or diagnosis.get("status")!="direct_saved_file_readback_completed"
            or diagnosis.get("bound_inputs_unchanged") is not True
            or diagnosis.get("single_optimized_worker_proof")!={"worker_report_sha256":INPUT_HASHES[INPUT_WORKER],"field":"after","independent_prior_reader_alias_used":False}
            or diagnosis.get("direct_counts_metrics_and_positive_poor_total_match_single_worker_after") is not True):
        raise ValueError("Single current optimized worker.after and completed diagnosis required")
    proof=worker["after"]
    if (proof["tetrahedra"],proof["total_mesh_nodes"],proof["tetra_referenced_interior_nodes"],proof["unreferenced_mesh_nodes"])!=(3802217,1104778,233047,0):
        raise ValueError("Exact current 3802217/1104778/233047 baseline required")
    for observed,expected in [("actual_mesh_nodes","total_mesh_nodes"),("actual_tetrahedra","tetrahedra"),
            ("actual_tetra_referenced_nodes","tetra_referenced_nodes"),("actual_unreferenced_mesh_nodes","unreferenced_mesh_nodes"),
            ("actual_referenced_interior_nodes","tetra_referenced_interior_nodes")]:
        if diagnosis[observed]!=proof[expected]:raise ValueError("Current diagnosis count differs from worker.after")
    for key,value in proof["array_sha256s"].items():
        if diagnosis[key]!=value:raise ValueError("Current diagnosis tagged array differs from worker.after")
    for observed,expected in [("SICN","minimum_SICN"),("Jacobian","minimum_jacobian"),("native_volume_mm3","native_volume_mm3")]:
        if any(diagnosis["direct_native_quality_extrema"][observed].get(k)!=v for k,v in proof["quality"][expected].items()):
            raise ValueError("Current diagnosis native metric differs from worker.after")
    signed=diagnosis["independent_signed_volume_mm3"]
    if (any(signed[k]!=v for k,v in proof["quality"]["independent_signed_volume_mm3"].items())
            or signed["sum"]!=proof["summed_tetra_volume_mm3"]
            or signed["relative_error_to_candidate"]!=proof["volume_relative_error"]
            or diagnosis["positive_poor_SICN_cells"]["total"]!=3438
            or proof["quality"]["minimum_SICN"]["below_point1_count"]!=3438
            or any(row["nonpositive_count"] for row in proof["quality"].values())):
        raise ValueError("Current signed-volume and 3438-positive-poor baseline required")
    return proof


def boundary_identity(core,state,points,classification):
    """Exact source-tag/binary64 boundary identity; interior tags are unrestricted."""
    np=core.np;q,nt,_,_=state;expected=np.arange(1,len(points)+1,dtype=nt.dtype)
    ix=np.searchsorted(nt,expected)
    if (np.any(ix>=len(nt)) or not np.array_equal(nt[ix],expected)
            or np.ascontiguousarray(q[ix]).tobytes()!=np.ascontiguousarray(points).tobytes()):
        raise ValueError("Bitwise original boundary coordinates and exact source tags required")
    return dict(source_boundary_nodes=len(points),source_node_tags_sha256=core.array_sha(expected),
        source_coordinate_bits_sha256=core.array_sha(q[ix]),
        classification_dimensions_sha256=classification["boundary_node_classification_dimensions_sha256"],
        classification_entity_tags_sha256=classification["boundary_node_classification_entity_tags_sha256"],
        no_curve_or_surface_periodic_mapping=classification["no_curve_or_surface_periodic_mapping"],
        periodic_entities_checked=classification["periodic_entities_checked"])


def require_boundary_continuity(before,after):
    if before!=after:
        raise ValueError("Original boundary tags, coordinate bits, classifications or periodic identity changed")


def load_before(core,gmsh,points,faces):
    worker=json.loads((ROOT/INPUT_WORKER).read_text());receipt=json.loads((ROOT/INPUT_RECEIPT).read_text())
    diagnosis=json.loads((ROOT/INPUT_READBACK).read_text())
    proof=current_after_proof(worker,receipt,diagnosis,core.CANDIDATE_SHA)
    state,fresh=audit_after(core,gmsh,points,faces)
    for key,value in proof.items():
        if key=="classifications":
            if any(fresh[key].get(k)!=v for k,v in value.items()):
                raise ValueError("Fresh baseline classifications differ from worker.after")
        elif fresh.get(key)!=value:
            raise ValueError("Fresh full baseline audit differs from worker.after: "+key)
    identity=boundary_identity(core,state,points,fresh["classifications"])
    report=dict(audit=fresh,source_boundary_identity=identity,
        single_worker_proof_path=INPUT_WORKER,single_worker_proof_sha256=INPUT_HASHES[INPUT_WORKER],
        single_worker_field="after",completed_saved_diagnosis_path=INPUT_READBACK,
        completed_saved_diagnosis_sha256=INPUT_HASHES[INPUT_READBACK],
        older_first_pass_reader_alias_used=False,fresh_full_input_incidence_and_metrics_completed=True,
        prior_diagnosis_repeated_incidence=False,input_baseline_SICN_point1_passed=False)
    return state,report


def geometry_flag_only(core,gmsh,points,faces,before,report,checkpoint):
    if gmsh.model.getEntities(3)!=[(3,1)] or not gmsh.model.getBoundary([(3,1)],oriented=True,recursive=False):
        raise ValueError("Exactly one volume(3,1) with a nonempty bounding shell required")
    report.update(stage="volume_only_geometry_flag",geometry_creation_call_count=1);checkpoint()
    gmsh.model.mesh.createGeometry([(3,1)])
    state,fresh=audit_after(core,gmsh,points,faces)
    identity=boundary_identity(core,state,points,fresh["classifications"])
    if fresh!=before["audit"] or identity!=before["source_boundary_identity"]:
        raise ValueError("Volume-only geometry flag changed full arrays, classifications or metrics")
    report.update(after_geometry_flag=dict(audit=fresh,source_boundary_identity=identity),
        geometry_flag_full_tagged_arrays_classifications_and_quality_identity_exact=True)
    checkpoint()

def optimize_and_refresh(gmsh,report,checkpoint):
    report.update(stage="calling_Netgen_postexport_optimizer",optimizer_call_count=1)
    checkpoint()
    gmsh.model.mesh.optimize(method="Netgen",force=True)
    report.update(optimizer_returned=True,stage="refreshing_element_lookup_cache")
    checkpoint()
    # False forces rebuilding even if the pre-optimization cache is populated.
    # Gmsh4.15.2 GModel.cpp2046-2082: this changes lookup pointers, not the mesh.
    report["element_cache_refresh_count"]=1
    gmsh.model.mesh.rebuildElementCache(False)
    report.update(element_cache_refresh_completed=True,
                  stage="optimizer_returned_and_element_cache_refreshed")
    checkpoint()


def audit_after(core,gmsh,points,faces):
    np=core.np;q,cells,nt,et,en=core.tagged_volume(gmsh);state=(q,nt,et,en)
    referenced=np.unique(en)
    if (len(np.unique(nt))!=len(nt) or len(np.unique(et))!=len(et)
            or not np.array_equal(referenced,nt)):
        raise ValueError("Unique tagged nodes/cells and no orphan mesh nodes required")
    report=dict(surface=core.surface_roundtrip(gmsh,points,faces,exact_tagged_order=False),
        classifications=classifications(core,gmsh,nt,len(points)),tetrahedra=len(cells),
        total_mesh_nodes=len(nt),retained_boundary_nodes=len(points),tetra_referenced_nodes=len(referenced),
        tetra_referenced_interior_nodes=int(np.count_nonzero(referenced>len(points))),unreferenced_mesh_nodes=0,
        quality={},interior_node_count_establishes_thermal_resolution=False)
    for name,measure in [("minimum_jacobian","minDetJac"),("native_volume_mm3","volume"),("minimum_SICN","minSICN")]:
        values=np.asarray(gmsh.model.mesh.getElementQualities(et,measure))
        if len(values)!=len(et):raise ValueError("Every actual tetrahedron quality must be returned")
        report["quality"][name]={**core.distribution(values),"array_sha256":core.array_sha(values)}
        if measure=="minSICN":report["quality"][name]["below_point1_count"]=int(np.count_nonzero(values<.1))
    signed=core.tetra_volumes(q,cells)
    report["quality"]["independent_signed_volume_mm3"]=core.distribution(signed)
    if any(type(q.get("count")) is not int or q["count"] != len(cells) for q in report["quality"].values()):
        raise ValueError("Every metric distribution must cover every actual tetrahedron")
    report["summed_tetra_volume_mm3"]=math.fsum(signed)
    report["volume_relative_error"]=abs(report["summed_tetra_volume_mm3"]/core.CANDIDATE_VOLUME-1)
    report["actual_tetra_boundary"]=core.tetra_boundary(cells,np.searchsorted(nt,faces+1))
    report["internal_tetra_face_orientation"]=core.internal_face_orientation(cells)
    report["array_sha256s"]=array_identity(core,state)
    return state,report


def canonical_cells(np,nodes):
    ordered=np.sort(nodes,axis=1)
    return ordered[np.lexsort(ordered.T[::-1])]


def worker(core,args):
    launch=core.claim_worker(args);initialized=False;started=time.monotonic()
    path=args.output/"head-volume.msh"
    report=dict(status="running",stage="checking_runtime",geometry_creation_call_count=0,optimizer_call_count=0,
        optimizer_returned=False,element_cache_refresh_count=0,element_cache_refresh_completed=False,
        API_call_counters_record_attempts=True,options=OPTIONS,mesh_generation_called=False,
        candidate_sha256=core.CANDIDATE_SHA,candidate_volume_reference_mm3=core.CANDIDATE_VOLUME,
        volume_relative_bookkeeping_bound=1e-6,bookkeeping_bound_is_manufacturing_tolerance=False,
        qualification=dict(geometric_volume_gate_passed=False,
            mesh_convergence_established=False,thermal_resolution_established=False,engineering_accepted=False,
            thermal_performance_validated=False,strength_validated=False,manufacturing_authorized=False))
    checkpoint=lambda:core.save(args.output/"worker-report.json",report)
    try:
        import gmsh
        runtime=dict(python=sys.version,numpy=core.np.__version__,gmsh=gmsh.__version__,machine=platform.machine(),
            executable_sha256=core.sha(Path(sys.executable).resolve()),gmsh_module_sha256=core.sha(Path(gmsh.__file__)),
            libgmsh_sha256=core.sha(Path(gmsh.lib._name)))
        report["runtime"]=runtime
        if runtime != {'python': '3.10.11 (v3.10.11:7d4cc5aa85, Apr  4 2023, 19:05:19) [Clang 13.0.0 (clang-1300.0.29.30)]', 'numpy': '2.0.2', 'gmsh': '4.15.2', 'machine': 'arm64', 'executable_sha256': '72956ad35cff7691dfed9e04c9593de825ffd5b2fa7e8bc9ae96ce9a1af65621', 'gmsh_module_sha256': 'f4b0935cebde899750293d87a643090e5ea33c9b18d249267f507db68a0e01c3', 'libgmsh_sha256': 'def0f5c10988a986e5e879b3db9669d8fe016a81e2d994bbaf2b8497c6b8a58a'}:
            raise ValueError("Exact observed native Python/NumPy/Gmsh runtime required")
        points,faces=core.audit_quality_head.read(core.CANDIDATE)
        points,faces=core.np.asarray(points,dtype=core.np.float64),core.np.asarray(faces,dtype=core.np.int64)
        if (len(points),len(faces))!=(871731,1743878):raise ValueError("Admitted candidate counts changed")
        gmsh.initialize([],readConfigFiles=False,run=False);initialized=True
        gmsh.option.setNumber("General.Terminal",1);gmsh.logger.start()
        for key,value in OPTIONS.items():gmsh.option.setNumber(key,value)
        if "Netgen" not in gmsh.option.getString("General.BuildOptions").split():
            raise ValueError("Compiled Netgen capability token required")
        report.update(stage="loading_exact_saved_default_optimized_Delaunay_mesh");checkpoint()
        gmsh.open(str(INPUT));before,report["before"]=load_before(core,gmsh,points,faces)
        if any(gmsh.option.getNumber(k)!=v for k,v in OPTIONS.items()):raise ValueError("Fixed optimizer options changed")
        geometry_flag_only(core,gmsh,points,faces,report["before"],report,checkpoint)
        optimize_and_refresh(gmsh,report,checkpoint)
        gmsh.write(str(path));report.update(mesh_sha256=core.sha(path),mesh_bytes=path.stat().st_size,
                                           stage="auditing_all_optimized_tetrahedra");checkpoint()
        after,report["after"]=audit_after(core,gmsh,points,faces)
        report["after"]["source_boundary_identity"]=boundary_identity(core,after,points,report["after"]["classifications"])
        require_boundary_continuity(report["before"]["source_boundary_identity"],report["after"]["source_boundary_identity"])
        report["comparison"]=dict(total_nodes_before=len(before[1]),total_nodes_after=len(after[1]),
            referenced_interior_nodes_before=report["before"]["audit"]["tetra_referenced_interior_nodes"],
            referenced_interior_nodes_after=report["after"]["tetra_referenced_interior_nodes"],
            tetrahedra_before=len(before[2]),tetrahedra_after=len(after[2]),
            source_boundary_identity_unchanged=True,interior_recreation_retagging_and_count_changes_permitted=True,
            interior_ancestry_or_physical_topology_change_inferred=False,
            minimum_SICN_before_fresh=report["before"]["audit"]["quality"]["minimum_SICN"]["minimum"],
            minimum_SICN_after_actual=report["after"]["quality"]["minimum_SICN"]["minimum"])
        report["comparison"]["minimum_SICN_strictly_improved"]=(report["comparison"]["minimum_SICN_after_actual"]>
            report["comparison"]["minimum_SICN_before_fresh"])
        report["comparison"]["actual_SICN_point1_gate_passed"]=report["comparison"]["minimum_SICN_after_actual"]>=.1
        del before
        report.update(stage="reading_back_the_single_optimized_mesh");checkpoint()
        gmsh.clear();gmsh.open(str(path));q,_,nt,et,en=core.tagged_volume(gmsh)
        if (array_identity(core,(q,nt,et,en))!=report["after"]["array_sha256s"]
                or not core.matching_mesh(path,report["mesh_sha256"])):
            raise ValueError("Saved optimized tagged coordinates/connectivity or mesh bytes changed")
        report["saved_surface"]=core.surface_roundtrip(gmsh,points,faces,exact_tagged_order=False)
        if classifications(core,gmsh,nt,len(points))!=report["after"]["classifications"]:
            raise ValueError("Saved node classifications or periodic identity changed")
        require_boundary_continuity(report["after"]["source_boundary_identity"],
            boundary_identity(core,(q,nt,et,en),points,classifications(core,gmsh,nt,len(points))))
        report.update(saved_mesh_identity_exact=True)
        quality=report["after"]["quality"]
        if any(q["nonpositive_count"] for q in quality.values()) or quality["minimum_SICN"]["minimum"]<.1:
            raise ValueError("Positive finite Jacobians/volumes and actual minimum SICN at least 0.1 required")
        if report["after"]["volume_relative_error"]>1e-6:raise ValueError("Candidate-relative volume bookkeeping exceeds 1e-6")
        report.update(status="completed_geometric_volume_quality_only",stage="finished")
        report["qualification"]["geometric_volume_gate_passed"]=True
    except Exception as exc:report.update(status="failed_outputs_preserved",error=type(exc).__name__+": "+str(exc))
    finally:
        if initialized:
            try:
                report["gmsh_warnings_errors"]=[s for s in gmsh.logger.get() if s.startswith(("Warning","Error"))]
                gmsh.logger.stop()
            except Exception as exc:
                report.update(status="failed_runtime_cleanup",cleanup_error=type(exc).__name__+": "+str(exc))
                report["qualification"]["geometric_volume_gate_passed"]=False
            try:gmsh.finalize()
            except Exception as exc:
                report.update(status="failed_runtime_cleanup",finalize_error=type(exc).__name__+": "+str(exc))
                report["qualification"]["geometric_volume_gate_passed"]=False
        try:
            core.require_admission(args.admission,args.admission_sha256)
            report["bound_inputs_unchanged"]=(core.sha(args.output/"surface-admission.json")==args.admission_sha256
                and all(core.sha(ROOT/p)==h and core.sha(args.output/"source-snapshots"/Path(p).name)==h
                        for p,h in launch["source_sha256s"].items()))
        except Exception:report["bound_inputs_unchanged"]=False
        if not report["bound_inputs_unchanged"]:
            report.update(status="failed_bound_input_drift");report["qualification"]["geometric_volume_gate_passed"]=False
        if report["qualification"]["geometric_volume_gate_passed"] and not core.matching_mesh(path,report.get("mesh_sha256")):
            report.update(status="failed_saved_mesh_drift");report["qualification"]["geometric_volume_gate_passed"]=False
        report["worker_wall_s"]=time.monotonic()-started;checkpoint()
    return 0 if report["qualification"]["geometric_volume_gate_passed"] else 2


def main(argv=None):
    require_inputs();core=configure_core()
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--admission",type=Path,required=True);parser.add_argument("--admission-sha256",required=True)
    parser.add_argument("--output",type=Path,required=True);parser.add_argument("--worker",action="store_true",help=argparse.SUPPRESS)
    args=parser.parse_args(argv)
    if core.sha(Path(sys.executable).resolve())!=PYTHON_SHA256:raise ValueError("Selected native Python required")
    return core.worker(args) if args.worker else core.run(args)


if __name__=="__main__":raise SystemExit(main())
