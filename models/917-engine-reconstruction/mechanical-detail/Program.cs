using System.Globalization;
using System.Numerics;
using System.Security.Cryptography;
using System.Text.Json;
using PicoGK;
using PicoGKCatalog;

if(args.Length!=4)throw new ArgumentException("Usage: Detail config.json sha256 voxel_mm new_work_output");
string Hash(string p){using var f=File.OpenRead(p);return Convert.ToHexString(SHA256.HashData(f)).ToLowerInvariant();}
string input=Path.GetFullPath(args[0]),output=Path.GetFullPath(args[3]);
float grid=float.Parse(args[2],CultureInfo.InvariantCulture);
if(Hash(input)!=args[1] || grid is not (1f or .5f) || Path.Exists(output))throw new ArgumentException("Hash, grid or existing output rejected");
bool work=false;
for(DirectoryInfo? p=new(output);p!=null;p=p.Parent)
 if(File.Exists(Path.Combine(p.FullName,".git"))||Directory.Exists(Path.Combine(p.FullName,".git")))
 {work=Path.GetRelativePath(p.FullName,output).StartsWith("work"+Path.DirectorySeparatorChar,StringComparison.Ordinal);break;}
if(!work)throw new IOException("Output must stay under ignored work/");
using var doc=JsonDocument.Parse(File.ReadAllText(input));var cfg=doc.RootElement;
if(cfg.GetProperty("classification").GetString()!="917_mechanical_detail_geometry_hypothesis" || cfg.GetProperty("manufacturing_authorized").GetBoolean() || cfg.GetProperty("engine_start_authorized").GetBoolean())throw new InvalidDataException("Physical release rejected");
float[][] Rows(string name)=>cfg.GetProperty(name).EnumerateArray().Select(r=>r.EnumerateArray().Select(x=>x.GetSingle()).ToArray()).ToArray();
var gears=Rows("gear_envelopes");var bolts=Rows("cover_bolts_yz");
if(gears.Length!=26 || gears.Any(r=>r.Length!=4||r.Any(v=>!float.IsFinite(v))||r[3]<=0) || bolts.Length<12 || bolts.Any(r=>r.Length!=2||r.Any(v=>!float.IsFinite(v))))throw new InvalidDataException("Invalid drive inputs");
Directory.CreateDirectory(output);using Library lib=new(grid);
var records=new Dictionary<string,object>();
Voxels Field(Func<Vector3,float> f,Vector3 lo,Vector3 hi)=>Sdf.Vox(lib,f,lo-new Vector3(3*grid),hi+new Vector3(3*grid));
Voxels C(Vector3 a,Vector3 b,float r){using Lattice l=new(lib);l.AddBeam(a,b,r,r,false);return new Voxels(l);}
Voxels B(Vector3 c,Vector3 h,float r=0)=>Field(p=>r==0?Sdf.Box(p,c,h):Sdf.RoundBox(p,c,h,r),c-h,c+h);
void Export(Voxels v,string id)
{
 if(v.bIsEmpty())throw new InvalidDataException("Empty object "+id);
 using Mesh m=new(v);v.CalculateProperties(out float volume,out _);
 if(!float.IsFinite(volume)||volume<=0)throw new InvalidDataException("Invalid volume "+id);
 string stl=Path.Combine(output,id+".stl"),vdb=Path.Combine(output,id+".vdb");m.SaveToStlFile(stl);v.SaveToVdbFile(vdb);
 records[id]=new {stl_sha256=Hash(stl),vdb_sha256=Hash(vdb),triangles=m.nTriangleCount(),native_resampled_volume_mm3=volume};
 Console.WriteLine("EXPORT "+id);
}
void Curve(Lattice l,Vector3 a,Vector3 b,Vector3 c,float r0,float r1)
{
 var last=a;for(int i=1;i<=20;i++){float t=i/20f;var next=Sdf.Bezier(a,b,c,t);l.AddBeam(last,next,r0+(r1-r0)*(t-.05f),r0+(r1-r0)*t,true);last=next;}
}
float Slot(Vector3 p,float length,float yPitch,float yLimit,float zLimit)
{
 float y=Math.Clamp(MathF.Round(p.Y/yPitch),-yLimit/yPitch,yLimit/yPitch)*yPitch;
 float z=Math.Clamp(MathF.Round((p.Z+zLimit)/8),0,2*zLimit/8)*8-zLimit;
 return Sdf.Box(p,new(0,y,z),new(length+2,yPitch/2-2,1.5f));
}
float TankPlan(Vector3 p,float length,float width,float height)
{
 float t=Math.Clamp((p.X-length)/45,0,1),a=width+(26.5f-width)*t,b=height+(26.5f-height)*t,r=6+20.5f*t;
 return Sdf.RoundBox(new(0,p.Y,p.Z),Vector3.Zero,new(1000,a,b),MathF.Min(r,MathF.Min(a,b)));
}
float TankInner(Vector3 p,float length,float width,float height)=>MathF.Max(TankPlan(p,length,width,height)+2.5f+1.5f*Math.Clamp((p.X-length)/45,0,1),MathF.Max(length-1-p.X,p.X-(length+48)));
void Cooler(string id,float length,float width,float height,float yPitch,float yLimit,float zLimit)
{
 float Gas(Vector3 p)=>Slot(p,length,yPitch,yLimit,zLimit);
 float Air(Vector3 p)
 {
  float x=Math.Clamp(MathF.Round(p.X/10),-(length-10)/10,(length-10)/10)*10;
  float z=Math.Clamp(MathF.Round((p.Z+zLimit-4)/8),0,(2*zLimit-8)/8)*8-zLimit+4;
  return Sdf.Box(p,new(x,0,z),new(3.5f,width+3,.75f));
 }
 using var core=Field(p=>MathF.Max(Sdf.RoundBox(p,Vector3.Zero,new(length,width,height),3),-MathF.Min(Gas(p),Air(p))),new(-length,-width,-height),new(length,width,height));
 if(id=="intercooler")foreach(int sx in new[]{-1,1})foreach(int sy in new[]{-1,1})
 {using var ear=B(new(sx*80,sy*51,-23),new(10,8,5),3);core.BoolAdd(ear);using var hole=C(new(sx*80,sy*52,-35),new(sx*80,sy*52,-13),3.2f);core.BoolSubtract(hole);}
 Export(core,id+"_core");
 var ribs=new List<(Vector3 a,Vector3 b,float r)>();
 foreach(int y in new[]{-1,1})foreach(int z in new[]{-1,1})
 {
  Vector3 a=new(length+4,y*(width-4),z*(height-4)),b=new(length+22,y*(width-1),z*(height-1)),c=new(length+39,y*19,z*12),last=a;
  for(int k=0;k<=20;k++)
  {
   float t=k/20f;Vector3 point=Sdf.Bezier(a,b,c,t);float lo=0,hi=4;
   // Place the rib outside the pressure skin so its blend cannot carve isolated inner pockets.
   for(int j=0;j<24;j++){float scale=(lo+hi)/2;var q=new Vector3(point.X,point.Y*scale,point.Z*scale);if(TankPlan(q,length,width,height)<2)lo=scale;else hi=scale;}
   Vector3 next=new(point.X,point.Y*hi,point.Z*hi);if(k>0)ribs.Add((last,next,3.5f-t));last=next;
  }
 }
 using var tank=Field(p=>{
  float d=MathF.Max(TankPlan(p,length,width,height),MathF.Max(length-p.X,p.X-length-45));
  foreach(var rib in ribs)d=Es.SMin(d,Sdf.Capsule(p,rib.a,rib.b,rib.r),1.1f);
  return MathF.Max(d,-TankInner(p,length,width,height));
 },new(length-1,-MathF.Max(width,25)-6,-MathF.Max(height,25)-6),new(length+46,MathF.Max(width,25)+6,MathF.Max(height,25)+6));
 Export(tank,id+"_tank");
 using var gas=Field(p=>MathF.Min(Gas(p),MathF.Min(TankInner(p,length,width,height),TankInner(new(-p.X,p.Y,p.Z),length,width,height))),new(-length-48,-width,-height),new(length+48,width,height));
 Export(gas,id+"_gas_domain");
}
Cooler("intercooler",95,45,25,28,28,20);
Cooler("oil_cooler",135,24,40,14,14,32);

