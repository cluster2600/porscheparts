"""HELD exact15 current126 combined application; context admission is pending; no native authority."""
from pathlib import Path
from fractions import Fraction
from types import SimpleNamespace
from itertools import combinations
import ast,hashlib,json,math,platform,struct,sys,time
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent
OUTPUT='work/962-engineering/head-star-current126-alternative-combined-application-001'
MESH='work/962-engineering/apex1613031-head-application-001/head-volume.msh'
CONTEXT='work/962-engineering/head-star-current126-alternative-union-context-001/readback-report.json'
CONTEXT_CONTRACT='work/962-engineering/head-star-current126-alternative-union-context-001/frozen-contract.json'
CONTEXT_SOURCE='work/962-engineering/head-star-current126-alternative-union-context-prep-001/reader.py'
CONTEXT_MANIFEST='work/962-engineering/head-star-current126-alternative-union-context-prep-001/case-manifest.json'
MANIFEST='work/962-engineering/head-star-current126-alternative-combined-application-prep-001/admitted-manifest.json'
BATCH='work/962-engineering/head-star-current126-alternative-batch-shells-001/report.json'
DOMAIN_SOURCE='work/962-engineering/head-star-current126-alternative-case-domains-prep-001/certify_domain.py'
DOMAIN_PEER='work/962-engineering/current126-alternative-case-domains-result-peer-001/review.json'
DOMAIN_BINDINGS='work/962-engineering/current126-alternative-case-domains-result-peer-001/bindings.json'
DOMAIN_ACCEPT='work/962-engineering/current126-alternative-case-domains-root-execution-001/result-peer-acceptance.json'
LOCAL_PEER='work/962-engineering/current126-alternative-Netgen-result-peer-001/review.json'
LOCAL_BINDINGS='work/962-engineering/current126-alternative-Netgen-result-peer-001/bindings.json'
LOCAL_ACCEPT='work/962-engineering/current126-alternative-Netgen-root-execution-001/result-peer-acceptance.json'
ORIGINAL_WORKER='work/962-engineering/apex1613031-head-application-001/readback-report.json'
ORIGINAL_RECEIPT='work/962-engineering/apex1613031-head-application-001/execution-receipt.json'
PARTIAL_CLOSED='work/962-engineering/apex1613031-head-application-root-execution-001/closed-result.json'
PARTIAL_ACCEPT='work/962-engineering/apex1613031-head-application-root-execution-001/result-peer-acceptance.json'
PARTIAL_METADATA='work/962-engineering/head-star-current126-full-stars-001/frozen-contract.json'
FIRST='work/962-engineering/head-star-current126-full-stars-001/readback-report.json'
FIRST_ACTUAL='work/962-engineering/head-star-current126-full-stars-execution-prep-001/actual-contract.json'
PROOF_SOURCE='work/962-engineering/head-star-current126-full-stars-prep-001/reader.py'
CENSUS_PEER='work/962-engineering/head-star-current126-full-stars-result-peer-001/review.json'
CENSUS_BINDINGS='work/962-engineering/head-star-current126-full-stars-result-peer-001/bindings.json'
CENSUS_ACCEPT='work/962-engineering/head-star-current126-full-stars-root-execution-001/result-peer-acceptance.json'
DEVIATION='work/962-engineering/head-star-current129-full-stars-root-execution-001/launch-deviation-001.json'
HEAD='twins/962-cylinder-head-f0/source/mesh_head.py'
CORE='work/962-engineering/atomic-cavity-plane-clip-cap-assembly-delaunay-prep-001/mesh_assembled_delaunay.py'
AUDIT='work/962-engineering/atomic-cavity-plane-clip-cap-assembly-delaunay-netgen-postexport-prep-002/mesh_delaunay_netgen_postexport.py'
WORKER=ORIGINAL_WORKER
FIRST_CONTRACT=PARTIAL_METADATA
MSH_SHA='48b66aafbd9f1eb69e44305982186e966fe8f041d9b4a6a59be4b610b5d12e08'
FIXED_INPUTS={'twins/962-cylinder-head-f0/source/mesh_head.py': '69c8012e99057e384d44d6971d41f0e2cc7197a978120a7c566b0ad5a6477da5', 'work/962-engineering/apex1613031-head-application-001/execution-receipt.json': '496b0e01950b777acd1c1759177fe26fac5659e5ec6512bb19ff9cb56b5fd46d', 'work/962-engineering/apex1613031-head-application-001/frozen-contract.json': '98c281e8e8633c7253a7e13e5a5979f1c31ab967ef1af798b0a0415fa07b26fb', 'work/962-engineering/apex1613031-head-application-001/readback-report.json': '64caf59811e229628ea1be138ebcc48cdf940c4ca2724be0b9080e255951c9f5', 'work/962-engineering/apex1613031-head-application-prep-002/reader.py': 'bd352d87c6fc3f4cfd8311ef169279725cf6a7c49e8cc0df2dca01b26d582361', 'work/962-engineering/apex1613031-head-application-root-execution-001/closed-result.json': '9324c5ef88293efa33f9e14cfeff3e092795eec337fceeaffd7481ac2ee41471', 'work/962-engineering/apex1613031-head-application-root-execution-001/result-peer-acceptance.json': '19ef174a208868bf174909a1add690971fdf018b8cf438c5c26e3a2bca9bfada', 'work/962-engineering/atomic-cavity-plane-clip-cap-assembly-delaunay-netgen-postexport-prep-002/mesh_delaunay_netgen_postexport.py': '0d1dd1f0625275343f16b713dae2d41143dda8da974bef42e59f6bfa3b0e388a', 'work/962-engineering/atomic-cavity-plane-clip-cap-assembly-delaunay-prep-001/mesh_assembled_delaunay.py': 'a3268687edc90b0149775cf5d80a89df82175cc982bbf5d7184b6ea8935be8a4', 'work/962-engineering/current126-alternative-Netgen-result-peer-001/bindings.json': '0d920fd251ba9dd35eeacece6f260043f146fc4c1f12c0c87679aa72d7d13301', 'work/962-engineering/current126-alternative-Netgen-result-peer-001/review.json': '8bd554dffc1f7cc918ef7597a9dd6536e93015406f86d8dcce166d2cc960bdb9', 'work/962-engineering/current126-alternative-Netgen-root-execution-001/apex-1433071/closed-result.json': 'ca06f48574a2cee4114ae7446d13d5afd7f05f3260468d31ac2c471b9fd3171a', 'work/962-engineering/current126-alternative-Netgen-root-execution-001/apex-1468585/closed-result.json': '397c18e070be140a8a8434d9b4b0864d4627677b8486ea91465c2817a189b4c8', 'work/962-engineering/current126-alternative-Netgen-root-execution-001/apex-1481549/closed-result.json': 'd04224fda1922a17dcb0b8b8f2228c8c83343daf05271db1a83d1a2606b6593d', 'work/962-engineering/current126-alternative-Netgen-root-execution-001/apex-1488093/closed-result.json': '3452c4b9c2e62556f80f2e0b4495ea3d4732907c5014c0e51b3e06e948227c49', 'work/962-engineering/current126-alternative-Netgen-root-execution-001/apex-1508641/closed-result.json': '95bd2b125dd4476b8eea33f53f58afd9617e51129b10469fcbf1e29c4ed15849', 'work/962-engineering/current126-alternative-Netgen-root-execution-001/apex-1515013/closed-result.json': '94b8549db71d3587a4b0b15884ec86ef25823918a8bbea4fa7b23e5556c42fcb', 'work/962-engineering/current126-alternative-Netgen-root-execution-001/apex-1538046/closed-result.json': 'f712b37e0e8f8566a3e79e55d2375dc6b7ab9b91c2b9ffc8cb49927f4a15f4bd', 'work/962-engineering/current126-alternative-Netgen-root-execution-001/apex-1541053/closed-result.json': 'ab40c5afc7a68bc0373fd8f94c9c811ea14c98a17f262f74de0b08fa5383625e', 'work/962-engineering/current126-alternative-Netgen-root-execution-001/apex-1558088/closed-result.json': '6edbca5124934b411acb91084f2f1ccec0c4bf6a9268b450dc941d82a4f2db2c', 'work/962-engineering/current126-alternative-Netgen-root-execution-001/apex-1570037/closed-result.json': '97bb7e966643790fdda7b13c1c12130d15ae9ab34d01770cc04b11504c813d9f', 'work/962-engineering/current126-alternative-Netgen-root-execution-001/apex-1611558/closed-result.json': '8c28e4eaa5d0235d8197027fbf3f74d49661b4b9f73d24b9501e6d54f1665e88', 'work/962-engineering/current126-alternative-Netgen-root-execution-001/apex-1611564/closed-result.json': 'c48d24ed210d12e2adcc92c2479b471dc4786dd3f2b46f3af0c12cc9f3dcfcf5', 'work/962-engineering/current126-alternative-Netgen-root-execution-001/apex-1613030/closed-result.json': '267753b9d277157d836ed3fb5d09553112579ada13059aede79d76ee7b88db93', 'work/962-engineering/current126-alternative-Netgen-root-execution-001/apex-1613794/closed-result.json': 'c10ffd753ba841c0b411b36c53251c6be798d45f2b3459a796e151d7a74cff66', 'work/962-engineering/current126-alternative-Netgen-root-execution-001/apex-1613795/closed-result.json': 'f9d5d77c3ea120b5036c42c07c0a2d92f0f01aaed14ad39f09eef0143f11e7ee', 'work/962-engineering/current126-alternative-Netgen-root-execution-001/result-peer-acceptance.json': '930277138dfe5564c47165989096b2f1b936362f428391d1fab61b039127ae15', 'work/962-engineering/current126-alternative-case-domains-result-peer-001/bindings.json': '99094124ca55cf5b6a607b38acd33cb05cfa46e8fcec7040a44568265aa4c3f2', 'work/962-engineering/current126-alternative-case-domains-result-peer-001/review.json': '438a90ab8f00bede3b5e732587fce9782b5fa95d5057eb24f0603ecb80db5f20', 'work/962-engineering/current126-alternative-case-domains-root-execution-001/apex-1433071/closed-result.json': '3ba36644aea2f0b45dd2631f353fef745352b59e9231dd315f6b76b734bcd580', 'work/962-engineering/current126-alternative-case-domains-root-execution-001/apex-1468585/closed-result.json': 'a9dba48c9d12f4f0562e5734196a7a38c24d10f1985fa4a44219ed6bfc126d8c', 'work/962-engineering/current126-alternative-case-domains-root-execution-001/apex-1481549/closed-result.json': '15fcffad241a76c0c6e5bc8a5eafb33b64f17d881082a3200c4097913b7695f7', 'work/962-engineering/current126-alternative-case-domains-root-execution-001/apex-1488093/closed-result.json': '85c4fff4136670f6e69ed884bcf61d04cb0d74b35a190098e0c82741db826df7', 'work/962-engineering/current126-alternative-case-domains-root-execution-001/apex-1508641/closed-result.json': '1385882dd274cd785362cbfa6d13bb9161bfe3204a8d99e290d43b1794290f43', 'work/962-engineering/current126-alternative-case-domains-root-execution-001/apex-1515013/closed-result.json': '7332f79269780296e2a9f094dda818e464c658fb714c196a07e3bc27f5ddc11e', 'work/962-engineering/current126-alternative-case-domains-root-execution-001/apex-1538046/closed-result.json': '1dbd1ad70e09c932bb42b4583d6caddc458c4fc2c0992eb0e57b135180bd4a8c', 'work/962-engineering/current126-alternative-case-domains-root-execution-001/apex-1541053/closed-result.json': '612f41939b98bba34bbeb2a838b652e6c49a7bbbf27def28c5b25fc046847104', 'work/962-engineering/current126-alternative-case-domains-root-execution-001/apex-1558088/closed-result.json': 'f98f2f3ccde4652581dc426d62f16297b01e3f86bb7350e2f55f86716d906ccc', 'work/962-engineering/current126-alternative-case-domains-root-execution-001/apex-1570037/closed-result.json': '78f24a7b872a809104258c981790289215bba2ec8a5664211e71296b45aceaf4', 'work/962-engineering/current126-alternative-case-domains-root-execution-001/apex-1611558/closed-result.json': 'afc56e8830b6fa6fb6f0180febe20eb384764c8625a6bd700ec84f7f532aeff9', 'work/962-engineering/current126-alternative-case-domains-root-execution-001/apex-1611564/closed-result.json': '660d9262f81a4a8bdd95c74836eea26422d7eb9b0879eee8ee55feb4c18df41b', 'work/962-engineering/current126-alternative-case-domains-root-execution-001/apex-1613030/closed-result.json': 'd1ae9db53ab23c10f1038f4b1bfd66dce21229d0c23e019d7f5d16061b7206fd', 'work/962-engineering/current126-alternative-case-domains-root-execution-001/apex-1613794/closed-result.json': '4384b86f22540c58f5f41dd7b6df4f6cd1d441ce1d847437939357efd7d8c53f', 'work/962-engineering/current126-alternative-case-domains-root-execution-001/apex-1613795/closed-result.json': 'edf64929052ba513ee27a7f26434de18c8155f0a621db6d0a068eb135a3b87ae', 'work/962-engineering/current126-alternative-case-domains-root-execution-001/result-peer-acceptance.json': '77353b4522df7defc9678ff8446876bcaa76a610660d108d13d74564af93b469', 'work/962-engineering/head-star-current126-alternative-apex-1433071-domain-001/report.json': 'bc346d2ae153f24f2c752ae6500f0f18d9b4463dc64fe3e66739922e96013ce9', 'work/962-engineering/head-star-current126-alternative-apex-1433071-netgen-001/arrays.json': 'f939a77936cdcad1e238806467e8ac7ded7a61650c32d35bdb927550c2f220ba', 'work/962-engineering/head-star-current126-alternative-apex-1433071-netgen-001/execution-receipt.json': 'e490ad8a14073d6ca333c4e3ca8ae310056f5bc4615e407c88ac844c67928195', 'work/962-engineering/head-star-current126-alternative-apex-1433071-netgen-001/fixture-report.json': '1815323e255e64cebc4639147574cc6615ff1cf29fbc87b545709932f9e98987', 'work/962-engineering/head-star-current126-alternative-apex-1433071-netgen-001/frozen-contract.json': '999353372694f7ac5b9b33047e30d4c7159c5bbea39596854be4a11637ed0d3a', 'work/962-engineering/head-star-current126-alternative-apex-1468585-domain-001/report.json': '04dec5828dcba05760a4bfb4c8076b25168a4d35faace1dd77de003f79465fa4', 'work/962-engineering/head-star-current126-alternative-apex-1468585-netgen-001/arrays.json': '166f078108f21c9736689a8de32ea9a2c7700d372aff5c0a37185d7a84c1c494', 'work/962-engineering/head-star-current126-alternative-apex-1468585-netgen-001/execution-receipt.json': 'bd9f89e85f4ed1a42ed05c485560053c2ce8cf055b9c5faf253d5a3ad55fce73', 'work/962-engineering/head-star-current126-alternative-apex-1468585-netgen-001/fixture-report.json': '478040c444432421472e6f5a463a02ac2a174110e1dbb7797b1ecbda7e991e85', 'work/962-engineering/head-star-current126-alternative-apex-1468585-netgen-001/frozen-contract.json': '6d139d7ce0214d345981fbd068077c344f29ddf1067e42c530ae0e5b649c1171', 'work/962-engineering/head-star-current126-alternative-apex-1481549-domain-001/report.json': '38a7012cd67bb86c6374ea76900439ecfba1582d9c6f368e59309039dcb3f0af', 'work/962-engineering/head-star-current126-alternative-apex-1481549-netgen-001/arrays.json': '67adb3f4a09ca360ebdd77d83e57b9df76657d4106658ed163e93f579669ff94', 'work/962-engineering/head-star-current126-alternative-apex-1481549-netgen-001/execution-receipt.json': '04cecb70596772b518adcedc17c473667e1f6ddaa2844c1b15a9361f9c29fa54', 'work/962-engineering/head-star-current126-alternative-apex-1481549-netgen-001/fixture-report.json': 'd1fe4725c3fab7145228c31ca8d6d1366bb0dba8a0666ca3800a9f3a8299716f', 'work/962-engineering/head-star-current126-alternative-apex-1481549-netgen-001/frozen-contract.json': 'e98f74edcb67ce776c84c95da328101cc2617725f7fcbd7566c36ed03c0d395f', 'work/962-engineering/head-star-current126-alternative-apex-1488093-domain-001/report.json': 'd84e07d96671d4e097458e2909519ad1640180eddf50cc9c737e374f483f16de', 'work/962-engineering/head-star-current126-alternative-apex-1488093-netgen-001/arrays.json': '6f6af6ed889a30b7c26c26efdb6d618844894bff2478d53799ddc846c98b626d', 'work/962-engineering/head-star-current126-alternative-apex-1488093-netgen-001/execution-receipt.json': '37435285bb723d7ec4e3c286b05893d8f7998bdde53beaaa943ad9cd650c5c5f', 'work/962-engineering/head-star-current126-alternative-apex-1488093-netgen-001/fixture-report.json': '36507d5a39f0ea9db0d93cf44645ac500fd2422fb46ef7457b13a3a34935aaf7', 'work/962-engineering/head-star-current126-alternative-apex-1488093-netgen-001/frozen-contract.json': '5313ce8abee6644e73c257cd9b065db639d1dfe30db1eb7ae098476411c77b17', 'work/962-engineering/head-star-current126-alternative-apex-1508641-domain-001/report.json': '2802ebdf8e26a141f4e0ca5a138da22b303aa06616ab2d4920e748cca48c8aff', 'work/962-engineering/head-star-current126-alternative-apex-1508641-netgen-001/arrays.json': 'f852ebc4fd5bb22d4d5e998a508829b6400b2a9c677a6dc80bd3db598c13d291', 'work/962-engineering/head-star-current126-alternative-apex-1508641-netgen-001/execution-receipt.json': '69547f21a1dadf21571e182f9e2a6f29502c41eb75516ca8b0054f4c961eb53e', 'work/962-engineering/head-star-current126-alternative-apex-1508641-netgen-001/fixture-report.json': 'e72bac94ab5e7420c6f288a65c68bf0bdec91abd8bfb733b8c6099bea23f6c4c', 'work/962-engineering/head-star-current126-alternative-apex-1508641-netgen-001/frozen-contract.json': '57bfa8754bc9939800073098abdaeadbb13dc7c0e498eaed1a5a2e39693bd6c0', 'work/962-engineering/head-star-current126-alternative-apex-1515013-domain-001/report.json': 'a18e12fcc2e1e57d0bd34ced18c55634f6fcd4254ec95cd4d1c54cc63f9fdce0', 'work/962-engineering/head-star-current126-alternative-apex-1515013-netgen-001/arrays.json': '221c01d12c14e8853b7e72ce23eded2d1467c4fc69d01e2163cec5c56654980e', 'work/962-engineering/head-star-current126-alternative-apex-1515013-netgen-001/execution-receipt.json': 'e978013fe003f5ace3a570d533bddc91b3e5cda59ac4e85db00c8e291a98d18e', 'work/962-engineering/head-star-current126-alternative-apex-1515013-netgen-001/fixture-report.json': 'cb8d71a635670f6e696199c2c83e9ed8f591dbfff17bba01e12c47db1a77126e', 'work/962-engineering/head-star-current126-alternative-apex-1515013-netgen-001/frozen-contract.json': 'd7e9410336640e6d4b1959fa1f0720d4d5ce140a39fe215864e4215d3b985285', 'work/962-engineering/head-star-current126-alternative-apex-1538046-domain-001/report.json': '48d3c5ff09121fb93b74829b9fc47352b3c376d2e4993aa50878c8a02674e73e', 'work/962-engineering/head-star-current126-alternative-apex-1538046-netgen-001/arrays.json': '368862904a107b358a7c1b6abf1a06610373474c98de1918a5a552f5e309ce1f', 'work/962-engineering/head-star-current126-alternative-apex-1538046-netgen-001/execution-receipt.json': '5c687a629d5a6329d28413ce46bad0ad9080b1f4e4e55ed47222ce8c9eb33b59', 'work/962-engineering/head-star-current126-alternative-apex-1538046-netgen-001/fixture-report.json': '09cab6daa41c3d307e792ae529c5eb14ac822fdad0691b54c9fa8842309ec5d5', 'work/962-engineering/head-star-current126-alternative-apex-1538046-netgen-001/frozen-contract.json': 'f6b75264fc2f1cd64e9517bd7ef5c0d5d2402b4c98bac8bd840477be473cc882', 'work/962-engineering/head-star-current126-alternative-apex-1541053-domain-001/report.json': 'ad641a24d554fb5591ee2ca208cc0bb99ecadbf4c8bc427dab3324c61f6d7194', 'work/962-engineering/head-star-current126-alternative-apex-1541053-netgen-001/arrays.json': '116fb3046ee444ee86797edd5159cd3be3dbad02c3ba390bf868268ce3b8b233', 'work/962-engineering/head-star-current126-alternative-apex-1541053-netgen-001/execution-receipt.json': '3e6026dd6ff5ca4d36aa9cd5d454f6fb48d690b5ed43df5c35994000d76a7320', 'work/962-engineering/head-star-current126-alternative-apex-1541053-netgen-001/fixture-report.json': 'dffc1f76994a4c8f4763a9b760325d31695ace4a744258d0aac3548e5854955d', 'work/962-engineering/head-star-current126-alternative-apex-1541053-netgen-001/frozen-contract.json': 'f77367f3241b813b3273d999d67c53b3bc6a093c5014b6ab36baf77ff6f5cd71', 'work/962-engineering/head-star-current126-alternative-apex-1558088-domain-001/report.json': '697db14bd19ca0baba2478fe5eaa7eba9a68ac2bb59be3f7c58cd84a15bbaf4d', 'work/962-engineering/head-star-current126-alternative-apex-1558088-netgen-001/arrays.json': 'ce1cfa2ee2d4b410a8e517a00d479d05272984614141ac1415635aece53e73d2', 'work/962-engineering/head-star-current126-alternative-apex-1558088-netgen-001/execution-receipt.json': 'e6a5d9ef6634cc48248888ccf00aadd9c258b644b9dc9f65d7df37e3c183aea7', 'work/962-engineering/head-star-current126-alternative-apex-1558088-netgen-001/fixture-report.json': '8328c3b25090896696ed1da63ab73fa00dbea109875b4459c2fdce8d73e621a4', 'work/962-engineering/head-star-current126-alternative-apex-1558088-netgen-001/frozen-contract.json': '92d63e225b033cec31a459ea1fe7e1d92a85de76b534220ff841573660749810', 'work/962-engineering/head-star-current126-alternative-apex-1570037-domain-001/report.json': '680bed2a73144c54a313c02f8d413ccf3eea3df018893e3b5b6cabc9e9dc226f', 'work/962-engineering/head-star-current126-alternative-apex-1570037-netgen-001/arrays.json': 'b780cbbc91ccc9598cdb6854e5d300b1a36dab5398ce4ea226d6b5f307efbb35', 'work/962-engineering/head-star-current126-alternative-apex-1570037-netgen-001/execution-receipt.json': 'bce6cd7728e2dd49dccadf4aafa618c823f4d48e12a8f72af742c1bef5cc9f3d', 'work/962-engineering/head-star-current126-alternative-apex-1570037-netgen-001/fixture-report.json': 'fe7ae43f709cfbe0a45c8c8fade6529bdf5e28ebb94e61e5c3da805168141c61', 'work/962-engineering/head-star-current126-alternative-apex-1570037-netgen-001/frozen-contract.json': '956022974846198cf54145dbfadfe24137ce95fbfb002f2fa0bb24bbddc92324', 'work/962-engineering/head-star-current126-alternative-apex-1611558-domain-001/report.json': '316a969267d3e150c87f6fa73285c5dbc73cf70238cf351dec144c26c252f355', 'work/962-engineering/head-star-current126-alternative-apex-1611558-netgen-001/arrays.json': '449138d2b052e773e762ab6d570573a490183090609ce37feda4d15b7dcedc40', 'work/962-engineering/head-star-current126-alternative-apex-1611558-netgen-001/execution-receipt.json': 'f97fd573549eeabcd2b8fb9000e2473473f1576c7e7bbeeccbece77a61283df3', 'work/962-engineering/head-star-current126-alternative-apex-1611558-netgen-001/fixture-report.json': '6ba457baed3c49a9e85f54a04927bf400df0f67dc6ef5dc806ecae9a8b6f1dfa', 'work/962-engineering/head-star-current126-alternative-apex-1611558-netgen-001/frozen-contract.json': '3c9f4a2ad574f2598c9ed8df8b265d2bec497cd4038c68887f237114840cf2a9', 'work/962-engineering/head-star-current126-alternative-apex-1611564-domain-001/report.json': '228667aff24848bba23ba65cb2d8a28ab80a0412f3fba013894e777e19f5caae', 'work/962-engineering/head-star-current126-alternative-apex-1611564-netgen-001/arrays.json': '91026ac7027e5da3ff10fb4c0d677c9e5de0b447d58fb80c3a105fd7b202030c', 'work/962-engineering/head-star-current126-alternative-apex-1611564-netgen-001/execution-receipt.json': '0524a24f368a13062db08a5f24cee381e174e26960e7de1d53207d3b9dd1ba5c', 'work/962-engineering/head-star-current126-alternative-apex-1611564-netgen-001/fixture-report.json': '7f6d0c321984e536d8d56970712736d55eb54fbff47e37205a84d7fa36e33c49', 'work/962-engineering/head-star-current126-alternative-apex-1611564-netgen-001/frozen-contract.json': '61f271bffeb0851593a322986be0f1f853c328a811de96198b74ed2c5575bc9c', 'work/962-engineering/head-star-current126-alternative-apex-1613030-domain-001/report.json': '775eeb533b2fb734b83cf493d1c039dfa46c725d61734e31b1f39dc5187bf4c3', 'work/962-engineering/head-star-current126-alternative-apex-1613030-netgen-001/arrays.json': 'c57389f71e937095c28408895b8fde398e7b9f3c61b1bd6ce55e918d6dc7edf0', 'work/962-engineering/head-star-current126-alternative-apex-1613030-netgen-001/execution-receipt.json': 'f36dbcc1c55611e1ac6cf66e829d5ad59090ffda8930079f684d7e2cd5e5a62f', 'work/962-engineering/head-star-current126-alternative-apex-1613030-netgen-001/fixture-report.json': 'f9fba0888d8eb1e0df027d9d571c1bd18ca18a357ad28577a329b15e97fc9df3', 'work/962-engineering/head-star-current126-alternative-apex-1613030-netgen-001/frozen-contract.json': '20ae7b0ba3aba16efcd624a013c8f2d203937e3f522c57c811985f20f6772ae1', 'work/962-engineering/head-star-current126-alternative-apex-1613794-domain-001/report.json': 'adf13499f5e2dad2feb8dcdf69b25273e1cbf241bde2a6f7c95c08315aa6244b', 'work/962-engineering/head-star-current126-alternative-apex-1613794-netgen-001/arrays.json': '322ee3eb4433f172b740e2f88e9212d845e48f7517dcb68d0faf2c6f168bced4', 'work/962-engineering/head-star-current126-alternative-apex-1613794-netgen-001/execution-receipt.json': 'b53ea8047b3724dd268c478aac663d97c4b83fbb8f1d99808a3a358f01c083b5', 'work/962-engineering/head-star-current126-alternative-apex-1613794-netgen-001/fixture-report.json': 'dbdea591e6b750072d604a0e968c9e9d51b4de02bd5d3951d6b514a91c5704bf', 'work/962-engineering/head-star-current126-alternative-apex-1613794-netgen-001/frozen-contract.json': '5798a58d1728a1428d5fb09922fa9f907436af1e983d571a0166e1fec034c038', 'work/962-engineering/head-star-current126-alternative-apex-1613795-domain-001/report.json': 'bfabc6886e377d545b802f29a7f223cfb9b93b10b5cd451d99303fc852c32062', 'work/962-engineering/head-star-current126-alternative-apex-1613795-netgen-001/arrays.json': '63f5a8bf484ca29bdbf8ced77a92694b52a7a73a56f321a897296045006720e8', 'work/962-engineering/head-star-current126-alternative-apex-1613795-netgen-001/execution-receipt.json': '6d75b661571cb7dfbef957959ee28d4f1d0f9bd0ad3ba6ab270f8c034831f680', 'work/962-engineering/head-star-current126-alternative-apex-1613795-netgen-001/fixture-report.json': '63554e773681ba29e36f051d159512f0aefe94c9906edf0f2b69f11e31a61210', 'work/962-engineering/head-star-current126-alternative-apex-1613795-netgen-001/frozen-contract.json': '4cb540c22185924cf583901e8f224bfcd18856d7b8515c586d3b44f7fed7f670', 'work/962-engineering/head-star-current126-alternative-batch-shells-001/report.json': '721e05802e305a124b99f97c779426e3d7b8960cab30fbabc3d93ee318e3de73', 'work/962-engineering/head-star-current126-alternative-case-domains-actuals-prep-001/apex-1433071.json': '981ec55eeec7584ee88cc0f7902d29e0c87156b026d8545fe3e59301983be4a9', 'work/962-engineering/head-star-current126-alternative-case-domains-actuals-prep-001/apex-1468585.json': '6e72b4659adaace7dd31eca77e9918951a9ae9283b7a5b9af2762999a83ba3a8', 'work/962-engineering/head-star-current126-alternative-case-domains-actuals-prep-001/apex-1481549.json': '70332f06b82e2fc44d3686a5ba28886b150a8993e4a439e0036ba7748183da5e', 'work/962-engineering/head-star-current126-alternative-case-domains-actuals-prep-001/apex-1488093.json': '477033383aac33fc8702380643bc90538803829963680f3c92ed9db76ed3d4aa', 'work/962-engineering/head-star-current126-alternative-case-domains-actuals-prep-001/apex-1508641.json': 'e3c1d4f625bdb9af7448ad2ba40e670c7720f04f653219741d41dfdc64392fc1', 'work/962-engineering/head-star-current126-alternative-case-domains-actuals-prep-001/apex-1515013.json': 'ff8887a69b07c3d571cb161d1e28a2232a4c8620762782357ded993d97d1977b', 'work/962-engineering/head-star-current126-alternative-case-domains-actuals-prep-001/apex-1538046.json': '7bbeb40e478e84a0e3cd1d89a03ca9826622b9c87a291af801e2727b86088e36', 'work/962-engineering/head-star-current126-alternative-case-domains-actuals-prep-001/apex-1541053.json': 'de64125763f8e8059557911ac7b4caf1d250563b1c3ac501204c6627e3cf7476', 'work/962-engineering/head-star-current126-alternative-case-domains-actuals-prep-001/apex-1558088.json': '8a1346faab0cc90c5219fdd592e037a8f0c6f1b28d83a2ee1721b394b280d285', 'work/962-engineering/head-star-current126-alternative-case-domains-actuals-prep-001/apex-1570037.json': '41d0d895820e3466a3f48d7412cf63b4397bf2b6b24400c2ec51341c02e8e27a', 'work/962-engineering/head-star-current126-alternative-case-domains-actuals-prep-001/apex-1611558.json': 'd58ae2fa2a5bbf9b792e736e08fe97a6229b31883e60bb8dbc338437fdab4d3e', 'work/962-engineering/head-star-current126-alternative-case-domains-actuals-prep-001/apex-1611564.json': '4767aac7aa0c9a27caf9cb9d6f28e52bf617103867018d2b0cc1d7c06dcf86a8', 'work/962-engineering/head-star-current126-alternative-case-domains-actuals-prep-001/apex-1613030.json': 'e378ab43b017b644a652b11375db6aa92522dd033870c7bf4537f057d7cef904', 'work/962-engineering/head-star-current126-alternative-case-domains-actuals-prep-001/apex-1613794.json': '4b0d46554a4da8bda2fff8e00432b3f1378f067aaab475b7ddb00968cd34ee8d', 'work/962-engineering/head-star-current126-alternative-case-domains-actuals-prep-001/apex-1613795.json': 'beb428bf43b1a0c902dfdfbdef3d32f2cede83b86dbbeb5ac8d863f26e60a951', 'work/962-engineering/head-star-current126-alternative-case-domains-prep-001/certify_domain.py': '8aad95004cd2bfb440e1436c679d8a5476cf84247a6911b4daa319b10f1f4558', 'work/962-engineering/head-star-current126-alternative-combined-application-prep-001/admitted-manifest.json': '5270a56b18e1dbefc1dd117fb38a53e1fd8a1bcd5bbf9868943896a46b1c6773', 'work/962-engineering/head-star-current126-alternative-local-stages-prep-001/case-inputs/apex-1433071/observation.json': '031dbd7c212086fcf00e5d97f11ce820cecddf066710b94884220dd6f60372e7', 'work/962-engineering/head-star-current126-alternative-local-stages-prep-001/case-inputs/apex-1433071/screen.json': '2bd93747ad40594ed8dfa21031fb40a3b0562dfb6b5e1b8c49b7b2c6ff759e4e', 'work/962-engineering/head-star-current126-alternative-local-stages-prep-001/case-inputs/apex-1433071/shell.json': 'f115393a9a4a665b0099932de3d6f8e09bf9f093b5fc9f214c46befa3afd42ee', 'work/962-engineering/head-star-current126-alternative-local-stages-prep-001/case-inputs/apex-1468585/observation.json': '6147a5fd7b57261a1f960da08c4174bfc98bd7ff57c0dd0981efa7dae96fdb8a', 'work/962-engineering/head-star-current126-alternative-local-stages-prep-001/case-inputs/apex-1468585/screen.json': '44ed72502bf35f48ffed14bbc707172e9fd769b2f50ca87811b257ad4a4f61d1', 'work/962-engineering/head-star-current126-alternative-local-stages-prep-001/case-inputs/apex-1468585/shell.json': '23b289afc63c85fa2fe88a46298aa12f53767f3f303e1714d48d86fdf92c17ed', 'work/962-engineering/head-star-current126-alternative-local-stages-prep-001/case-inputs/apex-1481549/observation.json': '3bd0356b884d7d505e8059de575c16bf876d1ce002502113770140c03f1b7f0b', 'work/962-engineering/head-star-current126-alternative-local-stages-prep-001/case-inputs/apex-1481549/screen.json': 'e9d8f91b74c26125ae4986670a6e13d55003a6e67845d2c344514012d9e8aaaf', 'work/962-engineering/head-star-current126-alternative-local-stages-prep-001/case-inputs/apex-1481549/shell.json': 'a48c3094a2f5a69b5ae81153f4c488f91cbb784e69393a3d10e437a8cca9fd60', 'work/962-engineering/head-star-current126-alternative-local-stages-prep-001/case-inputs/apex-1488093/observation.json': '9d3c3d689cab4e447eb3f9c3d295640267795c54cea946341b853a8fe3601c1c', 'work/962-engineering/head-star-current126-alternative-local-stages-prep-001/case-inputs/apex-1488093/screen.json': 'b59f5a213a9489e073957cac7ad684a5598b12415109367efe64388bee086119', 'work/962-engineering/head-star-current126-alternative-local-stages-prep-001/case-inputs/apex-1488093/shell.json': 'f7e374286cc6c85a411b125c174bf02d6db9889b0d23ce6b7f62d2fe0ffd219d', 'work/962-engineering/head-star-current126-alternative-local-stages-prep-001/case-inputs/apex-1508641/observation.json': '8ed107d91d00a7dfa08572f915baf4a206069bc1a656a299cec70ff6c4b08669', 'work/962-engineering/head-star-current126-alternative-local-stages-prep-001/case-inputs/apex-1508641/screen.json': '158ef64be95562e9ab0e0b5a83c684189aafc1f0a774d224fdad17045ec9ba7d', 'work/962-engineering/head-star-current126-alternative-local-stages-prep-001/case-inputs/apex-1508641/shell.json': '244a00b0e2371539a9690f0486da4a054366a62b9dbc057427cf66d46e1f7e00', 'work/962-engineering/head-star-current126-alternative-local-stages-prep-001/case-inputs/apex-1515013/observation.json': '007d9fc73d56ffbeb7c04daccd6c4ba75c3f742f4b1ff18a54d7bd7b7a6f58f3', 'work/962-engineering/head-star-current126-alternative-local-stages-prep-001/case-inputs/apex-1515013/screen.json': 'cdef77cb49d71a54924118e6698c907defd98b7dea90371f174de18fd61d7bdc', 'work/962-engineering/head-star-current126-alternative-local-stages-prep-001/case-inputs/apex-1515013/shell.json': '0047cad72700c6f2ef59d65c1b68158b34330eceeb79d83ae5d32bc282fa099e', 'work/962-engineering/head-star-current126-alternative-local-stages-prep-001/case-inputs/apex-1538046/observation.json': '8e06e1b7fc1c4c2e0ccdbcf00f01b6048662a8bbac7d1d6cec0282a3e24de5e4', 'work/962-engineering/head-star-current126-alternative-local-stages-prep-001/case-inputs/apex-1538046/screen.json': 'a12868a622697751d03da67eaa1f003de435c0803c346f09fcbcafc3384a856d', 'work/962-engineering/head-star-current126-alternative-local-stages-prep-001/case-inputs/apex-1538046/shell.json': 'a2445ce59d8ef870cb7ed01b26ceff3204acbfdce430af1391ac87e522d37708', 'work/962-engineering/head-star-current126-alternative-local-stages-prep-001/case-inputs/apex-1541053/observation.json': '98cab308100aaf08da991307fcbf9d0e388c20e313f2c73ed24e81e90955de2b', 'work/962-engineering/head-star-current126-alternative-local-stages-prep-001/case-inputs/apex-1541053/screen.json': '0de8eec52b7804ce82ff7e354fc2d60e42b0fb8bcdf7f9caae54cff3cafc932d', 'work/962-engineering/head-star-current126-alternative-local-stages-prep-001/case-inputs/apex-1541053/shell.json': '574a8c1947de4d5f3a0766d578224d1c3c0e80cf1fa0b7ccde22ceb74f9156ce', 'work/962-engineering/head-star-current126-alternative-local-stages-prep-001/case-inputs/apex-1558088/observation.json': 'd561d9c4ac9dfa28fa9e90851b2e9fe87c1e05421a5abfd9f01b02d964f71bcc', 'work/962-engineering/head-star-current126-alternative-local-stages-prep-001/case-inputs/apex-1558088/screen.json': '486c43b2ccd27621b6f650b4a7c9db84cba22768115a44227118f88cb9300369', 'work/962-engineering/head-star-current126-alternative-local-stages-prep-001/case-inputs/apex-1558088/shell.json': '2ec45f0150dd6bddb959f32228beea6d95faa04f4fa28cc5a6da808f05ad7319', 'work/962-engineering/head-star-current126-alternative-local-stages-prep-001/case-inputs/apex-1570037/observation.json': 'bd6f2556c3a22cbecca776dee8b7fc6f74320e76ebc3589370836e07d731b012', 'work/962-engineering/head-star-current126-alternative-local-stages-prep-001/case-inputs/apex-1570037/screen.json': 'e6f3303e6ef7c08ddb2bb6611c0171dd2e4f671c5d64e14f9847b9de031e13ba', 'work/962-engineering/head-star-current126-alternative-local-stages-prep-001/case-inputs/apex-1570037/shell.json': 'f719edf687577e21ad84ddff54afcf6da2dec4c03a6e54f765fd8e03d6985696', 'work/962-engineering/head-star-current126-alternative-local-stages-prep-001/case-inputs/apex-1611558/observation.json': 'ea8c393a0935bfe517791f41de8fec1a94201e2f5e54e720fdb91aeabd7df699', 'work/962-engineering/head-star-current126-alternative-local-stages-prep-001/case-inputs/apex-1611558/screen.json': '570727d97283db13fcca234d427e4479ee4b04e08e220f718e4ed3c9ec228319', 'work/962-engineering/head-star-current126-alternative-local-stages-prep-001/case-inputs/apex-1611558/shell.json': '1a0e6e4c224c9454250257d0ca383900ae54e863af2af49a5a776c96660e9038', 'work/962-engineering/head-star-current126-alternative-local-stages-prep-001/case-inputs/apex-1611564/observation.json': '5682cc3721f117aff9a2701582164e3cfb3c98e3b695edcbd60ba6d64ba397fb', 'work/962-engineering/head-star-current126-alternative-local-stages-prep-001/case-inputs/apex-1611564/screen.json': 'f43f4ca08f212ef0543d9e0d0ab175f221e56e6c1f977552a761ca5115cc4a6a', 'work/962-engineering/head-star-current126-alternative-local-stages-prep-001/case-inputs/apex-1611564/shell.json': '76707f26feeba67e3887997f6d984778b14288a2eef4329e25b899eca002c6aa', 'work/962-engineering/head-star-current126-alternative-local-stages-prep-001/case-inputs/apex-1613030/observation.json': '7aec06693db4583c17a0935c73ab83570d5c4c09c6514b34fbb149457876a9fa', 'work/962-engineering/head-star-current126-alternative-local-stages-prep-001/case-inputs/apex-1613030/screen.json': 'bc302ce8dfe2fc558374869c8f71ae4721fec61039f1318991ae7c46bda01690', 'work/962-engineering/head-star-current126-alternative-local-stages-prep-001/case-inputs/apex-1613030/shell.json': 'e16db5225dc4dce18643a289893238e2dddbbb3f7183681dcea15f92fc5a2cc0', 'work/962-engineering/head-star-current126-alternative-local-stages-prep-001/case-inputs/apex-1613794/observation.json': 'b6646b935e4c5b0d9d281cdcf4ed488fbc233b8228e81b6075c10fbaec92a49d', 'work/962-engineering/head-star-current126-alternative-local-stages-prep-001/case-inputs/apex-1613794/screen.json': '81fc573e35f878264f78851a92d5738ea963682ce15b11b8bf56204163e0d6d3', 'work/962-engineering/head-star-current126-alternative-local-stages-prep-001/case-inputs/apex-1613794/shell.json': 'b56df75b4089a9eb94f470493ea477e22ec02793df9d73231156f6da20834c98', 'work/962-engineering/head-star-current126-alternative-local-stages-prep-001/case-inputs/apex-1613795/observation.json': 'b2b36d690d39ea4e30f6f4dd993ae18a9b8f45721c45a51adbbd383e2c6f2a8a', 'work/962-engineering/head-star-current126-alternative-local-stages-prep-001/case-inputs/apex-1613795/screen.json': '4e25cbfb240a46ce3256adc00aa38efa28b42059d555ed2ec344d001777a4d16', 'work/962-engineering/head-star-current126-alternative-local-stages-prep-001/case-inputs/apex-1613795/shell.json': 'a481f208fd95d89dea25ad15e63ce67e8b74c1d55d885f26748dd2cbfe7edc66', 'work/962-engineering/head-star-current126-alternative-local-stages-prep-001/case-manifest.json': 'e83b8824581d68c3b3ca29acbd9f50573833561298159cf7969bbd46eb722e4c', 'work/962-engineering/head-star-current126-alternative-union-context-prep-001/case-manifest.json': '498127125485ace52a61f5668a31d0e07045704af0b961490427a173c0f4aac7', 'work/962-engineering/head-star-current126-alternative-union-context-prep-001/held-contract.json': 'f0e86d58fb755cee6c69ea3643e5072117976fb34a108e1b0405eeb75b36fb79', 'work/962-engineering/head-star-current126-alternative-union-context-prep-001/reader.py': '4a78676cb1b8dbf3ad3e773dd5d881c943e83083730b6fa7e06e291349334df6', 'work/962-engineering/head-star-current126-full-stars-001/frozen-contract.json': 'd579a794f18bc9f7c4e153cb2042f32cb32b2c6b2f2235cec2edbef8aba91317', 'work/962-engineering/head-star-current126-full-stars-001/readback-report.json': 'ac40521a4add15f1bb414d7d1a1c2cd231a0107278b6fe43ec38dad27c269e1a', 'work/962-engineering/head-star-current126-full-stars-execution-prep-001/actual-contract.json': 'd579a794f18bc9f7c4e153cb2042f32cb32b2c6b2f2235cec2edbef8aba91317', 'work/962-engineering/head-star-current126-full-stars-prep-001/reader.py': '2348c032ecbbb694563978cb333aff1a7e4d37a5052c3ed841a7128bf797409c', 'work/962-engineering/head-star-current126-full-stars-result-peer-001/bindings.json': 'c2c33a39a1cb3f393288ee4a7f344f17d45bfa44c8c81347fe07cca6421b66d5', 'work/962-engineering/head-star-current126-full-stars-result-peer-001/review.json': 'f22ee8bfc026caec2b6182bddfdfa250795ea3ee698c73c41a823a6dd1f5a4c4', 'work/962-engineering/head-star-current126-full-stars-root-execution-001/result-peer-acceptance.json': 'f66d5857a0fa75352c3880ab2cd7bbc0bcae73833254f39423fd48971ebd52d9', 'work/962-engineering/head-star-current129-full-stars-root-execution-001/launch-deviation-001.json': 'd60fff297c6c45dc92e117262e36ffde36e2169d53fcd32ce2b79fabde5eebc3', 'work/962-engineering/head-star-current204-combined-application-prep-001/reader.py': 'c66da821a1d98794ed78f403067e02c349c11a59d6c22de72e587b05e5fc82f5', 'work/962-engineering/apex1613031-head-application-001/head-volume.msh': '48b66aafbd9f1eb69e44305982186e966fe8f041d9b4a6a59be4b610b5d12e08'}
CASE_COUNT=15;NMAX=1613977;EMAX=32159077;BOUNDARY=871731
RUNTIME={'python':'3.10.11','numpy':'2.0.2','gmsh':'4.15.2','machine':'arm64'}
OPTIONS={'General.NumThreads':2,'Mesh.MaxNumThreads3D':2,'Mesh.Renumber':0,
 'Mesh.Optimize':0,'Mesh.OptimizeNetgen':0,'Mesh.Binary':1,'Mesh.SaveAll':1,'Mesh.MshFileVersion':4.1}
