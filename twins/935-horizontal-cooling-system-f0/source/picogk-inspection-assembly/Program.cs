using System.Numerics;
using System.Security.Cryptography;
using System.Text.Json;
using System.Text.RegularExpressions;
using PicoGK;

if (args.Length != 3) throw new ArgumentException("Usage: case.json sha256 NEW_PRIVATE_OUTPUT");
string source = Path.GetFullPath(args[0]), output = Path.GetFullPath(args[2]);
string Hash(string path) { using var stream = File.OpenRead(path); return Convert.ToHexString(SHA256.HashData(stream)).ToLowerInvariant(); }
if (Hash(source) != args[1]) throw new InvalidDataException("Case hash mismatch");
if (Directory.Exists(output) || File.Exists(output)) throw new IOException("Use a new output directory");
bool privateOutput = false;
for (DirectoryInfo parent = new(output); parent != null; parent = parent.Parent)
    if (File.Exists(Path.Combine(parent.FullName, ".git")) || Directory.Exists(Path.Combine(parent.FullName, ".git")))
    {
        privateOutput = Path.GetRelativePath(parent.FullName, output).StartsWith("work" + Path.DirectorySeparatorChar);
        break;
    }
if (!privateOutput) throw new IOException("Assembly geometry must stay in ignored repository work/");
using var doc = JsonDocument.Parse(File.ReadAllText(source));
var root = doc.RootElement;
if (root.GetProperty("classification").GetString() != "inspection_assembly_not_verified_935_installation" ||
    root.GetProperty("scale_verified").GetBoolean() || root.GetProperty("assumptions").GetArrayLength() == 0)
    throw new InvalidDataException("Explicit uncalibrated inspection assumptions required");
float Positive(JsonElement e) { float v = e.GetSingle(); if (!float.IsFinite(v) || v <= 0) throw new InvalidDataException("Positive finite dimension required"); return v; }
Vector3 Vec(JsonElement e)
{
    var a = e.EnumerateArray().Select(x => x.GetSingle()).ToArray();
    if (a.Length != 3 || a.Any(x => !float.IsFinite(x))) throw new InvalidDataException("Finite XYZ vector required");
    return new(a[0], a[1], a[2]);
}
Matrix4x4 Transform(JsonElement e)
{
    var rows = e.EnumerateArray().Select(r => r.EnumerateArray().Select(x => x.GetSingle()).ToArray()).ToArray();
    if (rows.Length != 4 || rows.Any(r => r.Length != 4 || r.Any(x => !float.IsFinite(x))) ||
        rows[3][0] != 0 || rows[3][1] != 0 || rows[3][2] != 0 || rows[3][3] != 1)
        throw new InvalidDataException("Finite affine column-vector matrix required");
    Vector3[] columns = Enumerable.Range(0,3).Select(i => new Vector3(rows[0][i],rows[1][i],rows[2][i])).ToArray();
    float scale = columns[0].Length();
    if (scale <= 0 || scale > 100 || columns.Any(c => MathF.Abs(c.Length()/scale-1) > 1e-5f) ||
        MathF.Abs(Vector3.Dot(columns[0],columns[1])) > 1e-5f*scale*scale ||
        MathF.Abs(Vector3.Dot(columns[0],columns[2])) > 1e-5f*scale*scale ||
        MathF.Abs(Vector3.Dot(columns[1],columns[2])) > 1e-5f*scale*scale ||
        Vector3.Dot(Vector3.Cross(columns[0],columns[1]),columns[2]) <= 0)
        throw new InvalidDataException("Only proper rigid poses with uniform positive scale are allowed");
    // JSON uses column vectors; System.Numerics/PicoGK uses row vectors.
    return new(rows[0][0],rows[1][0],rows[2][0],0, rows[0][1],rows[1][1],rows[2][1],0,
               rows[0][2],rows[1][2],rows[2][2],0, rows[0][3],rows[1][3],rows[2][3],1);
}
var imports = root.GetProperty("imports").EnumerateArray().ToArray();
var ids = new HashSet<string>();
foreach (var item in imports)
{
    string id = item.GetProperty("id").GetString();
    if (!Regex.IsMatch(id, "^[a-z][a-z0-9_]{0,63}$") || id == "provisional_shroud" || !ids.Add(id)) throw new InvalidDataException("Unique bounded component IDs required");
    if (Hash(item.GetProperty("path").GetString()) != item.GetProperty("sha256").GetString()) throw new InvalidDataException("Imported geometry hash mismatch");
    _ = Transform(item.GetProperty("source_to_assembly_mm"));
}
if (imports.Length == 0 || imports.Length > 16) throw new InvalidDataException("Bounded nonempty assembly required");
var h = root.GetProperty("shroud");
float voxel = Positive(root.GetProperty("voxel_mm")), inner = Positive(h.GetProperty("inner_radius_mm")), wall = Positive(h.GetProperty("wall_mm"));
float z0 = h.GetProperty("barrel_z0_mm").GetSingle(), z1 = h.GetProperty("barrel_z1_mm").GetSingle(), z2 = h.GetProperty("lip_z2_mm").GetSingle();
float top = Positive(h.GetProperty("top_inner_radius_mm"));
Vector3 origin = Vec(h.GetProperty("origin_mm"));
if (!float.IsFinite(z0+z1+z2) || !(z0 < z1 && z1 < z2) || top < inner || inner > 500 || z2-z0 > 500 || wall < 3*voxel || wall > 30 || voxel < .2f || voxel > 5)
    throw new InvalidDataException("Bounded shroud dimensions and resolved wall required");
