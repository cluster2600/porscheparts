using System.Numerics;
using PicoGK;

namespace PicoGKCatalog;

/// Charge-air pressure pipes (PET 107-45 pos 19, left and right), flow axis
/// X: turbo end at x = 0, intercooler end at x = length. Each pipe is a
/// swept S-bend whose bore grows smoothly from the turbo-end to the
/// cooler-end diameter, with straight clamp cuffs and a rolled hose-retention
/// bead near each end. The vertical and lateral offsets are solved so each
/// pipe fills its declared product envelope. The two pipes stand side by
/// side, joined by two organic display ties (not part of either pipe, not the
/// pos 5 bracket). The outer body is filleted as one solid before the bores
/// are cut; both ends are trimmed flat and open.
public sealed class ChargePipeSet : IPartGenerator
{
    public string Name => "charge_pipe_pair";

    static Vector3 Cubic(Vector3 a, Vector3 b, Vector3 c, Vector3 d, float t)
    {
        float u = 1f - t;
        return u * u * u * a + 3f * u * u * t * b + 3f * u * t * t * c + t * t * t * d;
    }

    public Voxels Build(Library lib, PartSpec s)
    {
        float L = s.P("hose_length_mm"), W = s.P("hose_width_mm");
        float hL = s.P("hose_left_height_mm"), hR = s.P("hose_right_height_mm");
        float ri0 = s.P("turbo_end_bore_mm") / 2f, ri1 = s.P("cooler_end_bore_mm") / 2f, w = s.P("wall_mm");
        float cuff = s.P("cuff_length_mm"), handle = s.P("bend_handle_fraction");
        float bh = s.P("bead_height_mm"), bIn = s.P("bead_inset_mm");
        float gap = s.P("pair_spacing_mm"), tieR = s.P("tie_radius_mm") , fil = s.P("fillet_mm");
        float ro0 = ri0 + w, ro1 = ri1 + w;
        float re0 = ro0 + bh, re1 = ro1 + bh;

        // One pipe: centreline points, matching bore radii and the x of each point.
        (List<Vector3> pts, List<float> rIn) Pipe(float y0, float side, float height)
        {
            float dz = height - re0 - re1;              // fills the declared height
            float dy = side * (W - re0 - re1);          // fills the declared width, outboard
            Vector3 a = new(cuff, y0, 0f), d = new(L - cuff, y0 + dy, dz);
            Vector3 b = a + new Vector3(handle * (L - 2f * cuff), 0, 0), c = d - new Vector3(handle * (L - 2f * cuff), 0, 0);
            List<Vector3> p = new() { new(-3f, y0, 0f), new(0f, y0, 0f) };
            for (int i = 0; i <= 8; i++) p.Add(new Vector3(cuff * i / 8f, y0, 0f));
            for (int i = 1; i <= 96; i++) p.Add(Cubic(a, b, c, d, i / 96f));
            for (int i = 1; i <= 8; i++) p.Add(d + new Vector3(cuff * i / 8f, 0, 0));
            p.Add(new Vector3(L + 3f, y0 + dy, dz));
            List<float> r = new();
            foreach (Vector3 q in p)
                r.Add(ri0 + (ri1 - ri0) * FlowKit.Smooth((q.X - cuff) / (L - 2f * cuff)));
            return (p, r);
        }

        var left = Pipe(gap / 2f, 1f, hL);
        var right = Pipe(-gap / 2f, -1f, hR);

        Sdf.Stage(s.PartId, "pipes");
        Lattice outer = new(lib), bore = new(lib);
        foreach (var (pts, rIn) in new[] { left, right })
        {
            // outer skin from x = 0 to x = L (end points 1 .. n-2), bore over the full extended path
            List<Vector3> skin = pts.GetRange(1, pts.Count - 2);
            List<float> rs = rIn.GetRange(1, rIn.Count - 2);
            FlowKit.Sweep(outer, skin, i => rs[i] + w, true);
            FlowKit.Sweep(bore, pts, i => rIn[i], true);
            // rolled retention beads (torus rings) near both ends
            foreach (Vector3 c in new[] { pts[1] + new Vector3(bIn, 0, 0), pts[^2] - new Vector3(bIn, 0, 0) })
            {
                float rr = (c.X < L / 2f ? ro0 : ro1) - 0.5f;
                const int n = 72;
                for (int k = 0; k < n; k++)
                {
                    float a0 = k * 2f * MathF.PI / n, a1 = (k + 1) * 2f * MathF.PI / n;
                    Vector3 p0 = c + new Vector3(0, rr * MathF.Cos(a0), rr * MathF.Sin(a0));
                    Vector3 p1 = c + new Vector3(0, rr * MathF.Cos(a1), rr * MathF.Sin(a1));
                    outer.AddBeam(p0, p1, bh + 0.5f, bh + 0.5f, true);
                }
            }
        }
        // Display ties between the two centrelines (bores cut them back to the walls).
        foreach (float t in new[] { s.P("tie_t1"), s.P("tie_t2") })
        {
            int k = (int)MathF.Round(t * (left.pts.Count - 1));
            Vector3 pa = left.pts[k], pb = right.pts[k];
            Vector3 mid = (pa + pb) / 2f - new Vector3(0, 0, 0.25f * MathF.Abs(pa.Z - pb.Z));
            outer.AddBeam(pa, mid, tieR, tieR * 0.8f, true);
            outer.AddBeam(mid, pb, tieR * 0.8f, tieR, true);
        }
        Voxels body = new(outer);

        Sdf.Stage(s.PartId, "fillet");
        body.Fillet(fil);

        Sdf.Stage(s.PartId, "bores");
        body.BoolSubtract(new Voxels(bore));
        // Tight trim box: Trim intersects with a box solid, whose surface costs memory.
        BBox3 bb = body.oCalculateBoundingBox();
        body.Trim(new BBox3(new Vector3(0f, bb.vecMin.Y - 1f, bb.vecMin.Z - 1f), new Vector3(L, bb.vecMax.Y + 1f, bb.vecMax.Z + 1f)));
        return body;
    }
}
