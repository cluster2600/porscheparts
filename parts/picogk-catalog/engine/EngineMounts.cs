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

    // shortcut: distance-like tapered polyline; refine curvature sampling for qualified manufacturing.
    internal static float Branch(Vector3 p, IReadOnlyList<Vector3> curve, float startRadius, float endRadius)
    {
        float d = float.MaxValue;
        for (int i = 0; i + 1 < curve.Count; i++)
        {
            Vector3 segment = curve[i + 1] - curve[i];
            float length2 = segment.LengthSquared();
            float t = length2 < 1e-8f ? 0 : Math.Clamp(Vector3.Dot(p - curve[i], segment) / length2, 0, 1);
            float q = (i + t) / (curve.Count - 1);
            float radius = startRadius + q * (endRadius - startRadius);
            d = MathF.Min(d, (p - curve[i] - t * segment).Length() - radius);
        }
        return d;
    }

}

// Four root collars feed two trunks and a curved crown; engine attachment remains unknown.
public sealed class EngineBracketStudy : IPartGenerator
{
    public string Name => "engine_bracket_bionic_study";

    public Voxels Build(Library lib, PartSpec s)
    {
        MountStudy.Validate(s);
        float l = s.P("envelope_length_mm"), w = s.P("envelope_width_mm");
        float t = s.P("root_pad_height_mm"), wall = s.P("root_pad_wall_mm");
        float h = s.P("crown_height_mm"), r = s.P("branch_radius_mm"), blend = s.P("blend_mm");
        float hx = s.P("study_hole_half_span_x_mm"), hy = s.P("study_hole_half_span_y_mm");
        float bore = s.P("study_hole_diameter_mm") / 2f, pad = bore + wall;
        if (t < 3 * s.VoxelMm || wall < 3 * s.VoxelMm || r < 1.5f * s.VoxelMm ||
            hx + pad + blend >= l / 2 || hy + pad + blend >= w / 2 ||
            hx <= 4 * r || hy <= 2 * r || h <= t + 6 * r || blend >= MathF.Min(wall, r))
            throw new ArgumentException("Bionic bracket has unresolved collars or intersecting branch envelopes.");
        var roots = new List<(float x, float y, List<Vector3> curve)>();
        foreach (float x in new[] { -hx, hx })
            foreach (float y in new[] { -hy, hy })
            {
                float sign = MathF.Sign(x);
                roots.Add((x, y, Es.CubicPts(
                    new(x - sign * (bore + wall / 2), y, t * .7f),
                    new(x * .8f, y * 1.1f, h * .2f),
                    new(x * .42f, y * .45f, h * .6f),
                    new(x * .36f, 0, h * .72f), 12)));
            }
        var crown = Es.CubicPts(new(-hx * .36f, 0, h * .72f), new(-hx * .36f, 0, h),
            new(hx * .36f, 0, h), new(hx * .36f, 0, h * .72f), 12);
        float Field(Vector3 p)
        {
            float d = MountStudy.Branch(p, crown, r * 1.3f, r * 1.3f);
            foreach (var root in roots)
            {
                d = Es.SMin(d, Sdf.CylZ(p, root.x, root.y, pad, 0, t), blend);
                d = Es.SMin(d, MountStudy.Branch(p, root.curve, r, r * 1.35f), blend);
            }
            d = MathF.Max(d, -p.Z);
            foreach (var root in roots)
                d = MathF.Max(d, -Sdf.CylZ(p, root.x, root.y, bore, -1, h + 2 * r));
            return d;
        }
        return Sdf.Vox(lib, Field, new(-l / 2, -w / 2, -2),
            new(l / 2, w / 2, h + 2 * r + blend));
    }
}

// Open branching basket, not a reconstruction of the OEM hydraulic/elastomer housing.
public sealed class EngineMountHousingStudy : IPartGenerator
{
    public string Name => "engine_mount_bionic_housing_study";

