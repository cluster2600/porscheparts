using System.Numerics;
using PicoGK;
using PicoGKCatalog;

// Editable display assumptions in mm; no K16 interface, tolerance, thread or load-path qualification.
public static class Components
{
    public static void Build(Library lib, Action<string, string, Voxels, Vector3> save)
    {
        const float shaftRadius = 4, clearanceBore = 4.8f;
        float Cyl(Vector3 q, float radius, float z0, float z1) => Sdf.CylZ(q, 0, 0, radius, z0, z1);
        float Ring(Vector3 q, float inner, float outer, float z0, float z1) =>
            MathF.Max(Cyl(q, outer, z0, z1), inner - RotKit.R(q));
        void Emit(string id, string label, Func<Vector3, float> field, Vector3 min, Vector3 max, Vector3 explode)
        {
            using Voxels solid = Sdf.Vox(lib, field, min - Vector3.One, max + Vector3.One);
            solid.Smoothen(.5f);
            save(id, label, solid, explode);
        }
        void Annulus(string id, string label, float inner, float outer, float z0, float z1, Vector3 explode) =>
            Emit(id, label, q => Ring(q, inner, outer, z0, z1), new(-outer, -outer, z0), new(outer, outer, z1), explode);
        PartSpec Spec(string id, string generator, params (string key, float value)[] values) => new()
        {
            PartId = id, Generator = generator, VoxelMm = .5f, Status = "assembly_concept_only",
            SafetyClass = "prohibited_pending_engineering", MaterialCandidate = "undetermined",
            Parameters = values.ToDictionary(v => v.key, v => new Param(v.value,
                v.key.EndsWith("_count") ? "count" : v.key.EndsWith("_deg") ? "deg" : v.key.EndsWith("exponent") ? "1" : "mm",
                "assumption", null, "Display assembly design variable; not a measured K16 dimension."))
        };
        var compressor = Spec("compressor-wheel", "k16_compressor_wheel",
            ("exducer_diameter_mm", 60.5f), ("inducer_diameter_mm", 40.6f), ("total_height_mm", 28),
            ("backplate_thickness_mm", 3), ("bore_diameter_mm", 9.6f), ("hub_top_radius_mm", 8),
            ("inducer_hub_diameter_mm", 17), ("splitter_inner_radius_mm", 18), ("leading_edge_z_mm", 24),
            ("exit_blade_width_mm", 4.5f), ("main_blade_count", 6), ("splitter_blade_count", 6),
            ("inducer_wrap_deg", 24), ("exit_backsweep_wrap_deg", 14), ("main_root_thickness_mm", 3),
            ("main_tip_thickness_mm", 2), ("splitter_root_thickness_mm", 2.8f), ("splitter_tip_thickness_mm", 2),
            ("root_fillet_mm", 1), ("hub_profile_exponent", 1.5f));
        var turbine = Spec("turbine-wheel", "k16_turbine_wheel",
            ("inducer_diameter_mm", 54.96f), ("exducer_diameter_mm", 48.97f), ("total_height_mm", 25),
            ("backface_thickness_mm", 4), ("tip_height_mm", 8), ("shaft_diameter_mm", 8),
            ("exducer_hub_radius_mm", 7), ("exducer_plane_z_mm", 23), ("blade_count", 12),
            ("blade_root_thickness_mm", 3), ("blade_tip_thickness_mm", 2), ("exducer_wrap_deg", 38),
            ("backface_scallop_depth_mm", 3.5f), ("root_fillet_mm", 1), ("hub_profile_exponent", 1.6f));
        void Wheel(string id, string label, IPartGenerator generator, PartSpec spec, Matrix4x4 transform, Vector3 explode)
        {
            using Voxels local = generator.Build(lib, spec);
            using Mesh mesh = new(local);
            using Mesh moved = mesh.mshCreateTransformed(transform);
            using Voxels placed = new(moved);
            if (id == "turbine-wheel")
            {
                using Voxels socket = Sdf.Vox(lib, q => Cyl(q, 4.8f, -91.5f, -85), new(-6, -6, -93), new(6, 6, -84));
                placed.BoolSubtract(socket);
            }
            placed.Smoothen(.5f);
            save(id, label, placed, explode);
        }
        Wheel("compressor-wheel", "Compressor wheel — assumed blade surfaces", new CompressorWheel(), compressor,
            Matrix4x4.CreateTranslation(0, 0, -3), new(0, 0, 70));
        Wheel("turbine-wheel", "Turbine wheel — assumed blade surfaces", new TurbineWheel(), turbine,
            Matrix4x4.CreateRotationX(MathF.PI) * Matrix4x4.CreateTranslation(0, 0, -87), new(0, 0, -65));
        Emit("shaft", "Shaft — no thread or weld definition", q => Cyl(q, shaftRadius, -90, 32),
            new(-5, -5, -91), new(5, 5, 33), new(-50, 0, 0));

        Vector3 BoltCenter(int i) => new(26 * MathF.Cos(MathF.Tau * i / 6), 26 * MathF.Sin(MathF.Tau * i / 6), 0);
        float BoltHoles(Vector3 q)
        {
            float holes = float.PositiveInfinity;
            for (int i = 0; i < 6; ++i) holes = MathF.Min(holes, Sdf.CylZ(q, BoltCenter(i).X, BoltCenter(i).Y, 2.6f, -21, -3));
            return holes;
        }
        float Chra(Vector3 q)
        {
            float outer = MathF.Min(Cyl(q, 22, -80, -13), MathF.Min(Cyl(q, 28, -80, -77), Cyl(q, 31, -16, -13)));
            outer = RotKit.SMin(outer, RotKit.Rod(q, new(0, 18, -48), new(0, 30, -48), 6), 1.5f);
            outer = RotKit.SMin(outer, RotKit.Rod(q, new(0, -31, -48), new(0, -18, -48), 8), 1.5f);
            float voids = MathF.Min(Cyl(q, 10.5f, -82, -11), Cyl(q, 15, -21, -11));
            voids = MathF.Min(voids, RotKit.Rod(q, new(0, 0, -48), new(0, 33, -48), 3));
            voids = MathF.Min(voids, RotKit.Rod(q, new(0, -34, -48), new(0, 0, -48), 5));
            foreach (float y in new[] { -7f, 7f })
                voids = MathF.Min(voids, RotKit.Rod(q, new(17, y, -65), new(25, y, -65), 2.75f));
            return MathF.Max(outer, -MathF.Min(voids, BoltHoles(q)));
        }
        Emit("chra-housing", "CHRA bearing housing with open feed and drain", Chra,
            new(-33, -34, -82), new(33, 33, -11), new(0, 0, -12));
        Annulus("journal-bearing-front", "Front journal bearing — assumed clearance", clearanceBore, 9.5f, -36, -24, new(-35, -30, 14));
        Annulus("journal-bearing-rear", "Rear journal bearing — assumed clearance", clearanceBore, 9.5f, -70, -58, new(-35, 30, -14));
        Annulus("thrust-bearing", "Thrust bearing — no oil-film design", 10.6f, 14, -20, -17, new(30, -30, 15));
        Emit("thrust-collar", "Thrust collar — assumed shoulder", q =>
            MathF.Min(Ring(q, clearanceBore, 9.8f, -20, -14), Ring(q, clearanceBore, 13.5f, -16.5f, -14)),
            new(-15, -15, -22), new(15, 15, -12), new(35, 0, 20));
        Annulus("seal-sleeve-front", "Front seal sleeve", clearanceBore, 7.2f, -13, -8, new(30, 30, 25));
        Annulus("seal-sleeve-rear", "Rear seal sleeve", clearanceBore, 7.2f, -83, -75, new(30, 30, -30));
        foreach (bool front in new[] { true, false })
        {
            float z0 = front ? -12 : -79;
            Emit(front ? "seal-ring-front" : "seal-ring-rear", "Split seal ring — no sealing qualification",
                q => MathF.Max(Ring(q, 7.7f, 9.8f, z0, z0 + 2), -Sdf.Box(q, new(10, 0, z0 + 1), new(4, 1.2f, 3))),
                new(-11, -11, z0 - 1), new(11, 11, z0 + 3), new(50, front ? 30 : -30, front ? 25 : -30));
        }
        Emit("compressor-backplate", "Compressor backplate — unmeasured rear interface", q =>
            MathF.Max(MathF.Min(Ring(q, 8.5f, 33.2f, -8.5f, -4), Ring(q, 10.5f, 18, -13, -8.3f)), -BoltHoles(q)),
            new(-35, -35, -15), new(35, 35, -2), new(0, 0, 30));
        Annulus("heat-shield", "Turbine heat shield — unqualified thickness/material", 9, 32, -86, -83, new(0, 0, -40));
        Annulus("compressor-retention-ring", "Compressor retention ring — schematic engagement", 30, 37, -11.5f, -8.5f, new(0, 0, 15));
        Annulus("turbine-retention-ring", "Turbine retention ring — schematic engagement", 22, 28, -83, -80, new(0, 0, -28));
        Emit("compressor-nut", "Compressor nut — unthreaded display geometry", q =>
        {
            float hex = float.NegativeInfinity;
            for (int i = 0; i < 6; ++i) hex = MathF.Max(hex, q.X * MathF.Cos(MathF.Tau * i / 6) + q.Y * MathF.Sin(MathF.Tau * i / 6) - 7);
            return MathF.Max(MathF.Max(hex, MathF.Max(25.5f - q.Z, q.Z - 31.5f)), clearanceBore - RotKit.R(q));
        }, new(-9, -9, 24), new(9, 9, 33), new(0, 0, 94));
        for (int i = 0; i < 6; ++i)
        {
            Vector3 c = BoltCenter(i);
            Emit($"backplate-bolt-{i + 1}", "Backplate fastener — unthreaded display geometry", q =>
                MathF.Min(Sdf.CylZ(q, c.X, c.Y, 1.6f, -16.3f, -4.7f), Sdf.CylZ(q, c.X, c.Y, 3.6f, -19.5f, -16)),
                c + new Vector3(-5, -5, -21), c + new Vector3(5, 5, -3), new(c.X * .7f, c.Y * .7f, 12));
        }
        foreach (bool feed in new[] { true, false })
        {
            Vector3 a = new(0, feed ? 30 : -46, -48), b = new(0, feed ? 43 : -31, -48);
            float outer = feed ? 6 : 8, inner = feed ? 3 : 5;
            Emit(feed ? "oil-feed-union" : "oil-drain-union", feed ? "Open oil feed union — no thread" : "Open oil drain union — no thread",
                q => MathF.Max(RotKit.Rod(q, a, b, outer), -RotKit.Rod(q, a - new Vector3(0, 2, 0), b + new Vector3(0, 2, 0), inner)),
                Vector3.Min(a, b) - new Vector3(outer), Vector3.Max(a, b) + new Vector3(outer), new(0, feed ? 35 : -35, 0));
        }
    }
}
