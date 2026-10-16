using System.Numerics;
using System.Text.Json;
using System.Security.Cryptography;
using PicoGK;
using Leap71.ShapeKernel;
using Leap71.LatticeLibrary;

// Four-rib coupon of ../picogk/Program.cs with an ASSUMED rib-root fillet on every hot-channel
// corner. The radius is a design proposal from fillet_convergence.py, not a measured or printed
// value. Everything else (envelope, cold box, BCC lattice, fields) follows the Mac source.
if(args.Length!=4)throw new ArgumentException("Usage: CouponFillet study.json new-output voxel-mm fillet-radius-mm");
var inv=System.Globalization.CultureInfo.InvariantCulture;
float voxel=float.Parse(args[2],inv),radius=float.Parse(args[3],inv);
if(!float.IsFinite(voxel)||voxel<.04f||voxel>.2f)throw new ArgumentException("Unsupported resolution");
if(!(radius==0f||radius==.2f||radius==.4f))throw new ArgumentException("Only the study's assumed radii 0, 0.2 and 0.4 mm are accepted");
// A fillet narrower than four voxels is not resolved.
if(radius>0f&&radius<4f*voxel-1e-6f)throw new ArgumentException("Fillet radius below four voxels");
var study=JsonDocument.Parse(File.ReadAllText(args[0])).RootElement;
float hotK=study.GetProperty("selected").GetProperty("design_point").GetProperty("compressor_outlet_c").GetSingle()+273.15f;
float coldK=study.GetProperty("selected").GetProperty("design_point").GetProperty("ambient_c").GetSingle()+273.15f;
if(!float.IsFinite(hotK)||!float.IsFinite(coldK)||coldK<273.15f||hotK<=coldK)throw new ArgumentException("Invalid initial temperatures");
string output=Path.GetFullPath(args[1]);if(Directory.Exists(output))throw new IOException("Output already exists");Directory.CreateDirectory(output);
using Library lib=new(voxel);Library.RegisterGlobalLibrary(lib);
using LogFile log=new(Path.Combine(output,"picogk.log"));Library.RegisterGlobalLog(log);
try{
 Voxels Box(Vector3 lo,Vector3 hi)=>new BaseBox(new BBox3(lo,hi)).voxConstruct();
 using Voxels envelope=Box(new(-12,-12,0),new(12,12,11.4f));
 // Same clear channels as the rib cutters of the Mac source: edges at +-11.2, +-9.4, +-8.6, +-3.4, +-2.6 mm.
 float[][] channels={new[]{-11.2f,-9.4f},new[]{-8.6f,-3.4f},new[]{-2.6f,2.6f},new[]{3.4f,8.6f},new[]{9.4f,11.2f}};
 using Voxels hot=new(lib);
 foreach(var c in channels){
  // Render beyond the channel so no channel face lies on the evaluation bounds.
  var implicitChannel=new RoundedChannel(c[0],c[1],.8f,3.8f,12f,radius);float pad=4*voxel;
  using Voxels channel=new(lib,implicitChannel,new BBox3(new Vector3(-12-pad,c[0]-pad,.8f-pad),new Vector3(12+pad,c[1]+pad,3.8f+pad)));
  hot.BoolAdd(channel);
 }
 using Voxels coldBox=Box(new(-11.2f,-12,4.6f),new(11.2f,12,10.6f));
 using Voxels solid=new(envelope);solid.BoolSubtract(hot);solid.BoolSubtract(coldBox);
 {
  using Lattice lattice=new(lib);Lattice target=lattice;
  for(int i=0;i<4;i++)for(int j=0;j<4;j++){
   float x=-12+6*i,y=-12+6*j,z=4.6f;
   var cell=new CuboidCell(new(x,y,z),new(x+6,y,z),new(x+6,y+6,z),new(x,y+6,z),new(x,y,z+6),new(x+6,y,z+6),new(x+6,y+6,z+6),new(x,y+6,z+6));
   new BodyCentreLattice().AddCell(ref target,cell,new ConstantBeamThickness(.8f),2);
  }
  using Voxels struts=new(lattice);struts.BoolIntersect(envelope);solid.BoolAdd(struts);
 }
 using Voxels cold=new(coldBox);cold.BoolSubtract(solid);
 using Voxels overlap=hot.voxBoolIntersect(cold);
 if(!overlap.bIsEmpty())throw new InvalidDataException("Hot/cold domains overlap");
 using ScalarField ht=new(hot,hotK,0);using ScalarField ct=new(cold,coldK,0);
 // shortcut: uniform 1 m/s initialization only; replace with solved inlet profiles before CFD acceptance.
 using VectorField hv=new(hot,Vector3.UnitX,0);using VectorField cv=new(cold,Vector3.UnitY,0);
 var domains=new Dictionary<string,Voxels>{{"solid_mm",solid},{"hot_fluid_mm",hot},{"cold_fluid_mm",cold}};
 string vdb=Path.Combine(output,"coupon-fields.vdb");
 using(OpenVdbFile f=new(lib)){
  foreach(var pair in domains)f.nAdd(pair.Value,pair.Key);
  f.nAdd(ht,"hot_temperature_initial_K");f.nAdd(ct,"cold_temperature_initial_K");
  f.nAdd(hv,"hot_velocity_initial_m_s");f.nAdd(cv,"cold_velocity_initial_m_s");f.SaveToFile(vdb);
 }
 var samples=new Dictionary<string,int>();
 using(OpenVdbFile f=new(lib,vdb)){
  if(f.nFieldCount()!=7||MathF.Abs(f.fPicoGKVoxelSizeMM()-voxel)>1e-6)throw new InvalidDataException("Field count or scale changed");
  foreach(var pair in domains){using Voxels restored=f.voxGet(pair.Key);if(!pair.Value.bIsEqual(restored))throw new InvalidDataException("Geometry roundtrip failed");}
  void Scalar(string name,ScalarField original){using ScalarField restored=f.oGetScalarField(name);var check=new ScalarCheck(restored);original.TraverseActive(check);if(check.Count==0)throw new InvalidDataException("Empty scalar");samples[name]=check.Count;}
  void Vector(string name,VectorField original){using VectorField restored=f.oGetVectorField(name);var check=new VectorCheck(restored);original.TraverseActive(check);if(check.Count==0)throw new InvalidDataException("Empty vector");samples[name]=check.Count;}
  Scalar("hot_temperature_initial_K",ht);Scalar("cold_temperature_initial_K",ct);Vector("hot_velocity_initial_m_s",hv);Vector("cold_velocity_initial_m_s",cv);
 }
 foreach(var pair in domains){using Mesh mesh=new(pair.Value);mesh.SaveToStlFile(Path.Combine(output,pair.Key+".stl"),Mesh.EStlUnit.MM);}
 string Sha(string path)=>Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(path))).ToLowerInvariant();
 var report=new{status="filleted_ribbed_coupon_geometry_and_initial_field_exchange_only",variant="bcc_hot_ribbed_assumed_root_fillet",fillet_radius_mm=radius,fillet_radius_is_assumption=true,
  hot_channel_edges_y_mm=channels,hot_rib_centres_y_mm=new[]{-9f,-3f,3f,9f},hot_rib_thickness_mm=.8f,voxel_mm=voxel,dimensions_mm=new[]{24f,24f,11.4f},wall_mm=.8f,cell_pitch_mm=6f,strut_diameter_mm=.8f,
  hot_initial_K=hotK,cold_initial_K=coldK,initial_velocity_m_s=1,field_count=7,geometry_roundtrip_exact=true,hot_cold_overlap_empty=true,active_values_checked=samples,scalar_vector_extra_active_values_checked=false,
  picogk_library=Library.strName(),picogk_version=Library.strVersion(),picogk_build=Library.strBuildInfo(),
  study_sha256=Sha(args[0]),vdb_sha256=Sha(vdb),source_assembly_sha256=Sha(typeof(ScalarCheck).Assembly.Location),thermal_solver_executed=false,hydraulic_solver_executed=false,pressure_qualified=false,manufacturing_authorized=false};
 File.WriteAllText(Path.Combine(output,"receipt.json"),JsonSerializer.Serialize(report,new JsonSerializerOptions{WriteIndented=true})+"\n");
 Console.WriteLine(JsonSerializer.Serialize(report));
}finally{Library.UnregisterGlobalLibrary();}

