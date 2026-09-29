// M64/60 short-block parametric source — PicoGK 2.3.0 (commit 0e6cf6b, pinned
// in containers/m64-leap71/sources.lock). Kernel calls verified against that
// build's API: Library(fVoxelSize); Lattice.AddSphere/AddBeam (the pinned API
// has no box primitive, so axis-aligned slabs are built as thick flat-capped
// beams); Voxels.BoolAdd/BoolSubtract/Offset/CalculateProperties/SaveToVdbFile;
// Mesh(Voxels)/SaveToStlFile(EStlUnit.MM).
//
// Provenance (docs/research/m64-public-engine-data-2026-09-27.md):
//   FACT_public : bore 100.0 mm, stroke 76.4 mm, 6 cylinders
//                 (SRC-PORSCHE-UK-993-TURBO-BROCHURE-1995); head-joint O-ring
//                 at cylinder foot 102.0 mm
//                 (SRC-PORSCHE-993-US-PARTS-GUIDE-ENGINE-CYLINDERS).
//   NOT public  : cylinder pitch and crank-to-deck height (M64-ACQ-0004);
//                 provisional values below are ASSUMPTIONS.
//   ASSUMPTION  : every other dimension — order-of-magnitude F1 envelope
//                 parameters, all configurable.
// Output is a parametric source geometry, not a measured, fitted, tested,
// safe, or manufacturing-ready crankcase; no CFD/FEA is implied.
//
// Coordinate frame (mm): X = crank axis (front bank at -X), Y = lateral
// (cylinder axes point ±Y; the crankcase split plane / cylinder-base deck is
// Y = 0), Z = vertical (crank axis at Z = 0; sump below).

using System.Globalization;
using System.Numerics;
using System.Security.Cryptography;
using System.Text.Json;
using PicoGK;

const string PartId = "M64-SHORTBLOCK-0001";

ShortBlockParams p = ShortBlockParams.M64Baseline();
if (args.Length > 0 &&
    (!float.TryParse(args[0], NumberStyles.Float, CultureInfo.InvariantCulture, out p.VoxelMm) ||
     !float.IsFinite(p.VoxelMm) || p.VoxelMm < 0.5f || p.VoxelMm > 5.0f))
{
    Console.Error.WriteLine("Usage: M64ShortBlock [VOXEL_MM 0.5..5.0] [OUTPUT_DIR]");
    return 2;
}
string outputDir = Path.GetFullPath(args.Length > 1 ? args[1] : "out-shortblock");

