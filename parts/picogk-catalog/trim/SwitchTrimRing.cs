using System.Numerics;
using PicoGK;

namespace PicoGKCatalog;

/// Turned switch trim ring, axis Z, rear face at z = 0, visible front at
/// z = depth. Cylindrical outside, linear conical bore from the rear to the
/// front diameter (the F1 hypothesis), radiused front outer edge, 45 deg
/// chamfer on the front bore edge and the rear outer edge, one turned
/// decorative groove on the front face and a straight retention knurl on the
/// hidden outer band. Everything is one axisymmetric profile in (r, z) plus
/// the knurl, evaluated as a single implicit.
public sealed class SwitchTrimRing : IPartGenerator
{
    public string Name => "switch_trim_ring";

    public Voxels Build(Library lib, PartSpec s)
    {
        float R = s.P("outer_diameter_mm") / 2f, D = s.P("depth_mm");
        float rf = s.P("front_inner_diameter_mm") / 2f, rr = s.P("rear_inner_diameter_mm") / 2f;
        float edgeR = s.P("front_outer_edge_radius_mm");
        float chIn = s.P("front_bore_chamfer_mm"), chRear = s.P("rear_edge_chamfer_mm");
        float gR = s.P("face_groove_radius_mm"), gW = s.P("face_groove_width_mm"), gD = s.P("face_groove_depth_mm");
        int nK = s.N("knurl_count");
        float kD = s.P("knurl_depth_mm"), kZ0 = s.P("knurl_z_start_mm"), kZ1 = s.P("knurl_z_end_mm");

        float cosB = MathF.Cos(MathF.Atan((rr - rf) / D));
        float pitchA = 2f * MathF.PI / nK;

        float Field(Vector3 p)
        {
            float r = MathF.Sqrt(p.X * p.X + p.Y * p.Y), z = p.Z;
            // outer envelope: rect [0..R] x [0..D] with rounded front outer corner
            float dOuter;
            if (r > R - edgeR && z > D - edgeR)
                dOuter = new Vector2(r - (R - edgeR), z - (D - edgeR)).Length() - edgeR;
            else
                dOuter = MathF.Max(r - R, MathF.Abs(z - D / 2f) - D / 2f);
            // conical bore: solid where r > rin(z)
            float rin = rr + (rf - rr) * Math.Clamp(z / D, 0f, 1f);
            float d = MathF.Max(dOuter, (rin - r) * cosB);
            // 45 deg chamfers: front bore edge, rear outer edge
            d = MathF.Max(d, (chIn - (r - rf) - (D - z)) * 0.7071f);
            d = MathF.Max(d, (chRear - (R - r) - z) * 0.7071f);
            // turned V-ish groove on the front face (round-bottom)
            float groove = new Vector2((r - gR) * (gD / (gW / 2f)), z - D).Length() - gD;
            d = MathF.Max(d, -groove);
            // straight knurl: 90 deg V grooves on the outer band
            if (z > kZ0 - 1f && z < kZ1 + 1f && r > R - 2f * kD)
            {
                float a = MathF.Atan2(p.Y, p.X);
                float k = a / pitchA;
                float off = (k - MathF.Round(k)) * pitchA * R;          // circumferential offset to the groove line
                float band = MathF.Max(kZ0 - z, z - kZ1);
                float cut = MathF.Max((R - kD + MathF.Abs(off)) - r, band) * 0.7071f;
                d = MathF.Max(d, -cut);
            }
            return d;
        }

        Vector3 lo = new(-R - 1, -R - 1, -1), hi = new(R + 1, R + 1, D + 1);
        Sdf.Stage(s.PartId, "ring profile");
        return Sdf.Vox(lib, Field, lo, hi);
    }
}
