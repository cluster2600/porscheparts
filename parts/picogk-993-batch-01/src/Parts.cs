using System.Numerics;
using PicoGK;

namespace PicoGK993Batch;

/// One generator per part family. Every dimension comes from the PartSpec;
/// nothing is hard-coded here except construction tolerances (bbox margins).
public static class Parts
{
    public static Voxels Build(Library lib, PartSpec s) => s.Generator switch
    {
        "oval_exhaust_tip" => OvalExhaustTip(lib, s),
        "wheel_center_cap" => WheelCenterCap(lib, s),
        "turbo_heat_shield" => TurboHeatShield(lib, s),
        "intercooler_bracket" => IntercoolerBracket(lib, s),
        "intercooler_air_duct" => IntercoolerAirDuct(lib, s),
        "door_opener_lever" => DoorOpenerLever(lib, s),
        "gear_shift_knob" => GearShiftKnob(lib, s),
        "headlamp_spring_hook" => HeadlampSpringHook(lib, s),
        "intake_velocity_stack" => IntakeVelocityStack(lib, s),
        "switch_blank" => SwitchBlank(lib, s),
        _ => throw new NotSupportedException($"unknown generator '{s.Generator}'"),
    };

    static float Smooth(float t) { t = Math.Clamp(t, 0f, 1f); return t * t * (3f - 2f * t); }

    // ---------------------------------------------------------------- 1
    /// Round-to-oval tip, axis Z, inlet at z = 0. Double wall: inner flow
    /// shell + outer cosmetic shell, ventilated gap open at the inlet end
    /// (also the depowdering path), closed by a solid lip at the outlet,
    /// tied by radial ribs. The slip collar is a straight section.
    static Voxels OvalExhaustTip(Library lib, PartSpec s)
    {
        float L = s.P("length_mm"), slip = s.P("slip_depth_mm");
        float rIn = s.P("inlet_pipe_od_mm") / 2f + s.P("slip_clearance_mm");
        float W = s.P("outlet_width_mm") / 2f, H = s.P("outlet_height_mm") / 2f;
        float wo = s.P("outer_wall_mm"), wi = s.P("inner_wall_mm"), gap = s.P("gap_mm");
        float lip = s.P("outlet_lip_mm");
        int ribs = s.N("rib_count");
        float ribT = s.P("rib_thickness_mm");

        // Bore semi-axes along z: constant through the collar, blended to the outlet.
        float aOut = W - wo - gap - wi, bOut = H - wo - gap - wi;
        (float, float) Bore(float z)
        {
            float t = Smooth((z - slip) / (L - slip));
            return (rIn + (aOut - rIn) * t, rIn + (bOut - rIn) * t);
        }
        Func<float, (float, float)> Off(float d) => z => { var (a, b) = Bore(z); return (a + d, b + d); };

        Vector3 lo = new(-W - 2, -H - 2, -1), hi = new(W + 2, H + 2, L + 1);
        Voxels outer = Sdf.Vox(lib, p => Sdf.EllipseLoftZ(p, Off(wi + gap + wo), 0, L), lo, hi);
        Voxels bore = Sdf.Vox(lib, p => Sdf.EllipseLoftZ(p, Bore, -1, L + 1), lo, hi);
        Voxels gapV = Sdf.Vox(lib, p => Sdf.EllipseLoftZ(p, Off(wi + gap), -1, L - lip), lo, hi);
        gapV.BoolSubtract(Sdf.Vox(lib, p => Sdf.EllipseLoftZ(p, Off(wi), -2, L), lo, hi));

        Voxels ribV = Sdf.Vox(lib, p =>
        {
            float best = float.MaxValue;
            for (int i = 0; i < ribs; i++)
            {
                float a = (i + 0.5f) * 2f * MathF.PI / ribs;
                Vector2 dir = new(MathF.Cos(a), MathF.Sin(a)), n = new(-dir.Y, dir.X);
                Vector2 q = new(p.X, p.Y);
                float plane = MathF.Abs(Vector2.Dot(q, n)) - ribT / 2f;
                best = MathF.Min(best, MathF.Max(plane, -Vector2.Dot(q, dir)));
            }
            return best;
        }, lo, hi);
        gapV.BoolSubtract(ribV);

        outer.BoolSubtract(bore);
        outer.BoolSubtract(gapV);
        return outer;
    }

