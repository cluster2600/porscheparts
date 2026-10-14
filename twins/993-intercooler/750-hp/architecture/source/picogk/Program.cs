using System.Numerics;
using System.Security.Cryptography;
using System.Text.Json;
using PicoGK;
using PicoGKCatalog;
if(args.Length!=2)throw new ArgumentException("Usage: Layout comparison.json new-output");
var report=JsonDocument.Parse(File.ReadAllText(args[0])).RootElement;
foreach(var v in report.GetProperty("acceptance").EnumerateObject())if(v.Value.GetBoolean())throw new ArgumentException("Study cannot grant acceptance");
var a=report.GetProperty("assumptions");var g=report.GetProperty("selected").GetProperty("geometry");
float P(JsonElement e,string name)=>e.GetProperty(name).GetSingle();
float width=P(g,"width_mm"), span=P(g,"span_mm"), depth=P(g,"depth_mm"), gap=P(a,"bank_gap_mm"), hd=P(a,"header_depth_mm"), wall=P(a,"header_wall_mm"), voxel=P(a,"voxel_mm"), radius=P(a,"charge_pipe_id_mm")/2;
foreach(float v in new[]{width,span,depth,gap,hd,wall,voxel,radius})if(!float.IsFinite(v)||v<=0)throw new ArgumentException("Invalid dimensions");
if(wall<4*voxel||hd<2*wall||gap<2*MathF.Sqrt(2)*radius+2*wall||depth<2*MathF.Sqrt(2)*radius+2*wall)throw new ArgumentException("Ports do not fit");
string output=Path.GetFullPath(args[1]);if(Directory.Exists(output))throw new IOException("Output already exists");Directory.CreateDirectory(output);
float Box(Vector3 p,Vector3 lo,Vector3 hi)=>Sdf.Box(p,(lo+hi)/2,(hi-lo)/2);
using Library lib=new(voxel);var parts=new List<object>();
void Save(string name,Func<Vector3,float> field,Vector3 lo,Vector3 hi){using Voxels v=Sdf.Vox(lib,field,lo-new Vector3(voxel),hi+new Vector3(voxel));using Mesh m=new(v);m.SaveToStlFile(Path.Combine(output,name+".stl"),Mesh.EStlUnit.MM);parts.Add(new{name,triangles=m.nTriangleCount()});Console.WriteLine("GENERATED "+name);}
foreach(int side in new[]{-1,1}){
 float c0=side<0?-width/2-gap/2:gap/2,c1=c0+width/2;
 Vector3 lo=new(c0,0,0),hi=new(c1,span,depth);
 Save("core-envelope-"+(side<0?"left":"right"),p=>Box(p,lo,hi),lo,hi);
 float x0=side<0?c0-hd:c1,x1=x0+hd;
 Vector3 hl=new(x0,0,0),hh=new(x1,span,depth);
 float Header(Vector3 p){
  float shell=MathF.Max(Box(p,hl,hh),-Box(p,new(side<0?x0+wall:x0-2*voxel,wall,wall),new(side<0?x1+2*voxel:x1-wall,span-wall,depth-wall)));
  float port=Sdf.CylZ(new(p.Y,p.Z,p.X),span/2,depth/2,radius,x0-voxel,x1+voxel);
  return MathF.Max(shell,-port);
 }
 Save("charge-inlet-"+(side<0?"left":"right"),Header,hl,hh);
}
Vector3 ol=new(-gap/2,0,0),oh=new(gap/2,span,depth);
float Outlet(Vector3 p){float shell=MathF.Max(Box(p,ol,oh),-Box(p,new(-gap/2-2*voxel,wall,wall),new(gap/2+2*voxel,span-wall,depth-wall)));float port=Sdf.CylZ(new(p.X,p.Z,p.Y),0,depth/2,MathF.Sqrt(2)*radius,-voxel,span/2);return MathF.Max(shell,-port);}
Save("common-charge-outlet",Outlet,ol,oh);
File.WriteAllText(Path.Combine(output,"generation.json"),JsonSerializer.Serialize(new{status="picogk_header_and_core_envelope_study",kernel=Library.strVersion(),voxel_mm=voxel,geometry=g,input_sha256=Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(args[0]))).ToLowerInvariant(),parts,core_fins_resolved=false,pressure_qualified=false,manufacturing_authorized=false,ports=new{inlet_count=2,inlet_id_mm=2*radius,outlet_id_mm=2*MathF.Sqrt(2)*radius},flow="Charge enters both outer X faces, crosses two half-cores and leaves central collector through -Y; ambient crosses along Z.",limitations="Core blocks are envelopes only. Collector mouths lack individual tube interfaces. External hoses, brackets, fan ducts and seals are not designed."},new JsonSerializerOptions{WriteIndented=true}));
