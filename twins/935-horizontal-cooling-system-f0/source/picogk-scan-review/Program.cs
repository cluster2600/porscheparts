using System.Globalization;
using System.Numerics;
using System.Security.Cryptography;
using System.Text.Json;
using PicoGK;

// Headless runtime witness and private open-mesh round trip. No scan voxelisation.
internal static class Program
{
    static readonly CultureInfo Invariant = CultureInfo.InvariantCulture;
    static string Hash(string path) => Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(path))).ToLowerInvariant();
    static void Require(bool condition, string message)
    {
        if (!condition) throw new InvalidDataException(message);
    }

    static void PrivateDirectory(string path)
    {
        Require(!Directory.Exists(path) && !File.Exists(path), "Output must be a new private directory");
        // Refuse publication into any enclosing Git checkout, except its ignored work directory.
        for (DirectoryInfo? parent = new(path); parent != null; parent = parent.Parent)
            if (File.Exists(Path.Combine(parent.FullName, ".git")) || Directory.Exists(Path.Combine(parent.FullName, ".git")))
            {
                var relative = Path.GetRelativePath(parent.FullName, path);
                Require(relative.StartsWith("work" + Path.DirectorySeparatorChar, StringComparison.Ordinal),
                        "Geometry output inside a checkout must be under ignored work/");
                break;
            }
        Directory.CreateDirectory(path);
        if (!OperatingSystem.IsWindows()) File.SetUnixFileMode(path, UnixFileMode.UserRead | UnixFileMode.UserWrite | UnixFileMode.UserExecute);
    }

    static void Receipt(string directory, object data)
    {
        var path = Path.Combine(directory, "receipt.json");
        File.WriteAllText(path, JsonSerializer.Serialize(data, new JsonSerializerOptions { WriteIndented = true }) + "\n");
        if (!OperatingSystem.IsWindows())
            foreach (var file in Directory.EnumerateFiles(directory))
                File.SetUnixFileMode(file, UnixFileMode.UserRead | UnixFileMode.UserWrite);
    }

    static object Runtime() => new { name = Library.strName(), version = Library.strVersion(), build = Library.strBuildInfo() };

    static void Witness(string output)
    {
        PrivateDirectory(output);
        using Library library = new(0.5f);
        using Lattice outer = new(library);
        using Lattice bore = new(library);
        outer.AddBeam(new Vector3(0, 0, 0), new Vector3(0, 0, 30), 20, 20, false);
        bore.AddBeam(new Vector3(0, 0, -2), new Vector3(0, 0, 32), 10, 10, false);
        using Voxels gauge = new(outer);
        using Voxels cut = new(bore);
        gauge.BoolSubtract(cut);
        gauge.CalculateProperties(out float volume, out _);
        double analytic = Math.PI * (20 * 20 - 10 * 10) * 30;
        double error = Math.Abs(volume / analytic - 1);
        bool probes = !gauge.bIsInside(new Vector3(0, 0, 15))
                      && gauge.bIsInside(new Vector3(15, 0, 15))
                      && !gauge.bIsInside(new Vector3(25, 0, 15));
        Require(probes && error < 0.03, "Synthetic annulus witness failed");
        Receipt(output, new { status = "synthetic_runtime_witness_passed", runtime = Runtime(),
            voxel_size_mm = 0.5, analytic_volume_mm3 = analytic, voxel_volume_mm3 = volume,
            relative_volume_error = error, interior_probes_passed = probes,
            scan_geometry_used = false, fan_reconstruction_validated = false });
    }

    static double Number(string text)
    {
        double value = double.Parse(text, NumberStyles.Float, Invariant);
        Require(double.IsFinite(value) && float.IsFinite((float)value), "Non-finite or non-representable vertex");
        return value;
    }

    static void MeshRoundTrip(string source, string expected, string output)
    {
        string inputHash = Hash(source);
        Require(inputHash == expected, "Input hash mismatch");
        PrivateDirectory(output);
        using Library library = new(0.5f); // Voxel size unused: mesh stays in unknown source units.
        using Mesh mesh = new(library);
        List<Triangle> faces = [];
        bool sawFaces = false;
        double maximumError = 0;
        foreach (string line in File.ReadLines(source))
        {
            string[] fields = line.Split((char[]?)null, StringSplitOptions.RemoveEmptyEntries);
            if (fields.Length == 0 || fields[0].StartsWith('#')) continue;
            if (fields[0] == "v")
            {
                Require(!sawFaces && fields.Length == 4, "Position-only vertices must precede faces");
                double x = Number(fields[1]), y = Number(fields[2]), z = Number(fields[3]);
                int expectedIndex = mesh.nVertexCount();
                Require(mesh.nAddVertex(new Vector3((float)x, (float)y, (float)z)) == expectedIndex, "Vertex indices changed");
                var actual = mesh.vecVertexAt(expectedIndex);
                double distance = Math.Sqrt(Math.Pow(actual.X - x, 2) + Math.Pow(actual.Y - y, 2) + Math.Pow(actual.Z - z, 2));
                maximumError = Math.Max(maximumError, distance);
            }
            else if (fields[0] == "f")
            {
                sawFaces = true;
                Require(fields.Length == 4, "Triangular position-only faces required");
                int[] indices = fields.Skip(1).Select(v => int.Parse(v, NumberStyles.None, Invariant) - 1).ToArray();
                Require(indices.All(v => v >= 0 && v < mesh.nVertexCount()), "Invalid positive vertex index");
                Require(mesh.nAddTriangle(indices[0], indices[1], indices[2]) == faces.Count, "Triangle indices changed");
                faces.Add(new Triangle(indices[0], indices[1], indices[2]));
            }
            else throw new InvalidDataException("Unsupported OBJ record");
        }
        Require(mesh.nVertexCount() > 0 && faces.Count > 0 && mesh.nTriangleCount() == faces.Count, "Empty or changed mesh");
        for (int i = 0; i < faces.Count; i++)
        {
            var actual = mesh.oTriangleAt(i);
            Require(actual.A == faces[i].A && actual.B == faces[i].B && actual.C == faces[i].C,
                    "Native mesh connectivity changed");
        }
        string export = Path.Combine(output, "picogk-open-scan.obj");
        using (var writer = new StreamWriter(export))
        {
            writer.WriteLine("# PRIVATE open scan; unit unknown; PicoGK float32; no scaling, welding or hole filling");
            for (int i = 0; i < mesh.nVertexCount(); i++)
            {
                var p = mesh.vecVertexAt(i);
                writer.WriteLine(FormattableString.Invariant($"v {p.X:R} {p.Y:R} {p.Z:R}"));
            }
            for (int i = 0; i < mesh.nTriangleCount(); i++)
            {
                var t = mesh.oTriangleAt(i);
                writer.WriteLine($"f {t.A + 1} {t.B + 1} {t.C + 1}");
            }
        }
        Require(Hash(source) == inputHash, "Source changed during processing");
        Receipt(output, new { status = "private_open_mesh_round_trip", runtime = Runtime(),
            input_sha256 = inputHash, export_sha256 = Hash(export), vertices = mesh.nVertexCount(),
            triangles = mesh.nTriangleCount(), maximum_float32_vertex_error_source_units = maximumError,
            connectivity_preserved = true, source_unit = (string?)null, scale_verified = false,
            hole_filling_executed = false, scan_voxelisation_executed = false,
            functional_interfaces_verified = false, solver_ready = false });
    }

    public static int Main(string[] args)
    {
        try
        {
            if (args.Length == 2 && args[0] == "witness") Witness(Path.GetFullPath(args[1]));
            else if (args.Length == 4 && args[0] == "mesh") MeshRoundTrip(Path.GetFullPath(args[1]), args[2], Path.GetFullPath(args[3]));
            else throw new ArgumentException("Usage: witness NEW_PRIVATE_DIR | mesh PREPARED.obj EXPECTED_SHA256 NEW_PRIVATE_DIR");
            Console.WriteLine("Private PicoGK operation completed; no functional fan validation");
            return 0;
        }
        catch (Exception error)
        {
            Console.Error.WriteLine($"Failed closed: {error.GetType().Name}: {error.Message}");
            return 1;
        }
    }
}