    // ---------------------------------------------------------------- 2
    /// Domed face with a strut-lattice sandwich core, cylindrical skirt, clip tabs
    /// with outward barbs at the open end (z = 0).
    static Voxels WheelCenterCap(Library lib, PartSpec s)
    {
        float R = s.P("face_diameter_mm") / 2f, Hh = s.P("overall_height_mm");
        float rs = s.P("skirt_outer_diameter_mm") / 2f, sw = s.P("skirt_wall_mm");
        float ft = s.P("face_thickness_mm"), dome = s.P("dome_height_mm");
        int tabs = s.N("tab_count");
        float tabW = s.P("tab_width_mm"), tabL = s.P("tab_length_mm"), barb = s.P("tab_barb_mm");
        float skin = s.P("skin_mm"), cell = s.P("lattice_cell_mm"), gw = s.P("strut_diameter_mm");

        float zFace = Hh - dome - ft;                       // underside of the face
        float Rs = (R * R + dome * dome) / (2f * dome);     // dome sphere radius
        Vector3 cDome = new(0, 0, Hh - Rs);
        Vector3 lo = new(-R - 2, -R - 2, -1), hi = new(R + 2, R + 2, Hh + 1);

        Sdf.Stage(s.PartId, "face");
        Voxels face = Sdf.Vox(lib, p => MathF.Max(Sdf.CylZ(p, 0, 0, R, zFace, Hh), Sdf.Sphere(p, cDome, Rs)), lo, hi);
        Sdf.Stage(s.PartId, "face fillet");
        face.Fillet(1.0f);
        Sdf.Stage(s.PartId, "face core");
        Voxels faceSolid = face.voxDuplicate();
        Voxels core = Sdf.LatticeCore(lib, faceSolid, skin, cell, gw);
        face.BoolSubtract(faceSolid.voxOffset(-skin));
        face.BoolAdd(core);

        Sdf.Stage(s.PartId, "skirt and tabs");
        float zTab = tabL;
        Voxels skirt = Sdf.Vox(lib, p => MathF.Max(Sdf.CylZ(p, 0, 0, rs, zTab, zFace + 0.5f), -Sdf.CylZ(p, 0, 0, rs - sw, -1, Hh)), lo, hi);
        float Sector(Vector3 p)
        {
            float best = float.MaxValue;
            for (int i = 0; i < tabs; i++)
            {
                float a = i * 2f * MathF.PI / tabs;
                Vector2 dir = new(MathF.Cos(a), MathF.Sin(a)), n = new(-dir.Y, dir.X);
                Vector2 q = new(p.X, p.Y);
                best = MathF.Min(best, MathF.Max(MathF.Abs(Vector2.Dot(q, n)) - tabW / 2f, -Vector2.Dot(q, dir)));
            }
            return best;
        }
        Voxels tabsV = Sdf.Vox(lib, p => MathF.Max(MathF.Max(Sdf.CylZ(p, 0, 0, rs, 0, zTab + 0.5f), -Sdf.CylZ(p, 0, 0, rs - sw, -1, Hh)), Sector(p)), lo, hi);
        Voxels barbs = Sdf.Vox(lib, p => MathF.Max(MathF.Max(Sdf.CylZ(p, 0, 0, rs + barb, 0.5f, 0.5f + 2f * barb), -Sdf.CylZ(p, 0, 0, rs - sw, -1, Hh)), Sector(p)), lo, hi);

        float drainD = s.P("drain_hole_diameter_mm");
        for (int i = 0; i < 4; i++)
        {
            float a = (i + 0.5f) * MathF.PI / 2f, x = 0.5f * (rs - sw) * MathF.Cos(a), y = 0.5f * (rs - sw) * MathF.Sin(a);
            face.BoolSubtract(Sdf.Vox(lib, p => Sdf.CylZ(p, x, y, drainD / 2f, zFace - 1f, zFace + skin + 1.0f), lo, hi));
        }
        face.BoolAdd(skirt);
        face.BoolAdd(tabsV);
        face.BoolAdd(barbs);
        return face;
    }

