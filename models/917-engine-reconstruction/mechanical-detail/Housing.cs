using System.Globalization;
using System.Numerics;
using System.Security.Cryptography;
using System.Text.Json;
using PicoGK;
if(args.Length!=4)throw new ArgumentException("Usage: Housing recipe.json sha256 voxel_mm new_work_output");
string Hash(string path){using var s=File.OpenRead(path);return Convert.ToHexString(SHA256.HashData(s)).ToLowerInvariant();}
string input=Path.GetFullPath(args[0]),output=Path.GetFullPath(args[3]);float grid=float.Parse(args[2],CultureInfo.InvariantCulture);
if(Hash(input)!=args[1]||grid is not (1f or .5f)||Path.Exists(output))throw new ArgumentException("Hash, grid or output rejected");
bool work=false;
for(DirectoryInfo? d=new(output);d!=null;d=d.Parent)if(File.Exists(Path.Combine(d.FullName,".git"))||Directory.Exists(Path.Combine(d.FullName,".git")))
 {work=Path.GetRelativePath(d.FullName,output).StartsWith("work"+Path.DirectorySeparatorChar,StringComparison.Ordinal);break;}
if(!work)throw new IOException("Output must stay under ignored work/");
using var doc=JsonDocument.Parse(File.ReadAllText(input));var root=doc.RootElement;
if(root.GetProperty("classification").GetString()!="housing_rotation_clearance_no_physical_release"||root.GetProperty("manufacturing_authorized").GetBoolean())throw new InvalidDataException("Physical release rejected");
var source=root.GetProperty("source_vdb");string path=source.GetProperty("path").GetString()!;
if(Hash(path)!=source.GetProperty("sha256").GetString())throw new InvalidDataException("Source field changed");
var gears=root.GetProperty("gear_envelopes").EnumerateArray().Select(g=>g.EnumerateArray().Select(x=>x.GetSingle()).ToArray()).ToArray();
if(gears.Length!=26||gears.Any(g=>g.Length!=4||g.Any(x=>!float.IsFinite(x))||g[3]<=0))throw new InvalidDataException("Invalid gear envelopes");
Directory.CreateDirectory(output);using Library lib=new(grid);using Voxels body=Voxels.voxFromVdbFile(lib,path);using Lattice holes=new(lib);
foreach(var g in gears)holes.AddBeam(new(g[0]-7.13f,g[1],g[2]),new(g[0]+7.13f,g[1],g[2]),g[3]+1.37f,g[3]+1.37f,false);
using(var reserve=new Voxels(holes))body.BoolSubtract(reserve);
body.CalculateProperties(out float volume,out _);if(body.bIsEmpty()||!float.IsFinite(volume)||volume<=0)throw new InvalidDataException("Empty housing");
using Mesh mesh=new(body);string stl=Path.Combine(output,"drive_housing.stl"),vdb=Path.Combine(output,"drive_housing.vdb");mesh.SaveToStlFile(stl);body.SaveToVdbFile(vdb);
if(Hash(input)!=args[1]||Hash(path)!=source.GetProperty("sha256").GetString())throw new InvalidDataException("Inputs changed");
File.WriteAllText(Path.Combine(output,"receipt.json"),JsonSerializer.Serialize(new {classification="hypothetical_engine_components_not_manufacturing_geometry",voxel_mm=grid,kernel=Library.strVersion(),source_vdb_sha256=Hash(path),parts=new Dictionary<string,object>{{"drive_housing",new {stl_sha256=Hash(stl),vdb_sha256=Hash(vdb),triangles=mesh.nTriangleCount(),native_resampled_volume_mm3=volume}}},manufacturing_authorized=false,engine_start_authorized=false},new JsonSerializerOptions{WriteIndented=true})+"\n");
