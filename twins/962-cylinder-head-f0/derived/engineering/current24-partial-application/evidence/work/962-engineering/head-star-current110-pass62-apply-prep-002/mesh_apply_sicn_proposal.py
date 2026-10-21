"""Held fixed 62-pass/66-node coordinate application with a complete saved-head census.

Source preparation only. A separately admitted actual and owned native controller are required.
The complete head remains quality-rejected; no PDE, physical or manufacturing authority.
"""
import argparse
from fractions import Fraction
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
INPUT = ROOT / 'work/962-engineering/head-star-current126-alternative-combined-application-001/head-volume.msh'
INPUT_WORKER = 'work/962-engineering/head-star-current126-alternative-combined-application-001/readback-report.json'
INPUT_RECEIPT = 'work/962-engineering/head-star-current126-alternative-combined-application-001/execution-receipt.json'
INPUT_READBACK = 'work/962-engineering/head-star-current110-full-stars-001/readback-report.json'
ADMISSION = ROOT / 'work/962-engineering/atomic-cavity-plane-clip-cap-assembly-surface-admission-001/surface-admission.json'
ADMISSION_SHA256 = "035c45d02357c9b7375a8e7795f7c1915d7e015ee2b63b576cf181965c96d962"
OUTPUT = ROOT / "work/962-engineering/head-star-current110-pass62-application-001"
CENSUS = ROOT / 'work/962-engineering/head-star-current110-full-stars-001/readback-report.json'
CENSUS_SHA256 = "657fbb0ce1c89dbf691f5a07c62feedf0fd91f7bc78f21d2aa14a3e01a9566da"
SELECTION = ROOT / 'work/962-engineering/head-star-current110-pass62-apply-prep-002/selected-proposals.json'
SELECTION_SHA256 = '3af57b7644901c8755f51286571f9b9cf32bcde2bcf23191c344401ffade2e6f'
APPLICATION_BINDING = ROOT / "work/962-engineering/head-star-current110-pass62-apply-execution-prep-001/actual-contract.json"
COMPONENT_MANIFEST = ROOT / 'work/962-engineering/head-star-current110-component-sicn-prep-001/component-manifest.json'
RESULT_ACCEPTANCE = ROOT / 'work/962-engineering/head-star-current110-component-sicn-root-execution-001/result-peer-acceptance.json'
RESULT_PEER = ROOT / 'work/962-engineering/head-star-current110-component-sicn-result-peer-001/review.json'
RESULT_BINDINGS = ROOT / 'work/962-engineering/head-star-current110-component-sicn-result-peer-001/bindings.json'
PASS_IDS = [1, 3, 4, 5, 6, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 22, 23, 24, 25, 26, 27, 29, 32, 33, 34, 35, 36, 37, 38, 40, 41, 42, 43, 44, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 69, 70, 71, 72, 73]
REJECTED_IDS = [2, 7, 8, 9, 10, 21, 28, 30, 31, 39, 45]
SELECTED_TAGS = [1393275, 1393281, 1421336, 1424314, 1432342, 1433502, 1441004, 1441011, 1441012, 1441013, 1442335, 1450443, 1458419, 1459063, 1459064, 1459592, 1459940, 1459941, 1460416, 1460612, 1470654, 1474771, 1481857, 1502469, 1504163, 1506129, 1506140, 1512157, 1512642, 1514912, 1527816, 1528968, 1534574, 1535650, 1548247, 1549365, 1549366, 1552068, 1555697, 1555743, 1555744, 1558090, 1560546, 1573898, 1585373, 1585374, 1585378, 1596472, 1606005, 1608113, 1610627, 1610628, 1611139, 1611467, 1611657, 1611658, 1611659, 1611943, 1612414, 1612796, 1612957, 1613513, 1613514, 1613588, 1613791, 1613798]
REJECTED_INITIAL_POOR = [28789125, 29366318, 29366445, 29367524, 29664233, 29664587, 29672503, 29672654, 29801902, 30103489, 30419427, 30419439, 31210046, 31211000, 31211001, 31211002, 31211003, 31251529, 31567572, 31580321, 31787912, 31905042, 32110904, 32124295]
NATIVE_RUNTIME_HASHES = {'runtime-role://registered-native/geometry/bin/python': '72956ad35cff7691dfed9e04c9593de825ffd5b2fa7e8bc9ae96ce9a1af65621', 'runtime-role://registered-native/geometry/lib/libgmsh.4.15.dylib': 'def0f5c10988a986e5e879b3db9669d8fe016a81e2d994bbaf2b8497c6b8a58a', 'runtime-role://registered-native/geometry/lib/python3.10/site-packages/gmsh.py': 'f4b0935cebde899750293d87a643090e5ea33c9b18d249267f507db68a0e01c3', 'runtime-role://registered-native/numpy-environment/lib/python3.10/site-packages/numpy/__init__.py': 'c09e25b58f6b2f8e2cb3c158168f902d447f8171e5ea6513c0aca41ecbda7c2b'}
OPTIONS = {"General.NumThreads":2, "Mesh.MaxNumThreads3D":2, "Mesh.Renumber":0,
    "Mesh.Optimize":0, "Mesh.OptimizeNetgen":0, "Mesh.OptimizeThreshold":.3,
    "Mesh.Binary":1, "Mesh.SaveAll":1, "Mesh.MshFileVersion":4.1}
