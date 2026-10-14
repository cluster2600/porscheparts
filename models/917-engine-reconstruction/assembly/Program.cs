using System.Globalization;
using System.Numerics;
using System.Security.Cryptography;
using System.Text.Json;
using System.Text.RegularExpressions;
using PicoGK;
using PicoGKCatalog;

if (args.Length != 4) throw new ArgumentException("Usage: Engine recipe.json sha256 voxel_mm new_work_output");
string Hash(string path) { using var s = File.OpenRead(path); return Convert.ToHexString(SHA256.HashData(s)).ToLowerInvariant(); }
string input = Path.GetFullPath(args[0]), output = Path.GetFullPath(args[3]);
if (Hash(input) != args[1]) throw new InvalidDataException("Recipe hash mismatch");
float voxel = float.Parse(args[2], CultureInfo.InvariantCulture);
if (!float.IsFinite(voxel) || voxel <= 0 || Directory.Exists(output) || File.Exists(output))
    throw new ArgumentException("Invalid voxel or existing output");
bool underWork = false;
for (DirectoryInfo? parent = new(output); parent != null; parent = parent.Parent)
    if (File.Exists(Path.Combine(parent.FullName,".git")) || Directory.Exists(Path.Combine(parent.FullName,".git")))
    {
        underWork = Path.GetRelativePath(parent.FullName,output).StartsWith("work" + Path.DirectorySeparatorChar,StringComparison.Ordinal);
        break;
    }
if (!underWork) throw new IOException("Geometry must stay under repository work/");
using var document = JsonDocument.Parse(File.ReadAllText(input));
var root = document.RootElement;
if (root.GetProperty("classification").GetString() != "hypothetical_engine_components_not_manufacturing_geometry")
    throw new InvalidDataException("Wrong recipe classification");
