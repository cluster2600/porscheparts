using System.Numerics;
using PicoGK;

namespace PicoGKCatalog;

// Continuous stock envelope for the unmeasured F0, before structural lightening or donor fitment.
public sealed class Head962EnclosedStudy : IPartGenerator
{
    public string Name => "962_4v_twin_plug_enclosed_head_study";

    public Voxels Build(Library lib, PartSpec s)
    {
        if (s.P("export_mode") != 0 || s.VoxelMm != .5f)
            throw new ArgumentException("The enclosed study exports only the 0.5 mm solid.");
        PartSpec Copy(int mode) => new()
        {
            PartId = s.PartId, Status = s.Status, SafetyClass = s.SafetyClass,
            DensityGCm3 = s.DensityGCm3, VoxelMm = s.VoxelMm,
            Parameters = s.Parameters.ToDictionary(p => p.Key, p => p.Key == "export_mode"
                ? p.Value with { Value = mode } : p.Value)
        };
        var original = new Head962Study();
        Voxels water = original.Build(lib, Copy(1));
        Voxels dry = original.Build(lib, Copy(2));
        // Dimensions and corner radius are study assumptions, not Porsche measurements.
        Voxels body = Sdf.Vox(lib, p => Sdf.RoundBox(p, new(0, 0, 45), new(80, 80, 45), 8),
            new(-90, -95, -80), new(90, 95, 100));
        body.BoolSubtract(water);
        body.BoolSubtract(dry);
        return body;
    }
}