    // ---------------------------------------------------------------- 3
    /// Open half-superellipsoid cover (open side down, z = 0), double skin
    /// with a strut-lattice core between, mounting bosses on the rim.
    static Voxels TurboHeatShield(Library lib, PartSpec s)
    {
        float L = s.P("length_mm") / 2f, W = s.P("width_mm") / 2f, Hh = s.P("height_mm");
        float wo = s.P("outer_skin_mm"), wi = s.P("inner_skin_mm"), gap = s.P("core_gap_mm");
        float n = s.P("superellipse_exponent");
        float cell = s.P("lattice_cell_mm"), gw = s.P("strut_diameter_mm");
        int bosses = s.N("boss_count");
        float bossD = s.P("boss_diameter_mm"), holeD = s.P("hole_diameter_mm"), bossH = s.P("boss_height_mm");
        float T = wo + gap + wi;

        Vector3 lo = new(-L - bossD, -W - bossD, -1), hi = new(L + bossD, W + bossD, Hh + 1);
        Func<Vector3, float> dome = p => MathF.Max(Sdf.SuperEllipsoid(p, Vector3.Zero, new(L, W, Hh), n), -p.Z);
        Voxels outer = Sdf.Vox(lib, dome, lo, hi);
        Voxels shell = outer.voxDuplicate();
        shell.BoolSubtract(Sdf.Vox(lib, p => MathF.Max(Sdf.SuperEllipsoid(p, Vector3.Zero, new(L - T, W - T, Hh - T), n), -p.Z - 2f), lo, hi));
        Voxels coreRegion = Sdf.Vox(lib, p => MathF.Max(Sdf.SuperEllipsoid(p, Vector3.Zero, new(L - wo, W - wo, Hh - wo), n), -p.Z - 1f), lo, hi);
        coreRegion.BoolSubtract(Sdf.Vox(lib, p => Sdf.SuperEllipsoid(p, Vector3.Zero, new(L - wo - gap, W - wo - gap, Hh - wo - gap), n), lo, hi));
        Voxels core = Sdf.LatticeIn(lib, coreRegion, cell, gw);
        shell.BoolSubtract(coreRegion);
        shell.BoolAdd(core);

        for (int i = 0; i < bosses; i++)
        {
            float a = (i + 0.5f) * 2f * MathF.PI / bosses;
            // point on the base superellipse, pulled inward so the boss stays inside the published envelope
            float ca = MathF.Cos(a), sa = MathF.Sin(a);
            float k = MathF.Pow(MathF.Pow(MathF.Abs(ca), n) + MathF.Pow(MathF.Abs(sa), n), -1f / n);
            Vector2 c = new(ca * k * (L - T / 2f), sa * k * (W - T / 2f));
            Vector2 dir = Vector2.Normalize(c);
            c -= dir * (bossD / 2f);
            Voxels boss = Sdf.Vox(lib, p => Sdf.CylZ(p, c.X, c.Y, bossD / 2f, 0, bossH), lo, hi);
            boss.BoolAdd(Sdf.Vox(lib, p => Sdf.Capsule(p, new(c.X, c.Y, bossH / 2f), new(c.X + dir.X * bossD * 0.4f, c.Y + dir.Y * bossD * 0.4f, bossH / 2f), bossH / 2f), lo, hi));
            boss.BoolSubtract(Sdf.Vox(lib, p => Sdf.CylZ(p, c.X, c.Y, holeD / 2f, -1, bossH + 1), lo, hi));
            shell.BoolAdd(boss);
            shell.BoolSubtract(Sdf.Vox(lib, p => Sdf.CylZ(p, c.X, c.Y, holeD / 2f, -1, bossH + 1), lo, hi));
        }
        shell.Trim(new BBox3(new Vector3(lo.X, lo.Y, 0), hi));
        return shell;
    }