INPUT_HASHES = {'twins/962-cylinder-head-f0/source/audit_quality_head.py': 'a298270aa00b1536314a07629b935500c68883ca0d3bd1a179d71b49a8e73991', 'twins/962-cylinder-head-f0/source/audit_quality_patch.py': '3532a172b2bce3a8ead7c8b11b712a2b55891377726fa1b6d847e84f0eed3912', 'twins/962-cylinder-head-f0/source/mesh_head.py': '69c8012e99057e384d44d6971d41f0e2cc7197a978120a7c566b0ad5a6477da5', 'twins/962-cylinder-head-f0/source/prepare_head_analysis.py': 'cda8f7155a8c22ab66898f07d1ad452ba5384ad7f75a1f012606685cd8a12dc3', 'work/962-engineering/atomic-cavity-plane-clip-cap-assembly-001/candidate.bin': '9d62eac6e2cd7b6a9ecb4a7ea5b632685820369b5c4ede379acc34238f50d7b4', 'work/962-engineering/atomic-cavity-plane-clip-cap-assembly-admission-evidence-map-001/evidence-map.json': '8b9138e3926b67ba0a9aa194343c6bc03f9d6d802c8d50e66403437922d7c642', 'work/962-engineering/atomic-cavity-plane-clip-cap-assembly-delaunay-prep-001/mesh_assembled_delaunay.py': 'a3268687edc90b0149775cf5d80a89df82175cc982bbf5d7184b6ea8935be8a4', 'work/962-engineering/atomic-cavity-plane-clip-cap-assembly-distance-001/original-changed-to-complete-assembled/worker-report.json': 'd89d132bc66889456aee27b399314ad3ac25bf862669272b8fd27c2b0b56cf77', 'work/962-engineering/atomic-cavity-plane-clip-cap-assembly-distance-cgal-assessment-001/assessment.json': 'c6efca4861fe60774ad0a2421ebc4ea087474554181144a9f91ed2f92d9d9a46', 'work/962-engineering/atomic-cavity-plane-clip-cap-assembly-distance-cgal-assessment-001/execution.json': '0531952f508dce0577e5842f5e59fc67638c00ebbb29c3d1a7b8fd436d3372d4', 'work/962-engineering/atomic-cavity-plane-clip-cap-assembly-distance-cgal-assessment-execution-prep-001/actual-contract-001.json': 'd0e3f4de54a1822e76495286b926ae0d2dd8bf294dae0b32034e08092e12600a', 'work/962-engineering/atomic-cavity-plane-clip-cap-assembly-distance-cgal-assessment-prep-001/held-preparation.json': 'd669384396939f76d78c421c46bb88acbaba43801d2b5753a9399c275c4b3016', 'work/962-engineering/atomic-cavity-plane-clip-cap-assembly-distance-cgal-assessment-result-peer-001/review.json': '5815f2a62c7aa5dfd83b6a4d9aa5eb763184bd14245e80c2c621889c5ebc9255', 'work/962-engineering/atomic-cavity-plane-clip-cap-assembly-distance-cgal-cap-001/assembled-cap-to-complete-original/report.json': '44171f8cd47576405cf252746a609ebf234cc08aadeae00e1ba98e1265852610', 'work/962-engineering/atomic-cavity-plane-clip-cap-assembly-distance-cgal-noncap-001/assembled-noncap-to-complete-original/report.json': 'a41b6a2eb07ebcea8356da7034a2bf6126cd768fc8b643689e7ca6a38d601e02', 'work/962-engineering/atomic-cavity-plane-clip-cap-assembly-feature-continuity-001/report.json': '502d89596fc38114625eab0c4cd89eb9f62a624744d234987d57cbe67ed356ab', 'work/962-engineering/atomic-cavity-plane-clip-cap-assembly-feature-continuity-result-peer-001/review.json': '16739cf5338d16f9a32ae9d56551be0716544ea0f60edab0b1465f00642fb115', 'work/962-engineering/atomic-cavity-plane-clip-cap-assembly-feature-continuity-root-result-001/review.json': '5ea562be46118da206644c8578b48b9876d166409aa60bdea90009f1f38a372c', 'work/962-engineering/atomic-cavity-plane-clip-cap-assembly-openings-001/worker-report.json': '77b120533dfab6f9631b3e74cabf81ece1bdc9227eb3bde4d1bcf40b7075679a', 'work/962-engineering/atomic-cavity-plane-clip-cap-assembly-openings-result-peer-001/review.json': '2ebe8b95119c501e9cd9457ea273626f3bdda28f3d9a3ed5fbf8ef985787a861', 'work/962-engineering/atomic-cavity-plane-clip-cap-assembly-openings-root-result-001/review.json': 'cfdbb5cf2608d0ef81b733c5e444bf8017663f44f3e999dbe7857f942200829e', 'work/962-engineering/atomic-cavity-plane-clip-cap-assembly-publication-prep-001/payload-final-001/provenance.json': '4fca9349958c12657da46020da0be90de5804075d6a3f9aa22976eb885dbcb1c', 'work/962-engineering/atomic-cavity-plane-clip-cap-assembly-publication-prep-001/payload-final-001/receipt.json': '06129545751bcce517fce11dfc0ec6e8bfd79926ce0217578fe6b22558e3cd95', 'work/962-engineering/atomic-cavity-plane-clip-cap-assembly-publication-prep-001/payload-final-001/status.json': 'd91e474f0c3d014321d5fee368b2111e957a6cdf514e5c992b35f1c48f1d65cb', 'work/962-engineering/atomic-cavity-plane-clip-cap-assembly-result-peer-001/review.json': '4498c149823907ddd46830f7dc582dc65b935d39f25b2b5053393eb34770c0ca', 'work/962-engineering/atomic-cavity-plane-clip-cap-assembly-surface-admission-001/surface-admission.json': '035c45d02357c9b7375a8e7795f7c1915d7e015ee2b63b576cf181965c96d962', 'work/962-engineering/atomic-cavity-plane-clip-cap-assembly-topology-001/worker-report.json': 'c94abc0968927a622d88dfe4a3f957533159f8a9dd67b7326b1f6400a9b781e6', 'work/962-engineering/atomic-cavity-plane-clip-cap-assembly-topology-result-peer-001/review.json': '46555605376ad11923f716e84d11ac74ddc8c7c36a567a5acf9c26d28b7e5e18', 'work/962-engineering/atomic-cavity-plane-clip-cap-census-001/readback-report.json': 'f246f1ef38a7657bd9eefc2349391cb31ab4a2147656743bb99c790c12d52a7d', 'work/962-engineering/atomic-cavity-plane-clip-cap-census-result-peer-001/review.json': 'fa5b363375236fb24ba8c9382bcf61da44ca39b63549a96ab0bd7b559a1b57c3', 'work/962-engineering/atomic-cavity-plane-clip-cap-native-quality-head-001/assembled-head/report.json': '325d5d33e1c01a9ace216cc08472c157219e0fbda5efa9e12d7bd5b77c19ebb1', 'work/962-engineering/atomic-cavity-plane-clip-cap-native-quality-head-result-peer-001/review.json': '9f2a2196b131e2f97ad61f3b280fc109bc70cd0ff62301c717eb2bbc13608e4d', 'work/962-engineering/atomic-cavity-plane-clip-cap-native-quality-head-root-001/review.json': 'dab4410a69ad0f4a2c994d7fa073278eafc6b257039dd05ea29d24aa74b3ca4e', 'work/962-engineering/current126-alternative-combined-application-root-execution-001/closed-result.json': 'd2924e4080d0d28d304092e9d4656559f067728a14776248f38d8086710fdcad', 'work/962-engineering/current126-alternative-combined-application-root-execution-001/result-peer-acceptance.json': 'a0a889ab8b7ae77bcfcce4da464492eebf3472c782329a4dedc7252493c7ab46', 'work/962-engineering/fixed-shell-coupled-sicn-apply-prep-001/reader.py': '20a7d00f0b1f8a05a5ff09eefd86a647886556b9ce327a922beb8647f1b8cd0c', 'work/962-engineering/head-star-current110-component-0001-sicn-001/diagnostic.json': '132090dd03f5a123083e0145014392e0bfd7145368f5215c8da33755a79c5e4f', 'work/962-engineering/head-star-current110-component-0003-sicn-001/diagnostic.json': '50c11f9c39eaa3481bc0eb9e3e686eac67cadb1a326f9ac561ae048d07bbc5a8', 'work/962-engineering/head-star-current110-component-0004-sicn-001/diagnostic.json': '86916b72cf90e0ba44d568891423662f96b8a4e41245425eac551aa3dbe384e6', 'work/962-engineering/head-star-current110-component-0005-sicn-001/diagnostic.json': '9eae2d0585c62ddbaa280497cc2235b594d9fd628b9cc7fdf35573e831c368c5', 'work/962-engineering/head-star-current110-component-0006-sicn-001/diagnostic.json': '16a4951d4858d7145bafc5ac2f7d39c2cd4afbeadfb498195af533fac7fc4ada', 'work/962-engineering/head-star-current110-component-0011-sicn-001/diagnostic.json': 'ee2885a4a6fd3db3b620cd2081fe8dd9728b828c7aa5416d196af99588c49272', 'work/962-engineering/head-star-current110-component-0012-sicn-001/diagnostic.json': 'b9781f136940bb5bc099fe6ca2fc9a02bb07b1848aa87120d8e424d54a6bd43d', 'work/962-engineering/head-star-current110-component-0013-sicn-001/diagnostic.json': '53e514eded510d7a0ddd9ce0703a3dbccbf933f7dc947943575b755e8fe002e1', 'work/962-engineering/head-star-current110-component-0014-sicn-001/diagnostic.json': '531296efd22ca6b8612aa4a32ab3d5bf80c72e7fbb432332cb7d73256903e414', 'work/962-engineering/head-star-current110-component-0015-sicn-001/diagnostic.json': 'c730b6705e976ca75e87d3cb1f62b5efb3f3bfd8706e6921d51aaf3279a9dcb2', 'work/962-engineering/head-star-current110-component-0016-sicn-001/diagnostic.json': 'cde8e941043a07ef64fdadef6c5d1dc2784a29c7de08c1a1b9606983f05c0d8e', 'work/962-engineering/head-star-current110-component-0017-sicn-001/diagnostic.json': 'a94ef5067e9611f30aec1886b9c1e852cb84585716a20ccaecffc4072284b873', 'work/962-engineering/head-star-current110-component-0018-sicn-001/diagnostic.json': '267c2b2d04d2494e77559ada19a88b20c0288416421a177043849bedd1c72b65', 'work/962-engineering/head-star-current110-component-0019-sicn-001/diagnostic.json': '689b6c788030c38b164800fb7a71b39e392943137c8adc0de98f3650f781c874', 'work/962-engineering/head-star-current110-component-0020-sicn-001/diagnostic.json': '0ecb373512c96bc502415ab973f4dfdbcc8fce48d48a5c2e66958fa28b8dfabc', 'work/962-engineering/head-star-current110-component-0022-sicn-001/diagnostic.json': '1d46f55ee3ee9bf024790fd239e649f5152a2b883405340d1c787ed17ab0a2b9', 'work/962-engineering/head-star-current110-component-0023-sicn-001/diagnostic.json': 'd6637971389ec8a1a8e50348bfb46c90ad890cc7c5b91f24fa7d359a3e139013', 'work/962-engineering/head-star-current110-component-0024-sicn-001/diagnostic.json': '9c90df04aa363c3eafbdcad4276daea478820f5405b3106a85ee6efa5f3e0bce', 'work/962-engineering/head-star-current110-component-0025-sicn-001/diagnostic.json': 'b3a78468c72bc0087ef6288c6e37dd8676c1bd3cc037cd146083f8ee306549e5', 'work/962-engineering/head-star-current110-component-0026-sicn-001/diagnostic.json': 'd0454a5c4ece3ffaa5bd8eed9b05d850602c459a483e048823b09c44422db6bd', 'work/962-engineering/head-star-current110-component-0027-sicn-001/diagnostic.json': 'a898b3fb4014bf8981f93f9c2f4315f35d3a249cc9799f972e8a9f13d6621b12', 'work/962-engineering/head-star-current110-component-0029-sicn-001/diagnostic.json': 'cd6f793f4d9bf02ad2632a1041a637f4854a1c3b688fd288b554586493a199b1', 'work/962-engineering/head-star-current110-component-0032-sicn-001/diagnostic.json': '946eee8b5f265ed121864ea9b6577d6a977e7201f32dd7d178d6adcf7c64f710', 'work/962-engineering/head-star-current110-component-0033-sicn-001/diagnostic.json': 'f896a309e521e162292e620d56d5439bd3910c12c7f5c07997ca0f941877ed8b', 'work/962-engineering/head-star-current110-component-0034-sicn-001/diagnostic.json': '1f83aba84626e6c9baf3b2cf622851c1548ba6a89f699729ffb3882f5e445218', 'work/962-engineering/head-star-current110-component-0035-sicn-001/diagnostic.json': '473e1aea54ab0f8ddf40e51fdba15979fdf6c90f32b217c5b738668bb1bc9c11', 'work/962-engineering/head-star-current110-component-0036-sicn-001/diagnostic.json': 'c0c57237fb05c5ed596e8f912824c4d97e2ffc653d9274960527ef7bf15db8c4', 'work/962-engineering/head-star-current110-component-0037-sicn-001/diagnostic.json': 'ecc4a1998e58d57f7574eb477f2b4fcd9aa2c9b1acd0c6aa808c9b24d68ff4a9', 'work/962-engineering/head-star-current110-component-0038-sicn-001/diagnostic.json': '452d7c4e80c4d7aef9253388494558cae8f5aa077da21c09a3f697de412ba53a', 'work/962-engineering/head-star-current110-component-0040-sicn-001/diagnostic.json': '1d6fa2246859f658a108d3157a6454b0c907924e12b20f7859662b473bfcb8a8', 'work/962-engineering/head-star-current110-component-0041-sicn-001/diagnostic.json': '17471237a258031e69821da93688edccd19de109bf2ec27717246ba96bc934cc', 'work/962-engineering/head-star-current110-component-0042-sicn-001/diagnostic.json': '1617d59f79e41102938a45fa49a027683b158e4b255a0dc3747ce39452bfd153', 'work/962-engineering/head-star-current110-component-0043-sicn-001/diagnostic.json': 'c9b259f96083845b9f8684ea12be8011de57af50a4e8ca1388ff20bfbdc49e66', 'work/962-engineering/head-star-current110-component-0044-sicn-001/diagnostic.json': '7a900c1d95d87dfd32e498abb047835b27074ccc780a59db37273f601a067e91', 'work/962-engineering/head-star-current110-component-0046-sicn-001/diagnostic.json': 'e4f91755d4ecbb969d1be0a7c88c8472804213495b043d340f07d2acd0625911', 'work/962-engineering/head-star-current110-component-0047-sicn-001/diagnostic.json': '20bba36233117c0e9a8ca9c0567850cfc58bb2e3ee1f54fa9be5538445b442a7', 'work/962-engineering/head-star-current110-component-0048-sicn-001/diagnostic.json': '3739777d2500ad504c94f05cd320fa8222654250641041cad8efc32c748ec7d2', 'work/962-engineering/head-star-current110-component-0049-sicn-001/diagnostic.json': 'bd3e07241f0747ef69d7dfff908a0a578fdc8fe45bb36705b2294f056e991dbe', 'work/962-engineering/head-star-current110-component-0050-sicn-001/diagnostic.json': '59e34b6cd10756da81a9d623a1a7294d59a003a0d5d76377a8087cde826c24c1', 'work/962-engineering/head-star-current110-component-0051-sicn-001/diagnostic.json': '0252a7cfe7cb3713356b30b74bd6575455860f613b31362116a0f9f2d606c36e', 'work/962-engineering/head-star-current110-component-0052-sicn-001/diagnostic.json': 'daafc2049b9601fe0aaf50e2e9696700cabed180eb9ff849d10e9d9ca01c4942', 'work/962-engineering/head-star-current110-component-0053-sicn-001/diagnostic.json': '90dda01e6dcae4eac8202bbb2c006bfd7f94a999dc21e3b04e50a5c1bd1cd5e9', 'work/962-engineering/head-star-current110-component-0054-sicn-001/diagnostic.json': 'd76a3ba5c99e81a61352211edb1fa73e58541afbec5c03df00465880b87fd72e', 'work/962-engineering/head-star-current110-component-0055-sicn-001/diagnostic.json': '3814f65b7e9a4d613e8d67d6fe651f57ff1003f8d064647494d03825e2692330', 'work/962-engineering/head-star-current110-component-0056-sicn-001/diagnostic.json': 'd9c24b08465298435e364698f53e4f116651482ec7560ca0c0f36822545a13ce', 'work/962-engineering/head-star-current110-component-0057-sicn-001/diagnostic.json': '62a2f763fdc53975a133ab4032a8ae2076813af2fc783d0f69e36f60870f5afc', 'work/962-engineering/head-star-current110-component-0058-sicn-001/diagnostic.json': '97864f751ac6a129177059288ce898ab2f2337fc5b6aa06c3126747baf210917', 'work/962-engineering/head-star-current110-component-0059-sicn-001/diagnostic.json': 'a09d523c4653c6d78c94829c385fabd8587472e0e3a3822f665a6330cf6534c1', 'work/962-engineering/head-star-current110-component-0060-sicn-001/diagnostic.json': '99fc81b2b3064b2c81d732061ef2d85796c4e238705232f5aca7a945471eb482', 'work/962-engineering/head-star-current110-component-0061-sicn-001/diagnostic.json': '1a83ece0b380500694f3ef936b5df00df6911c6f4f52c5d7794fb2f2e14e1d66', 'work/962-engineering/head-star-current110-component-0062-sicn-001/diagnostic.json': '3f3b6e4baf0191fc39cfbc0efb1dc9816cf9c933eb1aaf7cb81cffd7437a879d', 'work/962-engineering/head-star-current110-component-0063-sicn-001/diagnostic.json': '73cea988145f9d63d638b56d10be14e87092d86fa9f01928c8a91d7beb990bd8', 'work/962-engineering/head-star-current110-component-0064-sicn-001/diagnostic.json': '87adbb12dc4b99c86f66e062e3354dbc3068467d42354cd05ec011d43c2f7197', 'work/962-engineering/head-star-current110-component-0065-sicn-001/diagnostic.json': '96022ace88e65c5540b5c62b50df96f3e148461a0d0ebd7cdcbd573444095bcb', 'work/962-engineering/head-star-current110-component-0066-sicn-001/diagnostic.json': '321708521642ea265fe6476d4bf03cb9a08fa542c3c534c274aa09126deb81d0', 'work/962-engineering/head-star-current110-component-0067-sicn-001/diagnostic.json': '2ca63dd823c5f7e364c0115cc1177a6a594bf26381f4185f9146ad6db21ccf0c', 'work/962-engineering/head-star-current110-component-0068-sicn-001/diagnostic.json': '5d91f91a73a8f31b09e77e2145c68f67d8747c40af7969c801d8bd175b257438', 'work/962-engineering/head-star-current110-component-0069-sicn-001/diagnostic.json': 'ec49cfc41098504d20dbe00ede79365c71096a7144a01ff6841f1d9ba022aa6b', 'work/962-engineering/head-star-current110-component-0070-sicn-001/diagnostic.json': '7961f66645eeb0f25722188f6f0ab4ffb57de954f0691c202dfd064b713e170c', 'work/962-engineering/head-star-current110-component-0071-sicn-001/diagnostic.json': '99a44f1ffb5fa224a95e6592f8dc67e85511d1653197cca24a98ab41f42bb6ec', 'work/962-engineering/head-star-current110-component-0072-sicn-001/diagnostic.json': 'b497a05f946afdcd0c78187cc53af0c1be3484de6431ee0a5522037fadc419ff', 'work/962-engineering/head-star-current110-component-0073-sicn-001/diagnostic.json': '13fff1a1c8e34fc850f18a41d7ac640214e238b18851961246c58784f779b2e1', 'work/962-engineering/head-star-current110-component-sicn-prep-001/component-manifest.json': '8ae9f9e93aee4b9d06936c87f856b6e318e0b4ce5dbf5e9d78c9b99acdd8f8d7', 'work/962-engineering/head-star-current110-component-sicn-result-peer-001/bindings.json': '9e4845587a915d914d8b4d099562625a2c70b370603e308c6b55ffa8aac11cbf', 'work/962-engineering/head-star-current110-component-sicn-result-peer-001/review.json': '929ef79aecf7bcad15f64e27900db1ed1f0995f4541eee32170f96de05974e4d', 'work/962-engineering/head-star-current110-component-sicn-root-execution-001/batch-once-closed.json': 'f32b0023374b04fca0baeb12a36e222c9aba5f432fb9d4f4a3f6538babb3526b', 'work/962-engineering/head-star-current110-component-sicn-root-execution-001/result-peer-acceptance.json': '787de8cfe56c127b73f6185cc2a7be8e02c92c315ae2bd39b093bc03ce6237b1', 'work/962-engineering/head-star-current110-coupling-graph-001/coupling-graph.json': 'cf50b7abb47a35dcfdc52fd95605d2eec6ce406dd3a2d528439dfc7c6fe3de0b', 'work/962-engineering/head-star-current110-coupling-graph-001/root-review.json': '7d8925cfc3a4d8c445b4cfd7282d9092768e49f81637c97e01be820961ba4145', 'work/962-engineering/head-star-current110-full-stars-001/frozen-contract.json': '6a48c4ee306889b393d50924819004b5d158631a9a4e0063564f52e8d6a4cdf0', 'work/962-engineering/head-star-current110-full-stars-001/readback-report.json': '657fbb0ce1c89dbf691f5a07c62feedf0fd91f7bc78f21d2aa14a3e01a9566da', 'work/962-engineering/head-star-current110-full-stars-prep-001/reader.py': '485e0eac2a20d1abe1f12d48892ba17d2947ea3c6d0c963fa97408f421982ac5', 'work/962-engineering/head-star-current110-full-stars-root-execution-001/result-peer-acceptance.json': '3d21b5f1e2cca935e6840e6444acd247b74ef877462c3382a07798c0217c7ed0', 'work/962-engineering/head-star-current110-pass62-apply-prep-001/held-preparation.json': '17344c42b64db601149c4e2f93dd3dace8afd64709a1ea84abd2859bde0a99e0', 'work/962-engineering/head-star-current110-pass62-apply-prep-001/mesh_apply_sicn_proposal.py': '66f956df8156871501377d96489533425a75421cfe693d6c6888c963355afa83', 'work/962-engineering/head-star-current110-pass62-apply-prep-001/source-delta.json': '77253ead8b65bc562430978008a7ee0c2969285cd8ecba184b3e4a9436264fd4', 'work/962-engineering/head-star-current110-pass62-apply-prep-001/source-reuse.json': '06d9e0c77b9438a8c340cdfa3d1637278753156c7cca7936eb94859a8f53e86f', 'work/962-engineering/head-star-current110-pass62-apply-prep-002/selected-proposals.json': '3af57b7644901c8755f51286571f9b9cf32bcde2bcf23191c344401ffade2e6f', 'work/962-engineering/head-star-current126-alternative-combined-application-001/execution-receipt.json': 'bc8a8428c23e4d3d4f2cf580591c48099d9e9d75857a44e78d6329cd36444905', 'work/962-engineering/head-star-current126-alternative-combined-application-001/head-volume.msh': '1b3a5a454b9fcbeb2cf5d36aaa8be0bc9cce9319897e47a31af3ac597d5cdb20', 'work/962-engineering/head-star-current126-alternative-combined-application-001/readback-report.json': '522b994bf693231cbbc5d7a098200b4746d20bc65b2e91235d6bbe2b3c676732', 'work/962-engineering/head-star-remaining-direct-sicn-apply-prep-001/mesh_apply_sicn_proposal.py': 'cb19c153a6e47e22aa5223b1a78a177707fad1398b881e5d0a86beaf6721a44a'}

