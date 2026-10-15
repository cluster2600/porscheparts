using System.Globalization;
using System.Numerics;
using System.Security.Cryptography;
using System.Text.Json;
using PicoGK;
if(args.Length!=4)throw new ArgumentException("Usage: Route recipe.json sha256 voxel_mm new_work_output");
string Hash(string path){using var s=File.OpenRead(path);return Convert.ToHexString(SHA256.HashData(s)).ToLowerInvariant();}
string input=Path.GetFullPath(args[0]),output=Path.GetFullPath(args[3]);float grid=float.Parse(args[2],CultureInfo.InvariantCulture);
if(Hash(input)!=args[1]||grid!=.5f||Path.Exists(output))throw new ArgumentException("Input, grid or output rejected");
bool work=false;
for(DirectoryInfo? d=new(output);d!=null;d=d.Parent)if(File.Exists(Path.Combine(d.FullName,".git"))||Directory.Exists(Path.Combine(d.FullName,".git")))
 {work=Path.GetRelativePath(d.FullName,output).StartsWith("work"+Path.DirectorySeparatorChar,StringComparison.Ordinal);break;}
if(!work)throw new IOException("Output must stay under ignored work/");
using var doc=JsonDocument.Parse(File.ReadAllText(input));var root=doc.RootElement;
if(root.GetProperty("classification").GetString()!="hypothetical_pipe_routes_no_physical_release"||root.GetProperty("manufacturing_authorized").GetBoolean())throw new InvalidDataException("Wrong classification");
Directory.CreateDirectory(output);using Library lib=new(grid);var records=new Dictionary<string,object>();
foreach(var part in root.GetProperty("parts").EnumerateArray())
{
 string id=part.GetProperty("id").GetString()!;
 if(id is not ("intake_negative" or "intake_positive" or "charge_pipe_negative" or "charge_pipe_positive" or "intercooler_bionic_bracket_negative" or "intercooler_bionic_bracket_positive")||records.ContainsKey(id))throw new InvalidDataException("Invalid route ID");
 Vector3 Vec(JsonElement a){var v=a.EnumerateArray().Select(x=>x.GetSingle()).ToArray();if(v.Length!=3||v.Any(x=>!float.IsFinite(x)))throw new InvalidDataException("Invalid point");return new(v[0],v[1],v[2]);}
 void Export(Voxels body)
 {
  if(body.bIsEmpty())throw new InvalidDataException("Empty route");using var mesh=new Mesh(body);string stl=Path.Combine(output,id+".stl"),vdb=Path.Combine(output,id+".vdb");mesh.SaveToStlFile(stl);body.SaveToVdbFile(vdb);body.CalculateProperties(out float volume,out _);
  records[id]=new {stl_sha256=Hash(stl),vdb_sha256=Hash(vdb),triangles=mesh.nTriangleCount(),native_resampled_volume_mm3=volume};Console.WriteLine("EXPORT "+id);
 }
 if(part.TryGetProperty("branches",out var branches))
 {
  if(!id.StartsWith("intercooler_bionic_bracket_",StringComparison.Ordinal))throw new InvalidDataException("Wrong branch classification");
  using Lattice lattice=new(lib);
  foreach(var beam in branches.EnumerateArray())
  {Vector3 a=Vec(beam.GetProperty("a")),b=Vec(beam.GetProperty("b"));float r=beam.GetProperty("r").GetSingle();if(a==b||!float.IsFinite(r)||r<=0||r>20)throw new InvalidDataException("Invalid branch");lattice.AddBeam(a,b,r,r,true);}
  using var solid=new Voxels(lattice);Export(solid);continue;
 }
 Vector3[] p=part.GetProperty("points").EnumerateArray().Select(Vec).ToArray();
 if(p.Length<3||Vector3.Distance(p[0],p[1])<25)throw new InvalidDataException("Flat mouth stub too short");
 float[] Radii(string key,float fallback)=>part.TryGetProperty(key,out var values)?values.EnumerateArray().Select(x=>x.GetSingle()).ToArray():Enumerable.Repeat(fallback,p.Length).ToArray();
 float[] ro=Radii("outer_radii",25),ri=Radii("inner_radii",22.5f);
 if(ro.Length!=p.Length||ri.Length!=p.Length)throw new InvalidDataException("Radius count mismatch");
 for(int i=0;i<p.Length;i++)if(!float.IsFinite(ro[i])||!float.IsFinite(ri[i])||ri[i]<=0||ro[i]>25||ro[i]-ri[i]<2)throw new InvalidDataException("Invalid pipe wall");
 using Lattice outer=new(lib),inner=new(lib);
 for(int i=1;i<p.Length;i++)
 {
  if(p[i]==p[i-1])throw new InvalidDataException("Zero segment");
  outer.AddBeam(p[i-1],p[i],ro[i-1],ro[i],i!=1&&i!=p.Length-1);inner.AddBeam(p[i-1],p[i],ri[i-1],ri[i],true);
 }
 inner.AddBeam(p[0]-Vector3.Normalize(p[1]-p[0])*12,p[0],ri[0],ri[0],false);
 inner.AddBeam(p[^1],p[^1]+Vector3.Normalize(p[^1]-p[^2])*12,ri[^1],ri[^1],false);
 using Voxels body=new(outer),hole=new(inner);
 if(part.TryGetProperty("source_mesh",out var source))
 {string path=source.GetProperty("path").GetString()!;if(Hash(path)!=source.GetProperty("sha256").GetString())throw new InvalidDataException("Trunk hash mismatch");using var m=Mesh.mshFromStlFile(path,Mesh.EStlUnit.MM,libSet:lib);using var v=new Voxels(m);body.BoolAdd(v);}
 // The clipped inherited trunk has an open end beyond the new return junction.
 if(id is "intake_negative" or "intake_positive")
 {
  int bank=id=="intake_negative"?-1:1;using Lattice cap=new(lib);
  cap.AddBeam(new(370.13f,bank*310,155),new(377.13f,bank*310,155),25.13f,25.13f,false);
  using Voxels terminal=new(cap);body.BoolAdd(terminal);
 }
 body.BoolSubtract(hole);if(body.bIsEmpty())throw new InvalidDataException("Empty route");
 Export(body);
}
if(Hash(input)!=args[1])throw new InvalidDataException("Recipe changed");
File.WriteAllText(Path.Combine(output,"receipt.json"),JsonSerializer.Serialize(new {classification="hypothetical_engine_components_not_manufacturing_geometry",parts=records,voxel_mm=grid,kernel=Library.strVersion(),manufacturing_authorized=false,engine_start_authorized=false},new JsonSerializerOptions{WriteIndented=true})+"\n");