    // ---------------------------------------------------------------- 4
    /// Two rails along X joined by cross webs; rails are lattice-cored with
    /// a solid skin, the bolt pads stay fully solid.
    static Voxels IntercoolerBracket(Library lib, PartSpec s)
    {
        float L = s.P("length_mm") / 2f, W = s.P("width_mm") / 2f, Hh = s.P("height_mm");
        float rw = s.P("rail_width_mm");
        int webs = s.N("web_count");
        float webT = s.P("web_thickness_mm"), webH = s.P("web_height_mm");
        float holeD = s.P("hole_diameter_mm"), padL = s.P("pad_length_mm"), holeInset = s.P("hole_inset_mm");
        float skin = s.P("skin_mm"), cell = s.P("lattice_cell_mm"), gw = s.P("strut_diameter_mm");
        Vector3 lo = new(-L - 2, -W - 2, -1), hi = new(L + 2, W + 2, Hh + 1);
        float yr = W - rw / 2f;

        Func<Vector3, float> rails = p => MathF.Min(
            Sdf.RoundBox(p, new(0, yr, Hh / 2f), new(L, rw / 2f, Hh / 2f), 2f),
            Sdf.RoundBox(p, new(0, -yr, Hh / 2f), new(L, rw / 2f, Hh / 2f), 2f));
        Voxels railV = Sdf.Vox(lib, rails, lo, hi);
        Voxels pads = Sdf.Vox(lib, p => MathF.Max(rails(p), MathF.Abs(p.X) <= L - padL ? 1f : -1f), lo, hi);
        Voxels coreRegion = railV.voxDuplicate();
        coreRegion.BoolSubtract(pads);
        Voxels core = Sdf.LatticeCore(lib, coreRegion, skin, cell, gw);
        Voxels solid = railV.voxDuplicate();
        solid.BoolSubtract(coreRegion.voxOffset(-skin));
        solid.BoolAdd(core);

        for (int i = 0; i < webs; i++)
        {
            float x = -L + padL + (i + 0.5f) * (2f * (L - padL)) / webs;
            // Webs stop inside the rail skins so they never split a rail core
            // into sealed (undrainable) segments.
            float webHalfY = yr - rw / 2f + skin * 0.75f;
            solid.BoolAdd(Sdf.Vox(lib, p => Sdf.RoundBox(p, new(x, 0, webH / 2f), new(webT / 2f, webHalfY, webH / 2f), 1f), lo, hi));
        }
        foreach (float sx in new[] { -1f, 1f })
            foreach (float sy in new[] { -1f, 1f })
            {
                float hx = sx * (L - holeInset), hy = sy * yr;
                solid.BoolSubtract(Sdf.Vox(lib, p => Sdf.CylZ(p, hx, hy, holeD / 2f, -1, Hh + 1), lo, hi));
            }
        solid.Fillet(1.0f);
        float drainD = s.P("drain_hole_diameter_mm");
        foreach (float sx in new[] { -1f, 1f })
            foreach (float sy in new[] { -1f, 1f })
            {
                float dx = sx * (L - padL - 8f), dy = sy * yr;
                solid.BoolSubtract(Sdf.Vox(lib, p => Sdf.CylZ(p, dx, dy, drainD / 2f, -1, skin + 1.5f), lo, hi));
            }
        return solid;
    }

