using System.Numerics;
using PicoGK;

namespace PicoGKCatalog;

/// 993 dashboard trim (cars without passenger airbag). X across the car,
/// Y fore-aft (-Y toward the occupants), Z up, bottom at z = 0. A crowned
/// profile (windscreen-side flange, parabolic top, crest, elliptical roll
/// into the occupant face) is swept across the car with a forward plan bow
/// and a tuck-down at the pillar ends, smoothed, then shelled. The bottom is
/// opened between two return flanges; an instrument opening with a hanging
/// return flange, louvred face vents and transverse ribs complete it.
public sealed class DashboardTrim : IPartGenerator
{
    public string Name => "dashboard_trim_panel";

    public Voxels Build(Library lib, PartSpec s)
    {
        float L = s.P("length_mm"), Dp = s.P("depth_mm"), H = s.P("height_mm"), wall = s.P("wall_mm");
        float rearH = s.P("rear_height_mm"), crest = s.P("crest_offset_mm"), bow = s.P("plan_bow_mm");
        float taper = s.P("end_taper_ratio"), tStart = s.P("end_taper_start_ratio"), endR = s.P("end_round_mm");
        float smooth = s.P("edge_smooth_mm"), lip = s.P("front_lip_mm");
        float xi = s.P("instrument_opening_x_mm"), li = s.P("instrument_opening_length_mm"), wi = s.P("instrument_opening_width_mm");
        float flD = s.P("opening_flange_depth_mm");
        float cvx = s.P("centre_vent_x_mm"), cvw = s.P("centre_vent_width_mm"), cvh = s.P("centre_vent_height_mm"), vz = s.P("vent_z_mm");
        float svx = s.P("side_vent_x_mm"), svr = s.P("side_vent_diameter_mm") / 2f;
        float vt = s.P("vane_thickness_mm"), vp = s.P("vane_pitch_mm"), vd = s.P("vane_depth_mm");
        float rp = s.P("rib_pitch_mm"), rt = s.P("rib_thickness_mm"), rcl = s.P("rib_clearance_mm");

        float half = (Dp - bow) / 2f, yR = half, yF = -half;
        // closed profile in (u = y, v = z)
        var poly = new List<Vector2> { new(yR, 0f), new(yR, rearH) };
        for (int i = 1; i <= 40; i++)
        {
            float u = yR + (crest - yR) * i / 40f;
            float k = (u - crest) / (yR - crest);
            poly.Add(new Vector2(u, H - (H - rearH) * k * k));
        }
        for (int i = 1; i <= 40; i++)
        {
            float th = MathF.PI / 2f + MathF.PI / 2f * i / 40f;
            poly.Add(new Vector2(crest + (crest - yF) * MathF.Cos(th), H * MathF.Sin(th)));
        }
        var prof = new Raster2D(poly, yF - 12f, -12f, yR + 12f, H + 12f, 0.25f);

        float Yoff(float x) { float u = 2f * x / L; return -bow * (1f - u * u); }
        float E(float x) => BodyKit.Smooth((MathF.Abs(x) - tStart * L) / (0.5f * L - tStart * L));
        float Sz(float x) => 1f - taper * E(x);
        float Sy(float x) => 1f - 0.5f * taper * E(x);
        float U(Vector3 p) => (p.Y - Yoff(p.X)) / Sy(p.X);

        float Solid(Vector3 p)
        {
            float sy = Sy(p.X), sz = Sz(p.X);
            float d = prof[U(p), p.Z / sz] * MathF.Min(sy, sz);
            return BodyKit.RoundI(d, MathF.Abs(p.X) - L / 2f, endR);
        }

        Vector3 lo = new(-L / 2f - 2f, yF - bow - 2f, -2f), hi = new(L / 2f + 2f, yR + 2f, H + 2f);
        Sdf.Stage(s.PartId, "solid");
        Voxels v = Sdf.Vox(lib, Solid, lo, hi);
        v.Smoothen(smooth);
        Sdf.Stage(s.PartId, "shell");
        Voxels inner = v.voxOffset(-wall);
        Voxels shell = v.voxBoolSubtract(inner);

        // transverse ribs inside, stopping above the open bottom
        Voxels ribs = Sdf.Vox(lib, p =>
        {
            float k = MathF.Round(p.X / rp);
            if (MathF.Abs(k * rp) > L / 2f - 60f) k = MathF.Sign(k) * MathF.Floor((L / 2f - 60f) / rp);
            return MathF.Max(MathF.Abs(p.X - k * rp) - rt / 2f, rcl - p.Z);
        }, lo, hi);
        ribs.BoolIntersect(v);
        shell.BoolAdd(ribs);

        // instrument opening: stadium in plan around the crest line
        float yi = crest + Yoff(xi);
        float Stadium(Vector3 p)
        {
            float dx = MathF.Max(MathF.Abs(p.X - xi) - (li - wi) / 2f, 0f);
            return new Vector2(dx, p.Y - yi).Length() - wi / 2f;
        }
        Vector3 ilo = new(xi - li / 2f - 8f, yi - wi / 2f - 8f, 10f), ihi = new(xi + li / 2f + 8f, yi + wi / 2f + 8f, H + 2f);
        Voxels flange = Sdf.Vox(lib, p => MathF.Max(-Stadium(p), Stadium(p) - wall), ilo, ihi);
        flange.BoolIntersect(v);
        flange.BoolSubtract(v.voxOffset(-flD));
        shell.BoolAdd(flange);
        shell.BoolSubtract(Sdf.Vox(lib, p => MathF.Max(Stadium(p), 20f - p.Z), ilo, ihi));

        // face vents: two centre slots and two round side vents, cut through the occupant face only
        float FaceCut(Vector3 p) => U(p) - (crest - 0.55f * (crest - yF));
        float Vents(Vector3 p)
        {
            float d = float.MaxValue;
            for (int sg = -1; sg <= 1; sg += 2)
            {
                float zc = vz * Sz(sg * cvx);
                d = MathF.Min(d, BodyKit.RoundRect(p.X - sg * cvx, p.Z - zc, cvw / 2f, cvh / 2f, 4f));
                float zs = vz * Sz(sg * svx);
                d = MathF.Min(d, new Vector2(p.X - sg * svx, p.Z - zs).Length() - svr);
            }
            return d;
        }
        Vector3 vlo = new(-L / 2f, yF - bow - 2f, 0f), vhi = new(L / 2f, yF + 40f, H);
        Voxels ventCut = Sdf.Vox(lib, p => MathF.Max(Vents(p), FaceCut(p)), vlo, vhi);
        shell.BoolSubtract(ventCut);
        Voxels vanes = Sdf.Vox(lib, p =>
        {
            float zc = vz * Sz(p.X);
            float k = MathF.Round((p.Z - zc) / vp);
            float slab = MathF.Abs(p.Z - zc - k * vp) - vt / 2f;
            return MathF.Max(MathF.Max(slab, Vents(p) - 1.5f), FaceCut(p));
        }, vlo, vhi);
        vanes.BoolIntersect(v);
        vanes.BoolSubtract(v.voxOffset(-vd));
        shell.BoolAdd(vanes);

        // open the bottom between the occupant-side lip and the windscreen-side flange
        Sdf.Stage(s.PartId, "open bottom");
        shell.BoolSubtract(Sdf.Vox(lib, p =>
        {
            float u = U(p);
            float du = MathF.Max(yF + lip - u, u - (yR - wall));
            return MathF.Max(MathF.Max(du, p.Z - (wall + 1.5f)), MathF.Abs(p.X) - (L / 2f - endR));
        }, new Vector3(-L / 2f, yF - bow - 2f, -2f), new Vector3(L / 2f, yR + 2f, wall + 3f)));
        return shell;
    }
}
