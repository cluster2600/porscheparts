using System.Numerics;
using System.Text.Json;
using System.Security.Cryptography;
using PicoGK;
using Leap71.ShapeKernel;
using Leap71.LatticeLibrary;

if(args.Length!=3)throw new ArgumentException("Usage: Coupon study.json new-output voxel-mm");
float voxel=float.Parse(args[2],System.Globalization.CultureInfo.InvariantCulture);
if(!float.IsFinite(voxel)||voxel<.1f||voxel>.2f)throw new ArgumentException("Unsupported coupon or resolution");
var study=JsonDocument.Parse(File.ReadAllText(args[0])).RootElement;
float hotK=study.GetProperty("selected").GetProperty("design_point").GetProperty("compressor_outlet_c").GetSingle()+273.15f;
float coldK=study.GetProperty("selected").GetProperty("design_point").GetProperty("ambient_c").GetSingle()+273.15f;
if(!float.IsFinite(hotK)||!float.IsFinite(coldK)||coldK<273.15f||hotK<=coldK)throw new ArgumentException("Invalid initial temperatures");
string output=Path.GetFullPath(args[1]);if(Directory.Exists(output))throw new IOException("Output already exists");Directory.CreateDirectory(output);
using Library lib=new(voxel);Library.RegisterGlobalLibrary(lib);
try{
 Voxels Box(Vector3 lo,Vector3 hi)=>new BaseBox(new BBox3(lo,hi)).voxConstruct();
 using Voxels envelope=Box(new(-12,-12,0),new(12,12,11.4f));
 using Voxels hot=Box(new(-12,-11.2f,.8f),new(12,11.2f,3.8f));
 // Four longitudinal ties share the prescribed pressure-wall load path; root fillets remain unresolved.
 foreach(float y in new[]{-9f,-3f,3f,9f}){
  // Extend the cutter beyond the fluid ends to avoid coincident-face interpolation at ports.
  using Voxels rib=Box(new(-13,y-.4f,.6f),new(13,y+.4f,4f));hot.BoolSubtract(rib);
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
 var report=new{status="ribbed_coupon_geometry_and_initial_field_exchange_only",variant="bcc_hot_ribbed",hot_rib_centres_y_mm=new[]{-9f,-3f,3f,9f},hot_rib_thickness_mm=.8f,voxel_mm=voxel,dimensions_mm=new[]{24f,24f,11.4f},wall_mm=.8f,cell_pitch_mm=6f,strut_diameter_mm=.8f,hot_initial_K=hotK,cold_initial_K=coldK,initial_velocity_m_s=1,field_count=7,geometry_roundtrip_exact=true,hot_cold_overlap_empty=true,active_values_checked=samples,scalar_vector_extra_active_values_checked=false,study_sha256=Sha(args[0]),vdb_sha256=Sha(vdb),source_assembly_sha256=Sha(typeof(ScalarCheck).Assembly.Location),thermal_solver_executed=false,hydraulic_solver_executed=false,manufacturing_authorized=false};
 File.WriteAllText(Path.Combine(output,"receipt.json"),JsonSerializer.Serialize(report,new JsonSerializerOptions{WriteIndented=true})+"\n");
 Console.WriteLine(JsonSerializer.Serialize(report));
}finally{Library.UnregisterGlobalLibrary();}

sealed class ScalarCheck(ScalarField restored):ITraverseScalarField{
 public int Count;
 public void InformActiveValue(in Vector3 p,float value){if(!float.IsFinite(value)||!restored.bGetValue(p,out float found)||found!=value)throw new InvalidDataException("Scalar roundtrip changed");Count++;}
}
sealed class VectorCheck(VectorField restored):ITraverseVectorField{
 public int Count;
 public void InformActiveValue(in Vector3 p,in Vector3 value){if(!float.IsFinite(value.LengthSquared())||!restored.bGetValue(p,out Vector3 found)||found!=value)throw new InvalidDataException("Vector roundtrip changed");Count++;}
}
