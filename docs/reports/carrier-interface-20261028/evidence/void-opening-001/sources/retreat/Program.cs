using System.Globalization;
using System.Numerics;
using System.Text.Json;
using PicoGK;

if (args.Length != 2) throw new ArgumentException("Usage: NEW_OUTPUT_DIR VOXEL_MM");
string output = Path.GetFullPath(args[0]);
float h = float.Parse(args[1], CultureInfo.InvariantCulture);
if (Directory.Exists(output) || !float.IsFinite(h) || h < .02f || h > .1f)
    throw new ArgumentException("Fresh output and controlled voxel size required");
Directory.CreateDirectory(output);
using Library library = new(h);
const float radius = .4f;
var rows = new List<object>();
foreach (string name in new [] {"cube", "sphere"})
{
    IImplicit shape = new Primitive(name);
    BBox3 bounds = new(new Vector3(-2.6f), new Vector3(2.6f));
    using Voxels field = new(library, shape, bounds);
    field.CalculateProperties(out float before, out _);
    field.DoubleOffset(-(radius + .08f), radius);
    field.CalculateProperties(out float after, out _);
    using Mesh mesh = new(field);
    string file = name + ".stl";
    mesh.SaveToStlFile(Path.Combine(output, file), Mesh.EStlUnit.MM);
    rows.Add(new { name, file, before_mm3 = before, after_mm3 = after,
        triangles = mesh.nTriangleCount(), radius_mm = radius, retreat_mm = .08f });
}
File.WriteAllText(Path.Combine(output, "runtime.json"), JsonSerializer.Serialize(new {
    status = "numerical_opening_control_only", voxel_mm = h, radius_mm = radius, retreat_mm = .08f,
    picogk = "2.3.0", cases = rows, manufacturing_authorized = false
}, new JsonSerializerOptions {WriteIndented = true}));

sealed class Primitive(string name) : IImplicit
{
    public float fSignedDistance(in Vector3 point)
    {
        if (name == "sphere") return point.Length() - 2f;
        Vector3 q = Vector3.Abs(point) - new Vector3(2f);
        return Vector3.Max(q, Vector3.Zero).Length() + Math.Min(Math.Max(q.X, Math.Max(q.Y, q.Z)), 0f);
    }
}
