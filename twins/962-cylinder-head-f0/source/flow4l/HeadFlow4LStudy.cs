using System.Numerics;
using PicoGK;
using Leap71.ShapeKernel;

namespace PicoGKCatalog;

// Flow-sized fork preserves prior receipts; dimensions remain unmeasured study assumptions.
public sealed class HeadFlow4LStudy : IPartGenerator
{
    public string Name => "962_inspired_4l_sp95_flow_study";

    static Voxels Oval(Vector3 origin, Vector3 axis, Vector3 localX, float length,
        float a0, float b0, float a1, float b1)
    {
        var shape = new BaseCylinder(new LocalFrame(origin, axis, localX), length, a0);
        shape.SetRadius(new SurfaceModulation((phi, t) =>
        {
            float a = a0 + (a1 - a0) * t, b = b0 + (b1 - b0) * t;
            float x = b * MathF.Cos(phi), y = a * MathF.Sin(phi);
            return a * b / MathF.Sqrt(x * x + y * y);
        }));
        shape.SetLengthSteps(24); shape.SetPolarSteps(96);
        return shape.voxConstruct();
    }

    static void AddRibs(Library lib, Voxels body)
    {
        Lattice lattice = new(lib);
        var type = new Leap71.LatticeLibrary.BodyCentreLattice();
        foreach (float side in new[] { -1f, 1f })
        for (float y = -42; y < 42; y += 14)
        for (float z = 30; z < 72; z += 14)
        {
            float x0 = side < 0 ? -62 : 50, x1 = x0 + 12;
            var cell = new Leap71.LatticeLibrary.CuboidCell(new(x0, y, z), new(x0, y + 14, z),
                new(x1, y + 14, z), new(x1, y, z), new(x0, y, z + 14),
                new(x0, y + 14, z + 14), new(x1, y + 14, z + 14), new(x1, y, z + 14));
            type.AddCell(ref lattice, cell, new Leap71.LatticeLibrary.ConstantBeamThickness(3.5f), 2);
        }
        using Voxels ribs = new(lattice);
        body.BoolAdd(ribs);
        lattice.Dispose();
    }

