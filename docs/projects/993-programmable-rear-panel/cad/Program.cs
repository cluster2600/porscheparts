// Visual concept only: no measured Porsche dimensions, mounting interfaces or release.
using System.Numerics;
using System.Security.Cryptography;
using System.Text.Json;
using System.Text.Json.Serialization;
using PicoGK;

var json = new JsonSerializerOptions {
    PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower,
    UnmappedMemberHandling = JsonUnmappedMemberHandling.Disallow,
    WriteIndented = true
};
try
{
    if (args.Length == 2 && args[0] == "--self-test")
    {
        var p = JsonSerializer.Deserialize<Parameters>(File.ReadAllText(args[1]), json)!;
        p.Validate();
        Tests.Run(p);
        Console.WriteLine("REAR_PANEL_PARAMETER_AND_FIELD_CHECKS_PASS");
        return 0;
    }
    if (args.Length != 2)
        throw new ArgumentException("Usage: RearPanel PARAMETERS.json NEW_OUTPUT_DIR | --self-test PARAMETERS.json");
    var parameters = JsonSerializer.Deserialize<Parameters>(File.ReadAllText(args[0]), json)!;
    parameters.Validate();
    string output = Path.GetFullPath(args[1]);
    if (Path.Exists(output))
        throw new IOException("Output already exists; refusing to overwrite.");
    Directory.CreateDirectory(output);
    using Library library = new(parameters.VoxelMm);
    var records = new List<object>();
    foreach (string part in new[] { "lens", "housing", "rear-cover", "display-envelope" })
    {
        var shape = new PanelField(parameters, part);
        BBox3 bounds = new(-parameters.WidthMm / 2 - 3 * parameters.VoxelMm,
            -parameters.BowMm - parameters.DepthMm - parameters.AssemblyGapMm - parameters.RearThicknessMm - 3 * parameters.VoxelMm,
            -parameters.HeightMm / 2 - 3 * parameters.VoxelMm,
            parameters.WidthMm / 2 + 3 * parameters.VoxelMm, 3 * parameters.VoxelMm,
            parameters.HeightMm / 2 + 3 * parameters.VoxelMm);
        using Voxels solid = new(library, shape, bounds);
        solid.CalculateProperties(out float volume, out BBox3 box);
        using Mesh mesh = new(solid);
        if (!float.IsFinite(volume) || volume <= 0 || mesh.nTriangleCount() == 0)
            throw new InvalidDataException("Empty or invalid geometry: " + part);
        string file = part + ".stl";
        mesh.SaveToStlFile(Path.Combine(output, file), Mesh.EStlUnit.MM);
        using Mesh reread = Mesh.mshFromStlFile(Path.Combine(output, file), Mesh.EStlUnit.MM, libSet: library);
        if (reread.nTriangleCount() != mesh.nTriangleCount())
            throw new InvalidDataException("STL roundtrip failed: " + part);
        records.Add(new {
            id = part, file, volume_mm3 = volume, triangles = mesh.nTriangleCount(),
            bounds_min_mm = new[] { box.vecMin.X, box.vecMin.Y, box.vecMin.Z },
            bounds_max_mm = new[] { box.vecMax.X, box.vecMax.Y, box.vecMax.Z },
            sha256 = Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(Path.Combine(output, file)))).ToLowerInvariant()
        });
        Console.WriteLine($"Exported {file}: {mesh.nTriangleCount()} triangles");
    }
    // Completion report is written last; meshes without it are an incomplete run.
    File.WriteAllText(Path.Combine(output, "geometry.json"), JsonSerializer.Serialize(new {
        status = "visual_concept_not_oem_not_for_manufacturing", units = "mm",
        axes = new { x = "width", y = "towards_front_face", z = "height" },
        parameters, parts = records,
        vehicle_interfaces = (object?)null, legal_optical_functions = (object?)null,
        hardware_resolution = (object?)null, is_fitment_validated = false,
        is_manufacturing_release = false, parameters_sha256 =
            Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(args[0]))).ToLowerInvariant()
    }, json) + "\n");
    Console.WriteLine("REAR_PANEL_VISUAL_CONCEPT_EXPORTED");
    return 0;
}
catch (Exception error)
{
    Console.Error.WriteLine(error.Message);
    return 1;
}

record Parameters
{
    public required string Status { get; init; }
    public required float WidthMm { get; init; }
    public required float HeightMm { get; init; }
    public required float DepthMm { get; init; }
    public required float BowMm { get; init; }
    public required float CornerRadiusMm { get; init; }
    public required float LensThicknessMm { get; init; }
    public required float WallMm { get; init; }
    public required float RearThicknessMm { get; init; }
    public required float AssemblyGapMm { get; init; }
    public required float DisplayMarginMm { get; init; }
    public required float OpticalGapMm { get; init; }
    public required float DisplayEnvelopeThicknessMm { get; init; }
    public required float VoxelMm { get; init; }

