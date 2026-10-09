using System.Numerics;
using PicoGK;

namespace PicoGKCatalog;

/// Round-to-oval tip, axis Z, inlet at z = 0. Double wall: inner flow shell
/// and outer cosmetic shell, ventilated gap open at the inlet end (cooling and
/// depowdering path), closed by a solid lip at the outlet, tied by radial
/// ribs. The slip collar is a straight section. Used by both oval-tip records.
public sealed class OvalExhaustTip : IPartGenerator
{
    public string Name => "oval_exhaust_tip";

    static float Smooth(float t) { t = Math.Clamp(t, 0f, 1f); return t * t * (3f - 2f * t); }

    public Voxels Build(Library lib, PartSpec s)
    {
        float L = s.P("length_mm"), slip = s.P("slip_depth_mm");
        float rIn = s.P("inlet_pipe_od_mm") / 2f + s.P("slip_clearance_mm");
        float W = s.P("outlet_width_mm") / 2f, H = s.P("outlet_height_mm") / 2f;
        float wo = s.P("outer_wall_mm"), wi = s.P("inner_wall_mm"), gap = s.P("gap_mm");
        float lip = s.P("outlet_lip_mm");
        int ribs = s.N("rib_count");
        float ribT = s.P("rib_thickness_mm");

        float aOut = W - wo - gap - wi, bOut = H - wo - gap - wi;
        (float, float) Bore(float z)
        {
            float t = Smooth((z - slip) / (L - slip));
            return (rIn + (aOut - rIn) * t, rIn + (bOut - rIn) * t);
        }
        Func<float, (float, float)> Off(float d) => z => { var (a, b) = Bore(z); return (a + d, b + d); };

        Vector3 lo = new(-W - 2, -H - 2, -1), hi = new(W + 2, H + 2, L + 1);
        Voxels outer = Sdf.Vox(lib, p => Sdf.EllipseLoftZ(p, Off(wi + gap + wo), 0, L), lo, hi);
        Voxels bore = Sdf.Vox(lib, p => Sdf.EllipseLoftZ(p, Bore, -1, L + 1), lo, hi);
        Voxels gapV = Sdf.Vox(lib, p => Sdf.EllipseLoftZ(p, Off(wi + gap), -1, L - lip), lo, hi);
        gapV.BoolSubtract(Sdf.Vox(lib, p => Sdf.EllipseLoftZ(p, Off(wi), -2, L), lo, hi));
        Voxels ribV = Sdf.Vox(lib, p =>
        {
            float best = float.MaxValue;
            for (int i = 0; i < ribs; i++)
            {
                float a = (i + 0.5f) * 2f * MathF.PI / ribs;
                Vector2 dir = new(MathF.Cos(a), MathF.Sin(a)), n = new(-dir.Y, dir.X), q = new(p.X, p.Y);
                best = MathF.Min(best, MathF.Max(MathF.Abs(Vector2.Dot(q, n)) - ribT / 2f, -Vector2.Dot(q, dir)));
            }
            return best;
        }, lo, hi);
        gapV.BoolSubtract(ribV);
        outer.BoolSubtract(bore);
        outer.BoolSubtract(gapV);
        return outer;
    }
}
