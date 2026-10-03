using System.Globalization;
using System.Numerics;
using System.Security.Cryptography;
using System.Text.Json;
using PicoGK;

// Private numerical experiment: voxelisation does not establish missing surfaces or interfaces.
if (args.Length != 5 && args.Length != 6)
    throw new ArgumentException("Usage: ScanScreen prepared.obj sha256 mm_per_source_unit voxel_mm new_private_output [invert]");
bool invert = args.Length == 6 && args[5] == "invert";
if (args.Length == 6 && !invert) throw new ArgumentException("Unknown orientation option");
string source = Path.GetFullPath(args[0]), output = Path.GetFullPath(args[4]);
string Hash(string path) => Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(path))).ToLowerInvariant();
if (Hash(source) != args[1]) throw new InvalidDataException("Source hash mismatch");
float scale = float.Parse(args[2], CultureInfo.InvariantCulture);
float resolution = float.Parse(args[3], CultureInfo.InvariantCulture);
if (!float.IsFinite(scale) || scale <= 0 || !float.IsFinite(resolution) || resolution <= 0)
    throw new ArgumentException("Scale and resolution must be positive finite numbers");
if (Directory.Exists(output) || File.Exists(output)) throw new IOException("Use a new private output directory");
for (DirectoryInfo? parent = new(output); parent != null; parent = parent.Parent)
    if (File.Exists(Path.Combine(parent.FullName, ".git")) || Directory.Exists(Path.Combine(parent.FullName, ".git")))
    {
        if (!Path.GetRelativePath(parent.FullName, output).StartsWith("work" + Path.DirectorySeparatorChar, StringComparison.Ordinal))
            throw new IOException("Scan geometry must stay in ignored work/");
        break;
    }
Directory.CreateDirectory(output);
if (!OperatingSystem.IsWindows()) File.SetUnixFileMode(output, UnixFileMode.UserRead | UnixFileMode.UserWrite | UnixFileMode.UserExecute);
using Library library = new(resolution);
using Mesh mesh = new(library);
bool facesStarted = false;
foreach (string line in File.ReadLines(source))
{
    string[] f = line.Split((char[]?)null, StringSplitOptions.RemoveEmptyEntries);
    if (f.Length == 0 || f[0].StartsWith('#')) continue;
    if (f[0] == "v" && !facesStarted && f.Length == 4)
    {
        float Number(string x)
        {
            float v = float.Parse(x, CultureInfo.InvariantCulture) * scale;
            if (!float.IsFinite(v)) throw new InvalidDataException("Non-finite scaled position");
            return v;
        }
        mesh.nAddVertex(new Vector3(Number(f[1]), Number(f[2]), Number(f[3])));
    }
    else if (f[0] == "f" && f.Length == 4)
    {
        facesStarted = true;
        int[] ids = f.Skip(1).Select(x => int.Parse(x, CultureInfo.InvariantCulture) - 1).ToArray();
        if (ids.Any(x => x < 0 || x >= mesh.nVertexCount())) throw new InvalidDataException("Invalid vertex index");
        mesh.nAddTriangle(ids[0], ids[invert ? 2 : 1], ids[invert ? 1 : 2]);
    }
    else throw new InvalidDataException("Expected a prepared triangular position-only OBJ");
}
if (mesh.nTriangleCount() == 0) throw new InvalidDataException("Empty input mesh");
using Voxels voxels = new(mesh);
voxels.CalculateProperties(out float volume, out _);
if (!float.IsFinite(volume) || volume <= 0) throw new InvalidDataException("No positive voxel volume");
using Mesh result = voxels.mshAsMesh();
string file = Path.Combine(output, "conditional-geometry.stl");
result.SaveToStlFile(file);
if (Hash(source) != args[1]) throw new InvalidDataException("Source changed during calculation");
var receipt = new {
    status = "private_voxel_closure_experiment_not_functional_reconstruction",
    runtime = new { name = Library.strName(), version = Library.strVersion(), build = Library.strBuildInfo() },
    input_sha256 = args[1], output_sha256 = Hash(file),
    mm_per_source_unit_assumed = scale, voxel_size_mm_assumed = resolution, triangle_orientation_inverted = invert,
    voxel_volume_mm3_conditional = volume, output_triangles = result.nTriangleCount(),
    scale_verified = false, missing_surface_reconstruction_validated = false,
    functional_interfaces_verified = false, solver_ready = false, manufacturing_authorized = false
};
File.WriteAllText(Path.Combine(output, "receipt.json"), JsonSerializer.Serialize(receipt, new JsonSerializerOptions { WriteIndented = true }) + "\n");
if (!OperatingSystem.IsWindows())
    foreach (string path in Directory.EnumerateFiles(output)) File.SetUnixFileMode(path, UnixFileMode.UserRead | UnixFileMode.UserWrite);
Console.WriteLine(JsonSerializer.Serialize(receipt));
