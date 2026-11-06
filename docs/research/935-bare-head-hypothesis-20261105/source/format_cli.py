#!/usr/bin/env python3
"""Serialize native sections on the qualified 1e-12 mm decimal grid; no path edits."""
import argparse
import json
from pathlib import Path
import numpy as np
from prepare_aligned import sha


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("input",type=Path);p.add_argument("output",type=Path);p.add_argument("report",type=Path)
    a=p.parse_args()
    if a.output.exists() or a.report.exists():raise ValueError("Existing output refused")
    maximum=0.;count=0;contours=0;layers=0
    with a.input.open() as source,a.output.open("x") as target:
        for raw in source:
            line=raw.strip()
            if line.startswith("$$LAYER/"):
                value=float(line.split("/")[1]);text=f"{value:.12f}"
                assert abs(float(text)-value)<5.3e-13
                target.write("$$LAYER/"+text+"\n");layers+=1
            elif line.startswith("$$POLYLINE/"):
                fields=line.split("/")[1].split(",");n=int(fields[2])
                assert len(fields)==3+2*n
                values=np.asarray(fields[3:],float);text=[f"{x:.12f}" for x in values]
                assert all("." in x and "e" not in x and sum(c.isdigit() for c in x)<=16 for x in text)
                error=float(np.abs(np.asarray(text,float)-values).max());maximum=max(maximum,error)
                assert error<5.3e-13
                target.write("$$POLYLINE/"+",".join(fields[:3]+text)+"\n");contours+=1;count+=n
            else:target.write(raw)
    report={"source_sha256":sha(Path(__file__)),"input_sha256":sha(a.input),"output_sha256":sha(a.output),
            "layers":layers,"contours":contours,"coordinate_pairs":count,
            "maximum_scalar_coordinate_rounding_mm":maximum,"decimal_grid_mm":1e-12,
            "contour_vertex_order_and_counts_preserved":True,"independent_contour_validation_required":True,
            "machine_profile_present":False,"manufacturing_qualified":False}
    a.report.write_text(json.dumps(report,indent=2)+"\n");print(json.dumps(report))


if __name__=="__main__":main()
