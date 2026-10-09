using System.Numerics;
using PicoGK;

namespace PicoGKCatalog;

/// Pair of K16 turbochargers (display concept). Each unit, axis X, inlet at
/// x = 0: compressor inlet tube with hose bead, cover, spiral volute with a
/// tangential discharge, backplate and clamp ring, centre housing with oil
/// feed boss and drain pad, heat shield, turbine volute with a flanged
/// tangential inlet, axial outlet with a three-ear flange, integral
/// wastegate boss and actuator can. Gas paths are hollow and open at the
/// inlets/outlets; simplified wheels sit in both bores. The two units are
/// mirror images about Y = 0, joined by a schematic compressor-discharge
/// crossover with a central riser (one display body).
public sealed class K16TurboPair : IPartGenerator
{
    public string Name => "k16_turbo_pair";

    /// Distance to a solid of revolution about X: x0..x1, radius r, rounded edges.
    static float RevX(Vector3 q, float x0, float x1, float r, float rr) =>
        RotKit.Box2(q.X, MathF.Sqrt(q.Y * q.Y + q.Z * q.Z), x0, x1, -r, r, rr);

    /// Spiral volute about X in the plane x = xs. Section centre radius and
    /// tube radius vary linearly with t in [0,1]; t = 0 at psi0, advancing
    /// with dir * psi.
    static float Scroll(Vector3 q, float xs, float psi0, float dir, float rc0, float rc1, float a0, float a1, float inset)
    {
        float rho = MathF.Sqrt(q.Y * q.Y + q.Z * q.Z);
        float psi = MathF.Atan2(q.Z, q.Y);
        float phi = dir * (psi - psi0);
        phi -= 2f * RotKit.Pi * MathF.Floor(phi / (2f * RotKit.Pi));
        float t = phi / (2f * RotKit.Pi);
        float rc = rc0 + (rc1 - rc0) * t, a = a0 + (a1 - a0) * t - inset;
        float dr = rho - rc, dx = q.X - xs;
        return MathF.Sqrt(dr * dr + dx * dx) - a;
    }

