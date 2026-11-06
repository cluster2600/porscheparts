using System.Numerics;
using System.Security.Cryptography;
using System.Text.Json;
using PicoGK;
using PicoGKCatalog;

// This is a visual study in an invented stage frame. None of these shapes is a
// measured Porsche component, vehicle interface, or manufacturing candidate.
if (args.Length != 2)
    throw new ArgumentException("Usage: DashboardVisualScene scene.json NEW_OUTPUT_UNDER_REPO_WORK");

string scenePath = Path.GetFullPath(args[0]);
string output = Path.GetFullPath(args[1]);
string repoRoot = Path.GetFullPath(Path.Combine(Path.GetDirectoryName(scenePath)!, "../../.."));
string generatorPath = Path.Combine(Path.GetDirectoryName(scenePath)!, "Program.cs");
string outputRelative = Path.GetRelativePath(repoRoot, output);
if (!outputRelative.StartsWith("work" + Path.DirectorySeparatorChar, StringComparison.Ordinal) ||
    Directory.Exists(output) || File.Exists(output))
    throw new IOException("Use a new private output directory under repository work/");

string Hash(string path)
{
    using var stream = File.OpenRead(path);
    return Convert.ToHexString(SHA256.HashData(stream)).ToLowerInvariant();
}

float Number(JsonElement value)
{
    float result = value.GetSingle();
    if (!float.IsFinite(result)) throw new InvalidDataException("Finite scene numbers required");
    return result;
}

Vector3 Vec3(JsonElement value)
{
    float[] a = value.EnumerateArray().Select(Number).ToArray();
    if (a.Length != 3) throw new InvalidDataException("Three coordinates required");
    return new Vector3(a[0], a[1], a[2]);
}

float CylinderY(Vector3 p, Vector3 c, float radius, float halfDepth)
{
    float dr = new Vector2(p.X - c.X, p.Z - c.Z).Length() - radius;
    float dy = MathF.Abs(p.Y - c.Y) - halfDepth;
    return MathF.Min(MathF.Max(dr, dy), 0f) + new Vector2(MathF.Max(dr, 0f), MathF.Max(dy, 0f)).Length();
}

float RoundRectY(Vector3 p, Vector3 c, Vector3 half, float radius)
{
    Vector2 q = Vector2.Abs(new Vector2(p.X - c.X, p.Z - c.Z)) - new Vector2(half.X - radius, half.Z - radius);
    float dxz = Vector2.Max(q, Vector2.Zero).Length() + MathF.Min(MathF.Max(q.X, q.Y), 0f) - radius;
    float dy = MathF.Abs(p.Y - c.Y) - half.Y;
    return MathF.Min(MathF.Max(dxz, dy), 0f) + new Vector2(MathF.Max(dxz, 0f), MathF.Max(dy, 0f)).Length();
}

float Distance(string kind, Vector3 p, Vector3 centre, Vector3 half, float radius, float border) => kind switch
{
    "round_box" => RoundRectY(p, centre, half, radius),
    "frame_y" => MathF.Max(RoundRectY(p, centre, half, radius),
        -RoundRectY(p, centre, new Vector3(half.X - border, half.Y + 3f, half.Z - border), MathF.Max(0.5f, radius - border))),
    "disk_y" => CylinderY(p, centre, radius, half.Y),
    "annulus_y" => MathF.Max(CylinderY(p, centre, radius, half.Y),
        -CylinderY(p, centre, radius - border, half.Y + 3f)),
    _ => throw new InvalidDataException($"Unsupported visual element kind: {kind}")
};

using var scene = JsonDocument.Parse(File.ReadAllText(scenePath));
JsonElement root = scene.RootElement;
if (root.GetProperty("schema_version").GetString() != "1.0" ||
    root.GetProperty("status").GetString() != "visual_concept_only" ||
    root.GetProperty("coordinate_frame").GetString() != "visual_stage_not_vehicle" ||
    root.GetProperty("unit").GetString() != "mm_render_scale_only")
    throw new InvalidDataException("Scene must declare its unverified visual-only frame");