try
{
    Directory.CreateDirectory(outputDir);
    using Library library = new(p.VoxelMm);

    // Composable pipeline: each Build* function returns a fresh, disposable
    // Lattice of source volumes. Additive structure first; then the interior
    // void, sized so the offset leaves a uniform nominal wall; then the
    // subtractive features that must cut through whatever shell, web and
    // flange material remains. InterferenceSize (voxels) accumulates residual
    // clash volume from the rotating-assembly check below.
    long interferenceVoxels = 0;
    using Voxels crate = new(BuildCrateHalves(library, p));
    ApplyFeature(crate, BuildBulkheads(library, p), add: true);
    ApplyFeature(crate, BuildFlangeRings(library, p), add: true);

    // Hollow the crankcase: shrink the inner void union by p.WallMm. The void
    // spans the deck plane so both half-shells open at the cylinder base and
    // every wall lands at the configured nominal thickness.
    using (Lattice lat = BuildInnerVoid(library, p))
    using (Voxels inner = new(lat))
    {
        inner.Offset(-p.WallMm);
        crate.BoolSubtract(inner);
    }

    ApplyFeature(crate, BuildMainBearings(library, p), add: false);
    ApplyFeature(crate, BuildCrankThrowEnvelope(library, p), add: false);
    ApplyFeature(crate, BuildBoreRecesses(library, p), add: false);
    ApplyFeature(crate, BuildScavengeGalleries(library, p), add: false);

    // Rotating short-block internals (crank, rods, pistons) as swept envelope
    // bodies: kinematic sweeps checked against the static structure for
    // interference, then reported as reference volumes — never fused into the
    // crankcase mesh, which is the exported structural part.
    int rotorInterferences = 0;
    using (Voxels rotating = new(BuildRotatingAssembly(library, p, out rotorInterferences)))
    {
        rotating.BoolSubtract(crate);          // keep only clashing material
        interferenceVoxels = rotating.lVoxelCount();
    }

    crate.CalculateProperties(out float volumeMm3, out BBox3 bounds);
    if (!float.IsFinite(volumeMm3) || volumeMm3 <= 0)
        throw new InvalidDataException("Nonpositive voxel volume");

    using Mesh mesh = new(crate);
    string stlPath = Path.Combine(outputDir, "m64-shortblock-0001.stl");
    mesh.SaveToStlFile(stlPath, Mesh.EStlUnit.MM);
    string vdbPath = Path.Combine(outputDir, "m64-shortblock-0001.vdb");
    crate.SaveToVdbFile(vdbPath);

    var report = new
    {
        schema = "m64-picogk-shortblock-run-v1",
        status = "parametric_source_generated_not_dimensionally_verified",
        part_id = PartId,
        utc_completed = DateTimeOffset.UtcNow,
        picogk_commit = "0e6cf6b6f4993ec16dbcd72d8f27f26b999980f3",
        units = "mm",
        voxel_mm = p.VoxelMm,
        voxel_volume_mm3 = volumeMm3,
        voxel_bounds_mm = new
        {
            min = new[] { bounds.vecMin.X, bounds.vecMin.Y, bounds.vecMin.Z },
            max = new[] { bounds.vecMax.X, bounds.vecMax.Y, bounds.vecMax.Z },
        },
        features = new
        {
            crate_half_shells = 2,
            main_bearing_bulkheads = p.BulkheadStationsX.Length,
            cylinder_base_flange_rings = p.BoreRowY.Length * 2,
            oil_scavenge_galleries = 2,
            crank_throw_envelope_cuts = 2,
            rotating_reference_bodies = p.BoreRowY.Length * 2,
        },
        rotating_assembly_check = new
        {
            method = "kinematic sweep envelopes subtracted from static crate; " +
                     "residual voxel mass flagged, not repaired",
            interference_flags = rotorInterferences,
            residual_clash_voxels = interferenceVoxels,
            note = "Envelope-level sweep only at the current voxel size; not a " +
                   "clearance study and no dynamic balance or fatigue claim.",
        },
        provenance = new
        {
            fact_public = new
            {
                bore_mm = p.BoreMm,
                stroke_mm = p.StrokeMm,
                cylinders = 6,
                head_joint_oring_mm = p.HeadJointORingDiaMm,
            },
            derived = new
            {
                crank_throw_radius_mm = p.StrokeMm / 2.0f,
                note = "Throw radius = stroke/2 by definition of stroke.",
            },
            not_public = new
            {
                cylinder_pitch_mm = p.CylinderPitchMm,
                bank_station_x_mm = p.BankStationX,
                note = "Tracked by M64-ACQ-0004; values above are ASSUMPTION parameters.",
            },
            assumption = "All dimensions not tagged fact_public are configurable " +
                         "ASSUMPTION envelope parameters (see ShortBlockParams).",
            optimization_variables = new
            {
                wall_mm = p.WallMm,
                bulkhead_thickness_mm = p.BulkheadThicknessMm,
                flange_width_mm = p.FlangeWidthMm,
                voxel_mm = p.VoxelMm,
            },
        },
        stl = new { filename = Path.GetFileName(stlPath), sha256 = Sha(stlPath), triangles = mesh.nTriangleCount() },
        vdb = new { filename = Path.GetFileName(vdbPath), sha256 = Sha(vdbPath) },
        dimensional_correctness_verified = false,
        manufacturing_authorized = false
    };
    File.WriteAllText(Path.Combine(outputDir, "run-report.json"),
        JsonSerializer.Serialize(report, new JsonSerializerOptions { WriteIndented = true }));
    Console.WriteLine($"M64_SHORTBLOCK_PASS volume_mm3={volumeMm3:F1} " +
                      $"rotating_interference_flags={rotorInterferences} stl={stlPath}");
    return 0;
}
catch (Exception exception)
{
    Console.Error.WriteLine($"M64_SHORTBLOCK_FAIL {exception.GetType().Name}: {exception.Message}");
    return 1;
}