INPUT_ROOT_CLOSED = 'work/962-engineering/current126-alternative-combined-application-root-execution-001/closed-result.json'
PARTIAL_PROOF = {'MSH_bytes': 235798094, 'MSH_sha256': '1b3a5a454b9fcbeb2cf5d36aaa8be0bc9cce9319897e47a31af3ac597d5cdb20', 'declared_controller_command_conformant': False, 'diagnostic_maximum_nonpositive_cells': 0, 'expected_partial_operation_counts': {'removeElements': 1, 'setNode': 15, 'addNodes': 1, 'addElementsByType': 1, 'rebuildNodeCache': 1, 'rebuildElementCache': 1, 'write_mesh': 1, 'generate': 0, 'optimize': 0, 'createGeometry': 0, 'reclassifyNodes': 0, 'solve': 0}, 'expected_positive_poor_total': 110, 'expected_saved_counts': {'retained_boundary_nodes': 871731, 'tetra_referenced_interior_nodes': 225537, 'tetra_referenced_nodes': 1097268, 'tetrahedra': 3622025, 'total_mesh_nodes': 1097268, 'unreferenced_mesh_nodes': 0}, 'expected_source_boundary_identity': {'source_boundary_nodes': 871731, 'source_node_tags_sha256': 'ee1f8fe28907eb0dc4671e3b068a1bbd824fcea8c277698c3566f7d339af760f', 'source_coordinate_bits_sha256': 'e0009dc6c5481cb77383b91a6e72ee4f223f207917b345e74f0b5b8e65ca6786', 'classification_dimensions_sha256': '7ea4e17c700c23a5e6b7534a64ee620dc07e55e2584782d036902a5265fab5c5', 'classification_entity_tags_sha256': '78dda7d4a07eb679bb33af1340b0aaeb81a538d351cc92320f3c365d169a164c', 'no_curve_or_surface_periodic_mapping': True, 'periodic_entities_checked': [[2, 1]]}, 'original_parent_MSH_sha256': '48b66aafbd9f1eb69e44305982186e966fe8f041d9b4a6a59be4b610b5d12e08', 'partial_actual_descriptor': {'path': 'work/962-engineering/head-star-current126-alternative-combined-application-execution-prep-002/actual-contract.json', 'sha256': '28d0968b5348975ec3e36fdaa0ffd152edbd6e203373b0498d4c552a07388ff1', 'bytes': 54977}, 'partial_contract_sha256': '28d0968b5348975ec3e36fdaa0ffd152edbd6e203373b0498d4c552a07388ff1', 'partial_native_log_sha256': '689255e61789b7a3c3223298c356302b030eb9b4276dcb03ce0db212516d2133', 'partial_output_inventory': {'frozen-contract.json': {'path': 'work/962-engineering/head-star-current126-alternative-combined-application-001/frozen-contract.json', 'sha256': '28d0968b5348975ec3e36fdaa0ffd152edbd6e203373b0498d4c552a07388ff1', 'bytes': 54977}, 'head-volume.msh': {'path': 'work/962-engineering/head-star-current126-alternative-combined-application-001/head-volume.msh', 'sha256': '1b3a5a454b9fcbeb2cf5d36aaa8be0bc9cce9319897e47a31af3ac597d5cdb20', 'bytes': 235798094}, 'execution-receipt.json': {'path': 'work/962-engineering/head-star-current126-alternative-combined-application-001/execution-receipt.json', 'sha256': 'bc8a8428c23e4d3d4f2cf580591c48099d9e9d75857a44e78d6329cd36444905', 'bytes': 36286}, 'reader.py': {'path': 'work/962-engineering/head-star-current126-alternative-combined-application-001/reader.py', 'sha256': '566b3245fb85a7a84efc1e016aa59b626bde0faf5844825ae84d62cc2e4a957e', 'bytes': 87357}, 'native.log': {'path': 'work/962-engineering/head-star-current126-alternative-combined-application-001/native.log', 'sha256': '689255e61789b7a3c3223298c356302b030eb9b4276dcb03ce0db212516d2133', 'bytes': 1328}, 'readback-report.json': {'path': 'work/962-engineering/head-star-current126-alternative-combined-application-001/readback-report.json', 'sha256': '522b994bf693231cbbc5d7a098200b4746d20bc65b2e91235d6bbe2b3c676732', 'bytes': 289378}, 'run_readback.py': {'path': 'work/962-engineering/head-star-current126-alternative-combined-application-001/run_readback.py', 'sha256': '5ab38b53e4019506772cc429b46699ac0e217141c87a0a043718d8123ecb159c', 'bytes': 4652}}, 'partial_reader_sha256': '566b3245fb85a7a84efc1e016aa59b626bde0faf5844825ae84d62cc2e4a957e', 'partial_report_sha256': '522b994bf693231cbbc5d7a098200b4746d20bc65b2e91235d6bbe2b3c676732', 'partial_runner_sha256': '5ab38b53e4019506772cc429b46699ac0e217141c87a0a043718d8123ecb159c', 'upstream_census_launch_deviation_sha256': 'd60fff297c6c45dc92e117262e36ffde36e2169d53fcd32ce2b79fabde5eebc3', 'admitted_manifest_sha256': '5270a56b18e1dbefc1dd117fb38a53e1fd8a1bcd5bbf9868943896a46b1c6773', 'current_local_domain_peer_sha256': '438a90ab8f00bede3b5e732587fce9782b5fa95d5057eb24f0603ecb80db5f20', 'current_local_domain_root_acceptance_sha256': '77353b4522df7defc9678ff8446876bcaa76a610660d108d13d74564af93b469', 'context_sha256': 'b74fd6aae321dd44a0a1ce840880ee9df958c2e1847512b0482e4ea8997d779a'}