CONTROLS={'hard_wall_seconds':1200,'sampled_RSS_stop_bytes':8*1024**3,'sampled_output_stop_bytes':1024**3,'native_threads':2,'automatic_retry':False}
COUNTS={'removeElements':1,'setNode':15,'addNodes':1,'addElementsByType':1,'rebuildNodeCache':1,
 'rebuildElementCache':1,'write_mesh':1,'generate':0,'optimize':0,'createGeometry':0,'reclassifyNodes':0,'solve':0}
FORBIDDEN=['generation_authorized','optimization_authorized','reclassification_authorized','renumbering_authorized',
 'surface_TRI_insertion_authorized','stitching_authorized','head_PDE_authorized','engineering_accepted','physics_qualified','material_qualified','process_calibrated','manufacturing_authorized']
QUALIFICATION=dict(native_application_authorized=False,head_execution_authorized=False,stitching_authorized=False,
 engineering_accepted=False,physics_qualified=False,manufacturing_authorized=False,material_qualified=False,process_calibrated=False,head_PDE_authorized=False)
def sha(path):
 h=hashlib.sha256()
 with Path(path).open('rb') as f:
  for block in iter(lambda:f.read(1024**2),b''):h.update(block)
 return h.hexdigest()

def json_sha(value):
 return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()

