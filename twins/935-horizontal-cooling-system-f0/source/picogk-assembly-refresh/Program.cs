using System.Security.Cryptography;
using System.Text.Json;
using PicoGK;

if (args.Length != 3) throw new ArgumentException("Usage: case.json sha256 NEW_PRIVATE_OUTPUT");
string Hash(string p) { using var s=File.OpenRead(p); return Convert.ToHexString(SHA256.HashData(s)).ToLowerInvariant(); }
string source=Path.GetFullPath(args[0]), output=Path.GetFullPath(args[2]);
if (Hash(source)!=args[1] || Directory.Exists(output) || File.Exists(output)) throw new IOException("Pinned case and fresh output required");
bool privateOutput=false;
for (DirectoryInfo p=new(output);p!=null;p=p.Parent)
{
    if (p.LinkTarget!=null) throw new IOException("Output ancestry must not contain symlinks");
    if (File.Exists(Path.Combine(p.FullName,".git")) || Directory.Exists(Path.Combine(p.FullName,".git")))
    { privateOutput=Path.GetRelativePath(p.FullName,output).StartsWith("work"+Path.DirectorySeparatorChar);break; }
}
if (!privateOutput) throw new IOException("Derived geometry must stay in ignored repository work/");
using var doc=JsonDocument.Parse(File.ReadAllText(source));var c=doc.RootElement;
string[] flags={"scale_verified","interfaces_verified","mechanism_dynamics_validated","historical_installation_verified","manufacturing_authorized","physical_validation"};
if (c.GetProperty("target").GetString()!="935" || c.GetProperty("engine_cylinders").GetInt32()!=6 || c.GetProperty("scale_verified").GetBoolean())
    throw new InvalidDataException("Uncalibrated six-cylinder 935 inspection case required");
var parts=c.GetProperty("composition").GetProperty("parts").EnumerateArray().ToArray();
string[] ids={"engine_context","drive_observed","rotor_candidate","provisional_shroud"};
if (parts.Length!=4 || !parts.Select(p=>p.GetProperty("id").GetString()).Order().SequenceEqual(ids.Order()))
    throw new InvalidDataException("Exactly four retained 935 components required");
var rows=new List<JsonElement>();
foreach (var p in parts)
{
    string path=p.GetProperty("path").GetString(), receiptPath=p.GetProperty("receipt_path").GetString();
    if (Hash(path)!=p.GetProperty("sha256").GetString() || Hash(receiptPath)!=p.GetProperty("receipt_sha256").GetString())
        throw new InvalidDataException("Component or construction receipt changed");
    using var parent=JsonDocument.Parse(File.ReadAllText(receiptPath));var pr=parent.RootElement;
    if (pr.GetProperty("target").GetString()!="935" || pr.GetProperty("engine_cylinders").GetInt32()!=6 || flags.Any(f=>pr.GetProperty(f).GetBoolean()))
        throw new InvalidDataException("Retain unqualified 935 lineage flags");
    var row=pr.GetProperty("components").EnumerateArray().Single(r=>r.GetProperty("id").GetString()==p.GetProperty("id").GetString());
    if (row.GetProperty("sha256").GetString()!=p.GetProperty("sha256").GetString() || row.GetProperty("file").GetString()!=p.GetProperty("id").GetString()+".stl")
        throw new InvalidDataException("Construction receipt does not own this component");
    rows.Add(row.Clone());
}
Directory.CreateDirectory(output);File.SetUnixFileMode(output,UnixFileMode.UserRead|UnixFileMode.UserWrite|UnixFileMode.UserExecute);
File.Copy(source,Path.Combine(output,"case.json"));
using Library library=new(.8f);using Mesh combined=new(library);
for (int i=0;i<parts.Length;i++)
{
    var p=parts[i];string path=p.GetProperty("path").GetString();
    using Mesh mesh=Mesh.mshFromStlFile(path,Mesh.EStlUnit.MM,libSet:library);
    if (mesh.nTriangleCount()!=rows[i].GetProperty("triangles").GetInt32()) throw new InvalidDataException("Triangle count changed");
    combined.Append(mesh);File.Copy(path,Path.Combine(output,rows[i].GetProperty("file").GetString()));
    Console.WriteLine($"Retained {p.GetProperty("id").GetString()}: {mesh.nTriangleCount()} triangles");
}
combined.SaveToStlFile(Path.Combine(output,"assembly-inspection.stl"));
if (Hash(source)!=args[1] || parts.Any(p=>Hash(p.GetProperty("path").GetString())!=p.GetProperty("sha256").GetString() || Hash(p.GetProperty("receipt_path").GetString())!=p.GetProperty("receipt_sha256").GetString()))
    throw new InvalidDataException("Input changed during composition");
File.WriteAllText(Path.Combine(output,"receipt.json"),JsonSerializer.Serialize(new {
    status="PicoGK_inspection_assembly_not_verified_installation",stage="assembly_refresh",target="935",engine_cylinders=6,
    case_sha256=args[1],components=rows,assembly_sha256=Hash(Path.Combine(output,"assembly-inspection.stl")),
    engine_context_family="935_six_cylinder_packaging_hypothesis_not_exact_engine",
    geometry_creation_route="PicoGK native Mesh import and Append; original component files retained byte for byte; no revoxelization or coordinate transform",
    component_source_receipts=parts.Select(p=>new {id=p.GetProperty("id").GetString(),sha256=p.GetProperty("receipt_sha256").GetString()}),
    runtime=new {name=Library.strName(),version=Library.strVersion(),build=Library.strBuildInfo()},
    source_coordinate_unit="uncalibrated_scan_unit",millimetres_are_assumed=true,
    scale_verified=false,interfaces_verified=false,mechanism_dynamics_validated=false,historical_installation_verified=false,
    manufacturing_authorized=false,physical_validation=false
},new JsonSerializerOptions{WriteIndented=true})+"\n");