    // ---------------------------------------------------------------- 5
    /// Flat trapezoidal duct: wide inlet (y = -D/2) narrowing to the outlet
    /// (y = +D/2), thin walls, internal straight guide vanes splaying with
    /// the walls so each channel keeps its share of the flow area.
    static Voxels IntercoolerAirDuct(Library lib, PartSpec s)
    {
        float Li = s.P("inlet_width_mm") / 2f, Lo = s.P("outlet_width_mm") / 2f;
        float D = s.P("depth_mm") / 2f, Hh = s.P("height_mm"), t = s.P("wall_mm");
        int vanes = s.N("vane_count");
        float vt = s.P("vane_thickness_mm");
        float HalfW(float y) => Li + (Lo - Li) * Smooth((y + D) / (2f * D));
        Vector3 lo = new(-Li - t - 2, -D - 2, -1), hi = new(Li + t + 2, D + 2, Hh + 1);

        Func<Vector3, float> inner = p => MathF.Max(MathF.Max(MathF.Abs(p.X) - HalfW(p.Y) + t, MathF.Abs(p.Z - Hh / 2f) - (Hh / 2f - t)), MathF.Abs(p.Y) - D - 1f);
        Voxels duct = Sdf.Vox(lib, p => MathF.Max(MathF.Max(MathF.Abs(p.X) - HalfW(p.Y), MathF.Abs(p.Z - Hh / 2f) - Hh / 2f), MathF.Abs(p.Y) - D), lo, hi);
        Voxels cavity = Sdf.Vox(lib, inner, lo, hi);
        Voxels vaneV = Sdf.Vox(lib, p =>
        {
            float best = float.MaxValue, hw = HalfW(p.Y) - t;
            for (int i = 1; i <= vanes; i++)
            {
                float f = -1f + 2f * i / (vanes + 1);
                best = MathF.Min(best, MathF.Abs(p.X - f * hw) - vt / 2f);
            }
            return MathF.Max(best, MathF.Abs(p.Y) - D + 15f);
        }, lo, hi);
        cavity.BoolSubtract(vaneV);
        duct.BoolSubtract(cavity);
        return duct;
    }

    // ---------------------------------------------------------------- 6
    /// Curved lever: pivot boss with bore at the origin, arm swept along a
    /// quadratic Bezier to a grip paddle; arm and paddle lattice-cored.
    static Voxels DoorOpenerLever(Library lib, PartSpec s)
    {
        float Lt = s.P("length_mm"), Wt = s.P("width_mm"), Ht = s.P("height_mm");
        float bossD = s.P("pivot_boss_diameter_mm"), pinD = s.P("pivot_pin_diameter_mm");
        float armR = s.P("arm_radius_mm");
        float padW = s.P("paddle_width_mm"), padT = s.P("paddle_thickness_mm"), padL = s.P("paddle_length_mm");
        float skin = s.P("skin_mm"), cell = s.P("lattice_cell_mm"), gw = s.P("strut_diameter_mm");
        float rb = bossD / 2f;
        Vector3 a = new(0, 0, Ht / 2f), c = new(Lt - rb - padL, Wt - rb - padW / 2f, Ht / 2f);
        // Control point level with the paddle: the arm ends tangent to X, so the
        // paddle stays inside the published length x width envelope.
        Vector3 b = new(a.X + 0.55f * (c.X - a.X), c.Y, Ht / 2f);
        Vector3 lo = new(-rb - 2, -rb - 2, -1), hi = new(Lt, Wt, Ht + 1);

        Func<Vector3, float> arm = p =>
        {
            float best = float.MaxValue;
            const int seg = 24;
            Vector3 prev = a;
            for (int i = 1; i <= seg; i++)
            {
                Vector3 cur = Sdf.Bezier(a, b, c, i / (float)seg);
                Vector3 q = new(p.X, p.Y, a.Z + (p.Z - a.Z) * 1.6f);   // flattened section
                best = MathF.Min(best, Sdf.Capsule(q, prev, cur, armR));
                prev = cur;
            }
            return best;
        };
        Vector3 tan = Vector3.Normalize(c - b);
        Vector3 pc = c + tan * (padL / 2f);
        Func<Vector3, float> paddle = p =>
        {
            Vector3 q = p - pc;
            Vector2 u = new(tan.X, tan.Y), v = new(-tan.Y, tan.X);
            Vector3 local = new(Vector2.Dot(new(q.X, q.Y), u), Vector2.Dot(new(q.X, q.Y), v), q.Z);
            return Sdf.RoundBox(local, Vector3.Zero, new(padL / 2f, padW / 2f, padT / 2f), MathF.Min(padT / 2f - 0.1f, 4f));
        };
        Sdf.Stage(s.PartId, "arm");
        Voxels body = Sdf.Vox(lib, p => MathF.Min(arm(p), paddle(p)), lo, hi);
        Voxels boss = Sdf.Vox(lib, p => Sdf.CylZ(p, 0, 0, rb, 0, Ht), lo, hi);
        body.BoolAdd(boss);
        // Fillet the outer shape first: filleting after hollowing would round
        // the lattice voids shut.
        Sdf.Stage(s.PartId, "fillet");
        body.Fillet(1.5f);
        Sdf.Stage(s.PartId, "core");
        Voxels coreRegion = body.voxOffset(-skin);
        coreRegion.BoolSubtract(boss.voxOffset(skin));
        Voxels core = Sdf.LatticeIn(lib, coreRegion, cell, gw);
        body.BoolSubtract(coreRegion);
        body.BoolAdd(core);
        float drainD = s.P("drain_hole_diameter_mm");
        Vector3 dTip = pc + tan * (padL / 2f - 6f);
        body.BoolSubtract(Sdf.Vox(lib, p => Sdf.CylZ(p, dTip.X, dTip.Y, drainD / 2f, -1, Ht / 2f), lo, hi));
        Sdf.Stage(s.PartId, "bore");
        body.BoolSubtract(Sdf.Vox(lib, p => Sdf.CylZ(p, 0, 0, pinD / 2f, -1, Ht + 1), lo, hi));
        return body;
    }

