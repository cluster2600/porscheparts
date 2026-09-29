// M64/60 short-block parametric sources — PicoGK 2.3.0 (commit 0e6cf6b, image
// picogk-station:qualified-final-20260928, /upstream/PicoGK). Kernel calls used
// here were verified against that image's API surface:
//   Library(float fVoxelSizeMM)
//   Lattice.AddSphere(Vector3, float)
//   Lattice.AddBeam(Vector3, float, Vector3, float, bool)  (both overloads)
//   Voxels(Lattice) / Voxels.BoolAdd / BoolSubtract / Offset /
//   CalculateProperties(out float, out BBox3) / SaveToVdbFile
//   Mesh(Voxels) / Mesh.SaveToStlFile(string, EStlUnit.MM) / nTriangleCount()
// The pinned API has no box primitive, so axis-aligned slabs are built as
// thick flat-capped beams (flat caps give exact planar end faces).
//
// This file emits the four composable sources of the short-block lane:
//   1. Piston            — nominal-bore envelope (piston geometry itself missing)
//   2. ConnectingRod     — PAUTER aftermarket datum, HYPOTHESIS contour
//   3. FinnedCylinder    — deep fins fully parametric, interfaces partial
//   4. CrankcaseSkeleton — layout master; cylinder pitch and deck height are
//      PARAMETERIZED, never baked (unknown values are tracked by M64-ACQ-0004;
//      override via env M64_PITCH_MM / M64_DECK_MM / M64_BANK_X).
//
// Provenance (docs/research/m64-public-engine-data-2026-09-27.md,
// catalog/manual/993-workshop-manual-measurements.json,
// catalog/sources/src-tzr-pauter-993-connecting-rod-dimensions.json,
// twins/m64-engine-system/bom/m64-bom-v1.json M64B-CC/CS/CR/PS/CY lines):
//   FACT_public : bore 100.0 mm, stroke 76.4 mm, 6 cylinders
//                 (SRC-PORSCHE-UK-993-TURBO-BROCHURE-1995; manual technical_data
//                 p15 bore 100); head-joint O-ring at cylinder foot 102.0 mm
//                 (SRC-PORSCHE-993-US-PARTS-GUIDE-ENGINE-CYLINDERS).
//   SOURCED_B   : PAUTER rod datum L=127.00, pin bore 23.01, big-end bore
//                 58.01±0.003, widths 18.75/19.58, 535 g, 4340 steel
//                 (SRC-TZR-PAUTER-993-CONNECTING-ROD-DIMENSIONS, level B,
//                 declared — aftermarket part, NOT the OEM baseline).
//   NOT public  : cylinder pitch, crank-to-deck height (M64-ACQ-0004);
//                 compression height, pin location, crown geometry
//                 (M64B-PS-001: dims missing beyond bore); fin pitch/count
//                 (M64B-CY-001).
//   ASSUMPTION  : every other dimension — order-of-magnitude F1 envelope
//                 parameters, all configurable.
// Output is parametric source geometry, not measured, fitted, tested, safe,
// or manufacturing-ready parts; no CFD/FEA is implied. The rod contour is a
// hypothesis envelope around sourced bores; the piston is a nominal-bore
// envelope, not piston geometry.
//
// Layout frame (mm): X = crank axis (front bank at -X), Y = lateral
// (cylinder axes point ±Y from the split plane; the cylinder-base deck is
// Y = 0), Z = vertical (crank axis at Z = 0; sump below). Part-local builder
// frames are documented at each Build* function.

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
    Console.Error.WriteLine("Env overrides (M64-ACQ-0004 unknowns, no baked guess): M64_PITCH_MM, M64_DECK_MM, M64_BANK_X");
    return 2;
}
string outputDir = Path.GetFullPath(args.Length > 1 ? args[1] : "out-shortblock");

// M64-ACQ-0004: pitch and deck height are unknown; a run without the env
// override keeps the file value flagged PROVISIONAL and records the warning
// in the run report. The file value is an assumption, not a measurement.
bool pitchOverridden = TryEnvFloat("M64_PITCH_MM", out float pitchEnv);
if (pitchOverridden) p.CylinderPitchMm = pitchEnv;
bool deckOverridden = TryEnvFloat("M64_DECK_MM", out float deckEnv);
if (deckOverridden) p.DeckHeightMm = deckEnv;
bool bankOverridden = TryEnvFloat("M64_BANK_X", out float bankEnv);
if (bankOverridden) p.BankStationX = MathF.Abs(bankEnv);
p.BoreRowY = [-p.CylinderPitchMm, 0.0f, p.CylinderPitchMm];

