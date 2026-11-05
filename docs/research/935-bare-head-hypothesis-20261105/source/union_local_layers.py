#!/usr/bin/env python3
"""Reuse qualified per-layer union/check functions with the new declared layer count."""
import argparse
from concurrent.futures import ProcessPoolExecutor
import hashlib
import itertools
import json
import multiprocessing
from pathlib import Path
import time

import numpy as np
import pyclipper
import shapely
from union_component_layers_parallel import initialise,evaluate,layers
from union_component_layers import unite,SCALE
from validate_cli_readback import section


def sha(path):
    with path.open("rb") as stream:return hashlib.file_digest(stream,"sha256").hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("head_cli",type=Path);p.add_argument("hypotheses",type=Path);p.add_argument("output",type=Path)
    p.add_argument("--workers",type=int,default=4)
    a=p.parse_args();a.output.mkdir(exist_ok=False)
    start=time.monotonic();h=json.loads(a.hypotheses.read_text());declared=None
    with a.head_cli.open() as stream:
        for line in stream:
            if line.startswith("$$LAYERS/"):declared=int(line.split("/")[1])
            if line.startswith("$$GEOMETRYSTART"):break
    assert declared and 1<=a.workers<=8
    outer=np.array([[0,0],[2,0],[2,2],[0,2],[0,0]],float)
    hole=np.array([[.5,.5],[.5,1.5],[1.5,1.5],[1.5,.5],[.5,.5]])
    for rings,expected in [([(1,outer),(1,outer+1)],7),([(1,outer),(0,hole)],3),([(1,outer),(0,hole),(1,outer*.25+.75)],3.25)]:
        assert abs(section(unite(rings))[0]-expected)<1e-10
    target=a.output/"935-reconstruction-supported-50um.cli"
    rows=[];vertices=0;iterator=layers(a.head_cli)
    with target.open("x") as stream,ProcessPoolExecutor(max_workers=a.workers,mp_context=multiprocessing.get_context("spawn"),initializer=initialise,initargs=(h,)) as pool:
        stream.write('$$HEADERSTART\n$$ASCII\n$$UNITS/1.0\n$$VERSION/200\n$$LABEL/1,"935 local reconstruction hypotheses - neutral contours only"\n'+f'$$LAYERS/{declared}\n$$HEADEREND\n$$GEOMETRYSTART\n')
        while batch:=list(itertools.islice(iterator,32)):
            for text,row,n in pool.map(evaluate,batch,chunksize=1):
                stream.write(text);rows.append(row);vertices+=n
            stream.flush();print("Verified layer",len(rows),"of",declared,flush=True)
        assert len(rows)==declared and rows[0]["z_mm"]==0 and rows[0]["contours"]==0
        stream.write("$$GEOMETRYEND\n")
    report={"source_sha256":sha(Path(__file__)),"head_cli_sha256":sha(a.head_cli),"hypotheses_sha256":sha(a.hypotheses),
            "output_cli_sha256":sha(target),"pyclipper":pyclipper.__version__,"shapely":shapely.__version__,"geos":shapely.geos_version_string,
            "coordinate_grid_mm":1/SCALE,"layers_including_empty_zero_layer":len(rows),
            "contours":sum(r["contours"] for r in rows),"coordinate_pairs":vertices,"workers":a.workers,
            "all_layers_independently_checked":True,"all_layer_unions_match_independent_geometry":True,
            "output_layer_volume_mm3":sum(r["output_area_mm2"]*r["height_mm"] for r in rows),
            "independent_layer_volume_mm3":sum(r["independent_area_mm2"]*r["height_mm"] for r in rows),
            "maximum_layer_symmetric_difference_mm2":max(r["symmetric_difference_mm2"] for r in rows),
            "seconds":time.monotonic()-start,"machine_job":False,"hatch_or_exposure_present":False,
            "manufacturing_qualified":False,"engine_qualified":False}
    (a.output/"report.json").write_text(json.dumps(report,indent=2)+"\n")
    (a.output/"private-layers.json").write_text(json.dumps(rows)+"\n")
    print(json.dumps(report),flush=True)


if __name__=="__main__":main()
