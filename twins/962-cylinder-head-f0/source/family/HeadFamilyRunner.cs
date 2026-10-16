using System.Numerics;
using System.Text.Json;
using PicoGK;

namespace PicoGKCatalog;

public static class HeadFamilyRunner
{
    sealed class ScalarCheck(ScalarField target) : ITraverseScalarField
    {
        public int Count;
        public void InformActiveValue(in Vector3 p, float value)
        {
            if (!float.IsFinite(value) || !target.bGetValue(p, out float other) || value != other)
                throw new InvalidDataException("VDB scalar value changed");
            Count++;
        }
    }

    sealed class VectorCheck(VectorField target) : ITraverseVectorField
    {
        public int Count;
        public void InformActiveValue(in Vector3 p, in Vector3 value)
        {
            if (!float.IsFinite(value.Length()) || !target.bGetValue(p, out Vector3 other) || value != other)
                throw new InvalidDataException("VDB gradient value changed");
            Count++;
        }
    }

    public static void Main(string[] args)
    {
        if (args.Length != 2 || Directory.Exists(args[1]) || File.Exists(args[1]))
            throw new ArgumentException("Use variant-input.json and a new output directory.");
        using var document = JsonDocument.Parse(File.ReadAllText(args[0]));
        var config = document.RootElement;
        var geometry = HeadFamilyStudy.Validate(config);
        using Library lib = new(.5f);
        var domains = HeadFamilyStudy.Build(lib, geometry);
        using Voxels solid = domains.Solid, water = domains.Coolant, dry = domains.Dry;
        Library.RegisterGlobalLibrary(lib);
        try
        {
            Directory.CreateDirectory(args[1]);
            foreach (var (name, vox) in new[] { ("solid", solid), ("coolant", water), ("dry-passages", dry) })
            {
                using Mesh mesh = new(vox);
                mesh.SaveToStlFile(Path.Combine(args[1], name + ".stl"));
            }
            using ScalarField distance = new(water);
            using VectorField gradient = new(water);
            string path = Path.Combine(args[1], "head-fields.vdb");
            using (OpenVdbFile writer = new(lib))
            {
                writer.nAdd(solid, "metal_domain"); writer.nAdd(water, "coolant_domain");
                writer.nAdd(dry, "dry_domain"); writer.nAdd(distance, "coolant_native_signed_distance");
                writer.nAdd(gradient, "coolant_native_gradient"); writer.SaveToFile(path);
            }
            using OpenVdbFile reader = new(lib, path);
            if (reader.nFieldCount() != 5 || reader.fPicoGKVoxelSizeMM() != .5f ||
                !solid.bIsEqual(reader.voxGet("metal_domain")) || !water.bIsEqual(reader.voxGet("coolant_domain")) ||
                !dry.bIsEqual(reader.voxGet("dry_domain")))
                throw new InvalidDataException("VDB domains changed");
            using ScalarField restoredDistance = reader.oGetScalarField("coolant_native_signed_distance");
            using VectorField restoredGradient = reader.oGetVectorField("coolant_native_gradient");
            var sForward = new ScalarCheck(restoredDistance); var sReverse = new ScalarCheck(distance);
            var vForward = new VectorCheck(restoredGradient); var vReverse = new VectorCheck(gradient);
            distance.TraverseActive(sForward); restoredDistance.TraverseActive(sReverse);
            gradient.TraverseActive(vForward); restoredGradient.TraverseActive(vReverse);
            if (sForward.Count == 0 || sForward.Count != sReverse.Count ||
                vForward.Count == 0 || vForward.Count != vReverse.Count)
                throw new InvalidDataException("VDB active topology changed");
            var report = new {
                variant_id = config.GetProperty("id").GetString(),
                status = "unmeasured_bionic_family_study", geometry_assumptions_mm = geometry,
                fixed_body_envelope_mm = new[] { 120, 140, 90 },
                chamber_radius_mm = geometry["bore_mm"] / 2 - 2,
                deck_outer_radius_mm = geometry["bore_mm"] / 2 + 8,
                nominal_dry_water_separation_mm = 4.5, nominal_outer_water_skin_mm = 5,
                nominal_coolant_port_id_mm = 22, valve_passage_count = 4, spark_passage_count = 2,
                lattice_library_executed = true, cell_count = 36,
                cell_mm = new[] { 12, 14, 14 }, beam_diameter_mm = 3.5,
                voxel_mm = .5, dotnet_runtime_version = Environment.Version.ToString(),
                vdb_domains_equal = true, scalar_values_checked_each_direction = sForward.Count,
                vector_values_checked_each_direction = vForward.Count,
                all_active_values_checked_bidirectionally = true,
                fields = Enumerable.Range(0, 5).Select(i => new {
                    name = reader.strFieldName(i), type = reader.strFieldType(i) }).ToArray(),
                field_interpretation = "Native geometric signed-distance and gradient; no temperature, pressure or flow solution",
                whole_head_scaling_executed = false, structural_optimisation_executed = false,
                fluid_solver_executed = false, historical_replica_validated = false,
                fitment_validated = false, manufacturing_authorized = false
            };
            File.WriteAllText(Path.Combine(args[1], "native-fields-report.json"),
                JsonSerializer.Serialize(report, new JsonSerializerOptions { WriteIndented = true }) + "\n");
            Console.WriteLine(JsonSerializer.Serialize(report));
        }
        finally { Library.UnregisterGlobalLibrary(); }
    }
}