    // ---------------------------------------------------------------- 7
    /// Ovoid knob on a neck, blind bore from below for the lever; outer skin
    /// with a strut-lattice core whose wall sets the knob mass.
    static Voxels GearShiftKnob(Library lib, PartSpec s)
    {
        float Dk = s.P("knob_diameter_mm") / 2f, Hk = s.P("knob_height_mm");
        float neckD = s.P("neck_diameter_mm") / 2f, neckH = s.P("neck_height_mm");
        float boreD = s.P("bore_diameter_mm") / 2f, boreH = s.P("bore_depth_mm");
        float n = s.P("superellipse_exponent");
        float skin = s.P("skin_mm"), cell = s.P("lattice_cell_mm"), gw = s.P("strut_diameter_mm");
        float total = neckH + Hk;
        Vector3 lo = new(-Dk - 2, -Dk - 2, -1), hi = new(Dk + 2, Dk + 2, total + 1);
        Vector3 cK = new(0, 0, neckH + Hk / 2f);

        Voxels knob = Sdf.Vox(lib, p => MathF.Min(Sdf.SuperEllipsoid(p, cK, new(Dk, Dk, Hk / 2f), n),
                                                  Sdf.CylZ(p, 0, 0, neckD, 0, neckH + Hk * 0.3f)), lo, hi);
        knob.Fillet(3f);
        Voxels bore = Sdf.Vox(lib, p => Sdf.CylZ(p, 0, 0, boreD, -1, boreH), lo, hi);
        Voxels sleeve = Sdf.Vox(lib, p => Sdf.CylZ(p, 0, 0, boreD + skin * 1.5f, -1, boreH + skin * 1.5f), lo, hi);
        Voxels coreRegion = knob.voxOffset(-skin);
        coreRegion.BoolSubtract(sleeve);
        Voxels core = Sdf.LatticeIn(lib, coreRegion, cell, gw);
        knob.BoolSubtract(coreRegion);
        knob.BoolAdd(core);
        knob.BoolSubtract(bore);
        int screws = s.N("setscrew_count");
        float screwD = s.P("setscrew_hole_diameter_mm"), screwZ = s.P("setscrew_height_mm");
        for (int i = 0; i < screws; i++)
        {
            float a = i * 2f * MathF.PI / Math.Max(screws, 1);
            Vector3 dir = new(MathF.Cos(a), MathF.Sin(a), 0);
            knob.BoolSubtract(Sdf.Vox(lib, p => Sdf.Capsule(p, new(0, 0, screwZ), new Vector3(0, 0, screwZ) + dir * (Dk + 2f), screwD / 2f), lo, hi));
        }
        float drainD = s.P("drain_hole_diameter_mm");
        foreach (float sx in new[] { -1f, 1f })
        {
            float x = sx * (boreD + skin * 1.5f + (neckD - boreD - skin * 1.5f) / 2f);
            knob.BoolSubtract(Sdf.Vox(lib, p => Sdf.CylZ(p, x, 0, drainD / 2f, -1, neckH + skin + 2f), lo, hi));
        }
        return knob;
    }

