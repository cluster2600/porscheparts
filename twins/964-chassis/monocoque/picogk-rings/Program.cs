// 964/993 carbon monocoque study on the plate 50-05a outline, with PicoGK.
//
// Architecture from docs/MONOCOQUE_964_993_ARCHITECTURE.md: a monocoque is a
// body shell whose rings are closed by construction. Elements, in the order of
// return measured by ring_study.py / body_study.py:
//   windscreen frame + A-pillars (front ring), longitudinal tunnel beam,
//   wheel-arch rings, bulkheads, B-hoop and boxed sills, roof rails.
// The outer skin is the plate 50-05a shell with its openings.
//
// Headless; no viewer. Usage:
//   Monocoque964 <params.json> <input-dir> <output-dir>
// Writes monocoque-f0.stl and monocoque-f0.report.json. F0 study geometry:
// prohibited_pending_engineering, nothing here is a part.

using System.Numerics;
using System.Text.Json;
using System.Text.Json.Nodes;
using PicoGK;

string paramsPath = args.Length > 0 ? args[0] : "params/monocoque-f0.json";
string inputDir = args.Length > 1 ? args[1] : "input";
string outputDir = args.Length > 2 ? args[2] : "output";
Directory.CreateDirectory(outputDir);

JsonNode spec = JsonNode.Parse(File.ReadAllText(paramsPath))!;
JsonNode geo = JsonNode.Parse(File.ReadAllText(Path.Combine(inputDir, "geometry.json")))!;
float P(string k) => spec["parameters"]![k]!["value"]!.GetValue<float>();
float G(string k) => geo[k]!.GetValue<float>();
float voxel = spec["voxel_mm"]!.GetValue<float>();
var clock = System.Diagnostics.Stopwatch.StartNew();
void Log(string s) => Console.Error.WriteLine($"  [{clock.Elapsed.TotalSeconds,6:F1}s] {s}");

using Library lib = new(voxel);
double rho = P("cfrp_density_g_cm3"), rhoCore = P("core_density_g_cm3");
var masses = new Dictionary<string, double>();   // grams, analytic (thin-wall)

// ---------------------------------------------------------------- body + skin
Log("body volume");
Mesh bodyMesh = Mesh.mshFromStlFile(Path.Combine(inputDir, "body-closed.stl"), libSet: lib);
Voxels body = new(bodyMesh);
Log("skin");
Mesh skinMesh = Mesh.mshFromStlFile(Path.Combine(inputDir, "skin-surface.stl"), libSet: lib);
float tSkin = P("skin_thickness_mm");
float tRender = MathF.Max(tSkin, 2f * voxel);
Voxels skin = Voxels.voxMeshShell(lib, skinMesh, tRender / 2f);
skin.BoolIntersect(body.voxOffset(voxel));                 // keep the skin on the body side
double skinArea = MeshArea(skinMesh);
masses["skin"] = skinArea * tSkin / 1000.0 * rho;

