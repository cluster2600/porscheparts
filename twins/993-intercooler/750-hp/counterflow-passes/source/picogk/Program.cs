using System.Numerics;
using System.Text.Json;
using PicoGK;
using PicoGKCatalog;

// Topology coupon of a two-pass charge tube: offset-strip fins, the pass divider
// and one return tank. Local dimensions come from the lightest two-pass
// candidate; the channel count per pass and the tank length are reduced or
// assumed, so this is not a core segment. Metal and the charge domain, with and
// without the tank, are exported for an independent connectivity check.
if (args.Length != 2) throw new ArgumentException("Usage: Passes passes.json new-output");
var report = JsonDocument.Parse(File.ReadAllText(args[0])).RootElement;
foreach (var item in report.GetProperty("acceptance").EnumerateObject())
    if (item.Value.GetBoolean()) throw new ArgumentException("Coupon cannot grant engineering acceptance");
var g = report.GetProperty("extended_search").GetProperty("lightest_by_passes").GetProperty("2").GetProperty("geometry");
float F(string name) => g.GetProperty(name).GetSingle();
float gap = F("hot_gap_mm"), pitch = F("hot_pitch_mm"), fin = F("fin_mm"), strip = F("strip_length_mm"), wall = F("wall_mm");
if (g.GetProperty("charge_passes").GetInt32() != 2) throw new ArgumentException("Expected the two-pass candidate");
const float voxel = 0.0375f;
const int channelsPerPass = 5, strips = 2;
const float tank = 8f;
if (fin < 4 * voxel || wall < 4 * voxel || pitch <= fin) throw new ArgumentException("Unresolved fins or walls");
string output = Path.GetFullPath(args[1]);
if (Directory.Exists(output)) throw new IOException("Output exists; preserve previous run");
Directory.CreateDirectory(output);

// x along the charge flow, y along the cooling air (front y = 0), z across the tube.
float length = strips * strip, group = channelsPerPass * pitch;
float y0 = wall, ym = wall + group + wall / 2, depth = 2 * group + 3 * wall, height = gap + 2 * wall;
float Box(Vector3 p, Vector3 lo, Vector3 hi) => Sdf.Box(p, (lo + hi) / 2, (hi - lo) / 2);
float Outer(Vector3 p) => Box(p, new(0, 0, 0), new(length + tank + wall, depth, height));
float Inner(Vector3 p) => Box(p, new(-1, wall, wall), new(length + tank, depth - wall, wall + gap));
float Shell(Vector3 p) => MathF.Max(Outer(p), -Inner(p));
float Divider(Vector3 p) => Box(p, new(-1, ym - wall / 2, wall - voxel), new(length, ym + wall / 2, wall + gap + voxel));
// Offset strips: fin lines every pitch inside each pass, shifted by half a pitch on alternate strips.
float Fins(Vector3 p)
{
    int k = Math.Clamp((int)MathF.Floor(p.X / strip), 0, strips - 1);
    float offset = (k % 2) * pitch / 2, start = p.Y < ym ? y0 : ym + wall / 2;
    float m = ((p.Y - start - offset) % pitch + pitch) % pitch;
    float line = MathF.Min(m, pitch - m) - fin / 2;
    float inPass = MathF.Max(start - p.Y, p.Y - (start + group));
    float band = MathF.Max(MathF.Abs(p.Z - height / 2) - (gap / 2 + voxel), MathF.Max(-p.X, p.X - length));
    return MathF.Max(MathF.Max(line, inPass), band);
}
float Cut(Vector3 p) => -p.X;
float Metal(Vector3 p) => MathF.Max(MathF.Min(MathF.Min(Shell(p), Divider(p)), Fins(p)), Cut(p));
float Charge(Vector3 p) => MathF.Max(MathF.Max(Inner(p), -MathF.Min(Divider(p), Fins(p))), Cut(p));
float NoTank(Vector3 p) => MathF.Max(Charge(p), p.X - (length - 2 * voxel));
// View only: the metal without its top wall so the fins and the divider are visible.
float Open(Vector3 p) => MathF.Max(Metal(p), p.Z - (wall + gap));

using Library lib = new(voxel);
var parts = new List<object>();
Vector3 lo = new(-voxel, -voxel, -voxel), hi = new(length + tank + wall + voxel, depth + voxel, height + voxel);
foreach (var (name, f) in new (string, Func<Vector3, float>)[] { ("two-pass-metal", Metal), ("two-pass-charge", Charge), ("two-pass-charge-without-tank", NoTank), ("two-pass-metal-open-view", Open) })
{
    using Voxels v = Sdf.Vox(lib, f, lo, hi);
    using Mesh mesh = new(v);
    mesh.SaveToStlFile(Path.Combine(output, name + ".stl"), Mesh.EStlUnit.MM);
    parts.Add(new { name, triangles = mesh.nTriangleCount(), voxel_volume_mm3 = Sdf.Vol(v) * 1000 });
    Console.WriteLine("GENERATED " + name);
}
File.WriteAllText(Path.Combine(output, "generation.json"), JsonSerializer.Serialize(new {
    status = "native_picogk_topology_coupon_not_qualified", kernel = Library.strVersion(), voxel_mm = voxel,
    source = "extended_search.lightest_by_passes.2", hot_gap_mm = gap, hot_pitch_mm = pitch, fin_mm = fin, strip_length_mm = strip, wall_mm = wall,
    channels_per_pass = channelsPerPass, strips, return_tank_length_mm = tank, coupon_extents_mm = new[] { length + tank + wall, depth, height },
    reduced = "channels per pass reduced from the candidate; tank length assumed; inlet end cut open",
    parts, manufacturing_authorized = false, full_core_generated = false, headers_generated = false
}, new JsonSerializerOptions { WriteIndented = true }) + "\n");
