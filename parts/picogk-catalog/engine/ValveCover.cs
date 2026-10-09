using System.Numerics;
using PicoGK;

namespace PicoGKCatalog;

/// Upper valve cover, open oil side down (z = 0 is the gasket face). Domed
/// shell with rounded top edges set in from a perimeter gasket flange;
/// bolt bosses sit in scalloped pockets of the wall so the nut faces are
/// reachable; cooling fins on the roof; coil-on-plug towers with through
/// bores to the plug wells and a coil retaining-screw ear each. All joints
/// carry smooth-min fillets; the shell is hollowed conformally (scallops
/// included) after the outer form is filleted.
public sealed class ValveCover : IPartGenerator
{
    public string Name => "valve_cover_cop";

    public Voxels Build(Library lib, PartSpec s)
    {
        float L = s.P("length_mm") / 2f, W = s.P("width_mm") / 2f, H = s.P("shell_height_mm");
        float roof = s.P("roof_thickness_mm"), wall = s.P("wall_thickness_mm");
        float inset = s.P("side_flange_width_mm"), tf = s.P("flange_thickness_mm");
        float rTop = s.P("top_edge_radius_mm"), rCorner = s.P("plan_corner_radius_mm");
        float towerH = s.P("cop_tower_height_mm"), rTower = s.P("cop_tower_outer_diameter_mm") / 2f;
        float rTowerBore = s.P("cop_tower_bore_diameter_mm") / 2f;
        float[] towerX = { s.P("cop_tower_1_x_mm"), s.P("cop_tower_2_x_mm"), s.P("cop_tower_3_x_mm") };
        float earOff = s.P("coil_ear_offset_mm"), rEar = s.P("coil_ear_diameter_mm") / 2f, rEarHole = s.P("coil_ear_hole_diameter_mm") / 2f;
        float rBoss = s.P("bolt_boss_outer_diameter_mm") / 2f, rBolt = s.P("bolt_bore_diameter_mm") / 2f;
        float hBoss = s.P("bolt_boss_height_mm"), rScallop = s.P("bolt_pocket_radius_mm");
        int nBoltX = s.N("bolt_count_per_side");
        float boltPitch = s.P("bolt_pitch_x_mm"), boltY = s.P("bolt_y_mm");
        int nFin = s.N("fin_count");
        float finL = s.P("fin_length_mm") / 2f, finT = s.P("fin_thickness_mm") / 2f, finH = s.P("fin_height_mm");
        float finPitch = s.P("fin_pitch_y_mm");

        var bolts = new List<Vector2>();
        for (int i = 0; i < nBoltX; i++)
            foreach (float y in new[] { -boltY, boltY })
                bolts.Add(new Vector2((i - (nBoltX - 1) / 2f) * boltPitch, y));
        var fins = new List<float>();
        for (int i = 0; i < nFin; i++) fins.Add((i - (nFin - 1) / 2f) * finPitch);
        float zTowerTop = H + towerH;

        float F(Vector3 p)
        {
            float x = p.X, y = p.Y, z = p.Z;
            // Outer shell form (unbounded below), bolt pockets scalloped in.
            float plan = Es.Rect2(x, y, 0f, 0f, L - inset, W - inset, rCorner);
            float ext = Es.RoundEdge(plan, z - H, rTop);
            float pockets = float.MaxValue, bosses = float.MaxValue, holes = float.MaxValue;
            foreach (Vector2 b in bolts)
            {
                float rb = Es.Len2(x - b.X, y - b.Y);
                pockets = MathF.Min(pockets, MathF.Max(rb - rScallop, hBoss - z));
                bosses = MathF.Min(bosses, Es.RoundEdge(rb - rBoss, MathF.Max(-z, z - hBoss), 0.8f));
                holes = MathF.Min(holes, rb - rBolt);
            }
            ext = Es.SMax(ext, -pockets, 2f);
            float shell = MathF.Max(MathF.Max(ext, -z), -(ext + wall));
            // Perimeter gasket flange, inner edge on the cavity.
            float fplan = Es.Rect2(x, y, 0f, 0f, L, W, rCorner + inset);
            float flange = MathF.Max(MathF.Max(Es.RoundEdge(fplan, z - tf, 1.5f), -z), -(plan + wall));
            float d = Es.SMin(shell, flange, 3f);
            d = Es.SMin(d, bosses, 1.5f);
            // Roof fins.
            float fin = float.MaxValue;
            foreach (float fy in fins)
                fin = MathF.Min(fin, Sdf.RoundBox(p, new Vector3(0f, fy, H - 1f + (finH + 1f) / 2f),
                                                   new Vector3(finL, finT, (finH + 1f) / 2f), finT * 0.9f));
            d = Es.SMin(d, fin, 2f);
            // Coil-on-plug towers and screw ears.
            float towers = float.MaxValue, bores = float.MaxValue;
            foreach (float tx in towerX)
            {
                float rt = Es.Len2(x - tx, y);
                towers = MathF.Min(towers, Es.RoundEdge(rt - rTower, MathF.Max(H - roof - z, z - zTowerTop), 1.2f));
                float re = Es.Len2(x - tx - earOff, y);
                towers = Es.SMin(towers, Es.RoundEdge(re - rEar, MathF.Max(H - roof - z, z - (zTowerTop - 6f)), 1f), 2f);
                bores = MathF.Min(bores, MathF.Max(rt - rTowerBore, H - roof - 2f - z));
                bores = MathF.Min(bores, MathF.Max(re - rEarHole, zTowerTop - 16f - z));
            }
            d = Es.SMin(d, towers, 4f);
            d = MathF.Max(d, -bores);
            return MathF.Max(d, -MathF.Max(holes, -z - 1f));
        }

        Sdf.Stage(s.PartId, "cover field");
        return Sdf.Vox(lib, F, new Vector3(-L - 1.5f, -W - 1.5f, -1.5f), new Vector3(L + 1.5f, W + 1.5f, zTowerTop + 1.5f));
    }
}
