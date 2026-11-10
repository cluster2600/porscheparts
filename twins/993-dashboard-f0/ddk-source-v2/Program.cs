using System.Numerics;
using System.Security.Cryptography;
using System.Text.Json;
using PicoGK;

// Original display geometry. Every number is an artistic assumption: no scan,
// vehicle transform, fastening pattern or functional surface is represented.
if (args.Length != 2)
    throw new ArgumentException("Usage: DashboardDdkStudy scene.json NEW_OUTPUT_UNDER_REPO_WORK");
string scenePath = Path.GetFullPath(args[0]);
string sourceDir = Path.GetDirectoryName(scenePath)!;
string repoRoot = Path.GetFullPath(Path.Combine(sourceDir, "../../.."));
string output = Path.GetFullPath(args[1]);
if (!Path.GetRelativePath(repoRoot, output).StartsWith("work" + Path.DirectorySeparatorChar, StringComparison.Ordinal) ||
    Directory.Exists(output) || File.Exists(output))
    throw new IOException("Use a fresh private output directory under repository work/");
string Hash(string p) => Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(p))).ToLowerInvariant();
var sources = new[] { scenePath, Path.Combine(sourceDir, "Program.cs"), Path.Combine(sourceDir, "DashboardDdkStudy.csproj") };
var inputHashes = sources.Select(Hash).ToArray();
using var document = JsonDocument.Parse(File.ReadAllText(scenePath));
var root = document.RootElement;
if (root.GetProperty("schema_version").GetString() != "2.0" ||
    root.GetProperty("status").GetString() != "visual_concept_only" ||
    root.GetProperty("coordinate_frame").GetString() != "visual_stage_not_vehicle" ||
    root.GetProperty("unit").GetString() != "mm_render_scale_only")
    throw new InvalidDataException("Explicit unverified visual-stage declaration required");
var scenario = root.GetProperty("target_scenario");
if (scenario.GetProperty("option_code").GetString() != "M564" || scenario.GetProperty("drive").GetString() != "LHD" ||
    scenario.GetProperty("part_number").ValueKind != JsonValueKind.Null || scenario.GetProperty("verification").GetString() != "unresolved")
    throw new InvalidDataException("Unresolved M564 LHD target scenario required");
float voxel = Study.Number(root.GetProperty("voxel_mm"));
if (voxel < 1.5f || voxel > 3f) throw new InvalidDataException("Visual resolution outside bounded range");
string[] required = ["DASHBOARD_TRIM", "INSTRUMENT_HOOD", "INSTRUMENT_CLUSTER", "INSTRUMENT_GAUGE_MARKS",
    "CENTER_AIR_VENTS", "SIDE_AIR_VENTS", "DEFROST_OUTLETS_AND_DUCTS", "GLOVEBOX", "CENTER_CONSOLE",
    "HVAC_RADIO_CONTROLS", "SWITCHES_AND_BLANKS", "KNEE_STRIP_RESERVED"];
var layers = root.GetProperty("layers").EnumerateArray().ToArray();
if (!layers.Select(l => l.GetProperty("family_id").GetString()).OrderBy(x => x).SequenceEqual(required.OrderBy(x => x)))
    throw new InvalidDataException("Expected complete visible-family inventory required");