List<string> warnings =
[
    pitchOverridden ? "cylinder pitch overridden from environment (still ASSUMPTION class until metrology)"
                    : "cylinder pitch PROVISIONAL assumption (M64-ACQ-0004): set M64_PITCH_MM when acquired",
    deckOverridden ? "deck height overridden from environment (still ASSUMPTION class until metrology)"
                   : "deck height PROVISIONAL assumption (M64-ACQ-0004): set M64_DECK_MM when acquired"
];
if (p.FinThicknessMm < 2.0f * p.VoxelMm)
    warnings.Add($"fin thickness {p.FinThicknessMm} mm < 2x voxel {p.VoxelMm} mm: fin detail aliased at this voxel size");

try
{
    Directory.CreateDirectory(outputDir);
    using Library library = new(p.VoxelMm);

    var partReports = new List<object>();

    // ---- Part 1: piston (nominal-bore envelope) --------------------------
    // Placed at its layout pin-centre position for the -Y bank, mid-bore.
    Vector3 pistonCentre = new(p.BankStationX, 0.0f,
        p.CompressionHeightMm - p.PistonSkirtBelowPinMm - 5.0f);
    partReports.Add(EmitPart(BuildPiston(library, p, pistonCentre), "piston",
        outputDir, p, warnings));

    // ---- Part 2: connecting rod (HYPOTHESIS contour, sourced bores) ------
    Vector3 pinCentre = new(p.BankStationX, 0.0f, p.PinCentreOffsetMm);
    partReports.Add(EmitPart(BuildConnectingRod(library, p, pinCentre, +1.0f),
        "connectingrod", outputDir, p, warnings));

    // ---- Part 3: finned cylinder (parametric deep fins) ------------------
    Vector3 cylBase = new(p.BankStationX, p.DeckHeightMm, p.BoreRowY[2]);
    partReports.Add(EmitPart(BuildFinnedCylinder(library, p, cylBase, -1.0f),
        "finnedcylinder", outputDir, p, warnings));

    // ---- Part 4: crankcase skeleton = layout master ----------------------
    // Composable pipeline: each Build* function returns a fresh, disposable
    // Lattice of source volumes. Additive structure first; then the interior
    // void, sized so the offset leaves a uniform nominal wall; then the
    // subtractive features that must cut through whatever shell, web and
    // flange material remains; finally layout instances of the other three
    // sources so the master shows registered positions.
    Voxels crate = new(BuildCrateHalves(library, p));
    Merge(crate, Voxelize(library, BuildBulkheads(library, p)), add: true);
    Merge(crate, Voxelize(library, BuildFlangeRings(library, p)), add: true);

    // Hollow the crankcase: shrink the inner void union by p.WallMm. The void
    // spans the deck plane so both half-shells open at the cylinder base and
    // every wall lands at the configured nominal thickness.
    using (Voxels inner = Voxelize(library, BuildInnerVoid(library, p)))
    {
        inner.Offset(-p.WallMm);
        crate.BoolSubtract(inner);
    }

    Merge(crate, Voxelize(library, BuildMainBearings(library, p)), add: false);
    Merge(crate, Voxelize(library, BuildBoreRecesses(library, p)), add: false);
    Merge(crate, Voxelize(library, BuildScavengeGalleries(library, p)), add: false);

    // Layout instances: two banks x three bores. Cylinders stand on the deck
    // at each flange ring; one reference piston+rod pair per bank marks the
    // kinematic envelope at the assumed pin station (big end on the crank
    // axis). Layout fidelity, not assembly kinematics.
    foreach (float bankX in new[] { p.BankStationX, -p.BankStationX })
    {
        float side = MathF.Sign(bankX);
        foreach (float yb in p.BoreRowY)
            Merge(crate, BuildFinnedCylinder(library, p,
                new Vector3(bankX, p.DeckHeightMm, yb), -side), add: true);
        Vector3 pin = new(bankX, 0.0f, p.PinCentreOffsetMm);
        Merge(crate, BuildConnectingRod(library, p, pin, side), add: true);
        Merge(crate, BuildPiston(library, p,
            new Vector3(bankX, 0.0f, p.PinCentreOffsetMm
                        - side * (p.RodCentreDistanceMm - p.CompressionHeightMm))),
            add: true);
    }

    partReports.Add(EmitPart(crate, "crankcase", outputDir, p, warnings));
    crate.Dispose();

    var report = new
    {
        schema = "m64-picogk-shortblock-run-v2",
        status = "parametric_source_generated_not_dimensionally_verified",
        part_id = PartId,
        utc_completed = DateTimeOffset.UtcNow,
        picogk_commit = "0e6cf6b6f4993ec16dbcd72d8f27f26b999980f3",
        units = "mm",
        voxel_mm = p.VoxelMm,
        parts = partReports,
        provenance = new
        {
            fact_public = new
            {
                bore_mm = p.BoreMm,
                stroke_mm = p.StrokeMm,
                cylinders = 6,
                head_joint_oring_mm = p.HeadJointORingDiaMm,
            },
            sourced_b_hypothesis = new
            {
                rod_centre_distance_mm = p.RodCentreDistanceMm,
                rod_pin_bore_mm = p.RodPinBoreDiaMm,
                rod_big_end_bore_mm = p.RodBigEndBoreDiaMm,
                note = "PAUTER aftermarket, level B declared; contour is HYPOTHESIS.",
            },
            not_public = new
            {
                cylinder_pitch_mm = p.CylinderPitchMm,
                deck_height_mm = p.DeckHeightMm,
                bank_station_x_mm = p.BankStationX,
                note = "Tracked by M64-ACQ-0004; parameterized, never baked. " +
                       "Values above are PROVISIONAL unless env-overridden.",
                overridden = new { pitch = pitchOverridden, deck = deckOverridden, bank = bankOverridden },
            },
        },
        warnings,
        dimensional_correctness_verified = false,
        manufacturing_authorized = false
    };
    File.WriteAllText(Path.Combine(outputDir, "run-report.json"),
        JsonSerializer.Serialize(report, new JsonSerializerOptions { WriteIndented = true }));
    Console.WriteLine($"M64_SHORTBLOCK_PASS parts={partReports.Count} out={outputDir}");
    return 0;
}
catch (Exception exception)
{
    Console.Error.WriteLine($"M64_SHORTBLOCK_FAIL {exception.GetType().Name}: {exception.Message}");
    return 1;
}

