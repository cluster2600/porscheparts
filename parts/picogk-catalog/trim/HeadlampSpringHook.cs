using System.Numerics;
using PicoGK;

namespace PicoGKCatalog;

/// Repair hook for the headlamp spring mount. X along the part, Z up.
/// A rounded bonding socket (x 0..socket_length) with a blind cavity open at
/// x = 0 slides over the remaining stub of the cast hook; from its rear end a
/// flattened rod rises, curls over in a constant-radius arc and drops into a
/// bulbed tip, forming the J that carries the spring end. A spring seat
/// groove runs round the inside of the arc. Stem, arc and socket are merged
/// with fillets (no weld or bend line), the port of the batch-01 J hook onto
/// the F0 socket concept.
public sealed class HeadlampSpringHook : IPartGenerator
{
    public string Name => "headlamp_spring_hook";

    public Voxels Build(Library lib, PartSpec s)
    {
        float sL = s.P("socket_length_mm"), sW = s.P("socket_width_mm"), sH = s.P("socket_height_mm");
        float cL = s.P("cavity_length_mm"), cW = s.P("cavity_width_mm"), cH = s.P("cavity_height_mm"), cF = s.P("cavity_floor_mm");
        float sR = s.P("socket_edge_radius_mm");
        float L = s.P("overall_length_mm"), H = s.P("overall_height_mm");
        float t = s.P("rod_thickness_mm") / 2f, w = s.P("rod_width_mm") / 2f;
        float rA = s.P("hook_inner_radius_mm") + t;            // arc centre-line radius
        float tipBulb = s.P("tip_bulb_diameter_mm") / 2f, tipZ = s.P("tip_bottom_z_mm");
        float gD = s.P("spring_groove_diameter_mm") / 2f;
        float fil = s.P("root_fillet_mm");

        // Path: stem up at xs, arc of radius rA over the top, tip down at xt.
        float xt = L - tipBulb;                                // tip centre line
        float xs = xt - 2f * rA;                               // stem centre line
        float zc = H - t - rA;                                 // arc centre height
        Vector3 cArc = new(xs + rA, 0, zc);
        float zTipEnd = tipZ + tipBulb;

        Vector3 lo = new(-1, -sW / 2f - 1, -1), hi = new(L + 1, sW / 2f + 1, H + 1);
        float Squash(Vector3 p, Func<Vector3, float> f) => f(new Vector3(p.X, p.Y * (t / w), p.Z));

        Sdf.Stage(s.PartId, "socket");
        Voxels v = Sdf.Vox(lib, p => Sdf.RoundBox(p, new(sL / 2f, 0, sH / 2f), new(sL / 2f, sW / 2f, sH / 2f), sR), lo, hi);

        Sdf.Stage(s.PartId, "hook");
        Voxels hook = Sdf.Vox(lib, p => Squash(p, q =>
        {
            // stem: from inside the socket to the arc start
            float d = Sdf.Capsule(q, new Vector3(xs, 0, sH * 0.5f), new Vector3(xs, 0, zc), t);
            // arc: upper half circle in XZ, centre cArc
            Vector3 r = q - cArc;
            float dArc;
            if (r.Z >= 0) dArc = new Vector2(new Vector2(r.X, r.Z).Length() - rA, r.Y).Length() - t;
            else dArc = float.MaxValue;
            d = MathF.Min(d, dArc);
            // tip: straight drop to a bulb
            d = MathF.Min(d, Sdf.Capsule(q, new Vector3(xt, 0, zc), new Vector3(xt, 0, zTipEnd), t));
            return d;
        }), lo, hi);
        // Bulb is round (not squashed) so it reads as a retention knob.
        hook.BoolAdd(Sdf.Vox(lib, p => Sdf.Sphere(p, new Vector3(xt, 0, zTipEnd), tipBulb), lo, hi));
        // Stem flares into the socket: tapered web along the stem root.
        hook.BoolAdd(Sdf.Vox(lib, p =>
            Sdf.Capsule(new Vector3(p.X, p.Y * (1.25f * t / w), p.Z), new Vector3(xs - 0.6f, 0, sH * 0.6f),
                        new Vector3(xs, 0, sH + 2.2f), t * 1.25f), lo, hi));
        v.BoolAdd(hook);
        Sdf.Stage(s.PartId, "fillet");
        v.Fillet(fil);

        Sdf.Stage(s.PartId, "cavity and groove");
        // Bonding cavity: open at x = 0, rounded inner corners, mouth chamfer.
        v.BoolSubtract(Sdf.Vox(lib, p =>
        {
            float box = Sdf.RoundBox(p, new(cL / 2f - 1f, 0, cF + cH / 2f), new(cL / 2f + 1f, cW / 2f, cH / 2f), 0.6f);
            float mouth = MathF.Max(MathF.Max(MathF.Abs(p.Y) - cW / 2f - 0.6f + p.X, MathF.Abs(p.Z - (cF + cH / 2f)) - cH / 2f - 0.6f + p.X), p.X - 0.6f);
            return MathF.Min(box, mouth);
        }, lo, hi));
        // Spring seat: torus round the inside of the arc, in the mid plane.
        v.BoolSubtract(Sdf.Vox(lib, p =>
        {
            Vector3 r = p - cArc;
            // distance to an arc of the inner surface, angles 25..155 deg: round-ended channel
            float phi = Math.Clamp(MathF.Atan2(r.Z, r.X), 0.14f * MathF.PI, 0.86f * MathF.PI);
            Vector3 c = cArc + (rA - t) * new Vector3(MathF.Cos(phi), 0, MathF.Sin(phi));
            return (p - c).Length() - gD;
        }, lo, hi));
        return v;
    }
}