def require_inputs():
    bound_proposal()  # Authority refusal precedes every opaque geometry input hash.
    if not INPUT_HASHES:
        raise ValueError("Complete fixed head and cube evidence bindings required")
    for name, expected in INPUT_HASHES.items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest() != expected:
            raise ValueError("Bound head optimizer input or software evidence changed")


def configure_core():
    if hashlib.sha256(CORE_PATH.read_bytes()).hexdigest() != CORE_SHA256:
        raise ValueError("Exact reviewed frozen quality-volume controller required")
    require_inputs()
    binding=bound_proposal()
    spec=importlib.util.spec_from_file_location("_962_frozen_postexport_core",CORE_PATH)
    core=importlib.util.module_from_spec(spec);spec.loader.exec_module(core)
    globals()["np"]=core.np  # Exact copied485e classifier retains its original module NumPy name.
    sources=tuple(core.source_files());original_save=core.save;original_admission=core.require_admission
    if len(sources)!=5 or sources[0]!=CORE_PATH:
        raise ValueError("Original controller and its four source imports required")
    def require_bound_admission(path,digest):
        require_inputs();bound_proposal()
        if path.resolve()!=ADMISSION.resolve() or digest!=ADMISSION_SHA256:
            raise ValueError("The fixed original surface-admission receipt is required")
        return original_admission(path,digest)
    def save_postexport(path,report):
        report["postexport_companion"]=dict(frozen_core_sha256=CORE_SHA256,
            wrapper_source_sha256=hashlib.sha256(WRAPPER_PATH.read_bytes()).hexdigest(),
            input_sha256s=INPUT_HASHES,proposal_application=dict(method="strict_selected_setNode",selected_nodes=66),
            proposal_binding_sha256=hashlib.sha256(APPLICATION_BINDING.read_bytes()).hexdigest(),
            selection_sha256=SELECTION_SHA256,census_sha256=CENSUS_SHA256,
            geometry_creation_dim_tags=[],volume_only_geometry_flag=False,
            interior_recreation_and_retagging_permitted=False,
            interior_ancestry_or_physical_topology_change_inferred=False,
            stronger_Mesh2_admitted=False,
            mesh_generation_called=False,optimizer_called=False,proposal_generation_in_original_runtime=False,
            proposal_solver_success_is_not_native_acceptance=True,
            cache_refresh="rebuildElementCache(False): lookup repair, no geometry change",
            analytic_proposal_gate_is_not_native_SICN=True,actual_minimum_SICN_gate_unchanged=.1,
            cube_success_is_not_head_acceptance=True)
        original_save(path,report)
    core.__file__=str(WRAPPER_PATH)  # Both controller and worker re-enter this wrapper.
    core.source_files=lambda:[WRAPPER_PATH,*sources,APPLICATION_BINDING,SELECTION]
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


def partial_after_proof(worker,receipt,closed,contract):
 """Bind the actual partial-replacement after/saved proof without optimizer aliases."""
 if (worker.get('schema')!='962-current126-alternative15-combined-head-application-result/v1'
     or worker.get('status')!='completed_partial_head_replacement_whole_head_quality_gate_applied'
     or worker.get('stage')!='completed_partial_repair_audits'
     or any(worker.get(k) is not True for k in ['procedural_checks_passed','partial_replacement_completed','saved_mesh_identity_exact','bound_inputs_unchanged'])
     or worker.get('after')!=worker.get('saved_reopen')
     or worker.get('mesh_sha256')!=contract['MSH_sha256'] or worker.get('mesh_bytes')!=contract['MSH_bytes']
     or any(worker.get(key)!=contract[key] for key in ['admitted_manifest_sha256','current_local_domain_peer_sha256','current_local_domain_root_acceptance_sha256','context_sha256'])
     or worker.get('native_operation_counts')!=contract['expected_partial_operation_counts'] or worker.get('call_counts_are_attempts') is not True
     or worker.get('upstream_census_launch_deviation_sha256')!=contract['upstream_census_launch_deviation_sha256']
     or worker.get('declared_controller_command_conformant') is not False or contract['declared_controller_command_conformant'] is not False
     or worker.get('original_parent_MSH_sha256')!=contract['original_parent_MSH_sha256']
     or receipt.get('returncode')!=2 or receipt.get('stop_reason') is not None
     or receipt.get('readback_report_sha256')!=contract['partial_report_sha256']
     or receipt.get('contract_sha256')!=contract['partial_contract_sha256']
     or receipt.get('reader_sha256')!=contract['partial_reader_sha256']
     or receipt.get('runner_sha256')!=contract['partial_runner_sha256']
     or receipt.get('native_log_sha256')!=contract['partial_native_log_sha256']
     or receipt.get('native_generate_optimize_solve_calls_declared')!=0 or receipt.get('mesh_write_calls_declared')!=1 or receipt.get('counters_are_declarations') is not True
     or closed.get('schema')!='962-current126-alternative15-combined002-native-root-execution/v1'
     or closed.get('returncode')!=2 or closed.get('error') is not None or closed.get('signals')!=[]
     or any(closed.get(k) is not True for k in ['waited_reaped','owned_group_absent','all_captured_inputs_and_runtime5_unchanged','full_parent_body_hash_checked_before_after'])
     or closed.get('automatic_retry') is not False
     or closed.get('actual')!=contract['partial_actual_descriptor']
     or closed.get('output_files')!=contract['partial_output_inventory']):
  raise ValueError('Exact stopped partial-replacement after/saved proof required')
 proof=worker['after'];n=proof['tetrahedra'];quality=proof['quality'];keys={'sorted_node_tags_sha256','sorted_coordinates_sha256','sorted_tetra_tags_sha256','tagged_tetra_connectivity_sha256'}
 counts={k:proof[k] for k in contract['expected_saved_counts']}
 if (counts!=contract['expected_saved_counts'] or any(type(v) is not int for v in counts.values())
     or set(proof['array_sha256s'])!=keys
     or set(quality)!={'minimum_jacobian','native_volume_mm3','minimum_SICN','independent_signed_volume_mm3'}
     or any(type(row.get('count')) is not int or row['count']!=n or type(row.get('nonpositive_count')) is not int for row in quality.values())
     or quality['minimum_SICN']['below_point1_count']-quality['minimum_SICN']['nonpositive_count']!=contract['expected_positive_poor_total']
     or quality['minimum_SICN']['nonpositive_count']!=contract['diagnostic_maximum_nonpositive_cells']
     or worker.get('actual_whole_head_positive_poor_count')!=contract['expected_positive_poor_total']
     or worker.get('actual_whole_head_SICN_gate_passed') is not (quality['minimum_SICN']['minimum']>=.1 and quality['minimum_SICN']['nonpositive_count']==0)
     or proof['source_boundary_identity']!=contract['expected_source_boundary_identity']):
  raise ValueError('Complete current partial-head arrays/counts/quality/boundary proof required')
 return proof


def require_after_match(report,proof,expected_positive_poor_total):
 """Require direct full saved-file observations to match the single worker proof."""
 for observed,expected in [('actual_mesh_nodes','total_mesh_nodes'),('actual_tetrahedra','tetrahedra'),('actual_tetra_referenced_nodes','tetra_referenced_nodes'),('actual_unreferenced_mesh_nodes','unreferenced_mesh_nodes'),('actual_referenced_interior_nodes','tetra_referenced_interior_nodes')]:
  if type(report[observed]) is not int or report[observed]!=proof[expected]:raise ValueError('Saved node/tetrahedron/reference counts differ from worker.after')
 fields=['count','minimum','maximum','p01','p05','p50','p95','p99','nonpositive_count']
 for name,key in [('SICN','minimum_SICN'),('Jacobian','minimum_jacobian'),('native_volume_mm3','native_volume_mm3')]:
  observed=report['direct_native_quality_extrema'][name];expected=proof['quality'][key]
  if any(observed[k]!=expected[k] for k in [*fields,'array_sha256']):raise ValueError('Full saved native metric differs from worker.after: '+name)
  if name=='SICN' and observed['below_point1_count']!=expected['below_point1_count']:raise ValueError('SICN below-point1 count differs from worker.after')
 observed=report['independent_signed_volume_mm3'];expected=proof['quality']['independent_signed_volume_mm3']
 if (any(observed[k]!=expected[k] for k in fields) or observed['sum']!=proof['summed_tetra_volume_mm3'] or observed['relative_error_to_candidate']!=proof['volume_relative_error']):
  raise ValueError('Independent saved signed-volume distribution/sum differs from worker.after')
 if report['positive_poor_SICN_cells']['total']!=expected_positive_poor_total:raise ValueError('Exact current positive-poor partition required')


def movable_from_poor_rows(poor_rows,interior_tags,boundary_count):
 """Only poor-cell members in the freshly proved dim3 tag set are variables."""
 if (type(boundary_count) is not int or boundary_count<=0
     or any(type(t) is not int or t<=boundary_count for t in interior_tags)
     or interior_tags!=sorted(set(interior_tags))):
  raise ValueError('Exact positive boundary count and sorted unique interior tags required')
 interior=set(interior_tags);members=set()
 for row in poor_rows:
  if len(row)!=4 or any(type(t) is not int or t<=0 for t in row) or len(set(row))!=4:
   raise ValueError('Complete positive distinct integer TET4 rows required')
  if any(t>boundary_count and t not in interior for t in row):
   raise ValueError('Poor row has an unclassified nonboundary tag')
  members.update(row)
 return sorted(members & interior)



