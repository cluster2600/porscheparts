using System.Numerics;
using System.Security.Cryptography;
using System.Text.Json;
using PicoGK;
using PicoGKCatalog;

if (args.Length != 3) throw new ArgumentException("Usage: PINNED_LOWER_FLANGE_JSON SHA256 NEW_PRIVATE_OUTPUT");
string source = Path.GetFullPath(args[0]), output = Path.GetFullPath(args[2]);
string Hash(string path) { using var stream = File.OpenRead(path); return Convert.ToHexString(SHA256.HashData(stream)).ToLowerInvariant(); }
if (Hash(source) != args[1]) throw new InvalidDataException("Pinned lower-flange report changed");
if (Directory.Exists(output) || File.Exists(output)) throw new IOException("Fresh output directory required");
bool privateOutput = false;
for (DirectoryInfo parent = new(output); parent != null; parent = parent.Parent)
{
    if (parent.LinkTarget != null) throw new IOException("Output ancestry must not contain symlinks");
    if (File.Exists(Path.Combine(parent.FullName, ".git")) || Directory.Exists(Path.Combine(parent.FullName, ".git")))
    { privateOutput = Path.GetRelativePath(parent.FullName, output).StartsWith("work" + Path.DirectorySeparatorChar); break; }
}
if (!privateOutput) throw new IOException("Derived geometry must stay in ignored repository work/");
using var document = JsonDocument.Parse(File.ReadAllText(source));
JsonElement report = document.RootElement;
if (report.GetProperty("status").GetString() != "eight_lower_flange_opening_candidates_only" ||
    report.GetProperty("drive_stl_sha256").GetString() != "fbae73f9c7182eebe5d0da5d4af991c42e06a59edd145d85f3221c128e7cef35" ||
    report.GetProperty("source_unit_to_mm_verified").GetBoolean() || report.GetProperty("mounting_role_verified").GetBoolean() ||
    report.GetProperty("through_holes_verified").GetBoolean() || report.GetProperty("manufacturing_authorized").GetBoolean())
    throw new InvalidDataException("Only the unqualified pinned 935 drive pattern is accepted");
