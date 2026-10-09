using System.Numerics;
using PicoGK;

namespace PicoGKCatalog;

/// Seat rail trim cover: a long channel open underneath (X along the rail,
/// Z up, open face at z = 0). Crowned top, drafted side walls, rounded plan
/// corners and end caps that ramp down to a low nose at both ends, all edges
/// rounded. Inside: transverse stiffening ribs under the crown, a screw boss
/// with a countersunk through hole in each end ramp, and snap clips cut out
/// of the side walls (slotted tongues with inward hook lips at the open edge).
public sealed class SeatRailCover : IPartGenerator
{
    public string Name => "seat_rail_cover";

    public Voxels Build(Library lib, PartSpec s)
    {
        float L = s.P("length_mm"), W = s.P("width_mm"), H = s.P("height_mm"), wall = s.P("wall_mm");
        float crown = s.P("crown_mm"), draft = s.P("side_draft_mm"), ramp = s.P("end_ramp_length_mm"), nose = s.P("nose_height_mm");
        float rc = s.P("plan_corner_radius_mm"), edgeR = s.P("edge_radius_mm");
        int ribN = s.N("rib_count");
        float ribT = s.P("rib_thickness_mm"), ribD = s.P("rib_depth_mm");
        int clipN = s.N("clips_per_side");
        float clipL = s.P("clip_length_mm"), clipH = s.P("clip_slot_height_mm"), slot = s.P("clip_slot_mm"), hook = s.P("clip_hook_mm");
        float bossD = s.P("screw_boss_diameter_mm"), holeD = s.P("screw_hole_diameter_mm"), csD = s.P("countersink_diameter_mm");
        float vox = s.VoxelMm;
        float hx = L / 2f, hy = W / 2f;

        float Height(float x)
        {
            float e = hx - MathF.Abs(x);
            return nose + (H - nose) * TrimKit.Smooth(e / ramp);
        }
        float HalfW(float z) => hy - draft * Math.Clamp(z / H, 0f, 1f);
        // Outer field; inset > 0 gives the inner (offset) surface analytically.
        float Shell(Vector3 p, float inset, float zMin)
        {
            float hw = HalfW(p.Z) - inset;
            float d2 = TrimKit.RoundRect(p.X, p.Y, hx - inset, hw, MathF.Max(rc - inset, 0.5f));
            float top = Height(p.X) - inset - crown * Math.Clamp((p.Y / hw) * (p.Y / hw), 0f, 1f);
            return MathF.Max(d2, MathF.Max((p.Z - top) * 0.85f, zMin - p.Z));
        }

        Vector3 lo = new(-hx - 1, -hy - 1, -1), hi = new(hx + 1, hy + 1, H + 1);
        Sdf.Stage(s.PartId, "outer");
        Voxels outer = Sdf.Vox(lib, p => Shell(p, 0f, -6f), new(lo.X, lo.Y, -7), hi);
        TrimKit.Round(outer, edgeR);
        outer.BoolIntersect(Sdf.Vox(lib, p => -p.Z, lo, hi));        // crisp open face at z = 0

        Sdf.Stage(s.PartId, "hollow");
        Voxels cavity = Sdf.Vox(lib, p => Shell(p, wall, -2f), lo, hi);
        outer.BoolSubtract(cavity);
        Voxels inside = cavity.voxOffset(vox);       // overlap into the walls for every insert

        Sdf.Stage(s.PartId, "ribs and bosses");
        float span = L - 2f * ramp;
        Voxels ribs = Sdf.Vox(lib, p =>
        {
            float best = float.MaxValue;
            for (int i = 0; i < ribN; i++)
            {
                float x = -span / 2f + span * (i + 0.5f) / ribN;
                best = MathF.Min(best, MathF.Abs(p.X - x) - ribT / 2f);
            }
            return MathF.Max(best, (H - ribD) - p.Z);
        }, lo, hi);
        float xb = hx - ramp * 0.55f;
        Voxels bosses = Sdf.Vox(lib, p =>
        {
            float d = MathF.Min(Sdf.CylZ(p, xb, 0, bossD / 2f, 1.5f, H), Sdf.CylZ(p, -xb, 0, bossD / 2f, 1.5f, H));
            return d;
        }, lo, hi);
        ribs.BoolAdd(bosses);
        ribs.BoolIntersect(inside);
        outer.BoolAdd(ribs);

        Sdf.Stage(s.PartId, "clips");
        float pitch = span / clipN;
        float hwBot = HalfW(0f);
        Voxels lips = Sdf.Vox(lib, p =>
        {
            float best = float.MaxValue;
            for (int i = 0; i < clipN; i++)
            {
                float x = -span / 2f + pitch * (i + 0.5f);
                // inward hook lip with a lead-in chamfer at the open edge
                Vector3 q = new(p.X - x, MathF.Abs(p.Y), p.Z);
                float box = Sdf.Box(q, new(0, hwBot - wall - hook / 2f + 0.3f, 1.6f), new(clipL / 2f - 1f, hook / 2f + 0.3f, 1.6f));
                // lead-in chamfer on the lower inner corner (the rail enters from below)
                float keep = ((hwBot - wall - hook) + hook * 0.8f - q.Y - q.Z) * 0.7071f;
                best = MathF.Min(best, MathF.Max(box, keep));
            }
            return best;
        }, lo, hi);
        outer.BoolAdd(lips);
        outer.Fillet(0.6f);

        // U slots either side of each tongue, open at the bottom edge.
        outer.BoolSubtract(Sdf.Vox(lib, p =>
        {
            float best = float.MaxValue;
            for (int i = 0; i < clipN; i++)
            {
                float x = -span / 2f + pitch * (i + 0.5f);
                float dx = MathF.Abs(MathF.Abs(p.X - x) - (clipL / 2f + slot / 2f)) - slot / 2f;
                best = MathF.Min(best, MathF.Max(dx, MathF.Max(p.Z - clipH, MathF.Abs(MathF.Abs(p.Y) - (hwBot - wall / 2f)) - wall - hook)));
            }
            return best;
        }, lo, hi));

        Sdf.Stage(s.PartId, "screw holes");
        outer.BoolSubtract(Sdf.Vox(lib, p =>
        {
            float d = float.MaxValue;
            foreach (float x in new[] { xb, -xb })
            {
                float r = new Vector2(p.X - x, p.Y).Length();
                float hole = r - holeD / 2f;
                float top = Height(x);                                // countersink from the local top
                float cs = (r - (csD / 2f - (top + 0.2f - p.Z))) * 0.7071f;
                d = MathF.Min(d, MathF.Min(hole, cs));
            }
            return d;
        }, lo, hi));
        return outer;
    }
}
