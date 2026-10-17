using System.Numerics;
using PicoGK;
using Leap71.ShapeKernel;

namespace PicoGKCatalog;

// Photo-informed architecture only; every dimension is a synthetic study assumption.
public sealed class Head962ArchitectureStudy : IPartGenerator
{
    public string Name => "962_photo_informed_head_architecture_study";

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
            body.BoolAdd(new BaseCylinder(new LocalFrame(), 12, 55).voxConstruct());

            Voxels gas = Sdf.Vox(lib, p => Sdf.SuperEllipsoid(p, new(0, 0, -1), new(45, 45, 13), 2),
                new(-50, -50, -16), new(50, 50, 15));
            var branches = new Lattice(lib);
            foreach (float side in new[] { -1f, 1f })
            {
                float radius = side < 0 ? 11 : 9;
                foreach (float x in new[] { -18f, 18f })
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
                foreach (float x in new[] { -18f, 18f })
                    guides.AddBeam(new(x, side * 25, 25), 3.5f, new(x, side * 39, 100), 3.5f, true);
            foreach (float x in new[] { -9f, 9f })
                guides.AddBeam(new(x, 0, 4), 3.5f, new(x, 0, 100), 3.5f, true);
            dry.BoolAdd(new Voxels(guides));
            Voxels protectedDry = dry.voxOffset(4.5f);

            Voxels pockets = Oval(new(0, -32, 62), Vector3.UnitZ, Vector3.UnitX, 34, 35, 23, 39, 26);
            pockets.BoolAdd(Oval(new(0, 32, 62), Vector3.UnitZ, Vector3.UnitX, 34, 35, 23, 39, 26));
            dry.BoolAdd(pockets);

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
            feeds.AddBeam(new(-70, 0, 20), 5, new(-39, 0, 20), 5, true);
            feeds.AddBeam(new(39, 0, 20), 5, new(70, 0, 20), 5, true);
            water.BoolAdd(new Voxels(feeds));
            water.BoolSubtract(protectedDry);
            foreach (float side in new[] { -1f, 1f })
                body.BoolAdd(Oval(new(side * 48, 0, 20), new(side, 0, 0), Vector3.UnitY, 16, 11, 11, 10, 10));
            // The open necks are study terminals, with no fitted hose or thread geometry.
            water.BoolIntersect(Sdf.Vox(lib, p => MathF.Abs(p.X) - 64,
                new(-75, -90, -20), new(75, 90, 110)));
            if (s.P("export_mode") == 1) return water;
            if (s.P("export_mode") == 2) return dry;
            body.BoolSubtract(water); body.BoolSubtract(dry);
            // Remove the four observed sub-voxel closed cavities from Boolean intersections.
            body.Smoothen(.25f);
            return body;
        }
        finally { Library.UnregisterGlobalLibrary(); }
    }
}
