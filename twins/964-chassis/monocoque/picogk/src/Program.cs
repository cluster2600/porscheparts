using System.Diagnostics;
using System.Numerics;
using System.Text.Json;
using PicoGK;
using ZesadMonocoque;

// A ZESAD-type carbon monocoque in voxels, inside the plate-50-05a envelope.
// Headless: no viewer.
//
//   ZesadMonocoque <work-dir> <out-dir> [voxel-mm]
//
// Reads envelope.stl, fields.bin/json and stations.json (prep_envelope.py),
// writes one STL per member group and monocoque.report.json. Every size below
// is a modelling hypothesis: this is a design envelope, not a part.

string work = args.Length > 0 ? args[0] : "work";
string outDir = args.Length > 1 ? args[1] : "out";
float vox = args.Length > 2 ? float.Parse(args[2], System.Globalization.CultureInfo.InvariantCulture) : 2.5f;
Directory.CreateDirectory(outDir);

// Geometric thickness of every laminate wall: two voxels. The laminate itself
// is thinner; masses use assumed layups, not this.
float wall = 2f * vox;
const float Panel = 25f;            // sandwich floor and bulkheads
const float DeepRim = 100f, ShallowRim = 60f;
var rims = new (string name, float width, float depth)[]
{
    ("door", 90f, DeepRim), ("windscreen", 80f, DeepRim), ("quarter_window", 70f, DeepRim),
    ("rear_window", 70f, DeepRim), ("front_lid", 50f, ShallowRim), ("engine_lid", 50f, ShallowRim),
    ("front_arch", 50f, ShallowRim), ("rear_arch", 50f, ShallowRim),
};
var clock = Stopwatch.StartNew();
void Stage(string s) => Console.Error.WriteLine($"  [{clock.Elapsed.TotalSeconds,6:F1} s] {s}");

using Library lib = new(vox);
Stations st = Stations.Load(Path.Combine(work, "stations.json"));
Apertures ap = new(work);
float D(in Vector3 p) => -p.X;
static float Slab(float x, float lo, float hi) => MathF.Max(lo - x, x - hi);
BBox3 Box(float d0, float d1, float y, float z0, float z1) => new(new Vector3(-d1, -y, z0), new Vector3(-d0, y, z1));
Voxels Vox(Func<Vector3, float> f, BBox3 b) => new(lib, new Fn(f), b);

Stage("envelope");
Voxels env = new(Mesh.mshFromStlFile(Path.Combine(work, "envelope.stl"), Mesh.EStlUnit.MM, 1f, null, lib));
Voxels deep = env.voxShell(-DeepRim), shallow = env.voxShell(-ShallowRim);

Stage("apertures");
Voxels cut = new(lib);
var cutters = new Dictionary<string, Voxels>();
foreach (string name in ap.Names)
{
    int k = ap.Index(name);
    // Bounded and clamped: the raw field runs to the grid edge and reaches
    // hundreds of millimetres, and the sign fill then leaks out of one side.
    cutters[name] = Vox(p => Math.Clamp(MathF.Max(-ap.Value(k, p), MathF.Abs(p.Y) - 880f), -30f, 30f), ap.Bounds(k, 30f));
    cut.BoolAdd(cutters[name]);
}

Stage("skin");
Voxels skin = env.voxShell(-wall);
skin.BoolSubtract(cut);

Stage("closed sections: aperture rings");
Voxels region = new(lib);
foreach (var (name, width, depth) in rims)
{
    Voxels ring = cutters[name].voxOffset(width);
    ring.BoolSubtract(cutters[name]);
    ring.BoolIntersect(depth == DeepRim ? deep : shallow);
    region.BoolAdd(ring);
    Stage($"  ring {name}");
}

Stage("closed sections: sills, tunnel, rails, B-ring");
float doorEnd = (float)st.door_d[1];
var members = new (string name, Func<Vector3, float> f, BBox3 b)[]
{
    ("sills", p => MathF.Max(Slab(D(p), 360, 1990), MathF.Max(st.Width(D(p)) - 210 - MathF.Abs(p.Y), p.Z - st.Bottom(D(p)) - 270)),
        Box(340, 2010, 900, 0, 750)),
    ("tunnel", p => MathF.Max(Slab(D(p), 380, 1975), MathF.Max(MathF.Abs(p.Y) - 100, p.Z - st.Bottom(D(p)) - 240)),
        Box(360, 1995, 120, 0, 700)),
    ("front rails", p => MathF.Max(Slab(D(p), -640, 392), MathF.Max(Slab(MathF.Abs(p.Y), 230, 330), Slab(p.Z, st.Bottom(D(p)) + 20, st.Bottom(D(p)) + 150))),
        Box(-660, 410, 350, 100, 600)),
    ("rear rails", p => MathF.Max(Slab(D(p), 1962, 3040), MathF.Max(Slab(MathF.Abs(p.Y), 360, 460), Slab(p.Z, st.Bottom(D(p)) + 30, st.Bottom(D(p)) + 150))),
        Box(1940, 3060, 480, 100, 600)),
};
foreach (var (name, f, b) in members)
{
    Voxels m = Vox(f, b);
    m.BoolIntersect(env);
    region.BoolAdd(m);
}
Voxels bRing = Vox(p => Slab(D(p), doorEnd + 5, doorEnd + 95), Box(doorEnd - 20, doorEnd + 120, 900, 0, 1400));
bRing.BoolIntersect(deep);
region.BoolAdd(bRing);

