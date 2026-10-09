using System.Numerics;
using PicoGK;

namespace PicoGKCatalog;

/// 993 front lid, composite concept. X across the car, Y from the nose
/// (y = 0) to the windscreen edge (y = length), Z up. Skin: transverse crown
/// of constant radius plus a longitudinal fall toward the nose, cut to a
/// plan with the headlamp waist, a curved nose and rounded corners. Rolled
/// edge into a return flange all round. Inner frame: perimeter hat section
/// (two walls and a panel) whose panel carries a field of lightening holes
/// that also drain and vent the hat, plus an X brace and a centre rib.
/// Rendered tile by tile so the implicit is only evaluated near the skin.
public sealed class FrontLid : IPartGenerator
{
    public string Name => "front_lid_composite";

    public Voxels Build(Library lib, PartSpec s)
    {
        float W = s.P("width_mm"), L = s.P("length_mm"), R = s.P("crown_radius_mm"), t = s.P("skin_mm");
        float D = s.P("nose_drop_mm"), ratio = s.P("nose_width_ratio");
        float y0 = s.P("waist_start_ratio"), y1 = s.P("waist_end_ratio"), nose = s.P("nose_curve_mm");
        float rF = s.P("front_corner_radius_mm"), rR = s.P("rear_corner_radius_mm"), rE = s.P("edge_roll_radius_mm");
        float hF = s.P("flange_depth_mm"), tF = s.P("flange_thickness_mm");
        float i1 = s.P("frame_inset_mm"), fw = s.P("frame_width_mm"), Df = s.P("frame_depth_mm"), tl = s.P("frame_laminate_mm");
        float holeR = s.P("lightening_hole_diameter_mm") / 2f, pitch = s.P("lightening_hole_pitch_mm");
        float tr = s.P("rib_thickness_mm"), Dr = s.P("rib_depth_mm");
        float i2 = i1 + fw;
        float W2 = W / 2f, wf = ratio * W2;
        float zBase = MathF.Sqrt(R * R - W2 * W2);

        float Wy(float y) => wf + (W2 - wf) * BodyKit.Smooth((y / L - y0) / (y1 - y0));
        float Yf(float x) => nose * (x / wf) * (x / wf);
        float F(float x, float y)
        {
            float c = MathF.Sqrt(MathF.Max(R * R - x * x, 0f)) - zBase;
            float u = 1f - y / L;
            return c - D * u * u;
        }
        float Plan(float x, float y)
        {
            const float e = 0.5f;
            float dw = (Wy(y + e) - Wy(y - e)) / (2 * e);
            float dSide = (MathF.Abs(x) - Wy(y)) / MathF.Sqrt(1f + dw * dw);
            float dy = 2f * nose * x / (wf * wf);
            float dFront = (Yf(x) - y) / MathF.Sqrt(1f + dy * dy);
            return BodyKit.RoundI(BodyKit.RoundI(dSide, dFront, rF), y - L, rR);
        }
        // X brace (front corners to rear corners) and centre rib, as 2D lines
        Vector2 a1 = new(-0.62f * W2, 0.18f * L), b1 = new(0.70f * W2, 0.86f * L);
        Vector2 a2 = new(0.62f * W2, 0.18f * L), b2 = new(-0.70f * W2, 0.86f * L);
        static float Seg(Vector2 p, Vector2 a, Vector2 b)
        {
            Vector2 ab = b - a, ap = p - a;
            float h = Math.Clamp(Vector2.Dot(ap, ab) / Vector2.Dot(ab, ab), 0f, 1f);
            return (ap - ab * h).Length();
        }

        float Field(Vector3 p)
        {
            float x = p.X, y = p.Y;
            float d2 = Plan(x, y);
            if (d2 > 4f) return d2;
            const float e = 0.5f;
            float fx = (F(x + e, y) - F(x - e, y)) / (2 * e), fy = (F(x, y + e) - F(x, y - e)) / (2 * e);
            float sN = (p.Z - F(x, y)) / MathF.Sqrt(1f + fx * fx + fy * fy);

            // skin + rolled edge + return flange
            float outer = BodyKit.RoundI(d2, sN, rE);
            float inner = BodyKit.RoundI(d2 + tF, sN + t, MathF.Max(rE - t, 0.5f));
            float d = MathF.Max(MathF.Max(outer, -inner), -(sN + hF));

            // perimeter hat section: panel with lightening holes, outer and inner walls
            float panel = MathF.Max(MathF.Max(d2 + i1, -(d2 + i2)), MathF.Abs(sN + Df - tl / 2f) - tl / 2f);
            float gx = x - pitch * MathF.Floor(x / pitch) - pitch / 2f, gy = y - pitch * MathF.Floor(y / pitch) - pitch / 2f;
            panel = MathF.Max(panel, -(MathF.Sqrt(gx * gx + gy * gy) - holeR));
            float wallZ = MathF.Max(sN + t - 1f, -(sN + Df));
            float wallO = MathF.Max(MathF.Abs(d2 + i1 + tl / 2f) - tl / 2f, wallZ);
            float wallI = MathF.Max(MathF.Abs(d2 + i2 - tl / 2f) - tl / 2f, wallZ);
            d = MathF.Min(d, MathF.Min(panel, MathF.Min(wallO, wallI)));

            // X brace and centre rib inside the frame, open below
            Vector2 q = new(x, y);
            float line = MathF.Min(MathF.Min(Seg(q, a1, b1), Seg(q, a2, b2)), Seg(q, new Vector2(0, 0.1f * L), new Vector2(0, 0.95f * L)));
            float rib = MathF.Max(MathF.Max(line - tr / 2f, MathF.Max(sN + t - 1f, -(sN + Dr))), d2 + i2 - 1f);
            // filleted rib roots, but never above the skin surface (no print-through)
            return MathF.Max(BodyKit.SMin(d, rib, 3f), MathF.Min(d, sN));
        }

        Sdf.Stage(s.PartId, "render tiles");
        float depth = MathF.Max(MathF.Max(hF, Df), Dr) + 4f;
        Voxels lid = BodyKit.Tiled(lib, Field, -W2 - 2f, W2 + 2f, -2f, L + 2f, 125f, (xa, xb, ya, yb) =>
        {
            float lo = float.MaxValue, hi = float.MinValue, dmin = float.MaxValue;
            for (int i = 0; i <= 6; i++)
                for (int j = 0; j <= 6; j++)
                {
                    float x = xa + (xb - xa) * i / 6f, y = ya + (yb - ya) * j / 6f;
                    float z = F(Math.Clamp(x, -W2, W2), Math.Clamp(y, 0f, L));
                    lo = MathF.Min(lo, z); hi = MathF.Max(hi, z);
                    dmin = MathF.Min(dmin, Plan(x, y));
                }
            float diag = new Vector2(xb - xa, yb - ya).Length();
            if (dmin > diag / 6f + 4f) return null;
            return (lo - depth, hi + 4f);
        });
        return lid;
    }
}
