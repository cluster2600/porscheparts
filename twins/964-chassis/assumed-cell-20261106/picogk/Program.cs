using System.Numerics;
using System.Security.Cryptography;
using System.Text.Json;
using PicoGK;
using Leap71.ShapeKernel;

// The input is the independently declared assumed midplane contract, never a
// scan reconstruction, measured attachment or a road/track release.
if (args.Length != 3)
    throw new ArgumentException("SURFACES_JSON NEW_PRIVATE_OUTPUT_DIRECTORY VOXEL_MM");
string inputPath = Path.GetFullPath(args[0]);
string output = Path.GetFullPath(args[1]);
float voxel = float.Parse(args[2], System.Globalization.CultureInfo.InvariantCulture);
using JsonDocument document = JsonDocument.Parse(File.ReadAllText(inputPath));
JsonElement input = document.RootElement;
float thickness = input.GetProperty("thickness_mm").GetSingle();
if (input.GetProperty("units").GetString() != "mm" ||
    input.GetProperty("status").GetString() != "assumed" ||
    !float.IsFinite(thickness) || thickness <= 0 || thickness > 10f ||
    !float.IsFinite(voxel) || voxel < 0.25f || voxel > thickness / 2f)
    throw new InvalidDataException("Expected assumed millimetre midplanes, physical thickness in (0,10] mm and voxel in [0.25,t/2] mm");
var boxes = new List<(string Name, Vector3 Min, Vector3 Max)>();
foreach (JsonElement panel in input.GetProperty("panels").EnumerateArray())
{
    int normal = panel.GetProperty("normal_axis").GetInt32();
    int u = panel.GetProperty("u_axis").GetInt32();
    int v = panel.GetProperty("v_axis").GetInt32();
    if (normal < 0 || normal > 2 || u != (normal + 1) % 3 || v != (normal + 2) % 3)
        throw new InvalidDataException("Panel axes must follow the declared positive-normal order");
    float[] lo = new float[3], hi = new float[3];
    lo[normal] = panel.GetProperty("at_mm").GetSingle() - thickness / 2;
    hi[normal] = panel.GetProperty("at_mm").GetSingle() + thickness / 2;
    lo[u] = panel.GetProperty("u_mm")[0].GetSingle();
    hi[u] = panel.GetProperty("u_mm")[1].GetSingle();
    lo[v] = panel.GetProperty("v_mm")[0].GetSingle();
    hi[v] = panel.GetProperty("v_mm")[1].GetSingle();
    if (lo.Concat(hi).Any(x => !float.IsFinite(x) || Math.Abs(x) > 10000) ||
        Enumerable.Range(0, 3).Any(a => lo[a] >= hi[a]))
        throw new InvalidDataException("Nonfinite, oversized or degenerate panel bounds");
    boxes.Add((panel.GetProperty("name").GetString() ?? throw new InvalidDataException("Missing panel name"),
               new Vector3(lo[0], lo[1], lo[2]), new Vector3(hi[0], hi[1], hi[2])));
}
if (boxes.Count == 0 || boxes.Count > 100 || boxes.Select(b => b.Name).Distinct().Count() != boxes.Count)
    throw new InvalidDataException("Expected 1..100 uniquely named midplane rectangles");