def selected(path,names,namespace):
 tree=ast.parse((ROOT/path).read_text());rows=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in names]
 if {n.name for n in rows}!=set(names):raise ValueError('Exact selected frozen helper definitions required')
 exec(compile(ast.Module(body=rows,type_ignores=[]),path,'exec'),namespace)

def context_admission_records(c):
 """No native import is reachable from the held null-context state."""
 admission=c.get('context_admission')
 paths={'report':CONTEXT,'contract':CONTEXT_CONTRACT,
  'receipt':'work/962-engineering/head-star-current126-alternative-union-context-001/execution-receipt.json',
  'root_closed':'work/962-engineering/current126-alternative-union-context-root-execution-001/closed-result.json',
  'peer':'work/962-engineering/current126-alternative-union-context-result-peer-001/review.json',
  'bindings':'work/962-engineering/current126-alternative-union-context-result-peer-001/bindings.json',
  'root_acceptance':'work/962-engineering/current126-alternative-union-context-root-execution-001/result-peer-acceptance.json'}
 if (c.get('fresh_context_result_and_peer_root_admitted') is not True or type(admission) is not dict or set(admission)!=set(paths)):
  raise ValueError('Fresh completed current15 context and exact peer/root admission are pending')
 for role,path in paths.items():
  row=admission[role]
  if (type(row) is not dict or set(row)!={'path','sha256','bytes'} or row.get('path')!=path
      or type(row.get('bytes')) is not int or row['bytes']<=0 or type(row.get('sha256')) is not str
      or len(row['sha256'])!=64 or any(x not in '0123456789abcdef' for x in row['sha256'])
      or c.get('input_hashes',{}).get(path)!=row['sha256']):
   raise ValueError('Every future context report/control/peer/root must be a direct exact input pin')
 return admission


