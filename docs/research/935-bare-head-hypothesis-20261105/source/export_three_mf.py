#!/usr/bin/env python3
"""Prefer exact-coordinate 3MF when binary STL rounding loses tiny facets."""
import argparse
import json
from pathlib import Path
from prepare_aligned import admit,module,sha


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ("mesh","raw-report","contacts","contact-source","validator-source","output"):
        p.add_argument("--"+key,type=Path,required=True)
    a=p.parse_args();a.output.mkdir(exist_ok=False)
    v,f,report=admit(a.mesh,a.raw_report,a.contacts,a.contact_source,a.validator_source)
    validator=module(a.validator_source,"qualified_three_mf_writer")
    target=a.output/"935-reconstructed-head-hypotheses-mm.3mf"
    validator.write_3mf(target,v,f)
    report.update({"export_source_sha256":sha(Path(__file__)),"three_mf_sha256":sha(target),
                   "every_coordinate_index_and_unit_roundtrips_exact":True,
                   "binary_stl_is_not_the_preferred_delivery":True,"manufacturing_qualified":False})
    (a.output/"digital-geometry-and-export.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({"three_mf_sha256":sha(target),"vertices":len(v),"triangles":len(f),
                      "exact_roundtrip":True,"manufacturing_qualified":False}))


if __name__=="__main__":main()