var allIds = new HashSet<string>();
var descriptors = new List<(JsonElement layer, Shape[] shapes)>();
foreach (var layer in layers)
{
    string colour = layer.GetProperty("colour").GetString()!;
    if (colour.Length != 7 || colour[0] != '#' || !colour.Skip(1).All(Uri.IsHexDigit))
        throw new InvalidDataException("Hex colour required");
    var shapes = layer.GetProperty("elements").EnumerateArray().Select(e => Shape.Parse(e, allIds)).ToArray();
    if (shapes.Length < 1 || shapes.Length > 512) throw new InvalidDataException("Bounded nonempty layer required");
    descriptors.Add((layer, shapes));
}
Directory.CreateDirectory(output);
if (!OperatingSystem.IsWindows()) File.SetUnixFileMode(output, UnixFileMode.UserRead | UnixFileMode.UserWrite | UnixFileMode.UserExecute);
File.Copy(scenePath, Path.Combine(output, "scene.json"));
using Library library = new(voxel);
var records = new List<object>();
foreach (var (layer, shapes) in descriptors)
{
    string family = layer.GetProperty("family_id").GetString()!;
    using Mesh mesh = new(library);
    foreach (var shape in shapes)
    {
        Vector3 pad = new(3 * voxel);
        using Voxels voxels = new(library, new DistanceField(shape.Distance), new BBox3(shape.Min - pad, shape.Max + pad));
        using Mesh primitive = voxels.mshAsMesh();
        if (primitive.nTriangleCount() == 0) throw new InvalidDataException($"Empty display element: {shape.Id}");
        mesh.Append(primitive);
    }
    string filename = family + ".stl";
    string path = Path.Combine(output, filename);
    mesh.SaveToStlFile(path);
    records.Add(new { family_id = family, file = filename, sha256 = Hash(path), triangles = mesh.nTriangleCount(),
        colour = layer.GetProperty("colour").GetString(), element_count = shapes.Length });
    Console.WriteLine($"{family}: {mesh.nTriangleCount()} triangles, {shapes.Length} display elements");
}
if (!sources.Select(Hash).SequenceEqual(inputHashes)) throw new InvalidDataException("Input changed during generation");
File.WriteAllText(Path.Combine(output, "scene-report.json"), JsonSerializer.Serialize(new {
    scene_id = root.GetProperty("scene_id").GetString(), status = "visual_concept_only", coordinate_frame = "visual_stage_not_vehicle",
    unit = "mm_render_scale_only", layers = records, scene_sha256 = inputHashes[0], generator_source_sha256 = inputHashes[1],
    project_source_sha256 = inputHashes[2], voxel_mm = voxel,
    source_files = sources.Select((p, i) => new { file = Path.GetRelativePath(repoRoot, p).Replace('\\', '/'), sha256 = inputHashes[i] }),
    runtime = new { name = Library.strName(), version = Library.strVersion(), build = Library.strBuildInfo() },
    input_measurements_available = false, fit_verified = false, dimensions_verified = false,
    manufacturing_authorized = false, physical_validation = false,
    mesh_policy = "Separate overlapping display surfaces; no printable or physically assembled part is exported."
}, new JsonSerializerOptions { WriteIndented = true }) + "\n");
Console.WriteLine($"PicoGK DDK visual study: {records.Count} families; report at {output}");

sealed class DistanceField(Func<Vector3, float> distance) : IImplicit
{
    public float fSignedDistance(in Vector3 p) => distance(p);
}

static class Study
{
    public static float Number(JsonElement e)
    {
        float x = e.GetSingle();
        if (!float.IsFinite(x)) throw new InvalidDataException("Finite numbers required");
        return x;
    }
    public static Vector3 Vector(JsonElement e)
    {
        var a = e.EnumerateArray().Select(Number).ToArray();
        if (a.Length != 3 || a.Any(x => MathF.Abs(x) > 2000)) throw new InvalidDataException("Bounded XYZ triple required");
        return new(a[0], a[1], a[2]);
    }
    public static float Box(Vector3 p, Vector3 half)
    {
        Vector3 q = Vector3.Abs(p) - half;
        return Vector3.Max(q, Vector3.Zero).Length() + MathF.Min(MathF.Max(q.X, MathF.Max(q.Y, q.Z)), 0);
    }
    public static float Extrude(float plane, float axis) => MathF.Min(MathF.Max(plane, axis), 0) + new Vector2(MathF.Max(plane, 0), MathF.Max(axis, 0)).Length();
    public static float Panel(Vector3 p, Vector3 half, float r)
    {
        Vector2 q = Vector2.Abs(new(p.X, p.Z)) - new Vector2(half.X - r, half.Z - r);
        float d = Vector2.Max(q, Vector2.Zero).Length() + MathF.Min(MathF.Max(q.X, q.Y), 0) - r;
        return Extrude(d, MathF.Abs(p.Y) - half.Y);
    }
}