float voxel = Number(root.GetProperty("voxel_mm"));
if (voxel < 1.5f || voxel > 4f) throw new InvalidDataException("Bounded visual voxel size required");
JsonElement scenario = root.GetProperty("target_scenario");
if (scenario.GetProperty("market").GetString() != "M564" || scenario.GetProperty("drive").GetString() != "LHD" ||
    scenario.GetProperty("part_number").ValueKind != JsonValueKind.Null || scenario.GetProperty("verification").GetString() != "unresolved")
    throw new InvalidDataException("Unresolved M564 LHD scenario required");

JsonElement trim = root.GetProperty("tracked_trim");
string trimRelative = trim.GetProperty("path_from_repo").GetString()!;
string trimPath = Path.GetFullPath(Path.Combine(repoRoot, trimRelative));
string generatorHash = Hash(generatorPath);
if (!trimPath.StartsWith(repoRoot + Path.DirectorySeparatorChar, StringComparison.Ordinal) ||
    Hash(trimPath) != trim.GetProperty("sha256").GetString())
    throw new InvalidDataException("Tracked trim source hash or path mismatch");

JsonElement[] layers = root.GetProperty("layers").EnumerateArray().ToArray();
string[] requiredFamilies = [
    "DASHBOARD_TRIM", "INSTRUMENT_HOOD", "INSTRUMENT_CLUSTER", "INSTRUMENT_GAUGE_MARKS", "CENTER_AIR_VENTS",
    "SIDE_AIR_VENTS", "DEFROST_OUTLETS_AND_DUCTS", "GLOVEBOX", "CENTER_CONSOLE",
    "HVAC_RADIO_CONTROLS", "SWITCHES_AND_BLANKS", "KNEE_STRIP_RESERVED"
];
if (layers.Length != requiredFamilies.Length ||
    !layers.Select(l => l.GetProperty("family_id").GetString()).OrderBy(x => x)
        .SequenceEqual(requiredFamilies.OrderBy(x => x)))
    throw new InvalidDataException("Complete expected visible-layer inventory required");

// Inspect all descriptors before creating output. These numbers are assumptions,
// and the scene's bounded domain is only an aid to rendering.
int trackedTrimCount = 0;
var elementIds = new HashSet<string>(StringComparer.Ordinal);
foreach (JsonElement layer in layers)
{
    if (layer.GetProperty("colour").GetString() is not string colour ||
        colour.Length != 7 || colour[0] != '#' || !colour.Skip(1).All(Uri.IsHexDigit))
        throw new InvalidDataException("Hex layer colour required");
    JsonElement[] elements = layer.GetProperty("elements").EnumerateArray().ToArray();
    if (elements.Length == 0 || elements.Length > 24) throw new InvalidDataException("Bounded nonempty visual layer required");
    foreach (JsonElement e in elements)
    {
        string id = e.GetProperty("id").GetString()!;
        string kind = e.GetProperty("kind").GetString()!;
        if (!elementIds.Add(id) || e.GetProperty("basis").GetString() != "artistic_assumption" ||
            id.Contains("airbag", StringComparison.OrdinalIgnoreCase) ||
            id.Contains("mount", StringComparison.OrdinalIgnoreCase) ||
            id.Contains("fastener", StringComparison.OrdinalIgnoreCase) ||
            id.Contains("steering", StringComparison.OrdinalIgnoreCase))
            throw new InvalidDataException("Unique assumed nonfunctional visual elements required");
        Vector3 c = Vec3(e.GetProperty("centre"));
        Vector3 h = Vec3(e.GetProperty("half"));
        float r = Number(e.GetProperty("radius"));
        float b = Number(e.GetProperty("border"));
        if (Vector3.Abs(c).X > 2000 || Vector3.Abs(c).Y > 2000 || Vector3.Abs(c).Z > 2000 ||
            h.X <= 0 || h.Y <= 0 || h.Z <= 0 || h.X > 1000 || h.Y > 200 || h.Z > 300 ||
            r < 0 || b < 0)
            throw new InvalidDataException("Bounded assumed scene elements required");
        if (kind == "tracked_trim")
        {
            if (layer.GetProperty("family_id").GetString() != "DASHBOARD_TRIM" || ++trackedTrimCount > 1)
                throw new InvalidDataException("Exactly one tracked upper pad import required");
        }
        else if (kind == "round_box")
        {
            if (r >= MathF.Min(h.X, h.Z))
                throw new InvalidDataException("Invalid rounded panel");
        }
        else if (kind == "frame_y")
        {
            if (r >= MathF.Min(h.X, h.Z) || b <= 0 || b >= MathF.Min(h.X, h.Z) || r - b < 0.5f)
                throw new InvalidDataException("Invalid visual outline");
        }
        else if (kind is "disk_y" or "annulus_y")
        {
            if (r <= 0 || r > MathF.Min(h.X, h.Z) ||
                (kind == "annulus_y" && (b <= 0 || b >= r)))
                throw new InvalidDataException("Invalid gauge or vent ring");
        }
        else throw new InvalidDataException("Unknown visual element kind");
    }
}
if (trackedTrimCount != 1) throw new InvalidDataException("Tracked upper pad import required");

