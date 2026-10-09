using System.Numerics;
using PicoGK;

namespace PicoGKCatalog;

/// Three-into-one manifold, axis Z: three head ports at z = 0 (common flange),
/// primaries leave vertically and bend along quadratic Beziers into a
/// collector ending at the outlet flange (z = total length). The outer body
/// (tubes + flanges) is filleted as one solid before the flow passages are
/// subtracted, so the crotch blends smoothly and nothing is sealed.
public sealed class ExhaustManifold : IPartGenerator
{
    public string Name => "exhaust_manifold_3into1";

    public Voxels Build(Library lib, PartSpec s)
    {
        float rpi = s.P("primary_inner_diameter_mm") / 2f, rci = s.P("collector_inner_diameter_mm") / 2f, w = s.P("wall_mm");
        float sx = s.P("port_spacing_x_mm"), sy = s.P("port_offset_y_mm");
        float ex = s.P("merge_spacing_x_mm"), ey = s.P("merge_offset_y_mm");
        float zm = s.P("merge_z_mm"), zc = s.P("collector_start_z_mm"), Lt = s.P("total_length_mm"), zb = s.P("bend_control_z_mm");
        float fT = s.P("head_flange_thickness_mm"), fRim = s.P("head_flange_rim_mm");
        float boltR = s.P("bolt_hole_diameter_mm") / 2f, bossR = s.P("bolt_boss_radius_mm"), nutR = s.P("nut_clearance_radius_mm");
        float oT = s.P("outlet_flange_thickness_mm"), oR = s.P("outlet_flange_radius_mm"), oB = s.P("outlet_bolt_offset_mm");
        float fil = s.P("fillet_mm");
        float rpo = rpi + w, rco = rci + w;

        Vector2[] ports = { new(-sx, -sy), new(0, 0), new(sx, sy) };
        Vector2[] ends = { new(-ex, -ey), new(0, 0), new(ex, ey) };
        Vector2[] bolts = { (ports[0] + ports[1]) / 2f, (ports[1] + ports[2]) / 2f };

        Sdf.Stage(s.PartId, "tubes");
        Lattice outerLat = new(lib), innerLat = new(lib);
        for (int i = 0; i < 3; i++)
        {
            Vector3 a = new(ports[i], 0), b = new(ports[i], zb), c = new(ends[i], zm);
            List<Vector3> path = FlowKit.Bezier(a, b, c, 48);
            FlowKit.Sweep(outerLat, path, _ => rpo, false);
            List<Vector3> bore = new() { new Vector3(ports[i], -3f) };
            bore.AddRange(path);
            FlowKit.Sweep(innerLat, bore, _ => rpi, false);
        }
        // Collector: short cone under the merge so the outer skin closes
        // smoothly around the converging primaries, then the straight pipe.
        outerLat.AddBeam(new Vector3(0, 0, zc - 10f), new Vector3(0, 0, zc + 15f), rco * 0.8f, rco, true);
        outerLat.AddBeam(new Vector3(0, 0, zc + 15f), new Vector3(0, 0, Lt), rco, rco, false);
        innerLat.AddBeam(new Vector3(0, 0, zc + 5f), new Vector3(0, 0, zm), rpi * 0.7f, rci, true);
        innerLat.AddBeam(new Vector3(0, 0, zm), new Vector3(0, 0, Lt + 3f), rci, rci, true);
        Voxels body = new(outerLat);
        // The round cap of the primaries' outer beams must not poke below the flange.
        body.Trim(new BBox3(new Vector3(-500, -500, 0), new Vector3(500, 500, Lt)));

        Sdf.Stage(s.PartId, "flanges");
        float rf = rpo + fRim;
        float Head2(Vector2 q)
        {
            float d = float.MaxValue;
            foreach (Vector2 p in ports) d = FlowKit.Smin(d, (q - p).Length() - rf, 6f);
            foreach (Vector2 p in bolts) d = FlowKit.Smin(d, (q - p).Length() - bossR - 3f, 6f);
            return d;
        }
        float hx = sx + rf + 2f, hy = sy + rf + 2f;
        body.BoolAdd(Sdf.Vox(lib, p => FlowKit.Extrude(Head2(new(p.X, p.Y)), p.Z, 0f, fT, 1f),
            new(-hx, -hy, -1), new(hx, hy, fT + 1)));
        float Out2(Vector2 q) => FlowKit.Smin(q.Length() - oR,
            MathF.Min((q - new Vector2(-oB, 0)).Length(), (q - new Vector2(oB, 0)).Length()) - bossR - 1f, 8f);
        float ox = oB + bossR + 3f;
        body.BoolAdd(Sdf.Vox(lib, p => FlowKit.Extrude(Out2(new(p.X, p.Y)), p.Z, Lt - oT, Lt, 1f),
            new(-ox, -oR - 2, Lt - oT - 1), new(ox, oR + 2, Lt + 1)));

        Sdf.Stage(s.PartId, "fillet");
        body.Fillet(fil);

        Sdf.Stage(s.PartId, "passages");
        body.BoolSubtract(new Voxels(innerLat));
        body.Trim(new BBox3(new Vector3(-500, -500, 0), new Vector3(500, 500, Lt)));

        Sdf.Stage(s.PartId, "bolts");
        Lattice holes = new(lib);
        foreach (Vector2 p in bolts)
        {
            holes.AddBeam(new Vector3(p, -2f), new Vector3(p, fT + 1f), boltR, boltR, false);
            holes.AddBeam(new Vector3(p, fT), new Vector3(p, fT + 18f), nutR, nutR, true);
        }
        foreach (float x in new[] { -oB, oB })
        {
            holes.AddBeam(new Vector3(x, 0, Lt - oT - 1f), new Vector3(x, 0, Lt + 2f), boltR, boltR, false);
            holes.AddBeam(new Vector3(x, 0, Lt - oT - 30f), new Vector3(x, 0, Lt - oT), nutR, nutR, true);
        }
        body.BoolSubtract(new Voxels(holes));
        return body;
    }
}