sealed class Shape
{
    public required string Id;
    public required string Kind;
    public Vector3 Centre, Half, A, B, Min, Max;
    public float Radius, Border, Tilt;
    public float[][] Sections = [];
    public static Shape Parse(JsonElement e, HashSet<string> ids)
    {
        var s = new Shape { Id = e.GetProperty("id").GetString()!, Kind = e.GetProperty("kind").GetString()!,
            Centre = Study.Vector(e.GetProperty("centre")), Half = Study.Vector(e.GetProperty("half")),
            Radius = Study.Number(e.GetProperty("radius")), Border = Study.Number(e.GetProperty("border")) };
        if (!ids.Add(s.Id) || e.GetProperty("basis").GetString() != "artistic_assumption" ||
            new[] { "airbag", "mount", "fastener", "steering" }.Any(word => s.Id.Contains(word, StringComparison.OrdinalIgnoreCase)))
            throw new InvalidDataException("Unique nonfunctional visual assumption required");
        if (s.Half.X <= 0 || s.Half.Y <= 0 || s.Half.Z <= 0 || s.Half.X > 1000 || s.Half.Y > 350 || s.Half.Z > 400 || s.Radius < 0 || s.Border < 0)
            throw new InvalidDataException("Bounded positive shape envelope required");
        s.Min = s.Centre - s.Half; s.Max = s.Centre + s.Half;
        switch (s.Kind)
        {
            case "round_box":
                if (s.Radius >= MathF.Min(s.Half.X, MathF.Min(s.Half.Y, s.Half.Z))) throw new InvalidDataException("Rounded box radius out of range");
                break;
            case "round_panel_y":
            case "frame_y":
                if (s.Radius >= MathF.Min(s.Half.X, s.Half.Z)) throw new InvalidDataException("Panel radius out of range");
                if (s.Kind == "frame_y" && (s.Border <= 0 || s.Border >= s.Radius)) throw new InvalidDataException("Frame border out of range");
                break;
            case "disk_y":
            case "annulus_y":
                if (s.Radius <= 0 || s.Radius > MathF.Min(s.Half.X, s.Half.Z) || (s.Kind == "annulus_y" && (s.Border <= 0 || s.Border >= s.Radius)))
                    throw new InvalidDataException("Disk or ring out of range");
                break;
            case "segment":
                s.A = Study.Vector(e.GetProperty("a")); s.B = Study.Vector(e.GetProperty("b"));
                if (s.Radius <= 0 || Vector3.Distance(s.A, s.B) < 0.1f) throw new InvalidDataException("Nonzero segment required");
                s.Min = Vector3.Min(s.A, s.B) - new Vector3(s.Radius); s.Max = Vector3.Max(s.A, s.B) + new Vector3(s.Radius);
                break;
            case "loft_x":
                s.Sections = e.GetProperty("sections").EnumerateArray().Select(v => v.EnumerateArray().Select(Study.Number).ToArray()).ToArray();
                if (s.Sections.Length < 3 || s.Sections.Length > 24) throw new InvalidDataException("Bounded loft section list required");
                float last = float.NegativeInfinity;
                foreach (var sec in s.Sections)
                {
                    // x, front-y, rear-y, bottom-z, top-z, corner radius.
                    if (sec.Length != 6 || sec[0] <= last || sec[1] >= sec[2] || sec[3] >= sec[4] || sec[5] <= 0 || sec[5] >= MathF.Min(sec[2]-sec[1],sec[4]-sec[3])/2 || sec.Any(v => MathF.Abs(v)>2000))
                        throw new InvalidDataException("Ordered bounded loft sections required");
                    last = sec[0];
                }
                s.Min = new(s.Sections.First()[0], s.Sections.Min(v => v[1]), s.Sections.Min(v => v[3]));
                s.Max = new(s.Sections.Last()[0], s.Sections.Max(v => v[2]), s.Sections.Max(v => v[4]));
                break;
            default: throw new InvalidDataException($"Unsupported shape kind: {s.Kind}");
        }
        if (e.TryGetProperty("tilt_x_degrees", out var tilt))
        {
            s.Tilt = Study.Number(tilt) * MathF.PI / 180;
            if (MathF.Abs(s.Tilt) > MathF.PI/3 || s.Kind != "round_box") throw new InvalidDataException("Only bounded visual boxes may be tilted");
            float hy = MathF.Abs(MathF.Cos(s.Tilt))*s.Half.Y + MathF.Abs(MathF.Sin(s.Tilt))*s.Half.Z;
            float hz = MathF.Abs(MathF.Sin(s.Tilt))*s.Half.Y + MathF.Abs(MathF.Cos(s.Tilt))*s.Half.Z;
            s.Min = s.Centre-new Vector3(s.Half.X,hy,hz); s.Max=s.Centre+new Vector3(s.Half.X,hy,hz);
        }
        return s;
    }
    public float Distance(Vector3 p)
    {
        Vector3 q = p-Centre;
        if (Tilt != 0) q = new(q.X, MathF.Cos(Tilt)*q.Y+MathF.Sin(Tilt)*q.Z, -MathF.Sin(Tilt)*q.Y+MathF.Cos(Tilt)*q.Z);
        switch (Kind)
        {
            case "round_box": return Study.Box(q, Half-new Vector3(Radius))-Radius;
            case "round_panel_y": return Study.Panel(q,Half,Radius);
            case "frame_y": return MathF.Max(Study.Panel(q,Half,Radius), -Study.Panel(q,new(Half.X-Border,Half.Y+3,Half.Z-Border),Radius-Border));
            case "disk_y": return Study.Extrude(new Vector2(q.X,q.Z).Length()-Radius,MathF.Abs(q.Y)-Half.Y);
            case "annulus_y": return MathF.Max(Study.Extrude(new Vector2(q.X,q.Z).Length()-Radius,MathF.Abs(q.Y)-Half.Y),-Study.Extrude(new Vector2(q.X,q.Z).Length()-Radius+Border,MathF.Abs(q.Y)-Half.Y-3));
            case "segment":
                Vector3 v=p-A,w=B-A;
                return (v-w*Math.Clamp(Vector3.Dot(v,w)/Vector3.Dot(w,w),0,1)).Length()-Radius;
            case "loft_x": return Loft(p);
            default: throw new InvalidDataException("Unhandled shape");
        }
    }
    float Loft(Vector3 p)
    {
        int i=0;
        while(i<Sections.Length-2 && p.X>Sections[i+1][0]) i++;
        float[] a=Sections[i],b=Sections[i+1];
        float t=Math.Clamp((p.X-a[0])/(b[0]-a[0]),0,1);
        // Shape-preserving cubic interpolation removes shoulders at display
        // stations without overshooting their bounds. No station is measured.
        float Get(int j)
        {
            float Delta(int k)=>(Sections[k+1][j]-Sections[k][j])/(Sections[k+1][0]-Sections[k][0]);
            float Slope(int k)
            {
                if(k==0) return Delta(0);
                if(k==Sections.Length-1) return Delta(k-1);
                float before=Delta(k-1),after=Delta(k);
                if(before*after<=0) return 0;
                float h0=Sections[k][0]-Sections[k-1][0],h1=Sections[k+1][0]-Sections[k][0];
                float w0=2*h1+h0,w1=h1+2*h0;
                return (w0+w1)/(w0/before+w1/after);
            }
            float h=b[0]-a[0],tt=t*t,ttt=tt*t;
            return (2*ttt-3*tt+1)*a[j]+(ttt-2*tt+t)*h*Slope(i)+(-2*ttt+3*tt)*b[j]+(ttt-tt)*h*Slope(i+1);
        }
        float front=Get(1),back=Get(2),bottom=Get(3),top=Get(4),r=Get(5);
        Vector2 h=new((back-front)/2,(top-bottom)/2);
        Vector2 q=Vector2.Abs(new Vector2(p.Y-(front+back)/2,p.Z-(bottom+top)/2))-(h-new Vector2(r));
        float d=Vector2.Max(q,Vector2.Zero).Length()+MathF.Min(MathF.Max(q.X,q.Y),0)-r;
        return Study.Extrude(d,MathF.Max(Sections[0][0]-p.X,p.X-Sections[^1][0]));
    }
}