if (Directory.Exists(output) || File.Exists(output)) throw new IOException("Output already exists");
Directory.CreateDirectory(output);
string Hash(string path)
{
    using FileStream stream = File.OpenRead(path);
    return Convert.ToHexString(SHA256.HashData(stream)).ToLowerInvariant();
}
float Coordinate(Vector3 p, int axis) => axis == 0 ? p.X : axis == 1 ? p.Y : p.Z;
var cuts = Enumerable.Range(0, 3).Select(a => boxes.SelectMany(b => new[] { Coordinate(b.Min, a), Coordinate(b.Max, a) }).Distinct().Order().ToArray()).ToArray();
// Exact box-union reference volume; no voxel/mesh values enter this reference.
double analyticVolume = 0;
for (int i = 0; i + 1 < cuts[0].Length; i++)
for (int j = 0; j + 1 < cuts[1].Length; j++)
for (int k = 0; k + 1 < cuts[2].Length; k++)
{
    Vector3 middle = new((cuts[0][i] + cuts[0][i+1])/2, (cuts[1][j] + cuts[1][j+1])/2, (cuts[2][k] + cuts[2][k+1])/2);
    if (boxes.Any(b => middle.X > b.Min.X && middle.X < b.Max.X && middle.Y > b.Min.Y && middle.Y < b.Max.Y && middle.Z > b.Min.Z && middle.Z < b.Max.Z))
        analyticVolume += (double)(cuts[0][i+1]-cuts[0][i])*(cuts[1][j+1]-cuts[1][j])*(cuts[2][k+1]-cuts[2][k]);
}
var watch = System.Diagnostics.Stopwatch.StartNew();
using Library lib = new(voxel);
Library.RegisterGlobalLibrary(lib);
try
{
    using Voxels combined = new(lib);
    foreach (var box in boxes)
    {
        using Voxels plate = new BaseBox(new BBox3(box.Min, box.Max)).voxConstruct();
        combined.BoolAdd(plate);
        Console.WriteLine($"Unioned {box.Name}");
    }
    combined.oMetaData().SetValue("study.status", "assumed");
    combined.oMetaData().SetValue("study.units", "mm");
    combined.oMetaData().SetValue("study.source_sha256", Hash(inputPath));
    combined.CalculateProperties(out float volume, out BBox3 bounds);
    if (!float.IsFinite(volume) || volume <= 0) throw new InvalidDataException("Empty/nonfinite assumed union");
    using Mesh mesh = new(combined);
    string stl = Path.Combine(output, "assumed-cell.stl");
    mesh.SaveToStlFile(stl, Mesh.EStlUnit.MM);
    string vdb = Path.Combine(output, "assumed-cell.vdb");
    using (OpenVdbFile file = new(lib)) { file.nAdd(combined, "assumed_central_cell"); file.SaveToFile(vdb); }
    using OpenVdbFile roundtrip = new(lib, vdb);
    using Voxels restored = roundtrip.voxGet("assumed_central_cell");
    if (!combined.bIsEqual(restored)) throw new InvalidDataException("VDB roundtrip changed original field");
    var materialProbes = boxes.Select(box =>
    {
        Vector3 p = (box.Min + box.Max) / 2;
        return new { panel = box.Name, point_mm = new[] { p.X, p.Y, p.Z }, expected_inside = true, observed_inside = combined.bIsInside(p) };
    }).ToArray();
    var voidProbes = new List<object>();
    if (input.TryGetProperty("dimensions_mm", out JsonElement dimensions))
    {
        float height = dimensions.GetProperty("tunnel_height").GetSingle();
        float width = dimensions.GetProperty("tunnel_width").GetSingle();
        float[] xCuts = input.GetProperty("axis_breaks_mm").GetProperty("x").EnumerateArray().Select(x => x.GetSingle()).ToArray();
        foreach (float x in xCuts.Zip(xCuts.Skip(1), (a, b) => (a + b) / 2))
        foreach (float y in new[] { -0.3f * width, 0, 0.3f * width })
        foreach (float z in new[] { 0.2f * height, 0.5f * height, 0.8f * height })
        {
            Vector3 p = new(x, y, z);
            voidProbes.Add(new { point_mm = new[] { p.X, p.Y, p.Z }, expected_inside = false, observed_inside = combined.bIsInside(p) });
        }
    }
    float[] expectedMin = cuts.Select(a => a[0]).ToArray(), expectedMax = cuts.Select(a => a[^1]).ToArray();
    var report = new
    {
        status = "executed_assumed_geometry_only", input_sha256 = Hash(inputPath),
        physical_plate_thickness_mm = thickness, voxel_mm = voxel, min_thickness_voxels = thickness / voxel,
        method = "Literal rectangular midplanes extruded +/-t/2 along their normal, then PicoGK union; no other corner fill, offset, scan or repair",
        panel_count = boxes.Count, panel_names = boxes.Select(b => b.Name).ToArray(),
        exact_axis_aligned_box_union_volume_mm3 = analyticVolume,
        raw_native_property_volume_mm3 = volume,
        raw_native_relative_volume_error = Math.Abs(volume - analyticVolume) / analyticVolume,
        native_volume_admitted = false,
        native_volume_status = "diagnostic_unusable: native property API disagreed with exact box union on prior thin-wall baseline; independent topology and integration checks required",
        exact_bounds_min_mm = expectedMin, exact_bounds_max_mm = expectedMax,
        voxel_bounds_min_mm = new[] { bounds.vecMin.X, bounds.vecMin.Y, bounds.vecMin.Z },
        voxel_bounds_max_mm = new[] { bounds.vecMax.X, bounds.vecMax.Y, bounds.vecMax.Z },
        triangles = mesh.nTriangleCount(), native_vdb_roundtrip_equal = true,
        observed_material_midpoint_probes = materialProbes,
        observed_tunnel_void_probes = voidProbes,
        point_probe_scope = "Finite canonical-model occupancy checks only; no continuous-clearance, vehicle-interface or physical-thickness qualification",
        managed_program_binary_sha256 = Hash(System.Reflection.Assembly.GetExecutingAssembly().Location),
        stl_sha256 = Hash(stl), vdb_sha256 = Hash(vdb), elapsed_seconds = watch.Elapsed.TotalSeconds,
        framework = System.Runtime.InteropServices.RuntimeInformation.FrameworkDescription,
        physical_wall_thickness_convergence_verified = false, source_geometry_assumed = true,
        donor_fitment_verified = false, strength_verified = false, manufacturing_authorized = false,
        native_omniverse = false
    };
    File.WriteAllText(Path.Combine(output, "report.json"), JsonSerializer.Serialize(report, new JsonSerializerOptions { WriteIndented = true }) + "\n");
    Console.WriteLine($"ASSUMED_GEOMETRY_EXPORTED panels={boxes.Count} triangles={mesh.nTriangleCount()} volume_mm3={volume}");
}
finally { Library.UnregisterGlobalLibrary(); }