    public Voxels Build(Library lib, PartSpec s)
    {
        float L = s.P("unit_length_mm"), W = s.P("unit_width_mm"), H = s.P("unit_height_mm");
        float spacing = s.P("pair_spacing_mm"), wall = s.P("wall_mm");
        float rCs = W / 2f;                                   // compressor volute outer radius
        float rTs = s.P("turbine_volute_outer_radius_mm");
        float rIn = s.P("compressor_inlet_bore_diameter_mm") / 2f, rOut = s.P("turbine_outlet_bore_diameter_mm") / 2f;
        float rPipe = s.P("crossover_pipe_od_mm") / 2f;
        float zTop = H - W / 2f;                               // axis at z = 0, volute bottom at -W/2
        float zPipe = s.P("crossover_axis_height_mm");
        float half = spacing / 2f;

        // Compressor layout (local x from the inlet face).
        float xs = 88f, a1c = 32f, rc1c = rCs - a1c, a0c = 10f, rc0c = 50f;
        // Turbine layout.
        float xt = 212f, a1t = 27f, rc1t = rTs - a1t, a0t = 9f, rc0t = 45f;
        float zBot = -W / 2f;

        float Unit(Vector3 q)
        {
            // ---------------- solids
            float inlet = RevX(q, 0f, 56f, rIn + wall + 3f, 2f);
            float bead = RevX(q, 3f, 10f, rIn + wall + 6f, 2.5f);
            float rho = MathF.Sqrt(q.Y * q.Y + q.Z * q.Z);
            float coverR = (rIn + wall + 3f) + (62f - (rIn + wall + 3f)) * Math.Clamp((q.X - 50f) / 30f, 0f, 1f);
            float cover = MathF.Max((rho - coverR) * 0.8f, MathF.Abs(q.X - 81f) - 31f);
            float volC = Scroll(q, xs, RotKit.Pi, -1f, rc0c, rc1c, a0c, a1c, 0f);
            float back = RevX(q, 100f, 113f, 72f, 3f);
            float clamp = RevX(q, 104f, 110f, 76f, 2.5f);
            Vector3 d0 = new(xs, -rc1c, 0f), d1 = new(xs, -rc1c, zPipe), d2 = new(xs, -half - 12f, zPipe);
            float disV = RotKit.Cone(q, d0, d1, a1c, rPipe);
            float disH = RotKit.Rod(q, d1, d2, rPipe);
            Vector3 c0 = new(xs, -half, zPipe), c1 = new(xs, -half, zTop - 3f);
            float riser = RotKit.Rod(q, c0, c1, rPipe);
            float riserBead = RotKit.Rod(q, new Vector3(xs, -half, zTop - 10f), c1, rPipe + 3f);

            float comp = RotKit.SMin(inlet, bead, 2f);
            comp = RotKit.SMin(comp, cover, 4f);
            comp = RotKit.SMin(comp, volC, 5f);
            comp = RotKit.SMin(comp, back, 4f);
            comp = MathF.Min(comp, clamp);
            float pipe = RotKit.SMin(RotKit.SMin(disV, disH, 14f), MathF.Min(riser, riserBead), 10f);
            comp = RotKit.SMin(comp, pipe, 6f);

            // Centre housing.
            float chra = RotKit.Box2(q.X, rho, 112f, 182f, -44f, 44f, 5f);
            float oil = RotKit.Rod(q, new Vector3(146f, 0f, 30f), new Vector3(146f, 0f, 54f), 9f);
            float drain = Sdf.RoundBox(q, new Vector3(146f, 0f, -45f), new Vector3(14f, 14f, 9f), 3f);
            float shield = RevX(q, 180.5f, 184f, 80f, 1.4f);
            float core = RotKit.SMin(RotKit.SMin(chra, oil, 4f), drain, 4f);
            core = MathF.Min(core, shield);

            // Turbine housing.
            float tCore = RevX(q, 182.5f, 242f, 50f, 4f);
            float volT = Scroll(q, xt, 0f, 1f, rc1t, rc0t, a1t, a0t, 0f);
            Vector3 i0 = new(xt, rc1t, 0f), i1 = new(xt, rc1t, zBot + 10f);
            float tin = RotKit.Rod(q, i0, i1, a1t);
            float tfl = Sdf.RoundBox(q, new Vector3(xt, rc1t, zBot + 5f), new Vector3(33f, MathF.Min(33f, rCs - rc1t - 1f), 5f), 4f);
            float tout = RevX(q, 238f, 270f, rOut + wall + 6f, 2f);
            float tofl = RevX(q, 268f, L, rOut + wall + 18f, 2f);
            float ang = RotKit.Near(MathF.Atan2(q.Z, q.Y) - RotKit.Pi / 2f, 2f * RotKit.Pi / 3f);
            float ex = rho * MathF.Cos(ang) - (rOut + wall + 20f), ey = rho * MathF.Sin(ang);
            float ear = MathF.Max(MathF.Sqrt(ex * ex + ey * ey) - 9f, MathF.Abs(q.X - (L - 6f)) - 6f);
            float wg = RotKit.Rod(q, new Vector3(226f, 0f, 30f), new Vector3(226f, 0f, 66f), 13f);
            float strut = RotKit.Rod(q, new Vector3(229f, 0f, 60f), new Vector3(229f, 0f, zTop - 25f), 7f);
            float rCan = MathF.Sqrt((q.X - 232f) * (q.X - 232f) + q.Y * q.Y);
            float can = RotKit.Box2(rCan, q.Z, -30f, 30f, zTop - 27f, zTop, 6f);
            float rod = Sdf.Capsule(q, new Vector3(250f, 0f, zTop - 27f), new Vector3(250f, 0f, 62f), 2.5f);
            float lever = Sdf.Capsule(q, new Vector3(250f, 0f, 62f), new Vector3(226f, 0f, 62f), 3.5f);

            float turb = RotKit.SMin(tCore, volT, 5f);
            turb = RotKit.SMin(turb, tin, 8f);
            turb = RotKit.SMin(turb, tfl, 3f);
            turb = RotKit.SMin(turb, tout, 4f);
            turb = RotKit.SMin(turb, MathF.Min(tofl, ear), 3f);
            turb = RotKit.SMin(turb, wg, 4f);
            turb = RotKit.SMin(turb, strut, 4f);
            turb = RotKit.SMin(turb, can, 5f);
            turb = MathF.Min(turb, MathF.Min(rod, lever));

            float solid = MathF.Min(MathF.Min(comp, core), turb);

            // ---------------- gas paths (each inside its own solid, open at the ends)
            float g = RevX(q, -5f, 96f, rIn, 1f);
            g = MathF.Min(g, RevX(q, 85f, 91f, 56f, 1f));
            g = MathF.Min(g, Scroll(q, xs, RotKit.Pi, -1f, rc0c, rc1c, a0c, a1c, wall));
            g = MathF.Min(g, RotKit.SMin(RotKit.Cone(q, d0, d1, a1c - wall, rPipe - wall),
                                        RotKit.Rod(q, d1, d2, rPipe - wall), 14f));
            g = MathF.Min(g, RotKit.Rod(q, c0, c1 + new Vector3(0f, 0f, 10f), rPipe - wall));
            g = MathF.Min(g, RotKit.Rod(q, i0, i1 - new Vector3(0f, 0f, 20f), a1t - wall - 3f));
            g = MathF.Min(g, Scroll(q, xt, 0f, 1f, rc1t, rc0t, a1t, a0t, wall));
            g = MathF.Min(g, RevX(q, 209f, 215f, 47f, 1f));
            g = MathF.Min(g, RevX(q, 192f, 236f, 30f, 2f));
            g = MathF.Min(g, RevX(q, 230f, L + 10f, rOut, 1f));
            float body = MathF.Max(solid, -g);

            // Blind holes: oil feed, oil drain; flange bolt holes.
            float holes = RotKit.Rod(q, new Vector3(146f, 0f, 40f), new Vector3(146f, 0f, 60f), 3f);
            holes = MathF.Min(holes, RotKit.Rod(q, new Vector3(146f, 0f, -60f), new Vector3(146f, 0f, -42f), 7f));
            float hy = MathF.Abs(q.Y - rc1t) - 22f, hx = MathF.Abs(q.X - xt) - 22f;
            holes = MathF.Min(holes, MathF.Max(MathF.Sqrt(hx * hx + hy * hy) - 4.5f, q.Z - (zBot + 12f)));
            holes = MathF.Min(holes, MathF.Max(MathF.Sqrt(ex * ex + ey * ey) - 4f, MathF.Abs(q.X - (L - 6f)) - 7f));
            body = MathF.Max(body, -holes);

            // ---------------- simplified wheels in the bores
            float wc = Wheel(q, 98f, 64f, 1f, 6, rIn - 2.5f, 22f, 5f);
            float wt = Wheel(q, 190f, 234f, -1f, 9, 27f, 22f, 5f);
            return MathF.Min(body, MathF.Min(wc, wt));
        }

        float Field(Vector3 p)
        {
            Vector3 q = new(p.X + L / 2f, MathF.Abs(p.Y) - half, p.Z);
            return Unit(q);
        }

        Sdf.Stage(s.PartId, "turbo pair implicit");
        float x0 = -L / 2f - 2f, x1 = L / 2f + 2f;
        Voxels right = Sdf.Vox(lib, Field, new Vector3(x0, half - rCs - 25f, zBot - 2f), new Vector3(x1, half + rCs + 2f, zTop + 2f));
        Voxels left = Sdf.Vox(lib, Field, new Vector3(x0, -half - rCs - 2f, zBot - 2f), new Vector3(x1, -half + rCs + 25f, zTop + 2f));
        float xm = xs - L / 2f;
        Voxels mid = Sdf.Vox(lib, Field, new Vector3(xm - rPipe - 20f, -half + rCs + 15f, zPipe - rPipe - 20f),
                                         new Vector3(xm + rPipe + 20f, half - rCs - 15f, zTop + 2f));
        right.BoolAdd(left);
        right.BoolAdd(mid);
        return right;
    }

