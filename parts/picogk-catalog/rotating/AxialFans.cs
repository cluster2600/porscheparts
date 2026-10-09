using System.Numerics;
using PicoGK;

namespace PicoGKCatalog;

static class FanRows
{
    /// Blade row from hub/mid/tip section parameters named <prefix>_<station>_<quantity>.
    public static AxialRow Row(PartSpec s, string pre, int n, float rRoot, float rTip, float zMid, float minHalf)
    {
        AxialRow row = new()
        {
            N = n, RRoot = rRoot, RTip = rTip, ZMid = zMid, MinHalf = minHalf,
            RHub = s.P($"{pre}_hub_radius_mm"), RMid = s.P($"{pre}_mid_radius_mm"), RTipSec = s.P($"{pre}_tip_radius_mm"),
        };
        string[] st = { "hub", "mid", "tip" };
        for (int i = 0; i < 3; i++)
        {
            row.Chord[i] = s.P($"{pre}_{st[i]}_chord_mm");
            row.Stagger[i] = s.P($"{pre}_{st[i]}_stagger_deg");
            row.Camber[i] = s.P($"{pre}_{st[i]}_camber_deg");
            row.Tmax[i] = s.P($"{pre}_{st[i]}_thickness_mm");
        }
        return row;
    }
}

/// Archived Carrera F0 fan: 12 twisted, cambered, swept airfoil blades between
/// a hub annulus and a peripheral ring, root and tip fillets by smooth union.
public sealed class RingAxialImpeller : IPartGenerator
{
    public string Name => "ring_axial_impeller";

    public Voxels Build(Library lib, PartSpec s)
    {
        float Ro = s.P("outer_diameter_mm") / 2f, depth = s.P("axial_depth_mm"), ring = s.P("outer_rim_thickness_mm");
        float rHub = s.P("hub_outer_diameter_mm") / 2f, rBore = s.P("hub_bore_diameter_mm") / 2f;
        float zMid = s.P("blade_z_mm") + s.P("blade_axial_height_mm") / 2f;
        float fil = s.P("root_fillet_mm");
        AxialRow row = FanRows.Row(s, "blade", s.N("blade_count"), rHub - 1.5f, Ro - ring + 1.0f, zMid, s.VoxelMm * 1.1f);
        row.TipSweep = RotKit.Rad(s.P("blade_sweep_deg"));
        row.Phase = 0f;

        float Field(Vector3 p)
        {
            float hub = RotKit.Annulus(p, rBore, rHub, 0f, depth, 2f);
            float rim = RotKit.Annulus(p, Ro - ring, Ro, 0f, depth, 1.2f);
            float b = row.Eval(p);
            float u = MathF.Min(RotKit.SMin(hub, b, fil), RotKit.SMin(rim, b, fil * 0.8f));
            float r = RotKit.R(p);
            return MathF.Max(u, MathF.Max(r - Ro, rBore - r));   // fillets never bulge through the ring or bore
        }

        Sdf.Stage(s.PartId, "impeller implicit");
        return Sdf.Vox(lib, Field, new Vector3(-Ro - 1, -Ro - 1, -1), new Vector3(Ro + 1, Ro + 1, depth + 1));
    }
}

/// Turbo rotor F1: alternator cup (wall, web with 12 windows, 3 bolt holes,
/// bore) carrying 11 twisted airfoil blades designed from velocity triangles;
/// no shroud. Blade roots filleted onto the cup by smooth union.
public sealed class CupAxialImpeller : IPartGenerator
{
    public string Name => "cup_axial_impeller";

