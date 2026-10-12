using System.Numerics;
using System.Security.Cryptography;
using System.Text.Json;
using System.Text.RegularExpressions;
using PicoGK;

namespace BionicTurboAssembly;

public static class Program
{
    static string Sha(byte[] bytes) => Convert.ToHexString(SHA256.HashData(bytes)).ToLowerInvariant();
    static void Require(bool condition, string error) { if (!condition) throw new InvalidDataException(error); }

    public static int Main(string[] args)
    {
        if (args.Length != 3)
        {
            Console.Error.WriteLine("Usage: Assembly CONTRACT.json HOUSING_RUN_DIR NEW_OUTPUT_DIR");
            return 2;
        }
        string? output = null;
        Library? lib = null;
        var shapes = new Dictionary<string, Voxels>();
        var json = new JsonSerializerOptions { WriteIndented = true };
        try
        {
            byte[] contractBytes = File.ReadAllBytes(args[0]);
            using JsonDocument contract = JsonDocument.Parse(contractBytes);
            JsonElement c = contract.RootElement;
            Require(c.GetProperty("status").GetString() == "concept_only" && c.GetProperty("units").GetString() == "mm",
                "Only the millimetre concept contract is supported.");
            Require(c.GetProperty("voxel_mm").GetSingle() == .5f, "This assembly supports only 0.5 mm voxels.");
            var entries = c.GetProperty("components").EnumerateArray().ToDictionary(x => x.GetProperty("id").GetString()!);
            Require(entries.Count == 39 && entries.Keys.All(id => Regex.IsMatch(id, "^[a-z][a-z0-9-]*$")), "Invalid component contract.");
            string source = Path.Combine(Path.GetFullPath(args[1]), "housing.stl");
            byte[] housingBytes = File.ReadAllBytes(source);
            Require(Sha(housingBytes) == c.GetProperty("compressor_housing_sha256").GetString(), "Housing does not match the independent contract.");
            string target = Path.GetFullPath(args[2]);
            Require(!Directory.Exists(target) && !File.Exists(target), "Output exists; refusing to overwrite.");
            Directory.CreateDirectory(target);
            output = target;
            lib = new(.5f);
            var files = new List<object>();
            void Record(string id, Mesh mesh, string filename, Vector3 offset)
            {
                Require(entries.ContainsKey(id) && !shapes.ContainsKey(id), "Unexpected or duplicate component: " + id);
                Require(mesh.nTriangleCount() > 0 && float.IsFinite(offset.X) && float.IsFinite(offset.Y) && float.IsFinite(offset.Z), "Invalid geometry or display offset.");
                JsonElement entry = entries[id];
                files.Add(new { id, label = entry.GetProperty("label").GetString(), group = entry.GetProperty("group").GetString(),
                    file = id + ".stl", sha256 = Sha(File.ReadAllBytes(filename)), triangles = mesh.nTriangleCount(),
                    explode_offset_mm = new[] { offset.X, offset.Y, offset.Z }, units = "mm", basis = "design_assumption" });
            }
            void Save(string id, string label, Voxels shape, Vector3 offset)
            {
                Console.WriteLine("EXPORT " + id);
                using Mesh mesh = new(shape);
                string filename = Path.Combine(output, id + ".stl");
                Require(entries.ContainsKey(id) && !shapes.ContainsKey(id), "Unexpected or duplicate component: " + id);
                mesh.SaveToStlFile(filename, Mesh.EStlUnit.MM);
                Record(id, mesh, filename, offset);
                shapes.Add(id, shape.voxDuplicate());
            }
            string housingPath = Path.Combine(output, "compressor-housing.stl");
            File.WriteAllBytes(housingPath, housingBytes);
            using (Mesh housingMesh = Mesh.mshFromStlFile(housingPath, Mesh.EStlUnit.MM, libSet: lib))
            {
                Record("compressor-housing", housingMesh, housingPath, new(0, 0, 160));
                shapes.Add("compressor-housing", new Voxels(housingMesh));
            }
            Components.Build(lib, Save);
            HotSide.Build(lib, Save);
            Require(entries.Keys.ToHashSet().SetEquals(shapes.Keys), "Missing component exports.");
            var intersections = new List<object>();
            bool clear = true;
            foreach (JsonElement pair in c.GetProperty("noninterference_pairs").EnumerateArray())
            {
                string a = pair[0].GetString()!, b = pair[1].GetString()!;
                using Voxels intersection = shapes[a].voxBoolIntersect(shapes[b]);
                float volume = 0;
                if (!intersection.bIsEmpty()) intersection.CalculateProperties(out volume, out _);
                bool passed = float.IsFinite(volume) && volume == 0;
                clear &= passed;
                intersections.Add(new { a, b, voxel_intersection_mm3 = volume, passed });
            }
            File.WriteAllText(Path.Combine(output, "report.json"), JsonSerializer.Serialize(new {
                schema_version = 1, status = clear ? "concept_assembly_generated" : "failed_voxel_interference",
                units = "mm", voxel_mm = .5f, kernel = Library.strVersion(),
                contract_sha256 = Sha(contractBytes), compressor_source_sha256 = Sha(housingBytes),
                concept_bom_complete = true, production_bom_complete = false, component_count = files.Count,
                measured_interfaces = false, engineering_validated = false, manufacturing_authorized = false,
                minimum_clearance_measured = false, selected_voxel_intersections = intersections, files,
                note = "All parts are hypothetical concept representations. Threads, material and operating clearances are unqualified."
            }, json) + "\n");
            Require(clear, "Selected rotating/stationary pairs have voxel interference; inspect report.json.");
            Console.WriteLine("ASSEMBLY_GENERATED: 39 components; independent mesh inspection still required.");
            return 0;
        }
        catch (Exception error)
        {
            if (output is not null) File.WriteAllText(Path.Combine(output, "FAILED.json"), JsonSerializer.Serialize(new {
                status = "failed", error = error.Message, manufacturing_authorized = false }, json));
            Console.Error.WriteLine(error.Message);
            return 1;
        }
        finally
        {
            foreach (Voxels shape in shapes.Values) shape.Dispose();
            lib?.Dispose();
        }
    }
}