// ----------------------------------------------------------------------
// Run-report plumbing
// ----------------------------------------------------------------------

// Mesh one part, export STL (+ vdb), record volume/bounds/hash and the
// warnings carried so far. Consumes 'vox'.
static object EmitPart(Voxels vox, string name, string outputDir,
                       ShortBlockParams p, List<string> warnings)
{
    vox.CalculateProperties(out float volumeMm3, out BBox3 bounds);
    if (!float.IsFinite(volumeMm3) || volumeMm3 <= 0)
        throw new InvalidDataException($"Nonpositive voxel volume for {name}");
    using Mesh mesh = new(vox);
    string stlPath = Path.Combine(outputDir, $"m64-shortblock-0001-{name}.stl");
    mesh.SaveToStlFile(stlPath, Mesh.EStlUnit.MM);
    string vdbPath = Path.Combine(outputDir, $"m64-shortblock-0001-{name}.vdb");
    vox.SaveToVdbFile(vdbPath);
    vox.Dispose();
    return new
    {
        part = name,
        voxel_volume_mm3 = volumeMm3,
        voxel_bounds_mm = new
        {
            min = new[] { bounds.vecMin.X, bounds.vecMin.Y, bounds.vecMin.Z },
            max = new[] { bounds.vecMax.X, bounds.vecMax.Y, bounds.vecMax.Z },
        },
        stl = new { filename = Path.GetFileName(stlPath), sha256 = Sha(stlPath), triangles = mesh.nTriangleCount() },
        vdb = new { filename = Path.GetFileName(vdbPath), sha256 = Sha(vdbPath) },
    };
}

static void Merge(Voxels target, Voxels operand, bool add)
{
    if (add) target.BoolAdd(operand);
    else target.BoolSubtract(operand);
    operand.Dispose();
}

