using System.Numerics;
using System.Reflection;
using System.Text.Json;
using PicoGK;

namespace PicoGKCatalog;

/// One PicoGK generator per catalogue part. Implementations are discovered by
/// reflection, so each group project only adds files, never edits a registry.
public interface IPartGenerator
{
    /// Matches "generator" in params/<part-id>.json.
    string Name { get; }
    Voxels Build(Library lib, PartSpec spec);
}

public static class Runner
{
    // Usage: <exe> <params.json> <out-dir>
    // Writes <out-dir>/<PART_ID>.stl and <PART_ID>.report.json. Volume is the
    // mesh volume (CalculateProperties ignores fully enclosed voids).
    public static int Main(string[] args)
    {
        if (args.Length < 2)
        {
            Console.Error.WriteLine("usage: <exe> <params.json> <out-dir>");
            return 2;
        }
        PartSpec spec = PartSpec.Load(args[0]);
        string outDir = args[1];
        Directory.CreateDirectory(outDir);
        var generators = Assembly.GetExecutingAssembly().GetTypes()
            .Where(t => typeof(IPartGenerator).IsAssignableFrom(t) && t is { IsInterface: false, IsAbstract: false })
            .Select(t => (IPartGenerator)Activator.CreateInstance(t)!)
            .ToDictionary(g => g.Name);
        if (!generators.TryGetValue(spec.Generator, out IPartGenerator? gen))
        {
            Console.Error.WriteLine($"FAIL {spec.PartId}: no generator '{spec.Generator}' in this project " +
                                    $"({string.Join(", ", generators.Keys)})");
            return 2;
        }
        var clock = System.Diagnostics.Stopwatch.StartNew();
        using Library lib = new(spec.VoxelMm);
        Voxels part = gen.Build(lib, spec);
        BBox3 bounds = part.oCalculateBoundingBox();
        Mesh mesh = new(part);
        if (mesh.nTriangleCount() == 0) { Console.Error.WriteLine($"FAIL {spec.PartId}: empty geometry"); return 1; }
        string stl = Path.Combine(outDir, spec.PartId + ".stl");
        mesh.SaveToStlFile(stl);
        double vol = 0;
        for (int i = 0; i < mesh.nTriangleCount(); i++)
        {
            mesh.GetTriangle(i, out Vector3 a, out Vector3 b, out Vector3 c);
            vol += Vector3.Dot(a, Vector3.Cross(b, c)) / 6.0;
        }
        Vector3 size = bounds.vecMax - bounds.vecMin;
        var report = new
        {
            part_id = spec.PartId,
            generator = spec.Generator,
            status = spec.Status,
            kernel = $"{Library.strName()} {Library.strVersion()}",
            voxel_mm = spec.VoxelMm,
            triangles = mesh.nTriangleCount(),
            volume_cm3 = Math.Round(Math.Abs(vol) / 1000.0, 2),
            mass_estimate_g = Math.Round(Math.Abs(vol) / 1000.0 * spec.DensityGCm3, 1),
            bbox_mm = new[] { Math.Round(size.X, 1), Math.Round(size.Y, 1), Math.Round(size.Z, 1) },
            parameter_basis_counts = spec.Parameters.Values.GroupBy(p => p.Basis).ToDictionary(g => g.Key, g => g.Count()),
            seconds = Math.Round(clock.Elapsed.TotalSeconds, 1),
        };
        string text = JsonSerializer.Serialize(report, new JsonSerializerOptions { WriteIndented = true }).Replace("\r\n", "\n") + "\n";
        File.WriteAllText(Path.Combine(outDir, spec.PartId + ".report.json"), text);
        Console.WriteLine($"OK   {spec.PartId}  bbox {size.X:F1} x {size.Y:F1} x {size.Z:F1} mm  " +
                          $"{report.volume_cm3} cm3  {report.triangles} tris  {report.seconds}s");
        return 0;
    }
}
