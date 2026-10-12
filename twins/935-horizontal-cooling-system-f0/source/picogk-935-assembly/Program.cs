using System.Numerics;
using System.Security.Cryptography;
using System.Text.Json;
using PicoGK;
using PicoGKCatalog;

if (args.Length != 3) throw new ArgumentException("Usage: case.json sha256 NEW_PRIVATE_OUTPUT");
string source = Path.GetFullPath(args[0]), output = Path.GetFullPath(args[2]);
string Hash(string path) { using var stream = File.OpenRead(path); return Convert.ToHexString(SHA256.HashData(stream)).ToLowerInvariant(); }
if (Hash(source) != args[1]) throw new InvalidDataException("Case hash mismatch");
if (Directory.Exists(output) || File.Exists(output)) throw new IOException("Use a new output directory");
bool privateOutput = false;
for (DirectoryInfo parent = new(output); parent != null; parent = parent.Parent)
{
    if (parent.LinkTarget != null) throw new IOException("Output ancestry must not contain symlinks");
    if (File.Exists(Path.Combine(parent.FullName,".git")) || Directory.Exists(Path.Combine(parent.FullName,".git")))
    { privateOutput = Path.GetRelativePath(parent.FullName,output).StartsWith("work"+Path.DirectorySeparatorChar); break; }
}
if (!privateOutput) throw new IOException("Private geometry must stay in ignored repository work/");
using var document = JsonDocument.Parse(File.ReadAllText(source)); var c = document.RootElement;
if (c.GetProperty("target").GetString() != "935" || c.GetProperty("engine_cylinders").GetInt32() != 6 ||
    c.GetProperty("scale_verified").GetBoolean() || c.GetProperty("assumptions").GetArrayLength() == 0)
    throw new InvalidDataException("Only explicit uncalibrated six-cylinder 935 hypotheses are accepted");
float Number(JsonElement v, float min, float max)
{
    float f = v.GetSingle(); if (!float.IsFinite(f) || f < min || f > max) throw new InvalidDataException("Finite bounded parameter required"); return f;
}
float voxel = Number(c.GetProperty("voxel_mm"),.3f,2f);
string stage = c.GetProperty("stage").GetString();
if (stage != "assembly" && stage != "rotor_only" || stage == "assembly" && voxel < .8f)
    throw new InvalidDataException("Bounded assembly or rotor-only resolution study required");
string centresPath = c.GetProperty("centres_path").GetString(), bladesPath = c.GetProperty("blades_path").GetString();
if (Hash(centresPath) != c.GetProperty("centres_sha256").GetString() || Hash(bladesPath) != c.GetProperty("blades_sha256").GetString() ||
    c.GetProperty("blade_reconstruction").GetString() != "nine_individually_observed_blades_with_missing_root_tip_hypotheses")
    throw new InvalidDataException("Native blade or centre proposal changed");
using var centreDocument = JsonDocument.Parse(File.ReadAllText(centresPath)); var layout = centreDocument.RootElement;
if (layout.GetProperty("classification").GetString() != "hypothesis" || layout.GetProperty("axis").GetString() != "Y" || layout.GetProperty("scale_verified").GetBoolean())
    throw new InvalidDataException("Prescribed hypothetical horizontal cylinder axes required");
var centres = layout.GetProperty("centres_mm").EnumerateArray().Select(r => r.EnumerateArray().Select(x=>Number(x,-400,400)).ToArray()).ToArray();
if (centres.Length != 6 || centres.Any(v=>v.Length != 3) ||
    centres.Where((v,i)=>v[0] != new[]{-115f,0,115}[i%3] || v[1] != (i<3 ? -190 : 190) || v[2] != -205).Any())
    throw new InvalidDataException("Six independent prescribed centres required; duplicates and other engine layouts rejected");
var imports = c.GetProperty("imports").EnumerateArray().ToArray();
if (imports.Length != 1 || imports[0].GetProperty("id").GetString() != "drive_observed" ||
    imports[0].GetProperty("classification").GetString() != "935_fan_drive_observed_open_mesh")
    throw new InvalidDataException("Only the observed 935 fan-drive mesh may be imported; no engine scan import");
