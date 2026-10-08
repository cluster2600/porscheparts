using System.Numerics;
using System.Text.Json;
using PicoGK;
using PicoGK993Batch;

// Headless batch: no viewer. Usage:
//   PicoGK993Batch <params-dir> <out-dir> [part-id ...]
// Each params/<id>.json yields out/<id>.stl and out/<id>.report.json.
// Output geometry is an F0 concept: values tagged "assumption" are not evidence.

string paramsDir = args.Length > 0 ? args[0] : "params";
string outDir = args.Length > 1 ? args[1] : "out";
HashSet<string> only = args.Skip(2).Select(a => a.ToUpperInvariant()).ToHashSet();
Directory.CreateDirectory(outDir);

int failures = 0;
foreach (string path in Directory.GetFiles(paramsDir, "*.json").OrderBy(p => p))
{
    PartSpec spec = PartSpec.Load(path);
    if (only.Count > 0 && !only.Contains(spec.PartId.ToUpperInvariant()))
        continue;
    try
    {
        var clock = System.Diagnostics.Stopwatch.StartNew();
        using Library lib = new(spec.VoxelMm);
        Voxels part = Parts.Build(lib, spec);
        part.CalculateProperties(out float volumeMm3, out BBox3 bounds);
        if (volumeMm3 <= 0f) throw new Exception("empty geometry");

        Mesh mesh = new(part);
        // Mesh-based volume: CalculateProperties does not subtract fully enclosed voids.
        volumeMm3 = MeshVolume(mesh);
        string stl = Path.Combine(outDir, spec.PartId + ".stl");
        mesh.SaveToStlFile(stl);

        Vector3 size = bounds.vecMax - bounds.vecMin;
        var basisCounts = spec.Parameters.Values.GroupBy(p => p.Basis).ToDictionary(g => g.Key, g => g.Count());
        var report = new
        {
            part_id = spec.PartId,
            name = spec.Name,
            status = spec.Status,
            safety_class = spec.SafetyClass,
            kernel = $"{PicoGK.Library.strName()} {PicoGK.Library.strVersion()}",
            voxel_mm = spec.VoxelMm,
            triangles = mesh.nTriangleCount(),
            volume_mm3 = Math.Round(volumeMm3, 1),
            bbox_mm = new[] { Math.Round(size.X, 2), Math.Round(size.Y, 2), Math.Round(size.Z, 2) },
            material_candidate = spec.MaterialCandidate,
            mass_estimate_g = Math.Round(volumeMm3 / 1000.0 * spec.DensityGCm3, 1),
            parameter_basis_counts = basisCounts,
            open_interfaces = spec.OpenInterfaces,
            stl = Path.GetFileName(stl),
            seconds = Math.Round(clock.Elapsed.TotalSeconds, 1),
        };
        File.WriteAllText(Path.Combine(outDir, spec.PartId + ".report.json"),
            JsonSerializer.Serialize(report, new JsonSerializerOptions { WriteIndented = true }));
        Console.WriteLine($"OK   {spec.PartId,-44} bbox {size.X:F1} x {size.Y:F1} x {size.Z:F1} mm  " +
                          $"vol {volumeMm3 / 1000f:F1} cm3  mass~{report.mass_estimate_g} g  ({report.seconds}s)");
    }
    catch (Exception e)
    {
        failures++;
        Console.Error.WriteLine($"FAIL {spec.PartId}: {e.GetType().Name}: {e.Message}");
    }
}
return failures == 0 ? 0 : 1;

static float MeshVolume(Mesh m)
{
    double v = 0;
    for (int i = 0; i < m.nTriangleCount(); i++)
    {
        m.GetTriangle(i, out Vector3 a, out Vector3 b, out Vector3 c);
        v += Vector3.Dot(a, Vector3.Cross(b, c)) / 6.0;
    }
    return (float)Math.Abs(v);
}
