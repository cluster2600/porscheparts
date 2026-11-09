using System.Numerics;
using System.Text.Json;
using Leap71.ShapeKernel;
using Leap71.LatticeLibrary;
using PicoGK;

namespace PicoGKCatalog;

// Synthetic boxes and one lattice cell exercise the runtime, never the head geometry.
public static class LinuxQualification
{
    public static void Main(string[] args)
    {
        if (args.Length != 1 || Directory.Exists(args[0]))
            throw new ArgumentException("Supply a new qualification output directory");
        using Library library = new(0.5f);
        Library.RegisterGlobalLibrary(library);
        try
        {
            using Voxels metal = new BaseBox(new LocalFrame(), 30, 10, 20).voxConstruct();
            using Voxels water = new BaseBox(new LocalFrame(new Vector3(40, 0, 0)), 30, 10, 20).voxConstruct();
            using Voxels dry = new BaseBox(new LocalFrame(new Vector3(80, 0, 0)), 30, 10, 20).voxConstruct();
            Lattice lattice = new(library);
            try
            {
                var cell = new CuboidCell(new(0, 0, 0), new(0, 10, 0), new(10, 10, 0), new(10, 0, 0),
                    new(0, 0, 10), new(0, 10, 10), new(10, 10, 10), new(10, 0, 10));
                new BodyCentreLattice().AddCell(ref lattice, cell, new ConstantBeamThickness(2), 2);
                using Voxels ribs = new(lattice);
                using ScalarField distance = new(water);
                using VectorField gradient = new(water);
                Directory.CreateDirectory(args[0]);
                foreach (var (name, voxels) in new[] { ("metal_domain", metal), ("coolant_domain", water),
                    ("dry_domain", dry), ("lattice", ribs) })
                {
                    using Mesh mesh = new(voxels);
                    if (mesh.nTriangleCount() == 0) throw new InvalidDataException("Empty synthetic domain");
                    mesh.SaveToStlFile(Path.Combine(args[0], name + ".stl"), Mesh.EStlUnit.MM);
                }
                string vdb = Path.Combine(args[0], "qualification.vdb");
                using (OpenVdbFile writer = new(library))
                {
                    writer.nAdd(metal, "metal_domain"); writer.nAdd(water, "coolant_domain");
                    writer.nAdd(dry, "dry_domain"); writer.nAdd(ribs, "lattice");
                    writer.nAdd(distance, "geometric_distance"); writer.nAdd(gradient, "geometric_gradient");
                    writer.SaveToFile(vdb);
                }
                using OpenVdbFile reader = new(library, vdb);
                if (reader.nFieldCount() != 6 || reader.fPicoGKVoxelSizeMM() != 0.5f ||
                    !metal.bIsEqual(reader.voxGet("metal_domain")) || !water.bIsEqual(reader.voxGet("coolant_domain")) ||
                    !dry.bIsEqual(reader.voxGet("dry_domain")) || !ribs.bIsEqual(reader.voxGet("lattice")))
                    throw new InvalidDataException("Named voxel fields changed during VDB round trip");
                var report = new { scope = "synthetic_linux_runtime_only", voxel_mm = 0.5,
                    box_dimensions_mm = new[] { 10, 20, 30 }, lattice_library_executed = true,
                    named_voxel_domains_equal = true, vdb_field_count = 6,
                    scalar_vector_values_validated = false, head_geometry_executed = false,
                    fasteners_executed = false, manufacturing_authorized = false };
                File.WriteAllText(Path.Combine(args[0], "qualification.json"),
                    JsonSerializer.Serialize(report, new JsonSerializerOptions { WriteIndented = true }) + "\n");
            }
            finally { lattice.Dispose(); }
        }
        finally { Library.UnregisterGlobalLibrary(); }
    }
}