    /// Simplified radial wheel on the X axis: hub cone from xBack (radius rh0)
    /// to xNose (radius rh1), n twisted plate blades up to rTip.
    static float Wheel(Vector3 q, float xBack, float xNose, float sgn, int n, float rTip, float rh0, float rh1)
    {
        float lo = MathF.Min(xBack, xNose), hi = MathF.Max(xBack, xNose);
        if (q.X < lo - 2f || q.X > hi + 2f) return 10f;
        float rho = MathF.Sqrt(q.Y * q.Y + q.Z * q.Z);
        if (rho > rTip + 3f) return rho - rTip;
        float u = Math.Clamp((q.X - xBack) / (xNose - xBack), 0f, 1f);
        float rh = rh0 + (rh1 - rh0) * MathF.Sqrt(u);
        float hub = MathF.Max((rho - rh) * 0.7f, MathF.Abs(q.X - (lo + hi) / 2f) - (hi - lo) / 2f);
        float psi = MathF.Atan2(q.Z, q.Y) - sgn * 1.1f * u * u;
        float d = RotKit.Near(psi, 2f * RotKit.Pi / n);
        float blade = rho * MathF.Abs(d) / MathF.Sqrt(1f + 4f * u * u) - 1.4f;
        float tipR = rTip - (rTip - rh1 - 4f) * MathF.Max(0f, u - 0.6f) / 0.4f;
        blade = MathF.Max(blade, MathF.Max(rho - tipR, MathF.Abs(q.X - (lo + hi) / 2f) - (hi - lo) / 2f));
        return RotKit.SMin(hub, blade, 1.5f);
    }
}
