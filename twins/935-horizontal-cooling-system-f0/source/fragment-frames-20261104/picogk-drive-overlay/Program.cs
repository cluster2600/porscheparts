using System.Security.Cryptography;
using System.Text.Json;
using PicoGK;

if (args.Length != 4) throw new ArgumentException("Usage: SCAN_STL SHAFT_STL SUPPORT_STL NEW_PRIVATE_OUTPUT");
string Hash(string path) { using var s=File.OpenRead(path); return Convert.ToHexString(SHA256.HashData(s)).ToLowerInvariant(); }
string[] expected={"6d7b5c6a35935013659d45af33c63bb2f69f8c82c53092155ba7ac3c07463f72","1f607a95bc107d2e18ea4a5806170652e534e9125561aa7eec730ccb01ee1f4c","637f7fcce78441cd4ef8fa1d33e6c23ba1a3a1a3864276cfcafaba7097cbc38c"};
int[] counts={2484656,2112,94}; string[] labels={"observed-drive","shaft-open-candidate","support-open-candidate"};
string output=Path.GetFullPath(args[3]);
if (File.Exists(output)||Directory.Exists(output)) throw new IOException("Fresh private output required");
bool ok=false; for(DirectoryInfo? d=new(output);d!=null;d=d.Parent) { if(d.LinkTarget!=null) throw new IOException("Symlink ancestry forbidden"); if(File.Exists(Path.Combine(d.FullName,".git"))||Directory.Exists(Path.Combine(d.FullName,".git"))) {ok=Path.GetRelativePath(d.FullName,output).StartsWith("work"+Path.DirectorySeparatorChar);break;} }
if(!ok) throw new IOException("Output must be in ignored work/");
for(int i=0;i<3;i++) if(Hash(args[i])!=expected[i]) throw new InvalidDataException("Input hash mismatch");
Directory.CreateDirectory(output);if(!OperatingSystem.IsWindows()) File.SetUnixFileMode(output,UnixFileMode.UserRead|UnixFileMode.UserWrite|UnixFileMode.UserExecute);
using Library lib=new(.8f); using Mesh combined=new(lib);
for(int i=0;i<3;i++) {
 using Mesh mesh=Mesh.mshFromStlFile(args[i],Mesh.EStlUnit.MM,libSet:lib);
 if(mesh.nTriangleCount()!=counts[i]) throw new InvalidDataException("Unexpected triangle count");
 combined.Append(mesh); File.Copy(args[i],Path.Combine(output,labels[i]+".stl"));
}
string result=Path.Combine(output,"drive-overlay.stl"); combined.SaveToStlFile(result);
for(int i=0;i<3;i++) if(Hash(args[i])!=expected[i]) throw new InvalidDataException("Input changed");
File.WriteAllText(Path.Combine(output,"receipt.json"),JsonSerializer.Serialize(new {status="same_scan_picogk_mesh_overlay_not_mechanical_assembly", labels, input_sha256=expected, triangle_counts=counts, total_triangles=combined.nTriangleCount(), output_sha256=Hash(result), geometry_operation="PicoGK Mesh import and Append, no revoxelization", assumed_mm_per_source_unit=1.0,scale_verified=false,physical_registration_verified=false,mating_interface_verified=false,manufacturing_authorized=false, runtime=new{name=Library.strName(),version=Library.strVersion(),build=Library.strBuildInfo()}},new JsonSerializerOptions{WriteIndented=true})+"\n");
Console.WriteLine($"PicoGK inspection overlay: {combined.nTriangleCount()} triangles");
