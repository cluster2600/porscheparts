// M64 four-valve cylinder head — parametric F1 envelope module (attempt 3).
//
// Provenance discipline (docs/research/m64-public-engine-data-2026-09-27.md):
// only FACT_PUBLIC or explicitly-tagged scan-candidate values enter this
// geometry. Every value below is tagged FACT_PUBLIC, SCAN_CANDIDATE_935_C,
// V2_DESIGN, ASSUMPTION or UNKNOWN, mirroring
// parts/m64-cylinder-head-0001/provenance.json. Most internal head
// dimensions remain UNPUBLISHED (blocked by M64-ACQ-0001/0004).
//
// Layout authorities (relative to repo root):
//   - four-valve V2 submodule layout:
//     twins/m64-cylinder-head/evidence/four-valve-design-v2-20260907/build-report.json
//     (intake_x -18, exhaust_x +23.5, pair_half_spacing 22.5, diameters
//      40 / 33, stem 6, guide OD 11, 45 deg seat, seat width 1.0)
//   - G1 valve axis angles: twins/m64-cylinder-head/source/fourvalve/params/head.json
//     (26.576 deg intake / 29.162 deg exhaust, provenance candidate_935_scan_C)
//   - G2 features context: twins/m64-cylinder-head/params-g2/head_features.json
//     (ports/galerie/fins stay OUT of this envelope; ports are G2 design
//      hypotheses, kept out to avoid baking unswept beziers into the F1 body)
//   - G3 seat contact geometry: twins/m64-cylinder-head/evidence/
//     g3-seat-contact-20260925/audit.json (45 deg concordant seats, 0 overlap)
//   - plug wells: twins/m64-cylinder-head/source/fourvalve/params-plugs/
//     spark_plug_envelope.json (NGK BKR EIX-P candidate envelope, unsourced)
//
// M64-ACQ-0004 (cylinder pitch, deck height): parameterized via --params
// JSON file, never baked in. null stays null; nothing in this module
// silently defaults them to a number.

using System.Diagnostics;
using System.Globalization;
using System.Numerics;
using System.Security.Cryptography;
using System.Text.Json;
using PicoGK;

// ---------------------------------------------------------------------------
// Command line: OUTPUT_DIR VOXEL_MM [--params FILE] [--no-view]
// The output directory must not exist yet (no overwrite), matching the
// HeadVoxels station convention in twins/m64-cylinder-head/source/picogk.
// ---------------------------------------------------------------------------
if (args.Length < 2 ||
    !float.TryParse(args[1], NumberStyles.Float, CultureInfo.InvariantCulture, out float voxelMm) ||
    !float.IsFinite(voxelMm) || voxelMm < 0.5f || voxelMm > 10f)
{
    Console.Error.WriteLine("Usage: Head4vEnvelope NEW_OUTPUT_DIR VOXEL_MM (0.5..10.0) [--params FILE] [--no-view]");
    return 2;
}

string output = Path.GetFullPath(args[0]);
if (Directory.Exists(output) || File.Exists(output))
{
    Console.Error.WriteLine("Output directory must not exist (no overwrite).");
    return 2;
}

// ACQ-0004 parameters: loaded from file, kept null when absent/null.
string? paramsFile = null;
for (int i = 2; i < args.Length; i++)
    if (args[i] == "--params" && i + 1 < args.Length) paramsFile = args[++i];

double? cylinderPitchMm = null;
double? deckHeightMm = null;
if (paramsFile is not null)
{
    using JsonDocument pd = JsonDocument.Parse(File.ReadAllText(paramsFile));
    if (pd.RootElement.TryGetProperty("cylinder_pitch_mm", out JsonElement jp) &&
        jp.ValueKind == JsonValueKind.Number) cylinderPitchMm = jp.GetDouble();
    if (pd.RootElement.TryGetProperty("deck_height_mm", out JsonElement dh) &&
        dh.ValueKind == JsonValueKind.Number) deckHeightMm = dh.GetDouble();
}