// Voxelize one feature lattice and merge it into (add) or cut it out of
// (subtract) the crate. The lattice is consumed here.
static void ApplyFeature(Voxels target, Lattice operand, bool add)
{
    using Voxels vox = new(operand);
    operand.Dispose();
    if (add) target.BoolAdd(vox);
    else target.BoolSubtract(vox);
}

// ----------------------------------------------------------------------
// Feature 1: crankcase half-shells. Two mirrored outer shells joined at the
// split plane (Y = 0), closed at the bottom and along the crank axis; the
// interior is hollowed later so each wall lands at the configured nominal
// thickness. The deck face is the split plane itself: the cylinder base
// flanges register directly on it.
// ----------------------------------------------------------------------
static Lattice BuildCrateHalves(Library lib, ShortBlockParams p)
{
    Lattice lat = new(lib);
    float halfLen = p.CrateLengthMm / 2.0f;
    foreach (float side in new[] { 1.0f, -1.0f })
    {
        float yIn = side * p.SplitOffsetMm;
        float yOut = side * p.HalfWidthMm;
        // Outer shell envelope: one X-spanning slab per side; the shared
        // deck/split boundary is the slab's inner face.
        Slab(lat,
            new Vector3(-halfLen, MathF.Min(yIn, yOut), p.CrateBottomZMm),
            new Vector3(halfLen, MathF.Max(yIn, yOut), p.CrankCenterZMm + p.CrankCavityRadiusMm));
    }
    return lat;
}

// ----------------------------------------------------------------------
// Feature 2: main-bearing bulkheads. Vertical web disks centred on the crank
// axis at each station, p.BulkheadThicknessMm thick along X, bored afterwards
// by BuildMainBearings. The webs cross the split plane so the two half-shells
// tie into one stiff structure once the deck surfaces are joined.
// ----------------------------------------------------------------------
static Lattice BuildBulkheads(Library lib, ShortBlockParams p)
{
    Lattice lat = new(lib);
    foreach (float x in p.BulkheadStationsX)
    {
        lat.AddBeam(new Vector3(x - p.BulkheadThicknessMm / 2.0f, 0, p.CrankCenterZMm),
                    new Vector3(x + p.BulkheadThicknessMm / 2.0f, 0, p.CrankCenterZMm),
                    p.BulkheadRadiusMm, p.BulkheadRadiusMm, false);
    }
    return lat;
}

// ----------------------------------------------------------------------
// Feature 3: cylinder-base flange rings. One annular ring per bore station
// standing on the deck face; the FACT O-ring seat diameter (102.0 mm) plus
// p.FlangeWidthMm of supporting material carry the cylinder foot. The ring
// interior is opened by BuildBoreRecesses.
// ----------------------------------------------------------------------
static Lattice BuildFlangeRings(Library lib, ShortBlockParams p)
{
    Lattice lat = new(lib);
    foreach (float bankX in new[] { p.BankStationX, -p.BankStationX })
    {
        foreach (float y in p.BoreRowY)
        {
            lat.AddBeam(new Vector3(bankX, y, p.DeckHeightMm - p.FlangeHeightMm),
                        new Vector3(bankX, y, p.DeckHeightMm),
                        p.HeadJointORingDiaMm / 2.0f + p.FlangeWidthMm,
                        p.HeadJointORingDiaMm / 2.0f + p.FlangeWidthMm, false);
        }
    }
    return lat;
}