Stage("wheel space");
Voxels wheels = new(lib);
var axles = new (float dc, float zc, float r)[] { ((float)st.front_axle_d, 300f, 340f), ((float)st.rear_axle_d, 300f, 350f) };
foreach (var (dc, zc, r) in axles)
{
    float inner = 0.6f * st.Width(dc);
    wheels.BoolAdd(Vox(p => MathF.Max(new Vector2(D(p) - dc, p.Z - zc).Length() - r, inner - MathF.Abs(p.Y)),
        Box(dc - r - 20, dc + r + 20, 900, zc - r - 20, zc + r + 20)));
}

Stage("hollow sections");
region.BoolSubtract(cut);
region.BoolSubtract(wheels);
Voxels sections = region.voxShell(-wall);
sections.BoolSubtract(skin);

Stage("sandwich panels");
float fb = (float)st.front_bulkhead_d, rb = (float)st.rear_bulkhead_d;
Voxels panels = Vox(p => MathF.Max(Slab(D(p), fb, rb), p.Z - st.Bottom(D(p)) - Panel), Box(fb - 20, rb + 20, 900, 0, 450));
panels.BoolAdd(Vox(p => MathF.Max(Slab(D(p), fb - Panel / 2, fb + Panel / 2), p.Z - 860), Box(fb - 40, fb + 40, 900, 0, 900)));
panels.BoolAdd(Vox(p => MathF.Max(Slab(D(p), rb - Panel / 2, rb + Panel / 2), p.Z - st.Belt(rb)), Box(rb - 40, rb + 40, 900, 0, 920)));
panels.BoolIntersect(env.voxOffset(-wall));
panels.BoolSubtract(wheels);
panels.BoolSubtract(region);

Stage("wheel tubs");
Voxels tubs = new(lib);
foreach (var (dc, zc, r) in axles)
{
    float inner = 0.6f * st.Width(dc);
    Func<Vector3, float> rr = p => new Vector2(D(p) - dc, p.Z - zc).Length();
    tubs.BoolAdd(Vox(p => MathF.Max(MathF.Max(MathF.Abs(rr(p) - r - wall / 2) - wall / 2, inner - MathF.Abs(p.Y)), zc - 0.3f * r - p.Z),
        Box(dc - r - 30, dc + r + 30, 900, zc - r, zc + r + 30)));
    tubs.BoolAdd(Vox(p => MathF.Max(MathF.Max(MathF.Abs(MathF.Abs(p.Y) - inner + wall / 2) - wall / 2, rr(p) - r - wall), zc - 0.3f * r - p.Z),
        Box(dc - r - 30, dc + r + 30, inner + 20, zc - r, zc + r + 30)));
}
tubs.BoolIntersect(env);
tubs.BoolSubtract(skin);

Stage("export");
var groups = new (string name, Voxels v, float t)[] { ("skin", skin, wall), ("sections", sections, wall), ("panels", panels, Panel), ("tubs", tubs, wall) };
var report = new Dictionary<string, object>();
foreach (var (name, v, t) in groups)
{
    v.CalculateProperties(out float vol, out BBox3 bb);
    Mesh m = new(v);
    m.SaveToStlFile(Path.Combine(outDir, $"monocoque-{name}.stl"));
    report[name] = new { volume_dm3 = Math.Round(vol / 1e6, 2), geometric_thickness_mm = t, area_m2_estimate = Math.Round(vol / t / 1e6, 2),
                         triangles = m.nTriangleCount() };
    Stage($"  {name}: {vol / 1e6:F1} dm3, {m.nTriangleCount()} triangles");
}
env.CalculateProperties(out float envVol, out BBox3 envBox);
Vector3 size = envBox.vecMax - envBox.vecMin;
var doc = new
{
    model = "ZESAD-type carbon monocoque, design envelope (prohibited_pending_engineering)",
    kernel = $"{Library.strName()} {Library.strVersion()}",
    voxel_mm = vox,
    envelope = new { volume_m3 = Math.Round(envVol / 1e9, 3), size_mm = new[] { Math.Round(size.X), Math.Round(size.Y), Math.Round(size.Z) } },
    hypotheses = new
    {
        wall_geometric_mm = wall, sandwich_panel_mm = Panel,
        aperture_rings = rims.Select(r => new { r.name, width_mm = r.width, depth_mm = r.depth }),
        sills_mm = new { width = 210, height_above_floor = 270, d = new[] { 360, 1990 } },
        tunnel_mm = new { half_width = 100, height_above_floor = 240 },
        front_rails_mm = new { y = new[] { 230, 330 }, z_above_floor = new[] { 20, 150 } },
        rear_rails_mm = new { y = new[] { 360, 460 }, z_above_floor = new[] { 30, 150 } },
        b_ring_d_mm = new[] { doorEnd + 5, doorEnd + 95 },
        wheel_space = axles.Select(a => new { d = a.dc, z = a.zc, radius = a.r, inner_y = "0.6 x half width" }),
    },
    groups = report,
    seconds = Math.Round(clock.Elapsed.TotalSeconds, 1),
};
File.WriteAllText(Path.Combine(outDir, "monocoque.report.json"), JsonSerializer.Serialize(doc, new JsonSerializerOptions { WriteIndented = true }));
Console.WriteLine($"OK monocoque at {vox} mm voxels in {clock.Elapsed.TotalSeconds:F0} s");
return 0;