var drive = imports[0]; string drivePath = drive.GetProperty("path").GetString();
if (Hash(drivePath) != drive.GetProperty("sha256").GetString()) throw new InvalidDataException("Drive hash mismatch");
var rows = drive.GetProperty("source_to_assembly_mm").EnumerateArray().Select(r=>r.EnumerateArray().Select(x=>Number(x,-10000,10000)).ToArray()).ToArray();
if (rows.Length != 4 || rows.Any(r=>r.Length != 4) || !rows[3].SequenceEqual(new[]{0f,0,0,1})) throw new InvalidDataException("Affine column-vector matrix required");
Vector3[] columns = Enumerable.Range(0,3).Select(i=>new Vector3(rows[0][i],rows[1][i],rows[2][i])).ToArray();
if (columns.Any(v=>MathF.Abs(v.Length()-1)>1e-5f) || MathF.Abs(Vector3.Dot(columns[0],columns[1]))>1e-5f ||
    MathF.Abs(Vector3.Dot(columns[0],columns[2]))>1e-5f || MathF.Abs(Vector3.Dot(columns[1],columns[2]))>1e-5f ||
    Vector3.Dot(Vector3.Cross(columns[0],columns[1]),columns[2]) <= 0) throw new InvalidDataException("Proper rigid drive pose required");
Matrix4x4 transform = new(rows[0][0],rows[1][0],rows[2][0],0,rows[0][1],rows[1][1],rows[2][1],0,
    rows[0][2],rows[1][2],rows[2][2],0,rows[0][3],rows[1][3],rows[2][3],1);
