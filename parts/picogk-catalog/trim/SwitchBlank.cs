using System.Numerics;
using PicoGK;

namespace PicoGKCatalog;

/// Dashboard switch blank, insertion axis Z: back (clip ends) at z = 0,
/// visible face from z = tab_length to tab_length + face_thickness.
/// Pillow-crowned face plate with rounded corners and rolled edges; a thin
/// hollow body that passes through the opening, open at the back; two
/// cantilever snap tongues cut out of the long walls with lead-in barbs that
/// latch behind the fascia. One body, slots kept open by cutting them last.
public sealed class SwitchBlank : IPartGenerator
{
    public string Name => "switch_blank";

    public Voxels Build(Library lib, PartSpec s)
    {
        float fw = s.P("face_width_mm") / 2f, fh = s.P("face_height_mm") / 2f, ft = s.P("face_thickness_mm");
        float fr = s.P("face_corner_radius_mm"), er = s.P("face_edge_radius_mm"), crown = s.P("face_crown_mm");
        float ow = s.P("opening_width_mm") / 2f, oh = s.P("opening_height_mm") / 2f, clr = s.P("body_clearance_mm");
        float depth = s.P("tab_length_mm"), wall = s.P("tab_thickness_mm"), br = s.P("body_corner_radius_mm");
        float clipW = s.P("clip_width_mm") / 2f, slot = s.P("clip_slot_mm"), clipL = s.P("clip_slot_length_mm");
        float barb = s.P("clip_barb_mm"), panel = s.P("panel_thickness_mm"), barbL = s.P("clip_barb_length_mm");

        float bx = ow - clr, by = oh - clr;              // body outer half sizes
        float z0 = depth, z1 = depth + ft;               // face slab
        Vector3 lo = new(-fw - 1, -fh - 1, -1), hi = new(fw + 1, fh + 1, z1 + 1);

        Sdf.Stage(s.PartId, "face");
        // Crowned slab: top surface rises by `crown` at the centre.
        Voxels face = Sdf.Vox(lib, p =>
        {
            float d2 = TrimKit.RoundRect(p.X, p.Y, fw, fh, fr);
            float u = p.X / fw, v = p.Y / fh;
            float top = z1 - crown * Math.Clamp(u * u + v * v, 0f, 1f);
            float dz = MathF.Max(z0 - p.Z, p.Z - top);
            return TrimKit.Extrude(d2, dz);
        }, lo, hi);
        TrimKit.Round(face, er);

        Sdf.Stage(s.PartId, "body");
        Voxels body = Sdf.Vox(lib, p =>
        {
            float outer = TrimKit.Extrude(TrimKit.RoundRect(p.X, p.Y, bx, by, br), MathF.Max(-p.Z, p.Z - (z0 + 0.5f)));
            float inner = TrimKit.Extrude(TrimKit.RoundRect(p.X, p.Y, bx - wall, by - wall, MathF.Max(br - wall, 0.3f)),
                                          MathF.Max(-1f - p.Z, p.Z - (z0 - 0.0f)));
            return MathF.Max(outer, -inner);
        }, lo, hi);

        // Barbs on the long (x = +-bx) walls: wedge growing from 0 at the
        // back to `barb` at its latch face, which sits one panel thickness
        // under the face.
        float zl = z0 - panel, zb = zl - barbL;
        Voxels barbs = Sdf.Vox(lib, p =>
        {
            float ax = MathF.Abs(p.X);
            float t = Math.Clamp((p.Z - zb) / (zl - zb), 0f, 1f);
            float box = Sdf.Box(new Vector3(ax, p.Y, p.Z), new Vector3(bx - wall / 2f + barb / 2f, 0, (zl + zb) / 2f),
                                new Vector3(wall / 2f + barb / 2f, clipW - 0.3f, (zl - zb) / 2f));
            float ramp = (ax - (bx + barb * t)) * 0.9f;
            return MathF.Max(box, ramp);
        }, lo, hi);
        body.BoolAdd(barbs);
        // Pull-off notch on the face bottom edge would be cosmetic; leave the face plain.
        face.BoolAdd(body);
        face.Fillet(0.4f);   // root fillet face/body before any slot is cut

        Sdf.Stage(s.PartId, "clip slots");
        Voxels slots = Sdf.Vox(lib, p =>
        {
            float ax = MathF.Abs(p.X), ay = MathF.Abs(p.Y);
            // two vertical slits per side, either side of the tongue, open at the back
            float slit = MathF.Max(MathF.Abs(ay - (clipW + slot / 2f)) - slot / 2f,
                                   MathF.Max(MathF.Abs(ax - (bx - wall / 2f)) - wall, MathF.Max(-1f - p.Z, p.Z - clipL)));
            return slit;
        }, lo, hi);
        face.BoolSubtract(slots);
        return face;
    }
}
