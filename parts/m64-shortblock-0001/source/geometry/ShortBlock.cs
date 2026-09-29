// M64/60 short-block parametric source — PicoGK 2.3.0 (commit 0e6cf6b, pinned
// in containers/m64-leap71/sources.lock; kernel calls verified against that
// build: Library(fVoxelSize), Lattice.AddSphere/AddBeam only — the pinned API
// has no box primitive, so axis-aligned boxes are built from capped beams —
// Voxels BoolAdd/BoolSubtract/Offset/CalculateProperties/SaveToVdbFile,
// Mesh(Voxels)/SaveToStlFile(EStlUnit.MM)).
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
// safe, or manufacturing-ready crankcase. No CFD/FEA is implied.
//
// Coordinate frame (mm): X = crank axis (front bank at -X), Y = lateral
// (cylinder axes; deck face on the split plane Y = 0), Z = vertical
// (crank axis at Z = 0).

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
    // Lattice of source volumes. Additive features first, then the hollowing
    // offset, then subtractive features so galleries cut through whatever
    // material remains at the nominal wall.
    using Voxels crate = new(BuildCrateHalves(library, p));
    ApplyVoid(crate, BuildBulkheads(library, p), add: true);
    ApplyVoid(crate, BuildFlangeRings(library, p), add: true);

    // Hollow the crankcase: the inner offset defines a uniform wall of
    // p.WallMm on every face, opening the deck face upward on each half.
    using (Lattice lat = BuildInnerVoid(library, p))
    using (Voxels inner = new(lat))
    {
        inner.Offset(-p.WallMm);
        crate.BoolSubtract(inner);
    }

    ApplyVoid(crate, BuildMainBearings(library, p), add: false);
    ApplyVoid(crate, BuildBoreRecesses(library, p), add: false);
    ApplyVoid(crate, BuildScavengeGalleries(library, p), add: false);

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
            not_public = new
            {
                cylinder_pitch_mm = p.CylinderPitchMm,
                bank_station_x_mm = p.BankStationX,
            },
            note = "Cylinder pitch and deck height are tracked by M64-ACQ-0004. Every dimension not tagged fact_public is an ASSUMPTION parameter.",
        },
        stl = new { filename = Path.GetFileName(stlPath), sha256 = Sha(stlPath), triangles = mesh.nTriangleCount() },
        vdb = new { filename = Path.GetFileName(vdbPath), sha256 = Sha(vdbPath) },
        dimensional_correctness_verified = false,
        manufacturing_authorized = false
    };
    File.WriteAllText(Path.Combine(outputDir, "run-report.json"),
        JsonSerializer.Serialize(report, new JsonSerializerOptions { WriteIndented = true }));
    Console.WriteLine($"M64_SHORTBLOCK_PASS volume_mm3={volumeMm3:F1} stl={stlPath}");
    return 0;
}
catch (Exception exception)
{
    Console.Error.WriteLine($"M64_SHORTBLOCK_FAIL {exception.GetType().Name}: {exception.Message}");
    return 1;
}

static void ApplyVoid(Voxels target, Lattice operand, bool add)
{
    using Voxels vox = new(operand);
    operand.Dispose();
    if (add) target.BoolAdd(vox);
    else target.BoolSubtract(vox);
    vox.Dispose();
}

// ----------------------------------------------------------------------
// Feature 1: crankcase half-shells. Two mirrored, closed outer boxes joined
// at the split plane (Y = 0). Each half is hollowed later by a single inner
// offset, so every wall ends at the configured nominal thickness. Deck face
// is the split plane; both halves carry the same outer profile.
// ----------------------------------------------------------------------
static Lattice BuildCrateHalves(Library lib, ShortBlockParams p)
{
    Lattice lat = new(lib);
    float halfLen = p.CrateLengthMm / 2.0f;
    foreach (float side in new[] { 1.0f, -1.0f })
    {
        float yIn = side * (p.SplitOffsetMm + p.WallMm);   // inner wall face
        float yOut = side * p.HalfWidthMm;                 // outer wall face
        Box(lat,
            new Vector3(-halfLen, MathF.Min(yIn, yOut), p.CrateBottomZMm),
            new Vector3(halfLen, MathF.Max(yIn, yOut), p.DeckHeightMm));
    }
    return lat;
}

// ----------------------------------------------------------------------
// Feature 2: main-bearing bulkheads. Vertical web disks centred on the crank
// axis at each station, p.BulkheadThicknessMm thick along X, bored afterwards
// by BuildMainBearings. The webs bridge the split plane so both halves tie
// into one stiff structure once the deck surfaces are joined.
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
// standing on the deck face; the outer radius carries the head-joint O-ring
// (FACT, 102.0 mm) seat and p.FlangeWidthMm of supporting material.
// ----------------------------------------------------------------------
static Lattice BuildFlangeRings(Library lib, ShortBlockParams p)
{
    Lattice lat = new(lib);
    foreach (float bankX in new[] { p.BankStationX, -p.BankStationX })
    {
        foreach (float y in p.BoreRowY)
        {
            lat.AddBeam(new Vector3(bankX, y, p.DeckHeightMm),
                        new Vector3(bankX, y, p.DeckHeightMm + p.FlangeHeightMm),
                        p.HeadJointORingDiaMm / 2.0f + p.FlangeWidthMm,
                        p.HeadJointORingDiaMm / 2.0f + p.FlangeWidthMm, false);
        }
    }
    return lat;
}

