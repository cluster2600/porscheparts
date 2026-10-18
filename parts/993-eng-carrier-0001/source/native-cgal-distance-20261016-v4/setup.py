"""Install the fixed finite-sample gate; reuse the unchanged pinned V3 binary."""
import argparse,hashlib,json,shutil
from pathlib import Path
SOURCE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('prefix',type=Path);p.add_argument('--distance-runtime',type=Path,required=True);args=p.parse_args()
    prefix=args.prefix.resolve();base=args.distance_runtime.resolve();assert not prefix.exists()
    manifest=base/'installation-receipt.json';runtime=json.loads(manifest.read_text());binary=base/'build/carrier_exact_distance'
    assert runtime['CGAL_commit']=='109ed62eeaa7e38eb383e9444700e6ff7bd4c449' and sha(binary)==runtime['binary_sha256']
    assert sha(SOURCE/'distance.cpp')==runtime['source_files_sha256']['distance.cpp']==sha(base/'distance.cpp')
    assert all(sha(path)==value for path,value in runtime['runtime_files_sha256'].items())
    prefix.mkdir(parents=True);(prefix/'jobs').mkdir();(prefix/'build').mkdir()
    for name in ['distance.cpp','CMakeLists.txt','worker.py','run.py','setup.py']:shutil.copyfile(SOURCE/name,prefix/name)
    shutil.copy2(binary,prefix/'build/carrier_exact_distance');assert sha(prefix/'build/carrier_exact_distance')==runtime['binary_sha256']
    runtime.update(base_distance_receipt=str(manifest),base_distance_receipt_sha256=sha(manifest),
       source_files_sha256={name:sha(prefix/name) for name in ['distance.cpp','CMakeLists.txt','worker.py','run.py','setup.py']},
       scope='Unchanged V3 exact-distance binary. V4 separates20 iteration convergence budget from the original5delta finite-sample admission limit; reference receipt required, no continuous5delta claim.')
    (prefix/'installation-receipt.json').write_text(json.dumps(runtime,indent=2)+'\n');print(json.dumps({'prefix':str(prefix),'binary_sha256':runtime['binary_sha256'],'binary_recompiled':False}))
if __name__=='__main__':main()
