using System.Diagnostics;
using System.Globalization;
using System.Numerics;
using System.Security.Cryptography;
using System.Text.Json;
using PicoGK;

// A geometry qualification job on a supplied head, never an engine solver.
// No transform, global smoothing, master overwrite or invented interfaces.
if (args.Length != 3 ||
    !float.TryParse(args[2], NumberStyles.Float, CultureInfo.InvariantCulture, out float voxelMm) ||
    !float.IsFinite(voxelMm) || voxelMm < 0.1f || voxelMm > 1f)
{
    Console.Error.WriteLine("Usage: HeadVoxels INPUT_STL NEW_OUTPUT_DIR VOXEL_MM (0.1..1.0)");
    return 2;
}

string input = Path.GetFullPath(args[0]);
string output = Path.GetFullPath(args[1]);
if (!File.Exists(input) || Directory.Exists(output) || File.Exists(output))
{
    Console.Error.WriteLine("Input must exist; output directory must not exist (no overwrite).");
    return 2;
}

string Sha(string path)
{
    using var stream = File.OpenRead(path);
    return Convert.ToHexString(SHA256.HashData(stream)).ToLowerInvariant();
}
float[] V(Vector3 value) => [value.X, value.Y, value.Z];
object Box(BBox3 value) => new { min = V(value.vecMin), max = V(value.vecMax) };
var timer = Stopwatch.StartNew();
void Stage(string stage)
{
    Console.WriteLine(JsonSerializer.Serialize(new { stage, elapsed_seconds = timer.Elapsed.TotalSeconds }));
    Console.Out.Flush();
}
Directory.CreateDirectory(output);
try
{
    string inputSha = Sha(input);
    Stage("load_input_stl_mm_no_transform");
    using Library library = new(voxelMm);
    Mesh source = Mesh.mshFromStlFile(input, Mesh.EStlUnit.MM, libSet: library);
    int sourceTriangles = source.nTriangleCount();
    if (sourceTriangles <= 0) throw new InvalidDataException("Input mesh is empty");
    Stage("voxelize_master_copy");
    Voxels voxels = new(source);
    voxels.CalculateProperties(out float volume, out BBox3 bounds);
    if (!float.IsFinite(volume) || volume <= 0) throw new InvalidDataException("Nonpositive voxel volume");
    Stage("export_roundtrip");
    Mesh roundtrip = new(voxels);
    string roundtripPath = Path.Combine(output, "head-roundtrip.stl");
    roundtrip.SaveToStlFile(roundtripPath, Mesh.EStlUnit.MM);

    // Opening by a radius-0.75 mm ball is a morphological feature-screen.
    // It flags corners/ridges AND narrow features; NOT a wall-thickness test.
    // These diagnostic volumes are not candidates for manufacture.
    const float openingRadius = 0.75f;
    Stage("morphological_opening_diagnostic_only");
    Voxels opened = voxels.voxDoubleOffset(-openingRadius, openingRadius);
    opened.BoolIntersect(voxels);
    Voxels removed = voxels.voxBoolSubtract(opened);
    removed.CalculateProperties(out float removedVolume, out BBox3 removedBounds);
    string removedPath = Path.Combine(output, "opening-sensitive-features.stl");
    Mesh removedMesh = new(removed);
    removedMesh.SaveToStlFile(removedPath, Mesh.EStlUnit.MM);

    string finalInputSha = Sha(input);
    if (finalInputSha != inputSha) throw new InvalidDataException("Input changed during run");
    var report = new
    {
        schema = "m64-picogk-geometry-run-v1",
        status = "geometry_job_completed_not_physics_validation",
        utc_completed = DateTimeOffset.UtcNow,
        input_sha256 = inputSha,
        input_unchanged = true,
        input_triangles = sourceTriangles,
        units = "mm_under_unverified_1_scan_unit_per_mm_hypothesis",
        transform = "identity",
        voxel_mm = voxelMm,
        voxel_volume_mm3 = volume,
        voxel_bounds_mm = Box(bounds),
        roundtrip = new { filename = "head-roundtrip.stl", sha256 = Sha(roundtripPath), triangles = roundtrip.nTriangleCount() },
        morphology = new
        {
            operation = "erosion_then_dilation_intersect_original",
            radius_mm = openingRadius,
            sensitive_volume_mm3 = removedVolume,
            sensitive_volume_fraction = removedVolume / volume,
            filename = "opening-sensitive-features.stl",
            sha256 = Sha(removedPath),
            triangles = removedMesh.nTriangleCount(),
            is_wall_thickness_measurement = false,
            is_manufacturing_candidate = false
        },
        elapsed_seconds = timer.Elapsed.TotalSeconds,
        peak_working_set_bytes = Process.GetCurrentProcess().PeakWorkingSet64,
        master_modified = false,
        exterior_redesigned = false,
        thermal_simulation = false,
        structural_simulation = false,
        manufacturing_authorized = false
    };
    File.WriteAllText(Path.Combine(output, "run-report.json"), JsonSerializer.Serialize(report, new JsonSerializerOptions { WriteIndented = true }));
    Stage("M64_PICOGK_GEOMETRY_PASS");
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
    Console.Error.WriteLine($"M64_PICOGK_GEOMETRY_FAIL {exception.GetType().Name}: {exception.Message}");
    return 1;
}
