using System.Numerics;
using System.Text.Json;
using PicoGK;
using Leap71.LatticeLibrary;

namespace PicoGKCatalog;

// Open external rib study; no load-derived optimisation or manufacturing approval.
public static class HeadBionicRunner
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
        var original = new Head962ArchitectureStudy();
        Voxels Build(string n) => original.Build(lib, PartSpec.Load(Path.Combine(args[0], n + ".json")));
        using Voxels solid = Build("solid"), water = Build("coolant"), dry = Build("dry-passages");
        Library.RegisterGlobalLibrary(lib);
        try
        {
            int cells = 0;
            foreach (float side in new[] { -1f, 1f })
            {
                Lattice lattice = new(lib);
                var type = new BodyCentreLattice();
                // Every full cell has its inner face embedded in the existing skin.
                for (float y = -42; y < 42; y += 14)
                for (float z = 30; z < 72; z += 14)
                {
                    float x0 = side < 0 ? -62 : 50, x1 = x0 + 12;
                    var cell = new CuboidCell(new(x0, y, z), new(x0, y + 14, z),
                        new(x1, y + 14, z), new(x1, y, z), new(x0, y, z + 14),
                        new(x0, y + 14, z + 14), new(x1, y + 14, z + 14), new(x1, y, z + 14));
                    type.AddCell(ref lattice, cell, new ConstantBeamThickness(3.5f), 2);
                    cells++;
                }
                using Voxels ribs = new(lattice);
                solid.BoolAdd(ribs);
                lattice.Dispose();
            }
            // Re-fair the rib-to-skin junctions at half a voxel, then inspect the resulting mesh.
            solid.Smoothen(.25f);
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
            if (sForward.Count == 0 || sForward.Count != sReverse.Count || vForward.Count == 0 || vForward.Count != vReverse.Count)
                throw new InvalidDataException("VDB active topology changed");
            var report = new { lattice_library_executed = true, cell_count = cells,
                cell_mm = new[] { 12, 14, 14 }, beam_diameter_mm = 3.5,
                voxel_mm = .5, vdb_domains_equal = true, scalar_values_checked_each_direction = sForward.Count,
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
