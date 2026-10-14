using System.Globalization;
using System.Numerics;
using System.Security.Cryptography;
using System.Text.Json;
using PicoGK;
using PicoGKCatalog;

if (args.Length != 4) throw new ArgumentException("Usage: Head config.json sha256 voxel_mm new_work_output");
string Hash(string path) { using var f=File.OpenRead(path); return Convert.ToHexString(SHA256.HashData(f)).ToLowerInvariant(); }
string input=Path.GetFullPath(args[0]), output=Path.GetFullPath(args[3]);
float grid=float.Parse(args[2],CultureInfo.InvariantCulture);
if (Hash(input)!=args[1] || grid is not (1f or .5f) || Path.Exists(output)) throw new ArgumentException("Input hash, grid or output rejected");
bool work=false;
for (DirectoryInfo? p=new(output);p!=null;p=p.Parent)
    if (File.Exists(Path.Combine(p.FullName,".git")) || Directory.Exists(Path.Combine(p.FullName,".git")))
    { work=Path.GetRelativePath(p.FullName,output).StartsWith("work"+Path.DirectorySeparatorChar,StringComparison.Ordinal);break; }
if (!work) throw new IOException("Output must stay under ignored work/");
using var doc=JsonDocument.Parse(File.ReadAllText(input));
var cfg=doc.RootElement;
if (cfg.GetProperty("classification").GetString()!="917_bionic_head_design_candidate_no_physical_release" ||
    cfg.GetProperty("manufacturing_authorized").GetBoolean() || cfg.GetProperty("engine_start_authorized").GetBoolean())
    throw new InvalidDataException("Physical promotion rejected");
float D(string name) { float v=cfg.GetProperty(name).GetSingle(); if(!float.IsFinite(v)||v<=0||v>500)throw new InvalidDataException(name);return v; }
float x=D("pair_half_pitch_mm"), y=D("row_offset_mm"), face=D("face_z_mm"), roof=D("roof_height_mm"), wall=D("port_wall_mm");
float alpha=8*MathF.PI/180, si=MathF.Sin(alpha), co=MathF.Cos(alpha);
float camS=116+2+.1f+18+20+8, camZ=face+camS*co, camY=y+camS*si;
Directory.CreateDirectory(output);
using Library lib=new(grid);
var exports=new Dictionary<string,object>();
Voxels Cylinder(Vector3 a,Vector3 b,float r) { using Lattice l=new(lib);l.AddBeam(a,b,r,r,false);return new Voxels(l); }
Voxels Ring(Vector3 a,Vector3 b,float outer,float inner)
{ var v=Cylinder(a,b,outer);Vector3 n=Vector3.Normalize(b-a);using var hole=Cylinder(a-n*3,b+n*3,inner);v.BoolSubtract(hole);return v; }
Voxels Box(Vector3 c,Vector3 h)=>Sdf.Vox(lib,p=>Sdf.Box(p,c,h),c-h-new Vector3(3*grid),c+h+new Vector3(3*grid));
void Export(Voxels v,string name)
{
    if(v.bIsEmpty())throw new InvalidDataException("Empty field: "+name);
    using Mesh m=new(v);string stl=Path.Combine(output,name+".stl"),vdb=Path.Combine(output,name+".vdb");
    m.SaveToStlFile(stl);v.SaveToVdbFile(vdb);v.CalculateProperties(out float volume,out _);
    exports[name]=new { stl_sha256=Hash(stl),vdb_sha256=Hash(vdb),triangles=m.nTriangleCount(),native_resampled_volume_mm3=volume };
    Console.WriteLine("EXPORT "+name);
}
Vector3[] centres=[new(-x,y,face),new(x,y,face),new(-x,-y,face),new(x,-y,face)];
Vector3[] axes=[new(0,si,co),new(0,si,co),new(0,-si,co),new(0,-si,co)];
ValveDims[] dims=Enumerable.Range(0,4).Select(i=>new ValveDims(D(i<2?"intake_diameter_mm":"exhaust_diameter_mm")/2,1.1f,1.5f,3,116,3,.5f,1.6f,6,.5f)).ToArray();
Voxels LocalField(int i,Func<float,float,float> f,float radial,float s0,float s1)
{
    Vector3 c=centres[i], n=axes[i];
    Vector3 min=Vector3.Min(c+n*s0,c+n*s1)-new Vector3(radial+3*grid),max=Vector3.Max(c+n*s0,c+n*s1)+new Vector3(radial+3*grid);
    return Sdf.Vox(lib,p=>{Vector3 d=p-c;float s=Vector3.Dot(d,n);return f((d-n*s).Length(),s);},min,max);
}
var chamber=Sdf.Vox(lib,p=>MathF.Max(MathF.Max(new Vector2(p.X,p.Y).Length()-42.5f,-3-p.Z),p.Z-(roof-MathF.Abs(p.Y)*MathF.Tan(alpha))),
    new(-44,-44,-4),new(44,44,roof+1));
