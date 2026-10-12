using System.Globalization;
using System.Security.Cryptography;
using System.Text.Json;
using System.Numerics;
using PicoGK;

if (args.Length != 4 && args.Length != 5) throw new ArgumentException("Usage: candidate.stl sha256 voxel_mm NEW_PRIVATE_OUTPUT [FEA_pitches_mm_comma_separated]");
string source = Path.GetFullPath(args[0]), output = Path.GetFullPath(args[3]);
string Hash(string p) => Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(p))).ToLowerInvariant();
if (Hash(source) != args[1]) throw new InvalidDataException("Candidate hash mismatch");
float voxel = float.Parse(args[2], CultureInfo.InvariantCulture);
if (!float.IsFinite(voxel) || voxel <= 0 || Directory.Exists(output) || File.Exists(output))
    throw new ArgumentException("Positive finite voxel size and new output required");
for (DirectoryInfo parent = new(output); parent != null; parent = parent.Parent)
    if (File.Exists(Path.Combine(parent.FullName, ".git")) || Directory.Exists(Path.Combine(parent.FullName, ".git")))
    {
        if (!Path.GetRelativePath(parent.FullName, output).StartsWith("work" + Path.DirectorySeparatorChar))
            throw new IOException("Private output must stay in ignored work/");
        break;
    }
using Library library = new(voxel);
using Mesh input = Mesh.mshFromStlFile(source, Mesh.EStlUnit.MM, libSet: library);
if (input.nTriangleCount() == 0) throw new InvalidDataException("Empty input mesh");
using Voxels field = new(input);
field.CalculateProperties(out float volume, out _);
if (!float.IsFinite(volume) || volume <= 0) throw new InvalidDataException("Invalid voxel volume");
Directory.CreateDirectory(output);
using Mesh result = field.mshAsMesh();
string meshPath = Path.Combine(output, "candidate-rotor.stl"); result.SaveToStlFile(meshPath);
if (args.Length == 5)
{
    using ScalarField distances = new(field);
    var box = input.oBoundingBox();
    foreach (float pitch in args[4].Split(',').Select(x => float.Parse(x, CultureInfo.InvariantCulture)))
    {
        if (!float.IsFinite(pitch) || pitch <= 0) throw new ArgumentException("Positive finite FEA pitch required");
        int[] lower = { (int)MathF.Floor(box.vecMin.X/pitch), (int)MathF.Floor(box.vecMin.Y/pitch), (int)MathF.Floor(box.vecMin.Z/pitch) };
        int[] upper = { (int)MathF.Ceiling(box.vecMax.X/pitch), (int)MathF.Ceiling(box.vecMax.Y/pitch), (int)MathF.Ceiling(box.vecMax.Z/pitch) };
        long count = (long)(upper[0]-lower[0]) * (upper[1]-lower[1]) * (upper[2]-lower[2]);
        if (count <= 0 || count > 2000000) throw new ArgumentException("FEA grid exceeds bounded pilot resources");
        var cells = new List<int[]>();
        for (int i=lower[0]; i<upper[0]; i++)
            for (int j=lower[1]; j<upper[1]; j++)
                for (int k=lower[2]; k<upper[2]; k++)
                    if (distances.fSignedDistance(new Vector3((i+.5f)*pitch,(j+.5f)*pitch,(k+.5f)*pitch)) < 0)
                        cells.Add(new[] {i,j,k});
        if (cells.Count == 0) throw new InvalidDataException("Empty FEA grid");
        string name = "fea-grid-" + pitch.ToString(CultureInfo.InvariantCulture) + ".json";
        File.WriteAllText(Path.Combine(output,name), JsonSerializer.Serialize(new {
            schema = "935-signed-distance-hexa-grid-v1", input_sha256 = args[1], field_voxel_mm = voxel,
            pitch_mm = pitch, cells = cells, classification = "cell_centres_inside_hypothesis_SDF", scale_verified = false
        }));
    }
}
if (Hash(source) != args[1]) throw new InvalidDataException("Input changed during voxelization");
File.WriteAllText(Path.Combine(output, "receipt.json"), JsonSerializer.Serialize(new {
    status = "voxelized_rotor_hypothesis_not_historical_replica", input_sha256 = args[1],
    voxel_mm = voxel, conditional_volume_mm3 = volume, output_sha256 = Hash(meshPath),
    triangles = result.nTriangleCount(), runtime = new {name = Library.strName(), version = Library.strVersion(), build = Library.strBuildInfo()},
    scale_verified = false, manufacturing_authorized = false, physical_validation = false
}, new JsonSerializerOptions {WriteIndented = true}) + "\n");
Console.WriteLine($"Conditional volume {volume:R} mm3; {result.nTriangleCount()} triangles");
