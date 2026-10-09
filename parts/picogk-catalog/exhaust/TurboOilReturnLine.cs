using System.Numerics;
using PicoGK;

namespace PicoGKCatalog;

/// Oil line: tube swept along a Catmull-Rom spline through the F0 control
/// points with vertical end tangents, two horizontal two-bolt flanges centred
/// on the end points (bolt lobes) and a mid-span support tab, all filleted
/// into one body before the bore is cut (bore open at both ends).
public sealed class TurboOilReturnLine : IPartGenerator
{
    public string Name => "turbo_oil_return_line";

    public Voxels Build(Library lib, PartSpec s)
    {
        float ro = s.P("tube_outer_diameter_mm") / 2f, ri = ro - s.P("tube_wall_mm");
        float fR = s.P("flange_diameter_mm") / 2f, fT = s.P("flange_thickness_mm");
        float bc = s.P("flange_bolt_centres_mm") / 2f, bR = s.P("flange_bore_diameter_mm") / 2f;
        float lobeR = s.P("flange_lobe_radius_mm"), fil = s.P("fillet_mm");
        float tabT = s.P("clip_tab_t"), tabL = s.P("clip_tab_length_mm"), tabTh = s.P("clip_tab_thickness_mm"), tabHole = s.P("clip_tab_hole_diameter_mm") / 2f;

        List<Vector3> cps = new();
        for (int i = 0; i < 6; i++) cps.Add(new(s.P($"cp{i}_x_mm"), s.P($"cp{i}_y_mm"), s.P($"cp{i}_z_mm")));
        Vector3 up = new(0, 0, 24f);
        List<Vector3> path = FlowKit.CatmullRom(cps, up, up, 16);
        Vector3 a = path[0], b = path[^1];

        Sdf.Stage(s.PartId, "tube");
        Lattice outerLat = new(lib);
        FlowKit.Sweep(outerLat, path, _ => ro, true);


        // Support tab at mid-span: a lug sticking out sideways (+Y side of the
        // local tube direction) with a bolt hole.
        int k = (int)Math.Round(tabT * (path.Count - 1));
        Vector3 pc = path[k], dir = Vector3.Normalize(path[Math.Min(k + 1, path.Count - 1)] - path[Math.Max(k - 1, 0)]);
        Vector3 side = Vector3.Normalize(Vector3.Cross(dir, Vector3.UnitZ));
        if (side.Y < 0) side = -side;
        Vector3 tabEnd = pc + side * tabL;
        Vector3 nrm = Vector3.Normalize(Vector3.Cross(dir, side));
        Voxels body = new(outerLat);

        Sdf.Stage(s.PartId, "flanges");
        float Flange(Vector3 p, Vector3 c)
        {
            Vector2 q = new(p.X - c.X, p.Y - c.Y);
            float d = FlowKit.Smin(q.Length() - fR, MathF.Min((q - new Vector2(-bc, 0)).Length(), (q - new Vector2(bc, 0)).Length()) - lobeR, 3f);
            return FlowKit.Extrude(d, p.Z, c.Z - fT / 2f, c.Z + fT / 2f, 0.8f);
        }
        float fx = bc + lobeR + 1f;
        foreach (Vector3 c in new[] { a, b })
            body.BoolAdd(Sdf.Vox(lib, p => Flange(p, c), c - new Vector3(fx, fR + 1, fT), c + new Vector3(fx, fR + 1, fT)));
        Vector3 tlo = Vector3.Min(pc, tabEnd) - new Vector3(10), thi = Vector3.Max(pc, tabEnd) + new Vector3(10);
        body.BoolAdd(Sdf.Vox(lib, p =>
        {
            // flat lug: capsule in the tab plane, thickness along nrm
            float dPlane = MathF.Abs(Vector3.Dot(p - pc, nrm)) - tabTh / 2f;
            Vector3 q = p - nrm * Vector3.Dot(p - pc, nrm);
            float dCap = Sdf.Capsule(q, pc, tabEnd, 6f);
            return FlowKit.Extrude(dCap, dPlane, -1e3f, 0f, 0.6f);
        }, tlo, thi));

        Sdf.Stage(s.PartId, "fillet");
        body.Fillet(fil);

        Sdf.Stage(s.PartId, "bores");
        Lattice cut = new(lib);
        List<Vector3> bore = new() { a - new Vector3(0, 0, fT) };
        bore.AddRange(path);
        bore.Add(b + new Vector3(0, 0, fT));
        FlowKit.Sweep(cut, bore, _ => ri, false);
        foreach (Vector3 c in new[] { a, b })
            foreach (float dx in new[] { -bc, bc })
                cut.AddBeam(c + new Vector3(dx, 0, -fT), c + new Vector3(dx, 0, fT), bR, bR, false);
        cut.AddBeam(tabEnd - nrm * (tabTh + 1f), tabEnd + nrm * (tabTh + 1f), tabHole, tabHole, false);
        body.BoolSubtract(new Voxels(cut));
        // Bolt heads / nuts need flat seats: clear the root fillet above the
        // start flange and below the end flange around each bolt.
        Lattice seats = new(lib);
        foreach (float dx in new[] { -bc, bc })
        {
            seats.AddBeam(a + new Vector3(dx, 0, fT / 2f), a + new Vector3(dx, 0, fT / 2f + 6f), bR + 1.5f, bR + 1.5f, false);
            seats.AddBeam(b - new Vector3(-dx, 0, fT / 2f), b - new Vector3(-dx, 0, fT / 2f + 6f), bR + 1.5f, bR + 1.5f, false);
        }
        body.BoolSubtract(new Voxels(seats));
        return body;
    }
}