using(var alternator=C(new(0,0,-42),new(0,0,42),40))
{
 using(var cavity=C(new(0,0,-36),new(0,0,36),35))alternator.BoolSubtract(cavity);
 for(int k=0;k<12;k++)
 {
  float a=k*2*MathF.PI/12;var n=new Vector3(MathF.Cos(a),MathF.Sin(a),0);
  using var slot=C(n*30+new Vector3(0,0,-28),n*46+new Vector3(0,0,-28),4);alternator.BoolSubtract(slot);
  using var upper=C(n*30+new Vector3(0,0,28),n*46+new Vector3(0,0,28),4);alternator.BoolSubtract(upper);
  using var rib=C(n*40+new Vector3(0,0,-22),n*40+new Vector3(0,0,22),2);alternator.BoolAdd(rib);
 }
 using(var shaft=C(new(0,0,-50),new(0,0,53),7))alternator.BoolAdd(shaft);
 using(var pulley=C(new(0,0,44),new(0,0,52),26))alternator.BoolAdd(pulley);
 foreach(int sign in new[]{-1,1}){using var foot=B(new(0,sign*32,-35),new(12,8,6),3);alternator.BoolAdd(foot);}
 Export(alternator,"alternator");
}
using(var starter=C(new(0,0,-70),new(0,0,28),32))
{
 using var nose=C(new(0,0,24),new(0,0,62),19);starter.BoolAdd(nose);
 using var solenoid=C(new(38,0,-44),new(38,0,16),14);starter.BoolAdd(solenoid);
 using var bridge=B(new(25,0,-17),new(16,9,20),4);starter.BoolAdd(bridge);
 using var flange=C(new(0,0,22),new(0,0,30),38);starter.BoolAdd(flange);
 using(var cavity=C(new(0,0,-63),new(0,0,19),28))starter.BoolSubtract(cavity);
 using(var shaftBore=C(new(0,0,-85),new(0,0,70),10))starter.BoolSubtract(shaftBore);
 foreach(int sign in new[]{-1,1}){using var pad=C(new(0,sign*35,20),new(0,sign*35,32),7);starter.BoolAdd(pad);using var hole=C(new(0,sign*35,16),new(0,sign*35,36),3.3f);starter.BoolSubtract(hole);}
 Export(starter,"starter_motor");
}
using(var ecu=B(Vector3.Zero,new(65,40,12),5))
{
 for(int i=-5;i<=5;i++){using var fin=B(new(i*10,0,12),new(1.2f,34,4),.8f);ecu.BoolAdd(fin);}
 foreach(int sign in new[]{-1,1}){using var plug=B(new(sign*64,0,0),new(10,18,7),3);ecu.BoolAdd(plug);}
 Export(ecu,"ecu");
}
using(var throttle=C(new(0,0,-23),new(0,0,23),28))
{
 using(var bore=C(new(0,0,-30),new(0,0,30),22.5f))throttle.BoolSubtract(bore);
 using(var actuator=B(new(36,0,0),new(16,20,17),5))throttle.BoolAdd(actuator);
 using(var connection=B(new(24,0,0),new(12,12,12),3))throttle.BoolAdd(connection);
 using(var repeatBore=C(new(0,0,-30),new(0,0,30),22.5f))throttle.BoolSubtract(repeatBore);
 Export(throttle,"throttle");
}
float PumpPlan(Vector3 p,float radius)=>Es.SMin(new Vector2(p.X-15,p.Y).Length()-radius,new Vector2(p.X+15,p.Y).Length()-radius,5);
var pumpBolts=new[]{new Vector2(-27,-17),new Vector2(-27,17),new Vector2(0,-18),new Vector2(0,18),new Vector2(27,-17),new Vector2(27,17)};
using(var pump=Field(p=>MathF.Max(PumpPlan(p,19.63f),MathF.Max(-18.13f-p.Z,p.Z-18.13f)),new(-42,-27,-18.13f),new(42,27,18.13f)))
{
 foreach(var q in pumpBolts){using var pad=C(new(q.X,q.Y,-4.17f),new(q.X,q.Y,18.13f),6.17f);pump.BoolAdd(pad);}
 using(var cavity=Field(p=>MathF.Max(PumpPlan(p,15.87f),MathF.Max(-10.17f-p.Z,p.Z-23.13f)),new(-33,-18,-10.17f),new(33,18,23.13f)))pump.BoolSubtract(cavity);
 foreach(int sign in new[]{-1,1})
 {
  using var boss=C(new(0,sign*15,0),new(0,sign*30.13f,0),7.13f);pump.BoolAdd(boss);
  using var port=C(new(0,sign*7,0),new(0,sign*34.13f,0),4.13f);pump.BoolSubtract(port);
 }
 foreach(var q in pumpBolts){using var hole=C(new(q.X,q.Y,-20),new(q.X,q.Y,23),2.8f);pump.BoolSubtract(hole);}
 using(var shaft=C(new(-15,0,-23),new(-15,0,4),5.6f))pump.BoolSubtract(shaft);
 Export(pump,"oil_pump_body");
}
using(var cover=Field(p=>MathF.Max(PumpPlan(p,19.5f),MathF.Abs(p.Z)-2),new(-42,-26,-2),new(42,26,2)))
{
 foreach(var q in pumpBolts){using var pad=C(new(q.X,q.Y,-2),new(q.X,q.Y,2),6);cover.BoolAdd(pad);using var hole=C(new(q.X,q.Y,-6),new(q.X,q.Y,6),2.8f);cover.BoolSubtract(hole);}
 Export(cover,"oil_pump_cover");
}
float coverTop=cfg.GetProperty("valve_cover_top_mm").GetSingle();
using(var cover=B(new(0,0,(68+coverTop)/2),new(56.17f,76.17f,(coverTop-68)/2),8))
{
 using(var cavity=B(new(0,0,(60+coverTop-3)/2),new(53.17f,73.17f,(coverTop-3-60)/2),5))cover.BoolSubtract(cavity);
 using(var flange=B(new(0,0,70.13f),new(58.17f,78.17f,2.11f),6))
 {using var hole=B(new(0,0,70.13f),new(52.17f,72.17f,5.19f),4);flange.BoolSubtract(hole);cover.BoolAdd(flange);}
 using Lattice ribs=new(lib);
 foreach(int sx in new[]{-1,1})foreach(int sy in new[]{-1,1})Curve(ribs,new(sx*54,sy*57,74),new(sx*53,sy*63,coverTop-4),new(sx*22,sy*43,coverTop-1),3,2);
 using(var v=new Voxels(ribs))cover.BoolAdd(v);
 float cy=cfg.GetProperty("cam_local_y_mm").GetSingle(),cz=cfg.GetProperty("cam_local_z_mm").GetSingle();
 foreach(int sign in new[]{-1,1}){using var hole=C(new(-70,sign*cy,cz),new(70,sign*cy,cz),10);cover.BoolSubtract(hole);}
 Export(cover,"valve_cover");
}
foreach(int sign in new[]{-1,1})
{
 float cy=cfg.GetProperty("cam_local_y_mm").GetSingle(),cz=cfg.GetProperty("cam_local_z_mm").GetSingle();
 using var sweep=C(new(-24,sign*cy,cz),new(24,sign*cy,cz),31);
 using var shaft=C(new(-70,sign*cy,cz),new(70,sign*cy,cz),9.5f);sweep.BoolAdd(shaft);
 Export(sweep,sign==1?"cam_sweep_intake":"cam_sweep_exhaust");
}
using(var sump=B(Vector3.Zero,new(390,82,5),5))
{
 for(int i=-3;i<=3;i++){using var rib=B(new(i*105,0,-5),new(2.5f,74,3),1.5f);sump.BoolAdd(rib);}
 Export(sump,"sump_cover");
}

