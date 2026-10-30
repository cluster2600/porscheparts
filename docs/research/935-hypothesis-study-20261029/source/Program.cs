using System.Numerics;
using System.Text.Json;
using System.Security.Cryptography;
using PicoGK;

if (args.Length != 3) throw new ArgumentException("Usage: BuildCandidate INPUT_STL BUILD_HYPOTHESES NEW_OUTPUT");
string output = Path.GetFullPath(args[2]);
if (Directory.Exists(output)) throw new IOException("Refusing existing output");
Directory.CreateDirectory(output);
using JsonDocument document = JsonDocument.Parse(File.ReadAllText(args[1]));
JsonElement hypothesis = document.RootElement;
float[] GetArray(string name) => hypothesis.GetProperty(name).EnumerateArray().Select(x => x.GetSingle()).ToArray();
using Library library = new(0.25f);
using Mesh input = Mesh.mshFromStlFile(args[0], Mesh.EStlUnit.MM, libSet: library);
using Voxels head = new(input);
head.CalculateProperties(out float headVolume, out BBox3 headBounds);
head.SaveToVdbFile(Path.Combine(output, "head-study.vdb"));
using Mesh headMesh = new(head);
headMesh.SaveToStlFile(Path.Combine(output, "head-picogk-study-mm.stl"), Mesh.EStlUnit.MM);
Console.WriteLine($"Head reconstructed: {headMesh.nTriangleCount()} triangles");

using Lattice lattice = new(library);
foreach (JsonElement row in hypothesis.GetProperty("support_columns").EnumerateArray())
{
    float[] c = row.EnumerateArray().Select(x => x.GetSingle()).ToArray();
    Vector3 bottom = new(c[0],c[1],c[2]);
    Vector3 shoulder = new(c[0],c[1],c[3]-1);
    Vector3 top = new(c[0],c[1],c[3]);
    lattice.AddBeam(bottom,1.2f,shoulder,1.2f,false);
    lattice.AddBeam(shoulder,1.2f,top,.5f,false);
}
using Voxels supports = new(lattice);
using Mesh supportMesh = new(supports);
supportMesh.SaveToStlFile(Path.Combine(output,"supports-provisional-mm.stl"),Mesh.EStlUnit.MM);
float[] plate = GetArray("base_plate_mm");
Vector3 plateMax = new(plate[0],plate[1],plate[2]);
IImplicit plateShape = new Box(plateMax/2,plateMax/2);
BBox3 plateBox = new(Vector3.Zero,plateMax);
using Voxels basePlate = new(library,plateShape,plateBox);
float[] centre=GetArray("coupon_centre_mm");
Vector3 couponBottom = new(centre[0],centre[1],centre[2]);
Vector3 couponTop = couponBottom+new Vector3(0,0,20);
using Lattice couponLattice = new(library);
couponLattice.AddBeam(couponBottom,6f,couponTop,6f,false);
using Voxels coupon = new(couponLattice);
using Mesh couponMesh = new(coupon);
couponMesh.SaveToStlFile(Path.Combine(output,"qwen-coupon-12x20-mm.stl"),Mesh.EStlUnit.MM);
using Voxels assembly = head + supports;
assembly.BoolAdd(basePlate);
assembly.BoolAdd(coupon);
assembly.CalculateProperties(out float assemblyVolume,out BBox3 assemblyBounds);
using Mesh assemblyMesh = new(assembly);
assemblyMesh.SaveToStlFile(Path.Combine(output,"build-candidate-provisional-mm.stl"),Mesh.EStlUnit.MM);
assembly.SaveToVdbFile(Path.Combine(output,"build-candidate-provisional.vdb"));
Console.WriteLine($"Build candidate: {assemblyMesh.nTriangleCount()} triangles. Slicing...");
assembly.SaveToCliFile(Path.Combine(output,"build-candidate-30um.cli"),.03f,CliIo.EFormat.FirstLayerWithContent,true);
var report = new {
    scope="conditional monolithic demonstrator with provisional supports, not a qualified engine head or machine job",
    voxel_mm=.25,layer_mm=.03,head_volume_mm3=headVolume,assembly_volume_mm3=assemblyVolume,
    input_triangles=input.nTriangleCount(),head_triangles=headMesh.nTriangleCount(),assembly_triangles=assemblyMesh.nTriangleCount(),
    bounds_min_mm=new[]{assemblyBounds.vecMin.X,assemblyBounds.vecMin.Y,assemblyBounds.vecMin.Z},
    bounds_max_mm=new[]{assemblyBounds.vecMax.X,assemblyBounds.vecMax.Y,assemblyBounds.vecMax.Z},
    source_stl_sha256=Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(args[0]))).ToLowerInvariant(),
    manufacturing_qualified=false,engine_qualified=false
};
File.WriteAllText(Path.Combine(output,"report.json"),JsonSerializer.Serialize(report,new JsonSerializerOptions{WriteIndented=true})+"\n");
Console.WriteLine("Conditional build geometry and layer contours exported.");

sealed class Box(Vector3 centre,Vector3 halfSize):IImplicit
{
    public float fSignedDistance(in Vector3 position)
    {
        Vector3 q=Vector3.Abs(position-centre)-halfSize;
        return Vector3.Max(q,Vector3.Zero).Length()+MathF.Min(MathF.Max(q.X,MathF.Max(q.Y,q.Z)),0);
    }
}
