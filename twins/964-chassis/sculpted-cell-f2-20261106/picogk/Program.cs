using System.Numerics;
using System.Security.Cryptography;
using System.Text.Json;
using PicoGK;

// Consume a bound physical-wall tessellation from the same canonical loft/cap
// contract as CAD and FE. No vehicle scan, inferred interface or F1 is read.
if (args.Length != 3)
    throw new ArgumentException("BREP_DISPLAY_JSON NEW_PRIVATE_OUTPUT_DIRECTORY VOXEL_MM");
string inputPath = Path.GetFullPath(args[0]);
string output = Path.GetFullPath(args[1]);
float voxel = float.Parse(args[2], System.Globalization.CultureInfo.InvariantCulture);
using JsonDocument document = JsonDocument.Parse(File.ReadAllText(inputPath));
JsonElement input = document.RootElement;
string kind = input.GetProperty("geometry_source_kind").GetString() ?? "";
bool analytic = kind == "analytic_normal_offset_tessellation";
if (kind != "exact_brep_tessellation" && !analytic)
    throw new InvalidDataException("Expected a bound BRep or analytic normal-offset wall tessellation");
if (analytic && (input.GetProperty("units").GetString() != "mm" ||
    input.GetProperty("status").GetString() != "assumed" ||
    !input.GetProperty("two_resolution_preflight_passed").GetBoolean()))
    throw new InvalidDataException("Analytic wall tessellation requires the two-resolution preflight");
JsonElement[] components = input.GetProperty("components").EnumerateArray().ToArray();
if (components.Length == 0 || components.Length > 100)
    throw new InvalidDataException("Expected 1..100 structural wall components");
float[] thicknesses = components.Select(c => c.GetProperty("physical_thickness_mm").GetSingle()).ToArray();
float minThickness = thicknesses.Min();
if (thicknesses.Any(t => !float.IsFinite(t) || t <= 0 || t > 10) ||
    !float.IsFinite(voxel) || voxel < 0.25 || voxel > minThickness / 2)
    throw new InvalidDataException("Physical thickness must be positive <=10 mm; voxel must be in [0.25,min(t)/2] mm");