def require_contract(c):
 if (c.get('schema')!='962-current126-alternative15-combined-head-application/v1' or c.get('native_execution_authorized') is not True
     or c.get('partial_head_replacement_authorized') is not True or c.get('root_and_peer_review_complete') is not True
     or c.get('selected_runtime_review_complete') is not True or c.get('automatic_retry') is not False or c.get('head_execution_authorized') is not False
     or any(c.get(k) is not False for k in FORBIDDEN) or c.get('options')!=OPTIONS
     or c.get('declared_operation_counts')!=COUNTS or c.get('controls')!=CONTROLS or c.get('output_directory')!=OUTPUT or ROOT/OUTPUT!=OUT):
  raise ValueError('Separate reviewed one-partial-replacement actual authority required')
 admission=context_admission_records(c)
 if c.get('declared_controller_command_conformant') is not False or c.get('upstream_census_launch_deviation_sha256')!=FIXED_INPUTS[DEVIATION]:raise ValueError('Historical d60 false scope required')
 if any(c['input_hashes'].get(k)!=v for k,v in FIXED_INPUTS.items()):raise ValueError('Every consumed source/data/peer requires its exact direct pin')
 for name,digest in c['input_hashes'].items():
  path=ROOT/name
  if Path(name).is_absolute() or '..' in Path(name).parts or path.is_symlink() or not path.resolve().is_relative_to(ROOT) or sha(path)!=digest:
   raise ValueError('Bound input drift: '+name)
 for record in admission.values():
  if (ROOT/record['path']).stat().st_size!=record['bytes']:raise ValueError('Context descriptor byte count changed')
 original=json.loads((ROOT/CONTEXT_CONTRACT).read_text())
 if (original['reader_sha256']!=FIXED_INPUTS[CONTEXT_SOURCE] or original['runner_sha256']!='4fb37080e1f3847b8b1d14d5df467799d8e9f7bf81b0a09170e5850857de3943'
     or original['MSH_sha256']!=MSH_SHA or original['MSH_bytes']!=235786462):raise ValueError('Exact current15 context source/controller/parent contract required')
 for key in ['external_runtime_hashes','runtime_sha256s','runtime','native_python','numpy_init','numpy_init_sha256']:
  if c[key]!=original[key]:raise ValueError('Selected original runtime scope changed: '+key)
 if sha(Path(c['numpy_init']))!=c['numpy_init_sha256']:raise ValueError('Selected NumPy init changed')
 if len(c['external_runtime_hashes'])!=3:raise ValueError('Exactly three selected native runtime identities required')
 for name,digest in c['external_runtime_hashes'].items():
  if sha(name)!=digest:raise ValueError('Selected runtime drift')
 if (sha(OUT/'reader.py')!=c['reader_sha256'] or sha(OUT/'run_readback.py')!=c['runner_sha256']
     or sha(Path(sys.executable).resolve())!=c['runtime']['python_executable_sha256']):raise ValueError('Materialized source or interpreter changed')