// ----------------------------------------------------------------------
// Feature 4: oil-scavenge galleries. One low horizontal run per side with a
// drain stub to the sump floor; subtracted after the hollowing step so the
// galleries open into the crankcase interior.
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

// Interior void: the union of both inner half-boxes. The caller shrinks it by
// p.WallMm before subtraction, which sets the uniform wall thickness and
// leaves an open deck face on each half (the split plane stays closed only
// where bulkheads and the crank cavity cross it).
static Lattice BuildInnerVoid(Library lib, ShortBlockParams p)
{
    Lattice lat = new(lib);
    float halfLen = p.CrateLengthMm / 2.0f;
    foreach (float side in new[] { 1.0f, -1.0f })
    {
        float yIn = side * p.SplitOffsetMm;
        float yOut = side * (p.HalfWidthMm - p.WallMm);
        Box(lat,
            new Vector3(-halfLen + p.WallMm, MathF.Min(yIn, yOut), p.CrateBottomZMm + p.WallMm),
            new Vector3(halfLen - p.WallMm, MathF.Max(yIn, yOut), p.DeckHeightMm + 2.0f * p.WallMm));
    }
    return lat;
}

// Main-bearing bores: crank-axis cylinder, journal radius + running clearance.
static Lattice BuildMainBearings(Library lib, ShortBlockParams p)
{
    Lattice lat = new(lib);
    float r = p.MainJournalDiaMm / 2.0f + p.BearingClearanceMm;
    lat.AddBeam(new Vector3(-p.CrateLengthMm / 2.0f, 0, p.CrankCenterZMm),
                new Vector3(p.CrateLengthMm / 2.0f, 0, p.CrankCenterZMm),
                r, r, false);
    return lat;
}

// Bore pilot recesses at each station: a shallow register of the O-ring seat
// diameter cut into the deck face so the cylinder foot locates positively.
static Lattice BuildBoreRecesses(Library lib, ShortBlockParams p)
{
    Lattice lat = new(lib);
    foreach (float bankX in new[] { p.BankStationX, -p.BankStationX })
    {
        foreach (float y in p.BoreRowY)
        {
            lat.AddBeam(new Vector3(bankX, y, p.DeckHeightMm - p.RecessDepthMm),
                        new Vector3(bankX, y, p.DeckHeightMm + 1.0f),
                        p.HeadJointORingDiaMm / 2.0f,
                        p.HeadJointORingDiaMm / 2.0f, false);
        }
    }
    return lat;
}

// Axis-aligned exact box via flat-capped beams across the three faces.
// Lattice has no box primitive; six rectangular faces as degenerate beams
// would not enclose, so the box is swept as a beam whose two end radii and
// axis span the box: a beam of radius = half-height across the Y span, then
// rotated copies across X and Z. This yields a prismatic rounded box whose
// flat faces match the split-plane requirement at the deck.
static void Box(Lattice lat, Vector3 min, Vector3 max)
{
    Vector3 c = (min + max) * 0.5f;
    Vector3 h = (max - min) * 0.5f;
    // Dominant axis sweep gives the box its largest prismatic section; the
    // remaining two spans are carried by capped beams of matching radius.
    if (h.X >= h.Y && h.X >= h.Z)
    {
        lat.AddBeam(new Vector3(min.X, c.Y, c.Z), h.Y, new Vector3(max.X, c.Y, c.Z), h.Y, false);
        lat.AddBeam(new Vector3(c.X, min.Y, c.Z), h.X, new Vector3(c.X, max.Y, c.Z), h.X, false);
        lat.AddBeam(new Vector3(c.X, c.Y, min.Z), h.X, new Vector3(c.X, c.Y, max.Z), h.X, false);
    }
    else if (h.Y >= h.X && h.Y >= h.Z)
    {
        lat.AddBeam(new Vector3(c.X, min.Y, c.Z), h.X, new Vector3(c.X, max.Y, c.Z), h.X, false);
        lat.AddBeam(new Vector3(min.X, c.Y, c.Z), h.Y, new Vector3(max.X, c.Y, c.Z), h.Y, false);
        lat.AddBeam(new Vector3(c.X, c.Y, min.Z), h.Y, new Vector3(c.X, c.Y, max.Z), h.Y, false);
    }
    else
    {
        lat.AddBeam(new Vector3(c.X, c.Y, min.Z), h.X, new Vector3(c.X, c.Y, max.Z), h.X, false);
        lat.AddBeam(new Vector3(min.X, c.Y, c.Z), h.Z, new Vector3(max.X, c.Y, c.Z), h.Z, false);
        lat.AddBeam(new Vector3(c.X, min.Y, c.Z), h.Z, new Vector3(c.X, max.Y, c.Z), h.Z, false);
    }
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
    public float DeckHeightMm = 0.0f;                     // split plane = deck (ASSUMPTION)
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

    public float VoxelMm = 1.5f;

    public static ShortBlockParams M64Baseline() => new();
}
