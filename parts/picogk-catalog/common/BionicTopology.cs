using System.Numerics;
using System.Text.Json.Nodes;
using PicoGK;

namespace PicoGKCatalog;

/// Load-driven body from topopt.py's density field, shaped by PicoGK.
///
/// 1. The filtered, projected density (0..1 per element) becomes a signed
///    distance by trilinear interpolation: d = (0.5 - rho) * element size.
/// 2. Smoothen() rounds it into organic members with filleted junctions.
/// 3. The functional features of bionic.json are fused exactly: "solid"
///    shapes added, "void" shapes cut, so bores and seats keep their size.
/// Optional: shaping.base_stl (a functional body such as a flow passage)
/// is added before the voids are cut.
public sealed class BionicTopology : IPartGenerator
{
    public string Name => "bionic_topology";

    public Voxels Build(Library lib, PartSpec spec)
    {
        // Runner.cs is hash-pinned by other studies, so the params path comes from
        // the command line (<exe> <params.json> <out-dir>) rather than from Runner.
        string paramsPath = Environment.GetCommandLineArgs().Skip(1)
            .First(a => a.EndsWith(".json", StringComparison.OrdinalIgnoreCase));
        string sourceDir = Path.GetDirectoryName(Path.GetFullPath(paramsPath))!;
        string root = Path.GetFullPath(Path.Combine(sourceDir, "..", "..", ".."));
        JsonNode bio = JsonNode.Parse(File.ReadAllText(Path.Combine(sourceDir, "bionic.json")))!;
        string outDir = Path.Combine(root, "parts", "picogk-catalog", "out", "bionic");
        JsonNode meta = JsonNode.Parse(File.ReadAllText(Path.Combine(outDir, spec.PartId + ".density.json")))!;
        float[] rho = ReadFloats(Path.Combine(outDir, spec.PartId + ".density.bin"));
        Vector3 origin = V(meta["origin_mm"]!);
        float h = meta["element_mm"]!.GetValue<float>();
        int nx = meta["shape_xyz"]![0]!.GetValue<int>(), ny = meta["shape_xyz"]![1]!.GetValue<int>(), nz = meta["shape_xyz"]![2]!.GetValue<int>();
        if (rho.Length != nx * ny * nz) throw new InvalidDataException("density size mismatch");

        float Rho(int i, int j, int k) =>
            (i < 0 || j < 0 || k < 0 || i >= nx || j >= ny || k >= nz) ? 0f : rho[i + nx * (j + ny * k)];
        float Field(Vector3 p)
        {
            Vector3 g = (p - origin) / h - new Vector3(0.5f);        // element centres at integer g
            int i = (int)MathF.Floor(g.X), j = (int)MathF.Floor(g.Y), k = (int)MathF.Floor(g.Z);
            float fx = g.X - i, fy = g.Y - j, fz = g.Z - k;
            float c00 = Rho(i, j, k) * (1 - fx) + Rho(i + 1, j, k) * fx;
            float c10 = Rho(i, j + 1, k) * (1 - fx) + Rho(i + 1, j + 1, k) * fx;
            float c01 = Rho(i, j, k + 1) * (1 - fx) + Rho(i + 1, j, k + 1) * fx;
            float c11 = Rho(i, j + 1, k + 1) * (1 - fx) + Rho(i + 1, j + 1, k + 1) * fx;
            float r = (c00 * (1 - fy) + c10 * fy) * (1 - fz) + (c01 * (1 - fy) + c11 * fy) * fz;
            return (0.5f - r) * h;
        }
        Vector3 size = new Vector3(nx, ny, nz) * h;
        Voxels body = new(lib, new Fn(Field), new BBox3(origin - new Vector3(h), origin + size + new Vector3(h)));
        float smooth = bio["shaping"]?["smooth_mm"]?.GetValue<float>() ?? h * 0.5f;
        if (smooth > 0) body.Smoothen(smooth);

        // Functional features are added, then the junctions are blended with a
        // smaller radius so the members flow into them; voids are cut last so
        // bores and passages keep their exact size.
        JsonNode opt = bio["optimization"]!;
        foreach (JsonNode? s in opt["solid"]?.AsArray() ?? new JsonArray())
            if (s!["analysis_only"]?.GetValue<bool>() != true)    // analysis-only walls come from base_stl
                body.BoolAdd(Shape(lib, s, root));
        string? baseStl = bio["shaping"]?["base_stl"]?.GetValue<string>();
        if (baseStl != null)
            body.BoolAdd(new Voxels(Mesh.mshFromStlFile(Path.Combine(root, baseStl), libSet: lib)));
        float blend = bio["shaping"]?["blend_mm"]?.GetValue<float>() ?? smooth * 0.5f;
        if (blend > 0) body.Smoothen(blend);
        foreach (JsonNode? s in opt["void"]?.AsArray() ?? new JsonArray())
            body.BoolSubtract(Shape(lib, s!, root));
        return body;
    }