def require_domain(domain,entry,observation,shell,a):
 row=entry['local_case'];records=entry['completed_domain'];old={r['tetrahedron_tag']:r['node_tags'] for r in observation['native_ordered_cell_rows']}
 if (domain.get('schema')!='962-current126-alternative-fixed15-one-case-domain-result/v1' or domain.get('status')!='same_compact_oriented_local_domain'
     or domain.get('case_apex')!=row['apex'] or domain.get('case_record_sha256')!=row['source_record_sha256']
     or any(domain.get(k) is not True for k in ['exact_old_pair_embedding','exact_candidate_pair_embedding','local_domain_equivalence_proved','bound_inputs_unchanged','exact_common_shell_coordinate_words','exact_identical_oriented_boundary','exact_signed_volume_identity'])
     or domain.get('pair_failures')!={'old':0,'candidate':0} or domain.get('qualification')!=QUALIFICATION
     or domain.get('source_sha256')!=FIXED_INPUTS[DOMAIN_SOURCE] or domain.get('contract_sha256')!=records['actual']['sha256']
     or domain.get('source_candidate_report_sha256')!=row['records']['worker']['sha256']
     or domain.get('source_candidate_arrays_sha256')!=row['records']['arrays']['sha256']
     or domain.get('source_candidate_independent_peer_sha256')!=FIXED_INPUTS[LOCAL_PEER]
     or domain.get('parent_context_sha256') is not None or domain.get('parent_owner_context_queried') is not False
     or domain.get('outside_owner_context_established') is not False or domain.get('declared_controller_command_conformant') is not False
     or domain.get('source_census_sha256')!=FIXED_INPUTS[FIRST] or domain.get('source_partial_report_sha256')!=FIXED_INPUTS[ORIGINAL_WORKER]
     or domain.get('source_candidate_root_acceptance_sha256')!=FIXED_INPUTS[LOCAL_ACCEPT]
     or domain.get('source_candidate_peer_bindings_sha256')!=FIXED_INPUTS[LOCAL_BINDINGS] or domain.get('candidate_interior_node_tags')!=row['candidate_interior_node_tags']
     or domain.get('native_optimizer_or_meshwrite_calls')!=0 or domain.get('coordinates_changed') is not False
     or tuple(domain.get(k) for k in ['old_complete_unordered_pairs','candidate_complete_unordered_pairs','complete_unordered_pairs','plane_triples_enumerated'])!=tuple(row[k] for k in ['old_unordered_pairs','candidate_unordered_pairs','total_pairs','plane_triples'])):
  raise ValueError('Exact accepted same-case completed domain source/result identities required')
 for record in row['records'].values():
  if domain['input_hashes'].get(record['path'])!=record['sha256']:raise ValueError('Every same-case domain source/native record must directly join')
 expected_map={str(t):i+1 for i,t in enumerate(shell['local_to_global_node_tags'])};expected_map[str(row['apex'])]=row['NV']+1
 if domain.get('original_global_to_comparison_node_tags')!=expected_map:raise ValueError('Exact original comparison map required')
 expected_faces=sorted(min(tuple(f[i:]+f[:i]) for i in range(3)) for f in [r['local_node_tags'] for r in shell['oriented_triangle_rows']])
 for name,cells,count,internal in [('old',{t:[expected_map[str(n)] for n in conn] for t,conn in old.items()},row['old_unordered_pairs'],row['original_internal_pairs']),('candidate',dict(zip(a['tetra_tags'],a['tetra_node_tags'])),row['candidate_unordered_pairs'],row['candidate_internal_pairs'])]:
  data=domain[name];pairs=domain['pair_results'][name]
  if (data['cell_count']!=len(cells) or data['internal_face_pairs']!=internal or data.get('all_exact_positive') is not True
      or [tuple(f) for f in data['oriented_boundary']]!=expected_faces or len(pairs)!=count
      or [tuple(p['tetrahedron_tags']) for p in pairs]!=list(combinations(sorted(cells),2))
      or any(p.get('intersection_equals_tagged_shared_simplex') is not True or p.get('plane_triples_enumerated')!=56 or p.get('illegal_intersection_vertices')!=0 or p.get('all_illegal_rational_witnesses')!=[] for p in pairs)):
   raise ValueError('Complete accepted same-case saved pair coverage/common shell required; no predicate replay')
 if domain['old']['exact_signed_volume_mm3']!=domain['candidate']['exact_signed_volume_mm3'] or domain['old']['exact_signed_volume_mm3']!={k:str(v) for k,v in shell['exact_enclosed_volume_mm3'].items()}:
  raise ValueError('Exact same-case volume identity required')
 exact=domain['candidate']['quality_rows']
 if len(exact)!=row['M'] or [r['tetrahedron_tag'] for r in exact]!=a['tetra_tags']:raise ValueError('Complete exact candidate quality associations required')
 for proof,conn in zip(exact,a['tetra_node_tags']):
  det=proof['exact_determinant_mm3'];q=proof['exact_SICN_squared']
  if (proof['ordered_node_tags']!=conn or proof.get('exact_point1_gate_passed') is not True
      or Fraction(int(det['numerator']),int(det['denominator']))<=0 or Fraction(int(q['numerator']),int(q['denominator']))<Fraction(1,100)):
   raise ValueError('Every stored candidate exact determinant/quality gate required')
 closed=json.loads((ROOT/records['root_closed']['path']).read_text())
 if (closed['returncode']!=0 or closed['stop_reason'] is not None or closed['error'] is not None or closed['signals']!=[]
     or closed['waited_reaped'] is not True or closed['owned_group_absent'] is not True
     or closed['actual']!=records['actual'] or closed['outputs']!={'report.json':records['report']}):
  raise ValueError('Exact natural stopped same-case domain closure required')

def allocate_case(row,shell,a,nmax,emax):
 """Only fixed saved tag/row associations; first actual interior tag is a storage slot."""
 interior=row['candidate_interior_node_tags'];tags=a['node_tags'];xyz=a['coordinates_mm'];old=row['old_tetrahedron_tags']
 if (interior!=sorted(set(interior)) or len(interior)!=row['I'] or row['I']<1 or row['M']<row['K']
     or tags!=sorted(set(tags)) or len(tags)!=len(xyz) or len(tags)!=row['N']
     or set(tags)!=set(range(1,row['NV']+1))|set(interior) or any(type(t) is not int or t<=row['NV'] for t in interior)
     or old!=sorted(set(old)) or len(old)!=row['K'] or a['tetra_tags']!=sorted(set(a['tetra_tags']))
     or len(a['tetra_tags'])!=row['M'] or len(a['tetra_node_tags'])!=row['M']
     or any(len(p)!=3 or any(type(v) is not float or not math.isfinite(v) for v in p) for p in xyz)
     or any(len(c)!=4 or len(set(c))!=4 or not set(c)<=set(tags) for c in a['tetra_node_tags'])
     or set().union(*(set(c) for c in a['tetra_node_tags']))!=set(tags)):
  raise ValueError('Complete saved tag lookup/dynamic counts/no-orphan storage policy required')
 coordinates=dict(zip(tags,xyz));fresh=list(range(nmax+1,nmax+row['I']));slots=old+list(range(emax+1,emax+row['M']-row['K']+1))
 if (len(shell['local_to_global_node_tags'])!=row['NV'] or len(set(shell['local_to_global_node_tags']))!=row['NV'] or row['apex'] in shell['local_to_global_node_tags']
     or any(type(t) is not int or t<=0 or t>nmax for t in [row['apex'],*shell['local_to_global_node_tags']])
     or any(type(t) is not int or t<=0 or t>emax for t in old)
     or max([nmax,*fresh,emax,*slots])>=2**64 or len(slots)!=len(set(slots))):raise ValueError('Tag allocation overflow/collision')
 mapping={i+1:t for i,t in enumerate(shell['local_to_global_node_tags'])};mapping.update(dict(zip(interior,[row['apex'],*fresh])))
 if len(mapping)!=row['N'] or len(set(mapping.values()))!=row['N']:raise ValueError('Complete injective local/global storage map required')
 proposed={mapping[t]:list(coordinates[t]) for t in tags}
 replacement={slot:[mapping[t] for t in conn] for slot,conn in zip(slots,a['tetra_node_tags'])}
 return dict(apex=row['apex'],node_map=mapping,fresh_nodes=fresh,element_slots=slots,replacement=replacement,proposed=proposed,
  local_tetra_tags=a['tetra_tags'],interior_node_tags=interior)

