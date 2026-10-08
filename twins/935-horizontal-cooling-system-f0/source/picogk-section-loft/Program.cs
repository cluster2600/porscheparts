using System.Globalization;
using System.Numerics;
using System.Security.Cryptography;
using System.Text.Json;
using PicoGK;

// Loft measured blade sections. End caps are artificial crop boundaries, not recovered roots/tips.
if (args.Length != 5) throw new ArgumentException("Usage: sections.json sha256 assumed_mm_per_source_unit voxel_mm NEW_PRIVATE_OUTPUT");
string source = Path.GetFullPath(args[0]), output = Path.GetFullPath(args[4]);
string Hash(string p) => Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(p))).ToLowerInvariant();
if (Hash(source) != args[1]) throw new InvalidDataException("Section hash mismatch");
float scale = float.Parse(args[2], CultureInfo.InvariantCulture), voxel = float.Parse(args[3], CultureInfo.InvariantCulture);
if (!float.IsFinite(scale) || scale <= 0 || !float.IsFinite(voxel) || voxel <= 0) throw new ArgumentException("Positive finite scale/resolution required");
if (Directory.Exists(output) || File.Exists(output)) throw new IOException("Output must be new");
for (DirectoryInfo? parent = new(output); parent != null; parent = parent.Parent)
    if (File.Exists(Path.Combine(parent.FullName, ".git")) || Directory.Exists(Path.Combine(parent.FullName, ".git")))
    {
        if (!Path.GetRelativePath(parent.FullName, output).StartsWith("work" + Path.DirectorySeparatorChar))
            throw new IOException("Scan derivatives must stay in ignored work/");
        break;
    }