def current_after_proof(worker,receipt,diagnosis,candidate_sha):
    """The sole completed current partial.after/saved proof plus fresh110 census."""
    closed=json.loads((ROOT/INPUT_ROOT_CLOSED).read_text())
    proof=partial_after_proof(worker,receipt,closed,PARTIAL_PROOF)
    if (candidate_sha!=INPUT_HASHES["work/962-engineering/atomic-cavity-plane-clip-cap-assembly-001/candidate.bin"]
            or diagnosis.get("status")!="direct_saved_file_readback_completed"
            or diagnosis.get("bound_inputs_unchanged") is not True
            or diagnosis.get("single_partial_replacement_saved_proof")!={"report_sha256":INPUT_HASHES[INPUT_WORKER],
                "field":"after","after_equals_saved_reopen":True,"independent_prior_reader_alias_used":False,"old210_bins_reused":False}
            or diagnosis.get("direct_counts_metrics_and_positive_poor_total_match_single_worker_after") is not True
            or any(diagnosis.get(k)!=v for k,v in proof["array_sha256s"].items())):
        raise ValueError("Single completed current partial.after/saved and fresh110 census required")
    require_after_match(diagnosis,proof,110)
    return proof

def boundary_identity(core,state,points,classification):
    """Exact source-tag/binary64 boundary identity; whole-tag continuity is checked separately."""
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
    if gmsh.model.getEntities(3)!=[(3,1)] or not gmsh.model.getBoundary([(3,1)],oriented=True,recursive=False):
        raise ValueError("Exactly one volume(3,1) with a nonempty bounding shell required")
    worker=json.loads((ROOT/INPUT_WORKER).read_text());receipt=json.loads((ROOT/INPUT_RECEIPT).read_text())
    diagnosis=json.loads((ROOT/INPUT_READBACK).read_text())
    proof=current_after_proof(worker,receipt,diagnosis,core.CANDIDATE_SHA)
    state,fresh=audit_after(core,gmsh,points,faces)
    fresh["source_boundary_identity"]=boundary_identity(core,state,points,fresh["classifications"])
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
    require_after_match(fresh["complete_native_census"],proof,110)
    observed=fresh["complete_native_census"]["complete_seed_star_census"];saved=diagnosis["complete_seed_star_census"]
    if ({k:v for k,v in observed.items() if k!="complete_incident_tetrahedra"}!={k:v for k,v in saved.items() if k!="complete_incident_tetrahedra"}
            or len(observed["complete_incident_tetrahedra"])!=len(saved["complete_incident_tetrahedra"])
            or any({k:v for k,v in a.items() if k!="native_array_index"}!={k:v for k,v in b.items() if k!="native_array_index"}
                for a,b in zip(observed["complete_incident_tetrahedra"],saved["complete_incident_tetrahedra"]))):
        raise ValueError("Every fresh before tagged seed-star row, word and six typed sections must equal current110 saved census")
    report["selected_cell_index_associations"]=[dict(tetrahedron_tag=a["tetrahedron_tag"],fresh_sorted_tagged_array_index=a["native_array_index"],saved_native_enumeration_index=b["native_array_index"])
        for a,b in zip(observed["complete_incident_tetrahedra"],saved["complete_incident_tetrahedra"])]
    core._pass62_before_census=fresh["complete_native_census"]["complete_seed_star_census"]
    return state,report


def require_relocation_continuity(before,after):
    for key in ("sorted_node_tags_sha256","sorted_tetra_tags_sha256","tagged_tetra_connectivity_sha256"):
        if before["array_sha256s"][key]!=after["array_sha256s"][key]:
            raise ValueError("Relocation changed node tags, tetra tags or oriented connectivity")
    for key in ("classifications","tetrahedra","total_mesh_nodes","retained_boundary_nodes",
            "tetra_referenced_nodes","tetra_referenced_interior_nodes","unreferenced_mesh_nodes"):
        if before[key]!=after[key]:
            raise ValueError("Relocation changed full classifications or counts")
    require_boundary_continuity(before["source_boundary_identity"],after["source_boundary_identity"])

def coordinate_rows(rows,expected_tags):
    """Strict ordered row/hex association; floats are compared by binary64 representation."""
    if (not isinstance(rows,list) or len(rows)!=len(expected_tags)
            or any(type(t) is not int or t<=0 for t in expected_tags)
            or expected_tags!=sorted(set(expected_tags))):
        raise ValueError("Complete increasing positive coordinate-tag rows required")
    coordinates=[]
    for row,tag in zip(rows,expected_tags):
        if not isinstance(row,dict):raise ValueError("Coordinate row must be an object")
        xyz=row.get("coordinates_mm");bits=row.get("binary64_hex")
        if (row.get("node_tag")!=tag or type(row.get("node_tag")) is not int
                or not isinstance(xyz,list) or len(xyz)!=3 or not isinstance(bits,list) or len(bits)!=3
                or any(type(x) not in (int,float) or not math.isfinite(x) for x in xyz)
                or any(type(h) is not str for h in bits)
                or [float(x).hex() for x in xyz]!=bits):
            raise ValueError("Exact node-tag/finite coordinate/binary64-hex association required")
        coordinates.append([float(x) for x in xyz])
    return coordinates


def bound_proposal():
    """A root-owned actual is required before importing the native core or reading geometry."""
    binding=json.loads(APPLICATION_BINDING.read_text())
    if (binding.get("schema")!="962-current110-pass62-application-actual/v1"
            or any(binding.get(k) is not True for k in ["native_execution_authorized",
                "root_and_peer_source_review_complete","synthetic_guard_review_complete",
                "selected_runtime_review_complete","coordinate_application_authorized"])
            or any(binding.get(k) is not False for k in ["automatic_retry","generation_authorized",
                "optimization_authorized","remeshing_authorized","head_PDE_authorized",
                "engineering_accepted","physics_qualified","manufacturing_authorized"])
            or binding.get("apply_source_sha256")!=hashlib.sha256(WRAPPER_PATH.read_bytes()).hexdigest()
            or binding.get("selection_sha256")!=SELECTION_SHA256
            or binding.get("selection_path")!=str(SELECTION.relative_to(ROOT))
            or binding.get("input_mesh_path")!=str(INPUT.relative_to(ROOT))
            or binding.get("input_mesh_sha256")!=PARTIAL_PROOF["MSH_sha256"]
            or binding.get("output_directory")!=str(OUTPUT.relative_to(ROOT))
            or binding.get("selected_nodes")!=66 or type(binding.get("selected_nodes")) is not int
            or binding.get("selected_incident_tetrahedra")!=1983
            or type(binding.get("selected_incident_tetrahedra")) is not int
            or binding.get("external_runtime_hashes")!=NATIVE_RUNTIME_HASHES
            or any(binding.get("input_hashes",{}).get(p)!=h for p,h in INPUT_HASHES.items())
            or APPLICATION_BINDING.is_symlink() or SELECTION.is_symlink()
            or hashlib.sha256(SELECTION.read_bytes()).hexdigest()!=SELECTION_SHA256):
        raise ValueError("A separately reviewed exact root actual for this fixed62 coordinate-only application is required")
    for name,digest in NATIVE_RUNTIME_HASHES.items():
        if hashlib.sha256(Path(name).read_bytes()).hexdigest()!=digest:
            raise ValueError("Selected existing native runtime drift")
    return binding


def selected_census(core,before):
    """Recompute complete seed incidence from ALL freshly loaded connectivity before setNode."""
    np=core.np;q,nt,et,en=before
    census=json.loads(CENSUS.read_text());c=census["complete_seed_star_census"]
    if (census.get("status")!="direct_saved_file_readback_completed" or census.get("bound_inputs_unchanged") is not True
            or census.get("single_partial_replacement_saved_proof")!={"report_sha256":INPUT_HASHES[INPUT_WORKER],"field":"after","after_equals_saved_reopen":True,"independent_prior_reader_alias_used":False,"old210_bins_reused":False}
            or c.get("schema")!="962-complete-current-poor-seed-stars/v1"
            or (c["movable_count"],c["complete_incident_tetrahedron_count"],c["unique_incident_node_count"],
                c["initially_positive_poor_incident_tetrahedra"],c["initially_good_incident_tetrahedra"])!=(82,2482,1439,110,2372)
            or any(census[k]!=core.array_sha(v) for k,v in zip(("sorted_coordinates_sha256","sorted_node_tags_sha256", "sorted_tetra_tags_sha256","tagged_tetra_connectivity_sha256"),before))):
        raise ValueError("Exact complete current full-star census and fresh full arrays required")
    movable=c["movable_node_tags"];rows=c["complete_incident_tetrahedra"];nodes=c["unique_incident_nodes"]
    coordinate_rows(nodes,[row["node_tag"] for row in nodes])
    if (len(movable)!=82 or movable!=sorted(set(movable)) or any(type(t) is not int or t<=871731 for t in movable)
            or len(rows)!=2482 or len(nodes)!=1439):
        raise ValueError("Exact 82 interior seeds and complete 2482/1439 rows required")
    poor=c["positive_poor_tetrahedron_tags"];pi=np.searchsorted(et,poor)
    if (len(poor)!=110 or poor!=sorted(set(poor)) or any(type(t) is not int or t<=0 for t in poor)
            or np.any(pi>=len(et)) or not np.array_equal(et[pi],poor)
            or movable_from_poor_rows(en[pi].tolist(),[int(t) for t in nt if t>871731],871731)!=movable):
        raise ValueError("All 110 current poor cells must derive exactly the 82 fresh dim3 seeds")
    ix=np.flatnonzero(np.any(np.isin(en,movable),axis=1));union=np.unique(en[ix]);ni=np.searchsorted(nt,union)
    expected_et=np.asarray([row["tetrahedron_tag"] for row in rows],dtype="<u8")
    expected_en=np.asarray([row["node_tags"] for row in rows],dtype="<u8").reshape(-1,4)
    expected_nt=np.asarray([row["node_tag"] for row in nodes],dtype="<u8")
    expected_q=np.asarray([row["coordinates_mm"] for row in nodes],dtype="<f8").reshape(-1,3)
    values={"movable_node_tags_u64":np.asarray(movable,dtype="<u8"),"selected_tetrahedron_tags_u64":expected_et,
        "selected_tetrahedron_connectivity_u64":expected_en,"union_node_tags_u64":expected_nt,
        "union_coordinates_f64":expected_q,"selected_initial_SICN_f64":np.asarray([row["initial_native_SICN"] for row in rows],dtype="<f8")}
    if (set(c["ordered_tagged_array_sha256s"])!=set(values)
            or any(core.array_sha(v)!=c["ordered_tagged_array_sha256s"][k] for k,v in values.items())
            or len(ix)!=2482 or not np.array_equal(et[ix],expected_et) or not np.array_equal(en[ix],expected_en)
            or not np.array_equal(union,expected_nt) or np.any(ni>=len(nt)) or not np.array_equal(nt[ni],union)
            or np.ascontiguousarray(q[ni]).tobytes()!=np.ascontiguousarray(expected_q).tobytes()):
        raise ValueError("Complete fresh incident union/connectivity/context bits differ from census")
    if before_fresh_census_sha256s(core,before)!=c["ordered_tagged_array_sha256s"]:
        raise ValueError("Fresh full native metrics/seed census differs from all six saved typed sections")
    return movable,c