Directory.CreateDirectory(output);
if (!OperatingSystem.IsWindows())
    File.SetUnixFileMode(output, UnixFileMode.UserRead | UnixFileMode.UserWrite | UnixFileMode.UserExecute);
File.Copy(scenePath, Path.Combine(output, "scene.json"));
using Library library = new(voxel);
var records = new List<object>();
foreach (JsonElement layer in layers)
{
    string family = layer.GetProperty("family_id").GetString()!;
    using Mesh layerMesh = new(library);
    foreach (JsonElement e in layer.GetProperty("elements").EnumerateArray())
    {
        string kind = e.GetProperty("kind").GetString()!;
        Vector3 centre = Vec3(e.GetProperty("centre"));
        if (kind == "tracked_trim")
        {
            using Mesh imported = Mesh.mshFromStlFile(trimPath, Mesh.EStlUnit.MM, vecPostOffsetMM: centre, libSet: library);
            if (imported.nTriangleCount() < 1000) throw new InvalidDataException("Tracked trim mesh unexpectedly empty");
            layerMesh.Append(imported);
            continue;
        }
        Vector3 half = Vec3(e.GetProperty("half"));
        float radius = Number(e.GetProperty("radius"));
        float border = Number(e.GetProperty("border"));
        Vector3 padding = new(3f * voxel);
        using Voxels voxels = Sdf.Vox(library,
            p => Distance(kind, p, centre, half, radius, border),
            centre - half - padding, centre + half + padding);
        using Mesh primitive = voxels.mshAsMesh();
        if (primitive.nTriangleCount() == 0) throw new InvalidDataException($"Visual element empty: {e.GetProperty("id").GetString()}");
        layerMesh.Append(primitive);
    }
    if (layerMesh.nTriangleCount() == 0) throw new InvalidDataException($"Visual layer empty: {family}");
    string file = family + ".stl";
    string path = Path.Combine(output, file);
    layerMesh.SaveToStlFile(path);
    records.Add(new { family_id = family, file, sha256 = Hash(path), triangles = layerMesh.nTriangleCount(),
        colour = layer.GetProperty("colour").GetString() });
    Console.WriteLine($"{family}: {layerMesh.nTriangleCount()} triangles");
}
if (Hash(trimPath) != trim.GetProperty("sha256").GetString() ||
    Hash(scenePath) != Hash(Path.Combine(output, "scene.json")) ||
    Hash(generatorPath) != generatorHash)
    throw new InvalidDataException("Source changed during render");
File.WriteAllText(Path.Combine(output, "scene-report.json"), JsonSerializer.Serialize(new {
    scene_id = root.GetProperty("scene_id").GetString(), status = "visual_concept_only",
    coordinate_frame = "visual_stage_not_vehicle", unit = "mm_render_scale_only", layers = records,
    scene_sha256 = Hash(scenePath), generator_source_sha256 = generatorHash,
    tracked_trim_sha256 = Hash(trimPath), voxel_mm = voxel,
    runtime = new { name = Library.strName(), version = Library.strVersion(), build = Library.strBuildInfo() },
    input_measurements_available = false, fit_verified = false, dimensions_verified = false,
    manufacturing_authorized = false, physical_validation = false
}, new JsonSerializerOptions { WriteIndented = true }) + "\n");
Console.WriteLine($"PicoGK visual dashboard scene: {records.Count} separate layers; report at {output}");