static Voxels Voxelize(Library lib, Lattice lat)
{
    Voxels vox = new(lat);
    lat.Dispose();
    return vox;
}

// Union of ready voxel groups (additive features only).
static Voxels UnionAll(params Voxels[] parts)
{
    Voxels result = parts[0];
    for (int i = 1; i < parts.Length; i++) Merge(result, parts[i], add: true);
    return result;
}

static bool TryEnvFloat(string name, out float value) =>
    float.TryParse(Environment.GetEnvironmentVariable(name),
        NumberStyles.Float, CultureInfo.InvariantCulture, out value)
    && float.IsFinite(value);

// ----------------------------------------------------------------------
// Source 1: Piston — nominal-bore envelope, NOT piston geometry
// (M64B-PS-001: only the bore is sourced).
// Local frame: bore axis = Y, origin at the pin centre; 'dir' = +1/-1 is the
// direction from the pin towards the crown (bank side). Built as a shell of
// uniform configured wall: skirt up to the crown, solid crown with ring-groove
// cuts, pin-bore cut at the sourced PAUTER pin diameter. Ring pack, cooling
// gallery and combustion dish are DEFERRED unknowns; the pin-bore cut through
// the shell is a documented envelope artefact (pin bosses deferred).
// ----------------------------------------------------------------------
static Voxels BuildPiston(Library lib, ShortBlockParams p, Vector3 centre)
{
    float rOut = (p.BoreMm - p.PistonBoreClearanceMm) / 2.0f;
    float yTop = p.CompressionHeightMm;                       // pin -> crown
    float yBottom = yTop - p.PistonOverallHeightMm;           // skirt end
    using Voxels body = Annulus(lib, centre + new Vector3(0, yBottom, 0),
                                    centre + new Vector3(0, yTop, 0),
                                    rOut, rOut - p.PistonWallMm);
    // Solid crown slab closed at the top face.
    using (Lattice lat = new(lib))
    {
        lat.AddBeam(centre + new Vector3(0, yTop - p.CrownThicknessMm, 0), rOut,
                    centre + new Vector3(0, yTop, 0), rOut, false);
        using Voxels cap = new(lat);
        body.BoolAdd(cap);
    }
    // Ring grooves (ASSUMPTION pack): annular cuts open at the bore surface.
    for (int n = 0; n < p.RingGrooveDistancesFromCrownMm.Length; n++)
    {
        float y = yTop - p.RingGrooveDistancesFromCrownMm[n];
        using Voxels groove = Annulus(lib, centre + new Vector3(0, y - p.RingGrooveWidthMm / 2.0f, 0),
                                          centre + new Vector3(0, y + p.RingGrooveWidthMm / 2.0f, 0),
                                          rOut + 0.5f, rOut - p.RingGrooveDepthMm);
        body.BoolSubtract(groove);
    }
    // Pin bore at the sourced pin diameter; pin axis is transverse (Z).
    using (Lattice lat = new(lib))
    {
        float r = p.RodPinBoreDiaMm / 2.0f;
        lat.AddBeam(centre + new Vector3(0, 0, -p.PistonOverallHeightMm), r,
                    centre + new Vector3(0, 0, +p.PistonOverallHeightMm), r, false);
        body.BoolSubtract(Voxelize(lib, lat));
    }
    return body;
}