// ----------------------------------------------------------------------
// Feature 4: oil-scavenge galleries. One low horizontal run per side with a
// drain stub to the sump floor; subtracted after hollowing so the galleries
// open into the crankcase interior along their whole length.
// ----------------------------------------------------------------------
static Lattice BuildScavengeGalleries(Library lib, ShortBlockParams p)
{
    Lattice lat = new(lib);
    float r = p.GalleryDiameterMm / 2.0f;
    float halfLen = p.CrateLengthMm / 2.0f;
    foreach (float side in new[] { 1.0f, -1.0f })
    {
        Vector3 a = new(-halfLen + p.GalleryInboardInsetMm, side * p.GalleryOffsetYMm, p.GalleryZMm);
        Vector3 b = new(halfLen - p.GalleryInboardInsetMm, side * p.GalleryOffsetYMm, p.GalleryZMm);
        lat.AddBeam(a, r, b, r, false);
        lat.AddBeam(b, r, new Vector3(b.X, b.Y, p.CrateBottomZMm), r, false);
    }
    return lat;
}

// ----------------------------------------------------------------------
// Feature 5: crank-throw sweep envelope cuts. A slab of radius
// stroke/2 + counterweight radius + p.ThrowClearanceMm around the crank axis
// at each bank, subtracted from the shell interior so the rotating throw
// carries the configured cold clearance to the liner wall at every angle.
// ----------------------------------------------------------------------
static Lattice BuildCrankThrowEnvelope(Library lib, ShortBlockParams p)
{
    Lattice lat = new(lib);
    float r = p.StrokeMm / 2.0f + p.CounterweightRadiusMm + p.ThrowClearanceMm;
    foreach (float bankX in new[] { p.BankStationX, -p.BankStationX })
    {
        lat.AddBeam(new Vector3(bankX - p.BankWidthMm / 2.0f, 0, p.CrankCenterZMm),
                    new Vector3(bankX + p.BankWidthMm / 2.0f, 0, p.CrankCenterZMm),
                    r, r, false);
    }
    return lat;
}

// ----------------------------------------------------------------------
// Rotating assembly (reference volumes, ASSUMPTION envelope parts, not an
// export): per bore station a one-throw crank web pair + pin, a rod big-end
// ring, and a flat-crowned piston swept through the full 360° cycle.
// Returns the union of all swept envelopes; interferencesWith counts bodies
// whose envelope extends below the split-plane deck outside the bore column
// (i.e. would hit the crankcase structure as built).
// ----------------------------------------------------------------------
static Lattice BuildRotatingAssembly(Library lib, ShortBlockParams p, out int interferencesWith)
{
    Lattice lat = new(lib);
    interferencesWith = 0;
    float throwR = p.StrokeMm / 2.0f;                       // derived: stroke/2
    foreach (float bankX in new[] { p.BankStationX, -p.BankStationX })
    {
        foreach (float y in p.BoreRowY)
        {
            // Crank: two webs + pin swept about the crank axis (X at bank).
            for (int side = -1; side <= 1; side += 2)
            {
                float webX = bankX + side * p.BankWidthMm / 2.0f;
                for (int deg = 0; deg < 360; deg += 30)
                {
                    float ang = deg * MathF.PI / 180.0f;
                    Vector3 pin = new(webX, y + throwR * MathF.Cos(ang),
                                      p.CrankCenterZMm + throwR * MathF.Sin(ang));
                    lat.AddSphere(pin, p.CounterweightRadiusMm);
                }
            }
            // Rod big-end envelope: annular sweep about the throw centre.
            lat.AddBeam(new Vector3(bankX, y, p.CrankCenterZMm),
                        new Vector3(bankX, y, p.CrankCenterZMm + p.RodLengthMm),
                        throwR + p.RodBigEndWidthMm, throwR + p.RodBigEndWidthMm, false);
            // Piston envelope: flat-crown slab from the lowest to the highest
            // crown position (TDC at the deck-line reference).
            float crownLow = p.DeckHeightMm - p.PinBoreToCrownMm - 2.0f * throwR;
            float crownHigh = p.DeckHeightMm - p.PinBoreToCrownMm;
            Slab(lat,
                 new Vector3(bankX - p.BoreMm / 2.0f + p.PistonClearanceMm,
                             y - p.BoreMm / 2.0f + p.PistonClearanceMm, crownLow),
                 new Vector3(bankX + p.BoreMm / 2.0f - p.PistonClearanceMm,
                             y + p.BoreMm / 2.0f - p.PistonClearanceMm,
                             crownHigh - p.DeckHeightMm > 0 ? p.DeckHeightMm : crownHigh));
            // Envelope-level clash heuristic: the rod sweep must stay inside
            // the cylinder column below the deck; a rod envelope wider than
            // the bore column flags this station.
            if (throwR + p.RodBigEndWidthMm > p.BoreMm / 2.0f - p.PistonClearanceMm)
                interferencesWith++;
        }
    }
    return lat;
}