    // ---------------------------------------------------------------- 8
    /// Repair hook: flat mounting tab with screw hole, a gusseted stem and a
    /// round-section hook (J) that carries the adjuster spring end.
    static Voxels HeadlampSpringHook(Library lib, PartSpec s)
    {
        float tabL = s.P("tab_length_mm"), tabW = s.P("tab_width_mm"), tabT = s.P("tab_thickness_mm");
        float holeD = s.P("hole_diameter_mm");
        float stemH = s.P("stem_height_mm"), rodR = s.P("hook_rod_diameter_mm") / 2f;
        float hookR = s.P("hook_inner_radius_mm") + rodR;
        Vector3 lo = new(-tabL / 2f - 2, -tabW / 2f - hookR - 4, -1), hi = new(tabL / 2f + 2, tabW / 2f + 2, stemH + 2 * hookR + 4);

        Voxels v = Sdf.Vox(lib, p => Sdf.RoundBox(p, new(0, 0, tabT / 2f), new(tabL / 2f, tabW / 2f, tabT / 2f), 1f), lo, hi);
        Vector3 s0 = new(tabL / 4f, 0, tabT), s1 = new(tabL / 4f, 0, stemH);
        Lattice lat = new(lib);
        lat.AddBeam(s0, s1, rodR * 1.6f, rodR, true);
        // J hook: arc in the YZ plane from the stem top, curling toward -Y.
        Vector3 cArc = new(tabL / 4f, -hookR, stemH);
        Vector3 prev = s1;
        const int seg = 20;
        for (int i = 1; i <= seg; i++)
        {
            float a = MathF.PI * 1.25f * i / seg;
            Vector3 cur = cArc + new Vector3(0, hookR * MathF.Cos(a), hookR * MathF.Sin(a));
            lat.AddBeam(prev, cur, rodR, rodR, true);
            prev = cur;
        }
        v.BoolAdd(new Voxels(lat));
        v.Fillet(0.6f);
        v.BoolSubtract(Sdf.Vox(lib, p => Sdf.CylZ(p, -tabL / 4f, 0, holeD / 2f, -1, tabT + 1), lo, hi));
        return v;
    }