float Number(JsonElement value, float min, float max)
{
    float f = value.GetSingle();
    if (!float.IsFinite(f) || f < min || f > max) throw new InvalidDataException("Finite bounded source coordinate required");
    return f;
}
var openings = report.GetProperty("openings").EnumerateArray().ToArray();
if (openings.Length != 8) throw new InvalidDataException("Exactly eight acquired opening candidates required");
const float voxel = .25f, halfThickness = .4f, z0 = -190f, z1 = -170f;
var shapes = new List<(Vector2 lower, float lowerR, Vector2 upper, float upperR)>();
foreach (JsonElement opening in openings)
{
    var fits = opening.GetProperty("fits").EnumerateArray().ToArray();
    if (fits.Length != 2) throw new InvalidDataException("Two axial bands required");
    Vector2[] centres = new Vector2[2]; float[] radii = new float[2];
    for (int i = 0; i < 2; i++)
    {
        float[] band = fits[i].GetProperty("z_band_source_units").EnumerateArray().Select(v => Number(v, -200, -150)).ToArray();
        if (band.Length != 2 || band[0] != (i == 0 ? -190f : -180f) || band[1] != (i == 0 ? -180f : -170f))
            throw new InvalidDataException("Unexpected axial band");
        float[] xy = fits[i].GetProperty("fit_centre_xy_source_units").EnumerateArray().Select(v => Number(v, -100, 250)).ToArray();
        if (xy.Length != 2) throw new InvalidDataException("XY centre required");
        centres[i] = new(xy[0], xy[1]);
        radii[i] = Number(fits[i].GetProperty("fit_radius_source_units"), 2, 4);
        if (fits[i].GetProperty("sidewall_face_centroids").GetInt32() < 200 ||
            Number(fits[i].GetProperty("angular_coverage_deg"), 180, 360) < 200)
            throw new InvalidDataException("Insufficient acquired sidewall coverage");
    }
    if (Vector2.Distance(centres[0], centres[1]) > 1 || MathF.Abs(radii[0] - radii[1]) > .5f)
        throw new InvalidDataException("Axial fit discontinuity");
    shapes.Add((centres[0], radii[0], centres[1], radii[1]));
}
Directory.CreateDirectory(output);
if (!OperatingSystem.IsWindows()) File.SetUnixFileMode(output, UnixFileMode.UserRead | UnixFileMode.UserWrite | UnixFileMode.UserExecute);
File.Copy(source, Path.Combine(output, "lower-flange-input.json"));
using Library library = new(voxel);
using Mesh assembled = new(library);
var rows = new List<object>();
for (int i = 0; i < shapes.Count; i++)
{
    var shape = shapes[i];
    float extent = MathF.Max(shape.lowerR, shape.upperR) + halfThickness + 1.5f;
    Vector2 min = Vector2.Min(shape.lower, shape.upper) - new Vector2(extent);
    Vector2 max = Vector2.Max(shape.lower, shape.upper) + new Vector2(extent);
    using Voxels witness = Sdf.Vox(library, p =>
    {
        float t = Math.Clamp((p.Z + 185f) / 10f, 0, 1);
        Vector2 centre = Vector2.Lerp(shape.lower, shape.upper, t);
        float radius = shape.lowerR + (shape.upperR - shape.lowerR) * t;
        return MathF.Max(Sdf.CylZ(p, centre.X, centre.Y, radius + halfThickness, z0, z1),
                        -Sdf.CylZ(p, centre.X, centre.Y, radius - halfThickness, z0 - 1, z1 + 1));
    }, new Vector3(min.X, min.Y, z0 - 2), new Vector3(max.X, max.Y, z1 + 2));
    using Mesh mesh = witness.mshAsMesh();
    if (mesh.nTriangleCount() < 100 || mesh.nTriangleCount() > 1000000)
        throw new InvalidDataException("Unexpected witness mesh size");
    string name = $"opening_{i:D2}.stl", path = Path.Combine(output, name);
    mesh.SaveToStlFile(path); assembled.Append(mesh);
    rows.Add(new { id = i, file = name, sha256 = Hash(path), triangles = mesh.nTriangleCount(),
                   lower_centre_source_units = new[] { shape.lower.X, shape.lower.Y }, lower_radius_source_units = shape.lowerR,
                   upper_centre_source_units = new[] { shape.upper.X, shape.upper.Y }, upper_radius_source_units = shape.upperR });
}
string combined = Path.Combine(output, "opening-witnesses.stl");
assembled.SaveToStlFile(combined);
if (Hash(source) != args[1]) throw new InvalidDataException("Report changed during PicoGK construction");
File.WriteAllText(Path.Combine(output, "receipt.json"), JsonSerializer.Serialize(new {
    status = "PicoGK_scan_feature_witness_only", target = "935", report_sha256 = args[1],
    drive_stl_sha256 = report.GetProperty("drive_stl_sha256").GetString(),
    classification = "analytic_wall_location_witness_not_mounting_material",
    source_coordinate_unit = "uncalibrated_scan_unit", PicoGK_unit_assumption = "1_source_unit_as_1_mm_for_runtime_only",
    voxel_source_units_assumed_mm = voxel, witness_radial_half_thickness_source_units = halfThickness,
    axial_span_source_units = new[] { z0, z1 }, openings = rows,
    combined_file = "opening-witnesses.stl", combined_sha256 = Hash(combined), combined_triangles = assembled.nTriangleCount(),
    runtime = new { name = Library.strName(), version = Library.strVersion(), build = Library.strBuildInfo() },
    source_unit_to_mm_verified = false, mating_face_verified = false, through_holes_verified = false,
    interface_verified = false, manufacturing_authorized = false, physical_validation = false
}, new JsonSerializerOptions { WriteIndented = true }) + "\n");
Console.WriteLine($"PicoGK eight-opening witness: {assembled.nTriangleCount()} triangles; output {output}");
