using System.Numerics;
using PicoGK;
using PicoGKCatalog;

static class HotSide
{
    // shortcut: all dimensions and clearances are concept hypotheses, replace after donor metrology and engineering review.
    public static void Build(Library lib, Action<string, string, Voxels, Vector3> save)
    {
        Vector3 polar(float r, float a, float z) => new(r * MathF.Cos(a), r * MathF.Sin(a), z);
        float cylinderX(Vector3 p, float y, float z, float r, float a, float b) =>
            RotKit.Rod(p, new(a, y, z), new(b, y, z), r);
        float cylinderY(Vector3 p, float x, float z, float r, float a, float b) =>
            RotKit.Rod(p, new(x, a, z), new(x, b, z), r);
        void emit(string id, string label, Func<Vector3, float> field, Vector3 min, Vector3 max, Vector3 offset)
        {
            using Voxels solid = Sdf.Vox(lib, field, min, max);
            solid.Smoothen(.5f);
            save(id, label, solid, offset);
        }
        float exhaust(Vector3 p)
        {
            float r = float.Lerp(19, 29.75f, Math.Clamp((p.Z + 117.25f) / 6, 0, 1));
            return MathF.Max(RotKit.R(p) - r, MathF.Max(-150.25f - p.Z, p.Z + 84.25f));
        }
        float outer(Vector3 p) => MathF.Min(Sdf.CylZ(p, 0, 0, 34.25f, -116.25f, -86.75f),
            MathF.Min(Sdf.CylZ(p, 0, 0, 23.25f, -141.25f, -108.25f),
            MathF.Min(Sdf.CylZ(p, 0, 0, 29, -142.75f, -137.25f),
            MathF.Min(cylinderY(p, 43, -99.75f, 17, -2, 56.25f),
                cylinderY(p, 43, -99.75f, 22, 53.25f, 58.25f)))));
        float inner(Vector3 p) => MathF.Min(exhaust(p),
            MathF.Min(Sdf.CylZ(p, 0, 0, 43, -102.75f, -96.75f),
                cylinderY(p, 43, -99.75f, 13, -3, 68)));
        Vector3 minimum = new(-65, -65, -151), maximum = new(70, 70, -80);
        using Voxels housing = Sdf.Vox(lib, outer, minimum, maximum);
        using Voxels flow = Sdf.Vox(lib, inner, minimum, maximum);
        foreach (bool outside in new[] { false, true })
        {
            using Lattice scroll = new(lib);
            for (int i = 0; i < 128; ++i)
            {
                float t0 = i / 128f, t1 = (i + 1) / 128f, extra = outside ? 4 : 0;
                scroll.AddBeam(polar(43, MathF.Tau * t0, -99.75f), 5 + 8 * t0 + extra,
                    polar(43, MathF.Tau * t1, -99.75f), 5 + 8 * t1 + extra);
            }
            using Voxels scrollSolid = new(scroll);
            (outside ? housing : flow).BoolAdd(scrollSolid);
        }
        // The bypass has an explicit small seat above an enlarged flapper chamber.
        Vector3[] bypass = { new(43, 30, -99.75f), new(31, 26, -107), new(24, 18, -116.25f) };
        foreach (bool outside in new[] { false, true })
        {
            using Lattice duct = new(lib);
            for (int i = 0; i + 1 < bypass.Length; ++i)
                duct.AddBeam(bypass[i], outside ? 11 : 7, bypass[i + 1], outside ? 11 : 7);
            using Voxels ductSolid = new(duct);
            (outside ? housing : flow).BoolAdd(ductSolid);
            using Voxels chamber = Sdf.Vox(lib, p => MathF.Max(Sdf.Capsule(p,
                new(24, 18, -132), new(0, 0, -132), outside ? 19.125f : 15.125f),
                MathF.Max((outside ? -143.75f : -141.25f) - p.Z, p.Z + (outside ? 121.25f : 125.25f))),
                minimum, maximum);
            (outside ? housing : flow).BoolAdd(chamber);
            using Voxels seat = Sdf.Vox(lib, p => Sdf.CylZ(p, 24, 18, outside ? 11 : 7,
                -127.25f, -114.25f), minimum, maximum);
            (outside ? housing : flow).BoolAdd(seat);
        }
        using Lattice ribs = new(lib);
        for (int i = 0; i < 6; ++i)
        {
            float a = MathF.Tau * (i + .4f) / 6;
            Vector3 root = polar(22.5f, a, -126), fork = polar(34, a + .07f, -113);
            ribs.AddBeam(root, 2.5f, fork, 2);
            ribs.AddBeam(fork, 2, polar(43, a - .12f, -108), 1.7f);
            ribs.AddBeam(fork, 2, polar(43, a + .2f, -108), 1.7f);
        }
        using Voxels ribsSolid = new(ribs);
        housing.BoolAdd(ribsSolid);
        housing.BoolSubtract(flow);
        using Voxels pivotBore = Sdf.Vox(lib, p => cylinderY(p, 38, -128, 4.8f, 15, 45), minimum, maximum);
        housing.BoolSubtract(pivotBore);
        housing.Smoothen(.5f);
        foreach (Vector3 point in new[] { new Vector3(43, 54, -99.75f), new(0, 0, -139),
            new(24, 18, -120), new(24, 18, -125), new(24, 18, -132), new(31, 26, -107) })
            if (housing.bIsInside(point) || !flow.bIsInside(point))
                throw new InvalidDataException($"Blocked conceptual hot-side passage at {point}.");
        save("turbine-housing", "Carter turbine bionique et dérivation de wastegate", housing, new(0, 0, -120));

        emit("wastegate-flapper", "Clapet et bras de wastegate",
            p => MathF.Max(MathF.Min(Sdf.CylZ(p, 24, 18, 9.5f, -129.25f, -126.75f),
                MathF.Min(RotKit.Rod(p, new(24, 18, -128), new(38, 18, -128), 2),
                    cylinderY(p, 38, -128, 4.5f, 16.25f, 20.25f))),
                -cylinderY(p, 38, -128, 2.7f, 14, 23)),
            new(12, 6, -135), new(45, 30, -121), new(40, -30, -50));
        emit("wastegate-pivot-lever", "Axe et levier de wastegate",
            p => MathF.Min(cylinderY(p, 38, -128, 2.2f, 17.25f, 50.25f),
                MathF.Min(RotKit.Rod(p, new(38, 41, -128), new(61, 41, -119), 3),
                    cylinderY(p, 61, -119, 2.2f, 39.25f, 52.25f))),
            new(33, 14, -133), new(66, 56, -114), new(55, 45, -35));
        emit("wastegate-pivot-bushing", "Bague de pivot de wastegate",
            p => MathF.Max(cylinderY(p, 38, -128, 4.5f, 25.25f, 37.25f),
                -cylinderY(p, 38, -128, 2.8f, 23, 39)),
            new(31, 22, -135), new(45, 40, -121), new(45, 28, -30));
        emit("wastegate-pivot-clip", "Rondelle de retenue du pivot",
            p => MathF.Max(cylinderY(p, 38, -128, 4.5f, 44.75f, 46.75f),
                -cylinderY(p, 38, -128, 2.5f, 43, 48)),
            new(31, 42, -135), new(45, 49, -121), new(45, 68, -30));
        emit("wastegate-actuator-rod", "Tige et œillet d’actionneur",
            p => MathF.Max(MathF.Min(Sdf.CylZ(p, 61, 47, 2.2f, -117.25f, -57.75f),
                    cylinderY(p, 61, -119, 5.2f, 44.25f, 49.75f)),
                -cylinderY(p, 61, -119, 2.8f, 42, 52)),
            new(53, 39, -127), new(69, 55, -54), new(70, 45, 0));

        float lowerCup(Vector3 p) => MathF.Max(MathF.Min(
            Sdf.CylZ(p, 61, 47, 14, -75.25f, -53.25f), Sdf.CylZ(p, 61, 47, 16, -55.25f, -53.25f)),
            -MathF.Min(Sdf.CylZ(p, 61, 47, 11, -72.25f, -50), Sdf.CylZ(p, 61, 47, 3.8f, -79, -69)));
        emit("wastegate-actuator-lower-cup", "Coupelle inférieure d’actionneur",
            lowerCup, new(42, 28, -79), new(80, 66, -49), new(78, 50, 12));
        float upperCup(Vector3 p) => MathF.Max(MathF.Min(Sdf.CylZ(p, 61, 47, 14, -50.25f, -35.25f),
                MathF.Min(Sdf.CylZ(p, 61, 47, 16, -50.25f, -48.25f),
                    Sdf.CylZ(p, 61, 47, 3.5f, -37.25f, -28.25f))),
            -MathF.Min(Sdf.CylZ(p, 61, 47, 11, -54, -38.25f), Sdf.CylZ(p, 61, 47, 1.75f, -41, -25)));
        emit("wastegate-actuator-upper-cup", "Coupelle supérieure et prise de pression",
            upperCup, new(42, 28, -54), new(80, 66, -25), new(78, 50, 68));
        emit("wastegate-actuator-diaphragm", "Membrane et plateau d’actionneur, enveloppe conceptuelle",
            p => MathF.Min(Sdf.CylZ(p, 61, 47, 14.75f, -52.75f, -50.75f),
                Sdf.CylZ(p, 61, 47, 5, -58.25f, -49.75f)),
            new(43, 29, -62), new(79, 65, -46), new(78, 50, 44));
        using Lattice coil = new(lib);
        Vector3 spring(float t) => new(61 + 7 * MathF.Cos(MathF.Tau * 3 * t),
            47 + 7 * MathF.Sin(MathF.Tau * 3 * t), -70.75f + 14 * t);
        for (int i = 0; i < 120; ++i) coil.AddBeam(spring(i / 120f), 1.15f, spring((i + 1) / 120f), 1.15f);
        using Voxels springSolid = new(coil);
        save("wastegate-actuator-spring", "Ressort de rappel, raideur non définie", springSolid, new(78, 50, 28));

        float bracketHoles(Vector3 p) => MathF.Min(cylinderX(p, -7, -65, 2.75f, 20, 33),
            MathF.Min(cylinderX(p, 7, -65, 2.75f, 20, 33), Sdf.CylZ(p, 61, 47, 4, -84, -72)));
        float bracket(Vector3 p) => MathF.Max(MathF.Min(Sdf.Box(p, new(25.5f, 0, -65), new(3, 13, 8)),
            MathF.Min(Sdf.CylZ(p, 61, 47, 16, -80.25f, -76.25f),
            MathF.Min(RotKit.Rod(p, new(26, 10, -69), new(53, 41, -78), 4),
                RotKit.Rod(p, new(26, -10, -69), new(67, 36, -78), 4)))), -bracketHoles(p));
        emit("wastegate-actuator-bracket", "Support d’actionneur à deux branches",
            bracket, new(19, -17, -85), new(81, 67, -54), new(60, 35, -10));
        for (int i = 0; i < 2; ++i)
        {
            float y = i == 0 ? -7 : 7;
            emit($"wastegate-bracket-bolt-{i + 1}", $"Vis de support d’actionneur {i + 1}, sans filetage",
                p => MathF.Min(cylinderX(p, y, -65, 2.1f, 17.5f, 31), cylinderX(p, y, -65, 4.5f, 29.25f, 32.25f)),
                new(14, y - 7, -72), new(36, y + 7, -58), new(85, i == 0 ? -5 : 10, -5));
        }
    }
}
