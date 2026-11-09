using System.Numerics;
using System.Security.Cryptography;
using System.Text.Json;
using PicoGK;

if (args.Length != 5) throw new ArgumentException("SOURCE_VDB SOURCE_STL PROBES_JSON NEW_OUTPUT VOXEL_MM");
string vdbPath=Path.GetFullPath(args[0]),stlPath=Path.GetFullPath(args[1]),probePath=Path.GetFullPath(args[2]),output=Path.GetFullPath(args[3]);
float voxel=float.Parse(args[4],System.Globalization.CultureInfo.InvariantCulture);
if (!float.IsFinite(voxel) || voxel<=0 || Directory.Exists(output) || File.Exists(output)) throw new InvalidDataException("Expected positive voxel size and fresh output");
string Hash(string path) { using FileStream f=File.OpenRead(path);return Convert.ToHexString(SHA256.HashData(f)).ToLowerInvariant(); }
string originalVdbHash=Hash(vdbPath),originalStlHash=Hash(stlPath),originalProbeHash=Hash(probePath);
Directory.CreateDirectory(output);
var watch=System.Diagnostics.Stopwatch.StartNew();
using Library lib=new(voxel);Library.RegisterGlobalLibrary(lib);
try
{
    using OpenVdbFile file=new(lib,vdbPath);
    using Voxels field=file.voxGet("assumed_sculpted_cell");
    using Mesh mesh=new(field);
    int vertices=mesh.nVertexCount(),triangles=mesh.nTriangleCount();
    Console.WriteLine($"Native indexed mesh: {vertices} vertices, {triangles} triangles");
    string regenerated=Path.Combine(output,"reextracted.stl");
    mesh.SaveToStlFile(regenerated,Mesh.EStlUnit.MM);
    string regeneratedHash=Hash(regenerated);
    bool identicalStl=regeneratedHash==originalStlHash;
    // Native indices are used directly. No position quantisation, point merge,
    // reconstruction, voxel operation or geometric simplification occurs here.
    string vp=Path.Combine(output,"vertices.f32"),tp=Path.Combine(output,"triangles.i32");
    using (BinaryWriter writer=new(new FileStream(vp,FileMode.CreateNew,FileAccess.Write,FileShare.None,1<<20)))
        for (int i=0;i<vertices;i++) { Vector3 p=mesh.vecVertexAt(i);writer.Write(p.X);writer.Write(p.Y);writer.Write(p.Z); }
    int[] parent=new int[vertices],size=new int[vertices];
    for (int i=0;i<vertices;i++) {parent[i]=i;size[i]=1;}
    int Find(int x) {while (parent[x]!=x) {parent[x]=parent[parent[x]];x=parent[x];}return x;}
    int regions=vertices;
    void Join(int a,int b) {a=Find(a);b=Find(b);if (a==b)return;if (size[a]<size[b]) (a,b)=(b,a);parent[b]=a;size[a]+=size[b];regions--;}
    using (BinaryWriter writer=new(new FileStream(tp,FileMode.CreateNew,FileAccess.Write,FileShare.None,1<<20)))
        for (int i=0;i<triangles;i++)
        {
            Triangle t=mesh.oTriangleAt(i);
            if (t.A<0 || t.B<0 || t.C<0 || t.A>=vertices || t.B>=vertices || t.C>=vertices) throw new InvalidDataException("Native index outside vertex array");
            writer.Write(t.A);writer.Write(t.B);writer.Write(t.C);Join(t.A,t.B);Join(t.B,t.C);
        }
    int largest=0;for (int i=0;i<vertices;i++) if (parent[i]==i) largest=Math.Max(largest,size[i]);
    using JsonDocument probes=JsonDocument.Parse(File.ReadAllText(probePath));
    var observations=new List<object>();int failed=0;
    foreach (JsonElement p in probes.RootElement.GetProperty("probes").EnumerateArray())
    {
        JsonElement a=p.GetProperty("point_mm");Vector3 point=new(a[0].GetSingle(),a[1].GetSingle(),a[2].GetSingle());
        bool inside=field.bIsInside(point);bool? expected=p.GetProperty("expected_inside").ValueKind==JsonValueKind.Null?null:p.GetProperty("expected_inside").GetBoolean();
        if (expected is not null && inside!=expected)failed++;
        observations.Add(new {label=p.GetProperty("label").GetString(),probe_class=p.GetProperty("class").GetString(),point_mm=new[] {point.X,point.Y,point.Z},expected_inside=expected,observed_inside=inside});
    }
    if (Hash(vdbPath)!=originalVdbHash || Hash(stlPath)!=originalStlHash || Hash(probePath)!=originalProbeHash) throw new InvalidDataException("Original input changed during export");
    var report=new {
        status=identicalStl?"exact_native_indexed_export":"native_reextraction_order_or_geometry_difference_needs_review",
        source_vdb_sha256=originalVdbHash,source_stl_sha256=originalStlHash,probes_sha256=originalProbeHash,
        reextracted_stl_sha256=regeneratedHash,reextracted_stl_byte_identical=identicalStl,
        vertex_count=vertices,triangle_count=triangles,vertices_f32_sha256=Hash(vp),triangles_i32_sha256=Hash(tp),
        binary_format="Little-endian float32 XYZ vertices and int32 zero-based triangular indices; native vertex/triangle ordering",
        indexed_graph_components=regions,largest_component_vertices=largest,
        connectivity_scope="Union-find on native vertex-index adjacency, without geometric deduplication; not a manifoldness, complete-edge structural-junction or physical-load-path proof",
        finite_occupancy_probe_failures=failed,finite_occupancy_observations=observations,
        program_binary_sha256=Hash(System.Reflection.Assembly.GetExecutingAssembly().Location),
        framework_description=System.Runtime.InteropServices.RuntimeInformation.FrameworkDescription,
        runtime_version=Environment.Version.ToString(),
        process_architecture=System.Runtime.InteropServices.RuntimeInformation.ProcessArchitecture.ToString(),
        elapsed_seconds=watch.Elapsed.TotalSeconds,
        geometry_changed=false,continuous_clearance_verified=false,wall_convergence_verified=false,manufacturing_authorized=false
    };
    File.WriteAllText(Path.Combine(output,"report.json"),JsonSerializer.Serialize(report,new JsonSerializerOptions {WriteIndented=true})+"\n");
    Console.WriteLine($"Indexed export complete; byte-identical STL={identicalStl}, graph components={regions}, probe failures={failed}");
}
finally {Library.UnregisterGlobalLibrary();}
