# LPBF AlSi10Mg conductivity source records

The [English material follow-up](../../../MATERIAL_CONDUCTIVITY_FOLLOWUP.md) explains the measured points, separate recipe and proposed interpolation. These records contain no head solver result or material qualification.

`source-data.json` is the exact initial primary-source register. Its institutional-PDF hash remains null. The later exact `visual-check.json` binds the separately downloaded official publisher PDF and confirms the table and treatment by viewing both rendered pages. It does not claim the publisher and institutional files are byte-identical. Neither PDF nor page image is bundled.

`original-records.json` binds the four exact copies. The source study is attributed to Willkomm et al., IOP Conference Series: Materials Science and Engineering 1097 (2021) 012021, DOI [10.1088/1757-899X/1097/1/012021](https://doi.org/10.1088/1757-899X/1097/1/012021), CC BY 3.0. The project licence is separate in `LICENSE.project`.

Run `python3 -B verify.py` to check sealed bytes and file closure only. It imports no scientific runtime, evaluates no material law and runs no geometry or physics.