// ------------------------------------------------- closed-section ring tubes
Log("ring tubes");
var groups = new Dictionary<string, (string od, string wall)>
{
    ["front_ring"] = ("front_ring_od_mm", "front_ring_wall_mm"),
    ["b_ring"] = ("b_ring_od_mm", "b_ring_wall_mm"),
    ["rear_ring"] = ("rear_ring_od_mm", "rear_ring_wall_mm"),
    ["roof_rails"] = ("roof_rail_od_mm", "roof_rail_wall_mm"),
    ["arches"] = ("arch_od_mm", "arch_wall_mm"),
};
Lattice outer = new(lib), inner = new(lib);
foreach (var (name, path) in geo["paths"]!.AsObject())
{
    string group = path!["group"]!.GetValue<string>();
    var (odKey, wallKey) = groups[group];
    float ro = P(odKey) / 2f, ri = ro - P(wallKey);
    var pts = path["points"]!.AsArray().Select(p => new Vector3(
        p![0]!.GetValue<float>(), p[1]!.GetValue<float>(), p[2]!.GetValue<float>())).ToList();
    double length = 0;
    for (int i = 1; i < pts.Count; i++)
    {
        outer.AddBeam(pts[i - 1], pts[i], ro, ro, true);
        // Inner beams run past the tube ends: every tube is open-ended, so no
        // closed section seals a cavity, and joints share one continuous bore.
        Vector3 a = pts[i - 1], b = pts[i], dir = Vector3.Normalize(b - a);
        inner.AddBeam(i == 1 ? a - dir * ro : a, i == pts.Count - 1 ? b + dir * ro : b, ri, ri, false);
        length += (pts[i] - pts[i - 1]).Length();
    }
    masses[group] = masses.GetValueOrDefault(group) + length * MathF.PI * (ro * ro - ri * ri) / 1000.0 * rho;
}
// Solid tubes now; their bores are cut after assembly, through every panel
// they cross, so a bore never ends sealed inside a bulkhead or a sill.
Voxels frame = new(outer);
Voxels bores = new(inner);

// --------------------------------------------------- sills and tunnel (boxes)
Log("sills and tunnel");
float xf = G("front_bulkhead_x"), xr = G("rear_bulkhead_x");
float floorZ = G("floor_z_mm"), sillTop = geo["door_aperture"]!["sill_top_z"]!.GetValue<float>();
float wMid = geo["half_width_at"]!["door_mid"]!.GetValue<float>();
float sw = P("sill_width_mm"), swall = P("sill_wall_mm");
float tw = P("tunnel_width_mm"), th = P("tunnel_height_mm"), twall = P("tunnel_wall_mm");
float panelT = P("panel_thickness_mm"), panelSkin = P("panel_skin_mm");
float xMid = (xf + xr) / 2f, xHalf = (xf - xr) / 2f;
Voxels HollowBox(Vector3 c, Vector3 half, float wall)
{
    Vector3 lo = c - half - new Vector3(2), hi = c + half + new Vector3(2);
    Voxels v = Box(c, half, lo, hi);
    // inner box longer than the outer along x: open ends, no sealed cavity
    v.BoolSubtract(Box(c, half - new Vector3(-4f, wall, wall), lo - new Vector3(4, 0, 0), hi + new Vector3(4, 0, 0)));
    return v;
}
Voxels Box(Vector3 c, Vector3 half, Vector3 lo, Vector3 hi) =>
    new(lib, new Fn(p => { Vector3 q = Vector3.Abs(p - c) - half; return Vector3.Max(q, Vector3.Zero).Length() + MathF.Min(MathF.Max(q.X, MathF.Max(q.Y, q.Z)), 0f); }),
        new BBox3(lo, hi));

// Sills run out to the skin (clipped by the body) and sink one wall into the
// floor panel, so every contact has volume.
float sillY = wMid - sw / 2f + 10f;
float sillZ0 = floorZ + panelT - swall, sillH = sillTop - sillZ0;
Voxels sills = HollowBox(new(xMid, sillY, sillZ0 + sillH / 2f), new(xHalf, sw / 2f, sillH / 2f), swall);
sills.BoolAdd(HollowBox(new(xMid, -sillY, sillZ0 + sillH / 2f), new(xHalf, sw / 2f, sillH / 2f), swall));
sills.BoolIntersect(body);
masses["sills"] = 2 * 2 * (sw + sillH) * swall * (2 * xHalf) / 1000.0 * rho;

Vector3 tc = new(xMid, 0, floorZ + panelT - twall + th / 2f);
Voxels tunnel = HollowBox(tc, new(xHalf, tw / 2f, th / 2f), twall);
tunnel.BoolIntersect(body);
masses["tunnel"] = 2 * (tw + th) * twall * (2 * xHalf) / 1000.0 * rho;
// C4 tube clearance: a cylinder along the tunnel axis must not touch its walls.
float rc = P("c4_tube_clearance_diameter_mm") / 2f;
Voxels c4 = new(lib, new Fn(p => MathF.Max(new Vector2(p.Y - tc.Y, p.Z - tc.Z).Length() - rc, MathF.Abs(p.X - xMid) - xHalf)),
                new BBox3(new Vector3(xr - 2, -rc - 2, tc.Z - rc - 2), new Vector3(xf + 2, rc + 2, tc.Z + rc + 2)));