var r = c.GetProperty("rotor");
float radius = Number(r.GetProperty("cup_radius_mm"),70,110), bore = Number(r.GetProperty("bore_radius_mm"),5,20);
float boss = Number(r.GetProperty("boss_radius_mm"),21,40), wall = Number(r.GetProperty("wall_mm"),3,8), back = Number(r.GetProperty("back_mm"),3,8);
float z0 = Number(r.GetProperty("z0_mm"),-40,-15), z1 = Number(r.GetProperty("z1_mm"),15,40), tip = Number(r.GetProperty("tip_radius_mm"),130,147);
if (bore >= boss || boss >= radius-wall || Math.Min(wall,back) < 3*voxel) throw new InvalidDataException("Resolved cup walls and ordered radii required");
Vector3 passageCentre = new(), passageHalf = new();
if (stage == "assembly")
{
    var passage = c.GetProperty("shroud").GetProperty("drive_passage");
    if (passage.GetProperty("classification").GetString() != "hypothesis") throw new InvalidDataException("Unqualified drive passage must remain a hypothesis");
    var pc = passage.GetProperty("centre_mm").EnumerateArray().Select(v=>Number(v,-400,400)).ToArray();
    var ph = passage.GetProperty("half_mm").EnumerateArray().Select(v=>Number(v,10,150)).ToArray();
    if (pc.Length != 3 || ph.Length != 3) throw new InvalidDataException("Three-dimensional passage box required");
    passageCentre = new(pc[0],pc[1],pc[2]); passageHalf = new(ph[0],ph[1],ph[2]);
}
Directory.CreateDirectory(output);
if (!OperatingSystem.IsWindows()) File.SetUnixFileMode(output,UnixFileMode.UserRead|UnixFileMode.UserWrite|UnixFileMode.UserExecute);
File.Copy(source,Path.Combine(output,"case.json"));
using Library library = new(voxel);
using Mesh assembled = new(library), engine = new(library);
var records = new List<object>(); var engineParts = new List<object>();
void Store(string id, Mesh mesh, string classification)
{
    using Mesh retained = new(library); int removed = 0;
    if (id == "rotor_candidate")
    {
        for (int i=0;i<mesh.nTriangleCount();i++)
        {
            mesh.GetTriangle(i,out Vector3 a,out Vector3 b,out Vector3 c);
            double ux=(double)b.X-a.X,uy=(double)b.Y-a.Y,uz=(double)b.Z-a.Z;
            double vx=(double)c.X-a.X,vy=(double)c.Y-a.Y,vz=(double)c.Z-a.Z;
            if (uy*vz-uz*vy == 0 && uz*vx-ux*vz == 0 && ux*vy-uy*vx == 0) { removed++; continue; }
            retained.nAddTriangle(a,b,c);
        }
        if (removed > 100) throw new InvalidDataException("Unexpected number of exactly zero-area native triangles");
        if (removed > 0) mesh.SaveToStlFile(Path.Combine(output,id+"-unfiltered.stl"));
        mesh = retained;
    }
    string file = id+".stl"; mesh.SaveToStlFile(Path.Combine(output,file)); assembled.Append(mesh);
    var box = mesh.oBoundingBox();
    if (mesh.nTriangleCount() == 0 || mesh.nTriangleCount() > (stage == "rotor_only" ? 8000000 : 5000000)) throw new InvalidDataException("Bounded nonempty mesh required");
    records.Add(new {id,file,classification,triangles=mesh.nTriangleCount(),zero_area_triangles_removed=removed,sha256=Hash(Path.Combine(output,file)),
        bounds_mm=new[]{new[]{box.vecMin.X,box.vecMin.Y,box.vecMin.Z},new[]{box.vecMax.X,box.vecMax.Y,box.vecMax.Z}}});
}
void EnginePart(string id, Voxels field, object parameters)
{
    using Mesh mesh = field.mshAsMesh(); string file = id+".stl"; mesh.SaveToStlFile(Path.Combine(output,file)); engine.Append(mesh);
    engineParts.Add(new {id,file,classification="935_engine_packaging_hypothesis_not_reconstructed_material",parameters,
        triangles=mesh.nTriangleCount(),sha256=Hash(Path.Combine(output,file))});
}
if (stage == "assembly")
{
using (Voxels crankcase = Sdf.Vox(library,p=>Sdf.Box(p,new Vector3(0,0,-275),new Vector3(235,115,65)),new Vector3(-240,-120,-345),new Vector3(240,120,-205)))
    EnginePart("crankcase_envelope",crankcase,new {centre=new[]{0,0,-275},half=new[]{235,115,65}});
for (int i=0;i<centres.Length;i++)
{
    Vector3 centre = new(centres[i][0],centres[i][1],centres[i][2]); int bank=i<3 ? -1 : 1;
    using Lattice cylinder = new(library);
    cylinder.AddBeam(new Vector3(centre.X,bank*120,centre.Z),new Vector3(centre.X,bank*265,centre.Z),62,62,false);
    foreach (float y in new[]{135f,155,175,195,215,235,255})
        cylinder.AddBeam(new Vector3(centre.X,bank*(y-3),centre.Z),new Vector3(centre.X,bank*(y+3),centre.Z),70,70,false);
    using (Voxels field = new(cylinder)) EnginePart($"cylinder_{i+1}",field,new {centre=centres[i],axis=new[]{0,bank,0},outer_radius=62,fin_radius=70});
    Vector3 headCentre = new(centre.X,bank*305,-195), headHalf = new(40,40,65);
    using (Voxels head = Sdf.Vox(library,p=>Sdf.Box(p,headCentre,headHalf),headCentre-headHalf-new Vector3(4),headCentre+headHalf+new Vector3(4)))
        EnginePart($"head_{i+1}_envelope",head,new {centre=new[]{headCentre.X,headCentre.Y,headCentre.Z},half=new[]{40,40,65}});
}
Store("engine_context",engine,"PicoGK_935_six_cylinder_packaging_hypothesis_no_917_geometry");
}
using Mesh bladeMesh = Mesh.mshFromStlFile(bladesPath,Mesh.EStlUnit.MM,libSet:library);
using Voxels rotor = new(bladeMesh);
using (Voxels cup = Sdf.Vox(library,p=>MathF.Max(MathF.Min(Sdf.CylZ(p,0,0,radius,z0,z1),Sdf.CylZ(p,0,0,boss,z0,z1)),
    -MathF.Min(Sdf.CylZ(p,0,0,radius-wall,z0+back,z1+4),Sdf.CylZ(p,0,0,bore,z0-4,z1+4))),
    new Vector3(-radius-4,-radius-4,z0-4),new Vector3(radius+4,radius+4,z1+4)))
    rotor.BoolAdd(cup);
// Keep the central boss while hollowing the cup; its bore remains a hypothesis.
using (Voxels bossField = Sdf.Vox(library,p=>MathF.Max(Sdf.CylZ(p,0,0,boss,z0,z1),-Sdf.CylZ(p,0,0,bore,z0-4,z1+4)),
    new Vector3(-boss-4,-boss-4,z0-4),new Vector3(boss+4,boss+4,z1+4))) rotor.BoolAdd(bossField);
