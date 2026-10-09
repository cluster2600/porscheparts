using System.Numerics;
using PicoGK;

namespace PicoGKCatalog;

/// Timing chain case, open engine side down (z = 0 is the gasket face).
/// Planform: a large sprocket bay and a small one joined by tangent walls.
/// Conformal 4 mm shell on a bolted perimeter flange with gussets, the two
/// bay lids as raised bolted plateaus with a parting groove (case and lids
/// consolidated in one body), a chain-tensioner boss with its cap on the
/// side wall, and stiffening ribs on the face. Open underneath: no trapped
/// powder volume.
public sealed class ChainCase : IPartGenerator
{
    public string Name => "chain_case";

    public Voxels Build(Library lib, PartSpec s)
    {
        float L = s.P("length_mm"), W = s.P("width_mm"), H = s.P("height_mm");
        float wall = s.P("wall_mm"), inset = s.P("flange_width_mm"), tf = s.P("flange_thickness_mm");
        float rSmallBay = s.P("small_bay_radius_mm"), rEdge = s.P("top_edge_radius_mm");
        float lidRaise = s.P("lid_raise_mm");
        float rLidA = s.P("lid_a_radius_mm"), boltCircleA = s.P("lid_a_bolt_circle_mm") / 2f;
        int nLidA = s.N("lid_a_bolt_count");
        float rLidB = s.P("lid_b_radius_mm"), boltCircleB = s.P("lid_b_bolt_circle_mm") / 2f;
        int nLidB = s.N("lid_b_bolt_count");
        int nFlange = s.N("flange_bolt_count");
        float rFlangeBoss = s.P("flange_boss_diameter_mm") / 2f, rFlangeBolt = s.P("flange_bolt_diameter_mm") / 2f;
        float hFlangeBoss = s.P("flange_boss_height_mm");
        float rTens = s.P("tensioner_boss_diameter_mm") / 2f, rTensBore = s.P("tensioner_bore_diameter_mm") / 2f;
        float xTens = s.P("tensioner_x_mm"), zTens = s.P("tensioner_z_mm");
        float ribT = s.P("rib_thickness_mm") / 2f, ribH = s.P("rib_height_mm");
        int nGusset = s.N("gusset_count");

        float R1 = W / 2f, R2 = rSmallBay;
        float c1 = -L / 2f + R1, c2 = L / 2f - R2;
        float zShell = H - lidRaise;
        float S1 = R1 - inset, S2 = R2 - inset;   // shell planform radii

        var flangeBolts = new List<Vector2>();
        for (int i = 0; i < nFlange; i++)
            flangeBolts.Add(Es.TwinContour((i + 0.5f) / nFlange, c1, c2, R1 - inset / 2f, R2 - inset / 2f).pt);
        var gussets = new List<(Vector2 pt, Vector2 n)>();
        for (int i = 0; i < nGusset; i++)
            gussets.Add(Es.TwinContour(i / (float)nGusset, c1, c2, S1, S2));
        List<Vector2> Ring(float cx, float rc, int n, float phase)
        {
            var l = new List<Vector2>();
            for (int i = 0; i < n; i++)
            {
                float a = phase + i * 2f * MathF.PI / n;
                l.Add(new Vector2(cx + rc * MathF.Cos(a), rc * MathF.Sin(a)));
            }
            return l;
        }
        var lidBoltsA = Ring(c1, boltCircleA, nLidA, MathF.PI / nLidA);
        var lidBoltsB = Ring(c2, boltCircleB, nLidB, MathF.PI / nLidB);
        // Tensioner on the -y tangent wall.
        float h = c2 - c1, b = (S1 - S2) / h, a = MathF.Sqrt(1f - b * b);
        Vector2 nT = new(b, -a);
        float tWall = (xTens - (c1 + b * S1)) / (c2 - c1);
        Vector2 wallPt = Vector2.Lerp(new Vector2(c1 + b * S1, -a * S1), new Vector2(c2 + b * S2, -a * S2), Math.Clamp(tWall, 0f, 1f));
        Vector3 tensIn = new(wallPt.X - nT.X * 6f, wallPt.Y - nT.Y * 6f, zTens);
        float reach = s.P("tensioner_reach_mm");
        Vector3 tensOut = new(wallPt.X + nT.X * reach, wallPt.Y + nT.Y * reach, zTens);
        Vector3 capIn = new(wallPt.X + nT.X * (reach - 4f), wallPt.Y + nT.Y * (reach - 4f), zTens);

        float Lid(float x, float y, float cx, float rLid, List<Vector2> bolts, out float boltHeads)
        {
            float plan = Es.Len2(x - cx, y) - rLid;
            boltHeads = float.MaxValue;
            foreach (Vector2 q in bolts)
            {
                float rq = Es.Len2(x - q.X, y - q.Y);
                plan = Es.SMin(plan, rq - 6f, 3f);
                boltHeads = MathF.Min(boltHeads, rq - 3.5f);
            }
            return plan;
        }

        float F(Vector3 p)
        {
            float x = p.X, y = p.Y, z = p.Z;
            float plan = Es.TwinCircle(x, y, c1, c2, S1, S2);
            float ext = Es.RoundEdge(plan, z - zShell, rEdge);
            float d = MathF.Max(MathF.Max(ext, -z), -(ext + wall));
            // Perimeter flange with bolt bosses and gussets.
            float fplan = Es.TwinCircle(x, y, c1, c2, R1, R2);
            float flange = MathF.Max(MathF.Max(Es.RoundEdge(fplan, z - tf, 1.5f), -z), -(plan + wall));
            d = Es.SMin(d, flange, 3f);
            float bosses = float.MaxValue, holes = float.MaxValue;
            foreach (Vector2 q in flangeBolts)
            {
                float rq = Es.Len2(x - q.X, y - q.Y);
                bosses = MathF.Min(bosses, Es.RoundEdge(rq - rFlangeBoss, z - hFlangeBoss, 1f));
                holes = MathF.Min(holes, rq - rFlangeBolt);
            }
            d = Es.SMin(d, MathF.Max(MathF.Max(bosses, -z), -(plan + wall)), 2f);
            float gus = float.MaxValue;
            foreach (var (pt, n) in gussets)
            {
                if (Vector2.Distance(pt, wallPt) < rTens + 6f) continue;   // keep the tensioner boss clear
                float u = (x - pt.X) * n.X + (y - pt.Y) * n.Y, v = -(x - pt.X) * n.Y + (y - pt.Y) * n.X;
                float tri = (u * 30f + (z - tf) * (inset - 1f) - (inset - 1f) * 30f) / MathF.Sqrt(900f + (inset - 1f) * (inset - 1f));
                gus = MathF.Min(gus, MathF.Max(MathF.Max(MathF.Abs(v) - ribT, -u - 2f), MathF.Max(tri, tf - 1f - z)));
            }
            d = Es.SMin(d, gus, 1.5f);
            // Lids: raised bolted plateaus with parting groove and bolt heads.
            float lidA = Lid(x, y, c1, rLidA, lidBoltsA, out float headsA);
            float lidB = Lid(x, y, c2, rLidB, lidBoltsB, out float headsB);
            float lids = Es.RoundEdge(MathF.Min(lidA, lidB), MathF.Max(zShell - 2f - z, z - (H - 1.2f)), 1.2f);
            float heads = Es.RoundEdge(MathF.Min(headsA, headsB), MathF.Max(zShell - z, z - H), 0.6f);
            float lidRing = MathF.Max(MathF.Abs(MathF.Min(lidA, lidB) - 0.6f) - 0.5f, MathF.Abs(z - zShell) - 0.6f);
            d = MathF.Max(MathF.Min(d, lids), -lidRing);
            d = MathF.Min(d, heads);
            // Face ribs between the bays.
            float ribs = float.MaxValue;
            foreach (float ry in new[] { -0.3f * S2, 0f, 0.3f * S2 })
                ribs = MathF.Min(ribs, Sdf.RoundBox(p, new Vector3((c1 + rLidA + c2 - rLidB) / 2f, ry, zShell - 1f + ribH / 2f),
                                                     new Vector3((c2 - rLidB - c1 - rLidA) / 2f + 4f, ribT, ribH / 2f + 1f), ribT * 0.9f));
            d = Es.SMin(d, ribs, 2f);
            // Chain tensioner boss with its cap on the side wall.
            float tens = Es.Cyl(p, tensIn, tensOut, rTens);
            d = Es.SMin(d, tens, 3f);
            Vector3 n3 = new(nT.X, nT.Y, 0f);
            float capGroove = MathF.Max(Es.Cyl(p, capIn, capIn + n3 * 0.8f, rTens + 1f),
                                        -Es.Cyl(p, capIn - n3, capIn + n3 * 1.8f, rTens - 0.8f));
            d = MathF.Max(d, -capGroove);
            float tensBore = Es.Cyl(p, tensIn - n3 * 4f, capIn - n3 * 1.5f, rTensBore);
            d = MathF.Max(d, -tensBore);
            return MathF.Max(d, -MathF.Max(holes, MathF.Max(-z - 1f, z - hFlangeBoss - 1f)));
        }

        Sdf.Stage(s.PartId, "chain case field");
        return Sdf.Vox(lib, F, new Vector3(-L / 2f - 1.5f, -W / 2f - 1.5f, -1.5f), new Vector3(L / 2f + 1.5f, W / 2f + 1.5f, H + 1.5f));
    }
}