    // ---------------------------------------------------------------- 9
    /// Velocity stack: bore tapering from the bottom to the top diameter,
    /// elliptical bellmouth at the top, bolted flange at the bottom.
    static Voxels IntakeVelocityStack(Library lib, PartSpec s)
    {
        float rt = s.P("top_bore_diameter_mm") / 2f, rbt = s.P("bottom_bore_diameter_mm") / 2f;
        float Hh = s.P("height_mm"), w = s.P("wall_mm"), lipA = s.P("bellmouth_axial_mm"), lipR = s.P("bellmouth_radial_mm");
        float fR = s.P("flange_diameter_mm") / 2f, fT = s.P("flange_thickness_mm");
        int bolts = s.N("bolt_count");
        float boltD = s.P("bolt_hole_diameter_mm"), pcd = s.P("bolt_pcd_mm") / 2f;
        float zLip = Hh - lipA;
        float Rb(float z)
        {
            float r = rbt + (rt - rbt) * Math.Clamp(z / zLip, 0f, 1f);
            if (z > zLip) { float u = Math.Clamp((z - zLip) / lipA, 0f, 1f); r += lipR * (1f - MathF.Sqrt(1f - u * u)); }
            return r;
        }
        float rMax = MathF.Max(fR, rt + lipR + w) + 2;
        Vector3 lo = new(-rMax, -rMax, -1), hi = new(rMax, rMax, Hh + 1);
        Voxels wall = Sdf.Vox(lib, p =>
        {
            float z = Math.Clamp(p.Z, 0, Hh);
            float dr = MathF.Sqrt(p.X * p.X + p.Y * p.Y) - Rb(z);
            float shell = MathF.Abs(dr - w / 2f) - w / 2f;
            return MathF.Max(shell, MathF.Max(-p.Z, p.Z - Hh));
        }, lo, hi);
        Voxels flange = Sdf.Vox(lib, p => Sdf.CylZ(p, 0, 0, fR, 0, fT), lo, hi);
        flange.BoolSubtract(Sdf.Vox(lib, p => Sdf.CylZ(p, 0, 0, rbt, -1, fT + 1), lo, hi));
        for (int i = 0; i < bolts; i++)
        {
            float a = i * 2f * MathF.PI / bolts, x = pcd * MathF.Cos(a), y = pcd * MathF.Sin(a);
            flange.BoolSubtract(Sdf.Vox(lib, p => Sdf.CylZ(p, x, y, boltD / 2f, -1, fT + 1), lo, hi));
        }
        wall.BoolAdd(flange);
        wall.Fillet(Math.Min(w * 0.45f, 1.5f));
        return wall;
    }

    // ---------------------------------------------------------------- 10
    /// Blanking plug: rounded face plate, hollow body behind it, two snap
    /// clips with barbs on the long sides. Face at z = depth.
    static Voxels SwitchBlank(Library lib, PartSpec s)
    {
        float fw = s.P("face_width_mm") / 2f, fh = s.P("face_height_mm") / 2f, ft = s.P("face_thickness_mm"), fr = s.P("face_corner_radius_mm");
        float bw = s.P("body_width_mm") / 2f, bh = s.P("body_height_mm") / 2f, depth = s.P("body_depth_mm"), wall = s.P("wall_mm");
        float clipW = s.P("clip_width_mm") / 2f, barb = s.P("clip_barb_mm"), clipT = s.P("clip_thickness_mm");
        Vector3 lo = new(-fw - 2, -fh - 2, -1), hi = new(fw + 2, fh + 2, depth + ft + 1);

        Voxels v = Sdf.Vox(lib, p => Sdf.RoundBox(p, new(0, 0, depth + ft / 2f), new(fw, fh, ft / 2f), MathF.Min(fr, ft / 2f - 0.05f)), lo, hi);
        v.BoolAdd(Sdf.Vox(lib, p => MathF.Max(Sdf.Box(p, new(0, 0, depth / 2f + 0.5f), new(bw, bh, depth / 2f + 0.5f)),
                                               -Sdf.Box(p, new(0, 0, depth / 2f - 1f), new(bw - wall, bh - wall, depth / 2f))), lo, hi));
        // Clips: cut a slot around a tongue on each long side, add a barb.
        foreach (float sy in new[] { -1f, 1f })
        {
            float y = sy * (bh - wall / 2f);
            v.BoolSubtract(Sdf.Vox(lib, p => MathF.Max(Sdf.Box(p, new(0, y, depth * 0.4f), new(clipW + 0.6f, wall, depth * 0.45f)),
                                                       -Sdf.Box(p, new(0, y, depth * 0.4f), new(clipW, wall, depth * 0.5f))), lo, hi));
            v.BoolAdd(Sdf.Vox(lib, p => Sdf.Box(p, new(0, sy * (bh + barb / 2f), clipT + 1f), new(clipW, barb / 2f + wall / 2f, clipT)), lo, hi));
        }
        return v;
    }
}