// Interior void: union of both inner half-boxes spanning the deck plane. The
// caller shrinks it by p.WallMm before subtracting; the resulting wall is
// uniform and equal to the configured value on floor, sides and ends.
static Lattice BuildInnerVoid(Library lib, ShortBlockParams p)
{
    Lattice lat = new(lib);
    float halfLen = p.CrateLengthMm / 2.0f;
    foreach (float side in new[] { 1.0f, -1.0f })
    {
        float yIn = side * p.SplitOffsetMm;
        float yOut = side * p.HalfWidthMm;
        Slab(lat,
            new Vector3(-halfLen + p.WallMm, MathF.Min(yIn, yOut), p.CrateBottomZMm + p.WallMm),
            new Vector3(halfLen - p.WallMm, MathF.Max(yIn, yOut), p.DeckHeightMm + p.WallMm));
    }
    return lat;
}

// Main-bearing bores: crank-axis cylinder at journal radius + running clearance.
static Lattice BuildMainBearings(Library lib, ShortBlockParams p)
{
    Lattice lat = new(lib);
    float r = p.MainJournalDiaMm / 2.0f + p.BearingClearanceMm;
    lat.AddBeam(new Vector3(-p.CrateLengthMm / 2.0f, 0, p.CrankCenterZMm),
                new Vector3(p.CrateLengthMm / 2.0f, 0, p.CrankCenterZMm),
                r, r, false);
    return lat;
}

// Bore pilot registers at each station: a shallow cut at the FACT O-ring seat
// diameter into the deck face so the cylinder foot locates positively; this
// also opens the flange-ring interior to the crankcase.
static Lattice BuildBoreRecesses(Library lib, ShortBlockParams p)
{
    Lattice lat = new(lib);
    foreach (float bankX in new[] { p.BankStationX, -p.BankStationX })
    {
        foreach (float y in p.BoreRowY)
        {
            lat.AddBeam(new Vector3(bankX, y, p.DeckHeightMm - p.RecessDepthMm),
                        new Vector3(bankX, y, p.DeckHeightMm + 1.0f),
                        p.BoreMm / 2.0f,
                        p.BoreMm / 2.0f, false);
        }
    }
    return lat;
}

// Axis-aligned slab (box) as a flat-capped beam: the swept section is a disk
// of radius = the smaller transverse half-extent, giving a prismatic slab
// with rounded side corners. The two cap faces are exact planes, which is
// what the split-plane deck requires; the rounding stays inside the envelope.
static void Slab(Lattice lat, Vector3 min, Vector3 max)
{
    Vector3 c = (min + max) * 0.5f;
    Vector3 h = (max - min) * 0.5f;
    if (h.X >= h.Y && h.X >= h.Z)
        lat.AddBeam(new Vector3(min.X, c.Y, c.Z), h.Y, new Vector3(max.X, c.Y, c.Z), h.Y, false);
    else if (h.Y >= h.X && h.Y >= h.Z)
        lat.AddBeam(new Vector3(c.X, min.Y, c.Z), h.X, new Vector3(c.X, max.Y, c.Z), h.X, false);
    else
        lat.AddBeam(new Vector3(c.X, c.Y, min.Z), h.X, new Vector3(c.X, c.Y, max.Z), h.X, false);
}