c4.BoolIntersect(tunnel);
c4.CalculateProperties(out float c4Clash, out BBox3 _);

// ------------------------------------------------- sandwich floor + bulkheads
Log("sandwich panels");
// Sandwich panels are drawn solid: a prepreg monocoque core is foam or
// honeycomb, which fills its region. Faces and core are accounted in mass
// (SandwichMass), not drawn separately; an open lattice would be an AM concept
// and, clipped to 20 mm panels, left sealed pockets and detached crumbs.
// The floor follows the body bottom: everything inside the skin up to
// panelT above the local bottom line. A flat slab at the median height left
// slivers where the bottom profile wanders by a few millimetres.
float[] sx = geo["stations"]!["x"]!.AsArray().Select(n => n!.GetValue<float>()).ToArray();
float[] sb = geo["stations"]!["bottom"]!.AsArray().Select(n => n!.GetValue<float>()).ToArray();
float Bottom(float x)
{
    int i = Array.FindIndex(sx, v => v <= x);              // stations run front (+x) to rear (-x)
    if (i <= 0) return sb[Math.Max(i, 0)];
    float t = (x - sx[i]) / (sx[i - 1] - sx[i]);
    return sb[i] + t * (sb[i - 1] - sb[i]);
}
float floorTop = floorZ + panelT + 40f;
Voxels floorRegion = new(lib, new Fn(p => MathF.Max(MathF.Max(p.Z - (Bottom(p.X) + tSkin + panelT), MathF.Abs(p.X - xMid) - xHalf),
                                                    MathF.Abs(p.Y) - wMid)),
                         new BBox3(new Vector3(xr - 2, -wMid - 2, floorZ - 20), new Vector3(xf + 2, wMid + 2, floorTop + 200)));
floorRegion.BoolIntersect(body.voxOffset(-tSkin));
Voxels floorPanel = floorRegion;
floorRegion.CalculateProperties(out float floorVol, out BBox3 _);
masses["floor_sandwich"] = SandwichMass(floorVol);

Voxels bulkheads = new(lib);
double bulkMass = 0;
foreach (var (x, top) in new[] { (xf, G("front_bulkhead_top_z")), (xr, G("rear_bulkhead_top_z")) })
{
    Voxels region = Box(new(x, 0, top / 2f), new(panelT / 2f, 900, top / 2f),
                        new(x - panelT, -902, -2), new(x + panelT, 902, top + 2));
    region.BoolIntersect(body.voxOffset(-tSkin));
    region.CalculateProperties(out float vol, out BBox3 _);
    bulkMass += SandwichMass(vol);
    bulkheads.BoolAdd(region);
}
masses["bulkheads"] = bulkMass;

// Panel area from the region volume; faces and core by thickness, not by
// voxel counts (a 1.5 mm face is below the voxel size).
double SandwichMass(double regionVol)
{
    double area = regionVol / panelT;
    return area * 2 * panelSkin / 1000.0 * rho + area * (panelT - 2 * panelSkin) / 1000.0 * rhoCore;
}

// ---------------------------------------------------------------- assembly
Log("assembly");
Voxels mono = skin.voxDuplicate();
foreach (Voxels v in new[] { frame, sills, tunnel, floorPanel, bulkheads }) mono.BoolAdd(v);
mono.BoolSubtract(bores);

