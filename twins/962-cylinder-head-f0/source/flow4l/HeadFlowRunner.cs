using System.Numerics;
using System.Text.Json;
using PicoGK;
using Leap71.LatticeLibrary;

namespace PicoGKCatalog;

// Open external rib study; no load-derived optimisation or manufacturing approval.
public static class HeadFlowRunner
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
        if (args.Length != 2 || Directory.Exists(args[1]))
            throw new ArgumentException("Use architecture-input-directory and a new output directory");
        using Library lib = new(.5f);
        var original = new HeadFlow4LStudy();
        Voxels Build(string n) => original.Build(lib, PartSpec.Load(Path.Combine(args[0], n + ".json")));
        using Voxels solid = Build("solid"), water = Build("coolant"), dry = Build("dry-passages");
        Library.RegisterGlobalLibrary(lib);
        try
        {
            Directory.CreateDirectory(args[1]);
            foreach (var (name, vox) in new[] { ("solid", solid), ("coolant", water), ("dry-passages", dry) })
            {
                using Mesh mesh = new(vox);
                mesh.SaveToStlFile(Path.Combine(args[1], name + ".stl"));
            }

            foreach (int h in new[] { 2, 1 })
            {
                var cells = new List<int[]>();
                int nx = 152 / h, ny = 160 / h, nz = 56 / h;
                for (int i = 0; i < nx; i++)
                for (int j = 0; j < ny; j++)
                for (int k = 0; k < nz; k++)
                    if (water.bIsInside(new(-76 + (i + .5f) * h, -80 + (j + .5f) * h, (k + .5f) * h)))
                        cells.Add(new[] { i, j, k });
                File.WriteAllText(Path.Combine(args[1], $"coolant-cells-{h}mm.json"),
                    JsonSerializer.Serialize(new { voxel_mm = h, origin_mm = new[] { -76, -80, 0 },
                        shape = new[] { nx, ny, nz }, cells, classification = "native_Voxels_bIsInside_at_cell_centres",
                        analysis_derivative_not_native_surface = true }));
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
            if (sForward.Count == 0 || sForward.Count != sReverse.Count || vForward.Count == 0 || vForward.Count != vReverse.Count)
                throw new InvalidDataException("VDB active topology changed");
            var report = new { lattice_library_executed = true, cell_count = 36,
                cell_mm = new[] { 12, 14, 14 }, beam_diameter_mm = 3.5,
                voxel_mm = .5, dotnet_runtime_version = Environment.Version.ToString(), vdb_domains_equal = true, scalar_values_checked_each_direction = sForward.Count,
                vector_values_checked_each_direction = vForward.Count, all_active_values_checked_bidirectionally = true,
                fields = Enumerable.Range(0, 5).Select(i => new { name = reader.strFieldName(i), type = reader.strFieldType(i) }).ToArray(),
                field_interpretation = "Native geometric signed-distance and gradient; no temperature, pressure or flow solution",
                structural_optimisation_executed = false, fluid_solver_executed = false, manufacturing_authorized = false };
            File.WriteAllText(Path.Combine(args[1], "native-fields-report.json"), JsonSerializer.Serialize(report,
                new JsonSerializerOptions { WriteIndented = true }) + "\n");
            Console.WriteLine(JsonSerializer.Serialize(report));
        }
        finally { Library.UnregisterGlobalLibrary(); }
    }
}