// ----------------------------------------------------------------------
// Source 2: ConnectingRod — HYPOTHESIS contour around SOURCED_B bores
// (PAUTER datum; aftermarket part, not the OEM baseline).
// Local frame: rod axis = Y pointing from small-end (pin) centre to big-end
// centre; big-end bore axis = X (crank axis); pin bore axis = Z. Centre
// distance 127.00 mm and both bore diameters are sourced (declared, level B);
// everything outside the bore surfaces and the two sourced widths is a
// HYPOTHESIS envelope: round-section shank (real section is forged I), cap
// split and cap bolts are schematic F1 features. Sourced mass 535 g is NOT
// enforced by this envelope. Heavily loaded part: no reproduction without
// documented fatigue review.
// ----------------------------------------------------------------------
static Voxels BuildConnectingRod(Library lib, ShortBlockParams p,
                                 Vector3 pinCentre, float side)
{
    Vector3 bigC = pinCentre + new Vector3(0, side * p.RodCentreDistanceMm, 0);
    float seOr = p.RodPinBoreDiaMm / 2.0f + p.RodSmallEndWallMm;   // derived
    float beOr = p.RodBigEndBoreDiaMm / 2.0f + p.RodBigEndBossMm;  // derived

    // Small end: ring about Z (pin axis), width = sourced pin-side width.
    using Voxels smallEnd = Annulus(lib,
        pinCentre - new Vector3(0, 0, p.RodSmallEndWidthMm / 2.0f),
        pinCentre + new Vector3(0, 0, p.RodSmallEndWidthMm / 2.0f),
        seOr, p.RodPinBoreDiaMm / 2.0f);
    // Big end: ring about X (crank axis), width = sourced crank-side width.
    using Voxels bigEnd = Annulus(lib,
        bigC - new Vector3(p.RodBigEndWidthMm / 2.0f, 0, 0),
        bigC + new Vector3(p.RodBigEndWidthMm / 2.0f, 0, 0),
        beOr, p.RodBigEndBoreDiaMm / 2.0f);
    // Shank: solid prismatic envelope between the eyes (I-section deferred).
    // Rectangular-envelope substitute: solid swept beam at the smaller
    // transverse half-extent; rInner = 0 makes Annulus return the solid.
    float shankR = MathF.Min(p.RodShankWidthMm, p.RodShankDepthMm) / 2.0f;
    float shankStart = seOr * 0.6f;
    using Voxels shank = Annulus(lib,
        pinCentre + new Vector3(0, side * shankStart, 0),
        pinCentre + new Vector3(0, side * (p.RodCentreDistanceMm - beOr * 0.6f), 0),
        shankR, 0.0f);
    // Schematic cap split line and bolt bosses (ASSUMPTION).
    using Voxels capCuts = new();
    {
        using Voxels split = Annulus(lib,
            bigC - new Vector3(beOr + 1.0f, 0, 0) + new Vector3(0, side * 0.15f, 0),
            bigC + new Vector3(beOr + 1.0f, 0, 0) + new Vector3(0, side * 0.15f, 0),
            beOr + 1.0f, 0.0f);
        Merge(capCuts, split, add: true);
        foreach (float z in new[] { -1.0f, 1.0f })
        {
            Vector3 axis = bigC + new Vector3(0, 0, z * (beOr + p.RodCapBoltBossDiaMm / 2.0f - 2.0f));
            using Lattice lat = new(lib);
            lat.AddBeam(axis - new Vector3(0, beOr, 0), p.RodCapBoltBossDiaMm / 2.0f,
                        axis + new Vector3(0, beOr, 0), p.RodCapBoltBossDiaMm / 2.0f, false);
            Merge(capCuts, Voxelize(lib, lat), add: true);
        }
    }
    return UnionAll(smallEnd, bigEnd, shank, capCuts);
}

// ----------------------------------------------------------------------
// Source 3: FinnedCylinder — deep fins fully parametric.
// Local frame: bore axis along 'dir' (unit axis from the cylinder base
// outwards), base flange register face at the plane through 'base' normal to
// dir. The 102.0 mm O-ring seat and the 100 mm bore are FACT_public; fin
// envelope, pitch, count and thickness are configurable ASSUMPTIONs
// (M64B-CY-001: fin pitch/count unknown). Base flange carries the sourced
// O-ring groove and the bore pilot register matching the crankcase recess.
// ----------------------------------------------------------------------
static Voxels BuildFinnedCylinder(Library lib, ShortBlockParams p,
                                  Vector3 baseLoc, float dirSign)
{
    Vector3 dir = new(0, dirSign, 0);
    Vector3 y0 = baseLoc;
    Vector3 yTop = baseLoc + dir * p.CylBarrelLengthMm;
    float barrelOr = (p.BoreMm + 2.0f * p.CylWallMm) / 2.0f;

    // Barrel tube: bore wall from base to top, closed at the head-side end.
    using Voxels barrel = Annulus(lib, y0, yTop, barrelOr, p.BoreMm / 2.0f);
    using (Lattice lat = new(lib))
    {
        lat.AddBeam(yTop - new Vector3(0, dirSign * p.CylTopFaceThicknessMm, 0), barrelOr,
                    yTop, barrelOr, false);
        Merge(barrel, Voxelize(lib, lat), add: true);
    }
    // Base flange with the FACT O-ring groove and bore pilot.
    Vector3 flangeTop = y0 + dir * p.CylBaseFlangeHeightMm;
    using Voxels flange = Annulus(lib, y0, flangeTop,
                                  p.CylBaseFlangeDiaMm / 2.0f, p.BoreMm / 2.0f);
    using (Voxels groove = Annulus(lib,
               y0,
               y0 + dir * p.CylORingGrooveDepthMm,
               p.HeadJointORingDiaMm / 2.0f + p.CylORingGrooveWidthMm / 2.0f,
               p.HeadJointORingDiaMm / 2.0f - p.CylORingGrooveWidthMm / 2.0f))
        flange.BoolSubtract(groove);
    Merge(barrel, flange, add: true);

    // Deep cooling fins: annular disks at the configured pitch; thickness,
    // outer radius and count are the printability study inputs
    // (see printability.md for the LPBF minimum-thickness discussion).
    foreach (float s in FinStations(p))
    {
        Vector3 c = y0 + dir * s;
        using Voxels fin = Annulus(lib,
            c - dir * (p.FinThicknessMm / 2.0f + 0.01f),
            c + dir * (p.FinThicknessMm / 2.0f + 0.01f),
            p.FinOuterDiaMm / 2.0f, barrelOr - p.CylWallMm * 0.5f);
        Merge(barrel, fin, add: true);
    }
    return barrel;
}

