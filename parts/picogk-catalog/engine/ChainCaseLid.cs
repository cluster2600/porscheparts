using System.Numerics;
using PicoGK;

namespace PicoGKCatalog;

/// Chain-case lid concept (964 105 107 01), gasket face at z = 0, lid
/// outward +Z. Elliptic outline sized from the screening plan area and the
/// extreme bolt span of parts/993-eng-chain-case-lid-ti-f0-0001/source/
/// chain_case_lid_screen.py; the plate keeps the screen's thickness and is
/// domed in its centre (constant thickness, so the dome's underside is an
/// open recess facing the chain, not a sealed cavity). Low organic ribs flow
/// from each bolt boss toward the dome crown and blend into it; flat bolt
/// seats are kept around the clearance holes. One implicit field.
public sealed class ChainCaseLid : IPartGenerator
{
    public string Name => "chain_case_lid";

    public Voxels Build(Library lib, PartSpec s)
    {
        float span = s.P("extreme_hole_span_mm"), area = s.P("plan_area_cm2") * 100f, t = s.P("thickness_mm");
        float hole = s.P("clearance_hole_mm") / 2f, boss = s.P("bolt_boss_radius_mm"), bossH = s.P("bolt_boss_height_mm");
        int nb = s.N("bolt_count");
        float land = s.P("gasket_land_mm"), dome = s.P("dome_height_mm");
        float ribW = s.P("rib_width_mm") / 2f, ribH = s.P("rib_height_mm"), edge = s.P("edge_radius_mm");

        // Outline: ellipse with the bolt ring inset by the boss margin and pi*a*b = plan area.
        float margin = boss + 2.5f;
        float a = span / 2f + margin, b = area / (MathF.PI * a);
        float ra = a - margin, rb = b - margin;                 // bolt ring semi-axes (extreme span = 2*ra)
        float da = ra - boss - land, db = rb - boss - land;      // dome footprint semi-axes
        List<Vector2> bolts = new();
        for (int i = 0; i < nb; i++)
        {
            float ang = i * 2f * MathF.PI / nb;                  // holes 0 and nb/2 on the major axis
            bolts.Add(new Vector2(ra * MathF.Cos(ang), rb * MathF.Sin(ang)));
        }

        static float Ellipse(float x, float y, float ea, float eb)
        {
            float k0 = new Vector2(x / ea, y / eb).Length();
            float k1 = new Vector2(x / (ea * ea), y / (eb * eb)).Length();
            return k1 > 1e-6f ? k0 * (k0 - 1f) / k1 : -MathF.Min(ea, eb);
        }
        float Bump(float x, float y)
        {
            float u = new Vector2(x / da, y / db).Length();
            if (u >= 1f) return 0f;
            float v = 1f - u * u;
            return v * v * (3f - 2f * v);                        // smooth crown, zero slope at the rim
        }

        float F(Vector3 p)
        {
            float x = p.X, y = p.Y, z = p.Z;
            float lift = dome * Bump(x, y);
            float plan = Ellipse(x, y, a, b);
            // constant-thickness domed plate, outer edge rounded on the outside only
            float zTop = lift + t, zBot = lift;
            float slab = MathF.Max(zBot - z, z - zTop);
            float d = Es.RoundEdge(plan, z - zTop, edge);
            d = MathF.Max(d, zBot - z);
            d = MathF.Max(d, slab);
            // ribs from each boss toward the crown, height fading to zero at the centre
            float ribs = float.MaxValue;
            foreach (Vector2 q in bolts)
            {
                Vector2 tip = q * 0.18f;
                float dl = Es.Seg2(x, y, q.X, q.Y, tip.X, tip.Y);
                float along = Math.Clamp(Vector2.Dot(new Vector2(x, y) - q, tip - q) / (tip - q).LengthSquared(), 0f, 1f);
                float wHere = ribW * (1.15f - 0.45f * along);
                float hHere = ribH * MathF.Sin(MathF.PI * MathF.Min(1f, along * 1.1f + 0.08f));
                float r = Es.RoundEdge(dl - wHere, z - (zTop + hHere), wHere * 0.9f);
                ribs = MathF.Min(ribs, MathF.Max(r, zBot + 0.5f - z));
            }
            d = Es.SMin(d, ribs, 4f);
            // bolt bosses: flat seats slightly proud of the plate
            float bosses = float.MaxValue, holes = float.MaxValue;
            foreach (Vector2 q in bolts)
            {
                float rq = Es.Len2(x - q.X, y - q.Y);
                bosses = MathF.Min(bosses, MathF.Max(Es.RoundEdge(rq - boss, z - (t + bossH), 1.2f), -z));
                holes = MathF.Min(holes, rq - hole);
            }
            d = Es.SMin(d, bosses, 2.5f);
            // keep the gasket face flat and the bolt seats flat
            d = MathF.Max(d, -z);
            float seatCut = float.MaxValue;
            foreach (Vector2 q in bolts)
                seatCut = MathF.Min(seatCut, MathF.Max(Es.Len2(x - q.X, y - q.Y) - (hole + 3.5f), (t + bossH) - z));
            d = MathF.Max(d, -seatCut);
            return MathF.Max(d, -holes);
        }

        Sdf.Stage(s.PartId, "lid field");
        float zMax = dome + t + ribH + 2f;
        return Sdf.Vox(lib, F, new Vector3(-a - 1.5f, -b - 1.5f, -1f), new Vector3(a + 1.5f, b + 1.5f, zMax));
    }
}