// Exact signed distance of a straight channel whose rectangular section (y, z) has all four
// corners rounded with radius r, limited to |x| <= halfLength. Negative inside.
sealed class RoundedChannel(float y0,float y1,float z0,float z1,float halfLength,float r):IImplicit{
 readonly float cy=(y0+y1)/2,cz=(z0+z1)/2,hy=(y1-y0)/2,hz=(z1-z0)/2;
 public float fSignedDistance(in Vector3 p){
  float qy=MathF.Abs(p.Y-cy)-(hy-r),qz=MathF.Abs(p.Z-cz)-(hz-r);
  float section=MathF.Sqrt(MathF.Pow(MathF.Max(qy,0),2)+MathF.Pow(MathF.Max(qz,0),2))+MathF.Min(MathF.Max(qy,qz),0)-r;
  float ends=MathF.Abs(p.X)-halfLength;
  return MathF.Sqrt(MathF.Pow(MathF.Max(section,0),2)+MathF.Pow(MathF.Max(ends,0),2))+MathF.Min(MathF.Max(section,ends),0);
 }
}
sealed class ScalarCheck(ScalarField restored):ITraverseScalarField{
 public int Count;
 public void InformActiveValue(in Vector3 p,float value){if(!float.IsFinite(value)||!restored.bGetValue(p,out float found)||found!=value)throw new InvalidDataException("Scalar roundtrip changed");Count++;}
}
sealed class VectorCheck(VectorField restored):ITraverseVectorField{
 public int Count;
 public void InformActiveValue(in Vector3 p,in Vector3 value){if(!float.IsFinite(value.LengthSquared())||!restored.bGetValue(p,out Vector3 found)||found!=value)throw new InvalidDataException("Vector roundtrip changed");Count++;}
}