def apply_and_refresh(core,gmsh,before,report,checkpoint):
    binding=bound_proposal();all_movable,census=selected_census(core,before)
    coordinates,scope=accepted_coordinate_rows(core,before,census);movable=SELECTED_TAGS
    report.update(stage="applying_exact_62_passed_component_66_node_rows",selection_sha256=SELECTION_SHA256,
        application_binding_sha256=hashlib.sha256(APPLICATION_BINDING.read_bytes()).hexdigest(),census_sha256=CENSUS_SHA256,
        complete_fresh_incident_union_verified=True,selected_node_tags=movable,selected_scope=scope,setNode_call_count=0)
    checkpoint()
    for tag,xyz in zip(movable,coordinates):
        report["setNode_call_count"]+=1;gmsh.model.mesh.setNode(tag,xyz,[])
    report.update(proposal_applied=True,stage="refreshing_element_lookup_cache")
    checkpoint();report["element_cache_refresh_count"]=1
    gmsh.model.mesh.rebuildElementCache(False)
    report.update(element_cache_refresh_completed=True,stage="proposal_applied_and_element_cache_refreshed")
    checkpoint()
    return movable,coordinates


def require_selected_coordinate_identity(core,before,after,movable,coordinates):
    np=core.np;q0,nt0,_,_=before;q1,nt1,_,_=after
    if not np.array_equal(nt0,nt1):raise ValueError("Every input node tag must survive unchanged")
    selected=np.isin(nt0,movable);expected=np.asarray(coordinates,dtype="<f8").reshape(-1,3)
    if (int(np.count_nonzero(selected))!=66
            or np.ascontiguousarray(q0[~selected]).tobytes()!=np.ascontiguousarray(q1[~selected]).tobytes()
            or np.ascontiguousarray(q1[selected]).tobytes()!=np.ascontiguousarray(expected).tobytes()):
        raise ValueError("All unselected node bits and exact selected proposal bits must be unchanged/applied")
    return dict(selected_nodes=66,unselected_nodes=len(nt0)-66,
        all_unselected_coordinate_bits_identical=True,all_selected_coordinate_bits_equal_proposal=True,
        signed_zero_included=True,unselected_coordinates_sha256=core.array_sha(q1[~selected]))


def audit_after(core,gmsh,points,faces):
    np=core.np;q,cells,nt,et,en=core.tagged_volume(gmsh);state=(q,nt,et,en)
    referenced=np.unique(en)
    if (len(np.unique(nt))!=len(nt) or len(np.unique(et))!=len(et)
            or not np.array_equal(referenced,nt)):
        raise ValueError("Unique tagged nodes/cells and no orphan mesh nodes required")
    census=complete_native_census(core,gmsh,state,len(points))
    report=dict(surface=core.surface_roundtrip(gmsh,points,faces,exact_tagged_order=False),
        classifications=census["direct_fresh_classifications"],tetrahedra=len(cells),
        total_mesh_nodes=len(nt),retained_boundary_nodes=len(points),tetra_referenced_nodes=len(referenced),
        tetra_referenced_interior_nodes=int(np.count_nonzero(referenced>len(points))),unreferenced_mesh_nodes=0,
        quality={},interior_node_count_establishes_thermal_resolution=False)
    for name,key in [("minimum_jacobian","Jacobian"),("native_volume_mm3","native_volume_mm3"),("minimum_SICN","SICN")]:
        observed=census["direct_native_quality_extrema"][key]
        report["quality"][name]={k:v for k,v in observed.items() if k!="below_point1_count" or key=="SICN"}
    signed=census["independent_signed_volume_mm3"]
    report["quality"]["independent_signed_volume_mm3"]={k:v for k,v in signed.items() if k not in ["sum","relative_error_to_candidate"]}
    if any(type(q.get("count")) is not int or q["count"] != len(cells) for q in report["quality"].values()):
        raise ValueError("Every metric distribution must cover every actual tetrahedron")
    report["summed_tetra_volume_mm3"]=signed["sum"]
    report["volume_relative_error"]=signed["relative_error_to_candidate"]
    report["actual_tetra_boundary"]=core.tetra_boundary(cells,np.searchsorted(nt,faces+1))
    report["internal_tetra_face_orientation"]=core.internal_face_orientation(cells)
    report["array_sha256s"]=array_identity(core,state)
    report["complete_native_census"]=census
    return state,report


def canonical_cells(np,nodes):
    ordered=np.sort(nodes,axis=1)
    return ordered[np.lexsort(ordered.T[::-1])]


