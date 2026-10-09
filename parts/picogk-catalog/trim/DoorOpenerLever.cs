using System.Numerics;
using PicoGK;

namespace PicoGKCatalog;

/// Interior door opener lever (port of batch-01). Pivot sleeve on Z at the
/// origin; a flattened arm swept along a quadratic Bezier curve to a grip
/// paddle, tangent to X so the paddle stays inside the published length x
/// width envelope. The paddle carries a finger dish on top and a row of
/// through slots (FVD offers a perforated variant). Arm and paddle are a
/// skin over an open-cell BCC lattice core, drained through the paddle tip;
/// the pivot sleeve and the slot rims stay solid.
public sealed class DoorOpenerLever : IPartGenerator
{
    public string Name => "door_opener_lever";

    public Voxels Build(Library lib, PartSpec s)
    {
        float Lt = s.P("length_mm"), Wt = s.P("width_mm"), Ht = s.P("height_mm");
        float bossD = s.P("pivot_boss_diameter_mm"), pinD = s.P("pivot_pin_diameter_mm");
        float armR = s.P("arm_radius_mm"), flat = s.P("arm_flattening");
        float padW = s.P("paddle_width_mm"), padT = s.P("paddle_thickness_mm"), padL = s.P("paddle_length_mm");
        float dish = s.P("finger_dish_depth_mm");
        int nSlot = s.N("slot_count");
        float slotW = s.P("slot_width_mm"), slotL = s.P("slot_length_mm"), slotP = s.P("slot_pitch_mm");
        float skin = s.P("skin_mm"), cell = s.P("lattice_cell_mm"), gw = s.P("strut_diameter_mm");
        float drainD = s.P("drain_hole_diameter_mm");
        float bossCh = s.P("boss_edge_radius_mm");
        float vox = s.VoxelMm;

        float rb = bossD / 2f;
        Vector3 a = new(0, 0, Ht / 2f), c = new(Lt - rb - padL, Wt - rb - padW / 2f, Ht / 2f);
        Vector3 b = new(a.X + 0.55f * (c.X - a.X), c.Y, Ht / 2f);
        Vector3 lo = new(-rb - 2, -rb - 2, -1), hi = new(Lt, Wt, Ht + 1);
        Vector3 tan = Vector3.Normalize(c - b);
        Vector3 pc = c + tan * (padL / 2f);
        Vector2 u = new(tan.X, tan.Y), v = new(-tan.Y, tan.X);
        Vector3 Local(Vector3 p) { Vector3 q = p - pc; return new(Vector2.Dot(new(q.X, q.Y), u), Vector2.Dot(new(q.X, q.Y), v), q.Z); }

        float Arm(Vector3 p)
        {
            float best = float.MaxValue;
            const int seg = 24;
            Vector3 prev = a;
            Vector3 q = new(p.X, p.Y, a.Z + (p.Z - a.Z) * flat);   // flattened section
            for (int i = 1; i <= seg; i++)
            {
                Vector3 cur = Sdf.Bezier(a, b, c, i / (float)seg);
                // the arm thins slightly toward the paddle
                float r = armR * (1f - 0.12f * i / seg);
                best = MathF.Min(best, Sdf.Capsule(q, prev, cur, r));
                prev = cur;
            }
            return best;
        }
        float Paddle(Vector3 p)
        {
            Vector3 l = Local(p);
            // paddle swells slightly toward its tip (plan taper) and is rounded
            float hw = padW / 2f * (0.85f + 0.15f * Math.Clamp(l.X / padL + 0.5f, 0f, 1f));
            float d2 = TrimKit.RoundRect(l.X, l.Y, padL / 2f, hw, hw * 0.6f);
            return TrimKit.Extrude(d2, MathF.Abs(l.Z) - padT / 2f);
        }
        float Slots(Vector3 p)
        {
            Vector3 l = Local(p);
            float best = float.MaxValue;
            for (int i = 0; i < nSlot; i++)
            {
                float x0 = -padL / 2f + 6f + i * slotP;
                best = MathF.Min(best, TrimKit.Stadium(l.Y, l.X - x0, slotL / 2f - slotW / 2f, slotW / 2f));
            }
            return best;
        }

        Sdf.Stage(s.PartId, "arm and paddle");
        Voxels body = Sdf.Vox(lib, p => TrimKit.SMin(Arm(p), Paddle(p), 4f), lo, hi);
        TrimKit.Round(body, 1.2f);
        Voxels boss = Sdf.Vox(lib, p => Sdf.CylZ(p, 0, 0, rb, 0, Ht), lo, hi);
        TrimKit.Round(boss, bossCh);
        body.BoolAdd(boss);
        // Fillet the outer shape first: filleting after hollowing would round
        // the lattice voids shut.
        Sdf.Stage(s.PartId, "fillet");
        body.Fillet(2.0f);
        // Finger dish: shallow ellipsoidal scoop on the top of the paddle.
        body.BoolSubtract(Sdf.Vox(lib, p =>
        {
            Vector3 l = Local(p) - new Vector3(padL * 0.12f, 0, padT / 2f + 30f - dish);
            return Sdf.SuperEllipsoid(l, Vector3.Zero, new Vector3(padL * 0.42f, padW * 0.36f, 30f), 2f);
        }, lo, hi));

        Sdf.Stage(s.PartId, "core");
        Voxels slots = Sdf.Vox(lib, p => Slots(p), lo, hi);
        Voxels cavity = body.voxOffset(-skin);
        cavity.BoolSubtract(boss.voxOffset(skin));
        cavity.BoolSubtract(slots.voxOffset(skin));
        Voxels core = Sdf.LatticeIn(lib, cavity.voxOffset(vox), cell, gw);   // 1 voxel overlap into the skin
        body.BoolSubtract(cavity);
        body.BoolAdd(core);

        Sdf.Stage(s.PartId, "slots, drain, bore");
        body.BoolSubtract(slots);
        Vector3 dTip = pc + tan * (padL / 2f - 5f);
        body.BoolSubtract(Sdf.Vox(lib, p => Sdf.CylZ(p, dTip.X, dTip.Y, drainD / 2f, -1, Ht / 2f), lo, hi));
        Vector3 dRoot = Sdf.Bezier(a, b, c, 0.35f);
        body.BoolSubtract(Sdf.Vox(lib, p => Sdf.CylZ(p, dRoot.X, dRoot.Y, drainD / 2f, -1, Ht / 2f), lo, hi));
        body.BoolSubtract(Sdf.Vox(lib, p => Sdf.CylZ(p, 0, 0, pinD / 2f, -1, Ht + 1), lo, hi));
        return body;
    }
}
