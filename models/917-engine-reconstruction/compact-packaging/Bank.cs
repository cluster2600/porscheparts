using System.Globalization;
using System.Numerics;
using System.Security.Cryptography;
using System.Text.Json;
using PicoGK;
using PicoGKCatalog;

if(args.Length!=4)throw new ArgumentException("Usage: Bank config sha256 voxel_mm new_work_output");
string Hash(string p){using var f=File.OpenRead(p);return Convert.ToHexString(SHA256.HashData(f)).ToLowerInvariant();}
string input=Path.GetFullPath(args[0]),output=Path.GetFullPath(args[3]);float grid=float.Parse(args[2],CultureInfo.InvariantCulture);
if(Hash(input)!=args[1]||grid is not (1f or .5f)||Path.Exists(output))throw new ArgumentException("Hash, grid or existing output rejected");
bool work=false;
for(DirectoryInfo? p=new(output);p!=null;p=p.Parent)if(File.Exists(Path.Combine(p.FullName,".git"))||Directory.Exists(Path.Combine(p.FullName,".git")))
 {work=Path.GetRelativePath(p.FullName,output).StartsWith("work"+Path.DirectorySeparatorChar,StringComparison.Ordinal);break;}
if(!work)throw new IOException("Output must stay under ignored work/");
using var doc=JsonDocument.Parse(File.ReadAllText(input));var root=doc.RootElement;
if(root.GetProperty("classification").GetString()!="917_longitudinal_bank_geometry_hypothesis"||root.GetProperty("manufacturing_authorized").GetBoolean()||root.GetProperty("engine_start_authorized").GetBoolean())throw new InvalidDataException("Physical release rejected");
float wall=root.GetProperty("wall_mm").GetSingle();if(wall is not (3f or 5f))throw new InvalidDataException("Unscreened wall variant");
Directory.CreateDirectory(output);using Library lib=new(grid);var records=new Dictionary<string,object>();
Voxels C(Vector3 a,Vector3 b,float r){using Lattice l=new(lib);l.AddBeam(a,b,r,r,false);return new Voxels(l);}
var source=root.GetProperty("drive_housing_vdb");string path=source.GetProperty("path").GetString()!;
if(Hash(path)!=source.GetProperty("sha256").GetString())throw new InvalidDataException("Housing field changed");
using Voxels housing=Voxels.voxFromVdbFile(lib,path);using var housingReserve=housing.voxOffset(1.5f);
using Lattice gearPaths=new(lib);
foreach(var g in root.GetProperty("gear_envelopes").EnumerateArray())gearPaths.AddBeam(new(g[0].GetSingle()-8.13f,g[1].GetSingle(),g[2].GetSingle()),new(g[0].GetSingle()+8.13f,g[1].GetSingle(),g[2].GetSingle()),g[3].GetSingle()+2.37f,g[3].GetSingle()+2.37f,false);
using var gearReserve=new Voxels(gearPaths);
void Export(Voxels v,string id)
{
 v.CalculateProperties(out float volume,out _);if(v.bIsEmpty()||!float.IsFinite(volume)||volume<=0)throw new InvalidDataException("Empty part "+id);
 using Mesh m=new(v);string stl=Path.Combine(output,id+".stl"),vdb=Path.Combine(output,id+".vdb");m.SaveToStlFile(stl);v.SaveToVdbFile(vdb);
 records[id]=new{stl_sha256=Hash(stl),vdb_sha256=Hash(vdb),triangles=m.nTriangleCount(),native_resampled_volume_mm3=volume};Console.WriteLine("EXPORT "+id);
}
var banks=root.GetProperty("banks").EnumerateArray().ToArray();
if(banks.Length!=2||banks.Select(b=>b.GetProperty("bank").GetInt32()).Order().SequenceEqual(new[]{-1,1})==false)throw new InvalidDataException("Both banks required");
foreach(var bank in banks)
{
 int sign=bank.GetProperty("bank").GetInt32();if(sign is not (-1 or 1))throw new InvalidDataException("Invalid bank");
 string suffix=sign<0?"negative":"positive";var a=bank.GetProperty("pose");
 Vector3 eX=new(a[0][0].GetSingle(),a[1][0].GetSingle(),a[2][0].GetSingle()),eY=new(a[0][1].GetSingle(),a[1][1].GetSingle(),a[2][1].GetSingle()),eZ=new(a[0][2].GetSingle(),a[1][2].GetSingle(),a[2][2].GetSingle()),t=new(a[0][3].GetSingle(),a[1][3].GetSingle(),a[2][3].GetSingle());
 if(Vector3.Distance(Vector3.Cross(eX,eY),eZ)>1e-5f||MathF.Abs(eX.Length()-1)>1e-5f||MathF.Abs(eY.Length()-1)>1e-5f||MathF.Abs(eZ.Length()-1)>1e-5f)throw new InvalidDataException("Invalid rigid pose");
 Vector3 World(Vector3 p)=>t+p.X*eX+p.Y*eY+p.Z*eZ;
 Vector3 Local(Vector3 p)=>new(Vector3.Dot(p-t,eX),Vector3.Dot(p-t,eY),Vector3.Dot(p-t,eZ));
 Voxels Field(Func<Vector3,float> f,Vector3 lo,Vector3 hi)
 {
  Vector3 low=new(float.MaxValue),high=new(float.MinValue);
  foreach(float x in new[]{lo.X,hi.X})foreach(float y in new[]{lo.Y,hi.Y})foreach(float z in new[]{lo.Z,hi.Z}){var q=World(new(x,y,z));low=Vector3.Min(low,q);high=Vector3.Max(high,q);}
  return Sdf.Vox(lib,p=>f(Local(p)),low-new Vector3(3*grid),high+new Vector3(3*grid));
 }
 Voxels B(Vector3 c,Vector3 h,float r)=>Field(p=>Sdf.RoundBox(p,c,h,r),c-h,c+h);
 float half=bank.GetProperty("half_length_mm").GetSingle(),cy=bank.GetProperty("cam_y_mm").GetSingle(),cz=bank.GetProperty("cam_z_mm").GetSingle();
 var centres=bank.GetProperty("head_centres_local_x_mm").EnumerateArray().Select(x=>x.GetSingle()).ToArray();
 if(centres.Length!=6||centres.Any(x=>!float.IsFinite(x))||!float.IsFinite(half)||half<370||half>390||!float.IsFinite(cy)||!float.IsFinite(cz))throw new InvalidDataException("Invalid bank dimensions");
 float outerTop=cz+25.13f,innerTop=outerTop-wall;
 using var lid=B(new(0,0,(74.63f+outerTop)/2),new(half,78.17f,(outerTop-74.63f)/2),12);
 foreach(int side in new[]{-1,1}){using var roof=C(World(new(-half+38,side*cy,cz)),World(new(half-38,side*cy,cz)),38);lid.BoolAdd(roof);}
 using(var flange=B(new(0,0,76.13f),new(half,92.13f,1.5f),6))lid.BoolAdd(flange);
 // Bridge the rounded skirt to the gasket flange before subtracting the thin-wall cavity.
 using(var collar=B(new(0,0,78.13f),new(half,78.17f,3.5f),3))lid.BoolAdd(collar);
 using Lattice ribs=new(lib);
 foreach(int side in new[]{-1,1})foreach(int end in new[]{-1,1})
 {
  Vector3 start=new(end*245,side*76,83),control=new(end*170,side*79,cz+5),finish=new(0,side*cy,cz+37),last=Vector3.Zero;
  for(int i=0;i<=24;i++)
  {
   var point=Sdf.Bezier(start,control,finish,i/24f);float low=0,high=4;
   for(int j=0;j<24;j++)
   {
    float scale=(low+high)/2;Vector3 q=new(point.X,point.Y*scale,cz+(point.Z-cz)*scale);
    float d=MathF.Min(Sdf.RoundBox(q,new(0,0,(74.63f+outerTop)/2),new(half,78.17f,(outerTop-74.63f)/2),12),MathF.Min(new Vector2(q.Y-cy,q.Z-cz).Length()-38,new Vector2(q.Y+cy,q.Z-cz).Length()-38));
    if(d<1.2f)low=scale;else high=scale;
   }
   Vector3 next=new(point.X,point.Y*high,cz+(point.Z-cz)*high);
   if(i>0)ribs.AddBeam(World(last),World(next),2.7f,2.7f,true);last=next;
  }
 }
 using(var ribVolume=new Voxels(ribs))lid.BoolAdd(ribVolume);
 using(var inner=B(new(0,0,(60+innerTop)/2),new(half-wall-.5f,78.17f-wall,(innerTop-60)/2),7))lid.BoolSubtract(inner);
 using var camPaths=new Lattice(lib);
 foreach(int side in new[]{-1,1})
 {
  using(var inner=C(World(new(-half+38,side*cy,cz)),World(new(half-38,side*cy,cz)),38-wall))lid.BoolSubtract(inner);
  var c=World(new(0,side*cy,cz));camPaths.AddBeam(new(-382,c.Y,c.Z),new(382,c.Y,c.Z),31,31,false);
  using(var individual=C(new(-382,c.Y,c.Z),new(382,c.Y,c.Z),31))Export(individual,"bank_cam_reserve_"+suffix+(side>0?"_intake":"_exhaust"));
  using var shaft=C(new(-450,c.Y,c.Z),new(450,c.Y,c.Z),10.25f);lid.BoolSubtract(shaft);
 }
 using var camReserve=new Voxels(camPaths);using(var margin=camReserve.voxOffset(1))lid.BoolSubtract(margin);
 using var adapter=B(new(0,0,70.13f),new(half,92.13f,4),6);
 foreach(float x in centres){using var hole=B(new(x,0,70.13f),new(55.63f,71.63f,12),4);adapter.BoolSubtract(hole);}
 foreach(var x in bank.GetProperty("bolt_x_mm").EnumerateArray())foreach(int side in new[]{-1,1})
 {
  float top=bank.GetProperty("bolt_head_z_mm").GetSingle()-.5f,y=side*bank.GetProperty("bolt_y_mm").GetSingle();
  using var boss=C(World(new(x.GetSingle(),y,76.13f)),World(new(x.GetSingle(),y,top)),5.63f);lid.BoolAdd(boss);
  using var hole=C(World(new(x.GetSingle(),y,60)),World(new(x.GetSingle(),y,90)),3.3f);lid.BoolSubtract(hole);adapter.BoolSubtract(hole);
 }
 foreach(var body in new[]{lid,adapter}){body.BoolSubtract(housingReserve);body.BoolSubtract(gearReserve);}
 // The candidate front transition ends before the existing drive housing; its seal remains unqualified.
 if(sign<0){float right=389.37f-t.X;using var clip=B(new((right-half-3)/2,0,(60+cz+48)/2),new((right+half+3)/2,90,(cz+48-60)/2),0);lid.BoolIntersect(clip);adapter.BoolIntersect(clip);}
 Export(lid,"bank_valve_cover_"+suffix);Export(adapter,"bank_adapter_"+suffix);
}
foreach(var part in root.GetProperty("charge_parts").EnumerateArray())
{
 string id=part.GetProperty("id").GetString()!;
 if(id is not ("charge_pipe_negative" or "charge_pipe_positive")||records.ContainsKey(id))throw new InvalidDataException("Invalid charge ID");
 var points=part.GetProperty("points").EnumerateArray().Select(a=>{var v=a.EnumerateArray().Select(x=>x.GetSingle()).ToArray();if(v.Length!=3||v.Any(x=>!float.IsFinite(x)))throw new InvalidDataException("Invalid point");return new Vector3(v[0],v[1],v[2]);}).ToArray();
 var outerR=part.GetProperty("outer_radii").EnumerateArray().Select(x=>x.GetSingle()).ToArray();
 var innerR=part.GetProperty("inner_radii").EnumerateArray().Select(x=>x.GetSingle()).ToArray();
 if(points.Length<3||outerR.Length!=points.Length||innerR.Length!=points.Length||Vector3.Distance(points[0],points[1])<25)throw new InvalidDataException("Invalid mouth or radii");
 using Lattice outer=new(lib),inner=new(lib);
 for(int i=0;i<points.Length;i++)if(!float.IsFinite(outerR[i])||!float.IsFinite(innerR[i])||innerR[i]<=0||outerR[i]>25||outerR[i]-innerR[i]<2)throw new InvalidDataException("Invalid pipe wall");
 for(int i=1;i<points.Length;i++)
 {
  if(points[i]==points[i-1])throw new InvalidDataException("Zero pipe segment");
  outer.AddBeam(points[i-1],points[i],outerR[i-1],outerR[i],i!=1&&i!=points.Length-1);inner.AddBeam(points[i-1],points[i],innerR[i-1],innerR[i],true);
 }
 inner.AddBeam(points[0]-Vector3.Normalize(points[1]-points[0])*12,points[0],innerR[0],innerR[0],false);
 inner.AddBeam(points[^1],points[^1]+Vector3.Normalize(points[^1]-points[^2])*12,innerR[^1],innerR[^1],false);
 using Voxels pipe=new(outer),bore=new(inner);pipe.BoolSubtract(bore);Export(pipe,id);
}
if(records.Count!=10)throw new InvalidDataException("Missing generated parts");
if(Hash(input)!=args[1]||Hash(path)!=source.GetProperty("sha256").GetString())throw new InvalidDataException("Inputs changed");
File.WriteAllText(Path.Combine(output,"receipt.json"),JsonSerializer.Serialize(new{classification="hypothetical_engine_components_not_manufacturing_geometry",voxel_mm=grid,kernel=Library.strVersion(),config_sha256=args[1],source_vdb_sha256=Hash(path),parts=records,manufacturing_authorized=false,engine_start_authorized=false},new JsonSerializerOptions{WriteIndented=true})+"\n");
