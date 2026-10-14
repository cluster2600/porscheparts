using System.Globalization;
using System.Numerics;
using System.Security.Cryptography;
using System.Text.Json;
using PicoGK;

if (args.Length != 4) throw new ArgumentException("Usage: Prototype assumptions.json sha256 voxel_mm new_output");
string source = Path.GetFullPath(args[0]), output = Path.GetFullPath(args[3]);
string Hash(string path) { using var s = File.OpenRead(path); return Convert.ToHexString(SHA256.HashData(s)).ToLowerInvariant(); }
if (Hash(source) != args[1]) throw new InvalidDataException("Assumption hash mismatch");
float voxel = float.Parse(args[2], CultureInfo.InvariantCulture);
if (!float.IsFinite(voxel) || voxel <= 0) throw new ArgumentException("Invalid voxel size");
if (Directory.Exists(output) || File.Exists(output)) throw new IOException("Output already exists");
for (DirectoryInfo? parent = new(output); parent != null; parent = parent.Parent)
    if (File.Exists(Path.Combine(parent.FullName, ".git")) || Directory.Exists(Path.Combine(parent.FullName, ".git")))
    {
        if (!Path.GetRelativePath(parent.FullName, output).StartsWith("work" + Path.DirectorySeparatorChar, StringComparison.Ordinal))
            throw new IOException("Hypothesis geometry must stay in ignored work/");
        break;
    }
using var document = JsonDocument.Parse(File.ReadAllText(source));
var root = document.RootElement;
if (root.GetProperty("classification").GetString() != "hypothesis_only_not_identified_or_measured_engine")
    throw new InvalidDataException("Wrong hypothesis classification");
float D(string name)
{
    float v = root.GetProperty("dimensions_mm").GetProperty(name).GetSingle();
    if (!float.IsFinite(v) || v <= 0) throw new InvalidDataException("Invalid dimension: " + name);
    return v;
}
Directory.CreateDirectory(output);
using Library library = new(voxel);
Voxels Cylinder(Vector3 a, Vector3 b, float radius)
{
    using Lattice lattice = new(library);
    lattice.AddBeam(a, b, radius, radius, false);
    return new Voxels(lattice);
}
Voxels AlongX(float y, float length, float radius) => Cylinder(new(-length/2, y, 0), new(length/2, y, 0), radius);
var records = new Dictionary<string, object>();
void Export(Voxels part, string name)
{
    part.CalculateProperties(out float volume, out _);
    if (part.bIsEmpty() || !float.IsFinite(volume) || volume <= 0) throw new InvalidDataException("Invalid prototype: " + name);
    using Mesh mesh = new(part);
    string stl = Path.Combine(output, name + ".stl"), vdb = Path.Combine(output, name + ".vdb");
    mesh.SaveToStlFile(stl); part.SaveToVdbFile(vdb);
    records[name] = new { volume_mm3_hypothetical = volume, triangles = mesh.nTriangleCount(), stl_sha256 = Hash(stl), vdb_sha256 = Hash(vdb) };
}
using (Voxels barrel = Cylinder(Vector3.Zero, new(0,D("cylinder_length"),0), D("cylinder_outer_diameter")/2))
{
    int count = root.GetProperty("fin_count").GetInt32();
    if (count <= 0 || count > 100) throw new InvalidDataException("Invalid fin count");
    for (int i=0; i<count; i++)
    {
        float y = D("fin_start") + i*D("fin_pitch");
        using Voxels fin = Cylinder(new(0,y,0), new(0,y+D("fin_thickness"),0), D("fin_diameter")/2);
        barrel.BoolAdd(fin);
    }
    using Voxels bore = Cylinder(new(0,-voxel*3,0), new(0,D("cylinder_length")+voxel*3,0), D("bore")/2);
    barrel.BoolSubtract(bore); Export(barrel,"cylinder");
}
using (Voxels piston = Cylinder(new(0,-D("piston_height")/2,0),new(0,D("piston_height")/2,0),(D("bore")-D("piston_diametral_clearance"))/2))
{
    float radius = (D("bore")-D("piston_diametral_clearance"))/2;
    using Voxels envelope = Cylinder(new(0,-D("piston_height")/2,0),new(0,D("piston_height")/2,0),radius);
    using Voxels cavity = Cylinder(new(0,-D("piston_height")/2-voxel*3,0),
                                  new(0,D("piston_height")/2-D("piston_crown_thickness"),0),radius-D("piston_skirt_thickness"));
    piston.BoolSubtract(cavity);
    foreach (int sign in new[] {-1,1})
    {
        using Voxels boss = Cylinder(new(sign*D("piston_boss_inner_x"),0,0),
                                     new(sign*(radius+voxel*3),0,0),D("piston_boss_outer_diameter")/2);
        piston.BoolAdd(boss);
    }
    piston.BoolIntersect(envelope);
    using Voxels bore = AlongX(0,D("bore")+voxel*6,D("pin_outer_diameter")/2);
    piston.BoolSubtract(bore); Export(piston,"piston");
}
using (Voxels rod = Cylinder(Vector3.Zero,new(0,D("rod_length"),0),D("rod_beam_diameter")/2))
{
    using Voxels big = AlongX(0,D("rod_width"),D("rod_big_outer_diameter")/2);
    using Voxels small = AlongX(D("rod_length"),D("rod_width"),D("rod_small_outer_diameter")/2);
    rod.BoolAdd(big); rod.BoolAdd(small);
    using Voxels bigBore = AlongX(0,D("rod_width")+voxel*6,D("rod_big_bore")/2);
    using Voxels smallBore = AlongX(D("rod_length"),D("rod_width")+voxel*6,D("pin_outer_diameter")/2);
    rod.BoolSubtract(bigBore); rod.BoolSubtract(smallBore); Export(rod,"rod");
}
using (Voxels pin = AlongX(0,D("pin_length"),D("pin_outer_diameter")/2))
{
    using Voxels hollow = AlongX(0,D("pin_length")+voxel*6,D("pin_inner_diameter")/2);
    pin.BoolSubtract(hollow); Export(pin,"pin");
}
if (Hash(source) != args[1]) throw new InvalidDataException("Assumptions changed during execution");
File.WriteAllText(Path.Combine(output,"receipt.json"),JsonSerializer.Serialize(new {
    classification="hypothetical_parametric_prototypes_not_engine_parts", assumptions_sha256=args[1], voxel_mm=voxel,
    runtime=new { name=Library.strName(),version=Library.strVersion(),build=Library.strBuildInfo() }, prototypes=records,
    scan_fit_verified=false, material_qualified=false, manufacturing_authorized=false
},new JsonSerializerOptions { WriteIndented=true })+"\n");
