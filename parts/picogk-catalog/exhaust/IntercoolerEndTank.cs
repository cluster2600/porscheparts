using System.Numerics;
using PicoGK;

namespace PicoGKCatalog;

/// End tank, flow axis X: rectangular core face at x = 0 (core flange behind
/// it, x < 0) blending into the round hose port at x = transition length.
/// The section is a rounded rectangle whose corner radius grows until it is
/// the port circle. Guide vanes follow the converging section (each vane keeps
/// its fraction of the local height); external ribs stiffen the flat panels.
public sealed class IntercoolerEndTank : IPartGenerator
{
    public string Name => "intercooler_end_tank";

    public Voxels Build(Library lib, PartSpec s)
    {
        float W = s.P("core_face_width_mm") / 2f, H = s.P("core_face_height_mm") / 2f, rp = s.P("port_outer_diameter_mm") / 2f;
        float Lx = s.P("transition_length_mm"), w = s.P("wall_mm");
        float fA = s.P("core_flange_axial_mm"), fM = s.P("core_flange_margin_mm"), cA = s.P("port_collar_axial_mm");
        int nV = s.N("guide_count");
        float vT = s.P("guide_thickness_mm"), vS = s.P("guide_spacing_mm"), vx0 = s.P("guide_start_x_mm"), vx1 = s.P("guide_end_x_mm");
        float rc0 = s.P("face_corner_radius_mm");
        int nR = s.N("rib_count");
        float rPitch = s.P("rib_pitch_mm"), rH = s.P("rib_height_mm"), rT = s.P("rib_thickness_mm");
        float bead = s.P("bead_radius_mm"), fil = s.P("fillet_mm");
        float ri = rp - w;

        (float a, float b, float rc) Sec(float x)
        {
            float t = FlowKit.Smooth(Math.Clamp(x / Lx, 0f, 1f));
            return (W + (ri - W) * t, H + (ri - H) * t, rc0 + (ri - rc0) * t);
        }
        float Section(Vector3 p, float off)
        {
            var (a, b, rc) = Sec(p.X);
            return FlowKit.RoundRect(p.Y, p.Z, a + off, b + off, rc + off);
        }
        float Cap(float d, float x, float x0, float x1) => MathF.Max(d, MathF.Max(x0 - x, x - x1));

        float ymax = W + fM + 2f, zmax = H + fM + 2f;
        Vector3 lo = new(-fA - 1f, -ymax, -zmax), hi = new(Lx + cA + 1f, ymax, zmax);

        Sdf.Stage(s.PartId, "shell");
        Voxels body = Sdf.Vox(lib, p => Cap(Section(p, w), p.X, 0f, Lx + 0.5f), new(-0.5f, lo.Y, lo.Z), new(Lx + 1f, hi.Y, hi.Z));
        // Core flange (weld / braze land around the core header).
        body.BoolAdd(Sdf.Vox(lib, p => Cap(FlowKit.RoundRect(p.Y, p.Z, W + fM, H + fM, rc0 + fM), p.X, -fA, 0.5f),
            new(-fA - 1f, lo.Y, lo.Z), new(1f, hi.Y, hi.Z)));
        // Port collar with a hose bead near its end.
        float xb = Lx + cA - 2.5f;
        body.BoolAdd(Sdf.Vox(lib, p =>
        {
            float rr = new Vector2(p.Y, p.Z).Length();
            float col = Cap(rr - rp, p.X, Lx - 1f, Lx + cA);
            float tor = new Vector2(p.X - xb, rr - rp).Length() - bead;
            return MathF.Min(col, tor);
        }, new(Lx - 2f, -rp - bead - 1f, -rp - bead - 1f), new(Lx + cA + 1f, rp + bead + 1f, rp + bead + 1f)));
        // Stiffening ribs along X on the top and bottom panels.
        float xr1 = 0.8f * Lx;
        body.BoolAdd(Sdf.Vox(lib, p =>
        {
            float best = float.MaxValue;
            for (int i = 0; i < nR; i++)
            {
                float y = (i - (nR - 1) / 2f) * rPitch;
                best = MathF.Min(best, MathF.Abs(p.Y - y) - rT / 2f);
            }
            float band = Section(p, w + rH);
            // rib height fades to zero toward the round end
            float fade = Section(p, w + rH * (1f - FlowKit.Smooth(p.X / xr1)));
            return Cap(MathF.Max(best, MathF.Max(band, fade)), p.X, 0f, xr1);
        }, new(-0.5f, lo.Y, lo.Z), new(xr1 + 1f, hi.Y, hi.Z)));

        Sdf.Stage(s.PartId, "fillet");
        body.Fillet(fil);

        Sdf.Stage(s.PartId, "hollow");
        body.BoolSubtract(Sdf.Vox(lib, p =>
        {
            float d = p.X < 0f ? FlowKit.RoundRect(p.Y, p.Z, W, H, rc0) : Section(p, 0f);
            float dPort = new Vector2(p.Y, p.Z).Length() - ri;
            if (p.X > Lx) d = dPort;
            return Cap(d, p.X, -fA - 1f, Lx + cA + 1f);
        }, lo, hi));

        Sdf.Stage(s.PartId, "vanes");
        Voxels vanes = Sdf.Vox(lib, p =>
        {
            var (a, b, rc) = Sec(p.X);
            float best = float.MaxValue;
            for (int i = 0; i < nV; i++)
            {
                float z0 = (i - (nV - 1) / 2f) * vS;
                best = MathF.Min(best, MathF.Abs(p.Z - z0 * b / H) - vT / 2f);
            }
            // vanes reach half a wall into the shell so they fuse with it
            return Cap(MathF.Max(best, Section(p, w / 2f)), p.X, vx0, vx1);
        }, new(vx0 - 1f, lo.Y, -H - 1f), new(vx1 + 1f, hi.Y, H + 1f));
        body.BoolAdd(vanes);
        return body;
    }
}