def make_case(context,first):
 manifest=json.loads((ROOT/MANIFEST).read_text());accept=json.loads((ROOT/DOMAIN_ACCEPT).read_text());peer=json.loads((ROOT/DOMAIN_PEER).read_text())
 if (manifest['case_count']!=CASE_COUNT or len(manifest['cases'])!=CASE_COUNT
     or manifest['accepted_apices']!=accept['accepted_domain_case_tags'] or manifest['accepted_apices']!=sorted(set(manifest['accepted_apices']))
     or [r['local_case']['apex'] for r in manifest['cases']]!=manifest['accepted_apices']
     or accept['decision']!='ACCEPT_COMPLETE15_RELATIVE_LOCAL_DOMAIN_ASSOCIATIONS_FOR_CURRENT_PARENT_CONTEXT_PREPARATION_ONLY'
     or accept['peer_review']['sha256']!=FIXED_INPUTS[DOMAIN_PEER] or accept['peer_bindings']['sha256']!=FIXED_INPUTS[DOMAIN_BINDINGS]
     or accept['source']['sha256']!=FIXED_INPUTS[DOMAIN_SOURCE] or accept['current_parent']!={'sha256':MSH_SHA,'bytes':235786462}
     or accept['whole_head_quality_accepted'] is not False or accept['head_mesh_unchanged'] is not True
     or peer['decision']!='CLEAR_COMPLETED_SAVED15_RELATIVE_LOCAL_DOMAIN_ASSOCIATIONS_ONLY'
     or peer['bindings']!=accept['peer_bindings'] or peer['declared_controller_command_conformant'] is not False
     or context['status']!='complete_current126_alternative15_union_parent_context_census' or context['complete_context_census'] is not True
     or context['original_parent_MSH_sha256']!=MSH_SHA or context['original_parent_MSH_bytes']!=235786462
     or context['selected_apex_tags']!=manifest['accepted_apices']
     or (context['full_node_count'],context['full_TET4_count'])!=(1097222,3621771)
     or context['declared_controller_command_conformant'] is not False
     or context['independently_derived_global_maxima']!={'node':NMAX,'element_all_dimensions':EMAX}):
  raise ValueError('Exact root accepted15 manifest and newly admitted current126 parent context required')
 batch=json.loads((ROOT/BATCH).read_text());records={r['apex']:r for r in batch['all_candidate_star_records']}
 local_peer=json.loads((ROOT/LOCAL_PEER).read_text());native={r['node_tag']:r for r in context['selected_original_native_node_rows']}
 case=dict(cases=[],apices=manifest['accepted_apices'],old={},replacement={},proposed={},classes={},fresh_nodes=[],apex_parameters={},nmax=NMAX,emax=EMAX)
 nmax=NMAX;emax=EMAX;vertices=set()
 for entry in manifest['cases']:
  row=entry['local_case'];record=records[row['apex']];observation=record['observation'];shell=record['shell']
  encoded=lambda value:(json.dumps(value,indent=2,allow_nan=False)+'\n').encode()
  if any(hashlib.sha256(encoded(value)).hexdigest()!=row[key] for value,key in [(record,'source_record_sha256'),(shell,'shell_serialized_sha256'),(observation,'observation_serialized_sha256')]):raise ValueError('Immutable original batch subrecord/shell/observation required')
  original={r['tetrahedron_tag']:r['node_tags'] for r in observation['native_ordered_cell_rows']};present=set().union(*(set(c) for c in original.values()))
  if sorted(present)!=row['old_vertex_tags'] or present&vertices or len(original)!=row['K'] or sorted(original)!=row['old_tetrahedron_tags'] or any(row['apex'] not in c for c in original.values()):raise ValueError('Complete original vertex-disjoint stars required, including initially good cells')
  vertices.update(present)
  worker=json.loads((ROOT/row['records']['worker']['path']).read_text());arrays=json.loads((ROOT/row['records']['arrays']['path']).read_text())
  ns=dict(ROOT=ROOT,CASE=row,INPUTS=FIXED_INPUTS,FIXED_INPUTS=FIXED_INPUTS,CENSUS_DATA=first,CENSUS=FIRST,BATCH=BATCH,PEER=LOCAL_PEER,PEER_BINDINGS=LOCAL_BINDINGS,WORKER=row['records']['worker']['path'],ARRAYS=row['records']['arrays']['path'],Fraction=Fraction,struct=struct,math=math,json=json,hashlib=hashlib,sha=sha)
  selected(DOMAIN_SOURCE,['case_record','census_join','accepted_native_records','saved_candidate'],ns)
  if ns['case_record']()!=record:raise ValueError('Exact current embedded source case required')
  ns['census_join'](observation,shell);ns['accepted_native_records'](worker);ns['saved_candidate'](worker,arrays,shell,local_peer)
  if entry['completed_domain']!=accept['case_reports'][str(row['apex'])]:raise ValueError('Every accepted current domain descriptor required')
  a=arrays['saved_reopen'];domain=json.loads((ROOT/entry['completed_domain']['report']['path']).read_text());require_domain(domain,entry,observation,shell,a)
  part=allocate_case(row,shell,a,nmax,emax);part['old']=original
  for tag in present:
   observed=native[tag];expected=next(r for r in observation['selected_node_rows'] if r['node_tag']==tag)
   if (struct.pack('<3d',*observed['coordinates_mm'])!=struct.pack('<3d',*expected['coordinates_mm']) or [float(v).hex() for v in expected['coordinates_mm']]!=expected['binary64_hex']
       or [int(observed['dimension']),int(observed['entity_tag'])]!=([2,1] if tag in shell['original_source_classifications']['boundary_global_node_tags'] else [3,1])):
    raise ValueError('Every original coordinate word/class must join current native context')
   case['classes'][tag]=[int(observed['dimension']),int(observed['entity_tag'])]
  apex_native=native[row['apex']]
  if case['classes'][row['apex']]!=[3,1] or apex_native['available_parametric_coordinates']!=[] or apex_native['parametric_binary64_hex']!=[]:raise ValueError('Original dim3 apex storage slot and observed available parameters required')
  case['apex_parameters'][row['apex']]=list(apex_native['available_parametric_coordinates'])
  case['cases'].append(part);case['old'].update(original);case['replacement'].update(part['replacement']);case['proposed'].update(part['proposed']);case['fresh_nodes'].extend(part['fresh_nodes'])
  nmax+=row['I']-1;emax+=row['M']-row['K']
  del domain,arrays,worker,ns
 counts=manifest['aggregate_counts_from_frozen_metadata']
 if (len(case['old'])!=counts['removed_TET4'] or len(case['replacement'])!=counts['replacement_TET4'] or len(case['fresh_nodes'])!=counts['fresh_nodes'] or emax-EMAX!=counts['fresh_elements']
     or set(case['fresh_nodes'])&vertices or set(case['replacement'])-set(case['old'])!=set(range(EMAX+1,emax+1))):raise ValueError('Whole-manifest allocation/count/collision mismatch')
 validate_interfaces(case,context)
 case['expected_counts']={'nodes':1097222+len(case['fresh_nodes']),'TET4':3621771+len(case['replacement'])-len(case['old']),'interior':225491+len(case['fresh_nodes'])}
 case['expected_maxima']={'node':nmax,'element_all_dimensions':emax}
 case['declared_counts']=dict(COUNTS,addNodes=int(bool(case['fresh_nodes'])))
 if case['declared_counts']!=COUNTS:raise ValueError('Frozen declaration must match conditional calls for the exact15 manifest')
 return case

def validate_interfaces(case,context):
 faces={tuple(r['shell_face_key']):r for r in context['all_selected_shell_face_records']};u=set(case['old']);seen=set()
 for part in case['cases']:
  selected=next(r for r in context['selected_case_contexts'] if r['apex']==part['apex'])
  if selected['old_cell_tags']!=sorted(part['old']):raise ValueError('Complete current same-case incidence required')
  for key in map(tuple,selected['shell_face_keys']):
   if key in seen:raise ValueError('Admitted cases share an interface face')
   seen.add(key);hit=faces[key];inside=[r for r in hit['owners'] if r['tetrahedron_tag'] in u];outside=[r for r in hit['owners'] if r['tetrahedron_tag'] not in u]
   if (len(inside)!=1 or inside[0]['tetrahedron_tag'] not in part['old'] or inside[0]['node_tags']!=part['old'][inside[0]['tetrahedron_tag']]
       or inside[0]['dimension']!=3 or inside[0]['entity_tag']!=1):raise ValueError('One admitted native ordered old owner required, classified against subset U')
   face=inside[0]['oriented_face'];cycle=lambda f:min(tuple(f[i:]+f[:i]) for i in range(3))
   if hit['parent_exterior_TRI_rows']:
    if outside or len(hit['owners'])!=1 or len(hit['parent_exterior_TRI_rows'])!=1 or cycle(hit['parent_exterior_TRI_rows'][0]['node_tags'])!=cycle(face):raise ValueError('Exact unchanged exterior TRI owner/orientation required')
   elif len(outside)!=1 or len(hit['owners'])!=2 or cycle(outside[0]['oriented_face'])!=cycle(list(reversed(face))):raise ValueError('One opposite unchanged outside TET owner required')

def edit_once(gmsh,case,counts):
 if len(case['cases'])!=CASE_COUNT or not case['old'] or case['apices']!=sorted(set(case['apices'])):raise ValueError('Exact nonempty fixed15 union required')
 if gmsh.model.mesh.getMaxNodeTag()!=case['nmax'] or gmsh.model.mesh.getMaxElementTag()!=case['emax']:raise ValueError('Fresh full-parent maxima changed before edit')
 for tag,row in case['old'].items():
  kind,nodes,dim,entity=gmsh.model.mesh.getElement(tag)
  if kind!=4 or list(nodes)!=row or (dim,entity)!=(3,1):raise ValueError('Every complete old union row/entity must remain exact')
 for tag in case['apices']:
  xyz,param,dim,entity=gmsh.model.mesh.getNode(tag)
  if (dim,entity)!=(3,1) or [struct.pack('<d',v) for v in param]!=[struct.pack('<d',v) for v in case['apex_parameters'][tag]]:raise ValueError('Original apex storage class/parameters changed')
 counts['removeElements']+=1;gmsh.model.mesh.removeElements(3,1,sorted(case['old']))
 for tag in case['apices']:
  counts['setNode']+=1;gmsh.model.mesh.setNode(tag,case['proposed'][tag],case['apex_parameters'][tag])
 tags=case['fresh_nodes']
 if tags:
  counts['addNodes']+=1;gmsh.model.mesh.addNodes(3,1,tags,[x for t in tags for x in case['proposed'][t]])
 counts['addElementsByType']+=1;gmsh.model.mesh.addElementsByType(1,4,list(case['replacement']),[t for r in case['replacement'].values() for t in r])
 counts['rebuildNodeCache']+=1;gmsh.model.mesh.rebuildNodeCache(False)
 counts['rebuildElementCache']+=1;gmsh.model.mesh.rebuildElementCache(False)

def source_reference(core,gmsh,context):
 np=core.np;nt,xyz,_=gmsh.model.mesh.getNodes();ix=np.argsort(nt);nt=np.asarray(nt,dtype='<u8')[ix];xyz=np.asarray(xyz,dtype='<f8').reshape(-1,3)[ix]
 expected=np.arange(1,BOUNDARY+1,dtype='<u8');where=np.searchsorted(nt,expected)
 if np.any(where>=len(nt)) or not np.array_equal(nt[where],expected):raise ValueError('Every original surface tag required')
 points=np.ascontiguousarray(xyz[where]);types,tags,conn=gmsh.model.mesh.getElements(2)
 if list(types)!=[2] or len(tags)!=1:raise ValueError('Exact complete original TRI3 surface required')
 order=np.argsort(tags[0]);tt=np.asarray(tags[0],dtype='<u8')[order];rows=np.asarray(conn[0],dtype='<u8').reshape(-1,3)[order]
 lower=context['full_lower_dimensional_inventory']
 if (len(lower)!=1 or len(rows)!=1743878 or core.array_sha(tt)!=lower[0]['element_tags_u64_sha256']
     or core.array_sha(rows)!=lower[0]['ordered_connectivity_u64_sha256'] or np.any(rows<1) or np.any(rows>BOUNDARY)):
  raise ValueError('Full ordered parent surface typed hashes changed')
 return points,rows.astype(np.int64)-1

def outside_reference(core,state,case):
 np=core.np;xyz,nt,et,en=state;a=np.asarray(case['apices'],dtype='<u8');u=np.asarray(sorted(case['old']),dtype='<u8')
 if not np.isin(a,nt).all() or not np.isin(u,et).all():raise ValueError('Every exact subset A/U tag must occur in full verified parent arrays')
 nodes=~np.isin(nt,a);cells=~np.isin(et,u)
 return {'outside_node_tags_u64_sha256':core.array_sha(nt[nodes]),'outside_coordinate_words_f64_sha256':core.array_sha(xyz[nodes]),
  'outside_tetra_tags_u64_sha256':core.array_sha(et[cells]),'outside_ordered_tetra_connectivity_u64_sha256':core.array_sha(en[cells]),
  'outside_nodes':int(np.count_nonzero(nodes)),'outside_TET4':int(np.count_nonzero(cells))}

def parameter_projection(inventory):
 return [{k:row[k] for k in ['dimension','entity_tag','count','parameter_width','node_tags_u64_sha256','available_parameter_words_f64_sha256']} for row in inventory]

def retained_positions(tags,retained):
 if (tags!=sorted(set(tags)) or retained!=sorted(set(retained)) or any(type(t) is not int or t<=0 for t in tags+retained)):
  raise ValueError('Sorted unique positive actual and retained original tags required')
 indices={tag:i for i,tag in enumerate(tags)}
 if not set(retained)<=set(tags):raise ValueError('A retained original tag disappeared')
 return [indices[tag] for tag in retained]

def parameter_record(core,dim,entity,owned,owned_xyz,params,width):
 return {'dimension':dim,'entity_tag':entity,'count':len(owned),'parameter_width':width,
  'node_tags_u64_sha256':core.array_sha(owned),'coordinate_words_f64_sha256':core.array_sha(owned_xyz),
  'available_parameter_words_f64_sha256':core.array_sha(params)}

