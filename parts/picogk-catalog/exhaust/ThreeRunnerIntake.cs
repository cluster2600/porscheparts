using System.Numerics;
using PicoGK;

namespace PicoGKCatalog;

/// Three offset conical runners, axis Z: head flange at z = 0 (bottom bore),
/// throttle flange at z = height (top bore) with bellmouth entries radiused
/// into the flange. Runners, flanges and bolt bosses are filleted as one
/// solid before the bores and bolt holes are cut.
public sealed class ThreeRunnerIntake : IPartGenerator
{
    public string Name => "three_runner_intake";

    public Voxels Build(Library lib, PartSpec s)
    {
        float rt = s.P("top_bore_diameter_mm") / 2f, rb = s.P("bottom_bore_diameter_mm") / 2f, Hh = s.P("height_mm");
        float w = s.P("runner_wall_mm"), pl = s.P("lower_pitch_mm"), pu = s.P("upper_pitch_mm"), oy = s.P("upper_offset_y_mm");
        float fx = s.P("flange_x_mm") / 2f, fy = s.P("flange_y_mm") / 2f, fT = s.P("flange_thickness_mm"), fc = s.P("flange_corner_radius_mm");
        float bmR = s.P("bellmouth_radial_mm"), bmA = s.P("bellmouth_axial_mm");
        float boltR = s.P("bolt_hole_diameter_mm") / 2f, bossR = s.P("bolt_boss_radius_mm"), bossH = s.P("bolt_boss_height_mm");
        float fil = s.P("fillet_mm");
        int nb = s.N("bolt_count");

        Vector2 Ctr(int i, float z)
        {
            float t = z / Hh, k = i - 1;
            return new Vector2(k * (pl + (pu - pl) * t), oy * t);
        }
        float Rb(float z)
        {
            float r = rb + (rt - rb) * Math.Clamp(z / Hh, 0f, 1f);
            float z0 = Hh - bmA;
            if (z > z0) { float u = Math.Clamp((z - z0) / bmA, 0f, 1f); r += bmR * (1f - MathF.Sqrt(1f - u * u)); }
            return r;
        }
        float Runners(Vector3 p, float off, float z0, float z1, bool flare)
        {
            float z = Math.Clamp(p.Z, z0, z1), d = float.MaxValue;
            float r = flare ? Rb(z) : rb + (rt - rb) * Math.Clamp(z / Hh, 0f, 1f);
            for (int i = 0; i < 3; i++) d = MathF.Min(d, (new Vector2(p.X, p.Y) - Ctr(i, z)).Length() - r - off);
            return MathF.Max(d, MathF.Max(z0 - p.Z, p.Z - z1));
        }
        // Three bolts per flange (count stated, positions assumed): lower
        // flange two below and one above the centre runner, upper flange
        // mirrored, all clear of the bores.
        Vector2[] lowB = { new(-pl / 2f, -fy + 8f), new(pl / 2f, -fy + 8f), new(0, fy - 7f) };
        Vector2[] upB = { new(-pu / 2f, fy - 6f), new(pu / 2f, fy - 6f), new(0, -fy + 8f) };
        lowB = lowB.Take(nb).ToArray(); upB = upB.Take(nb).ToArray();

        Vector3 lo = new(-fx - 1, -fy - 1, -1), hi = new(fx + 1, fy + 1, Hh + 1);
        Sdf.Stage(s.PartId, "solid");
        Voxels body = Sdf.Vox(lib, p => Runners(p, w, 0f, Hh, false), lo, hi);
        float Plate(Vector3 p, float z0, float z1) => FlowKit.Extrude(FlowKit.RoundRect(p.X, p.Y, fx, fy, fc), p.Z, z0, z1, 1f);
        body.BoolAdd(Sdf.Vox(lib, p => Plate(p, 0f, fT), lo, new(hi.X, hi.Y, fT + 1)));
        body.BoolAdd(Sdf.Vox(lib, p => Plate(p, Hh - fT, Hh), new(lo.X, lo.Y, Hh - fT - 1), hi));
        Lattice bosses = new(lib);
        foreach (Vector2 b in lowB) bosses.AddBeam(new Vector3(b, fT - 1f), new Vector3(b, fT + bossH), bossR, bossR, false);
        foreach (Vector2 b in upB) bosses.AddBeam(new Vector3(b, Hh - fT + 1f), new Vector3(b, Hh - fT - bossH), bossR, bossR, false);
        body.BoolAdd(new Voxels(bosses));

        Sdf.Stage(s.PartId, "fillet");
        body.Fillet(fil);

        Sdf.Stage(s.PartId, "bores");
        body.BoolSubtract(Sdf.Vox(lib, p => Runners(p, 0f, -2f, Hh + 2f, true), new(lo.X, lo.Y, -3), new(hi.X, hi.Y, Hh + 3)));
        Lattice holes = new(lib);
        foreach (Vector2 b in lowB) holes.AddBeam(new Vector3(b, -1f), new Vector3(b, fT + bossH + 1f), boltR, boltR, false);
        foreach (Vector2 b in upB) holes.AddBeam(new Vector3(b, Hh + 1f), new Vector3(b, Hh - fT - bossH - 1f), boltR, boltR, false);
        body.BoolSubtract(new Voxels(holes));
        return body;
    }
}