Vector3 Vec(JsonElement element)
{
    var v = element.EnumerateArray().Select(x => x.GetSingle()).ToArray();
    if (v.Length != 3 || v.Any(x => !float.IsFinite(x))) throw new InvalidDataException("Invalid vector");
    return new(v[0],v[1],v[2]);
}
var ids = new HashSet<string>();
foreach (var item in root.GetProperty("parts").EnumerateArray())
{
    string id = item.GetProperty("id").GetString()!;
    if (!Regex.IsMatch(id,"^[a-z][a-z0-9_]*$") || !ids.Add(id)) throw new InvalidDataException("Invalid or duplicate part ID");
    if (item.GetProperty("add").GetArrayLength() == 0 && !item.TryGetProperty("source_mesh",out _))
        throw new InvalidDataException("Empty positive geometry");
    foreach (var group in new[] {"add","subtract","intersect","post_add","final_subtract"})
        foreach (var primitive in (item.TryGetProperty(group,out var list) ? list.EnumerateArray().ToArray() : Array.Empty<JsonElement>()))
        {
            if (primitive.GetProperty("kind").GetString() is "beam" or "annular_beam")
            {
                var a = Vec(primitive.GetProperty("a")); var b = Vec(primitive.GetProperty("b"));
                float r = primitive.GetProperty("r").GetSingle();
                if (a == b || !float.IsFinite(r) || r <= 0) throw new InvalidDataException("Invalid beam");
                if (primitive.GetProperty("kind").GetString() == "annular_beam")
                {
                    float inner = primitive.GetProperty("inner").GetSingle();
                    if (!float.IsFinite(inner) || inner <= 0 || inner >= r) throw new InvalidDataException("Invalid annular beam");
                }
            }
            else if (primitive.GetProperty("kind").GetString() == "box")
            {
                Vec(primitive.GetProperty("center")); var half = Vec(primitive.GetProperty("half"));
                if (MathF.Min(half.X,MathF.Min(half.Y,half.Z)) <= 0) throw new InvalidDataException("Invalid box");
            }
            else throw new InvalidDataException("Unknown primitive");
        }
}
Directory.CreateDirectory(output);
using Library library = new(voxel);
Voxels Primitive(JsonElement p)
{
    if (p.GetProperty("kind").GetString() is "beam" or "annular_beam")
    {
        using Lattice lat = new(library);
        float r = p.GetProperty("r").GetSingle();
        lat.AddBeam(Vec(p.GetProperty("a")),Vec(p.GetProperty("b")),r,r,p.GetProperty("round").GetBoolean());
        var v = new Voxels(lat);
        if (p.GetProperty("kind").GetString() == "annular_beam")
        {
            var a = Vec(p.GetProperty("a")); var b = Vec(p.GetProperty("b")); var delta = Vector3.Normalize(b-a)*5;
            using Lattice cut = new(library);
            float inner = p.GetProperty("inner").GetSingle();
            cut.AddBeam(a-delta,b+delta,inner,inner,false);
            using Voxels hole = new(cut);v.BoolSubtract(hole);
        }
        return v;
    }
    var center = Vec(p.GetProperty("center")); var half = Vec(p.GetProperty("half"));
    return Sdf.Vox(library,q => Sdf.Box(q,center,half),center-half-new Vector3(3*voxel),center+half+new Vector3(3*voxel));
}
var records = new List<object>();
foreach (var item in root.GetProperty("parts").EnumerateArray())
{
    string id = item.GetProperty("id").GetString()!;
    Console.WriteLine("EXPORT " + id);
    var positives = item.GetProperty("add").EnumerateArray().ToArray();
    Voxels initial;
    if (item.TryGetProperty("source_mesh",out var source))
    {
        string path = source.GetProperty("path").GetString()!;
        if (Hash(path) != source.GetProperty("sha256").GetString()) throw new InvalidDataException("Source mesh hash mismatch");
        using Mesh inputMesh = Mesh.mshFromStlFile(path,Mesh.EStlUnit.MM,libSet:library);
        initial = new Voxels(inputMesh);
    }
    else initial = Primitive(positives[0]);
    using Voxels body = initial;
    foreach (var p in positives.Skip(item.TryGetProperty("source_mesh",out _) ? 0 : 1)) { using var v = Primitive(p); body.BoolAdd(v); }
    foreach (var p in item.GetProperty("subtract").EnumerateArray()) { using var v = Primitive(p); body.BoolSubtract(v); }
    if (item.TryGetProperty("post_add",out var post)) foreach (var p in post.EnumerateArray()) { using var v = Primitive(p); body.BoolAdd(v); }
    if (item.TryGetProperty("final_subtract",out var cuts)) foreach (var p in cuts.EnumerateArray()) { using var v = Primitive(p); body.BoolSubtract(v); }
    foreach (var p in item.GetProperty("intersect").EnumerateArray()) { using var v = Primitive(p); body.BoolIntersect(v); }
    body.CalculateProperties(out float volume,out _);
    if (body.bIsEmpty() || !float.IsFinite(volume) || volume <= 0) throw new InvalidDataException("Empty or invalid part: " + id);
    using Mesh mesh = new(body);
    string stl = Path.Combine(output,id+".stl"), vdb = Path.Combine(output,id+".vdb");
    mesh.SaveToStlFile(stl); body.SaveToVdbFile(vdb);
    records.Add(new { id, triangles=mesh.nTriangleCount(), stl_sha256=Hash(stl), vdb_sha256=Hash(vdb), volume_mm3_hypothesis=volume });
}
if (Hash(input) != args[1]) throw new InvalidDataException("Recipe changed during generation");
File.WriteAllText(Path.Combine(output,"receipt.json"),JsonSerializer.Serialize(new {
    classification="hypothetical_engine_components_not_manufacturing_geometry", recipe_sha256=args[1], voxel_mm=voxel,
    kernel=Library.strVersion(), parts=records, manufacturing_authorized=false, engine_start_authorized=false
},new JsonSerializerOptions { WriteIndented=true })+"\n");
