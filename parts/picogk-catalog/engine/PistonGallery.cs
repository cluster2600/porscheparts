using System.Numerics;
using PicoGK;

namespace PicoGKCatalog;

/// Piston with closed toroidal cooling gallery under the crown, opened by two
/// radial depowdering ports. Axis Z, crown up, pin axis X. Crown with a
/// spherical dish, top land, three ring grooves with oil-drain holes in the
/// oil-ring groove, slipper skirt (pin-side panels recessed, thrust faces
/// kept), conformal under-crown cavity, two pin-boss stubs with circlip
/// grooves hung from the crown by load webs, all blended with smooth-min
/// fillets.
public sealed class PistonGallery : IPartGenerator
{
    public string Name => "piston_cooling_gallery";

    public Voxels Build(Library lib, PartSpec s)
    {
        float R = s.P("piston_outer_diameter_mm") / 2f, H = s.P("piston_height_mm");
        float zTop = H / 2f;
        float rCav = s.P("inner_cavity_diameter_mm") / 2f, zCav = s.P("inner_cavity_top_z_mm");
        float zPin = s.P("pin_axis_z_mm"), rPin = s.P("pin_bore_diameter_mm") / 2f;
        float rBoss = s.P("pin_boss_outer_diameter_mm") / 2f, xBoss = s.P("pin_boss_length_mm") / 2f;
        float xGap = s.P("boss_inner_gap_mm") / 2f, web = s.P("boss_web_thickness_mm") / 2f;
        float rRoot = s.P("ring_groove_root_diameter_mm") / 2f;
        float[] gz = { s.P("ring_groove_1_center_z_mm"), s.P("ring_groove_2_center_z_mm"), s.P("ring_groove_3_center_z_mm") };
        float[] gh = { s.P("ring_groove_1_height_mm"), s.P("ring_groove_2_height_mm"), s.P("ring_groove_3_height_mm") };
        float rBowl = s.P("bowl_diameter_mm") / 2f, dBowl = s.P("bowl_depth_mm");
        float Rg = s.P("gallery_major_radius_mm"), rg = s.P("gallery_minor_radius_mm"), zg = s.P("gallery_center_z_mm");
        float rPort = s.P("gallery_port_diameter_mm") / 2f, xPort = s.P("gallery_port_center_x_mm"), lPort = s.P("gallery_port_length_mm");
        float xWin = s.P("skirt_panel_x_mm"), yWin = s.P("skirt_panel_half_width_mm"), zWin = s.P("skirt_panel_top_z_mm");
        float wall = s.P("skirt_panel_wall_mm");
        int nDrain = s.N("oil_drain_hole_count");
        float rDrain = s.P("oil_drain_hole_diameter_mm") / 2f;
        float rClip = s.P("circlip_groove_diameter_mm") / 2f, wClip = s.P("circlip_groove_width_mm") / 2f;
        float xClip = s.P("circlip_groove_x_mm");

        float sphR = (rBowl * rBowl + dBowl * dBowl) / (2f * dBowl);
        Vector3 sphC = new(0f, 0f, zTop - dBowl + sphR);
        var drains = new List<Vector2>();
        for (int k = 0; k < nDrain; k++)
        {
            float a = (k + 0.5f) * 2f * MathF.PI / nDrain;
            drains.Add(new Vector2(MathF.Cos(a), MathF.Sin(a)));
        }

        float F(Vector3 p)
        {
            float r = Es.Len2(p.X, p.Y), ax = MathF.Abs(p.X);
            Vector3 q = new(ax, p.Y, p.Z);
            float outer = Es.Rect2(r, p.Z, 0f, 0f, R, H / 2f, 0.8f);
            // Slipper skirt: recess the pin-side panels below the ring belt.
            float panel = Es.SMax(Es.SMax(xWin - ax, MathF.Abs(p.Y) - yWin, 4f), p.Z - zWin, 4f);
            outer = Es.SMax(outer, -panel, 2.5f);
            // Under-crown cavity: concept bore, conformal behind the panels, open below.
            float cav = MathF.Max(Es.SMax(r - rCav, p.Z - zCav, 5f), outer + wall);
            float d = MathF.Max(outer, -cav);
            // Pin-boss stubs hung from the crown by load webs.
            float boss = Es.Cyl(q, new Vector3(xGap, 0f, zPin), new Vector3(xBoss, 0f, zPin), rBoss);
            float webs = Sdf.RoundBox(q, new Vector3((xGap + 2f + xWin) / 2f, 0f, (zPin + zCav + 4f) / 2f),
                                      new Vector3((xWin - xGap - 2f) / 2f, web, (zCav + 4f - zPin) / 2f), 1f);
            d = Es.SMin(d, Es.SMin(boss, webs, 4f), 3f);
            // Crown dish.
            d = Es.SMax(d, -Sdf.Sphere(p, sphC, sphR), 1.5f);
            // Ring grooves.
            for (int i = 0; i < 3; i++)
                d = MathF.Max(d, -MathF.Max(rRoot - r, MathF.Abs(p.Z - gz[i]) - gh[i] / 2f));
            // Oil-drain holes from the oil-ring groove into the cavity.
            if (MathF.Abs(p.Z - gz[2]) < rDrain + 1f)
                foreach (Vector2 u in drains)
                {
                    Vector3 a = new(u.X * (rCav - 4f), u.Y * (rCav - 4f), gz[2]);
                    Vector3 b = new(u.X * (R - 1f), u.Y * (R - 1f), gz[2]);
                    d = MathF.Max(d, -Es.Cyl(p, a, b, rDrain));
                }
            // Pin bore and circlip grooves.
            d = MathF.Max(d, -Es.Cyl(q, new Vector3(-1f, 0f, zPin), new Vector3(R + 2f, 0f, zPin), rPin));
            d = MathF.Max(d, -Es.Cyl(q, new Vector3(xClip - wClip, 0f, zPin), new Vector3(xClip + wClip, 0f, zPin), rClip));
            // Cooling gallery and its two depowdering ports.
            float tor = Es.Len2(r - Rg, p.Z - zg) - rg;
            float port = Es.Cyl(q, new Vector3(xPort - lPort / 2f, 0f, zg), new Vector3(xPort + lPort / 2f, 0f, zg), rPort);
            return MathF.Max(d, -MathF.Min(tor, port));
        }

        Sdf.Stage(s.PartId, "piston field");
        return Sdf.Vox(lib, F, new Vector3(-R - 1.5f, -R - 1.5f, -H / 2f - 1.5f), new Vector3(R + 1.5f, R + 1.5f, H / 2f + 1.5f));
    }
}
