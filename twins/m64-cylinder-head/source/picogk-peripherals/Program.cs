using System.Diagnostics;
using System.Globalization;
using System.Numerics;
using System.Security.Cryptography;
using System.Text.Json;
using PicoGK;
using PicoGKCatalog;

if(args.Length==1&&args[0]=="--self-test"){Design.Check();Console.WriteLine("Peripheral self-checks passed");return 0;}
if(args.Length!=3||!float.TryParse(args[2],NumberStyles.Float,CultureInfo.InvariantCulture,out float h)||(h!=.4f&&h!=.2f))
{Console.Error.WriteLine("Usage: Peripherals INPUT_DIR NEW_OUTPUT_DIR 0.4_OR_0.2");return 2;}
string input=Path.GetFullPath(args[0]),output=Path.GetFullPath(args[1]);
if(Directory.Exists(output)||File.Exists(output))return 2;
string Sha(string path){using var f=File.OpenRead(path);return Convert.ToHexString(SHA256.HashData(f)).ToLowerInvariant();}
var pins=new Dictionary<string,string>();
void Pin(string path,string expected)
{
    if(!File.Exists(path)||(File.GetAttributes(path)&FileAttributes.ReparsePoint)!=0||Sha(path)!=expected)
        throw new InvalidDataException("Input hash or type mismatch: "+Path.GetFileName(path));
    pins.Add(path,expected);
}
var watch=Stopwatch.StartNew();
try
{
    string manifest=Path.Combine(input,"inputs.json");Pin(manifest,Sha(manifest));
    using var doc=JsonDocument.Parse(File.ReadAllText(manifest));var data=doc.RootElement;
    var exact=new Dictionary<string,string>{["head"]="9c40df1642d5eb47a3c1a1aae68c761b23b77e3f7e02e0818294e88ee0322598",
        ["module"]="fac380b277add2e3d265d7fa8265baeb0ce460b9f69075730d14ece555e76a76",
        ["registration"]="ca2d8656f343f5e61d124d511e6a446190b24fb010ef484ce3c8bc5fb8bb3eb2"};
    if(data.GetProperty("schema").GetString()!="m64-peripheral-inputs/v1"||
       data.GetProperty("manufacturing_authorized").GetBoolean()||data.GetProperty("source_master_modified").GetBoolean()||
       !data.GetProperty("module_transform_applied_once").GetBoolean()||!data.GetProperty("source_files_unchanged").GetBoolean()||
       data.GetProperty("unit").GetString()!="uncalibrated_scan_unit_assumed_mm"||
       exact.Any(k=>data.GetProperty("source_sha256").GetProperty(k.Key).GetString()!=k.Value))
        throw new InvalidDataException("Pinned research input required");
    string[] names=["intake_1","intake_2","exhaust_1","exhaust_2"];
    var inputs=data.GetProperty("parts").EnumerateArray().ToDictionary(r=>r.GetProperty("name").GetString()!);
    var expected=names.SelectMany(n=>new[]{n+"_valve",n+"_seat",n+"_guide"}).Append("head").ToHashSet();
    if(!expected.SetEquals(inputs.Keys))throw new InvalidDataException("Thirteen retained parts required");
    foreach(var item in inputs)
    {
        if(item.Value.GetProperty("filename").GetString()!=item.Key+".stl")throw new InvalidDataException("Local STL filename required");
        Pin(Path.Combine(input,item.Key+".stl"),item.Value.GetProperty("sha256").GetString()!);
    }
    var axes=data.GetProperty("axes").EnumerateArray().ToDictionary(r=>r.GetProperty("name").GetString()!);
    if(!names.ToHashSet().SetEquals(axes.Keys))throw new InvalidDataException("Four distinct axes required");
    Vector3 Vector(JsonElement a){float[] v=a.EnumerateArray().Select(e=>e.GetSingle()).ToArray();
        if(v.Length!=3||v.Any(x=>!float.IsFinite(x)))throw new InvalidDataException("Finite three-vector required");return new(v[0],v[1],v[2]);}
    foreach(string name in names)
    {
        var a=axes[name];int sign=name.StartsWith("intake")?1:-1;
        if(Vector3.Distance(Vector(a.GetProperty("origin")),new(name.EndsWith("1")?-22.5f:22.5f,sign==1?18:-23.5f,3))>1e-5f||
           Vector3.Distance(Vector(a.GetProperty("direction")),new(0,sign*.13917310096006544f,.9902680687415704f))>1e-6f)
            throw new InvalidDataException("Retained registered axis required");
    }
    Design.Check();Directory.CreateDirectory(output);
    using Library lib=new(h);
    var fields=new List<(string Name,string Role,Voxels Field)>();
    var exports=new List<object>();
    void Guard(){if(watch.Elapsed.TotalSeconds>600)throw new TimeoutException("600 second native budget exceeded");}
    Voxels Read(string name){Guard();using Mesh mesh=Mesh.mshFromStlFile(Path.Combine(input,name+".stl"),Mesh.EStlUnit.MM,libSet:lib);return new(mesh);}
    void Export(string name,string role,Voxels field,bool reference=false)
    {
        Guard();field.CalculateProperties(out float volume,out BBox3 box);
        if(!float.IsFinite(volume)||volume<=0)throw new InvalidDataException("Empty or invalid part");
        string? digest=null;int? triangles=null;
        if(!reference){using Mesh mesh=new(field);string path=Path.Combine(output,name+".stl");mesh.SaveToStlFile(path,Mesh.EStlUnit.MM);digest=Sha(path);triangles=mesh.nTriangleCount();}
        fields.Add((name,role,field));
        exports.Add(new{name,role,reference,filename=name+".stl",sha256=digest??inputs[name].GetProperty("sha256").GetString(),triangles,
            voxel_volume=volume,low=new[]{box.vecMin.X,box.vecMin.Y,box.vecMin.Z},high=new[]{box.vecMax.X,box.vecMax.Y,box.vecMax.Z},
            transform="identity_already_registered",manufacturing_authorized=false});
        Console.WriteLine(JsonSerializer.Serialize(new{part=name,role,volume,seconds=watch.Elapsed.TotalSeconds}));
    }
    Export("head","head",Read("head"),true);
    foreach(string name in names)
    {
        Vector3 o=Vector(axes[name].GetProperty("origin")),d=Vector(axes[name].GetProperty("direction"));
        foreach(string role in new[]{"seat","guide"})Export(name+"_"+role,role,Read(name+"_"+role),true);
        using Voxels valve=Read(name+"_valve");
        using Voxels extension=Sdf.Vox(lib,p=>Es.Cyl(p,o+81*d,o+Design.Tip*d,3),
            Vector3.Min(o+81*d,o+Design.Tip*d)-new Vector3(4),Vector3.Max(o+81*d,o+Design.Tip*d)+new Vector3(4));
        Export(name+"_extended_valve","extended_valve_hypothesis",valve.voxBoolAdd(extension));
        foreach(var ring in new[]{("spring_seat","spring_seat_hypothesis",Design.Seat-3,Design.Seat,7.75f,16f),
                                  ("retainer","retainer_without_keeper",Design.Retainer,Design.Retainer+3,3.2f,16f),
                                  ("spring_space","keepout_not_spring",Design.Seat,Design.Retainer,7.75f,15f)})
        {
            Vector3 first=o+ring.Item3*d,last=o+ring.Item4*d;
            Export(name+"_"+ring.Item1,ring.Item2,Sdf.Vox(lib,p=>Design.Ring(p,o,d,ring.Item3,ring.Item4,ring.Item5,ring.Item6),
                Vector3.Min(first,last)-new Vector3(18),Vector3.Max(first,last)+new Vector3(18)));
        }
    }
    foreach(var cover in new[]{("intake_cover",31f),("exhaust_cover",-36.5f)})
        Export(cover.Item1,"veined_cover_without_mounts",Sdf.Vox(lib,p=>Design.Cover(p,cover.Item2),new(-46,cover.Item2-23,85),new(46,cover.Item2+23,132)));
    Export("oil_distributor","branched_oil_hypothesis",Sdf.Vox(lib,Design.OilWall,new(-56,-19,84),new(29,19,126)));
    using(Voxels fluid=Sdf.Vox(lib,Design.OilFluid,new(-56,-19,84),new(29,19,126)))
    {using Mesh mesh=new(fluid);mesh.SaveToStlFile(Path.Combine(output,"oil-fluid-diagnostic.stl"),Mesh.EStlUnit.MM);}
    // Broad phase then native intersections; no contact is silently waived or hidden by cutting the master.
    var collisions=new List<object>();var unresolved=new List<object>();int pairs=0,nativePairs=0;
    for(int i=0;i<fields.Count;i++)for(int j=i+1;j<fields.Count;j++)
    {
        Guard();var a=fields[i];var b=fields[j];
        if(new[]{"head","seat","guide"}.Contains(a.Role)&&new[]{"head","seat","guide"}.Contains(b.Role))continue;
        pairs++;BBox3 ba=a.Field.oCalculateBoundingBox(),bb=b.Field.oCalculateBoundingBox();
        Vector3 lo=Vector3.Max(ba.vecMin,bb.vecMin),hi=Vector3.Min(ba.vecMax,bb.vecMax);
        if(lo.X>=hi.X||lo.Y>=hi.Y||lo.Z>=hi.Z)continue;
        nativePairs++;using Voxels common=a.Field.voxBoolIntersect(b.Field);common.CalculateProperties(out float volume,out _);
        if(!float.IsFinite(volume))throw new InvalidDataException("Non-finite intersection volume: "+a.Name+" / "+b.Name);
        if(volume<0)unresolved.Add(new{first=a.Name,second=b.Name,raw_native_volume=volume,reason="negative_native_volume_not_clamped_to_zero"});
        if(volume>0)collisions.Add(new{first=a.Name,second=b.Name,voxel_intersection_volume=volume,
            includes_spring_keepout=a.Role=="keepout_not_spring"||b.Role=="keepout_not_spring"});
    }
    foreach(var pin in pins)if(Sha(pin.Key)!=pin.Value)throw new InvalidDataException("Input changed during generation");
    var report=new{schema="m64-picogk-peripherals/v1",status="research_assembly_incomplete_not_released",voxel_world_units=h,
        inputs_sha256=pins[manifest],source_sha256=exact,program_sha256=Sha(typeof(Design).Assembly.Location),
        picogk_sha256=Sha(typeof(Library).Assembly.Location),native_version=Library.strVersion(),native_build=Library.strBuildInfo(),
        units="uncalibrated_scan_unit_assumed_mm",source_master_modified=false,source_files_unchanged=true,
        original_valves_preserved_as_references=true,extended_valves_are_voxelized_variants_not_exact_functional_surfaces=true,
        assembly_complete=false,manufacturing_authorized=false,dynamics_validated=false,thermal_validated=false,
        spring_installed_height=40.4,spring_bind_height_nominal=22.7,stem_tip_variant=Design.Tip,
        supplier_keepers_or_spring_wire_modeled=false,spring_nominal_bind_reserve=new{intake=6.2,exhaust=8.1},
        oil_leaf_radius=Design.Radius(1),oil_fork_radius=Design.Radius(2),oil_root_radius=Design.Radius(4),
        oil_nominal_wall=Design.Wall,minimum_wall_proved=false,oil_hydraulics_validated=false,
        parts=exports,collision_screen=new{pairs,nativePairs,positive_intersections=collisions,unresolved_intersections=unresolved,
            all_native_volumes_nonnegative=unresolved.Count==0,
            reference_reference_pairs_excluded=true,closed_position_only=true,physical_clearance_proved=false},
        oil_fluid_diagnostic_sha256=Sha(Path.Combine(output,"oil-fluid-diagnostic.stl")),
        missing=new[]{"qualified_engine_interfaces_and_variant","carrier_and_mounts","camshafts_and_drive","rockers_followers_and_axes",
            "supplier_springs_keepers_seals","plug_sealing_interfaces","intake_exhaust_flanges","oil_supply_return_and_nozzles",
            "cover_bolts_and_gaskets","material_hot_fatigue_and_LPBF_qualification"},elapsed_seconds=watch.Elapsed.TotalSeconds};
    File.WriteAllText(Path.Combine(output,"assembly.json"),JsonSerializer.Serialize(report,new JsonSerializerOptions{WriteIndented=true}));
    foreach(var field in fields)field.Field.Dispose();
    Console.WriteLine(JsonSerializer.Serialize(new{report.status,parts=exports.Count,intersections=collisions.Count,report.elapsed_seconds}));return 0;
}
catch(Exception error)
{
    if(Directory.Exists(output))File.WriteAllText(Path.Combine(output,"FAILED.json"),JsonSerializer.Serialize(new{error=error.ToString(),manufacturing_authorized=false}));
    Console.Error.WriteLine(error);return 1;
}