using (Voxels crop = Sdf.Vox(library,p=>Sdf.CylZ(p,0,0,tip,z0-4,40),new Vector3(-tip-4,-tip-4,z0-8),new Vector3(tip+4,tip+4,44))) rotor.BoolIntersect(crop);
rotor.CalculateProperties(out float rotorVolume,out _);
if (!float.IsFinite(rotorVolume) || rotorVolume <= 0) throw new InvalidDataException("Positive native rotor volume required");
using (Mesh mesh = rotor.mshAsMesh()) Store("rotor_candidate",mesh,"PicoGK_nine_observed_blades_with_missing_root_tip_and_hub_hypotheses");
if (stage == "assembly")
{
using Mesh originalDrive = Mesh.mshFromStlFile(drivePath,Mesh.EStlUnit.MM,libSet:library);
if (originalDrive.nTriangleCount()>5000000) throw new InvalidDataException("Drive import exceeds resources");
using (Mesh placed = originalDrive.mshCreateTransformed(transform)) Store("drive_observed",placed,"935_fan_drive_observed_open_mesh_unresolved_datums");
float Inner(float z) => z <= 40 ? 150 : 150+(z-40)*20/35;
float Admission(Vector3 p) => MathF.Max(Sdf.EllipseLoftZ(p,z=>(Inner(z)+4,Inner(z)+4),-30,75),
    -Sdf.EllipseLoftZ(p,z=>(Inner(Math.Clamp(z,-30,75)),Inner(Math.Clamp(z,-30,75))),-35,80));
// shortcut: a designed open plenum envelope, replace with measured 935 outlet geometry before CFD.
float Plenum(Vector3 p)
{
    float z = Math.Clamp(p.Z,-110,-25), f=(z+110)/85, a=250-100*f, b=410-260*f;
    float rho=MathF.Pow(MathF.Pow(MathF.Abs(p.X)/a,4)+MathF.Pow(MathF.Abs(p.Y)/b,4),.25f);
    float inner=(rho-1)*MathF.Min(a,b);
    return MathF.Max(MathF.Max(inner-4,-inner),MathF.Max(-110-p.Z,p.Z+25));
}
using (Voxels hood = Sdf.Vox(library,p=>MathF.Min(Admission(p),Plenum(p)),new Vector3(-260,-420,-115),new Vector3(260,420,80)))
{
    using Voxels passage = Sdf.Vox(library,p=>Sdf.Box(p,passageCentre,passageHalf),passageCentre-passageHalf-new Vector3(4),passageCentre+passageHalf+new Vector3(4));
    hood.BoolSubtract(passage);
    using Mesh mesh = hood.mshAsMesh(); Store("provisional_shroud",mesh,"PicoGK_935_admission_and_six_cylinder_distribution_envelope_unverified");
}
}
if (Hash(source)!=args[1] || Hash(bladesPath)!=c.GetProperty("blades_sha256").GetString() || Hash(drivePath)!=drive.GetProperty("sha256").GetString() || Hash(centresPath)!=c.GetProperty("centres_sha256").GetString())
    throw new InvalidDataException("Input changed during generation");
assembled.SaveToStlFile(Path.Combine(output,"assembly-inspection.stl"));
File.WriteAllText(Path.Combine(output,"receipt.json"),JsonSerializer.Serialize(new {
    status="PicoGK_inspection_assembly_not_verified_installation",stage,case_sha256=args[1],target="935",engine_cylinders=6,
    engine_context_family="935_six_cylinder_packaging_hypothesis_not_exact_engine",engine_parts=engineParts,components=records,
    assembly_sha256=Hash(Path.Combine(output,"assembly-inspection.stl")),voxel_mm=voxel,rotor_volume_mm3_hypothesis=rotorVolume,
    geometry_creation_route="PicoGK section loft, Mesh, Lattice, implicit Voxels and native booleans; no FreeCAD engine or rotor input",
    runtime=new {name=Library.strName(),version=Library.strVersion(),build=Library.strBuildInfo()},
    scale_verified=false,interfaces_verified=false,mechanism_dynamics_validated=false,historical_installation_verified=false,
    manufacturing_authorized=false,physical_validation=false
},new JsonSerializerOptions{WriteIndented=true})+"\n");
Console.WriteLine($"935 only: {engineParts.Count} engine envelope parts, six cylinders; {assembled.nTriangleCount()} triangles");
