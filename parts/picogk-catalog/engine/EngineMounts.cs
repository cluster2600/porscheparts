using System.Numerics;
using PicoGK;

namespace PicoGKCatalog;

internal static class MountStudy
{
    internal const string Status = "shape_study_only_unmeasured_interfaces_no_manufacturing";

    internal static void Validate(PartSpec s)
    {
        if (s.Status != Status || s.SafetyClass != "prohibited_pending_engineering")
            throw new ArgumentException("Engine mounts require an explicitly unqualified shape study.");
        if (s.DensityGCm3 != 0)
            throw new ArgumentException("Unqualified mount studies must keep mass estimation disabled.");
        if (!float.IsFinite(s.VoxelMm) || s.VoxelMm < 0.25f || s.VoxelMm > 1f)
            throw new ArgumentException("Study voxel size must be between 0.25 and 1 mm.");
        foreach (Param p in s.Parameters.Values)
            if (!double.IsFinite(p.Value) || p.Value <= 0 || p.Value > 500 ||
                p.Unit != "mm" || p.Basis != "assumption")
                throw new ArgumentException("Mount study dimensions must be bounded, explicit assumptions in mm.");
    }
}

// A separate central console: four illustrative carrier holes, no invented engine interface.
public sealed class EngineBracketStudy : IPartGenerator
{
    public string Name => "engine_bracket_ribbed_study";

    public Voxels Build(Library lib, PartSpec s)
    {
        MountStudy.Validate(s);
        float l = s.P("plate_length_mm"), w = s.P("plate_width_mm"), t = s.P("plate_thickness_mm");
        float h = s.P("upright_height_mm"), u = s.P("upright_thickness_mm");
        float rx = s.P("rib_offset_mm"), r = s.P("rib_radius_mm"), blend = s.P("blend_mm");
        float hx = s.P("study_hole_half_span_x_mm"), hy = s.P("study_hole_half_span_y_mm");
        float bore = s.P("study_hole_diameter_mm") / 2f;
        if (t < 3 * s.VoxelMm || u < 3 * s.VoxelMm ||
            hx + bore + t >= l / 2 || hy + bore + t >= w / 2 ||
            rx + r >= hx - bore || h <= t + 2 * r || blend >= MathF.Min(t, u) / 2)
            throw new ArgumentException("Bracket study has unresolved walls or intersecting hole/rib envelopes.");
        float Field(Vector3 p)
        {
            float d = Sdf.RoundBox(p, new(0, 0, t / 2), new(l / 2, w / 2, t / 2), blend);
            float upright = Sdf.RoundBox(p, new(0, 0, (h + t) / 2),
                new(l / 2 - 2 * t, u / 2, (h - t) / 2), blend);
            d = Es.SMin(d, upright, blend);
            foreach (float x in new[] { -rx, rx })
                d = Es.SMin(d, Sdf.Capsule(p, new(x, -w / 2 + 2 * r, t),
                    new(x, 0, h - r), r), blend);
            foreach (float x in new[] { -hx, hx })
                foreach (float y in new[] { -hy, hy })
                    d = MathF.Max(d, -Sdf.CylZ(p, x, y, bore, -1, t + 1));
            return d;
        }
        return Sdf.Vox(lib, Field, new(-l / 2 - 2, -w / 2 - 2, -2),
            new(l / 2 + 2, w / 2 + 2, h + 2));
    }
}

// Exterior cup exercise only: the OEM hydraulic/elastomer architecture is unknown.
public sealed class EngineMountHousingStudy : IPartGenerator
{
    public string Name => "engine_mount_housing_study";

    public Voxels Build(Library lib, PartSpec s)
    {
        MountStudy.Validate(s);
        float l = s.P("base_length_mm"), w = s.P("base_width_mm"), t = s.P("base_thickness_mm");
        float outer = s.P("cup_outer_diameter_mm") / 2, wall = s.P("cup_wall_mm");
        float h = s.P("cup_height_mm"), span = s.P("study_body_hole_half_span_mm");
        float bore = s.P("study_body_hole_diameter_mm") / 2, blend = s.P("blend_mm");
        if (wall < 3 * s.VoxelMm || t < 3 * s.VoxelMm || wall >= outer ||
            h <= t + wall || span - bore <= outer + blend ||
            span + bore + t >= l / 2 || bore + t >= w / 2 || blend >= t / 2)
            throw new ArgumentException("Mount housing study has unresolved walls or intersecting hole/cup envelopes.");
        float Field(Vector3 p)
        {
            float plate = Sdf.RoundBox(p, new(0, 0, t / 2), new(l / 2, w / 2, t / 2), blend);
            float cup = Sdf.CylZ(p, 0, 0, outer, t / 2, h);
            float d = Es.SMin(plate, cup, blend);
            d = MathF.Max(d, -Sdf.CylZ(p, 0, 0, outer - wall, t, h + 1));
            foreach (float x in new[] { -span, span })
                d = MathF.Max(d, -Sdf.CylZ(p, x, 0, bore, -1, t + 1));
            return d;
        }
        float y = MathF.Max(w / 2, outer) + 2;
        return Sdf.Vox(lib, Field, new(-l / 2 - 2, -y, -2), new(l / 2 + 2, y, h + 2));
    }
}

// A separate occupancy envelope, not a selected rubber compound or stiffness model.
public sealed class EngineMountIsolatorStudy : IPartGenerator
{
    public string Name => "engine_mount_isolator_envelope_study";

    public Voxels Build(Library lib, PartSpec s)
    {
        MountStudy.Validate(s);
        float outer = s.P("outer_diameter_mm") / 2, inner = s.P("inner_diameter_mm") / 2;
        float h = s.P("height_mm");
        if (outer - inner < 3 * s.VoxelMm || h < 3 * s.VoxelMm)
            throw new ArgumentException("Isolator occupancy envelope is unresolved at the requested voxel size.");
        return Sdf.Vox(lib, p => MathF.Max(Sdf.CylZ(p, 0, 0, outer, 0, h),
                -Sdf.CylZ(p, 0, 0, inner, -1, h + 1)),
            new(-outer - 2, -outer - 2, -2), new(outer + 2, outer + 2, h + 2));
    }
}
