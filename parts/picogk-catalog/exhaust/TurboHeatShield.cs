using System.Numerics;
using PicoGK;

namespace PicoGKCatalog;

/// Port of parts/picogk-993-batch-01 TurboHeatShield: open half-superellipsoid
/// cover (open side down, z = 0), two thin skins with an open-cell BCC lattice
/// core between them, closed at the rim by a solid band with drain holes into
/// the gap. The F0 side bosses
/// (-Y wall, along X, bore along Y) are solid plugs through the double wall
/// standing proud on the inside, each with a through bore. Pressed-look beads
/// corrugate the whole sandwich for stiffness.
public sealed class TurboHeatShield : IPartGenerator
{
    public string Name => "turbo_heat_shield";

    public Voxels Build(Library lib, PartSpec s)
    {
        float L = s.P("length_mm") / 2f, W = s.P("width_mm") / 2f, Hh = s.P("height_mm");
        float wo = s.P("outer_skin_mm"), wi = s.P("inner_skin_mm"), gap = s.P("core_gap_mm");
        float n = s.P("superellipse_exponent");
        float cell = s.P("lattice_cell_mm"), gw = s.P("strut_diameter_mm");
        int nb = s.N("boss_count");
        float bp = s.P("boss_spacing_mm"), bz = s.P("boss_center_z_mm"), bR = s.P("boss_radius_mm"), bD = s.P("boss_depth_mm");
        float boreR = s.P("mount_bore_diameter_mm") / 2f;
        float rimH = s.P("rim_band_height_mm"), drainR = s.P("drain_hole_diameter_mm") / 2f;
        int nd = s.N("drain_count");
        int nBead = s.N("bead_count");
        float bPitch = s.P("bead_pitch_mm"), bDepth = s.P("bead_depth_mm"), bW = s.P("bead_width_mm"), bZ0 = s.P("bead_start_z_mm");
        float T = wo + gap + wi;

        // Pressed-look stiffening beads across the cover (constant x), pushing
        // the whole sandwich inward together; they fade out toward the rim.
        float Bead(Vector3 p)
        {
            float b = 0f;
            for (int i = 0; i < nBead; i++)
            {
                float u = (p.X - (i - (nBead - 1) / 2f) * bPitch) / bW;
                b += MathF.Exp(-u * u);
            }
            return bDepth * b * FlowKit.Smooth((p.Z - bZ0) / 20f);
        }
        float SE(Vector3 p, float off) => Sdf.SuperEllipsoid(p, Vector3.Zero, new(L - off, W - off, Hh - off), n) + Bead(p);
        Vector3 lo = new(-L - 1, -W - 1, -1), hi = new(L + 1, W + 1, Hh + 1);

        Sdf.Stage(s.PartId, "skins");
        Voxels shell = Sdf.Vox(lib, p => MathF.Max(SE(p, 0f), -p.Z), lo, hi);
        shell.BoolSubtract(Sdf.Vox(lib, p => MathF.Max(SE(p, T), -p.Z - 2f), lo, hi));
        Voxels coreRegion = Sdf.Vox(lib, p => MathF.Max(MathF.Max(SE(p, wo), -SE(p, wo + gap)), rimH - p.Z), lo, hi);

        Sdf.Stage(s.PartId, "lattice");
        // Struts reach one voxel into each skin so the contact has volume.
        Voxels core = Sdf.LatticeIn(lib, coreRegion.voxOffset(s.VoxelMm), cell, gw);
        shell.BoolSubtract(coreRegion);
        shell.BoolAdd(core);

        Sdf.Stage(s.PartId, "bosses");
        float[] xs = Enumerable.Range(0, nb).Select(i => (i - (nb - 1) / 2f) * bp).ToArray();
        Vector3 blo = new(-L, -W - 1, bz - bR - 1), bhi = new(L, -W + T + bD + 30f, bz + bR + 1);
        shell.BoolAdd(Sdf.Vox(lib, p =>
        {
            float d = float.MaxValue;
            foreach (float x in xs)
                d = MathF.Min(d, FlowKit.Cyl(p, new(x, -W - 1f, bz), new(x, 0f, bz), bR));
            // plug: inside the outer skin, reaching bD past the inner skin
            return MathF.Max(d, MathF.Max(SE(p, 0f), -SE(p, T + bD)));
        }, blo, bhi));
        Lattice bores = new(lib);
        foreach (float x in xs)
            bores.AddBeam(new Vector3(x, -W - 2f, bz), new Vector3(x, -W + T + bD + 30f, bz), boreR, boreR, false);
        // Powder / vent drains: through the solid rim band into the gap.
        float rmx = L - wo - gap / 2f, rmy = W - wo - gap / 2f;
        for (int i = 0; i < nd; i++)
        {
            float a = (i + 0.5f) * 2f * MathF.PI / nd, ca = MathF.Cos(a), sa = MathF.Sin(a);
            float k = MathF.Pow(MathF.Pow(MathF.Abs(ca), n) + MathF.Pow(MathF.Abs(sa), n), -1f / n);
            Vector3 c = new(ca * k * rmx, sa * k * rmy, 0f);
            bores.AddBeam(c - Vector3.UnitZ * 2f, c + Vector3.UnitZ * (rimH + 1.5f), drainR, drainR, false);
        }
        shell.BoolSubtract(new Voxels(bores));
        shell.Trim(new BBox3(new Vector3(lo.X, lo.Y, 0), hi));
        return shell;
    }
}
