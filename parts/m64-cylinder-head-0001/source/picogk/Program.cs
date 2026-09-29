// M64 four-valve cylinder head — parametric F1 envelope module.
//
// Provenance discipline (docs/research/m64-public-engine-data-2026-09-27.md):
// only FACT_public values may enter this geometry without promotion. Every
// value below is tagged FACT_PUBLIC, CROSSCHECKED, SINGLE_SOURCE, ASSUMPTION
// or UNKNOWN, mirroring parts/m64-cylinder-head-0001/provenance.json. Most
// internal head dimensions are UNPUBLISHED (blocked by M64-ACQ-0001/0004):
// they are carried here as explicitly-named ASSUMPTION/UNKNOWN parameters so
// a later metrology release can promote or replace them one by one.
//
// This module is an envelope generator, not an engine solver: no transform
// of any scan master, no invented interfaces, and no claim of a dimensionally
// correct, fitted, tested, safe or manufacturing-ready head.

using System.Diagnostics;
using System.Globalization;
using System.Numerics;
using System.Security.Cryptography;
using System.Text.Json;
using PicoGK;

// ---------------------------------------------------------------------------
// Command line: OUTPUT_DIR VOXEL_MM [--no-view]
// The output directory must not exist yet (no overwrite), matching the
// HeadVoxels station convention in twins/m64-cylinder-head/source/picogk.
// ---------------------------------------------------------------------------
if (args.Length < 2 ||
    !float.TryParse(args[1], NumberStyles.Float, CultureInfo.InvariantCulture, out float voxelMm) ||
    !float.IsFinite(voxelMm) || voxelMm < 0.5f || voxelMm > 10f)
{
    Console.Error.WriteLine("Usage: Head4vEnvelope NEW_OUTPUT_DIR VOXEL_MM (0.5..10.0) [--no-view]");
    return 2;
}

string output = Path.GetFullPath(args[0]);
if (Directory.Exists(output) || File.Exists(output))
{
    Console.Error.WriteLine("Output directory must not exist (no overwrite).");
    return 2;
}

// ---------------------------------------------------------------------------
// Physical inputs. Authority tags: FACT_PUBLIC | ASSUMPTION | UNKNOWN.
// ---------------------------------------------------------------------------
const string FACT_PUBLIC = "FACT_PUBLIC";
const string ASSUMPTION = "ASSUMPTION";
const string UNKNOWN = "UNKNOWN";

// Public bore (FACT_PUBLIC, brochure + 993 US Parts Guide via
// docs/research/m64-public-engine-data-2026-09-27.md).
const float BoreDiameter = 100.0f;            // FACT_PUBLIC
const float HeadLengthEnvelope = 118.0f;      // ASSUMPTION: bore + 2x9 mm deck margin
const float HeadWidthEnvelope = 112.0f;       // ASSUMPTION: bore + 12 mm cover flange
const float HeadHeightEnvelope = 60.0f;       // ASSUMPTION: head height UNPUBLISHED
const float DeckThickness = 12.0f;            // ASSUMPTION: deck/cap material above fire ring
const float SeatAngleDeg = 45.0f;             // ASSUMPTION: conventional 45 deg seat; M64 4V seat angle UNPUBLISHED

// Valve envelopes (FACT_PUBLIC diameters, see provenance.json sources).
const float IntakeValveHeadD = 49.0f;         // FACT_PUBLIC
const float ExhaustValveHeadD = 43.5f;        // FACT_PUBLIC (Turbo catalogue value)
const float ValveStemD = 8.0f;                // SINGLE_SOURCE; stock 2V reference only
// ASSUMPTION: 4V valve axis layout inside the 100 mm bore. NOT metrology:
// the true 4V pattern is UNPUBLISHED (M64-ACQ-0001).
const float ValveBankOffsetY = 24.0f;         // ASSUMPTION: pair offset across bore axis
const float ValvePairSpacingX = 27.0f;        // ASSUMPTION: intake/exhaust pair spacing along bore axis

