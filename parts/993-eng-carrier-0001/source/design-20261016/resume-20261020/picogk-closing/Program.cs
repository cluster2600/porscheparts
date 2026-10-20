using System.Numerics;
using System.Security.Cryptography;
using System.Text.Json;
using PicoGK;

// Trusted owner-authored morphological-closing study; no generated code execution.
if (args.Length != 5) throw new ArgumentException("MODE INPUT_STL OUTPUT VOXEL_MM ROUNDING_MM");
string mode = args[0];
string input = Path.GetFullPath(args[1]);
string output = Path.GetFullPath(args[2]);
float voxel = float.Parse(args[3], System.Globalization.CultureInfo.InvariantCulture);
float rounding = float.Parse(args[4], System.Globalization.CultureInfo.InvariantCulture);
if ((mode != "control" && mode != "carrier") || voxel < 0.1f || voxel > 0.2f || rounding < 0.6f || rounding > 2f)
    throw new ArgumentException("Declared study bounds differ");
Directory.CreateDirectory(output);
if (Directory.EnumerateFileSystemEntries(output).Any()) throw new ArgumentException("Fresh output required");
void Phase(string phase) {
    File.WriteAllText(Path.Combine(output, "progress.json"), JsonSerializer.Serialize(new { phase, voxel_mm = voxel, rounding_mm = rounding }));
    Console.WriteLine(phase);
}
Phase("initializing");
using Library lib = new(voxel);
Library.RegisterGlobalLibrary(lib);
try {
    using Mesh sourceMesh = mode == "carrier"
        ? Mesh.mshFromStlFile(input, Mesh.EStlUnit.MM, libSet: lib)
        : Utils.mshCreateCube(new BBox3(new Vector3(0,0,0), new Vector3(10,5,10)));
    using Voxels first = new(sourceMesh);
    using Mesh secondMesh = Utils.mshCreateCube(new BBox3(new Vector3(0,5,0), new Vector3(5,10,10)));
    using Voxels second = new(secondMesh);
    using Voxels original = mode == "control" ? first + second : first.voxDuplicate();
    original.CalculateProperties(out float originalVolume, out BBox3 originalBox);
    Phase("morphological_closing");
    using Voxels closed = original.voxFillet(rounding);
    closed.CalculateProperties(out float closedVolume, out BBox3 closedBox);
    Vector3 addedPoint = new(5.15f,5.15f,5f);
    bool control = mode != "control" || (!original.bIsInside(addedPoint) && closed.bIsInside(addedPoint)
        && closed.bIsInside(new Vector3(2,2,5)) && !closed.bIsInside(new Vector3(8,8,5)) && closedVolume > originalVolume);
    Phase("exporting");
    using Mesh mesh = new(closed);
    string stl = Path.Combine(output, "closed-study.stl");
    mesh.SaveToStlFile(stl, Mesh.EStlUnit.MM);
    var report = new {
        status = control ? "morphological_closing_experiment_completed" : "analytic_membership_control_refused",
        mode, voxel_mm = voxel, rounding_mm = rounding,
        operation = "PicoGK voxFillet: offset +R then -R; voxel approximation of morphological closing",
        original_voxel_volume_mm3 = originalVolume, closed_voxel_volume_mm3 = closedVolume,
        approximate_closed_mass_kg = closedVolume * 4.42e-6,
        output_triangles = mesh.nTriangleCount(), native_voxel_memory_bytes = closed.nMemUsage(),
        finite_control_probes_passed = control,
        input_SHA256 = mode == "carrier" ? Convert.ToHexStringLower(SHA256.HashData(File.ReadAllBytes(input))) : null,
        output_SHA256 = Convert.ToHexStringLower(SHA256.HashData(File.ReadAllBytes(stl))),
        library_version = typeof(Library).Assembly.GetName().Version?.ToString(),
        source_interfaces_unchanged = false, geometry_adopted = false,
        pending = new[]{"complete mesh audit", "protected interfaces and original material retention", "mechanical cases and refinement", "complete print preparation"}
    };
    File.WriteAllText(Path.Combine(output, "assessment.json"), JsonSerializer.Serialize(report, new JsonSerializerOptions { WriteIndented = true }));
    Console.WriteLine(JsonSerializer.Serialize(report));
    if (!control) Environment.ExitCode = 2;
}
finally { Library.UnregisterGlobalLibrary(); }