    public void Validate()
    {
        float[] positive = [WidthMm, HeightMm, DepthMm, CornerRadiusMm, LensThicknessMm,
            WallMm, RearThicknessMm, AssemblyGapMm, DisplayMarginMm, OpticalGapMm,
            DisplayEnvelopeThicknessMm, VoxelMm];
        if (Status != "visual_concept_provisional_dimensions" ||
            positive.Any(x => !float.IsFinite(x) || x <= 0) || !float.IsFinite(BowMm) || BowMm < 0)
            throw new ArgumentException("Explicit provisional status and finite positive dimensions required.");
        if (VoxelMm < 0.5f || VoxelMm > 2 || WidthMm > 1600 || HeightMm > 200 || DepthMm > 120 ||
            BowMm > WidthMm / 8 || WidthMm < 2 * HeightMm ||
            CornerRadiusMm >= HeightMm / 2 || CornerRadiusMm <= WallMm ||
            DisplayMarginMm <= WallMm + AssemblyGapMm || HeightMm - 2 * DisplayMarginMm < 4 * VoxelMm ||
            new[] { LensThicknessMm, WallMm, RearThicknessMm, DisplayEnvelopeThicknessMm }.Any(x => x / VoxelMm < 3 - 1e-5f) ||
            AssemblyGapMm < VoxelMm || OpticalGapMm < AssemblyGapMm ||
            LensThicknessMm + OpticalGapMm + DisplayEnvelopeThicknessMm + AssemblyGapMm >= DepthMm)
            throw new ArgumentException("Invalid geometry, insufficient clearance, or under-resolved walls.");
        double cells = (double)WidthMm * HeightMm * (DepthMm + BowMm + RearThicknessMm) / Math.Pow(VoxelMm, 3);
        if (cells > 30_000_000)
            throw new ArgumentException("Preview voxel budget exceeded; increase voxel size and wall thickness consistently.");
    }
}

sealed class PanelField(Parameters p, string part) : IImplicit
{
    public float fSignedDistance(in Vector3 point)
    {
        float bow = -p.BowMm * MathF.Pow(2 * point.X / p.WidthMm, 2);
        float depth = point.Y - bow;
        float outer = Outline(point.X, point.Z, p.WidthMm, p.HeightMm, p.CornerRadiusMm);
        // shortcut: warped implicit preserves the concept surface, not exact normal wall thickness; review after metrology.
        return part switch {
            "lens" => MathF.Max(outer, Slab(depth, -p.LensThicknessMm, 0)),
            "housing" => MathF.Max(MathF.Max(outer,
                -Outline(point.X, point.Z, p.WidthMm - 2 * p.WallMm, p.HeightMm - 2 * p.WallMm, p.CornerRadiusMm - p.WallMm)),
                Slab(depth, -p.DepthMm, -p.LensThicknessMm - p.AssemblyGapMm)),
            "rear-cover" => MathF.Max(outer,
                Slab(depth, -p.DepthMm - p.AssemblyGapMm - p.RearThicknessMm, -p.DepthMm - p.AssemblyGapMm)),
            "display-envelope" => MathF.Max(
                Outline(point.X, point.Z, p.WidthMm - 2 * p.DisplayMarginMm,
                    p.HeightMm - 2 * p.DisplayMarginMm, MathF.Max(p.VoxelMm, p.CornerRadiusMm - p.DisplayMarginMm)),
                Slab(depth, -p.LensThicknessMm - p.OpticalGapMm - p.DisplayEnvelopeThicknessMm,
                    -p.LensThicknessMm - p.OpticalGapMm)),
            _ => throw new ArgumentException("Unknown part")
        };
    }
    static float Slab(float value, float lower, float upper) => MathF.Max(lower - value, value - upper);
    static float Outline(float x, float z, float width, float height, float radius)
    {
        Vector2 q = Vector2.Abs(new(x, z)) - new Vector2(width / 2 - radius, height / 2 - radius);
        return Vector2.Max(q, Vector2.Zero).Length() + MathF.Min(MathF.Max(q.X, q.Y), 0) - radius;
    }
}

static class Tests
{
    public static void Run(Parameters p)
    {
        void Check(bool value) { if (!value) throw new InvalidDataException("Field self-test failed"); }
        foreach (var invalid in new[] { p with { WidthMm = float.NaN }, p with { BowMm = -1 },
            p with { Status = "measured" }, p with { WallMm = 0.1f }, p with { AssemblyGapMm = 0 },
            p with { DisplayMarginMm = p.HeightMm }, p with { OpticalGapMm = p.DepthMm },
            p with { CornerRadiusMm = p.HeightMm } })
        {
            bool rejected = false;
            try { invalid.Validate(); } catch (ArgumentException) { rejected = true; }
            Check(rejected);
        }
        foreach (float x in new[] { 0f, p.WidthMm / 4 })
        {
            float bow = -p.BowMm * MathF.Pow(2 * x / p.WidthMm, 2);
            Vector3[] inside = [new(x, bow - p.LensThicknessMm / 2, 0),
                new(x, bow - (p.DepthMm + p.LensThicknessMm + p.AssemblyGapMm) / 2, p.HeightMm / 2 - p.WallMm / 2),
                new(x, bow - p.DepthMm - p.AssemblyGapMm - p.RearThicknessMm / 2, 0),
                new(x, bow - p.LensThicknessMm - p.OpticalGapMm - p.DisplayEnvelopeThicknessMm / 2, 0)];
            string[] parts = ["lens", "housing", "rear-cover", "display-envelope"];
            for (int i = 0; i < parts.Length; i++)
                for (int j = 0; j < parts.Length; j++)
                    Check((new PanelField(p, parts[i]).fSignedDistance(inside[j]) < 0) == (i == j));
            Check(new PanelField(p, "housing").fSignedDistance(new(x, bow - p.DepthMm / 2, 0)) > 0);
        }
    }
}