using var document = JsonDocument.Parse(File.ReadAllText(source));
var root = document.RootElement;
if (root.GetProperty("schema").GetString() != "935-observed-section-loft-v1") throw new InvalidDataException("Unknown section schema");
using Library library = new(voxel);
using Mesh mesh = new(library);
var vertices = new List<Vector3>(); var faces = new List<(int, int, int)>();
foreach (var blade in root.GetProperty("regions").EnumerateArray())
{
    float phase = (float)blade.GetProperty("phase_radians").GetDouble();
    Vector3 tangent = new(-MathF.Sin(phase), MathF.Cos(phase), 0);
    var rows = blade.GetProperty("profiles").EnumerateArray().Select(row => row.EnumerateArray().Select(point =>
    {
        float[] p = point.EnumerateArray().Select(x => (float)x.GetDouble() * scale).ToArray();
        if (p.Length != 3 || p.Any(x => !float.IsFinite(x))) throw new InvalidDataException("Invalid section position");
        return new Vector3(p[0], p[1], p[2]);
    }).ToArray()).ToArray();
    if (rows.Length < 3 || rows[0].Length < 8 || rows.Any(row => row.Length != rows[0].Length)) throw new InvalidDataException("Inconsistent loft grid");
    int n = rows[0].Length, start = vertices.Count, faceStart = faces.Count;
    vertices.AddRange(rows.SelectMany(x => x));
    for (int r = 0; r < rows.Length - 1; r++)
        for (int i = 0; i < n; i++)
        {
            int a = start + r * n + i, b = start + r * n + (i + 1) % n;
            faces.Add((a, b, b + n)); faces.Add((a, b + n, a + n));
        }
    foreach (bool last in new[] { false, true })
    {
        int r = last ? rows.Length - 1 : 0;
        Vector2[] polygon = rows[r].Select(p => new Vector2(Vector3.Dot(p, tangent), p.Z)).ToArray();
        foreach (var (a, b, c) in Triangulate(polygon))
        {
            int offset = start + r * n;
            faces.Add(last ? (offset + a, offset + b, offset + c) : (offset + a, offset + c, offset + b));
        }
    }
    double signed = faces.Skip(faceStart).Sum(f => (double)Vector3.Dot(vertices[f.Item1], Vector3.Cross(vertices[f.Item2], vertices[f.Item3])) / 6);
    if (signed == 0 || !double.IsFinite(signed)) throw new InvalidDataException("Degenerate blade loft");
    if (signed < 0) for (int i = faceStart; i < faces.Count; i++) { var (a,b,c) = faces[i]; faces[i] = (a,c,b); }
}
if (vertices.Count == 0) throw new InvalidDataException("No reconstructed blade regions");
foreach (Vector3 p in vertices) mesh.nAddVertex(p);
foreach (var (a,b,c) in faces)
{
    if (Vector3.Cross(vertices[b] - vertices[a], vertices[c] - vertices[a]).LengthSquared() == 0) throw new InvalidDataException("Degenerate loft face");
    mesh.nAddTriangle(a,b,c);
}
Directory.CreateDirectory(output);
if (!OperatingSystem.IsWindows()) File.SetUnixFileMode(output, UnixFileMode.UserRead | UnixFileMode.UserWrite | UnixFileMode.UserExecute);
mesh.SaveToStlFile(Path.Combine(output, "section-lofts.stl"));
using Voxels field = new(mesh);
field.CalculateProperties(out float volume, out _);
if (!float.IsFinite(volume) || volume <= 0) throw new InvalidDataException("Nonpositive voxel volume");
using Mesh voxels = field.mshAsMesh();
string stl = Path.Combine(output, "voxel-blade-regions.stl"); voxels.SaveToStlFile(stl);
if (Hash(source) != args[1]) throw new InvalidDataException("Section input changed during reconstruction");
var receipt = new {
    status = "partial_observed_blade_lofts_with_artificial_crop_caps",
    sections_sha256 = args[1], source_sha256 = root.GetProperty("source_sha256").GetString(),
    assumed_mm_per_source_unit = scale, voxel_size_mm_conditional = voxel, voxel_volume_mm3_conditional = volume,
    observed_blade_count = root.GetProperty("blades").GetArrayLength(), blade_regions = root.GetProperty("regions").GetArrayLength(), mesh_triangles = mesh.nTriangleCount(), voxel_triangles = voxels.nTriangleCount(),
    output_sha256 = Hash(stl), section_lofts_sha256 = Hash(Path.Combine(output, "section-lofts.stl")),
    runtime = new { name = Library.strName(), version = Library.strVersion(), build = Library.strBuildInfo() },
    end_caps = "artificial_crop_surfaces", root_tip_and_hub_reconstructed = false, scale_verified = false,
    complete_rotor_reconstructed = false, solver_ready = false, manufacturing_authorized = false
};
File.WriteAllText(Path.Combine(output, "receipt.json"), JsonSerializer.Serialize(receipt, new JsonSerializerOptions { WriteIndented = true }) + "\n");
if (!OperatingSystem.IsWindows()) foreach (string p in Directory.EnumerateFiles(output)) File.SetUnixFileMode(p, UnixFileMode.UserRead | UnixFileMode.UserWrite);
Console.WriteLine($"PicoGK section loft saved: {mesh.nTriangleCount()} triangles; conditional voxel volume {volume:R}; incomplete rotor");

static IEnumerable<(int,int,int)> Triangulate(Vector2[] p)
{
    float Cross(Vector2 a, Vector2 b, Vector2 c) => (b.X-a.X)*(c.Y-a.Y)-(b.Y-a.Y)*(c.X-a.X);
    var ids = Enumerable.Range(0, p.Length).ToList();
    if (p.Select((q,i) => q.X*p[(i+1)%p.Length].Y-q.Y*p[(i+1)%p.Length].X).Sum() < 0) ids.Reverse();
    while (ids.Count > 3)
    {
        bool clipped = false;
        for (int i = 0; i < ids.Count; i++)
        {
            int a = ids[(i+ids.Count-1)%ids.Count], b=ids[i], c=ids[(i+1)%ids.Count];
            if (Cross(p[a],p[b],p[c]) <= 1e-8f) continue;
            if (ids.Any(j => j!=a && j!=b && j!=c && Cross(p[a],p[b],p[j])>=-1e-8f && Cross(p[b],p[c],p[j])>=-1e-8f && Cross(p[c],p[a],p[j])>=-1e-8f)) continue;
            yield return (a,b,c); ids.RemoveAt(i); clipped = true; break;
        }
        if (!clipped) throw new InvalidDataException("Crop contour self-intersects or cannot be triangulated");
    }
    yield return (ids[0],ids[1],ids[2]);
}
