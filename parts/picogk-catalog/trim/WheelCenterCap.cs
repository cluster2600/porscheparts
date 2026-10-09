using System.Numerics;
using PicoGK;

namespace PicoGKCatalog;

/// Wheel center cap, axis Z, clip end at z = 0, crown of the face at
/// z = overall_height. Domed face as a skin + open-cell BCC lattice sandwich
/// (drained through the underside), a short outer skirt with a rolled lip
/// (the F0 outer skirt), the centering ring (F0 ID/OD), radial gussets
/// between ring and skirt, and cantilever clip tabs continuing the ring
/// below its slotted end, each with an outward lead-in barb.
public sealed class WheelCenterCap : IPartGenerator
{
    public string Name => "wheel_center_cap";

    public Voxels Build(Library lib, PartSpec s)
    {
        float R = s.P("face_diameter_mm") / 2f, Hh = s.P("overall_height_mm");
        float rI = s.P("ring_inner_diameter_mm") / 2f, rO = s.P("ring_outer_diameter_mm") / 2f;
        float ft = s.P("face_thickness_mm"), dome = s.P("dome_height_mm");
        float skH = s.P("outer_skirt_height_mm"), skW = s.P("outer_skirt_wall_mm");
        int tabs = s.N("tab_count");
        float tabW = s.P("tab_width_mm"), tabL = s.P("tab_length_mm"), barb = s.P("tab_barb_mm"), barbH = s.P("tab_barb_height_mm");
        int ribs = s.N("rib_count");
        float ribT = s.P("rib_thickness_mm");
        float skin = s.P("skin_mm"), cell = s.P("lattice_cell_mm"), gw = s.P("strut_diameter_mm");
        float drainD = s.P("drain_hole_diameter_mm");
        float edgeR = s.P("face_edge_radius_mm");
        float vox = s.VoxelMm;

        float zRim = Hh - dome;                          // top of the face at its rim
        float zU = zRim - ft;                            // flat underside of the face
        float zSk = zRim - skH;                          // skirt bottom (F0: face top - 12 mm)
        float Rs = (R * R + dome * dome) / (2f * dome);
        Vector3 cDome = new(0, 0, Hh - Rs);
        Vector3 lo = new(-R - 2, -R - 2, -1), hi = new(R + 2, R + 2, Hh + 1);

        Sdf.Stage(s.PartId, "face");
        Voxels face = Sdf.Vox(lib, p => MathF.Max(Sdf.CylZ(p, 0, 0, R, zU, Hh + 1), Sdf.Sphere(p, cDome, Rs)), lo, hi);
        TrimKit.Round(face, edgeR);

        Sdf.Stage(s.PartId, "skirt, ring, ribs, tabs");
        // Outer skirt: thin ring from zSk up into the face, rolled (round) lip.
        Voxels body = Sdf.Vox(lib, p =>
        {
            float r = MathF.Sqrt(p.X * p.X + p.Y * p.Y);
            float wall = MathF.Max(MathF.Abs(r - (R - skW / 2f)) - skW / 2f, MathF.Max(zSk + skW / 2f - p.Z, p.Z - (zU + 1f)));
            float lip = new Vector2(r - (R - skW / 2f), p.Z - (zSk + skW / 2f)).Length() - skW / 2f;
            return MathF.Min(wall, lip);
        }, lo, hi);
        // Centering ring, full ring from the tab roots to the face.
        body.BoolAdd(Sdf.Vox(lib, p =>
        {
            float r = MathF.Sqrt(p.X * p.X + p.Y * p.Y);
            return MathF.Max(MathF.Abs(r - (rI + rO) / 2f) - (rO - rI) / 2f, MathF.Max(tabL - p.Z, p.Z - (zU + 1f)));
        }, lo, hi));
        float Sector(Vector3 p, float halfW, int n, float phase)
        {
            float best = float.MaxValue;
            for (int i = 0; i < n; i++)
            {
                float a = (i + phase) * 2f * MathF.PI / n;
                Vector2 dir = new(MathF.Cos(a), MathF.Sin(a)), nrm = new(-dir.Y, dir.X), q = new(p.X, p.Y);
                best = MathF.Min(best, MathF.Max(MathF.Abs(Vector2.Dot(q, nrm)) - halfW, -Vector2.Dot(q, dir)));
            }
            return best;
        }
        // Radial gussets between ring and skirt, tapering down from the face.
        body.BoolAdd(Sdf.Vox(lib, p =>
        {
            float r = MathF.Sqrt(p.X * p.X + p.Y * p.Y);
            float zb = zSk - 4f + 5f * Math.Clamp((r - rO) / (R - skW - rO), 0f, 1f);  // sloped lower edge, deepest at the ring
            float band = MathF.Max(MathF.Max(rO - 0.5f - r, r - (R - skW + 0.5f)), MathF.Max(zb - p.Z, p.Z - (zU + 1f)));
            return MathF.Max(band, Sector(p, ribT / 2f, ribs, 0.5f));
        }, lo, hi));
        // Clip tabs: the ring continued below its end in `tabs` sectors.
        body.BoolAdd(Sdf.Vox(lib, p =>
        {
            float r = MathF.Sqrt(p.X * p.X + p.Y * p.Y);
            float ringPart = MathF.Max(MathF.Abs(r - (rI + rO) / 2f) - (rO - rI) / 2f, MathF.Max(-p.Z, p.Z - (tabL + 1f)));
            return MathF.Max(ringPart, Sector(p, tabW / 2f, tabs, 0f));
        }, lo, hi));
        // Barbs: outward wedge, full height `barbH` at its latch face, lead-in to the tab end.
        body.BoolAdd(Sdf.Vox(lib, p =>
        {
            float r = MathF.Sqrt(p.X * p.X + p.Y * p.Y);
            float t = Math.Clamp((p.Z - 0.3f) / barbH, 0f, 1f);
            float wedge = MathF.Max(MathF.Max(rO - 0.6f - r, r - (rO + barb * t)), MathF.Max(0.3f - p.Z, p.Z - (0.3f + barbH)));
            return MathF.Max(wedge, Sector(p, tabW / 2f - 0.6f, tabs, 0f));
        }, lo, hi));
        face.BoolAdd(body);
        Sdf.Stage(s.PartId, "fillet");
        face.Fillet(1.0f);

        Sdf.Stage(s.PartId, "sandwich core");
        // Core: the face interior shrunk by the skin, kept clear of the outer rim.
        Voxels faceSolid = Sdf.Vox(lib, p => MathF.Max(Sdf.CylZ(p, 0, 0, R - skW - 1f, zU, Hh + 1), Sdf.Sphere(p, cDome, Rs)), lo, hi);
        Voxels cavity = faceSolid.voxOffset(-skin);
        Voxels lattice = Sdf.LatticeIn(lib, cavity.voxOffset(vox), cell, gw);   // 1 voxel overlap into the skins
        face.BoolSubtract(cavity);
        face.BoolAdd(lattice);

        Sdf.Stage(s.PartId, "drains");
        float rd1 = (rO + R - skW) / 2f, rd2 = rI * 0.5f;
        for (int i = 0; i < ribs; i++)
        {
            float a = i * 2f * MathF.PI / ribs;
            float x = rd1 * MathF.Cos(a), y = rd1 * MathF.Sin(a);
            face.BoolSubtract(Sdf.Vox(lib, p => Sdf.CylZ(p, x, y, drainD / 2f, zU - 3f, zU + skin + 0.5f), lo, hi));
        }
        for (int i = 0; i < 4; i++)
        {
            float a = (i + 0.5f) * MathF.PI / 2f;
            float x = rd2 * MathF.Cos(a), y = rd2 * MathF.Sin(a);
            face.BoolSubtract(Sdf.Vox(lib, p => Sdf.CylZ(p, x, y, drainD / 2f, zU - 3f, zU + skin + 0.5f), lo, hi));
        }
        return face;
    }
}