// A continuous swept-disc reserve bounds every gear angle; it is not a tooth-contact calculation.
foreach(float plane in new[]{400f,424f})
{
 Voxels? reserve=null;
 foreach(var g in gears.Where(g=>g[0]==plane))
 {var disc=C(new(plane-6.75f,g[1],g[2]),new(plane+6.75f,g[1],g[2]),g[3]+.75f);if(reserve==null)reserve=disc;else{reserve.BoolAdd(disc);disc.Dispose();}}
 if(reserve==null)throw new InvalidDataException("Missing plane");using(reserve)Export(reserve,plane==400?"drive_sweep_intake":"drive_sweep_exhaust");
}
Voxels DriveSlab(float x0,float x1,float extra)
{
 using Lattice slab=new(lib);
 foreach(var g in gears)slab.AddBeam(new(x0,g[1],g[2]),new(x1,g[1],g[2]),g[3]+extra,g[3]+extra,false);
 return new Voxels(slab);
}
using(var housing=DriveSlab(390,437,7))
{
 using(var inside=DriveSlab(392.25f,438,3))housing.BoolSubtract(inside);
 foreach(var q in bolts)
 {using var boss=C(new(421,q[0],q[1]),new(437,q[0],q[1]),7);housing.BoolAdd(boss);using var hole=C(new(419,q[0],q[1]),new(445,q[0],q[1]),3.3f);housing.BoolSubtract(hole);}
 foreach(var source in cfg.GetProperty("case_sources").EnumerateArray())
 {
  string path=source.GetProperty("path").GetString()!;
  if(Hash(path)!=source.GetProperty("sha256").GetString())throw new InvalidDataException("Case source changed");
  using var mesh=Mesh.mshFromStlFile(path,Mesh.EStlUnit.MM,libSet:lib);using var body=new Voxels(mesh);using var reserve=body.voxOffset(1);housing.BoolSubtract(reserve);
 }
 Export(housing,"drive_housing");
}
using(var lid=DriveSlab(437.5f,441.5f,7))
{
 foreach(var q in bolts){using var pad=C(new(437.5f,q[0],q[1]),new(443,q[0],q[1]),7);lid.BoolAdd(pad);using var hole=C(new(435,q[0],q[1]),new(448,q[0],q[1]),3.3f);lid.BoolSubtract(hole);}
 Export(lid,"drive_cover");
}
using Lattice framePaths=new(lib);
foreach(var t in cfg.GetProperty("trains").EnumerateArray())
{
 var points=t.GetProperty("centres_yz_mm").EnumerateArray().Select(p=>new Vector3(411,p[0].GetSingle(),p[1].GetSingle())).ToArray();
 for(int i=1;i<points.Length;i++)Curve(framePaths,points[i-1],(points[i-1]+points[i])/2+new Vector3(0,0,12),points[i],7,7);
}
foreach(int sign in new[]{-1,1})Curve(framePaths,new(411,sign*60,-70),new(411,sign*75,-25),new(411,0,0),8,7);
using(var frame=new Voxels(framePaths))
{
 foreach(var g in gears){using var boss=C(new(408,g[1],g[2]),new(414,g[1],g[2]),g[3]>40?15:12);frame.BoolAdd(boss);}
 using(var clip=B(new(411,0,30),new(3,445,175)))frame.BoolIntersect(clip);
 foreach(var g in gears){using var hole=C(new(403,g[1],g[2]),new(419,g[1],g[2]),g[3]<25||g[3]>40?10:6);frame.BoolSubtract(hole);}
 foreach(int sign in new[]{-1,1})
 {
  using var mount=C(new(380,sign*60,-70),new(414,sign*60,-70),9);frame.BoolAdd(mount);
  using var hole=C(new(375,sign*60,-70),new(418,sign*60,-70),3.5f);frame.BoolSubtract(hole);
 }
 Export(frame,"drive_bionic_frame");
}
foreach(var pair in new[]{("drive_pin_intake",26f),("drive_pin_exhaust",30f)})
 {using var pin=C(new(-pair.Item2/2,0,0),new(pair.Item2/2,0,0),5);Export(pin,pair.Item1);}