// Head studs: 12x M8x22 per head (FACT_PUBLIC quantity and size, Parts
// Guide). ASSUMPTION: the pattern (two rows of six on a 30 mm grid) is a
// placement placeholder; the true pitch is blocked by M64-ACQ-0004 and the
// derived "98.07/43.27" stud pattern is explicitly REJECTED (it is a cam
// gear dimension, not a stud pattern).
const int StudCount = 12;                     // FACT_PUBLIC
const float StudHoleDiameter = 8.5f;          // ASSUMPTION: M8 clearance hole
const float StudHoleDepth = 45.0f;            // ASSUMPTION: blind stud bore depth UNPUBLISHED
const float StudRowY = 52.0f;                 // ASSUMPTION: outer row offset
const float StudPitchX = 30.0f;               // ASSUMPTION: intra-row pitch placeholder

// Cam-carrier bosses (ASSUMPTION: positions and sizes UNPUBLISHED; one
// bore-side boss per cam axis is a minimal 4V layout, not a 917/30 or
// Swindon geometry transfer).
const float CamBossDiameter = 42.0f;          // ASSUMPTION
const float CamBossHeight = 14.0f;            // ASSUMPTION
const float CamBossBoreD = 30.0f;             // ASSUMPTION: carrier locating bore
const float CamBossY = 38.0f;                 // ASSUMPTION
const float CamBossX = 34.0f;                 // ASSUMPTION: symmetric pair along head

// ---------------------------------------------------------------------------
// Build.
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

