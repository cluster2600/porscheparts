using System.Numerics;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Text.Json;
using PicoGK;

// A small analytic sphere verifies software geometry only. It is never a
// cylinder-head model, cooling passage design, or engineering validation.
if (args.Length != 1)
{
    Console.Error.WriteLine("Usage: RuntimeWitness OUTPUT_DIRECTORY");
    return 2;
}
try
{
    string output = Path.GetFullPath(args[0]);
    Directory.CreateDirectory(output);
    using Library library = new(0.5f);
    using Lattice lattice = new(library);
    lattice.AddSphere(Vector3.Zero, 5f);
    using Voxels voxels = new(lattice);
    using Mesh mesh = new(voxels);
    int triangles = mesh.nTriangleCount();
    if (triangles <= 0) throw new Exception("Empty witness mesh");
    string stl = Path.Combine(output, "sphere-radius5mm-voxel0.5mm.stl");
    mesh.SaveToStlFile(stl, Mesh.EStlUnit.MM);
    using Mesh roundtrip = Mesh.mshFromStlFile(stl, Mesh.EStlUnit.MM, libSet: library);
    if (roundtrip.nTriangleCount() != triangles) throw new Exception("STL roundtrip mismatch");
    voxels.CalculateProperties(out float volume, out BBox3 bounds);
    double analyticVolume = 4.0 * Math.PI * Math.Pow(5.0, 3) / 3.0;
    double relativeVolumeError = Math.Abs(volume - analyticVolume) / analyticVolume;
    if (relativeVolumeError > 0.10) throw new Exception("Sphere volume error exceeds smoke tolerance");
    using Voxels inflated = voxels.voxOffset(1.0f);
    inflated.CalculateProperties(out float inflatedVolume, out BBox3 inflatedBounds);
    if (inflatedVolume <= volume) throw new Exception("Positive offset failed to expand witness");
    var report = new
    {
        status = "PASS",
        scope = "software_geometry_witness_only",
        architecture = RuntimeInformation.ProcessArchitecture.ToString(),
        framework = RuntimeInformation.FrameworkDescription,
        voxel_mm = 0.5,
        sphere_radius_mm = 5.0,
        triangles,
        stl_roundtrip_triangles = roundtrip.nTriangleCount(),
        stl_sha256 = Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(stl))).ToLowerInvariant(),
        voxel_volume_mm3 = volume,
        analytic_volume_mm3 = analyticVolume,
        relative_volume_error = relativeVolumeError,
        relative_volume_smoke_tolerance = 0.10,
        bounds_min_mm = new[] { bounds.vecMin.X, bounds.vecMin.Y, bounds.vecMin.Z },
        bounds_max_mm = new[] { bounds.vecMax.X, bounds.vecMax.Y, bounds.vecMax.Z },
        positive_offset_mm = 1.0,
        positive_offset_volume_mm3 = inflatedVolume,
        manufacturing_validated = false,
        engine_validated = false
    };
    File.WriteAllText(Path.Combine(output, "report.json"), JsonSerializer.Serialize(report, new JsonSerializerOptions { WriteIndented = true }) + "\n");
    Console.WriteLine($"NATIVE_GEOMETRY_FILE_SMOKE_PASS triangles={triangles} relative_volume_error={relativeVolumeError:G6}");
    return 0;
}
catch (Exception exception)
{
    Console.Error.WriteLine($"NATIVE_GEOMETRY_FILE_SMOKE_FAIL {exception.GetType().Name}: {exception.Message}");
    return 1;
}
