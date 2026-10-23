using System.Numerics;
using System.Text.Json.Nodes;
using PicoGK;

namespace PicoGKCatalog;

/// Skin + gyroid core on a part's published PicoGK body. The params file is
/// source/gyroid.json: a PartSpec whose "parameters" hold the core settings
/// (all basis "assumption"), plus "base", "keep_solid" and "recut_void".
///
/// 1. The base body is the part's published model (bionic_topology or its own
///    generator), read from the repository and checked against its SHA-256.
/// 2. Exact functional features of bionic.json are re-applied: "solid" shapes
///    added, "void" shapes (bores, passages) cut at their size.
/// 3. The core region is the body shrunk by the skin, minus a solid ring of
///    skin + 2 mm around every void (and minus the solid shapes themselves when
///    "keep_bionic_solids" is true), then morphologically opened by 1.5 cells:
///    wherever the region is thinner than three cells it stays solid.
/// 4. The region is hollowed and refilled with a sheet gyroid of even wall
///    (distance normalized by the local gradient) that overlaps the skin by one
///    wall, so the core and skin are one body.
/// 5. Drain ports are drilled from the core to the nearest outer surface, then
///    the body is re-voxelized from its mesh: any pocket the drains do not
///    reach is filled solid, so no sealed void (trapped powder) remains.
public sealed class GyroidCore : IPartGenerator
{
    public string Name => "gyroid_core";

    public Voxels Build(Library lib, PartSpec spec)
    {
        // Same convention as BionicTopology: <exe> <params.json> <out-dir>.
        string paramsPath = Environment.GetCommandLineArgs().Skip(1)
            .First(a => a.EndsWith(".json", StringComparison.OrdinalIgnoreCase));
        string sourceDir = Path.GetDirectoryName(Path.GetFullPath(paramsPath))!;
        string root = Path.GetFullPath(Path.Combine(sourceDir, "..", "..", ".."));
        JsonNode cfg = JsonNode.Parse(File.ReadAllText(paramsPath))!;
        string id = spec.PartId;

        string basePath = Path.Combine(root, cfg["base"]!["stl"]!.GetValue<string>());
        string want = cfg["base"]!["sha256"]!.GetValue<string>();
        string got = Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(File.ReadAllBytes(basePath))).ToLowerInvariant();
        if (got != want) throw new InvalidDataException($"base {basePath}: sha256 {got} != {want}");
        Sdf.Stage(id, "base");
        Voxels body = new(Mesh.mshFromStlFile(basePath, libSet: lib));
        float smooth = cfg["base"]?["smooth_mm"]?.GetValue<float>() ?? 0f;   // organic rounding of a non-bionic base
        if (smooth > 0) body.Smoothen(smooth);

        // Exact features from bionic.json, when the part has one.
        string bioPath = Path.Combine(sourceDir, "bionic.json");
        List<JsonNode> solids = new(), voids = new();
        if (File.Exists(bioPath) && cfg["reapply_bionic_features"]?.GetValue<bool>() != false)
        {
            JsonNode opt = JsonNode.Parse(File.ReadAllText(bioPath))!["optimization"]!;
            foreach (JsonNode? s in opt["solid"]?.AsArray() ?? new JsonArray())
                if (s!["analysis_only"]?.GetValue<bool>() != true) solids.Add(s);
            foreach (JsonNode? s in opt["void"]?.AsArray() ?? new JsonArray()) voids.Add(s!);
        }
        foreach (JsonNode? s in cfg["keep_solid"]?.AsArray() ?? new JsonArray()) solids.Add(s!);
        foreach (JsonNode? s in cfg["recut_void"]?.AsArray() ?? new JsonArray()) voids.Add(s!);
        // bionic.json "solid" shapes are design-domain constraints of the
        // optimization (bosses, grip cores, flanges): they take a core unless
        // the part asks to keep them solid. Material around voids always stays.
        bool keepSolids = cfg["keep_bionic_solids"]?.GetValue<bool>() == true;
        Voxels keep = new(lib), ring = new(lib);
        foreach (JsonNode s in solids)
        {
            Voxels f = BionicTopology.Shape(lib, s, root);
            body.BoolAdd(f);
            if (keepSolids) keep.BoolAdd(f);
        }
        foreach (JsonNode s in voids) ring.BoolAdd(BionicTopology.Shape(lib, s, root));