try
{
    using Library library = new(voxelMm);
    Stage("build_head_envelope_block");

    // Single-bore single-head envelope module. Deck face (cylinder mating
    // plane) is the Z = 0 plane; +Z goes toward the valve gear. The block is
    // rendered from a mesh shell so the build uses only the documented
    // Voxels constructors (voxMeshShell, voxSphere, voxLatticeBeam, booleans).
    using Mesh blockShell = new(library);
    {
        Vector3[] c =
        [
            new(-HeadLengthEnvelope / 2f, -HeadWidthEnvelope / 2f, 0f),
            new( HeadLengthEnvelope / 2f, -HeadWidthEnvelope / 2f, 0f),
            new( HeadLengthEnvelope / 2f,  HeadWidthEnvelope / 2f, 0f),
            new(-HeadLengthEnvelope / 2f,  HeadWidthEnvelope / 2f, 0f),
            new(-HeadLengthEnvelope / 2f, -HeadWidthEnvelope / 2f, HeadHeightEnvelope),
            new( HeadLengthEnvelope / 2f, -HeadWidthEnvelope / 2f, HeadHeightEnvelope),
            new( HeadLengthEnvelope / 2f,  HeadWidthEnvelope / 2f, HeadHeightEnvelope),
            new(-HeadLengthEnvelope / 2f,  HeadWidthEnvelope / 2f, HeadHeightEnvelope),
        ];
        int[][] faces =
        [
            [0, 3, 2], [0, 2, 1],           // deck face Z = 0
            [4, 5, 6], [4, 6, 7],           // top face
            [0, 1, 5], [0, 5, 4],           // -Y
            [1, 2, 6], [1, 6, 5],           // +X
            [2, 3, 7], [2, 7, 6],           // +Y
            [3, 0, 4], [3, 4, 7],           // -X
        ];
        foreach (int[] f in faces)
            blockShell.nAddTriangle(c[f[0]], c[f[1]], c[f[2]]);
    }
    Voxels head = Voxels.voxMeshShell(library, blockShell, 0f);

    Stage("add_cam_carrier_bosses");
    foreach (float sx in new[] { -CamBossX, CamBossX })
    foreach (float sy in new[] { -CamBossY, CamBossY })
    {
        Voxels boss = Voxels.voxSphere(library,
            new Vector3(sx, sy, HeadHeightEnvelope + CamBossHeight / 2f), CamBossDiameter / 2f);
        head.BoolAdd(boss);
    }

    Stage("cut_valve_envelopes_45deg_seats");
    // Valve envelope = head-disc cone with the 45 deg seat chamfer plus a
    // straight stem bore. Cones are axis-aligned (ASSUMPTION: valve incline
    // UNPUBLISHED; a 4V axis angle would be a metrology input).
    foreach ((float dHead, string kind) in new[]
             { (IntakeValveHeadD, "intake"), (ExhaustValveHeadD, "exhaust") })
    {
        float sx = (kind == "intake" ? -ValvePairSpacingX / 2f : ValvePairSpacingX / 2f);
        foreach (float sy in new[] { -ValveBankOffsetY, ValveBankOffsetY })
        {
            Vector3 axis = new(sx, sy, 0f);
            float rSeat = dHead / 2f;
            // 45 deg seat chamfer ring of width 2.5 mm (upward-inward) as a
            // mesh shell, subtracted as a cut band in the deck face.
            using Mesh coneShell = new(library);
            int ringSegments = 64;
            Vector3[] outer = new Vector3[ringSegments];
            Vector3[] inner = new Vector3[ringSegments];
            for (int i = 0; i < ringSegments; i++)
            {
                float a = 2f * MathF.PI * i / ringSegments;
                outer[i] = axis + new Vector3(MathF.Cos(a) * rSeat, MathF.Sin(a) * rSeat, 0f);
                inner[i] = axis + new Vector3(MathF.Cos(a) * (rSeat - 2.5f),
                                              MathF.Sin(a) * (rSeat - 2.5f), 2.5f);
            }
            for (int i = 0; i < ringSegments; i++)
            {
                int j = (i + 1) % ringSegments;
                coneShell.nAddTriangle(outer[i], outer[j], inner[j]);
                coneShell.nAddTriangle(outer[i], inner[j], inner[i]);
            }
            using Voxels seat = Voxels.voxMeshShell(library, coneShell, 0.3f);

            // Stem guide bore through deck into the head body.
            Voxels stem = Voxels.voxLatticeBeam(library,
                axis + new Vector3(0, 0, -1f), ValveStemD / 2f,
                axis + new Vector3(0, 0, HeadHeightEnvelope + CamBossHeight), ValveStemD / 2f);

            // Valve-pocket clearance cylinder above the deck around the disc.
            Voxels pocket = Voxels.voxLatticeBeam(library,
                axis + new Vector3(0, 0, -0.5f), rSeat + 1.5f,
                axis + new Vector3(0, 0, DeckThickness + 1f), rSeat + 1.5f);

            head.BoolSubtract(seat);
            head.BoolSubtract(stem);
            head.BoolSubtract(pocket);
        }
    }

    Stage("cut_stud_holes_12xM8");
    float firstX = -(StudCount / 2 - 1) * StudPitchX / 2f;
    int placed = 0;
    foreach (float sy in new[] { -StudRowY, StudRowY })
    {
        for (int i = 0; i < StudCount / 2; i++)
        {
            Vector3 p = new(firstX + i * StudPitchX, sy, -1f);
            head.BoolSubtract(Voxels.voxLatticeBeam(library,
                p, StudHoleDiameter / 2f,
                p + new Vector3(0, 0, StudHoleDepth), StudHoleDiameter / 2f));
            placed++;
        }
    }

    Stage("cut_cam_boss_locating_bores_ASSUMPTION");
    foreach (float sx in new[] { -CamBossX, CamBossX })
    foreach (float sy in new[] { -CamBossY, CamBossY })
    {
        head.BoolSubtract(Voxels.voxLatticeBeam(library,
            new Vector3(sx, sy, HeadHeightEnvelope - 1f), CamBossBoreD / 2f,
            new Vector3(sx, sy, HeadHeightEnvelope + CamBossHeight + 1f), CamBossBoreD / 2f));
    }

    Stage("export_stl_mm");
    head.CalculateProperties(out float volumeMm3, out BBox3 bounds);
    using Mesh mesh = new(head);
    string stlPath = Path.Combine(output, "m64-head-4v-envelope.stl");
    mesh.SaveToStlFile(stlPath, Mesh.EStlUnit.MM);

    var report = new
    {
        schema = "m64-picogk-head4v-envelope-run-v1",
        status = "envelope_generated_not_physics_validation_no_metrology",
        utc_completed = DateTimeOffset.UtcNow,
        voxel_mm = voxelMm,
        voxel_volume_mm3 = volumeMm3,
        voxel_bounds_mm = new { min = new[] { bounds.vecMin.X, bounds.vecMin.Y, bounds.vecMin.Z },
                                max = new[] { bounds.vecMax.X, bounds.vecMax.Y, bounds.vecMax.Z } },
        export = new { filename = "m64-head-4v-envelope.stl", sha256 = Sha(stlPath),
                       triangles = mesh.nTriangleCount(), units = "mm" },
        studs_placed = placed,
        provenance_file = "../provenance.json",
        blocked_by = new[] { "M64-ACQ-0001 (stud pattern, head height, gasket thickness)",
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
