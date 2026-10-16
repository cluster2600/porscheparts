using System.Numerics;
using System.Text.Json;
using PicoGK;
using Leap71.ShapeKernel;

namespace PicoGKCatalog;

// Bionic derivative assumptions; bore changes the chamber and deck, never the complete head.
public static class HeadFamilyStudy
{
    public static Dictionary<string, float> Validate(JsonElement config)
    {
        if (config.GetProperty("status").GetString() != "unmeasured_bionic_family_study" ||
            string.IsNullOrWhiteSpace(config.GetProperty("id").GetString()) ||
            config.GetProperty("qualification").GetProperty("manufacturing_authorized").ValueKind != JsonValueKind.False ||
            config.GetProperty("qualification").EnumerateObject().Any(p => p.Value.ValueKind != JsonValueKind.False))
            throw new ArgumentException("Only unqualified bionic family studies are accepted.");
        string[] names = ["bore_mm", "chamber_depth_mm", "intake_valve_diameter_mm",
            "exhaust_valve_diameter_mm", "valve_x_mm", "valve_y_mm", "guide_top_y_mm",
            "throat_intake_mm", "throat_exhaust_mm"];
        var geometry = config.GetProperty("geometry");
        if (geometry.EnumerateObject().Count() != names.Length)
            throw new ArgumentException("Exactly the nine documented geometry assumptions are required.");
        Dictionary<string, float> g = new();
        foreach (string name in names)
        {
            double value = geometry.GetProperty(name).GetDouble();
            if (!double.IsFinite(value) || value <= 0 || value > float.MaxValue ||
                !float.IsNormal((float)value))
                throw new ArgumentException("Geometry assumptions must be positive finite normal numbers.");
            if (name == "bore_mm" && (value < 95 || value > 102))
                throw new ArgumentException("Bore must be between 95 and 102 mm before float conversion.");
            g.Add(name, (float)value);
        }
        float bore = g["bore_mm"], vx = g["valve_x_mm"], vy = g["valve_y_mm"];
        if (bore < 95 || bore > 102 || g["chamber_depth_mm"] >= 45 ||
            g["guide_top_y_mm"] <= vy + 3 || g["guide_top_y_mm"] >= 60 ||
            g["throat_intake_mm"] > g["intake_valve_diameter_mm"] ||
            g["throat_exhaust_mm"] > g["exhaust_valve_diameter_mm"] ||
            MathF.Sqrt(vx * vx + vy * vy) + MathF.Max(g["intake_valve_diameter_mm"],
                g["exhaust_valve_diameter_mm"]) / 2 >= bore / 2 - 2)
            throw new ArgumentException("Geometry exceeds the chamber or fixed body study envelope.");
        return g;
    }

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

    public static (Voxels Solid, Voxels Coolant, Voxels Dry) Build(Library lib, Dictionary<string, float> g)
    {
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
            body.BoolAdd(new BaseCylinder(new LocalFrame(), 12, g["bore_mm"] / 2 + 8).voxConstruct());

            float chamber = g["bore_mm"] / 2 - 2, depth = g["chamber_depth_mm"];
            Voxels gas = Sdf.Vox(lib, p => Sdf.SuperEllipsoid(p, new(0, 0, -1),
                new(chamber, chamber, depth), 2),
                new(-54, -54, -depth - 3), new(54, 54, depth + 2));
            using var branches = new Lattice(lib);
            float vx = g["valve_x_mm"], vy = g["valve_y_mm"];
            foreach (float side in new[] { -1f, 1f })
            {
                float seat = g[side < 0 ? "intake_valve_diameter_mm" : "exhaust_valve_diameter_mm"] / 2;
                float throat = g[side < 0 ? "throat_intake_mm" : "throat_exhaust_mm"] / 2;
                foreach (float x in new[] { -vx, vx })
                {
                    branches.AddBeam(new(x, side * vy, 6), seat, new(x, side * (vy + 4), 29), throat, true);
                    branches.AddBeam(new(x, side * (vy + 4), 29), throat, new(0, side * 60, 43), 12, true);
                }
                gas.BoolAdd(Oval(new(0, side * 54, 43), new(0, side, 0), Vector3.UnitX, 32, 23, 13, 25, 14));
                body.BoolAdd(Oval(new(0, side * 56, 43), new(0, side, 0), Vector3.UnitX, 19, 30, 20, 32, 21));
            }
            gas.BoolAdd(new Voxels(branches));
            Voxels dry = gas.voxOffset(0);
            using var guides = new Lattice(lib);
            foreach (float side in new[] { -1f, 1f })
                foreach (float x in new[] { -vx, vx })
                    guides.AddBeam(new(x, side * (vy + 3), 25), 3.5f,
                        new(x, side * g["guide_top_y_mm"], 100), 3.5f, true);
            guides.AddBeam(new(0, 0, 4), 6, new(0, 0, 100), 6, true);
            guides.AddBeam(new(38, 0, 4), 5, new(38, 0, 100), 5, true);
            dry.BoolAdd(new Voxels(guides));
            Voxels pockets = Oval(new(0, -32, 62), Vector3.UnitZ, Vector3.UnitX, 34, 35, 23, 39, 26);
            pockets.BoolAdd(Oval(new(0, 32, 62), Vector3.UnitZ, Vector3.UnitX, 34, 35, 23, 39, 26));
            dry.BoolAdd(pockets);
            dry.Smoothen(.5f);
            Voxels protectedDry = dry.voxOffset(4.5f);

            Voxels water = gas.voxOffset(10);
            water.BoolSubtract(protectedDry);
            Voxels interior = body.voxOffset(-5);
            interior.BoolSubtract(pockets.voxOffset(5));
            water.BoolIntersect(interior);
            // Preserve the prior non-coincident crop on the 0.5 mm voxel grid.
            water.BoolIntersect(Sdf.Vox(lib, p => Sdf.Box(p, new(0, 0, 31.13f), new(70, 78, 23)),
                new(-80, -85, 0), new(80, 85, 65)));
            using var feeds = new Lattice(lib);
            feeds.AddBeam(new(-84, 0, 24), 11, new(-39, 0, 24), 11, true);
            feeds.AddBeam(new(60, 0, 24), 11, new(84, 0, 24), 11, false);
            using var bridgeSkin = new Lattice(lib);
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
            water.BoolIntersect(Sdf.Vox(lib, p => MathF.Abs(p.X) - 76,
                new(-85, -90, -20), new(85, 90, 110)));
            AddRibs(lib, body);
            body.Smoothen(.25f);
            body.BoolSubtract(water); body.BoolSubtract(dry);
            return (body, water, dry);
        }
        finally { Library.UnregisterGlobalLibrary(); }
    }
}
