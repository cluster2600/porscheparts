using System.Globalization;
using System.Numerics;
using System.Security.Cryptography;
using System.Text.Json;
using Leap71.ShapeKernel;
using PicoGK;

if (args.Length != 4 || !float.TryParse(args[3], NumberStyles.Float, CultureInfo.InvariantCulture, out float step)
    || (step != .6f && step != .3f))
{ Console.Error.WriteLine("Usage: WaterHead INPUT_DIR CONTRACT_JSON NEW_OUTPUT_DIR 0.6_OR_0.3"); return 2; }
string input = Path.GetFullPath(args[0]), contractPath = Path.GetFullPath(args[1]), output = Path.GetFullPath(args[2]);
void Require(bool ok, string message) { if (!ok) throw new InvalidDataException(message); }
string Sha(string path) { using var f = File.OpenRead(path); return Convert.ToHexString(SHA256.HashData(f)).ToLowerInvariant(); }
Vector3 Point(JsonElement p) { Require(p.GetArrayLength() == 3, "Three coordinates required"); return new(p[0].GetSingle(), p[1].GetSingle(), p[2].GetSingle()); }
var pins = new Dictionary<string, string>();
void Pin(string path, string hash)
{ Require(File.Exists(path) && (File.GetAttributes(path)&FileAttributes.ReparsePoint) == 0 && Sha(path) == hash, "Input hash/type mismatch: "+Path.GetFileName(path)); pins.Add(path, hash); }
try
{
    Require(!Directory.Exists(output) && !File.Exists(output), "Output must be new");
    Pin(contractPath, Sha(contractPath));
    using var document = JsonDocument.Parse(File.ReadAllText(contractPath)); var c = document.RootElement;
    Require(c.GetProperty("schema").GetString() == "m64-water-head-layout/v1"
        && c.GetProperty("units").GetString() == "uncalibrated_scan_unit_assumed_mm", "Research contract required");
    foreach (string key in new[] { "source_master_modified", "material_removal_authorized", "manufacturing_authorized", "gas_oil_stud_spark_plug_domains_complete" })
        Require(!c.GetProperty(key).GetBoolean(), "Research-only gate required: "+key);
    var d = c.GetProperty("layout");
    float arcRadius=d.GetProperty("exhaust_arc_radius").GetSingle(), z=d.GetProperty("exhaust_arc_z").GetSingle(),
        radius=d.GetProperty("channel_radius").GetSingle(), header=d.GetProperty("header_radius").GetSingle(),
        bleedRadius=d.GetProperty("bleed_radius").GetSingle(), margin=d.GetProperty("diagnostic_wall_margin").GetSingle();
    int segments=d.GetProperty("arc_segments_per_half").GetInt32();
    Require(new[] {arcRadius,z,radius,header,bleedRadius,margin}.All(float.IsFinite)
        && radius >= 4*step && bleedRadius >= 2*step && radius <= 5 && header >= radius && header <= 8
        && margin >= 0 && margin <= 8 && arcRadius >= 15 && arcRadius <= 22 && z >= 20 && z <= 35
        && segments >= 8 && segments <= 64, "Unresolved or out-of-scope routing dimensions");
    var locations = new[] { "inlet", "supply_fork", "return_merge", "outlet", "bleed" }.ToDictionary(k => k, k => Point(d.GetProperty(k)));
    Require(locations.Values.All(p => float.IsFinite(p.X) && float.IsFinite(p.Y) && float.IsFinite(p.Z) && p.Length() <= 160), "Invalid routing coordinates");
    Pin(Path.Combine(input,"inputs.json"), c.GetProperty("input_manifest_sha256").GetString()!);
    using var manifest = JsonDocument.Parse(File.ReadAllText(Path.Combine(input,"inputs.json")));
    var parts = manifest.RootElement.GetProperty("parts").EnumerateArray().ToArray();
    Require(parts.Length == 13 && parts.Select(p => p.GetProperty("name").GetString()).Distinct().Count() == 13, "Exact retained module required");
    foreach (var p in parts)
    {
        string file=p.GetProperty("filename").GetString()!, name=p.GetProperty("name").GetString()!;
        Require(Path.GetFileName(file) == file && file == name+".stl", "Local input filename required");
        Pin(Path.Combine(input,file), p.GetProperty("sha256").GetString()!);
    }
    Require(pins[Path.Combine(input,"head.stl")] == c.GetProperty("head_stl_sha256").GetString(), "Retained head required");
    var axes=manifest.RootElement.GetProperty("axes").EnumerateArray().Where(a => a.GetProperty("name").GetString()!.StartsWith("exhaust_")).ToArray();
    Require(axes.Length == 2, "Two retained exhaust axes required");
    Directory.CreateDirectory(output);
    using Library lib = new(step); Library.RegisterGlobalLibrary(lib);
    Vector3 phase = new(.173f,.119f,.071f);
    using Voxels water = new(lib);
    var paths = new List<object>();
    // shortcut: round-ended routing beams, replace with engineered jacket and CFD port faces after interface review.
    void Route(string name, Vector3[] points, float r)
    {
        Require(points.Length >= 2 && points.Zip(points.Skip(1)).All(pair => Vector3.Distance(pair.First,pair.Second) > step), "Nondegenerate route required");
        using Lattice lattice = new(lib);
        for (int i=1;i<points.Length;i++) lattice.AddBeam(points[i-1]+phase,r,points[i]+phase,r);
        using Voxels pipe = new(lattice); water.BoolAdd(pipe);
        paths.Add(new { name, radius = r, points = points.Select(p => new[] {p.X,p.Y,p.Z}) });
    }
    Route("cold_inlet", new[] {locations["inlet"],locations["supply_fork"]}, header);
    foreach (var axis in axes)
    {
        Vector3 origin=Point(axis.GetProperty("origin")), direction=Point(axis.GetProperty("direction"));
        Require(MathF.Abs(direction.Length()-1) < 1e-5 && direction.Z > .9f, "Retained axis direction required");
        Vector3 centre=origin+direction*((z-origin.Z)/direction.Z);
        Vector3 bottom=centre-new Vector3(0,arcRadius,0), top=centre+new Vector3(0,arcRadius,0);
        string name=axis.GetProperty("name").GetString()!;
        Route(name+"_feed",new[] {locations["supply_fork"],bottom},radius);
        foreach (int sign in new[] {-1,1})
        {
            var arc=Enumerable.Range(0,segments+1).Select(i => {
                float angle=MathF.PI*i/segments;
                return centre+new Vector3(sign*arcRadius*MathF.Sin(angle),-arcRadius*MathF.Cos(angle),0);
            }).ToArray();
            Route(name+"_arc_"+sign,arc,radius);
        }
        Route(name+"_return",new[] {top,locations["return_merge"]},radius);
    }
    Route("hot_outlet",new[] {locations["return_merge"],locations["outlet"]},header);
    Route("high_point_bleed",new[] {locations["return_merge"],locations["bleed"]},bleedRadius);
    foreach (string key in new[] {"supply_fork","return_merge"})
    {
        using Voxels plenum=new BaseSphere(new LocalFrame(locations[key]+phase),header*1.2f).voxConstruct();
        water.BoolAdd(plenum);
    }
    object Export(Voxels field, string name)
    {
        using Mesh grid = new(field); int count=grid.nTriangleCount();
        if (count == 0) return new {filename=name+".stl",sha256=(string?)null,triangles=0,native_volume=(float?)null};
        using Mesh mesh=grid.mshCreateTransformed(Vector3.One,-phase);
        string path=Path.Combine(output,name+".stl");mesh.SaveToStlFile(path,Mesh.EStlUnit.MM);
        field.CalculateProperties(out float volume,out _); Require(float.IsFinite(volume),"Finite volume required");
        return new {filename=name+".stl",sha256=(string?)Sha(path),triangles=count,native_volume=(float?)volume};
    }
    using Mesh headMesh=Mesh.mshFromStlFile(Path.Combine(input,"head.stl"),Mesh.EStlUnit.MM,libSet:lib);
    using Mesh shifted=headMesh.mshCreateTransformed(Vector3.One,phase);
    using Voxels head=new(shifted);
    using Voxels core=head.voxOffset(-margin);
    using Voxels envelope=water.voxOffset(margin);
    using Voxels intrusion=water.voxBoolSubtract(core);
    var files=new[] {Export(water,"coolant-routing"),Export(envelope,"routing-plus-wall-margin"),Export(intrusion,"outside-eroded-head")};
    var conflicts=new List<object>();
    foreach(var p in parts.Where(p => p.GetProperty("name").GetString() != "head"))
    {
        using Mesh reference=Mesh.mshFromStlFile(Path.Combine(input,p.GetProperty("filename").GetString()!),Mesh.EStlUnit.MM,libSet:lib);
        using Mesh shiftedReference=reference.mshCreateTransformed(Vector3.One,phase);
        using Voxels component=new(shiftedReference);
        using Voxels overlap=envelope.voxBoolIntersect(component);
        using Mesh witness=new(overlap);
        overlap.CalculateProperties(out float volume,out _);
        conflicts.Add(new {name=p.GetProperty("name").GetString(),triangles=witness.nTriangleCount(),native_volume=volume});
    }
    foreach(var pin in pins) Require(Sha(pin.Key) == pin.Value,"Input changed during generation");
    var report=new {schema="m64-water-head-generation/v1",status="routing_only_integration_blocked",
        contract_sha256=pins[contractPath],input_manifest_sha256=pins[Path.Combine(input,"inputs.json")],
        head_stl_sha256=pins[Path.Combine(input,"head.stl")],voxel_scan_units=step,units=c.GetProperty("units").GetString(),
        assembly_sha256=Sha(typeof(WaterMarker).Assembly.Location),picogk_sha256=Sha(typeof(Library).Assembly.Location),
        native_version=Library.strVersion(),shape_kernel_revision="7b9097842446a28bb5d49203724622e594ce7510",
        paths,files,reference_wall_margin_conflicts=conflicts,diagnostic_wall_margin=margin,
        source_master_modified=false,material_removed=false,manufacturing_authorized=false,
        gas_oil_stud_spark_plug_domains_complete=false,pressure_boundary_qualified=false,
        thermal_simulation=false,structural_simulation=false};
    File.WriteAllText(Path.Combine(output,"generation.json"),JsonSerializer.Serialize(report,new JsonSerializerOptions {WriteIndented=true})+"\n");
    Library.UnregisterGlobalLibrary(); Console.WriteLine("Coolant routing exported; head unchanged, integration blocked pending independent interfaces");return 0;
}
catch(Exception error) {Console.Error.WriteLine(error.GetType().Name+": "+error.Message);return 1;}
class WaterMarker { }