        float cell = spec.P("cell_mm"), wall = spec.P("wall_mm"), skin = spec.P("skin_mm");
        float minCells = spec.P("min_cells"), drainD = spec.P("drain_d_mm");
        int maxDrains = spec.N("max_drains");

        Sdf.Stage(id, "core region");
        Voxels region = body.voxOffset(-skin);
        region.BoolSubtract(keep.voxOffset(skin));
        region.BoolSubtract(ring.voxOffset(skin + 2f));
        float open = 0.5f * minCells * cell;
        region = region.voxDoubleOffset(-open, open);      // thinner than min_cells: stays solid
        region.BoolIntersect(body.voxOffset(-skin));       // the opening may grow past the skin
        // Solid counterpart of the cored part: same features, voids cut, no core.
        Voxels solidRef = new(body);
        foreach (JsonNode s in voids) solidRef.BoolSubtract(BionicTopology.Shape(lib, s, root));
        float bodyVol = MeshVol(solidRef), regionVol = Sdf.Vol(region);
        Console.Error.WriteLine($"  [{id}] body {bodyVol:F2} cm3, core region {regionVol:F2} cm3");
        var stats = new Dictionary<string, object> {
            ["cell_mm"] = cell, ["wall_mm"] = wall, ["skin_mm"] = skin, ["min_cells"] = minCells,
            ["drain_d_mm"] = drainD, ["solid_cm3"] = Math.Round(bodyVol, 2), ["core_region_cm3"] = Math.Round(regionVol, 2) };
        if (regionVol <= 0.001f)
        {
            Console.Error.WriteLine($"  [{id}] no zone holds {minCells} cells of {cell} mm: body stays solid");
            foreach (JsonNode s in voids) body.BoolSubtract(BionicTopology.Shape(lib, s, root));
            stats["cored"] = false;
            stats["drains"] = 0;
            WriteStats(id, stats);
            return body;
        }

        Sdf.Stage(id, "gyroid");
        BBox3 rb = region.oCalculateBoundingBox();
        Vector3 pad = new(cell);
        Voxels gyroid = Sdf.Vox(lib, p => GyroidSheet(p, cell, wall), rb.vecMin - pad, rb.vecMax + pad);
        gyroid.BoolIntersect(region.voxOffset(wall));      // overlap the skin: one body
        Voxels outer = new(body);                          // drains aim at the outer skin, not the sheet
        body.BoolSubtract(region);
        body.BoolAdd(gyroid);

        Sdf.Stage(id, "drains");
        int drains = DrillDrains(lib, body, outer, region, keep, cell, skin, drainD, maxDrains);
        foreach (JsonNode s in voids) body.BoolSubtract(BionicTopology.Shape(lib, s, root));