if (Directory.Exists(output) || File.Exists(output)) throw new IOException("Use a fresh output directory");
Directory.CreateDirectory(output);
string Hash(string path)
{
    using FileStream file = File.OpenRead(path);
    return Convert.ToHexString(SHA256.HashData(file)).ToLowerInvariant();
}
var watch = System.Diagnostics.Stopwatch.StartNew();
string originalInputHash = Hash(inputPath);
using Library lib = new(voxel);
Library.RegisterGlobalLibrary(lib);
try
{
    using Voxels combined = new(lib);
    var componentRecords = new List<object>();
    var names = new HashSet<string>();
    foreach (JsonElement component in components)
    {
        string name = component.GetProperty("name").GetString() ?? throw new InvalidDataException("Missing name");
        if (!names.Add(name) || component.GetProperty("scope").GetString() != "structural_cell")
            throw new InvalidDataException("Expected unique structural components; proxies are excluded");
        Vector3[] vertices = component.GetProperty("vertices_mm").EnumerateArray().Select(p =>
        {
            if (p.GetArrayLength() != 3) throw new InvalidDataException("Expected three coordinates");
            float[] a = p.EnumerateArray().Select(x => x.GetSingle()).ToArray();
            if (a.Any(x => !float.IsFinite(x) || Math.Abs(x) > 10000))
                throw new InvalidDataException("Nonfinite or oversized canonical vertex");
            return new Vector3(a[0], a[1], a[2]);
        }).ToArray();
        JsonElement[] triangles = component.GetProperty("triangles").EnumerateArray().ToArray();
        if (vertices.Length < 4 || vertices.Length > 2_000_000 || triangles.Length > 2_000_000)
            throw new InvalidDataException("Component tessellation exceeds the bounded contract");
        using Mesh mesh = new(lib);
        foreach (JsonElement face in triangles)
        {
            if (face.GetArrayLength() != 3) throw new InvalidDataException("Expected triangular faces");
            int[] ids = face.EnumerateArray().Select(x => x.GetInt32()).ToArray();
            if (ids.Any(i => i < 0 || i >= vertices.Length) || ids.Distinct().Count() != 3)
                throw new InvalidDataException("Invalid original BRep tessellation indices");
            Vector3 a = vertices[ids[0]], b = vertices[ids[1]], c = vertices[ids[2]];
            if (Vector3.Cross(b - a, c - a).LengthSquared() < 1e-16f)
                throw new InvalidDataException("Degenerate original BRep triangle");
            mesh.nAddTriangle(a, b, c);
        }
        using Voxels wall = new(mesh);
        combined.BoolAdd(wall);
        componentRecords.Add(new { name, original_vertices = vertices.Length, original_triangles = triangles.Length,
            physical_thickness_mm = component.GetProperty("physical_thickness_mm").GetSingle() });
        Console.WriteLine($"Unioned canonical wall {name}");
    }
    combined.oMetaData().SetValue("study.status", "assumed");
    combined.oMetaData().SetValue("study.source_sha256", Hash(inputPath));
    combined.CalculateProperties(out float diagnosticVolume, out BBox3 bounds);
    using Mesh result = new(combined);
    string stl = Path.Combine(output, "sculpted-cell.stl");
    result.SaveToStlFile(stl, Mesh.EStlUnit.MM);
    string vdb = Path.Combine(output, "sculpted-cell.vdb");
    using (OpenVdbFile file = new(lib)) { file.nAdd(combined, "assumed_sculpted_cell"); file.SaveToFile(vdb); }
    using OpenVdbFile restoredFile = new(lib, vdb);
    using Voxels restored = restoredFile.voxGet("assumed_sculpted_cell");
    if (!combined.bIsEqual(restored)) throw new InvalidDataException("VDB roundtrip changed native field");
    if (Hash(inputPath) != originalInputHash) throw new InvalidDataException("Input changed during native export");
    var report = new
    {
        status = "executed_native_PicoGK_assumed_geometry_only",
        input_manifest_sha256 = originalInputHash,
        geometry_source_kind = kind,
        geometry_sha256 = input.GetProperty("geometry_sha256").GetString(),
        source_STEP_sha256 = input.TryGetProperty("sourceSTEPsha256", out JsonElement stepHash) ? stepHash.GetString() : null,
        source_parameter_sha256 = input.TryGetProperty("parameter_sha256", out JsonElement parameterHash) ? parameterHash.GetString() : null,
        source_sampler_sha256 = input.TryGetProperty("sampler_sha256", out JsonElement samplerHash) ? samplerHash.GetString() : null,
        method = analytic
            ? "Canonical analytic midsurfaces sampled and offset +/-physical t/2 along their normals at two checked resolutions; fine physical-wall tessellation voxelised component by component; native PicoGK Boolean union; no repair, added thickness or scan geometry"
            : "Exact authored BRep physical-wall tessellation voxelised component by component; native PicoGK Boolean union; no repair, added thickness or scan geometry",
        voxel_mm = voxel, minimum_physical_wall_mm = minThickness,
        nominal_minimum_wall_voxels = minThickness / voxel,
        input_components = componentRecords, native_output_triangles = result.nTriangleCount(),
        native_bounds_min_mm = new[] { bounds.vecMin.X, bounds.vecMin.Y, bounds.vecMin.Z },
        native_bounds_max_mm = new[] { bounds.vecMax.X, bounds.vecMax.Y, bounds.vecMax.Z },
        raw_native_property_volume_mm3_diagnostic_only = diagnosticVolume,
        native_volume_admitted = false,
        native_volume_reason = "Known native thin-wall property discrepancy on prior synthetic controls; independent topology/integration required",
        native_vdb_roundtrip_equal = true, stl_sha256 = Hash(stl), vdb_sha256 = Hash(vdb),
        program_binary_sha256 = Hash(System.Reflection.Assembly.GetExecutingAssembly().Location),
        framework_description = System.Runtime.InteropServices.RuntimeInformation.FrameworkDescription,
        runtime_version = Environment.Version.ToString(),
        process_architecture = System.Runtime.InteropServices.RuntimeInformation.ProcessArchitecture.ToString(),
        elapsed_seconds = watch.Elapsed.TotalSeconds,
        wall_thickness_convergence_verified = false, donor_fitment_verified = false,
        strength_verified = false, manufacturing_authorized = false, native_omniverse = false
    };
    File.WriteAllText(Path.Combine(output, "report.json"), JsonSerializer.Serialize(report, new JsonSerializerOptions { WriteIndented = true }) + "\n");
}
finally { Library.UnregisterGlobalLibrary(); }