if (Math.Pow(2*(top+wall+2*voxel),2)*(z2-z0+12*voxel)/Math.Pow(voxel,3) > 100000000)
    throw new InvalidDataException("Shroud exceeds bounded voxel resources");
Directory.CreateDirectory(output);
if (!OperatingSystem.IsWindows()) File.SetUnixFileMode(output, UnixFileMode.UserRead|UnixFileMode.UserWrite|UnixFileMode.UserExecute);
File.Copy(source, Path.Combine(output,"case.json"));
using Library library = new(voxel);
using Mesh assembled = new(library);
var records = new List<object>();
foreach (var item in imports)
{
    string id = item.GetProperty("id").GetString(), path = item.GetProperty("path").GetString();
    using Mesh mesh = Mesh.mshFromStlFile(path, Mesh.EStlUnit.MM, libSet:library);
    if (mesh.nTriangleCount() == 0 || mesh.nTriangleCount() > 5000000) throw new InvalidDataException("Bounded nonempty imported mesh required");
    using Mesh placed = mesh.mshCreateTransformed(Transform(item.GetProperty("source_to_assembly_mm")));
    if (placed.nTriangleCount() != mesh.nTriangleCount()) throw new InvalidDataException("Import topology changed");
    string file = id + ".stl"; placed.SaveToStlFile(Path.Combine(output,file)); assembled.Append(placed);
    var box = placed.oBoundingBox();
    if (new[]{box.vecMin.X,box.vecMin.Y,box.vecMin.Z,box.vecMax.X,box.vecMax.Y,box.vecMax.Z}.Any(x => !float.IsFinite(x) || MathF.Abs(x)>1000000))
        throw new InvalidDataException("Invalid or unbounded placed mesh");
    if (Hash(path) != item.GetProperty("sha256").GetString()) throw new InvalidDataException("Import changed during assembly");
    records.Add(new {id, file, classification = item.GetProperty("classification").GetString(), triangles = placed.nTriangleCount(),
        sha256 = Hash(Path.Combine(output,file)), source_sha256 = Hash(path),
        source_to_assembly_mm = item.GetProperty("source_to_assembly_mm"),
        bounds_mm = new[] {new[]{box.vecMin.X,box.vecMin.Y,box.vecMin.Z},new[]{box.vecMax.X,box.vecMax.Y,box.vecMax.Z}}});
}
using Lattice outside = new(library), inside = new(library);
// Overlap the contained cylindrical sections to avoid coincident zero-distance caps.
outside.AddBeam(new Vector3(0,0,z0),new Vector3(0,0,z1+2*voxel),inner+wall,inner+wall,false);
outside.AddBeam(new Vector3(0,0,z1),new Vector3(0,0,z2),inner+wall,top+wall,false);
inside.AddBeam(new Vector3(0,0,z0-4*voxel),new Vector3(0,0,z1+2*voxel),inner,inner,false);
inside.AddBeam(new Vector3(0,0,z1),new Vector3(0,0,z2),inner,top,false);
inside.AddBeam(new Vector3(0,0,z2),new Vector3(0,0,z2+4*voxel),top,top,false);
using Voxels outer = new(outside), cavity = new(inside);
outer.BoolSubtract(cavity);
outer.CalculateProperties(out float volume, out _);
if (outer.bIsEmpty() || !float.IsFinite(volume) || volume <= 0) throw new InvalidDataException("Invalid provisional shroud");
using Mesh shroud = outer.mshAsMesh();
using Mesh placedShroud = shroud.mshCreateTransformed(Matrix4x4.CreateTranslation(origin));
placedShroud.SaveToStlFile(Path.Combine(output,"provisional_shroud.stl")); assembled.Append(placedShroud);
records.Add(new {id="provisional_shroud",file="provisional_shroud.stl",classification="generated_packaging_hypothesis_not_observed_935_housing",
    triangles=placedShroud.nTriangleCount(),sha256=Hash(Path.Combine(output,"provisional_shroud.stl")),volume_mm3_hypothesis=volume});
assembled.SaveToStlFile(Path.Combine(output,"assembly-inspection.stl"));
if (Hash(source) != args[1]) throw new InvalidDataException("Case changed during assembly");
File.WriteAllText(Path.Combine(output,"receipt.json"), JsonSerializer.Serialize(new {
    status="PicoGK_inspection_assembly_not_verified_installation",case_sha256=args[1],
    engine_context_family=root.GetProperty("engine_context_family").GetString(),components=records,
    assembly_sha256=Hash(Path.Combine(output,"assembly-inspection.stl")),voxel_mm=voxel,
    runtime=new{name=Library.strName(),version=Library.strVersion(),build=Library.strBuildInfo()},
    scale_verified=false,interfaces_verified=false,mechanism_dynamics_validated=false,
    historical_installation_verified=false,manufacturing_authorized=false,physical_validation=false
},new JsonSerializerOptions{WriteIndented=true})+"\n");
Console.WriteLine($"PicoGK inspection assembly: {records.Count} components; {assembled.nTriangleCount()} triangles");