        // Fill every pocket the drains do not reach: voxelizing a mesh fills
        // fully enclosed cavities, which is exactly a sealed-void fill.
        Sdf.Stage(id, "fill sealed pockets");
        float before = MeshVol(body);                      // mesh volume: counts enclosed voids
        body = new Voxels(body.mshAsMesh());
        float after = MeshVol(body);
        Console.Error.WriteLine($"  [{id}] cell {cell} mm, wall {wall} mm, skin {skin} mm, {drains} drains; " +
                                $"solid {bodyVol:F2} -> cored {after:F2} cm3, sealed pockets filled {after - before:F2} cm3");
        stats["cored"] = true;
        stats["drains"] = drains;
        stats["cored_cm3"] = Math.Round(after, 2);
        stats["sealed_pockets_filled_cm3"] = Math.Round(after - before, 2);
        stats["mass_saving_pct"] = Math.Round(100.0 * (1.0 - after / bodyVol), 1);
        WriteStats(id, stats);
        return body;
    }

    /// Sheet gyroid of period cell and thickness t. Sdf.GyroidSheet scales |g|
    /// by its maximum gradient, which thickens the sheet up to threefold where
    /// the gradient is small and pinches the channels shut (sealed pockets);
    /// dividing by the local gradient gives a first-order distance and an even
    /// wall.
    static float GyroidSheet(Vector3 p, float cell, float t)
    {
        float k = 2f * MathF.PI / cell;
        float x = p.X * k, y = p.Y * k, z = p.Z * k;
        float sx = MathF.Sin(x), cx = MathF.Cos(x), sy = MathF.Sin(y), cy = MathF.Cos(y), sz = MathF.Sin(z), cz = MathF.Cos(z);
        float g = sx * cy + sy * cz + sz * cx;
        Vector3 grad = k * new Vector3(cx * cy - sz * sx, cy * cz - sx * sy, cz * cx - sy * sz);
        return MathF.Abs(g) / MathF.Max(grad.Length(), 0.3f * k) - t * 0.5f;
    }

    /// Volume of the voxel body's mesh in cm3 (signed, so cavities subtract).
    static float MeshVol(Voxels v)
    {
        Mesh m = v.mshAsMesh();
        double vol = 0;
        for (int i = 0; i < m.nTriangleCount(); i++)
        {
            m.GetTriangle(i, out Vector3 a, out Vector3 b, out Vector3 c);
            vol += Vector3.Dot(a, Vector3.Cross(b, c)) / 6.0;
        }
        return (float)(Math.Abs(vol) / 1000.0);
    }

    /// out/<PART_ID>.gyroid.json, read by tools/finish.py --variant gyroid.
    static void WriteStats(string id, Dictionary<string, object> stats)
    {
        string outDir = Environment.GetCommandLineArgs().Skip(1)
            .First(a => !a.EndsWith(".json", StringComparison.OrdinalIgnoreCase));
        File.WriteAllText(Path.Combine(outDir, id + ".gyroid.json"),
            System.Text.Json.JsonSerializer.Serialize(stats, new System.Text.Json.JsonSerializerOptions { WriteIndented = true }) + "\n");
    }

    /// Drain ports at the lowest and highest core points, then farthest-point
    /// spread; each runs from the core to the nearest outer surface and is
    /// skipped when its exit would land on a shape kept solid; bores and
    /// passages may take drains, as printed parts are often drained through them.
    static int DrillDrains(Library lib, Voxels body, Voxels outer, Voxels region, Voxels keep,
                           float cell, float skin, float d, int maxDrains)
    {
        BBox3 b = region.oCalculateBoundingBox();
        List<Vector3> pts = new();
        for (float x = b.vecMin.X + cell / 2; x < b.vecMax.X; x += cell)
            for (float y = b.vecMin.Y + cell / 2; y < b.vecMax.Y; y += cell)
                for (float z = b.vecMin.Z + cell / 2; z < b.vecMax.Z; z += cell)
                {
                    Vector3 p = new(x, y, z);
                    if (region.bIsInside(p)) pts.Add(p);
                }
        Console.Error.WriteLine($"    drain candidates: {pts.Count} core points");
        if (pts.Count == 0) return 0;
        List<Vector3> sites = new() { pts.MinBy(p => p.Z), pts.MaxBy(p => p.Z) };
        while (sites.Count < Math.Min(maxDrains, pts.Count))
            sites.Add(pts.MaxBy(p => sites.Min(s => Vector3.Distance(p, s))));
        int drilled = 0;
        // An empty Voxels reports every point inside once offset: test only real shapes.
        Voxels? keepZone = Sdf.Vol(keep) > 0f ? keep.voxOffset(d) : null;
        foreach (Vector3 p in sites.Distinct())
        {
            if (!outer.bClosestPointOnSurface(p, out Vector3 q)) { Console.Error.WriteLine($"    drain at {p}: no surface point"); continue; }
            Vector3 dir = Vector3.Normalize(q - p);
            if (float.IsNaN(dir.X) || keepZone?.bIsInside(q) == true) { Console.Error.WriteLine($"    drain at {p}: exit {q} on a feature"); continue; }
            Vector3 a = p - dir * (cell * 0.5f), e = q + dir * (skin + 2f * d);
            body.BoolSubtract(Sdf.Vox(lib, v => Sdf.Capsule(v, a, e, d / 2f),
                                      Vector3.Min(a, e) - new Vector3(d), Vector3.Max(a, e) + new Vector3(d)));
            drilled++;
        }
        return drilled;
    }
}
