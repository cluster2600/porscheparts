# Reproducing the material references

`fetch_luo_sources.py` downloads only the three small public files named in `sources.json` (about 4.25 MB in total), checks size/SHA256, then extracts only the four expected workbooks. `extract_luo_rt.py INPUT NEW_OUTPUT` checks the sources again and reproduces the four sensitivity laws of the first published process set. The minimum versions installed for this check are pinned in `requirements.txt`.

The committable results, the data licence, the conversion assumptions and the numerical limits are in [material-luo-set1](../material-luo-set1/README.md). The raw source archives stay in `work/`.
