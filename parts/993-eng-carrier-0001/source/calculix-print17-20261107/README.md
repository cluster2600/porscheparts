# CalculiX 2.21: 17-digit output patch

This formatting-only patch changes four Fortran `WRITE` sites from `E13.6`
to `E25.16E3`, retaining the existing `1P` scale. It preserves 17 significant
decimal digits for the selected binary64 outputs instead of seven. It changes
no solver, element, assembly, material, load or arithmetic expression.

The exact scope is global displacement `U`, global reaction `RF`, stress `S`
when `iorien == 0`, and integration-point `ENER`. Other output branches,
including transformed/local-coordinate branches, are unchanged. Wider text
fields require whitespace-aware readers or corresponding fixed-column updates.

## Apply to the pinned source

Use a fresh CalculiX 2.21 source tree. The retained upstream archive is
`calculix-ccx_2.21.orig.tar.bz2`, SHA-256
`51d229aee320cf685216d360f7c04f9a57af0148fbe840483a964c86c315da82`.
Its two source members were independently compared byte for byte with the
pristine sources used for the qualified Mac candidate.

From `CalculiX/ccx_2.21` (the directory containing `src/`), check the inputs,
apply the patch, and check the exact outputs. Replace the example patch path.
The checks use GNU `sha256sum`; on macOS substitute `shasum -a 256`.

```sh
(
set -e
sha256sum -c <<'SHA256'
c0bbe37ece5ae10faf2ba93113767361fb3dd4f1225e5c2f082cdfad85889141  src/printoutnode.f
09e10433befe43b334ecac6a7ead6ac753eea64da6caa0669848f179d1fd05ea  src/printoutint.f
SHA256
patch --batch --forward --fuzz=0 -p1 < /path/to/calculix-2.21-print17.patch
sha256sum -c <<'SHA256'
1aff91853fa80418a70e8004241ea499546accdc61f24f477599ec36617f3192  src/printoutnode.f
a630526a98877a19efd517ce9f43d22f9de65ba437840c650865b02942f2cc22  src/printoutint.f
SHA256
)
```

Stop if any command fails. Build using the separately qualified platform and
solver recipe; this patch is not a complete build recipe. The new standard
`patch` application reproduced both qualified candidate files byte for byte,
without offsets or fuzz. `apply-verification.json` records that check;
`manifest.json` pins the patch, sources and existing evidence.

## Existing execution evidence

These checks were already executed on the local Mac candidate; preparing this
portable patch did not rebuild the solver or repeat a carrier solve.

| Check | Observed result |
|---|---|
| Formatter roundtrips | 16,378 finite binary64 values returned identical bits, covering all 2,047 finite exponent fields, signed zero, subnormal boundaries and finite extremes |
| Archive comparison | 1,145 other object members unchanged; only the two print objects and archive index changed; symbol-to-member mapping preserved |
| Native analytic controls | Quadratic, traction P1 and traction P2 passed |
| Four-field witness | U: 8 rows; RF: 8; S: 6; ENER: 6; every component printed with 17 significant digits |
| Independent ENER integral | Relative error 3.9789e-15 against the analytic value 1/214000 N mm; inherited limit 1e-4 |

Linux/PARDISO qualification and a full H9 replay with this output precision
remain pending at preparation time. The Mac result does not qualify those
paths or establish the unprinted native residual. It does not change the
existing H8-to-H9 convergence result.

The original source headers identify CalculiX, Copyright (C) 1998-2023 Guido
Dhondt, under GNU GPL version 2. This derivative patch is supplied under that
same license; retain the upstream license and notices with source distribution.