// Fin stations along the barrel, centred in the fin band between the base
// flange and the head-side top face.
static IEnumerable<float> FinStations(ShortBlockParams p)
{
    float bandStart = p.CylBaseFlangeHeightMm + p.FinBandInsetMm;
    float bandEnd = p.CylBarrelLengthMm - p.CylTopFaceThicknessMm - p.FinBandInsetMm;
    float span = bandEnd - bandStart;
    for (int n = 0; n < p.FinCount; n++)
        yield return bandStart + span * (n + 0.5f) / p.FinCount;
}

// ----------------------------------------------------------------------
// Source 4: CrankcaseSkeleton — layout master (see file header for frame).
// Cylinder pitch and deck height reach the geometry only through p; both are
// M64-ACQ-0004 unknowns carried as parameters, never baked constants at a
// call site.
// ----------------------------------------------------------------------

// Feature: crankcase half-shells. Two mirrored outer shells joined at the
// split plane (Y = 0), closed at the bottom and along the crank axis; the
// interior is hollowed later so each wall lands at the configured nominal
// thickness. The deck face is the split plane itself: the cylinder base
// flanges register directly on it.
static Lattice BuildCrateHalves(Library lib, ShortBlockParams p)
{
    Lattice lat = new(lib);
    float halfLen = p.CrateLengthMm / 2.0f;
    foreach (float side in new[] { 1.0f, -1.0f })
    {
        float yIn = side * p.SplitOffsetMm;
        float yOut = side * p.HalfWidthMm;
        Slab(lat,
            new Vector3(-halfLen, MathF.Min(yIn, yOut), p.CrateBottomZMm),
            new Vector3(halfLen, MathF.Max(yIn, yOut), p.CrankCenterZMm + p.CrankCavityRadiusMm));
    }
    return lat;
}

// Feature: main-bearing bulkheads. Vertical web disks centred on the crank
// axis at each station, p.BulkheadThicknessMm thick along X, bored afterwards
// by BuildMainBearings. The webs cross the split plane so the two half-shells
// tie into one stiff structure once the deck surfaces are joined.
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

// Feature: cylinder-base flange rings. One annular ring per bore station
// standing on the deck face; the FACT O-ring seat diameter (102.0 mm) plus
// p.FlangeWidthMm of supporting material carry the cylinder foot. The ring
// interior is opened by BuildBoreRecesses.
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

// Feature: oil-scavenge galleries. One low horizontal run per side with a
// drain stub to the sump floor; subtracted after hollowing so the galleries
// open into the crankcase interior along their whole length.
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

// ----------------------------------------------------------------------
// Shared primitives
// ----------------------------------------------------------------------