def metadata_snapshot(core,gmsh,state,case,context,after):
 np=core.np;xyz,nt,et,en=state;entities=sorted((int(d),int(t)) for d,t in gmsh.model.getEntities())
 parameter_inventory=[];entity_rows=[];lower=[];periodic=[];all_lower=[];groups=[];dimensions=np.full(len(nt),-1,dtype=np.int8);entity_tags=np.zeros(len(nt),dtype=np.int64)
 for dim,entity in entities:
  boundary=[list(map(int,row)) for row in gmsh.model.getBoundary([(dim,entity)],combined=False,oriented=True,recursive=False)] if dim else []
  entity_rows.append({'dimension':dim,'entity_tag':entity,'oriented_immediate_boundary':boundary,'name':gmsh.model.getEntityName(dim,entity)})
  owned,owned_xyz,owned_param=gmsh.model.mesh.getNodes(dim,entity,False,True)
  owned=np.asarray(owned,dtype='<u8');ix=np.argsort(owned);owned=owned[ix];where=np.searchsorted(nt,owned)
  owned_xyz=np.asarray(owned_xyz,dtype='<f8').reshape(-1,3)[ix];parameter_width=dim if len(owned_param) else 0
  if (len(np.unique(owned))!=len(owned) or np.any(where>=len(nt)) or not np.array_equal(nt[where],owned) or np.any(dimensions[where]!=-1)
      or owned_xyz.tobytes()!=np.asarray(xyz[where],dtype='<f8').tobytes() or len(owned_param) not in (0,len(owned)*dim)):
   raise ValueError('Complete entity ownership/coordinate/available-parameter association required')
  dimensions[where]=dim;entity_tags[where]=entity
  params=np.asarray(owned_param,dtype='<f8').reshape(len(owned),parameter_width)[ix] if parameter_width else np.empty((len(owned),0),dtype='<f8')
  if not np.isfinite(params).all():raise ValueError('Finite available parameter words required')
  full=parameter_record(core,dim,entity,owned,owned_xyz,params,parameter_width)
  expected=next(r for r in context['full_entity_node_parameter_inventory'] if (r['dimension'],r['entity_tag'])==(dim,entity))
  if not after:
   if full!=expected:raise ValueError('Full before entity tags/coordinates/available parameters must equal fresh current context')
   case.setdefault('retained_entity_node_tags',{})[(dim,entity)]=owned[~np.isin(owned,np.asarray(case['apices'],dtype='<u8'))].copy()
  retained=case['retained_entity_node_tags'][(dim,entity)]
  keep=retained_positions(owned.tolist(),retained.tolist())
  observed=parameter_record(core,dim,entity,owned[keep],owned_xyz[keep],params[keep],parameter_width)
  if not after:case.setdefault('retained_parameter_inventory',{})[(dim,entity)]=observed
  elif observed!=case['retained_parameter_inventory'][(dim,entity)]:raise ValueError('Every retained original parameter/coordinate word must remain exact')
  parameter_inventory.append(observed)
  if dim in (1,2):
   master,nodes,masters,transform=gmsh.model.mesh.getPeriodicNodes(dim,entity,True)
   periodic.append({'dimension':dim,'entity_tag':entity,'master_entity':int(master),'node_tags':list(map(int,nodes)),
    'master_node_tags':list(map(int,masters)),'affine_transform':list(map(float,transform))})
  if dim>=3:continue
  types,element_tags,element_nodes=gmsh.model.mesh.getElements(dim,entity)
  if not (len(types)==len(element_tags)==len(element_nodes)):raise ValueError('Complete lower-dimensional blocks required')
  for kind,tt,flat in zip(types,element_tags,element_nodes):
   kind=int(kind);properties=gmsh.model.mesh.getElementProperties(kind);width=int(properties[3])
   if int(properties[1])!=dim or width<=0 or len(flat)!=len(tt)*width:raise ValueError('Lower-dimensional type/row width changed')
   ix=np.argsort(tt);tt=np.asarray(tt,dtype='<u8')[ix];rows=np.asarray(flat,dtype='<u8').reshape(-1,width)[ix]
   if len(tt)!=len(np.unique(tt)) or (len(tt) and int(tt.min())<=0):raise ValueError('Unique positive lower-dimensional tags required')
   all_lower.append(tt)
   lower.append({'dimension':dim,'entity_tag':entity,'element_type':kind,'nodes_per_element':width,'count':len(tt),
    'minimum_tag':int(tt.min()) if len(tt) else None,'maximum_tag':int(tt.max()) if len(tt) else None,
    'element_tags_u64_sha256':core.array_sha(tt),'ordered_connectivity_u64_sha256':core.array_sha(rows)})
 for dim,tag in sorted(gmsh.model.getPhysicalGroups()):
  groups.append({'dimension':int(dim),'physical_tag':int(tag),'name':gmsh.model.getPhysicalName(dim,tag),'entity_tags':sorted(map(int,gmsh.model.getEntitiesForPhysicalGroup(dim,tag)))})
 lower.sort(key=lambda row:(row['dimension'],row['entity_tag'],row['element_type']))
 if np.any(dimensions<0):raise ValueError('Missing current node classifications')
 original=~np.isin(nt,np.asarray(case['fresh_nodes'],dtype='<u8'))
 if (core.array_sha(nt[original])!=context['full_array_sha256s']['sorted_node_tags_sha256']
     or core.array_sha(dimensions[original])!=context['full_native_classifications']['node_classification_dimensions_sha256']
     or core.array_sha(entity_tags[original])!=context['full_native_classifications']['node_classification_entity_tags_sha256']):
  raise ValueError('Every original node tag and classification must remain exact')
 fresh=np.flatnonzero(~original)
 if (len(fresh)!=(len(case['fresh_nodes']) if after else 0) or (after and (nt[fresh].tolist()!=case['fresh_nodes'] or np.any(dimensions[fresh]!=3) or np.any(entity_tags[fresh]!=1)))):
  raise ValueError('Only exact allocated fresh nodes on existing volume1 permitted')
 node_mask=~np.isin(nt,np.asarray([*case['apices'],*case['fresh_nodes']],dtype='<u8'))
 removed=list(case['replacement'] if after else case['old']);cell_mask=~np.isin(et,np.asarray(removed,dtype='<u8'))
 preservation={'outside_node_tags_u64_sha256':core.array_sha(nt[node_mask]),'outside_coordinate_words_f64_sha256':core.array_sha(xyz[node_mask]),
  'outside_tetra_tags_u64_sha256':core.array_sha(et[cell_mask]),'outside_ordered_tetra_connectivity_u64_sha256':core.array_sha(en[cell_mask]),
  'outside_nodes':int(np.count_nonzero(node_mask)),'outside_TET4':int(np.count_nonzero(cell_mask))}
 for key,value in preservation.items():
  if case['outside_reference'][key]!=value:raise ValueError('Outside preservation changed: '+key)
 metadata={'full_lower_dimensional_inventory':lower,'full_entity_metadata':entity_rows,'full_physical_group_metadata':groups,'full_periodic_metadata':periodic}
 for key,value in metadata.items():
  if value!=context[key]:raise ValueError('Complete original lower/entity/physical/periodic metadata changed: '+key)
 all_et=np.concatenate([et,*all_lower])
 if len(np.unique(all_et))!=len(all_et):raise ValueError('All-dimensional element tag collision refused')
 maxima={'node':int(nt.max()),'element_all_dimensions':int(all_et.max())}
 if maxima!=(case['expected_maxima'] if after else {'node':NMAX,'element_all_dimensions':EMAX}):raise ValueError('Complete actual maxima changed')
 if (int(gmsh.model.mesh.getMaxNodeTag()),int(gmsh.model.mesh.getMaxElementTag()))!=(maxima['node'],maxima['element_all_dimensions']):raise ValueError('Native tag caches differ from complete current arrays')
 for tag,expected in case['classes'].items():
  coordinates,param,dim,entity=gmsh.model.mesh.getNode(tag)
  if [int(dim),int(entity)]!=expected or [float(v).hex() for v in param]!=next(r['parametric_binary64_hex'] for r in context['selected_original_native_node_rows'] if r['node_tag']==tag):raise ValueError('Selected original classification/parametric association changed')
  index=int(np.searchsorted(nt,tag));want=case['proposed'][tag] if after else next(r['coordinates_mm'] for r in context['selected_original_native_node_rows'] if r['node_tag']==tag)
  if int(nt[index])!=tag or struct.pack('<3d',*coordinates)!=struct.pack('<3d',*want) or struct.pack('<3d',*xyz[index])!=struct.pack('<3d',*want):raise ValueError('Selected original coordinate words changed')
 if after:
  for tag,row in case['replacement'].items():
   index=int(np.searchsorted(et,tag))
   if index>=len(et) or int(et[index])!=tag or en[index].tolist()!=row:raise ValueError('Every new ordered replacement row required')
  for tag in case['fresh_nodes']:
   index=int(np.searchsorted(nt,tag))
   if struct.pack('<3d',*xyz[index])!=struct.pack('<3d',*case['proposed'][tag]):raise ValueError('Fresh proposed coordinate words changed')
 return dict(preservation=preservation,metadata_sha256s={key:json_sha(value) for key,value in metadata.items()},
  original_classification_projection_exact=True,new_nodes_on_volume1=len(case['fresh_nodes']) if after else 0,expected_new_nodes=len(case['fresh_nodes']),retained_original_parameter_projection=parameter_projection(parameter_inventory),maxima=maxima)

def require_snapshot(before,after):
 if (before['preservation']!=after['preservation'] or before['metadata_sha256s']!=after['metadata_sha256s']
     or before['retained_original_parameter_projection']!=after['retained_original_parameter_projection']):raise ValueError('Any subset outside or original metadata/parameter drift refused')
 if after['original_classification_projection_exact'] is not True or after['new_nodes_on_volume1']!=before['expected_new_nodes']:raise ValueError('Every original classification and allocated new node required')

def current_after_proof(worker,receipt,closed,first,prior,peer,peer_bindings,acceptance,helpers):
 """Current partial.after==saved and descriptor-shaped accepted126 census; d60 stays false."""
 proof=helpers['partial_after_proof'](worker,receipt,closed,prior)
 report_record=peer_bindings.get('outputs',{}).get('readback-report.json',{})
 contract_record=peer_bindings.get('outputs',{}).get('frozen-contract.json',{})
 actual_record=peer_bindings.get('selected_control_records',{}).get('actual',{})
 if (prior['MSH_sha256']!=MSH_SHA or prior['MSH_bytes']!=235786462
     or prior['partial_report_sha256']!=FIXED_INPUTS[WORKER] or prior['expected_positive_poor_total']!=126
     or first.get('status')!='direct_saved_file_readback_completed' or first.get('bound_inputs_unchanged') is not True
     or first.get('single_partial_replacement_saved_proof')!={'report_sha256':FIXED_INPUTS[WORKER],'field':'after','after_equals_saved_reopen':True,'independent_prior_reader_alias_used':False,'old210_bins_reused':False}
     or any(first.get(k)!=v for k,v in proof['array_sha256s'].items())
     or first['direct_fresh_classifications']!=proof['classifications']
     or peer.get('schema')!='962-current126-census-independent-stopped-saved-review/v1'
     or peer.get('decision')!='CLEAR_COMPLETED_READ_ONLY_CENSUS_SAVED_ASSOCIATIONS_ONLY'
     or peer.get('blockers')!=[] or peer.get('checked',{}).get('d60_false_conformance_preserved') is not True
     or any(peer.get(k) is not False for k in ['engineering_accepted','head_edit_authorized','head_PDE_authorized','physics_qualified','material_qualified','process_calibrated','manufacturing_authorized','automatic_retry'])
     or peer.get('bindings',{}).get('path')!=CENSUS_BINDINGS or peer['bindings'].get('sha256')!=FIXED_INPUTS[CENSUS_BINDINGS]
     or peer_bindings.get('schema')!='962-current126-census-saved-result-bindings/v1'
     or report_record.get('path')!=FIRST or report_record.get('sha256')!=FIXED_INPUTS[FIRST]
     or contract_record.get('path')!=FIRST_CONTRACT or contract_record.get('sha256')!=FIXED_INPUTS[FIRST_CONTRACT]
     or actual_record.get('path')!=FIRST_ACTUAL or actual_record.get('sha256')!=FIXED_INPUTS[FIRST_ACTUAL]
     or peer_bindings.get('source_proof',{}).get('path')!=WORKER or peer_bindings['source_proof'].get('sha256')!=FIXED_INPUTS[WORKER]
     or acceptance.get('schema')!='962-current126-census-root-result-acceptance/v1'
     or acceptance.get('decision')!='ACCEPT_COMPLETE_CURRENT126_READ_ONLY_CENSUS_ASSOCIATIONS_ONLY'
     or acceptance.get('peer_review',{}).get('path')!=CENSUS_PEER or acceptance['peer_review'].get('sha256')!=FIXED_INPUTS[CENSUS_PEER]
     or acceptance.get('peer_bindings')!=peer['bindings'] or acceptance.get('current_report')!=report_record or acceptance.get('current_contract')!=contract_record
     or acceptance.get('prior_d60_command_conformant') is not False
     or acceptance.get('counts',{}).get('positive_poor')!=126 or acceptance['counts'].get('seeds')!=100 or acceptance['counts'].get('incident_cells')!=3123
     or any(acceptance.get(k) is not False for k in ['whole_head_quality_accepted','native_query_or_mesh_edit_authorized_by_this_record','head_PDE_authorized','physics_qualified','material_qualified','process_calibrated','manufacturing_authorized','automatic_retry'])):
  raise ValueError('Current partial-after/saved126 census descriptor proof with historical d60 false required')
 helpers['require_after_match'](first,proof,126)
 return proof