using(var shank=C(new(-12.17f,0,0),new(1.17f,0,0),3))
{
 using var head=Field(p=>{float yz=float.MinValue;for(int i=0;i<6;i++){float a=i*MathF.PI/3;yz=MathF.Max(yz,p.Y*MathF.Cos(a)+p.Z*MathF.Sin(a)-5);}return MathF.Max(yz,MathF.Max(-p.X,p.X-4));},new(0,-6,-6),new(4,6,6));shank.BoolAdd(head);Export(shank,"drive_cover_bolt");
}
using Lattice mounts=new(lib);
foreach(int sign in new[]{-1,1})Curve(mounts,new(-185,sign*65,64),new(-185,sign*62,170),new(-185,sign*32,235),8,6);
using(var bracket=new Voxels(mounts))
{
 using(var bridge=C(new(-185,-32,235),new(-185,32,235),6))bracket.BoolAdd(bridge);
 Export(bracket,"alternator_bionic_bracket");
}
if(Hash(input)!=args[1])throw new InvalidDataException("Input changed during generation");
File.WriteAllText(Path.Combine(output,"receipt.json"),JsonSerializer.Serialize(new {classification="hypothetical_engine_components_not_manufacturing_geometry",config_sha256=args[1],voxel_mm=grid,kernel=Library.strVersion(),parts=records,manufacturing_authorized=false,engine_start_authorized=false},new JsonSerializerOptions{WriteIndented=true})+"\n");
