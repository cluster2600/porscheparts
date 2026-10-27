using System.Numerics;
using System.Security.Cryptography;
using System.Text.Json;
using PicoGK;
using PicoGKCatalog;

if (args.Length != 4) throw new ArgumentException("Usage: RADIAL_WINDOW_JSON ROTOR_STL DRIVE_STL NEW_PRIVATE_OUTPUT");
string reportPath = Path.GetFullPath(args[0]), rotorPath = Path.GetFullPath(args[1]);
string drivePath = Path.GetFullPath(args[2]), output = Path.GetFullPath(args[3]);
string Hash(string path) { using var stream = File.OpenRead(path); return Convert.ToHexString(SHA256.HashData(stream)).ToLowerInvariant(); }
const string reportHash = "05d52829fa35394fa017ae3ae9c5aae98f8d36468e52d17ba3b71db1517a2b36";
const string rotorHash = "5522ec1af957a4523244bc2b2f05ff902b52eb882e1cb3b2ef88b093ffb598eb";
const string driveHash = "fbae73f9c7182eebe5d0da5d4af991c42e06a59edd145d85f3221c128e7cef35";
if (Hash(reportPath) != reportHash || Hash(rotorPath) != rotorHash || Hash(drivePath) != driveHash)
    throw new InvalidDataException("Pinned 935 input changed");
if (Directory.Exists(output) || File.Exists(output)) throw new IOException("Use a new output directory");
bool privateOutput = false;
for (DirectoryInfo parent = new(output); parent != null; parent = parent.Parent)
{
    if (parent.LinkTarget != null) throw new IOException("Output ancestry must not contain symlinks");
    if (File.Exists(Path.Combine(parent.FullName, ".git")) || Directory.Exists(Path.Combine(parent.FullName, ".git")))
    {
        privateOutput = Path.GetRelativePath(parent.FullName, output).StartsWith("work" + Path.DirectorySeparatorChar);
        break;
    }
}
if (!privateOutput) throw new IOException("Private geometry must remain under ignored repository work/");
using JsonDocument document = JsonDocument.Parse(File.ReadAllText(reportPath));
JsonElement report = document.RootElement;
if (report.GetProperty("status").GetString() != "partial_arc_radial_window_screen_only" ||
    report.GetProperty("source_unit_to_mm_verified").GetBoolean() ||
    report.GetProperty("full_drive_circumference_observed").GetBoolean() ||
    report.GetProperty("torque_transfer_defined").GetBoolean() ||
    report.GetProperty("bands").GetArrayLength() != 4)
    throw new InvalidDataException("Only the unresolved four-band interface screen is accepted");

// All coordinates below are provisional millimetres at 1 mm per source unit.
// Radial margins deliberately leave the ring detached from both observed meshes.
const float innerRadius = 7.9f, outerRadius = 11.1f, zMin = -20f, zMax = 0f, voxel = 0.15f;
float screenedGap = report.GetProperty("min_screened_gap_source_units").GetSingle();
if (screenedGap < outerRadius - innerRadius || innerRadius >= outerRadius)
    throw new InvalidDataException("Chosen visual envelope exceeds the screened radial window");
Directory.CreateDirectory(output);
if (!OperatingSystem.IsWindows()) File.SetUnixFileMode(output, UnixFileMode.UserRead | UnixFileMode.UserWrite | UnixFileMode.UserExecute);
using Library library = new(voxel);
using Voxels space = Sdf.Vox(library,
    p => MathF.Max(Sdf.CylZ(p, 0, 0, outerRadius, zMin, zMax),
                   -Sdf.CylZ(p, 0, 0, innerRadius, zMin - 1, zMax + 1)),
    new Vector3(-outerRadius - 1, -outerRadius - 1, zMin - 1),
    new Vector3(outerRadius + 1, outerRadius + 1, zMax + 1));
space.CalculateProperties(out float volume, out _);
using Mesh ring = space.mshAsMesh();
if (!float.IsFinite(volume) || volume <= 0 || ring.nTriangleCount() == 0)
    throw new InvalidDataException("PicoGK did not produce a positive nonempty envelope");
string meshPath = Path.Combine(output, "hub-space-hypothesis.stl");
ring.SaveToStlFile(meshPath);
File.WriteAllText(Path.Combine(output, "receipt.json"), JsonSerializer.Serialize(new {
    status = "visual_hub_space_hypothesis_not_a_coupling",
    target = "935", report_sha256 = reportHash, rotor_sha256 = rotorHash, drive_sha256 = driveHash,
    mesh_sha256 = Hash(meshPath), triangles = ring.nTriangleCount(),
    assumed_mm_per_source_unit = 1.0f,
    inner_radius_mm_hypothesis = innerRadius, outer_radius_mm_hypothesis = outerRadius,
    axial_span_mm_hypothesis = new[] { zMin, zMax }, voxel_mm_hypothesis = voxel,
    native_volume_mm3_hypothesis = volume,
    full_drive_circumference_observed = false, scale_verified = false,
    fit_verified = false, torque_transfer_defined = false, axial_retention_defined = false,
    functional_component = false, manufacturing_authorized = false,
    runtime = new { name = Library.strName(), version = Library.strVersion(), build = Library.strBuildInfo() }
}, new JsonSerializerOptions { WriteIndented = true }) + "\n");
Console.WriteLine($"PicoGK hub-space visual hypothesis: {ring.nTriangleCount()} triangles, {volume:F3} provisional mm^3");
