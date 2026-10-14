using System.Numerics;
using System.Text.Json;
using PicoGK;
using PicoGKCatalog;

// Research coupons for the core family screen: one gyroid double-network cube
// and one helical-web tube (HelixHeatX transposition). Metal and each fluid
// domain are exported separately so an independent script can measure them.
if (args.Length != 2) throw new ArgumentException("Usage: Cells screen.json new-output");
var report = JsonDocument.Parse(File.ReadAllText(args[0])).RootElement;
foreach (var item in report.GetProperty("acceptance").EnumerateObject())
    if (item.Value.GetBoolean()) throw new ArgumentException("Coupon cannot grant engineering acceptance");
var gy = report.GetProperty("gyroid_break_even_lighter_than_witness").GetProperty("geometry");
var he = report.GetProperty("helical_closest_in_domain")[0];
float F(JsonElement e, string name) => e.GetProperty(name).GetSingle();
float cell = F(gy, "cell_mm"), sheet = F(gy, "wall_mm");
float d = F(he, "tube_inner_mm"), wall = F(he, "tube_wall_mm"), web = F(he, "web_mm"), twist = F(he, "twist_pitch_180_mm");
const float voxel = 0.0375f;
foreach (float v in new[] { cell, sheet, d, wall, web, twist })
    if (!float.IsFinite(v) || v <= 0) throw new ArgumentException("Invalid geometry");
if (sheet < 4 * voxel || web < 4 * voxel || wall < 4 * voxel || 2 * sheet >= cell) throw new ArgumentException("Unresolved walls");
string output = Path.GetFullPath(args[1]);
if (Directory.Exists(output)) throw new IOException("Output exists; preserve previous run");
Directory.CreateDirectory(output);

float Box(Vector3 p, Vector3 lo, Vector3 hi) => Sdf.Box(p, (lo + hi) / 2, (hi - lo) / 2);

// Gyroid: two periods per side. The sheet is |G| below a level; each network is
// one side of it. The distance estimate matches Sdf.GyroidSheet. The sheet
// passes through the lattice corners, so a cube aligned on them leaves loose
// corner slivers; the window is shifted by an eighth of a cell.
float k = 2f * MathF.PI / cell, n = 2 * cell, shift = cell / 8;
float G(Vector3 p) => (MathF.Sin(p.X * k) * MathF.Cos(p.Y * k) + MathF.Sin(p.Y * k) * MathF.Cos(p.Z * k) + MathF.Sin(p.Z * k) * MathF.Cos(p.X * k)) / (1.5f * k);
float Cube(Vector3 p) => Box(p, new(shift), new(shift + n));
var gyroid = new (string name, Func<Vector3, float> f)[] {
    ("gyroid-metal", p => MathF.Max(Sdf.GyroidSheet(p, cell, sheet), Cube(p))),
    ("gyroid-charge-network", p => MathF.Max(sheet / 2 - G(p), Cube(p))),
    ("gyroid-cooling-network", p => MathF.Max(sheet / 2 + G(p), Cube(p))) };

// Helical tube: one 180 degree twist of the web; the web roots overlap the wall
// so the union has volume instead of a shared face.
float ri = d / 2, ro = ri + wall;
float Twisted(Vector3 p)
{
    float a = MathF.PI * p.Z / twist, c = MathF.Cos(a), s = MathF.Sin(a);
    float y = -s * p.X + c * p.Y;
    return MathF.Max(MathF.Abs(y) - web / 2, MathF.Sqrt(p.X * p.X + p.Y * p.Y) - (ri + 2 * voxel));
}
float Slab(Vector3 p) => MathF.Max(-p.Z, p.Z - twist);
float R(Vector3 p) => MathF.Sqrt(p.X * p.X + p.Y * p.Y);
float Shell(Vector3 p) => MathF.Max(R(p) - ro, ri - R(p));
var helical = new (string name, Func<Vector3, float> f)[] {
    ("helical-metal", p => MathF.Max(MathF.Min(Shell(p), Twisted(p)), Slab(p))),
    ("helical-charge-passage", p => MathF.Max(MathF.Max(R(p) - ri, -Twisted(p)), Slab(p))) };

using Library lib = new(voxel);
var parts = new List<object>();
void Emit(string name, Func<Vector3, float> f, Vector3 lo, Vector3 hi)
{
    using Voxels v = Sdf.Vox(lib, f, lo, hi);
    using Mesh mesh = new(v);
    mesh.SaveToStlFile(Path.Combine(output, name + ".stl"), Mesh.EStlUnit.MM);
    parts.Add(new { name, triangles = mesh.nTriangleCount(), voxel_volume_mm3 = Sdf.Vol(v) * 1000 });
    Console.WriteLine("GENERATED " + name);
}
foreach (var (name, f) in gyroid) Emit(name, f, new(shift - voxel), new(shift + n + voxel));
foreach (var (name, f) in helical) Emit(name, f, new(-ro - voxel, -ro - voxel, -voxel), new(ro + voxel, ro + voxel, twist + voxel));

File.WriteAllText(Path.Combine(output, "generation.json"), JsonSerializer.Serialize(new {
    status = "native_picogk_family_coupons_not_qualified", kernel = Library.strVersion(), voxel_mm = voxel,
    gyroid = new { cell_mm = cell, sheet_mm = sheet, cube_mm = n, window_origin_mm = shift, source = "gyroid_break_even_lighter_than_witness" },
    helical = new { tube_inner_mm = d, tube_wall_mm = wall, web_mm = web, twist_pitch_180_mm = twist, source = "helical_closest_in_domain[0]" },
    parts, manufacturing_authorized = false, full_core_generated = false, headers_generated = false,
    limitation = "Unit coupons only: no headers, no network separation at the faces, no bench adapters, no interfaces."
}, new JsonSerializerOptions { WriteIndented = true }) + "\n");
