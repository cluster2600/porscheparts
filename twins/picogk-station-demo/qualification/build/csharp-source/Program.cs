using System.Globalization;
using System.Numerics;
using System.Security.Cryptography;
using System.Text.Json;
using PicoGK;

// Software witnesses in designed millimetres; no Porsche fitment or strength claim.
if (args.Length != 3 ||
    !float.TryParse(args[1], NumberStyles.Float, CultureInfo.InvariantCulture, out float span) ||
    !float.TryParse(args[2], NumberStyles.Float, CultureInfo.InvariantCulture, out float voxel) ||
    !float.IsFinite(span) || span < 20 || span > 80 ||
    !float.IsFinite(voxel) || voxel < 0.1f || voxel > 0.5f)
{
    Console.Error.WriteLine("Usage: StationDemo NEW_OUTPUT_DIR SPAN_MM[20..80] VOXEL_MM[0.1..0.5]");
    return 2;
}
string output = Path.GetFullPath(args[0]);
if (Directory.Exists(output) || File.Exists(output))
{
    Console.Error.WriteLine("Output already exists; refusing to overwrite.");
    return 2;
}
Directory.CreateDirectory(output);
try
{
    using Library library = new(voxel);
    var records = new List<object>();
    void Save(string name, Lattice lattice)
    {
        using Voxels solid = new(lattice);
        solid.CalculateProperties(out float volume, out BBox3 box);
        using Mesh mesh = new(solid);
        if (!float.IsFinite(volume) || volume <= 0 || mesh.nTriangleCount() <= 0)
            throw new InvalidDataException("Empty witness geometry");
        string path = Path.Combine(output, name + ".stl");
        mesh.SaveToStlFile(path, Mesh.EStlUnit.MM);
        using Mesh reread = Mesh.mshFromStlFile(path, Mesh.EStlUnit.MM, libSet: library);
        if (reread.nTriangleCount() != mesh.nTriangleCount())
            throw new InvalidDataException("STL roundtrip mismatch");
        records.Add(new {
            id = name, file = name + ".stl", volume_mm3 = volume,
            triangles = mesh.nTriangleCount(),
            sha256 = Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(path))).ToLowerInvariant(),
            bounds_min_mm = new[] { box.vecMin.X, box.vecMin.Y, box.vecMin.Z },
            bounds_max_mm = new[] { box.vecMax.X, box.vecMax.Y, box.vecMax.Z }
        });
    }
    using (Lattice bracket = new(library))
    {
        Vector3[] p = [new(-span/2, 0, 3), new(span/2, 0, 3), new(span/2, 0, 18), new(-span/2, 0, 18)];
        for (int i = 0; i < p.Length; ++i)
            bracket.AddBeam(p[i], 2.5f, p[(i+1)%p.Length], 2.5f);
        Save("bracket-witness", bracket);
    }
    foreach (float radius in new[] { 1.5f, 3.0f })
    {
        using Lattice coupon = new(library);
        coupon.AddBeam(new Vector3(0, 0, radius), radius, new Vector3(20, 0, radius), radius);
        Save(radius < 2 ? "coupon-thin" : "coupon-thick", coupon);
    }
    File.WriteAllText(Path.Combine(output, "geometry.json"), JsonSerializer.Serialize(new {
        schema_version = "1.0.0", status = "software_witness_only", units = "mm",
        source = "twins/picogk-station-demo/Program.cs", span_mm = span, voxel_mm = voxel,
        parts = records, physical_coupon_tested = false, manufacturing_authorized = false
    }, new JsonSerializerOptions { WriteIndented = true }) + "\n");
    Console.WriteLine("STATION_GEOMETRY_PASS");
    return 0;
}
catch (Exception exception)
{
    File.WriteAllText(Path.Combine(output, "FAILED.json"), JsonSerializer.Serialize(new {
        status = "failed", error = exception.Message, manufacturing_authorized = false
    }));
    Console.Error.WriteLine("STATION_GEOMETRY_FAIL: " + exception.Message);
    return 1;
}
