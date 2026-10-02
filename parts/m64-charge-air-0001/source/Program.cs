using System.Diagnostics;
using System.Numerics;
using System.Security.Cryptography;
using System.Text.Json;
using PicoGK;
using M64DigitalTwin.ChargeAir;

// M64/60 charge-air path geometry study — headless PicoGK job.
// Concept geometry only: no dimensional validation, no fitment, no testing,
// no release, no manufacturing authorization. Charge-air line dimensions are
// missing in the BOM; sources are vendor envelopes (see provenance.json).
// Repository-standard export: Mesh(Voxels) + SaveToStlFile(path,
// Mesh.EStlUnit.MM), the call pattern verified by containers/picogk-m64.
// Dockerfile witness (SDK 9.0.317, picogk.26.2.so).

if (args.Length != 1)
{
    Console.Error.WriteLine("Usage: ChargeAir NEW_OUTPUT_DIR");
    return 2;
}

string output = Path.GetFullPath(args[0]);
if (Directory.Exists(output) || File.Exists(output))
{
    Console.Error.WriteLine("Output directory must not exist (no overwrite).");
    return 2;
}

ChargeAirParameters P = new();
if (P.fVoxelSizeMm <= 0 || P.fVoxelSizeMm > P.fWallThicknessMm)
{
    Console.Error.WriteLine("Voxel size must be positive and no coarser than the wall thickness.");
    return 2;
}

string Sha(string path)
{
    using var stream = File.OpenRead(path);
    return Convert.ToHexString(SHA256.HashData(stream)).ToLowerInvariant();
}

var timer = Stopwatch.StartNew();
void Stage(string stage)
{
    Console.WriteLine(JsonSerializer.Serialize(new { stage, elapsed_seconds = timer.Elapsed.TotalSeconds }));
    Console.Out.Flush();
}

Directory.CreateDirectory(output);
try
{
    using Library library = new(P.fVoxelSizeMm);
    List<object> parts = new();

    void ExportPart(string name, Func<Voxels> build)
    {
        Stage("build_" + name);
        using Voxels vox = build();
        vox.CalculateProperties(out float volume, out BBox3 bounds);
        if (!float.IsFinite(volume) || volume <= 0)
            throw new InvalidDataException($"Nonpositive voxel volume for {name}");
        using Mesh mesh = new(vox);
        int triangles = mesh.nTriangleCount();
        if (triangles <= 0) throw new InvalidDataException($"Empty mesh for {name}");
        string path = Path.Combine(output, name + ".stl");
        mesh.SaveToStlFile(path, Mesh.EStlUnit.MM);
        parts.Add(new
        {
            name,
            stl = Path.GetFileName(path),
            sha256 = Sha(path),
            triangles,
            voxel_volume_mm3 = volume,
            bounds_mm = new
            {
                min = new[] { bounds.vecMin.X, bounds.vecMin.Y, bounds.vecMin.Z },
                max = new[] { bounds.vecMax.X, bounds.vecMax.Y, bounds.vecMax.Z }
            }
        });
    }

    ExportPart("tube-compressor-to-throttle-bank-posy", () => ChargeAirGeometry.TubeVoxels(P, false));
    ExportPart("tube-compressor-to-throttle-bank-negy", () => ChargeAirGeometry.TubeVoxels(P, true));
    ExportPart("coupling-bank-posy", () => ChargeAirGeometry.CouplingVoxels(P, false));
    ExportPart("coupling-bank-negy", () => ChargeAirGeometry.CouplingVoxels(P, true));
    ExportPart("plenum-bank-posy", () => ChargeAirGeometry.PlenumVoxels(P, false));
    ExportPart("plenum-bank-negy", () => ChargeAirGeometry.PlenumVoxels(P, true));
    ExportPart("hose-interconnect-bank-posy", () => ChargeAirGeometry.HoseVoxels(P, false));
    ExportPart("hose-interconnect-bank-negy", () => ChargeAirGeometry.HoseVoxels(P, true));
    ExportPart("charge-air-assembly", () => ChargeAirGeometry.AssemblyVoxels(P));

    Stage("centerline_report");
    float fTubeLen = ChargeAirGeometry.CenterlineLengthMm(P.aTubeWaypointsPosBank);
    float fHoseLen = ChargeAirGeometry.CenterlineLengthMm(P.aHoseWaypointsPosBank);
    bool hoseInBand = fHoseLen >= P.fHoseEnvelopeMinLenMm && fHoseLen <= P.fHoseEnvelopeMaxLenMm;

    var report = new
    {
        schema = "m64-picogk-geometry-run-v1",
        status = "geometry_job_completed_not_physics_validation",
        part_id = "M64-CHARGE-AIR-0001",
        utc_completed = DateTimeOffset.UtcNow,
        voxel_mm = P.fVoxelSizeMm,
        wall_mm = P.fWallThicknessMm,
        radial_clearance_mm = P.fRadialClearanceMm,
        hose_min_bend_radius_assumption_mm = P.fHoseMinBendRadiusMm,
        throttle_bore_assumption_mm = P.fThrottleBoreDiaMm,
        runner_offsets_y_mm = P.aRunnerOffsetsY,
        units = "mm_engine_frame_plusX_rear_plusZ_up_banks_mirror_about_Y0",
        centerlines = new
        {
            tube_polyline_len_mm = fTubeLen,
            hose_polyline_len_mm = fHoseLen,
            hose_vendor_envelope_band_mm = new { min = P.fHoseEnvelopeMinLenMm, max = P.fHoseEnvelopeMaxLenMm },
            hose_length_within_vendor_envelope_band = hoseInBand,
            note = "vendor envelope band is a packaging bound of an aftermarket kit, not an OEM dimension"
        },
        boost_bar = new
        {
            study_target = P.fBoostTargetBar,
            oem_declared = P.fBoostOemBar,
            sizes_geometry = false
        },
        parts,
        elapsed_seconds = timer.Elapsed.TotalSeconds,
        peak_working_set_bytes = Process.GetCurrentProcess().PeakWorkingSet64,
        dimensionally_validated = false,
        fitted = false,
        tested = false,
        safe_claimed = false,
        released = false,
        manufacturing_authorized = false
    };
    File.WriteAllText(Path.Combine(output, "run-report.json"),
        JsonSerializer.Serialize(report, new JsonSerializerOptions { WriteIndented = true }));
    Stage("M64_PICOGK_GEOMETRY_PASS");
    return 0;
}
catch (Exception exception)
{
    File.WriteAllText(Path.Combine(output, "FAILED.json"), JsonSerializer.Serialize(new
    {
        status = "failed",
        error_type = exception.GetType().Name,
        error = exception.Message,
        elapsed_seconds = timer.Elapsed.TotalSeconds,
        manufacturing_authorized = false
    }, new JsonSerializerOptions { WriteIndented = true }));
    Console.Error.WriteLine($"M64_PICOGK_GEOMETRY_FAIL {exception.GetType().Name}: {exception.Message}");
    return 1;
}