    public Voxels Build(Library lib, PartSpec s)
    {
        if (s.Status != "shape_study_only_unmeasured_interfaces_no_manufacturing" ||
            s.SafetyClass != "prohibited_pending_engineering" || s.DensityGCm3 != 0 ||
            s.VoxelMm != .5f || s.Parameters.Count != 1 || !s.Parameters.ContainsKey("export_mode") ||
            s.Parameters["export_mode"].Basis != "assumption" || s.Parameters["export_mode"].Unit != "1" ||
            !double.IsFinite(s.Parameters["export_mode"].Value) ||
            s.Parameters["export_mode"].Value != Math.Truncate(s.Parameters["export_mode"].Value) ||
            s.Parameters["export_mode"].Value < 0 || s.Parameters["export_mode"].Value > 2)
            throw new ArgumentException("Only fixed, unqualified architecture-study modes are accepted.");

        Library.RegisterGlobalLibrary(lib);
        try
        {
            var loft = new BaseBox(new LocalFrame(), 90, 120, 140);
            loft.SetWidth(new LineModulation(t => 120 - 12 * t));
            loft.SetDepth(new LineModulation(t => 140 - 4 * t));
            loft.SetLengthSteps(24); loft.SetWidthSteps(8); loft.SetDepthSteps(8);
            Voxels body = loft.voxConstruct();
            body.BoolIntersect(Sdf.Vox(lib, p => MathF.Abs(p.X) + MathF.Abs(p.Y) - 113,
                new(-80, -85, -5), new(80, 85, 100)));
            body.Smoothen(1);
            body.BoolAdd(new BaseCylinder(new LocalFrame(), 12, 59).voxConstruct());

            Voxels gas = Sdf.Vox(lib, p => Sdf.SuperEllipsoid(p, new(0, 0, -1), new(49, 49, 13), 2),
                new(-54, -54, -16), new(54, 54, 15));
            var branches = new Lattice(lib);
            foreach (float side in new[] { -1f, 1f })
            {
                float radius = side < 0 ? 11 : 9;
                foreach (float x in new[] { -20f, 20f })
                {
                    branches.AddBeam(new(x, side * 22, 6), radius, new(x, side * 26, 29), radius, true);
                    branches.AddBeam(new(x, side * 26, 29), radius, new(0, side * 60, 43), 12, true);
                }
                gas.BoolAdd(Oval(new(0, side * 54, 43), new(0, side, 0), Vector3.UnitX, 32, 23, 13, 25, 14));
                body.BoolAdd(Oval(new(0, side * 56, 43), new(0, side, 0), Vector3.UnitX, 19, 30, 20, 32, 21));
            }
            gas.BoolAdd(new Voxels(branches));
            Voxels dry = gas.voxOffset(0);
            var guides = new Lattice(lib);
            foreach (float side in new[] { -1f, 1f })
                foreach (float x in new[] { -20f, 20f })
                    guides.AddBeam(new(x, side * 25, 25), 3.5f, new(x, side * 39, 100), 3.5f, true);
            guides.AddBeam(new(0, 0, 4), 6, new(0, 0, 100), 6, true);
            guides.AddBeam(new(38, 0, 4), 5, new(38, 0, 100), 5, true);
            dry.BoolAdd(new Voxels(guides));

            Voxels pockets = Oval(new(0, -32, 62), Vector3.UnitZ, Vector3.UnitX, 34, 35, 23, 39, 26);
            pockets.BoolAdd(Oval(new(0, 32, 62), Vector3.UnitZ, Vector3.UnitX, 34, 35, 23, 39, 26));
            dry.BoolAdd(pockets);
            dry.Smoothen(.5f);
            Voxels protectedDry = dry.voxOffset(4.5f);

            // Conformal jacket: keep a nominal separation from every hot/dry reservation.
            Voxels water = gas.voxOffset(10);
            water.BoolSubtract(protectedDry);
            Voxels interior = body.voxOffset(-5);
            interior.BoolSubtract(pockets.voxOffset(5));
            water.BoolIntersect(interior);
            // Avoid the observed zero-level coincidence at z=54 on the 0.5 mm voxel grid.
            water.BoolIntersect(Sdf.Vox(lib, p => Sdf.Box(p, new(0, 0, 31.13f), new(70, 78, 23)),
                new(-80, -85, 0), new(80, 85, 65)));
            var feeds = new Lattice(lib);
            feeds.AddBeam(new(-84, 0, 24), 11, new(-39, 0, 24), 11, true);
            // Split around the secondary ignition keep-out instead of ending a blind feed behind it.
            feeds.AddBeam(new(60, 0, 24), 11, new(84, 0, 24), 11, false);
            var bridgeSkin = new Lattice(lib);
            foreach (float side in new[] { -1f, 1f })
            {
                feeds.AddBeam(new(60, 0, 24), 7, new(44, side * 24, 24), 7, true);
                bridgeSkin.AddBeam(new(60, 0, 24), 12, new(44, side * 24, 24), 12, true);
            }
            body.BoolAdd(new Voxels(bridgeSkin));
            water.BoolAdd(new Voxels(feeds));
            water.BoolSubtract(protectedDry);
            water.Smoothen(.25f);
            foreach (float side in new[] { -1f, 1f })
                body.BoolAdd(Oval(new(side * 45, 0, 24), new(side, 0, 0), Vector3.UnitY, 31, 16, 16, 16, 16));
            // The open necks are study terminals, with no fitted hose or thread geometry.
            water.BoolIntersect(Sdf.Vox(lib, p => MathF.Abs(p.X) - 76,
                new(-85, -90, -20), new(85, 90, 110)));
            if (s.P("export_mode") == 1) return water;
            if (s.P("export_mode") == 2) return dry;
            // Fair the exterior before subtraction so water walls are not displaced afterwards.
            AddRibs(lib, body);
            body.Smoothen(.25f);
            body.BoolSubtract(water); body.BoolSubtract(dry);
            return body;
        }
        finally { Library.UnregisterGlobalLibrary(); }
    }
}