var gas=chamber.voxOffset(0);
var pressure=Cylinder(new(0,0,0),new(0,0,23),53);
var seatHoles=new List<Voxels>();var guideHoles=new List<Voxels>();
for(int i=0;i<4;i++)
{
    int component=i*3+1;Vector3 c=centres[i],n=axes[i];ValveDims v=dims[i];
    using var valve=LocalField(i,(r,s)=>ValveShape.Profile(r,s,v),v.HeadR,-1,v.Length+1);
    Export(valve,$"head_component_{component:00}");
    var seat=LocalField(i,(r,s)=> {
        float inner=s<=2.6f ? v.HeadR+1.1f-s : .86f*v.HeadR;
        return MathF.Max(MathF.Max(r-(v.HeadR+1.5f),MathF.Max(.6f-s,s-7.6f)),inner-r);
    },v.HeadR+2,0,9);
    Export(seat,$"head_component_{component+1:00}");seat.Dispose();
    var seatHole=Cylinder(c+n*.5f,c+n*7.7f,v.HeadR+1.5f);seatHoles.Add(seatHole);
    using var guide=Ring(c+n*28,c+n*60,6.5f,3.1f);Export(guide,$"head_component_{component+2:00}");
    var guideHole=Cylinder(c+n*25,c+n*61,6.5f);guideHoles.Add(guideHole);
    using var guideBoss=Cylinder(c+n*26,c+n*60,9);pressure.BoolAdd(guideBoss);
    float sign=i<2?1:-1, throat=.86f*v.HeadR, mouth=throat*MathF.Sqrt(2)*1.03f;
    var a=c+n*2.1f;var b=a+n*22;var end=new Vector3(0,sign*100,35);var control=new Vector3(0,sign*72,35);
    using Lattice path=new(lib);
    Vector3 last=a;float lastR=throat;
    for(int k=1;k<=40;k++)
    {
        float t=k/40f;Vector3 next=Es.Cubic(a,b,control,end,t);float r=throat+(mouth-throat)*t;
        path.AddBeam(last,next,lastR,r,true);last=next;lastR=r;
    }
    using var flow=new Voxels(path);
    using var startClip=Sdf.Vox(lib,p=>2.0f-Vector3.Dot(p-c,n),new(-65,-135,-10),new(65,135,80));flow.BoolIntersect(startClip);
    using var bossKeep=Cylinder(c+n*26,c+n*60,9);flow.BoolSubtract(bossKeep);
    using var outer=flow.voxOffset(wall);pressure.BoolAdd(outer);gas.BoolAdd(flow);
    using var flange=Cylinder(new(0,sign*98,35),new(0,sign*104,35),mouth+wall+3);pressure.BoolAdd(flange);
    // Re-cut the straight, flat port mouth after the rounded curve construction.
    using var outlet=Cylinder(new(0,sign*94,35),new(0,sign*112,35),mouth);gas.BoolAdd(outlet);
}
using Lattice oilPath=new(lib);
Vector3 Oil(float deg,float r=47)=>new(r*MathF.Cos(deg*MathF.PI/180),r*MathF.Sin(deg*MathF.PI/180),5);
Vector3 oilLast=Oil(-140);
oilPath.AddBeam(Oil(-140,61),oilLast,2.25f,2.25f,true);
for(int k=1;k<=70;k++){Vector3 next=Oil(-140+k*4);oilPath.AddBeam(oilLast,next,2.25f,2.25f,true);oilLast=next;}
oilPath.AddBeam(oilLast,Oil(140,61),2.25f,2.25f,true);
using var oil=new Voxels(oilPath);
foreach(int sign in new[]{-1,1}){using var boss=Cylinder(Oil(sign*140,51),Oil(sign*140,61),5);pressure.BoolAdd(boss);}
using var sparkKeep=Cylinder(new(0,0,roof-2),new(0,0,32),10);pressure.BoolAdd(sparkKeep);
using var sparkHole=Cylinder(new(0,0,-4),new(0,0,40),5);
gas.BoolAdd(sparkHole);
var boltHoles=new List<Voxels>();
var dowelHoles=new List<Voxels>();
foreach(int sign in new[]{-1,1})
{
    float angle=sign*165*MathF.PI/180;Vector3 c=new(48*MathF.Cos(angle),48*MathF.Sin(angle),0);
    dowelHoles.Add(Cylinder(c-new Vector3(0,0,2),c+new Vector3(0,0,8.5f),3.2f));
}
foreach(int sx in new[]{-1,1})foreach(int sy in new[]{-1,1})
{
    Vector3 root=new(sx*39,sy*39,0);using var pad=Cylinder(root,root+new Vector3(0,0,26),8);pressure.BoolAdd(pad);
    boltHoles.Add(Cylinder(root-new Vector3(0,0,3),root+new Vector3(0,0,44),4.5f));
}
// Keep proposed fin and lattice cut planes away from exact grid coincidences.
for(int k=0;k<3;k++){using var fin=Ring(new(0,0,5.17f+k*6),new(0,0,7.17f+k*6),55,49);pressure.BoolAdd(fin);}
using var cutEnvelope=Box(new(0,0,35),new(55.5f,104,45));pressure.BoolIntersect(cutEnvelope);
foreach(var hole in seatHoles.Concat(guideHoles).Concat(boltHoles).Concat(dowelHoles))pressure.BoolSubtract(hole);
pressure.BoolSubtract(gas);pressure.BoolSubtract(oil);
Export(pressure,"pressure_envelope");
using var sideLeft=Box(new(-41.17f,0,42.13f),new(5.13f,24.83f,20.17f));
using var sideRight=Box(new(41.17f,0,42.13f),new(5.13f,24.83f,20.17f));
using Lattice carrierPaths=new(lib);
foreach(int sx in new[]{-1,1})foreach(int sy in new[]{-1,1})
{
    Vector3 root=new(sx*45,sy*39,34),tip=new(0,sy*camY,camZ-35),control=new(sx*46,sy*90,100),last=root;
    for(int k=1;k<=32;k++){float t=k/32f;Vector3 next=Sdf.Bezier(root,control,tip,t);float r=10*(1-t)+6*t;carrierPaths.AddBeam(last,next,r,r,true);last=next;}
}
foreach(int sign in new[]{-1,1})carrierPaths.AddBeam(new(0,sign*camY,camZ-35),new(0,sign*camY,camZ),6,6,true);
using var carrierArms=new Voxels(carrierPaths);
using var carrierReserve=carrierArms.voxOffset(1);
foreach(int sx in new[]{-1,1})foreach(int sy in new[]{-1,1})
{ using var padReserve=Cylinder(new(sx*39,sy*39,26),new(sx*39,sy*39,33),9);carrierReserve.BoolAdd(padReserve); }
using(var aboveJoint=Box(new(0,0,(26+camZ+30)/2),new(65,65,(camZ+30-26)/2)))carrierReserve.BoolIntersect(aboveJoint);
using Lattice ribPaths=new(lib);
for(int i=0;i<4;i++)
{
    Vector3 root=new(MathF.Sign(centres[i].X)*32,MathF.Sign(centres[i].Y)*25,18);
    Vector3 tip=centres[i]+axes[i]*54+new Vector3(MathF.Sign(centres[i].X)*11,0,0);
    Vector3 bend=new(root.X,root.Y,48),last=root;
    for(int k=1;k<=24;k++){float t=k/24f;Vector3 next=Sdf.Bezier(root,bend,tip,t);ribPaths.AddBeam(last,next,4.5f*(1-t)+3*t,4.5f*(1-t)+3*t,true);last=next;}
}
using var branches=new Voxels(ribPaths);
using var dense=pressure.voxBoolAdd(sideLeft);dense.BoolAdd(sideRight);dense.BoolAdd(branches);
dense.BoolSubtract(gas);dense.BoolSubtract(oil);
dense.BoolSubtract(carrierReserve);
foreach(var hole in seatHoles.Concat(guideHoles).Concat(boltHoles).Concat(dowelHoles))dense.BoolSubtract(hole);
Export(dense,"head_dense_reference");
foreach(float strut in new[]{2f,2.5f,3f})
{
    using var body=pressure.voxOffset(0);
    body.BoolAdd(branches);
    using var left=Sdf.LatticeIn(lib,sideLeft,10,strut);body.BoolAdd(left);
    using var right=Sdf.LatticeIn(lib,sideRight,10,strut);body.BoolAdd(right);
    body.BoolSubtract(gas);body.BoolSubtract(oil);
    body.BoolIntersect(cutEnvelope);body.BoolSubtract(carrierReserve);
    foreach(var hole in seatHoles.Concat(guideHoles).Concat(boltHoles).Concat(dowelHoles))body.BoolSubtract(hole);
    Export(body,"head_bionic_"+strut.ToString("0.0",CultureInfo.InvariantCulture).Replace('.','_'));
}
Export(gas,"gas_domain");Export(oil,"oil_domain");Export(chamber,"chamber_envelope");
// A declared inset witness checks separation; it is not the physical flow domain.
using(var gasInset=gas.voxOffset(-.5f))Export(gasInset,"gas_inset_screen_0_5mm");
using(var oilGuard=oil.voxOffset(2))Export(oilGuard,"oil_guard_2mm");
using(var plug=Cylinder(new(0,0,roof-2),new(0,0,33),5))Export(plug,"spark_plug");
var lengths=cfg.TryGetProperty("spring_lengths_mm",out var lengthsNode)?lengthsNode.EnumerateArray().Select(e=>e.GetSingle()).ToArray():new[]{44f};
for(int index=0;index<lengths.Length;index++)
foreach(var (family,r,wire,turns) in new[]{("outer_valve_spring",11f,2f,6), ("inner_valve_spring",6.8f,.9f,8)})
{
    float length=lengths[index];if(!float.IsFinite(length)||length<32||length>44)throw new InvalidDataException("Spring height rejected");
    using Lattice coil=new(lib);Vector3 last=new(r,0,wire);
    for(int k=1;k<=turns*64;k++){float t=k/(float)(turns*64),a=t*turns*MathF.Tau;Vector3 next=new(r*MathF.Cos(a),r*MathF.Sin(a),wire+(length-2*wire)*t);coil.AddBeam(last,next,wire,wire,true);last=next;}
    using var v=new Voxels(coil);Export(v,family+"_"+index);
}
foreach(var (name,r,inner,length) in new[]{("lower_spring_seat",14f,6.6f,2f),
    ("valve_stem_seal",6f,3.1f,6f)})
{ using var v=Ring(new(0,0,-length/2),new(0,0,length/2),r,inner);Export(v,name); }
using(var retainer=Sdf.Vox(lib,p=> {
    float r=new Vector2(p.X,p.Y).Length(),inner=4.7f-(p.Z-1)*MathF.Tan(alpha)+.05f;
    return MathF.Max(MathF.Max(r-14,MathF.Abs(p.Z)-2),inner-r);
},new(-15,-15,-3),new(15,15,3)))Export(retainer,"upper_spring_retainer");
using(var keeper=Sdf.Vox(lib,p=> {
    float r=new Vector2(p.X,p.Y).Length(),outer=4.7f-p.Z*MathF.Tan(alpha);
    return MathF.Max(MathF.Max(MathF.Max(r-outer,MathF.Abs(p.Z)-3),.15f-p.X),-ValveShape.Profile(r,p.Z+109,dims[0]));
},new(-1,-6,-4),new(6,6,4)))Export(keeper,"valve_keeper_half");
using(var shim=Cylinder(new(0,0,-2),new(0,0,2),3.5f))
{ using var recess=Cylinder(new(0,0,-3),Vector3.Zero,3.1f);shim.BoolSubtract(recess);Export(shim,"valve_shim"); }
using(var follower=Cylinder(new(0,0,0),new(0,0,7),3))
{
    using Lattice fork=new(lib);
    foreach(int sx in new[]{-1,1})
    {
        fork.AddBeam(new(sx*4,0,6),new(sx*6,0,18),2,2,true);
        using var lug=Ring(new(sx*6-1.5f,0,18),new(sx*6+1.5f,0,18),4.5f,3.3f);follower.BoolAdd(lug);
    }
    using var armsV=new Voxels(fork);follower.BoolAdd(armsV);Export(follower,"rocker");
}
using(var roller=Ring(new(-4,0,0),new(4,0,0),8,3.1f))Export(roller,"cam_roller");
using(var pin=Cylinder(new(-8,0,0),new(8,0,0),3))Export(pin,"cam_roller_pin");
using(var carrier=carrierArms.voxOffset(0))
{
    foreach(int sx in new[]{-1,1})foreach(int sy in new[]{-1,1})
    { using var pad=Ring(new(sx*39,sy*39,26),new(sx*39,sy*39,32),8,4.5f);carrier.BoolAdd(pad); }
    foreach(int sy in new[]{-1,1}){using var bearing=Ring(new(-6,sy*camY,camZ),new(6,sy*camY,camZ),15,9.25f);carrier.BoolAdd(bearing);}
    using var half=Box(new(0,0,(camZ+26)/2),new(57,70,(camZ-26)/2));carrier.BoolIntersect(half);
    using var bridge=Cylinder(new(0,-camY,camZ-15),new(0,camY,camZ-15),3);carrier.BoolAdd(bridge);
    foreach(int sign in new[]{-1,1})foreach(int side in new[]{-1,1})
    {
        Vector3 c=new(side*8,sign*camY+side*12,camZ);
        using var pad=Cylinder(c-new Vector3(0,0,10),c,3.5f);carrier.BoolAdd(pad);
        using var hole=Cylinder(c-new Vector3(0,0,12),c+new Vector3(0,0,12),2.1f);carrier.BoolSubtract(hole);
    }
    foreach(var h in boltHoles)carrier.BoolSubtract(h);
    foreach(int sx in new[]{-1,1})foreach(int sy in new[]{-1,1})
    {using var nutSpace=Cylinder(new(sx*39,sy*39,32),new(sx*39,sy*39,44),8.5f);carrier.BoolSubtract(nutSpace);}
    foreach(int sy in new[]{-1,1})
    {using var journal=Cylinder(new(-16,sy*camY,camZ),new(16,sy*camY,camZ),9.25f);carrier.BoolSubtract(journal);}
    Export(carrier,"rocker_carrier");
}
using(var cap2=Ring(new(-6,-camY,camZ),new(6,-camY,camZ),15,9.25f))
{
    using var other=Ring(new(-6,camY,camZ),new(6,camY,camZ),15,9.25f);cap2.BoolAdd(other);
    using var half=Box(new(0,0,camZ+25),new(55,60,25));cap2.BoolIntersect(half);
    using var bridge=Cylinder(new(0,-camY,camZ+15),new(0,camY,camZ+15),3);cap2.BoolAdd(bridge);
    foreach(int sign in new[]{-1,1})foreach(int side in new[]{-1,1})
    {
        Vector3 c=new(side*8,sign*camY+side*12,camZ);
        using var pad=Cylinder(c,c+new Vector3(0,0,10),3.5f);cap2.BoolAdd(pad);
        using var hole=Cylinder(c-new Vector3(0,0,12),c+new Vector3(0,0,12),2.1f);cap2.BoolSubtract(hole);
    }
    foreach(int sy in new[]{-1,1})
    {using var journal=Cylinder(new(-16,sy*camY,camZ),new(16,sy*camY,camZ),9.25f);cap2.BoolSubtract(journal);}
    Export(cap2,"cam_cap_bolted");
}
using(var capBolt=Cylinder(new(0,0,-12),new(0,0,12),2))Export(capBolt,"cam_cap_bolt");
using(var stud=Cylinder(new(0,0,-84.5f),new(0,0,84.5f),4))Export(stud,"head_stud");
using(var nut=Ring(new(0,0,-4),new(0,0,4),8,4.1f))Export(nut,"head_nut");
using(var dowel=Cylinder(new(0,0,-6),new(0,0,6),3))Export(dowel,"location_dowel");
using(var gasket=Ring(new(0,0,-1.25f),Vector3.Zero,47.5f,42.6f))
{foreach(var hole in dowelHoles)gasket.BoolSubtract(hole);Export(gasket,"head_gasket");}
using(var cover=Sdf.Vox(lib,p=>Sdf.RoundBox(p,new(0,0,(66+camZ+35)/2),new(56,76,(camZ+35-66)/2),6),new(-58,-78,64),new(58,78,camZ+37)))
{
    using var inside=Sdf.Vox(lib,p=>Sdf.RoundBox(p,new(0,0,(60+camZ+33)/2),new(54,74,(camZ+33-60)/2),4),new(-56,-76,58),new(56,76,camZ+35));
    cover.BoolSubtract(inside);
    foreach(int sign in new[]{-1,1}){using var journalExit=Cylinder(new(-60,sign*camY,camZ),new(60,sign*camY,camZ),10);cover.BoolSubtract(journalExit);}
    Export(cover,"valve_cover");
}
foreach(var h in seatHoles.Concat(guideHoles).Concat(boltHoles).Concat(dowelHoles))h.Dispose();
chamber.Dispose();gas.Dispose();pressure.Dispose();
if(Hash(input)!=args[1])throw new InvalidDataException("Configuration changed");
File.WriteAllText(Path.Combine(output,"receipt.json"),JsonSerializer.Serialize(new {
    classification="917_bionic_head_design_candidate_no_physical_release",config_sha256=args[1],voxel_mm=grid,kernel=Library.strVersion(),
    parts=exports,bionic_functions=new[]{"Sdf.Bezier","Sdf.LatticeIn","Lattice.AddBeam"},manufacturing_authorized=false,engine_start_authorized=false
},new JsonSerializerOptions{WriteIndented=true})+"\n");