    public Voxels Build(Library lib, PartSpec s)
    {
        float Ro = s.P("outer_diameter_mm") / 2f, depth = s.P("cup_depth_mm");
        float rc = s.P("cup_diameter_mm") / 2f, wall = s.P("cup_wall_mm"), web = s.P("web_thickness_mm");
        float rBore = s.P("bore_diameter_mm") / 2f;
        int nVent = s.N("vent_count");
        float rv = s.P("vent_radius_mm"), vRad = s.P("vent_radial_halfwidth_mm"), vTan = s.P("vent_tangential_halfwidth_mm");
        float vFil = s.P("vent_corner_radius_mm");
        int nBolt = s.N("bolt_count");
        float rbc = s.P("bolt_circle_radius_mm"), rbh = s.P("bolt_hole_radius_mm");
        float fil = s.P("root_fillet_mm");
        AxialRow row = FanRows.Row(s, "blade", s.N("blade_count"), rc - 1.5f, Ro, depth / 2f, s.VoxelMm * 1.1f);

        float Field(Vector3 p)
        {
            float r = RotKit.R(p), th = RotKit.Th(p);
            float wallF = RotKit.Annulus(p, rc - wall, rc, 0f, depth, 1.5f);
            float webF = RotKit.Annulus(p, rBore, rc - wall + 1f, 0f, web, 1.0f);
            float cup = RotKit.SMin(wallF, webF, 4f);
            // Windows in the web.
            float dv = RotKit.Near(th, 2f * RotKit.Pi / nVent);
            float wx = r * MathF.Cos(dv) - rv, wy = r * MathF.Sin(dv);
            float win = RotKit.Box2(wx, wy, -vRad, vRad, -vTan, vTan, vFil);
            // Bolt holes.
            float db = RotKit.Near(th + RotKit.Pi / nBolt, 2f * RotKit.Pi / nBolt);
            float bx = r * MathF.Cos(db) - rbc, by = r * MathF.Sin(db);
            float bolt = MathF.Sqrt(bx * bx + by * by) - rbh;
            cup = MathF.Max(cup, -MathF.Min(win, bolt));
            float blades = row.Eval(p);
            return RotKit.SMin(cup, blades, fil);
        }

        Sdf.Stage(s.PartId, "rotor implicit");
        return Sdf.Vox(lib, Field, new Vector3(-Ro - 1, -Ro - 1, -1), new Vector3(Ro + 1, Ro + 1, depth + 1));
    }
}

/// F1 guide-vane ring: 17 cambered vanes between an inner sleeve (with a
/// web flange to the alternator seat sleeve) and a thin outer ring; vane
/// roots and tips filleted by smooth union.
public sealed class FanStatorRing : IPartGenerator
{
    public string Name => "fan_stator_ring";

    public Voxels Build(Library lib, PartSpec s)
    {
        float L = s.P("ring_axial_length_mm"), rHub = s.P("hub_radius_mm"), rTip = s.P("tip_radius_mm");
        float tIn = s.P("inner_ring_thickness_mm"), web = s.P("inner_web_thickness_mm");
        float rSeat = s.P("inner_ring_bore_mm") / 2f, tSeat = s.P("seat_sleeve_thickness_mm");
        float Ro = s.P("outer_ring_outer_diameter_mm") / 2f;
        float fil = s.P("root_fillet_mm");
        AxialRow row = FanRows.Row(s, "vane", s.N("vane_count"), rHub - tIn / 2f, rTip + 0.8f, L / 2f, s.VoxelMm * 1.1f);

        float Field(Vector3 p)
        {
            float sleeve = RotKit.Annulus(p, rHub - tIn, rHub, 0f, L, 1.0f);
            float webF = RotKit.Annulus(p, rSeat, rHub - tIn + 0.8f, 0f, web, 0.8f);
            float seat = RotKit.Annulus(p, rSeat, rSeat + tSeat, 0f, L, 1.0f);
            float inner = RotKit.SMin(RotKit.SMin(sleeve, webF, 3f), seat, 3f);
            float outer = RotKit.Annulus(p, rTip, Ro, 0f, L, 0.6f);
            float v = row.Eval(p);
            float u = MathF.Min(RotKit.SMin(inner, v, fil), RotKit.SMin(outer, v, fil));
            float r = RotKit.R(p);
            return MathF.Max(u, MathF.Max(r - Ro, rSeat - r));   // fillets never bulge through the rings
        }

        Sdf.Stage(s.PartId, "stator implicit");
        return Sdf.Vox(lib, Field, new Vector3(-Ro - 1, -Ro - 1, -1), new Vector3(Ro + 1, Ro + 1, L + 1));
    }
}
