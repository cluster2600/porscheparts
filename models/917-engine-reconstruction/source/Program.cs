using System.Globalization;
using System.Security.Cryptography;
using System.Text.Json;
using PicoGK;

// An open scan becomes a numerical surface shell, never a filled engine casting.
if (args.Length != 4)
    throw new ArgumentException("Usage: ScanShell source.stl sha256 voxel_source_units new_output");
string source = Path.GetFullPath(args[0]), output = Path.GetFullPath(args[3]);
string Hash(string path)
{
    using var stream = File.OpenRead(path);
    return Convert.ToHexString(SHA256.HashData(stream)).ToLowerInvariant();
}
float voxel = float.Parse(args[2], CultureInfo.InvariantCulture);
if (!float.IsFinite(voxel) || voxel <= 0) throw new ArgumentException("Invalid voxel size");
if (Hash(source) != args[1]) throw new InvalidDataException("Input hash mismatch");
if (Directory.Exists(output) || File.Exists(output)) throw new IOException("Output already exists");
for (DirectoryInfo? parent = new(output); parent != null; parent = parent.Parent)
    if (File.Exists(Path.Combine(parent.FullName, ".git")) || Directory.Exists(Path.Combine(parent.FullName, ".git")))
    {
        if (!Path.GetRelativePath(parent.FullName, output).StartsWith("work" + Path.DirectorySeparatorChar, StringComparison.Ordinal))
            throw new IOException("Scan derivatives must stay in ignored work/");
        break;
    }
Directory.CreateDirectory(output);
if (!OperatingSystem.IsWindows()) File.SetUnixFileMode(output, UnixFileMode.UserRead | UnixFileMode.UserWrite | UnixFileMode.UserExecute);
using Library library = new(voxel);
// STL's MM convention is used for numeric transport only; physical scale is unknown.
using Mesh mesh = Mesh.mshFromStlFile(source, Mesh.EStlUnit.MM, libSet: library);
if (mesh.nTriangleCount() == 0) throw new InvalidDataException("Empty input");
using Voxels shell = Voxels.voxMeshShell(library, mesh, voxel);
shell.CalculateProperties(out float volume, out _);
if (shell.bIsEmpty() || !float.IsFinite(volume) || volume <= 0)
    throw new InvalidDataException("Empty or invalid shell");
using Mesh result = new(shell);
string stl = Path.Combine(output, "observed-surface-shell.stl");
string vdb = Path.Combine(output, "observed-surface-shell.vdb");
result.SaveToStlFile(stl, Mesh.EStlUnit.MM);
shell.SaveToVdbFile(vdb);
if (Hash(source) != args[1]) throw new InvalidDataException("Input changed during execution");
File.WriteAllText(Path.Combine(output, "receipt.json"), JsonSerializer.Serialize(new
{
    classification = "observed_surface_shell_not_functional_engine",
    runtime = new { name = Library.strName(), version = Library.strVersion(), build = Library.strBuildInfo() },
    input_sha256 = args[1], stl_sha256 = Hash(stl), vdb_sha256 = Hash(vdb),
    voxel_size_source_units = voxel, shell_half_thickness_source_units = voxel,
    voxel_shell_volume_source_units_cubed = volume, triangles = result.nTriangleCount(),
    scale_verified = false, functional_interfaces_verified = false,
    material_qualified = false, manufacturing_authorized = false
}, new JsonSerializerOptions { WriteIndented = true }) + "\n");