// ---------------------------------------------------------------------------
// Physical inputs. Authority tags: see header.
// ---------------------------------------------------------------------------
const float BoreDiameter = 100.0f;            // FACT_PUBLIC
const float RegisterDiameter = 113.423f;      // SCAN_CANDIDATE_935_C (head.json register_diameter)
const float RegisterDepth = 2.21f;            // SCAN_CANDIDATE_935_C (head.json register_depth)
const float CarrierFaceHeight = 86.461f;      // SCAN_CANDIDATE_935_C (head.json carrier_face_height)
const float HeadLengthEnvelope = 118.0f;      // ASSUMPTION: bore + 2x9 mm deck margin
const float HeadWidthEnvelope = 112.0f;       // ASSUMPTION: bore + 12 mm cover flange
const float DeckThickness = 12.0f;            // ASSUMPTION: deck material around pockets
const float SeatAngleDeg = 45.0f;             // V2_DESIGN + G3 audit (candidate 45 deg, not Porsche)

// Four-valve V2 layout (V2 build-report.json; diameters FACT_PUBLIC from the
// Swindon M64 24V head kit product sheet quoted in that report).
const float IntakeValveHeadD = 40.0f;         // V2 / product sheet
const float ExhaustValveHeadD = 33.0f;        // V2 / product sheet
const float ValveStemD = 6.0f;                // V2
const float GuideOuterD = 11.0f;              // V2
const float GuideStartZ = 20.0f;              // V2 guide_start_above_gauge_mm
const float GuideLength = 35.0f;              // V2 guide_length_mm
const float IntakeValveX = -18.0f;            // V2 intake_x_mm
const float ExhaustValveX = 23.5f;            // V2 exhaust_x_mm
const float ValvePairHalfSpacingY = 22.5f;    // V2 pair_half_spacing_mm
const float IntakeAxisAngleDeg = 26.576f;     // SCAN_CANDIDATE_935_C (G1 head.json)
const float ExhaustAxisAngleDeg = 29.162f;    // SCAN_CANDIDATE_935_C (G1 head.json)
const float SeatBandWidth = 2.5f;             // ASSUMPTION: cutting band; G3 contact width is 1.0
const float SeatInsertWall = 2.0f;            // ASSUMPTION: head.json guide_seat_retainer radial wall
const float SeatInsertDepth = 7.0f;           // ASSUMPTION: guide_seat_retainer seat_insert_height

// Head studs: 12 per head (FACT_PUBLIC quantity, Parts Guide). Pattern
// spans from scan candidate 935 C (gasket_studs.json); hole diameter
// 10.879 SCAN_CANDIDATE_935_C. Derived "98.07/43.27" stud-pattern reading
// remains REJECTED (cam-gear dimension).
const int StudCount = 12;                     // FACT_PUBLIC
const float StudHoleDiameter = 10.879f;       // SCAN_CANDIDATE_935_C
const float StudHoleDepth = 45.0f;            // ASSUMPTION: blind depth UNPUBLISHED
const float StudSpanX = 85.824f;              // SCAN_CANDIDATE_935_C
const float StudSpanY = 86.581f;              // SCAN_CANDIDATE_935_C

// Twin spark plug wells (params-plugs/spark_plug_envelope.json: NGK BKR
// EIX-P candidate envelope; ALL unsourced). Wells are circular
// approximations of hex+thread envelopes: ASSUMPTION simplification.
const float PlugWellDiameter = 17.0f;         // ASSUMPTION: hex 16 AF + clearance
const float PlugThreadDiameter = 15.0f;       // ASSUMPTION: thread 14 + clearance
const float PlugThreadReach = 19.0f;          // UNSOURCED candidate envelope
const float Plug1X = -8.0f;                   // ASSUMPTION: between ridge and intake valve
const float Plug2X = 12.5f;                   // ASSUMPTION: between ridge and exhaust valve
const float PlugTiltDeg = 25.0f;              // ASSUMPTION: plug tilt toward chamber centre

// Cam-carrier bosses (ASSUMPTION: UNPUBLISHED; minimal 4V layout).
const float CamBossDiameter = 42.0f;          // ASSUMPTION
const float CamBossHeight = 14.0f;            // ASSUMPTION
const float CamBossBoreD = 30.0f;             // ASSUMPTION
const float CamBossY = 38.0f;                 // ASSUMPTION
const float CamBossX = 34.0f;                 // ASSUMPTION

// ---------------------------------------------------------------------------
// Build helpers.
// ---------------------------------------------------------------------------
var timer = Stopwatch.StartNew();
void Stage(string stage)
{
    Console.WriteLine(JsonSerializer.Serialize(new { stage, elapsed_seconds = timer.Elapsed.TotalSeconds }));
    Console.Out.Flush();
}

