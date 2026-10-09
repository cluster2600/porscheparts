using System.Numerics;
using PicoGK;

namespace PicoGKCatalog;

/// I-beam connecting rod. Big end at the origin, small end at x = centre
/// distance, rod plane XY, widths along Z. Eyes, bolt lugs and a cap
/// balancing pad are blended into a tapered I-beam shank (two rails, thin
/// web, pockets on both faces) with smooth-min fillets. The cap split at x = 0
/// is a witness groove all round (body and cap printed as one piece and
/// separated afterwards), so the model stays a single body.
public sealed class ConnectingRod : IPartGenerator
{
    public string Name => "connecting_rod_ibeam";

    public Voxels Build(Library lib, PartSpec s)
    {
        float L = s.P("center_distance_mm");
        float rBig = s.P("big_end_bore_mm") / 2f, rPin = s.P("piston_pin_diameter_mm") / 2f;
        float hBig = s.P("big_end_width_mm") / 2f, hSmall = s.P("small_end_width_mm") / 2f;
        float RBig = s.P("big_end_od_mm") / 2f, RSmall = s.P("small_end_od_mm") / 2f;
        float hShank = s.P("shank_thickness_mm") / 2f, web = s.P("web_thickness_mm") / 2f;
        float rail = s.P("rail_width_mm");
        float wB = s.P("shank_half_width_big_mm"), wS = s.P("shank_half_width_small_mm");
        float xB = s.P("shank_start_x_mm"), xS = s.P("shank_end_x_mm");
        float boltY = s.P("bolt_axis_y_mm"), rBolt = s.P("bolt_clearance_diameter_mm") / 2f;
        float lugX = s.P("bolt_lug_length_x_mm") / 2f, lugY = s.P("bolt_lug_width_y_mm") / 2f;
        float split = s.P("cap_split_groove_width_mm") / 2f, splitDepth = s.P("cap_split_groove_depth_mm");
        float fillet = s.P("shank_fillet_mm"), edge = s.P("edge_round_mm"), chamfer = s.P("bore_chamfer_mm");
        float rOil = s.P("small_end_oil_hole_mm") / 2f, pad = s.P("cap_balance_pad_mm");

        float slope = (wS - wB) / (xS - xB), cosK = 1f / MathF.Sqrt(1f + slope * slope);
        float W(float x) => wB + slope * Math.Clamp(x - xB, 0f, xS - xB);
        float px0 = RBig + 5f, px1 = L - RSmall - 4f;   // pocket ends clear of the eyes

        float F(Vector3 p)
        {
            float rb = Es.Len2(p.X, p.Y), rs = Es.Len2(p.X - L, p.Y);
            float d = MathF.Min(Es.Rect2(rb, p.Z, 0f, 0f, RBig, hBig, edge),
                                Es.Rect2(rs, p.Z, 0f, 0f, RSmall, hSmall, edge));
            float shank2 = MathF.Max((MathF.Abs(p.Y) - W(p.X)) * cosK, MathF.Max(xB - p.X, p.X - xS));
            float shank = Es.RoundEdge(shank2, MathF.Abs(p.Z) - hShank, edge);
            d = Es.SMin(d, shank, fillet);
            float lugs = MathF.Min(Sdf.RoundBox(p, new Vector3(0f, boltY, 0f), new Vector3(lugX, lugY, hBig), 2.5f),
                                   Sdf.RoundBox(p, new Vector3(0f, -boltY, 0f), new Vector3(lugX, lugY, hBig), 2.5f));
            d = Es.SMin(d, lugs, 3f);
            d = Es.SMin(d, Sdf.RoundBox(p, new Vector3(-RBig + 1f - pad / 2f, 0f, 0f),
                                        new Vector3(pad / 2f + 1f, 10f, hBig - 2f), 2f), 2.5f);

            // I-beam pockets on both faces, rounded ends, filleted floor.
            float pocket2 = Es.SMax(Es.SMax((MathF.Abs(p.Y) - (W(p.X) - rail)) * cosK, px0 - p.X, 6f), p.X - px1, 6f);
            d = Es.SMax(d, -MathF.Max(pocket2, web - MathF.Abs(p.Z)), 1.5f);

            // Bores with edge chamfers, bolt passages, small-end oil drilling.
            float big = rb - rBig - MathF.Max(0f, chamfer - (hBig - MathF.Abs(p.Z)));
            float small = rs - rPin - MathF.Max(0f, chamfer - (hSmall - MathF.Abs(p.Z)));
            d = MathF.Max(d, -MathF.Min(big, small));
            float ay = MathF.Abs(p.Y);
            Vector3 q = new(p.X, ay, p.Z);
            d = MathF.Max(d, -Es.Cyl(q, new Vector3(-lugX - 3f, boltY, 0f), new Vector3(lugX + 3f, boltY, 0f), rBolt));
            d = MathF.Max(d, -Es.Cyl(p, new Vector3(L + rPin - 1f, 0f, 0f), new Vector3(L + RSmall + 2f, 0f, 0f), rOil));

            // Cap split witness groove at x = 0, splitDepth deep from every surface.
            float groove = MathF.Max(MathF.Abs(p.X) - split, -(d + splitDepth));
            return MathF.Max(d, -groove);
        }

        Sdf.Stage(s.PartId, "rod field");
        Vector3 lo = new(-RBig - pad - 2f, -boltY - lugY - 2f, -hSmall - 2f);
        Vector3 hi = new(L + RSmall + 2f, boltY + lugY + 2f, hSmall + 2f);
        return Sdf.Vox(lib, F, lo, hi);
    }
}