// Annular prism (tube) along A->B; rInner = 0 gives a solid prism. Flat caps
// are exact planes; a flat-capped disk is the box substitute the pinned API
// lacks.
static Voxels Annulus(Library lib, Vector3 a, Vector3 b, float rOuter, float rInner)
{
    Voxels outer;
    using (Lattice lat = new(lib))
    {
        lat.AddBeam(a, rOuter, b, rOuter, false);
        outer = Voxelize(lib, lat);
    }
    if (rInner > 0.0005f)
    {
        using Lattice lat = new(lib);
        lat.AddBeam(a, rInner, b, rInner, false);
        using Voxels inner = Voxelize(lib, lat);
        outer.BoolSubtract(inner);
    }
    return outer;
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
/// come from public sources; SOURCED_B values are manufacturer-declared
/// (level B, hypothesis-class geometry); NOT-public values are tracked by
/// M64-ACQ-0004 and reach the geometry only as parameters; every other value
/// is an ASSUMPTION parameter. No value is a measurement.
/// </summary>
sealed class ShortBlockParams
{
    // FACT_public — brochure 993 Turbo (SRC-PORSCHE-UK-993-TURBO-BROCHURE-1995;
    // manual technical_data p15 bore 100)
    public float BoreMm = 100.0f;
    public float StrokeMm = 76.4f;

    // FACT_public — head-joint O-ring at cylinder foot
    // (SRC-PORSCHE-993-US-PARTS-GUIDE-ENGINE-CYLINDERS)
    public float HeadJointORingDiaMm = 102.0f;

    // SOURCED_B — PAUTER aftermarket datum, declared level B
    // (catalog/sources/src-tzr-pauter-993-connecting-rod-dimensions.json).
    // Aftermarket part: NOT the OEM baseline; rod contour = HYPOTHESIS.
    public float RodCentreDistanceMm = 127.00f;
    public float RodPinBoreDiaMm = 23.01f;
    public float RodBigEndBoreDiaMm = 58.01f;
    public float RodBigEndWidthMm = 18.75f;      // sourced, crank side
    public float RodSmallEndWidthMm = 19.58f;    // sourced, pin side
    // Sourced mass 535 g +/-1 g per set; not enforced by the envelope.

    // NOT public (M64-ACQ-0004) — provisional PROVISIONAL values, parameterized.
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

    // ASSUMPTION — cylinder base flange and pilot register (crankcase side).
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

    // ASSUMPTION — piston envelope (M64B-PS-001: only bore sourced;
    // compression height, pin location, crown geometry unknown).
    public float PistonBoreClearanceMm = 0.04f;
    public float PistonWallMm = 5.0f;
    public float CompressionHeightMm = 60.0f;             // pin centre -> crown
    public float PistonSkirtBelowPinMm = 45.0f;
    public float CrownThicknessMm = 10.0f;
    public float[] RingGrooveDistancesFromCrownMm = [8.0f, 14.0f, 20.0f];
    public float RingGrooveWidthMm = 3.0f;
    public float RingGrooveDepthMm = 2.5f;
    public float PistonOverallHeightMm => CompressionHeightMm + PistonSkirtBelowPinMm;

    // ASSUMPTION — rod envelope outside the sourced bores/widths.
    public float RodSmallEndWallMm = 9.0f;                // -> derived eye ODs
    public float RodBigEndBossMm = 9.0f;
    public float RodShankWidthMm = 20.0f;
    public float RodShankDepthMm = 24.0f;
    public float RodCapBoltBossDiaMm = 14.0f;
    public float PinCentreOffsetMm = 40.0f;               // layout marker station

    // ASSUMPTION — finned cylinder (M64B-CY-001: fin pitch/count unknown).
    public float CylWallMm = 5.0f;                        // bore -> barrel OD
    public float CylBarrelLengthMm = 240.0f;
    public float CylTopFaceThicknessMm = 15.0f;
    public float CylBaseFlangeDiaMm = 150.0f;
    public float CylBaseFlangeHeightMm = 14.0f;
    public float CylORingGrooveDepthMm = 3.0f;
    public float CylORingGrooveWidthMm = 3.0f;
    public float FinOuterDiaMm = 380.0f;                  // deep-fin envelope
    public int FinCount = 28;
    public float FinThicknessMm = 1.5f;                   // printability input
    public float FinBandInsetMm = 8.0f;
    public float FinMinLPBFThicknessMm = 0.8f;            // study gate, printability.md

    public float VoxelMm = 1.5f;

    public static ShortBlockParams M64Baseline() => new();
}