// Drain and vent holes: closed sections and sandwich cores are vented to the
// outside (bonding out-gassing, water, inspection), so nothing is sealed.
float drainR = P("drain_hole_diameter_mm") / 2f;
var drains = new List<(float x, float y, float zTop)>();
foreach (float f in new[] { 0.2f, 0.5f, 0.8f })
{
    float x = xr + f * (xf - xr);
    drains.Add((x, sillY, floorZ + panelT + 5f));
    drains.Add((x, -sillY, floorZ + panelT + 5f));
    drains.Add((x, 0f, floorZ + panelT + 5f));
}

foreach (var (x, y, zTop) in drains)
    mono.BoolSubtract(new Voxels(lib, new Fn(p => MathF.Max(new Vector2(p.X - x, p.Y - y).Length() - drainR,
                                                            MathF.Max(floorZ - 80f - p.Z, p.Z - zTop))),
                                 new BBox3(new Vector3(x - drainR - 2, y - drainR - 2, floorZ - 82), new Vector3(x + drainR + 2, y + drainR + 2, zTop + 2))));
// (drains start below the body; each is a vertical cylinder up to zTop)
Log($"{drains.Count} drain/vent holes");
Mesh mesh = new(mono);
string stl = Path.Combine(outputDir, "monocoque-f0.stl");
mesh.SaveToStlFile(stl);
Log($"wrote {stl}: {mesh.nTriangleCount()} triangles");

double total = masses.Values.Sum();
var report = new JsonObject
{
    ["study_id"] = spec["study_id"]!.GetValue<string>(),
    ["status"] = spec["status"]!.GetValue<string>(),
    ["kernel"] = $"{Library.strName()} {Library.strVersion()}",
    ["voxel_mm"] = voxel,
    ["skin_rendered_thickness_mm"] = tRender,
    ["panels_drawn"] = "solid (foam/honeycomb core fills the region); mass from faces + core density",
    ["skin_area_m2"] = Math.Round(skinArea / 1e6, 3),
    ["mass_estimate_kg"] = new JsonObject(masses.OrderByDescending(kv => kv.Value)
        .Select(kv => KeyValuePair.Create(kv.Key, (JsonNode?)JsonValue.Create(Math.Round(kv.Value / 1000.0, 2)))).ToArray()),
    ["mass_total_kg"] = Math.Round(total / 1000.0, 1),
    ["mass_method"] = "thin-wall analytic: skin area x t; tube length x annulus; box perimeter x wall x length; sandwich faces at CFRP density, core region at core density. Joints and overlaps double-counted; no bonding, inserts, glass, doors or lids.",
    ["c4_tube_clearance_clash_mm3"] = Math.Round(c4Clash, 1),
    ["drain_vent_holes"] = drains.Count,
    ["triangles"] = mesh.nTriangleCount(),
    ["stl"] = Path.GetFileName(stl),
    ["seconds"] = Math.Round(clock.Elapsed.TotalSeconds, 1),
    ["release_flags"] = new JsonObject { ["geometry_released"] = false, ["manufacturing_released"] = false },
};
// LF and unescaped text, so Linux and Windows write identical bytes.
var jsonOptions = new JsonSerializerOptions
{
    WriteIndented = true,
    Encoder = System.Text.Encodings.Web.JavaScriptEncoder.UnsafeRelaxedJsonEscaping,
};
string reportText = report.ToJsonString(jsonOptions).Replace("\r\n", "\n") + "\n";
File.WriteAllText(Path.Combine(outputDir, "monocoque-f0.report.json"), reportText);
Console.Write(reportText);
return 0;

// ---------------------------------------------------------------- helpers
static double MeshArea(Mesh m)
{
    double a = 0;
    for (int i = 0; i < m.nTriangleCount(); i++)
    {
        m.GetTriangle(i, out Vector3 p0, out Vector3 p1, out Vector3 p2);
        a += Vector3.Cross(p1 - p0, p2 - p0).Length() / 2.0;
    }
    return a;
}

sealed class Fn : IImplicit
{
    readonly Func<Vector3, float> _f;
    public Fn(Func<Vector3, float> f) => _f = f;
    public float fSignedDistance(in Vector3 vec) => _f(vec);
}