def require_original_records(core,worker,receipt,first,closed,metadata,context):
 helpers={'partial_after_proof':core.partial_after_proof,'require_after_match':core.require_after_match}
 proof=current_after_proof(worker,receipt,closed,first,metadata,json.loads((ROOT/CENSUS_PEER).read_text()),json.loads((ROOT/CENSUS_BINDINGS).read_text()),json.loads((ROOT/CENSUS_ACCEPT).read_text()),helpers)
 accepted=json.loads((ROOT/PARTIAL_ACCEPT).read_text())
 if (accepted.get('decision')!='ACCEPT_COMPLETED_PROCEDURAL_PARTIAL_HEAD_REPAIR_ONLY_WHOLE_HEAD_REJECTED'
     or accepted['partial_report']['path']!=ORIGINAL_WORKER or accepted['partial_report']['sha256']!=FIXED_INPUTS[ORIGINAL_WORKER]
     or accepted.get('whole_head_quality_accepted') is not False
     or metadata['partial_contract_sha256']!=FIXED_INPUTS['work/962-engineering/apex1613031-head-application-001/frozen-contract.json']
     or proof['array_sha256s']!=context['full_array_sha256s'] or proof['classifications']!=context['full_native_classifications']
     or proof['source_boundary_identity']!=context['current_source_boundary_identity'] or proof['quality']!=context['retained_current_quality_and_global_incidence']['quality']
     or (proof['total_mesh_nodes'],proof['tetrahedra'],proof['tetra_referenced_interior_nodes'],proof['unreferenced_mesh_nodes'])!=(1097222,3621771,225491,0)):
  raise ValueError('Exact current126 partial.after/saved census and new full context required')
 return proof


def valid_positive_volume(audit):
 return all(row['nonpositive_count']==0 for row in audit['quality'].values()) and audit['volume_relative_error']<=1e-6

def main():
 c=json.loads((OUT/'frozen-contract.json').read_text());require_contract(c)
 if {p.name for p in OUT.iterdir()}!={'reader.py','run_readback.py','frozen-contract.json','native.log'}:raise ValueError('Exactly fresh three-file materialization plus native.log required')
 report=dict(schema='962-current126-alternative15-combined-head-application-result/v1',status='running',stage='imports',procedural_checks_passed=False,
  actual_whole_head_SICN_gate_passed=False,expected_whole_head_positive_poor_count_not_observed=110,
  expected_count_is_not_acceptance=True,native_operation_counts={k:0 for k in COUNTS},call_counts_are_attempts=True,
  original_parent_MSH_sha256=FIXED_INPUTS[MESH],admitted_manifest_sha256=FIXED_INPUTS[MANIFEST],current_local_domain_peer_sha256=FIXED_INPUTS[DOMAIN_PEER],current_local_domain_root_acceptance_sha256=FIXED_INPUTS[DOMAIN_ACCEPT],context_sha256=c['context_admission']['report']['sha256'],context_admission_records=c['context_admission'],
  upstream_census_launch_deviation_sha256=FIXED_INPUTS[DEVIATION],declared_controller_command_conformant=False,
  retained_original_parameter_scope='Full native before scan equals fresh context; retain all original actual tags excluding exactly the 15 admitted apices; new nodes never enter this reference.',
  original_local_domain_equivalence_is_separate=True,global_embedding_or_containment_proved=False,
  stronger_Mesh2_criterion_passed=False,engineering_accepted=False,physics_qualified=False,material_qualified=False,process_calibrated=False,manufacturing_authorized=False)
 started=time.monotonic();gmsh=None;initialized=False
 def checkpoint():
  with (OUT/'readback-report.json').open('w') as f:json.dump(report,f,indent=2,allow_nan=False);f.write('\n')
 try:
  import numpy as np
  import gmsh
  observed={'python':platform.python_version(),'numpy':np.__version__,'gmsh':gmsh.__version__,'machine':platform.machine()}
  runtime={'python':sha(Path(sys.executable).resolve()),'gmsh_module':sha(gmsh.__file__),'gmsh_library':sha(gmsh.lib._name)}
  if (observed!=RUNTIME or runtime!=c['runtime_sha256s'] or Path(np.__file__).resolve()!=Path(c['numpy_init']).resolve() or sha(np.__file__)!=c['numpy_init_sha256']):raise ValueError('Exact selected native/NumPy runtime required')
  report.update(runtime=observed,runtime_sha256s=runtime)
  ns={'np':np,'math':math,'hashlib':hashlib}
  selected(HEAD,['array_sha','volume_arrays','canonical_oriented','surface_roundtrip','distribution','tetra_volumes','tetra_boundary'],ns)
  selected(CORE,['tagged_volume','internal_face_orientation'],ns)
  selected(AUDIT,['classifications','array_identity','boundary_identity','audit_after'],ns)
  selected(PROOF_SOURCE,['partial_after_proof','require_after_match'],ns)
  core=SimpleNamespace(np=np,CANDIDATE_VOLUME=915453.1236217883,**{k:v for k,v in ns.items() if callable(v)})
  context=json.loads((ROOT/CONTEXT).read_text());first=json.loads((ROOT/FIRST).read_text());case=make_case(context,first)
  worker=json.loads((ROOT/ORIGINAL_WORKER).read_text())
  proof=require_original_records(core,worker,json.loads((ROOT/ORIGINAL_RECEIPT).read_text()),first,json.loads((ROOT/PARTIAL_CLOSED).read_text()),json.loads((ROOT/PARTIAL_METADATA).read_text()),context)
  report.update(admitted_apices=case['apices'],per_case_mappings=[{k:v for k,v in row.items() if k not in ['proposed','old']} for row in case['cases']],replacement_ordered_rows=case['replacement'],expected_counts=case['expected_counts'],expected_maxima=case['expected_maxima'])
  gmsh.initialize([],readConfigFiles=False,run=False);initialized=True;gmsh.logger.start()
  for key,value in OPTIONS.items():gmsh.option.setNumber(key,value)
  report['stage']='opening_exact_current_partial_head';checkpoint();gmsh.open(str(ROOT/MESH))
  points,faces=source_reference(core,gmsh,context)
  report['stage']='complete_before_audit';checkpoint();state,before=core.audit_after(core,gmsh,points,faces)
  before['source_boundary_identity']=core.boundary_identity(core,state,points,before['classifications'])
  if before!=proof or not valid_positive_volume(before):raise ValueError('Complete fresh original audit must equal sole current partial worker.after')
  case['outside_reference']=outside_reference(core,state,case)
  if (context['outside_mask_scope']['excluded_apex_tags']!=case['apices'] or context['outside_mask_scope']['excluded_original_TET4_tags']!=sorted(case['old'])
      or case['outside_reference']!={k:context['future_preservation_references'][k] for k in case['outside_reference']}):raise ValueError('Fresh exact15 A/U before masks must match admitted context')
  before_snapshot=metadata_snapshot(core,gmsh,state,case,context,False);del state
  report.update(before=before,before_preservation=before_snapshot,stage='one_tag_sparse_replacement');checkpoint()
  if any(gmsh.option.getNumber(k)!=v for k,v in OPTIONS.items()):raise ValueError('Options changed before replacement')
  report['partial_replacement_attempted']=True;edit_once(gmsh,case,report['native_operation_counts']);report['partial_replacement_completed']=True
  report['stage']='complete_after_audit';checkpoint();state,after=core.audit_after(core,gmsh,points,faces)
  after['source_boundary_identity']=core.boundary_identity(core,state,points,after['classifications'])
  after_snapshot=metadata_snapshot(core,gmsh,state,case,context,True);require_snapshot(before_snapshot,after_snapshot)
  if (after['total_mesh_nodes'],after['tetrahedra'],after['tetra_referenced_interior_nodes'])!=tuple(case['expected_counts'][k] for k in ['nodes','TET4','interior']) or not valid_positive_volume(after):raise ValueError('Actual changed counts/positive metrics/relative volume gate failed')
  if after['source_boundary_identity']!=before['source_boundary_identity']:raise ValueError('Original exact boundary bits/classes/periodicity changed')
  local_et=np.asarray(list(case['replacement']),dtype='<u8');local_metrics={name:np.asarray(gmsh.model.mesh.getElementQualities(local_et,api),dtype='<f8') for name,api in [('SICN','minSICN'),('Jacobian','minDetJac'),('native_volume_mm3','volume')]}
  if any(len(v)!=len(case['replacement']) or not np.isfinite(v).all() or np.any(v<=0) for v in local_metrics.values()) or np.any(local_metrics['SICN']<.1):raise ValueError('Every actual replacement cell must freshly pass unchanged local SICN/positivity gate')
  report.update(after=after,after_preservation=after_snapshot,replacement_native_metrics={k:v.tolist() for k,v in local_metrics.items()},actual_replacement_SICN_gate_passed=True)
  del state
  path=OUT/'head-volume.msh';report['stage']='saving_partial_repair';checkpoint();report['native_operation_counts']['write_mesh']+=1;gmsh.write(str(path));digest=sha(path)
  gmsh.clear();gmsh.open(str(path));report['stage']='complete_saved_reopen_audit';checkpoint();state,saved=core.audit_after(core,gmsh,points,faces)
  saved['source_boundary_identity']=core.boundary_identity(core,state,points,saved['classifications'])
  saved_snapshot=metadata_snapshot(core,gmsh,state,case,context,True);require_snapshot(before_snapshot,saved_snapshot)
  if saved!=after or saved_snapshot!=after_snapshot or sha(path)!=digest:raise ValueError('Full after/saved tagged arrays/metrics/classifications/metadata identity changed')
  if any(gmsh.option.getNumber(k)!=v for k,v in OPTIONS.items()) or report['native_operation_counts']!=case['declared_counts']:raise ValueError('Exact options/API operation attempts changed')
  report.update(saved_reopen=saved,saved_preservation=saved_snapshot,saved_mesh_identity_exact=True,mesh_sha256=digest,mesh_bytes=path.stat().st_size,
   procedural_checks_passed=True,actual_whole_head_SICN_gate_passed=after['quality']['minimum_SICN']['minimum']>=.1,
   actual_whole_head_positive_poor_count=after['quality']['minimum_SICN']['below_point1_count'],stage='completed_partial_repair_audits',status='completed_partial_head_replacement_whole_head_quality_gate_applied')
 except Exception as error:report.update(status='refused_or_failed_outputs_preserved',error=type(error).__name__+': '+str(error))
 finally:
  if initialized:
   try:report['gmsh_warnings_errors']=[s for s in gmsh.logger.get() if s.startswith(('Warning','Error'))];gmsh.logger.stop()
   except Exception as error:report.update(status='failed_runtime_cleanup',cleanup_error=type(error).__name__+': '+str(error),procedural_checks_passed=False)
   try:gmsh.finalize()
   except Exception as error:report.update(status='failed_runtime_cleanup',finalize_error=type(error).__name__+': '+str(error),procedural_checks_passed=False)
  try:require_contract(c);report['bound_inputs_unchanged']=True
  except Exception:report['bound_inputs_unchanged']=False
  report['wall_seconds']=time.monotonic()-started;checkpoint()
 return 0 if report['procedural_checks_passed'] and report['actual_whole_head_SICN_gate_passed'] and report['bound_inputs_unchanged'] else 2

if __name__=='__main__':raise SystemExit(main())
