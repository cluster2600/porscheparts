using System.Numerics;
using System.Security.Cryptography;
using System.Text.Json;
using PicoGK;

if (args.Length != 3) throw new ArgumentException("Usage: PicoGKClip INPUT_STL PLANES_JSON NEW_OUTPUT");
string output = Path.GetFullPath(args[2]);
if (Directory.Exists(output)) throw new IOException("Existing output refused");
Directory.CreateDirectory(output);
using JsonDocument document = JsonDocument.Parse(File.ReadAllText(args[1]));
float[][] planes = document.RootElement.EnumerateArray()
    .Select(row => row.GetProperty("keep_negative_halfspace_coefficients").EnumerateArray().Select(x => x.GetSingle()).ToArray()).ToArray();
using Library library = new(0.25f);
using Mesh input = Mesh.mshFromStlFile(args[0], Mesh.EStlUnit.MM, libSet: library);
using Voxels head = new(input);
head.CalculateProperties(out float inputVolume, out BBox3 bounds);
BBox3 maskBounds=new(bounds.vecMin-new Vector3(1),bounds.vecMax+new Vector3(1));
using Voxels clip = new(library, new Halfspaces(planes), maskBounds);
head.BoolIntersect(clip);
head.CalculateProperties(out float volume, out BBox3 clippedBounds);
using Mesh result = new(head);
result.SaveToStlFile(Path.Combine(output,"picogk-head-hypothesis-mm.stl"),Mesh.EStlUnit.MM);
var report = new {
    scope="Actual head clipping route under the same construction hypotheses; independent geometry acceptance is required",
    voxel_mm=0.25, input_triangles=input.nTriangleCount(), output_triangles=result.nTriangleCount(),
    input_volume_mm3=inputVolume, output_volume_mm3=volume,
    source_stl_sha256=Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(args[0]))).ToLowerInvariant(),
    physical_acceptance=false, manufacturing_qualified=false, engine_qualified=false
};
File.WriteAllText(Path.Combine(output,"report.json"),JsonSerializer.Serialize(report,new JsonSerializerOptions{WriteIndented=true})+"\n");
Console.WriteLine(JsonSerializer.Serialize(report));

sealed class Halfspaces(float[][] planes):IImplicit {
    public float fSignedDistance(in Vector3 point) {
        float value=float.NegativeInfinity;
        foreach(float[] plane in planes) {
            Vector3 normal=new(plane[0],plane[1],plane[2]);
            value=MathF.Max(value,(Vector3.Dot(normal,point)+plane[3])/normal.Length());
        }
        return value;
    }
}