def worker(core,args):
    launch=core.claim_worker(args);initialized=False;started=time.monotonic()
    path=args.output/"head-volume.msh"
    report=dict(status="running",stage="checking_runtime",geometry_creation_call_count=0,optimizer_call_count=0,
        optimizer_returned=False,proposal_applied=False,setNode_call_count=0,element_cache_refresh_count=0,element_cache_refresh_completed=False,
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
        report.update(stage="loading_exact_saved_partial_head_mesh");checkpoint()
        gmsh.open(str(INPUT));before,report["before"]=load_before(core,gmsh,points,faces)
        if any(gmsh.option.getNumber(k)!=v for k,v in OPTIONS.items()):raise ValueError("Fixed optimizer options changed")
        movable,coordinates=apply_and_refresh(core,gmsh,before,report,checkpoint)
        q,_,nt,et,en=core.tagged_volume(gmsh);applied=(q,nt,et,en)
        cls=classifications(core,gmsh,nt,len(points))
        if (any(array_identity(core,applied)[k]!=report["before"]["audit"]["array_sha256s"][k]
                for k in ["sorted_node_tags_sha256","sorted_tetra_tags_sha256","tagged_tetra_connectivity_sha256"])
                or cls!=report["before"]["audit"]["classifications"]):
            raise ValueError("Complete pre-write tags/connectivity/classifications changed")
        require_boundary_continuity(report["before"]["source_boundary_identity"],boundary_identity(core,applied,points,cls))
        report["prewrite_selected_coordinate_identity"]=require_selected_coordinate_identity(core,before,applied,movable,coordinates)
        report["prewrite_array_sha256s"]=array_identity(core,applied)
        report.update(stage="writing_single_coordinate_only_candidate",mesh_write_call_count=1);checkpoint()
        gmsh.write(str(path));report.update(mesh_sha256=core.sha(path),mesh_bytes=path.stat().st_size,
                                           stage="reopening_single_written_candidate_for_complete_native_census");checkpoint()
        gmsh.clear();gmsh.open(str(path))
        after,report["after"]=audit_after(core,gmsh,points,faces)
        if array_identity(core,after)!=report["prewrite_array_sha256s"] or not core.matching_mesh(path,report["mesh_sha256"]):
            raise ValueError("Saved reopened full arrays or candidate bytes changed")
        report["after"]["source_boundary_identity"]=boundary_identity(core,after,points,report["after"]["classifications"])
        require_relocation_continuity(report["before"]["audit"],report["after"])
        report["selected_coordinate_identity"]=require_selected_coordinate_identity(core,before,after,movable,coordinates)
        report["comparison"]=dict(total_nodes_before=len(before[1]),total_nodes_after=len(after[1]),
            referenced_interior_nodes_before=report["before"]["audit"]["tetra_referenced_interior_nodes"],
            referenced_interior_nodes_after=report["after"]["tetra_referenced_interior_nodes"],
            tetrahedra_before=len(before[2]),tetrahedra_after=len(after[2]),
            source_boundary_identity_unchanged=True,interior_recreation_retagging_and_count_changes_permitted=False,
            sorted_node_tags_tetra_tags_and_oriented_connectivity_unchanged=True,full_classifications_and_counts_unchanged=True,
            interior_ancestry_or_physical_topology_change_inferred=False,
            minimum_SICN_before_fresh=report["before"]["audit"]["quality"]["minimum_SICN"]["minimum"],
            minimum_SICN_after_actual=report["after"]["quality"]["minimum_SICN"]["minimum"])
        report["comparison"]["minimum_SICN_strictly_improved"]=(report["comparison"]["minimum_SICN_after_actual"]>
            report["comparison"]["minimum_SICN_before_fresh"])
        report["comparison"]["actual_SICN_point1_gate_passed"]=report["comparison"]["minimum_SICN_after_actual"]>=.1
        before_poor={r["tetrahedron_tag"]:r for r in report["before"]["audit"]["complete_native_census"]["positive_poor_SICN_cells"]["complete_tagged_cells"]}
        after_poor={r["tetrahedron_tag"]:r for r in report["after"]["complete_native_census"]["positive_poor_SICN_cells"]["complete_tagged_cells"]}
        if any(t not in after_poor or before_poor[t]["binary64_hex"]!=after_poor[t]["binary64_hex"]
                or before_poor[t]["node_tags"]!=after_poor[t]["node_tags"]
                or before_poor[t]["SICN"]!=after_poor[t]["SICN"] for t in REJECTED_INITIAL_POOR):
            raise ValueError("All24 rejected original poor cells and their native words must remain untouched")
        report.update(procedural_checks_passed=True,saved_mesh_identity_exact=True,
            saved_reopen=report["after"],actual_whole_head_positive_poor_count=len(after_poor),
            known_rejected_initial_poor_count_retained=24,original_worst_rejected_component_ID=30,
            original_worst_tetrahedron_tag=29801902,
            original_worst_native_SICN=after_poor[29801902]["SICN"],
            actual_whole_head_SICN_gate_passed=False,
            rejected11_proposed_coordinate_rows_applied=False,
            full_native_census_after_saved_reopen=True)
        del before,applied
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



def classify_positive_poor_chunk(values,tetra_tags,node_rows,offset,boundary_count,counts,representatives):
 """Complete participation bins; retain minimum(SICN,tag) per class."""
 if type(boundary_count) is not int or boundary_count<=0 or type(offset) is not int or offset<0:
  raise ValueError('Exact positive boundary count and nonnegative offset required')
 if set(counts)!={str(k) for k in range(5)} or any(type(v) is not int or v<0 for v in counts.values()):
  raise ValueError('Five exact nonnegative integer counters required')
 q=np.asarray(values);et=np.asarray(tetra_tags);en=np.asarray(node_rows)
 if (q.ndim!=1 or q.dtype.kind not in 'iuf' or not np.isfinite(q).all()
     or et.shape!=q.shape or et.dtype.kind not in 'iu' or np.any(et<=0)
     or en.shape!=(len(q),4) or en.dtype.kind not in 'iu' or np.any(en<=0)):
  raise ValueError('Complete finite SICN and integer tetrahedron/node rows required')
 positive=np.flatnonzero((q>0)&(q<.1));connections=en[positive]
 boundary_counts=np.count_nonzero((connections>=1)&(connections<=boundary_count),axis=1)
 for boundary_nodes in range(5):
  local=positive[boundary_counts==boundary_nodes];key=str(boundary_nodes)
  counts[key]+=len(local)
  if not len(local):continue
  minimum=float(q[local].min());ties=local[q[local]==minimum]
  chosen=int(ties[np.argmin(et[ties])]);tag=int(et[chosen])
  previous=representatives.get(key)
  if previous is not None and (minimum,tag)>=(previous['SICN'],previous['tetrahedron_tag']):continue
  representatives[key]=dict(native_array_index=offset+chosen,tetrahedron_tag=tag,SICN=minimum,
   original_boundary_node_count=boundary_nodes,interior_node_count=4-boundary_nodes)

def incident_positions(node_rows,movable_tags):
 """Every row touching any chosen tag, irrespective of its starting quality."""
 if (any(type(t) is not int or t<=0 for t in movable_tags)
     or movable_tags!=sorted(set(movable_tags))):
  raise ValueError('Sorted unique positive integer movable tags required')
 movable=set(movable_tags);positions=[]
 for index,row in enumerate(node_rows):
  if len(row)!=4 or any(type(t) is not int or t<=0 for t in row) or len(set(row))!=4:
   raise ValueError('Complete positive distinct integer TET4 rows required')
  if any(t in movable for t in row):positions.append(index)
 return positions

def before_fresh_census_sha256s(core,before):
    """Tie the saved six typed sections to the full freshly measured baseline census."""
    return core._pass62_before_census["ordered_tagged_array_sha256s"]


def accepted_coordinate_rows(core,before,census):
    """Read only the fixed62 accepted diagnostics; never select by score or use rejected vectors."""
    selection=json.loads(SELECTION.read_text())
    manifest=json.loads(COMPONENT_MANIFEST.read_text())
    acceptance=json.loads(RESULT_ACCEPTANCE.read_text())
    peer=json.loads(RESULT_PEER.read_text());bindings=json.loads(RESULT_BINDINGS.read_text())
    if (selection.get("schema")!="962-current110-fixed62-passed-coordinate-inputs/v1"
            or selection.get("component_IDs")!=PASS_IDS or selection.get("rejected_component_IDs")!=REJECTED_IDS
            or selection.get("selected_node_tags")!=SELECTED_TAGS or len(selection.get("diagnostics",[]))!=62
            or selection.get("selected_nodes")!=66 or selection.get("selected_incident_tetrahedra")!=1983
            or acceptance.get("decision")!="ACCEPT_COMPLETED73_SAVED_DIAGNOSTICS_ONLY_62_LOCAL_EXACT_PASSES_11_REJECTIONS_RETAINED"
            or acceptance.get("scientific_counts",{}).get("failed_component_IDs")!=REJECTED_IDS
            or acceptance.get("independent_peer")!=selection["result_peer"]
            or acceptance.get("peer_bindings")!=selection["result_peer_bindings"]
            or acceptance.get("batch")!=selection["batch"]
            or peer.get("bindings")!=selection["result_peer_bindings"]
            or bindings.get("all_captured_inputs_unchanged") is not True):
        raise ValueError("Exact accepted62 selection and saved result peer/root joins required")
    cases={r["component_ID"]:r for r in manifest["cases"]}
    peer_cases={r["component_ID"]:r for r in bindings["cases"]}
    source_nodes={r["node_tag"]:r for r in census["unique_incident_nodes"]}
    source_cells={r["tetrahedron_tag"]:r for r in census["complete_incident_tetrahedra"]}
    all_free=set(census["movable_node_tags"]);chosen={};used_cells=set();chosen_context=set()
    rejected_free=set(t for i in REJECTED_IDS for t in cases[i]["movable_node_tags"])
    rejected_cells=set(t for i in REJECTED_IDS for t in cases[i]["tetrahedron_tags"])
    rejected_context=set(t for i in REJECTED_IDS for t in cases[i]["all_incident_node_tags"])
    for row,component_ID in zip(selection["diagnostics"],PASS_IDS):
        case=cases[component_ID];descriptor=row["diagnostic"];path=ROOT/descriptor["path"]
        if (row["component_ID"]!=component_ID or row["case_key"]!=case["case_key"]
                or row["free_tags"]!=case["movable_node_tags"]
                or set(descriptor)!={"path","sha256","bytes"}
                or descriptor["path"]!=case["output_directory"]+"/diagnostic.json"
                or descriptor["sha256"]!=INPUT_HASHES[descriptor["path"]]
                or path.is_symlink() or path.stat().st_size!=descriptor["bytes"]
                or hashlib.sha256(path.read_bytes()).hexdigest()!=descriptor["sha256"]
                or descriptor not in peer_cases[component_ID]["outputs"]
                or peer_cases[component_ID]["status"]!="exact_feasible_point_solver_converged_native_unapproved"
                or peer_cases[component_ID]["final_positive_poor_tags"]!=[]):
            raise ValueError("One exact accepted original component descriptor and peer row required")
        d=json.loads(path.read_text());solver=d.get("solver",{})
        case_digest=hashlib.sha256(json.dumps(case,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()
        flags=["all_component_exact_quality_gate","procedural_checks_passed",
            "all_fixed_context_coordinate_bits_unchanged","source_boundary_context_bits_unchanged",
            "all_component_boundary_vertices_fixed","original_array_bits_unchanged",
            "original_ordered_connectivity_unchanged","exact_signed_volume_equals_same_component_before"]
        if (d.get("schema")!="962-current110-one-component-SLSQP-exact-diagnostic/v1"
                or d.get("status")!="exact_feasible_point_solver_converged_native_unapproved"
                or d.get("component_ID")!=component_ID or d.get("case_key")!=case["case_key"]
                or d.get("case_record_sha256")!=case_digest or row["case_record_sha256"]!=case_digest
                or d.get("component_manifest_sha256")!=INPUT_HASHES[str(COMPONENT_MANIFEST.relative_to(ROOT))]
                or d.get("source_census_sha256")!=CENSUS_SHA256
                or d.get("source_graph_sha256")!=selection["graph"]["sha256"]
                or d.get("source_mesh_sha256")!=PARTIAL_PROOF["MSH_sha256"]
                or d.get("free_tags")!=case["movable_node_tags"]
                or d.get("full_source_nodes")!=len(case["all_incident_node_tags"])
                or d.get("full_cells")!=len(case["tetrahedron_tags"])
                or any(d.get(k) is not True for k in flags)
                or solver.get("method")!="SLSQP" or type(solver.get("calls")) is not int or solver["calls"]!=1
                or solver.get("success") is not True or solver.get("status")!=0
                or d.get("positive_poor_cell_tags")!=[] or d.get("nonpositive_or_undefined_cell_tags")!=[]
                or d.get("exact_before_signed_volume_mm3")!=d.get("exact_final_signed_volume_mm3")
                or d.get("donor39_cell_shell_volume_reused") is not False
                or d.get("native_application_or_MSH_write") is not False
                or d.get("embedding_overlap_or_containment_checked") is not False
                or not isinstance(d.get("qualification"),dict)
                or any(v is not False for v in d["qualification"].values())):
            raise ValueError("Complete original accepted component proof, own volume and separate solver success required")
        tags=case["all_incident_node_tags"];coords=coordinate_rows(d.get("complete_proposed_coordinate_rows"),tags)
        free=case["movable_node_tags"];chosen_context.update(tags)
        if (set(free)&(set(chosen)|rejected_free|rejected_context)
                or used_cells&set(case["tetrahedron_tags"]) or rejected_cells&set(case["tetrahedron_tags"])
                or (set(tags)&all_free)!=set(free)):
            raise ValueError("Passed/rejected variable or cell coupling is forbidden")
        for tag,xyz in zip(tags,coords):
            original=source_nodes[tag]
            if tag not in free and [v.hex() for v in xyz]!=original["binary64_hex"]:
                raise ValueError("Any fixed source-boundary or other component context word drift refused")
            if tag in free:chosen[tag]=xyz
        exact=d.get("all_component_signed_quality_rows",[])
        if (len(exact)!=len(case["tetrahedron_tags"])
                or [r["tetrahedron_tag"] for r in exact]!=case["tetrahedron_tags"]):
            raise ValueError("All original ordered component exact-quality rows required")
        for proof in exact:
            old=source_cells[proof["tetrahedron_tag"]]
            det=proof["exact_native_ordered_determinant_mm3"];q=proof["exact_SICN_squared"]
            if (proof["ordered_node_tags"]!=old["node_tags"]
                    or proof.get("positive_orientation") is not True or proof.get("exact_point1_gate_passed") is not True
                    or Fraction(int(det["numerator"]),int(det["denominator"]))<=0
                    or Fraction(int(q["numerator"]),int(q["denominator"]))<Fraction(1,100)):
                raise ValueError("Every saved exact native-order determinant>0 and Q-squared>=1/100 is required")
        used_cells.update(case["tetrahedron_tags"])
    if (sorted(chosen)!=SELECTED_TAGS or len(chosen)!=66 or len(used_cells)!=1983
            or chosen_context&rejected_free or set(chosen)&rejected_context
            or sorted(t for i in REJECTED_IDS for t in cases[i]["initially_positive_poor_tetrahedron_tags"])!=REJECTED_INITIAL_POOR):
        raise ValueError("Exactly66 unique passed variables/1983 cells; rejected11 never setters")
    np=core.np;q0,nt,et,en=before
    ix=np.flatnonzero(np.any(np.isin(en,SELECTED_TAGS),axis=1))
    if et[ix].tolist()!=sorted(used_cells):
        raise ValueError("All fresh global cells touched by passed66 must be exactly the1983 accepted cells")
    return [chosen[t] for t in SELECTED_TAGS],dict(accepted_components=62,rejected_components_excluded=11,
        selected_cells=1983,original_poor_cells_covered=86,known_unmodified_rejected_initial_poor_tags=REJECTED_INITIAL_POOR,
        actual_native_quality_pending=True,global_embedding_overlap_or_containment_proved=False)


def complete_native_census(core,gmsh,state,boundary_count):
    """Exact485e complete metric/volume and seed-star loops in a fixed caller adapter."""
    np=core.np;xyz,tags,tet_tags,tet_nodes=state
    nv=boundary_count;tetorder=np.arange(len(tet_tags));array_sha=core.array_sha
    contract={"candidate_volume_mm3":core.CANDIDATE_VOLUME,"diagnostic_maximum_nonpositive_cells":0}
    report=dict(actual_mesh_nodes=len(tags),actual_tetrahedra=len(tet_tags),
        native_array_index_scope="Index into this complete sorted tagged TET4 state; original saved native enumeration index is retained separately in the before join.")
    native={};bad_tetrahedra=[]
    positive_poor_counts={str(k):0 for k in range(5)};positive_poor_representatives={};poor_indices=[];positive_poor_records=[]
    for name,measure in [('SICN','minSICN'),('Jacobian','minDetJac'),('native_volume_mm3','volume')]:
     row=dict(count=0,minimum=None,maximum=None,nonpositive_count=0,below_point1_count=0 if name=='SICN' else None)
     metric_values=np.empty(len(tet_tags),dtype=np.float64)
     for offset in range(0,len(tet_tags),100000):
      q=np.asarray(gmsh.model.mesh.getElementQualities(tet_tags[offset:offset+100000],measure))
      if len(q)!=len(tet_tags[offset:offset+100000]) or not np.isfinite(q).all():raise ValueError('Incomplete/nonfinite native metric')
      metric_values[offset:offset+len(q)]=q
      row['count']+=len(q);row['minimum']=float(q.min()) if row['minimum'] is None else min(row['minimum'],float(q.min()));row['maximum']=float(q.max()) if row['maximum'] is None else max(row['maximum'],float(q.max()));row['nonpositive_count']+=int(np.count_nonzero(q<=0))
      if name=='SICN':
       row['below_point1_count']+=int(np.count_nonzero(q<.1))
       classify_positive_poor_chunk(q,tet_tags[offset:offset+len(q)],tet_nodes[offset:offset+len(q)],offset,nv,positive_poor_counts,positive_poor_representatives)
       poor_indices.extend((offset+np.flatnonzero((q>0)&(q<.1))).tolist())
       for local in np.flatnonzero((q>0)&(q<.1)):
        index=offset+int(local);conn=tet_nodes[index];ids=np.searchsorted(tags,conn)
        if np.any(ids>=len(tags)) or not np.array_equal(tags[ids],conn):raise ValueError('Positive poor cell references missing saved node')
        coordinates=xyz[ids].tolist();boundary_nodes=int(np.count_nonzero((conn>=1)&(conn<=nv)))
        positive_poor_records.append(dict(native_array_index=index,tetrahedron_tag=int(tet_tags[index]),node_tags=conn.tolist(),coordinates_mm=coordinates,binary64_hex=[[float(v).hex() for v in point] for point in coordinates],SICN=float(q[local]),original_boundary_node_count=boundary_nodes,interior_node_count=4-boundary_nodes))
       for local in np.flatnonzero(q<=0):
        index=offset+int(local);conn=tet_nodes[index];ids=np.searchsorted(tags,conn)
        if np.any(ids>=len(tags)) or not np.array_equal(tags[ids],conn):raise ValueError('Nonpositive-SICN cell references missing node')
        bad_tetrahedra.append(dict(native_array_index=index,tetrahedron_tag=int(tet_tags[index]),node_tags=conn.tolist(),coordinates_mm=xyz[ids].tolist(),SICN=float(q[local]),all_nodes_original_boundary_tags=bool(np.all((conn>=1)&(conn<=nv)))))
        if len(bad_tetrahedra)>contract['diagnostic_maximum_nonpositive_cells']:raise ValueError('Unexpected diagnostic cell count; preserve refusal without truncating evidence')
      else:
       for bad in [*bad_tetrahedra,*positive_poor_representatives.values(),*positive_poor_records]:
        index=bad['native_array_index']
        if offset<=index<offset+len(q):bad[name]=float(q[index-offset])
     row.update(dict(zip(('p01','p05','p50','p95','p99'),map(float,np.percentile(metric_values,[1,5,50,95,99])))))
     row['array_sha256']=array_sha(metric_values[tetorder])
     native[name]=row
     if name=='SICN':sicn_values=metric_values
    report['direct_native_quality_extrema']=native
    for representative in positive_poor_representatives.values():
     conn=tet_nodes[representative['native_array_index']];ids=np.searchsorted(tags,conn)
     if np.any(ids>=len(tags)) or not np.array_equal(tags[ids],conn):raise ValueError('Positive poor cell references missing node')
     representative.update(node_tags=conn.tolist(),coordinates_mm=xyz[ids].tolist())
    volumes=np.empty(len(tet_tags),dtype=np.float64);referenced=np.zeros(len(tags),dtype=bool)
    for offset in range(0,len(tet_tags),100000):
     conn=tet_nodes[offset:offset+100000];ids=np.searchsorted(tags,conn)
     if np.any(ids>=len(tags)) or not np.array_equal(tags[ids],conn):raise ValueError('Tet references missing saved node')
     referenced[ids.ravel()]=True;v=xyz[ids];volumes[offset:offset+len(conn)]=np.einsum('ij,ij->i',v[:,1]-v[:,0],np.cross(v[:,2]-v[:,0],v[:,3]-v[:,0]))/6
    if not np.isfinite(volumes).all():raise ValueError('Nonfinite independent saved-file volume')
    total=math.fsum(volumes);report.update(independent_signed_volume_mm3=dict(count=len(volumes),minimum=float(volumes.min()),maximum=float(volumes.max()),nonpositive_count=int(np.count_nonzero(volumes<=0)),sum=total,relative_error_to_candidate=abs(total/contract['candidate_volume_mm3']-1)),actual_tetra_referenced_nodes=int(np.count_nonzero(referenced)),actual_unreferenced_mesh_nodes=int(np.count_nonzero(~referenced)),actual_referenced_interior_nodes=int(np.count_nonzero(referenced & ((tags<1)|(tags>nv)))))
    report['independent_signed_volume_mm3'].update(dict(zip(('p01','p05','p50','p95','p99'),map(float,np.percentile(volumes,[1,5,50,95,99])))))
    for bad in [*bad_tetrahedra,*positive_poor_representatives.values(),*positive_poor_records]:bad['independent_signed_volume_mm3']=float(volumes[bad['native_array_index']])
    report.update(nonpositive_SICN_tetrahedra=bad_tetrahedra,fixed_boundary_only_nonpositive_cells=all(bad['all_nodes_original_boundary_tags'] for bad in bad_tetrahedra))
    positive_poor_total=sum(positive_poor_counts.values())
    if positive_poor_total!=native['SICN']['below_point1_count']-native['SICN']['nonpositive_count']:raise ValueError('Complete positive-poor cell partition required')
    report['positive_poor_SICN_cells']=dict(total=positive_poor_total,
     by_original_boundary_node_count=positive_poor_counts,
     all_original_boundary_nodes=positive_poor_counts['4'],
     at_least_one_interior_node=positive_poor_total-positive_poor_counts['4'],
     representative_policy='One minimum(SICN,tetrahedron_tag) cell per nonempty0..4boundary-node class; at most5records, not a statistical sample.',
     representatives=positive_poor_representatives,
     original_boundary_definition='Exact admitted source surface tags1..nv; distinct from the surface-repair fixed-vertex mask.',
     positive_poor_feature_or_OEM_classification_computed=False)
    fresh_classifications=classifications(core,gmsh,tags,nv)
    poor_indices.sort(key=lambda i:int(tet_tags[i]))
    positive_poor_records.sort(key=lambda row:row['tetrahedron_tag'])
    if [row['tetrahedron_tag'] for row in positive_poor_records]!=[int(tet_tags[i]) for i in poor_indices]:raise ValueError('Complete ordered current positive-poor records required')
    report['positive_poor_SICN_cells']['complete_tagged_cells']=positive_poor_records
    if len(poor_indices)!=positive_poor_total:raise ValueError('All positive-poor rows required')
    interior_tags=tags[tags>nv].tolist()
    movable_tags=movable_from_poor_rows(tet_nodes[poor_indices].tolist(),interior_tags,nv)
    incident_indices=[]
    for offset in range(0,len(tet_tags),100000):
     incident_indices.extend(offset+i for i in incident_positions(tet_nodes[offset:offset+100000].tolist(),movable_tags))
    incident_indices.sort(key=lambda i:int(tet_tags[i]))
    unseedable_poor_indices=sorted(set(poor_indices)-set(incident_indices),key=lambda i:int(tet_tags[i]))
    selected_nodes=tet_nodes[incident_indices]
    union_tags=np.unique(selected_nodes).tolist();union_positions=np.searchsorted(tags,union_tags)
    if np.any(union_positions>=len(tags)) or not np.array_equal(tags[union_positions],union_tags):
     raise ValueError('Complete incident-cell coordinate association required')
    movable=set(movable_tags);poor_set=set(poor_indices);star_counts={t:0 for t in movable_tags}
    cells=[]
    for i in incident_indices:
     row=tet_nodes[i].tolist();touch=sorted(movable.intersection(row))
     for t in touch:star_counts[t]+=1
     cells.append(dict(tetrahedron_tag=int(tet_tags[i]),native_array_index=i,node_tags=row,
      initial_native_SICN=float(sicn_values[i]),initially_positive_poor=i in poor_set,movable_node_tags=touch))
    nodes=[]
    for tag,index in zip(union_tags,union_positions):
     row=xyz[index].tolist()
     nodes.append(dict(node_tag=int(tag),coordinates_mm=row,binary64_hex=[float(x).hex() for x in row],
      in_movable_seed_set=tag in movable,source_boundary_tag=tag<=nv,
      freshly_proved_classification_scope='below_dim3' if tag<=nv else 'dim3'))
    report['complete_seed_star_census']=dict(
     schema='962-complete-current-poor-seed-stars/v1',
     seed_policy='Union of nodes of ALL current positive SICN<0.1 cells, intersect freshly verified complete dim3 classifications; no optimizer proposal.',
     positive_poor_tetrahedron_tags=[int(tet_tags[i]) for i in poor_indices],
     movable_node_tags=movable_tags,movable_count=len(movable_tags),prospective_coordinate_variables=3*len(movable_tags),
     complete_incident_tetrahedra=cells,complete_incident_tetrahedron_count=len(cells),
     initially_positive_poor_incident_tetrahedra=sum(row['initially_positive_poor'] for row in cells),
     initially_good_incident_tetrahedra=sum(not row['initially_positive_poor'] for row in cells),
     shared_by_multiple_movable_nodes_tetrahedra=sum(len(row['movable_node_tags'])>1 for row in cells),
     per_movable_node_complete_incident_counts=[[t,star_counts[t]] for t in movable_tags],
     unique_incident_nodes=nodes,unique_incident_node_count=len(nodes),
     unique_incident_boundary_node_count=sum(row['source_boundary_tag'] for row in nodes),
     unique_incident_other_interior_node_count=sum(not row['source_boundary_tag'] and not row['in_movable_seed_set'] for row in nodes),
     ordered_tagged_array_sha256s=dict(
      movable_node_tags_u64=array_sha(np.asarray(movable_tags,dtype='<u8')),
      selected_tetrahedron_tags_u64=array_sha(np.asarray([tet_tags[i] for i in incident_indices],dtype='<u8')),
      selected_tetrahedron_connectivity_u64=array_sha(np.asarray(selected_nodes,dtype='<u8').reshape(-1,4)),
      union_node_tags_u64=array_sha(np.asarray(union_tags,dtype='<u8')),
      union_coordinates_f64=array_sha(np.asarray(xyz[union_positions],dtype='<f8')),
      selected_initial_SICN_f64=array_sha(np.asarray(sicn_values[incident_indices],dtype='<f8'))),
     all_seed_stars_complete_including_initially_good_and_shared_cells=True,
     all_positive_poor_rows_covered_by_movable_stars=not unseedable_poor_indices,
     unseedable_positive_poor_tetrahedron_tags=[int(tet_tags[i]) for i in unseedable_poor_indices],
     complete_list_policy='Complete or resource refusal; no sampling or record truncation.',
     cell_order='Increasing tetrahedron tag; original corner order retained.',node_order='Increasing node tag; coordinate hex preserves binary64 bits.',
     source_boundary_or_other_context_repair_policy_approved=False,
     shared_star_feasibility_computed=False,SLSQP_or_other_optimization_calls=0,candidate_or_geometry_export_written=False)
    report['direct_fresh_classifications']=fresh_classifications
    report["direct_fresh_classifications"]=fresh_classifications
    return report


def main(argv=None):
    require_inputs();core=configure_core()
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--admission",type=Path,required=True);parser.add_argument("--admission-sha256",required=True)
    parser.add_argument("--output",type=Path,required=True);parser.add_argument("--worker",action="store_true",help=argparse.SUPPRESS)
    args=parser.parse_args(argv)
    if core.sha(Path(sys.executable).resolve())!=PYTHON_SHA256:raise ValueError("Selected native Python required")
    return core.worker(args) if args.worker else core.run(args)


if __name__=="__main__":raise SystemExit(main())
