# Fatigue post-processor: tool and witness

The repository rules require fatigue assumptions for loaded and titanium parts
(AGENTS.md), but no stack document named a tool to compute them.

**Assigned tool:** [pyLife](https://github.com/boschresearch/pylife) 2.3.1
(Bosch Research, Apache-2.0). It provides rainflow counting, Wöhler (S-N)
curves and Palmgren-Miner damage, driven from Python.

## Witness

[`witness_rainflow_miner.py`](witness_rainflow_miner.py) checks pyLife against
references it does not produce:

1. **Rainflow counting** of the worked example in ASTM E1049-85 (reapproved
   2017): the history −2, 1, −3, 5, −1, 3, −4, 4, −2 gives ranges 3, 4, 6, 8
   and 9 with 0.5, 1.5, 0.5, 1.0 and 0.5 cycles. The script also carries an
   independent implementation of the standard's three-point procedure, and it
   stops unless that implementation reproduces the table.
2. **Miner damage** of the counted collective on a Basquin line
   N = ND (S/SD)^−k (k = 5, ND = 10⁶, SD = 100 MPa amplitude), against the
   closed form. Both the "original" rule (no damage below SD) and the
   "elementary" rule (the line continued below SD) are checked.

Result ([`results-20261110.json`](results-20261110.json)): the pyLife counts
equal the ASTM table, and both damage sums equal the closed form (relative
error 0). **Passed.**

## Run it

```bash
uv venv --python 3.12 work/fatigue-venv
uv pip install --python work/fatigue-venv/bin/python \
  --require-hashes -r benchmarks/fatigue-postprocessor/requirements.lock.txt
work/fatigue-venv/bin/python -I \
  benchmarks/fatigue-postprocessor/witness_rainflow_miner.py --output <new.json>
```

## What this does not establish

The S-N parameters are arbitrary round numbers. The witness qualifies the
counting and damage arithmetic only. It supplies no material, alloy, AM
process, build orientation, mean-stress, surface or notch data. A fatigue
assessment still needs those from a cited source, stress histories from a
converged FE result (not a singular peak: see AGENT_TOOL_GUIDE.md), and the
review that SAFETY.md requires for loaded parts.
