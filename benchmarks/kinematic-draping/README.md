# Kinematic draping: tool and witness

A woven carbon ply does not lie on an arbitrary double curvature. The monocoque
computation chain listed drapability as a need with no tool in the repository
([MONOCOQUE_964_993_COMPUTATION_CHAIN.md](../../docs/MONOCOQUE_964_993_COMPUTATION_CHAIN.md)).
This is the first screen for it.

**Tool:** [`scripts/kinematic_draping.py`](../../scripts/kinematic_draping.py),
written here on 2026-11-15 (NumPy only). It is the fishnet, or pin-jointed net,
method: warp and weft keep their length, the ply conforms only by shearing,
and the result is the shear angle of every cell of the net.

![Left, a square net lying over a dome and the flat ground around it, coloured by shear: dark along the two yarns through the top, bright in four lobes at the foot of the dome. Right, the same shear on the flat pattern: a dark cross and four bright lobes, up to 50 degrees](media/dome-on-a-plane.png)

*A 1.2 m square ply centred on a dome of radius 0.3 m with a 50 mm foot
fillet: no shear along the two yarns through the top, up to 50° on the
bias at the foot. A demonstration mould, not a part of this repository.*

## Why not the learned simulator

The owner asked for a learned particle simulator (WorldParticle) to drape
carbon plies. Its released cloth model replays the one scene it was trained on:
given a flat plane or a tunnel instead of its sphere, the sheet still drapes
over the absent sphere (the evidence belongs to that tool's own evaluation,
not to this folder). The kinematic method is the standard first screen for
woven plies, needs no training, and has exact answers to be checked against.

## Witness

`kinematic_draping.py witness` checks the construction against answers it does
not produce ([`results-20261115.json`](results-20261115.json)):

| Case | Answer known beforehand | Result |
|---|---|---|
| Plane, warp at 0.3 rad | every crossing on the square grid, no shear | to rounding |
| Half-cylinder, generators along the axis | developable: no shear | to rounding |
| Half-cylinder, generators at 30° to the axis | developable: no shear | 0.0043° at most, the size of the step |
| Sphere of radius 100, yarn spacing 4 | shear of the continuous net | within 0.0063° |
| Sphere of radius 100, yarn spacing 2 | the same | within 0.0016°: the error falls 3.9 times when the spacing halves |
| Every case | each yarn segment keeps its length; each crossing lies on the mould | to rounding |

**The reference for the sphere** is not another draping code. The angle ω
between the yarns of a continuous net obeys ω_uv = −K sin ω, with K the
Gaussian curvature. With two geodesic generators the shear depends only on
t = K·u·v and solves t φ″ + φ′ = cos φ, φ(0) = 0, φ′(0) = 1 (near zero,
φ = t − t³/18). The script integrates that equation with its own Runge-Kutta
scheme and compares it with the net it built from sphere intersections. Two
facts fall out of it:

- on a sphere of radius R the shear reaches 45° at u·v = 0.815 R², so on the
  bias (u = v) at 0.90 R from the top;
- the net closes completely (90°) at u·v = 1.862 R²: no woven ply covers a
  whole sphere from one point.

**Passed.** All 24 checks hold.

## Two demonstration moulds

| Mould | Ply | Shear, median / 95th / largest | Cells above 30° / 40° / 50° |
|---|---|---|---|
| [Dome](cases/dome-on-a-plane.json) of radius 0.3 m on a plane, 50 mm foot fillet | 1.2 m square, yarns every 20 mm, warp along x | 19.1° / 45.9° / 50.0° ([record](dome-on-a-plane.json)) | 22% / 11% / 0.1% |
| [Tunnel](cases/tunnel-on-a-plane.json) of radius 0.3 m on a plane, 50 mm foot fillet | the same, warp at 45° to the axis | 0.016° everywhere ([record](tunnel-on-a-plane.json), [picture](media/tunnel-on-a-plane.png)) | none |

- **A developable mould costs nothing.** The tunnel, its fillets and the
  ground are all developable, so the ply lies on them without shear at any
  warp angle.
- **A dome costs shear on the bias.** Half of the cells shear by more than
  19°, and 11% by more than 40°, in four lobes at the foot.
- **The sheared ply is thicker there.** Yarns pack closer where the cells
  close: up to 1.56 times more fibre per area in the dome case, and the
  ply covers 1.317 m² of mould with 1.44 m² of flat pattern.
- **Give the mould its fillets.** Over a sharp crease the net steps across
  the corner and lands unevenly; the shear beyond is noise. A first run of
  the same dome without its fillet showed it; that run is not kept.

## Run it

```bash
python3 scripts/kinematic_draping.py witness --output <new.json>
python3 scripts/kinematic_draping.py drape benchmarks/kinematic-draping/cases/dome-on-a-plane.json \
  --output <report.json> --plot <picture.png>
```

A case names a mould (`sphere`, `dome`, `tunnel`, or `height_grid` with an
`.npz` of `x`, `y`, `z`), a start point, the warp angle and the yarn spacing.
The picture needs matplotlib; the rest needs NumPy only.

## What this does not establish

- **No force.** No friction, bending stiffness, blank holder, gravity or
  tension: the method gives the shear a pinned net needs, not whether a real
  ply reaches it, and not the shape of a wrinkle.
- **No fabric.** A locking angle is a property of one fabric and must come
  from a cited source; none is admitted in this repository. The shares above
  30°, 40° and 50° are information, not a verdict.
- **Woven or biaxial only.** A unidirectional ply does not shear as a pinned
  net.
- **One start point, two geodesic generators.** Another start point or
  another generator path gives another shear field; a ply book would compare
  several.
- **Height-field moulds from above.** An undercut or a closed section needs
  the mould split first.
- **No mould of the monocoque was draped.** The cell's shape is not settled
  ([dimensional correction](../../twins/964-chassis/dimensional-correction-20261106/README.md)).
- **Sources.** The method goes back to Mack and Taylor (1956); the net
  equation is Servant's. Neither was opened for this work: the checks above
  stand on the equation's own derivation and on two constructions that agree.
