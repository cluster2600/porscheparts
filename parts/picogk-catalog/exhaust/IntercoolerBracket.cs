using System.Numerics;
using PicoGK;

namespace PicoGKCatalog;

/// Port of parts/picogk-993-batch-01 IntercoolerBracket, bent onto the F0
/// planform: two curved rails (quadratic Beziers) spanning the two F0 end
/// bores form a lens truss, with solid end pads, the F0 central pedestal and
/// cross webs. Rails are a solid skin around an open-cell BCC lattice core;
/// every core segment has two powder drains through the bottom skin.
public sealed class IntercoolerBracket : IPartGenerator
{
    public string Name => "intercooler_bracket";

    public Voxels Build(Library lib, PartSpec s)
    {
        Vector2 A = new(s.P("left_bore_x_mm"), s.P("left_bore_y_mm")), B = new(s.P("right_bore_x_mm"), s.P("right_bore_y_mm"));
        float rA = s.P("left_bore_diameter_mm") / 2f, rB = s.P("right_bore_diameter_mm") / 2f;
        float pA = s.P("left_pad_radius_mm"), pB = s.P("right_pad_radius_mm"), pT = s.P("pad_thickness_mm");
        float px = s.P("pedestal_x_mm"), py = s.P("pedestal_y_mm"), pl = s.P("pedestal_length_mm"), pw = s.P("pedestal_width_mm");
        float Hh = s.P("height_mm"), pedR = s.P("pedestal_bore_diameter_mm") / 2f;
        Vector2 cLow = new(s.P("lower_ctrl_x_mm"), s.P("lower_ctrl_y_mm")), cUp = new(s.P("upper_ctrl_x_mm"), s.P("upper_ctrl_y_mm"));
        float rw = s.P("rail_width_mm"), rh = s.P("rail_height_mm");
        float webT = s.P("web_thickness_mm"), webH = s.P("web_height_mm");
        float skin = s.P("skin_mm"), cell = s.P("lattice_cell_mm"), gw = s.P("strut_diameter_mm");
        float drainR = s.P("drain_hole_diameter_mm") / 2f, fil = s.P("fillet_mm");

        Vector2 Bz(Vector2 c, float t) => (1 - t) * (1 - t) * A + 2 * t * (1 - t) * c + t * t * B;
        List<Vector2> lowP = new(), upP = new();
        for (int i = 0; i <= 40; i++) { lowP.Add(Bz(cLow, i / 40f)); upP.Add(Bz(cUp, i / 40f)); }

        float Rail(Vector3 p, float off)
        {
            Vector2 q = new(p.X, p.Y);
            float d2 = MathF.Min(FlowKit.Poly2(q, lowP), FlowKit.Poly2(q, upP)) - rw / 2f + off;
            return FlowKit.Extrude(d2, p.Z, off, rh - off, 2f);
        }
        Vector3 lo = new(-1, -1, -1), hi = new(B.X + pB + 1, py + pw + 1, Hh + 1);

        Sdf.Stage(s.PartId, "rails");
        Voxels rails = Sdf.Vox(lib, p => Rail(p, 0f), lo, new(hi.X, hi.Y, rh + 1));

        // Solid parts: end pads and pedestal (rounded), webs.
        Sdf.Stage(s.PartId, "solids");
        Vector2 pc = new(px + pl / 2f, py + pw / 2f);
        Voxels solids = Sdf.Vox(lib, p =>
        {
            Vector2 q = new(p.X, p.Y);
            float pads = MathF.Min(
                FlowKit.Extrude((q - A).Length() - pA, p.Z, 0f, pT, 1.5f),
                FlowKit.Extrude((q - B).Length() - pB, p.Z, 0f, pT, 1.5f));
            float ped = FlowKit.Extrude(FlowKit.RoundRect(q.X - pc.X, q.Y - pc.Y, pl / 2f, pw / 2f, 4f), p.Z, 0f, Hh, 1.5f);
            return MathF.Min(pads, ped);
        }, lo, hi);
        Voxels body = rails.voxDuplicate();
        body.BoolAdd(solids);
        Lattice webs = new(lib);
        foreach (float t in new[] { 0.25f, 0.5f, 0.75f })
        {
            Vector2 a = Bz(cLow, t), b = Bz(cUp, t);
            if (t == 0.5f) b = pc;
            webs.AddBeam(new Vector3(a, webH / 2f), new Vector3(b, webH / 2f), webT / 2f, webT / 2f, true);
        }
        Voxels webV = new(webs);
        webV.Trim(new BBox3(new Vector3(-10, -10, 0), new Vector3(300, 100, 50)));
        body.BoolAdd(webV);

        Sdf.Stage(s.PartId, "fillet");
        body.Fillet(fil);

        Sdf.Stage(s.PartId, "lattice core");
        Voxels cavity = Sdf.Vox(lib, p => Rail(p, skin), lo, new(hi.X, hi.Y, rh + 1));
        cavity.BoolSubtract(solids.voxOffset(skin));
        body.BoolSubtract(cavity);
        // Struts reach one voxel into the skin so every contact has volume.
        body.BoolAdd(Sdf.LatticeIn(lib, cavity.voxOffset(s.VoxelMm), cell, gw));

        Sdf.Stage(s.PartId, "holes");
        Lattice holes = new(lib);
        holes.AddBeam(new Vector3(A, -1), new Vector3(A, Hh + 1), rA, rA, false);
        holes.AddBeam(new Vector3(B, -1), new Vector3(B, Hh + 1), rB, rB, false);
        holes.AddBeam(new Vector3(pc, -1), new Vector3(pc, Hh + 1), pedR, pedR, false);
        // Two drains per core segment (lower rail: one segment; upper rail:
        // split by the pedestal into two).
        foreach (var (c, t) in new[] { (cLow, 0.15f), (cLow, 0.85f), (cUp, 0.15f), (cUp, 0.36f), (cUp, 0.66f), (cUp, 0.85f) })
        {
            Vector2 d = Bz(c, t);
            holes.AddBeam(new Vector3(d, -1), new Vector3(d, skin + 1f), drainR, drainR, false);
        }
        body.BoolSubtract(new Voxels(holes));
        return body;
    }
}