    static float[] ReadFloats(string path)
    {
        byte[] b = File.ReadAllBytes(path);
        float[] f = new float[b.Length / 4];
        Buffer.BlockCopy(b, 0, f, 0, b.Length);
        return f;
    }

    static Vector3 V(JsonNode n) => new(n[0]!.GetValue<float>(), n[1]!.GetValue<float>(), n[2]!.GetValue<float>());

    /// Exact functional shapes, same vocabulary as topopt.py.
    public static Voxels Shape(Library lib, JsonNode s, string root)
    {
        string type = s["type"]!.GetValue<string>();
        switch (type)
        {
            case "box":
            {
                Vector3 lo = V(s["min"]!), hi = V(s["max"]!);
                Vector3 c = (lo + hi) / 2, half = (hi - lo) / 2;
                return Sdf.Vox(lib, p => Sdf.Box(p, c, half), lo - new Vector3(1), hi + new Vector3(1));
            }
            case "sphere":
            {
                Vector3 c = V(s["c"]!);
                float r = s["r"]!.GetValue<float>();
                return Sdf.Vox(lib, p => Sdf.Sphere(p, c, r), c - new Vector3(r + 1), c + new Vector3(r + 1));
            }
            case "capsule":
            case "cyl":
            {
                Vector3 a = V(s["a"]!), b = V(s["b"]!);
                float r = s["r"]!.GetValue<float>();
                bool flat = type == "cyl";
                Vector3 lo = Vector3.Min(a, b) - new Vector3(r + 1), hi = Vector3.Max(a, b) + new Vector3(r + 1);
                return Sdf.Vox(lib, p => flat ? CappedCylinder(p, a, b, r) : Sdf.Capsule(p, a, b, r), lo, hi);
            }
            case "stl":
                return new Voxels(Mesh.mshFromStlFile(Path.Combine(root, s["path"]!.GetValue<string>()), libSet: lib));
            default:
                throw new NotSupportedException($"shape '{type}'");
        }
    }

    /// Exact signed distance of a flat-ended cylinder between a and b.
    static float CappedCylinder(Vector3 p, Vector3 a, Vector3 b, float r)
    {
        Vector3 ba = b - a, pa = p - a;
        float baba = Vector3.Dot(ba, ba), paba = Vector3.Dot(pa, ba);
        float x = (pa * baba - ba * paba).Length() - r * baba;
        float y = MathF.Abs(paba - baba * 0.5f) - baba * 0.5f;
        float x2 = x * x, y2 = y * y * baba;
        float d = MathF.Max(x, y) < 0f ? -MathF.Min(x2, y2) : (x > 0f ? x2 : 0f) + (y > 0f ? y2 : 0f);
        return MathF.Sign(d) * MathF.Sqrt(MathF.Abs(d)) / baba;
    }
}