Directory.CreateDirectory(output);

string Sha(string path)
{
    using var stream = File.OpenRead(path);
    return Convert.ToHexString(SHA256.HashData(stream)).ToLowerInvariant();
}

static Vector3 AxisUp(float angleDeg, float xSign)
{
    // Valve axis tilted away from bore centreline about the Y axis,
    // as in the G1/G2 layout (axis_up in source/fourvalve/layout.py).
    float th = angleDeg * MathF.PI / 180f;
    return Vector3.Normalize(new Vector3(xSign * MathF.Sin(th), 0f, MathF.Cos(th)));
}

try
{
    using Library library = new(voxelMm);

    // ------------------------------------------------------------------
    // Head body field function: deck-face slab (deck plane Z = 0, +Z
    // toward valve gear), simplified to a block envelope in F1.
    // ------------------------------------------------------------------
    Stage("build_head_body_field");
    Voxels HeadBodyField()
    {
        using Mesh blockShell = new(library);
        Vector3[] c =
        [
            new(-HeadLengthEnvelope / 2f, -HeadWidthEnvelope / 2f, 0f),
            new( HeadLengthEnvelope / 2f, -HeadWidthEnvelope / 2f, 0f),
            new( HeadLengthEnvelope / 2f,  HeadWidthEnvelope / 2f, 0f),
            new(-HeadLengthEnvelope / 2f,  HeadWidthEnvelope / 2f, 0f),
            new(-HeadLengthEnvelope / 2f, -HeadWidthEnvelope / 2f, CarrierFaceHeight),
            new( HeadLengthEnvelope / 2f, -HeadWidthEnvelope / 2f, CarrierFaceHeight),
            new( HeadLengthEnvelope / 2f,  HeadWidthEnvelope / 2f, CarrierFaceHeight),
            new(-HeadLengthEnvelope / 2f,  HeadWidthEnvelope / 2f, CarrierFaceHeight),
        ];
        int[][] faces =
        [
            [0, 3, 2], [0, 2, 1], [4, 5, 6], [4, 6, 7],
            [0, 1, 5], [0, 5, 4], [1, 2, 6], [1, 6, 5],
            [2, 3, 7], [2, 7, 6], [3, 0, 4], [3, 4, 7],
        ];
        foreach (int[] f in faces)
            blockShell.nAddTriangle(c[f[0]], c[f[1]], c[f[2]]);
        // Solid (filled) voxelisation of the closed block mesh: the Voxels(Mesh)
        // constructor fills the interior. voxMeshShell would give a shelled
        // (hollow) body, which is why the first run exported a 55 cc shell.
        return new Voxels(blockShell);
    }
    Voxels head = HeadBodyField();

    // ------------------------------------------------------------------
    // Cam carrier bosses + locating bores.
    // ------------------------------------------------------------------
    Stage("add_cam_carrier_bosses");
    foreach (float sx in new[] { -CamBossX, CamBossX })
    foreach (float sy in new[] { -CamBossY, CamBossY })
    {
        Voxels boss = Voxels.voxSphere(library,
            new Vector3(sx, sy, CarrierFaceHeight + CamBossHeight / 2f), CamBossDiameter / 2f);
        head.BoolAdd(boss);
    }

    // ------------------------------------------------------------------
    // Four-valve V2 submodule: 4 valve axes (2 intake / 2 exhaust),
    // pockets, 45 deg seat bands, seat-insert bores, guide bores.
    // ------------------------------------------------------------------
    Stage("cut_4v_v2_valve_submodule");
    (float dHead, float vx, float axisAngle, float xSign)[] valveKinds =
    [
        (IntakeValveHeadD, IntakeValveX, IntakeAxisAngleDeg, -1f),
        (ExhaustValveHeadD, ExhaustValveX, ExhaustAxisAngleDeg, +1f),
    ];
    foreach ((float dHead, float vx, float axisAngle, float xSign) in valveKinds)
    {
        foreach (float sy in new[] { -ValvePairHalfSpacingY, ValvePairHalfSpacingY })
        {
            Vector3 axisOrigin = new(vx, sy, 0f);
            Vector3 u = AxisUp(axisAngle, xSign);
            float rSeat = dHead / 2f;

            // 45 deg seat band around the disc, perpendicular to the valve
            // axis (G3 concordant geometry: 45 deg face, contact 1 mm).
            using Mesh bandShell = new(library);
            int seg = 64;
            Vector3 ex = Vector3.Normalize(Vector3.Cross(u, Vector3.UnitZ)); // in deck plane
            Vector3 ey = Vector3.Cross(ex, u);
            Vector3[] outer = new Vector3[seg];
            Vector3[] inner = new Vector3[seg];
            for (int i = 0; i < seg; i++)
            {
                float a = 2f * MathF.PI * i / seg;
                Vector3 rad = ex * MathF.Cos(a) + ey * MathF.Sin(a);
                // Rim is sunk 0.3 mm below the deck plane so the subtractive
                // boolean never leaves a coplanar non-manifold edge on Z=0.
                outer[i] = axisOrigin + rad * rSeat - u * 0.3f;
                inner[i] = axisOrigin + rad * (rSeat - SeatBandWidth) + u * (SeatBandWidth - 0.3f);
            }
            for (int i = 0; i < seg; i++)
            {
                int j = (i + 1) % seg;
                bandShell.nAddTriangle(outer[i], outer[j], inner[j]);
                bandShell.nAddTriangle(outer[i], inner[j], inner[i]);
            }
            using Voxels seatBand = Voxels.voxMeshShell(library, bandShell, 0.3f);

            // Valve pocket clearance around the disc.
            Voxels pocket = Voxels.voxLatticeBeam(library,
                axisOrigin - u * 0.5f, rSeat + 1.5f,
                axisOrigin + u * (DeckThickness + 1f), rSeat + 1.5f);

            // Seat-insert annular bore (head.json seat_insert_height / radial wall).
            Voxels insertOuter = Voxels.voxLatticeBeam(library,
                axisOrigin - u * 0.5f, rSeat + SeatBandWidth + SeatInsertWall,
                axisOrigin + u * SeatInsertDepth, rSeat + SeatBandWidth + SeatInsertWall);
            Voxels insertInner = Voxels.voxLatticeBeam(library,
                axisOrigin - u * 1f, rSeat + SeatBandWidth,
                axisOrigin + u * (SeatInsertDepth + 1f), rSeat + SeatBandWidth);
            insertOuter.BoolSubtract(insertInner);

            // Stem bore + guide bore along the valve axis.
            Voxels stem = Voxels.voxLatticeBeam(library,
                axisOrigin - u * 1f, ValveStemD / 2f,
                axisOrigin + u * (CarrierFaceHeight + CamBossHeight), ValveStemD / 2f);
            Voxels guide = Voxels.voxLatticeBeam(library,
                axisOrigin + u * GuideStartZ, GuideOuterD / 2f,
                axisOrigin + u * (GuideStartZ + GuideLength), GuideOuterD / 2f);

            head.BoolSubtract(pocket);
            head.BoolSubtract(seatBand);
            head.BoolSubtract(insertOuter);
            head.BoolSubtract(stem);
            head.BoolSubtract(guide);
        }
    }

    // ------------------------------------------------------------------
    // Twin spark plug wells (double ignition; candidate envelope).
    // ------------------------------------------------------------------
    Stage("cut_spark_plug_wells_twin");
    foreach ((float px, float xSign) in new[] { (Plug1X, -1f), (Plug2X, +1f) })
    {
        float th = PlugTiltDeg * MathF.PI / 180f;
        Vector3 u = Vector3.Normalize(new Vector3(xSign * MathF.Sin(th), 0f, MathF.Cos(th)));
        Vector3 top = new(px, 0f, CarrierFaceHeight + CamBossHeight + 1f);
        // Well bore from the top face down to the thread section.
        head.BoolSubtract(Voxels.voxLatticeBeam(library,
            top, PlugWellDiameter / 2f,
            top - u * (CarrierFaceHeight + CamBossHeight - PlugThreadReach + 1f), PlugWellDiameter / 2f));
        // Thread reach bore down to just above deck (chamber entry).
        head.BoolSubtract(Voxels.voxLatticeBeam(library,
            top - u * (CarrierFaceHeight + CamBossHeight - PlugThreadReach + 1f), PlugThreadDiameter / 2f,
            top - u * (CarrierFaceHeight + CamBossHeight - 1f), PlugThreadDiameter / 2f));
    }

    // ------------------------------------------------------------------
    // Register bore (scan candidate) and 12 head stud holes (935 C pattern).
    // ------------------------------------------------------------------
    Stage("cut_register_and_studs");
    head.BoolSubtract(Voxels.voxLatticeBeam(library,
        new Vector3(0, 0, -1f), RegisterDiameter / 2f,
        new Vector3(0, 0, RegisterDepth), RegisterDiameter / 2f));

    int placed = 0;
    for (int row = 0; row < 2; row++)
    {
        float sy = (row == 0 ? -1f : 1f) * StudSpanY / 2f;
        for (int i = 0; i < StudCount / 2; i++)
        {
            float x = -StudSpanX / 2f + i * StudSpanX / (StudCount / 2 - 1);
            Vector3 p = new(x, sy, -1f);
            head.BoolSubtract(Voxels.voxLatticeBeam(library,
                p, StudHoleDiameter / 2f,
                p + new Vector3(0, 0, StudHoleDepth), StudHoleDiameter / 2f));
            placed++;
        }
    }

    Stage("cut_cam_boss_locating_bores_ASSUMPTION");
    foreach (float sx in new[] { -CamBossX, CamBossX })
    foreach (float sy in new[] { -CamBossY, CamBossY })
        head.BoolSubtract(Voxels.voxLatticeBeam(library,
            new Vector3(sx, sy, CarrierFaceHeight - 1f), CamBossBoreD / 2f,
            new Vector3(sx, sy, CarrierFaceHeight + CamBossHeight + 1f), CamBossBoreD / 2f));

    // ------------------------------------------------------------------
    // Export.
    // ------------------------------------------------------------------
    Stage("cleanup_offset_zero");
    // Merge any non-manifold contacts / tiny islands introduced by the
    // boolean chain before meshing (PicoGK convention: offset by 0).
    head.BoolOffset(0f);

    Stage("export_stl_mm");
    head.CalculateProperties(out float volumeMm3, out BBox3 bounds);
    using Mesh mesh = new(head);
    string stlPath = Path.Combine(output, "m64-head-4v-envelope.stl");
    mesh.SaveToStlFile(stlPath, Mesh.EStlUnit.MM);

    var report = new
    {
        schema = "m64-picogk-head4v-envelope-run-v2",
        status = "envelope_generated_not_physics_validation_no_metrology",
        utc_completed = DateTimeOffset.UtcNow,
        voxel_mm = voxelMm,
        voxel_volume_mm3 = volumeMm3,
        voxel_bounds_mm = new { min = new[] { bounds.vecMin.X, bounds.vecMin.Y, bounds.vecMin.Z },
                                max = new[] { bounds.vecMax.X, bounds.vecMax.Y, bounds.vecMax.Z } },
        export = new { filename = "m64-head-4v-envelope.stl", sha256 = Sha(stlPath),
                       triangles = mesh.nTriangleCount(), units = "mm" },
        valves_placed = 4,
        studs_placed = placed,
        acq_0004 = new
        {
            cylinder_pitch_mm = cylinderPitchMm,
            deck_height_mm = deckHeightMm,
            note = "parameterized, never baked; null means unresolved (M64-ACQ-0004)"
        },
        provenance_file = "../provenance.json",
        blocked_by = new[] { "M64-ACQ-0001 (head interior metrology, gasket thickness)",
                             "M64-ACQ-0004 (cylinder pitch, deck height)" },
        dimensionally_accurate = false,
        manufacturing_authorized = false
    };
    File.WriteAllText(Path.Combine(output, "run-report.json"),
        JsonSerializer.Serialize(report, new JsonSerializerOptions { WriteIndented = true }));
    Stage("M64_HEAD4V_ENVELOPE_PASS");
    return 0;
}
catch (Exception exception)
{
    File.WriteAllText(Path.Combine(output, "FAILED.json"), JsonSerializer.Serialize(new
    {
        status = "failed", error_type = exception.GetType().Name,
        error = exception.Message, elapsed_seconds = timer.Elapsed.TotalSeconds,
        manufacturing_authorized = false
    }, new JsonSerializerOptions { WriteIndented = true }));
    Console.Error.WriteLine($"M64_HEAD4V_ENVELOPE_FAIL {exception.GetType().Name}: {exception.Message}");
    return 1;
}