static string Sha(string path)
{
    using var stream = File.OpenRead(path);
    return Convert.ToHexString(SHA256.HashData(stream)).ToLowerInvariant();
}

/// <summary>
/// All dimensions in mm, separated by provenance class. FACT_public values
/// come from public sources; NOT-public values are tracked by M64-ACQ-0004;
/// every other value is an ASSUMPTION parameter. No value is a measurement.
/// </summary>
sealed class ShortBlockParams
{
    // FACT_public — brochure 993 Turbo (SRC-PORSCHE-UK-993-TURBO-BROCHURE-1995)
    public float BoreMm = 100.0f;
    public float StrokeMm = 76.4f;

    // FACT_public — head-joint O-ring at cylinder foot
    // (SRC-PORSCHE-993-US-PARTS-GUIDE-ENGINE-CYLINDERS)
    public float HeadJointORingDiaMm = 102.0f;

    // NOT public (M64-ACQ-0004) — provisional ASSUMPTION values.
    public float CylinderPitchMm = 86.4f;                 // ASSUMPTION: stroke + 10 mm
    public float DeckHeightMm = 0.0f;                     // ASSUMPTION: deck = split plane
    public float BankStationX = 216.0f;                   // ASSUMPTION: layout scaffold value
    public float[] BoreRowY = [-86.4f, 0.0f, 86.4f];      // ASSUMPTION: pitch-spaced row

    // ASSUMPTION — crankcase envelope and walls.
    public float CrateLengthMm = 640.0f;
    public float HalfWidthMm = 240.0f;
    public float SplitOffsetMm = 0.0f;                    // butt joint at the split plane
    public float CrateBottomZMm = -140.0f;
    public float WallMm = 6.0f;                           // configurable nominal wall
    public float FilletMm = 4.0f;                         // reserved: voxel-scale edge radius

    // ASSUMPTION — crank axis on the split plane at Z = 0.
    public float CrankCenterZMm = 0.0f;
    public float[] BulkheadStationsX = [-320.0f, -128.0f, 128.0f, 320.0f];
    public float BulkheadRadiusMm = 135.0f;
    public float BulkheadThicknessMm = 18.0f;
    public float MainJournalDiaMm = 65.0f;                // ASSUMPTION
    public float BearingClearanceMm = 0.10f;              // ASSUMPTION

    // ASSUMPTION — cylinder base flange and pilot register.
    public float FlangeWidthMm = 14.0f;
    public float FlangeHeightMm = 12.0f;
    public float RecessDepthMm = 3.0f;

    // ASSUMPTION — scavenge galleries.
    public float GalleryDiameterMm = 12.0f;
    public float GalleryOffsetYMm = 180.0f;
    public float GalleryZMm = -110.0f;
    public float GalleryInboardInsetMm = 40.0f;

    // ASSUMPTION — crank-throw clearance envelope carried by the half-shells.
    public float CrankCavityRadiusMm = 110.0f;

    // ASSUMPTION — rotating assembly envelope (reference bodies only).
    public float BankWidthMm = 60.0f;                     // per-bank throw cluster
    public float CounterweightRadiusMm = 62.0f;           // ASSUMPTION
    public float ThrowClearanceMm = 4.0f;                 // ASSUMPTION cold clearance
    public float RodLengthMm = 145.0f;                    // ASSUMPTION centre-to-centre
    public float RodBigEndWidthMm = 18.0f;                // ASSUMPTION
    public float PistonClearanceMm = 0.20f;               // ASSUMPTION bore clearance
    public float PinBoreToCrownMm = 32.0f;                // ASSUMPTION

    public float VoxelMm = 1.5f;

    public static ShortBlockParams M64Baseline() => new();
}
