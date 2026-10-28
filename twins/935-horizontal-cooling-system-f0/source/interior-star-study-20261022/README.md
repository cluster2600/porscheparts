# Exact interior-star study recipe

This is the executed bounded recipe for the retained private parent volume with
SHA-256 `68f5e6a4b1dcf188b8d536195821ce3c3475074d9ba95286f94022299442241a`.
It is an analysis-mesh experiment, not a change to the PicoGK design master.
Restore the parent from the private `analysis-mesh-935-20261022` evidence release.

Copy the recipe to a fresh direct child of `work/` before execution. It derives
the repository root from that location and refuses existing output directories.
Use the recorded scientific Python environment with NumPy and SciPy installed.

```sh
mkdir work/NEW-star-study
cp twins/935-horizontal-cooling-system-f0/source/interior-star-study-20261022/run_star_kernel.py work/NEW-star-study/
python work/NEW-star-study/run_star_kernel.py
python twins/935-horizontal-cooling-system-f0/source/audit_interior_relocation.py \
  work/935-analysis-patches-20261022/volume-151 \
  work/NEW-star-study/kernel-001/rotor \
  work/NEW-star-study/audited
```

The synthetic interior-star control must preserve exact volume 1/6, retain every
boundary coordinate, keep every cell positive and improve the minimum mean ratio.
The worker is bounded to 16 GiB RSS and 600 seconds. A successful worker output
remains unaudited until the independent whole-volume check passes. Mechanical
mesh quality, convergence, physical scale, supports and manufacture remain
separate requirements.