    public Voxels Build(Library lib, PartSpec s)
    {
        MountStudy.Validate(s);
        float l = s.P("envelope_length_mm"), t = s.P("root_pad_height_mm"), padWall = s.P("root_pad_wall_mm");
        float outer = s.P("hub_outer_diameter_mm") / 2, wall = s.P("hub_wall_mm");
        float h = s.P("hub_height_mm"), span = s.P("study_body_hole_half_span_mm");
        float bore = s.P("study_body_hole_diameter_mm") / 2, blend = s.P("blend_mm"), r = s.P("branch_radius_mm");
        float ring = outer - wall / 2, low = t + wall / 2, high = h - wall / 2;
        if (wall < 3 * s.VoxelMm || t < 3 * s.VoxelMm || padWall < 3 * s.VoxelMm ||
            r < 1.5f * s.VoxelMm || wall >= outer / 3 || h <= t + 6 * wall ||
            span - bore - padWall <= outer || span + bore + padWall + blend >= l / 2 ||
            blend >= MathF.Min(padWall, r))
            throw new ArgumentException("Bionic housing has unresolved collars or intersecting root/hub envelopes.");
        var branches = new List<List<Vector3>>();
        Vector3 At(float angle, float radius, float z) => new(radius * MathF.Cos(angle), radius * MathF.Sin(angle), z);
        for (int i = 0; i < 6; i++)
        {
            float a = i * MathF.PI / 3, b = a + MathF.PI / 9;
            branches.Add(Es.CubicPts(At(a, ring, low), At(a - .12f, ring + wall, h * .35f),
                At(b + .12f, ring + wall, h * .7f), At(b, ring, high), 12));
        }
        var roots = new List<List<Vector3>>();
        foreach (float sign in new[] { -1f, 1f })
            foreach (float side in new[] { -1f, 1f })
                roots.Add(Es.CubicPts(new(sign * (span - bore - padWall / 2), 0, t * .6f),
                    new(sign * (span - padWall), side * outer * .5f, h * .3f),
                    new(sign * ring * .75f, side * outer * .7f, h * .7f),
                    new(sign * ring * .8660254f, side * ring * .5f, high), 12));
        float Field(Vector3 p)
        {
            float rho = new Vector2(p.X, p.Y).Length();
            float d = MathF.Min(new Vector2(rho - ring, p.Z - low).Length(),
                new Vector2(rho - ring, p.Z - high).Length()) - wall / 2;
            foreach (var curve in branches)
                d = Es.SMin(d, MountStudy.Branch(p, curve, r, r), blend);
            foreach (var curve in roots)
                d = Es.SMin(d, MountStudy.Branch(p, curve, r, r * 1.25f), blend);
            foreach (float x in new[] { -span, span })
                d = Es.SMin(d, Sdf.CylZ(p, x, 0, bore + padWall, 0, t), blend);
            d = MathF.Max(d, -Sdf.CylZ(p, 0, 0, outer - wall, -1, h + 2 * r));
            d = MathF.Max(d, -p.Z);
            foreach (float x in new[] { -span, span })
                d = MathF.Max(d, -Sdf.CylZ(p, x, 0, bore, -1, h + 2 * r));
            return d;
        }
        float y = outer + wall + r + blend + 2;
        return Sdf.Vox(lib, Field, new(-l / 2, -y, -2), new(l / 2, y, h + 2 * r + blend));
    }
}

// Six-lobed waisted occupancy envelope; no selected rubber or predicted compliance.
public sealed class EngineMountIsolatorStudy : IPartGenerator
{
    public string Name => "engine_mount_bionic_isolator_envelope_study";

    public Voxels Build(Library lib, PartSpec s)
    {
        MountStudy.Validate(s);
        float outer = s.P("outer_diameter_mm") / 2, inner = s.P("inner_diameter_mm") / 2;
        float h = s.P("height_mm"), waist = s.P("waist_depth_mm"), lobes = s.P("lobe_depth_mm");
        if (outer - inner - waist - lobes < 3 * s.VoxelMm || h < 3 * s.VoxelMm)
            throw new ArgumentException("Bionic isolator occupancy envelope is unresolved at the requested voxel size.");
        float Field(Vector3 p)
        {
            float q = Math.Clamp(p.Z / h, 0, 1), theta = MathF.Atan2(p.Y, p.X);
            float radius = outer - 4 * waist * q * (1 - q)
                - lobes * .5f * (1 + MathF.Cos(6 * theta)) * MathF.Sin(MathF.PI * q);
            float d = Es.Extrude(new Vector2(p.X, p.Y).Length() - radius, p.Z, 0, h);
            return MathF.Max(d, -Sdf.CylZ(p, 0, 0, inner, -1, h + 1));
        }
        return Sdf.Vox(lib, Field, new(-outer - 2, -outer - 2, -2), new(outer + 2, outer + 2, h + 2));
    }
}
