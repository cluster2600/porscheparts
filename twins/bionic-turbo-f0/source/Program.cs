using System.Numerics;
using System.Security.Cryptography;
using System.Text.Json;
using System.Text.Json.Serialization;
using PicoGK;
using PicoGKCatalog;

var json = new JsonSerializerOptions { PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower,
    UnmappedMemberHandling = JsonUnmappedMemberHandling.Disallow, WriteIndented = true };
void Require(bool condition, string message) { if (!condition) throw new InvalidDataException(message); }
void Validate(Parameters p)
{
    foreach (var (name, value, min, max) in new (string, float, float, float)[] {
        ("voxel_mm", p.VoxelMm, .2f, 1f), ("wall_mm", p.WallMm, 2f, 6f),
        ("inlet_radius_mm", p.InletRadiusMm, 15f, 30f), ("rear_opening_radius_mm", p.RearOpeningRadiusMm, 28f, 45f),
        ("chamber_height_mm", p.ChamberHeightMm, 20f, 40f), ("inlet_neck_length_mm", p.InletNeckLengthMm, 12f, 30f),
        ("diffuser_height_mm", p.DiffuserHeightMm, 6f, 12f), ("volute_center_radius_mm", p.VoluteCenterRadiusMm, 42f, 65f),
        ("volute_start_radius_mm", p.VoluteStartRadiusMm, 5f, 9f), ("volute_end_radius_mm", p.VoluteEndRadiusMm, 10f, 18f),
        ("outlet_length_mm", p.OutletLengthMm, 35f, 65f), ("rib_radius_mm", p.RibRadiusMm, 1.5f, 4f) })
        Require(float.IsFinite(value) && value >= min && value <= max, $"Invalid {name}: expected finite [{min}, {max}].");
    Require(p.WallMm >= 4 * p.VoxelMm && p.RibRadiusMm >= 2 * p.VoxelMm, "Wall/ribs are unresolved at this voxel size.");
    Require(p.RibCount >= 4 && p.RibCount <= 12, "rib_count must be 4..12.");
    Require(p.RearOpeningRadiusMm > p.InletRadiusMm + 5, "Rear opening must exceed inlet radius by 5 mm.");
    Require(p.VoluteCenterRadiusMm > p.RearOpeningRadiusMm + 10, "Diffuser radial span must exceed 10 mm.");
    Require(p.VoluteEndRadiusMm > p.VoluteStartRadiusMm + 3 && p.VoluteStartRadiusMm > p.DiffuserHeightMm / 2,
        "Volute must grow and overlap the diffuser height.");
}
if (args is ["--self-test"])
{
    var good = new Parameters(.75f, 3.5f, 22, 34, 28, 18, 8, 49, 6, 14, 42, 2.2f, 8);
    Validate(good);
    foreach (Parameters bad in new[] { good with { VoxelMm = float.NaN }, good with { WallMm = 2 },
        good with { RibCount = 0 }, good with { InletRadiusMm = 33 }, good with { VoluteEndRadiusMm = 6 } })
    {
        bool rejected = false;
        try { Validate(bad); } catch (InvalidDataException) { rejected = true; }
        Require(rejected, "Parameter rejection self-test failed.");
    }
    Require(Sdf.CylZ(new(0, 0, 5), 0, 0, 10, 0, 10) < 0 && Sdf.CylZ(new(11, 0, 5), 0, 0, 10, 0, 10) > 0,
        "Signed field self-test failed.");
    Console.WriteLine("SELF_TEST_PASS (parameter validation and signed fields; no native geometry)");
    return 0;
}
if (args.Length != 2) { Console.Error.WriteLine("Usage: BionicTurbo PARAMETERS.json NEW_OUTPUT_DIR | --self-test"); return 2; }
string? output = null;
try
{
    byte[] parameterBytes = File.ReadAllBytes(args[0]);
    Parameters p = JsonSerializer.Deserialize<Parameters>(parameterBytes, json)
        ?? throw new InvalidDataException("Empty parameters.");
    Validate(p);
    string target = Path.GetFullPath(args[1]);
    Require(!Directory.Exists(target) && !File.Exists(target), "Output exists; refusing to overwrite.");
    Directory.CreateDirectory(target);
    output = target;
    float w = p.WallMm, r = p.VoluteCenterRadiusMm, h = p.ChamberHeightMm;
    float rear = -p.DiffuserHeightMm / 2 - w, front = h + p.InletNeckLengthMm;
    float slope = (p.RearOpeningRadiusMm - p.InletRadiusMm) / h, normal = MathF.Sqrt(1 + slope * slope);
    float a(float t) => p.VoluteStartRadiusMm + (p.VoluteEndRadiusMm - p.VoluteStartRadiusMm) * t;
    Vector3 Polar(float radius, float theta, float z) => new(radius * MathF.Cos(theta), radius * MathF.Sin(theta), z);
    float Core(Vector3 q, float offset)
    {
        float radius = p.RearOpeningRadiusMm - slope * Math.Clamp(q.Z, 0, h) + offset * normal;
        float chamber = MathF.Max((RotKit.R(q) - radius) / normal, MathF.Max(rear - q.Z, q.Z - h));
        float neck = Sdf.CylZ(q, 0, 0, p.InletRadiusMm + offset, h - w, front);
        float diffuser = Sdf.CylZ(q, 0, 0, r + offset, -p.DiffuserHeightMm / 2 - offset, p.DiffuserHeightMm / 2 + offset);
        float outlet = RotKit.Rod(q, new(r, 0, 0), new(r, p.OutletLengthMm, 0), p.VoluteEndRadiusMm + offset);
        return MathF.Min(MathF.Min(chamber, neck), MathF.Min(diffuser, outlet));
    }
    float extent = r + p.VoluteEndRadiusMm + w + 3;
    Vector3 min = new(-extent, -extent, -p.VoluteEndRadiusMm - w - 3);
    Vector3 max = new(extent, MathF.Max(extent, p.OutletLengthMm + 3), front + w + 3);
    using Library lib = new(p.VoxelMm);
    using Voxels housing = Sdf.Vox(lib, q => Core(q, w), min, max);
    using Voxels flow = Sdf.Vox(lib, q => Core(q, 0), min, max);
    // shortcut: circular growing scroll without an engineered tongue, replace after aero/interface measurements.
    foreach (bool outside in new[] { false, true })
    {
        using Lattice scroll = new(lib);
        const int segments = 128;
        for (int i = 0; i < segments; ++i)
        {
            float t0 = (float)i / segments, t1 = (float)(i + 1) / segments, offset = outside ? w : 0;
            scroll.AddBeam(Polar(r, MathF.Tau * t0, 0), a(t0) + offset, Polar(r, MathF.Tau * t1, 0), a(t1) + offset);
        }
        using Voxels tube = new(scroll);
        (outside ? housing : flow).BoolAdd(tube);
    }
    using Lattice ribs = new(lib);
    void Curve(Func<float, Vector3> curve, float radius0, float radius1)
    {
        const int n = 24;
        for (int j = 0; j < n; ++j)
        {
            float t0 = (float)j / n, t1 = (float)(j + 1) / n;
            ribs.AddBeam(curve(t0), float.Lerp(radius0, radius1, t0), curve(t1), float.Lerp(radius0, radius1, t1));
        }
    }
    for (int i = 0; i < p.RibCount; ++i)
    {
        float theta = MathF.Tau * (i + .5f) / p.RibCount, zEnd = h * .4f;
        float shellR(float z) => p.RearOpeningRadiusMm - slope * Math.Clamp(z, 0, h) + w * normal - .6f;
        Vector3 fork = Polar(shellR(zEnd), theta + .09f, zEnd);
        Curve(t => { float z = float.Lerp(h + p.InletNeckLengthMm * .35f, zEnd, t);
            return Polar(shellR(z), theta + .09f * t * t, z); }, p.RibRadiusMm, p.RibRadiusMm * .9f);
        foreach (float direction in new[] { -1f, 1f })
        {
            float endTheta = theta + .09f + direction * .16f;
            float fraction = (endTheta / MathF.Tau + 1) % 1;
            Vector3 end = Polar(r, endTheta, a(fraction) + w - .7f);
            Vector3 control = Polar(r - 5, theta + .09f + direction * .08f, MathF.Max(zEnd, a(fraction) + w) + 2 * p.RibRadiusMm);
            Curve(t => Sdf.Bezier(fork, control, end, t), p.RibRadiusMm * .9f, p.RibRadiusMm * .7f);
        }
    }
    using Voxels ribSolid = new(ribs);
    housing.BoolAdd(ribSolid);
    housing.BoolSubtract(flow);
    using Voxels ports = Sdf.Vox(lib, q => MathF.Min(
        Sdf.CylZ(q, 0, 0, p.InletRadiusMm, front - 2 * w, front + 2 * w), MathF.Min(
        Sdf.CylZ(q, 0, 0, p.RearOpeningRadiusMm, rear - 2 * w, rear + 2 * w),
        RotKit.Rod(q, new(r, p.OutletLengthMm - 2 * w, 0), new(r, p.OutletLengthMm + 2 * w, 0), p.VoluteEndRadiusMm))),
        min - new Vector3(2 * w), max + new Vector3(2 * w));
    housing.BoolSubtract(ports);
    // Remove subvoxel Boolean slivers before extraction; this also moves nominal inner surfaces.
    housing.Smoothen(p.VoxelMm);
    var probes = new List<object>();
    void Probe(string id, Vector3 point, bool material)
    {
        bool actual = housing.bIsInside(point), inFlow = flow.bIsInside(point);
        Require(actual == material && (material || inFlow), $"Native occupancy probe failed: {id}.");
        probes.Add(new { id, point_mm = new[] { point.X, point.Y, point.Z }, expected_material = material,
            actual_material = actual, inside_flow_domain = inFlow, passed = true });
    }
    Probe("axial-inlet", new(0, 0, h + p.InletNeckLengthMm / 2), false);
    Probe("rear-opening", new(0, 0, rear + w), false);
    Probe("tangent-outlet", new(r, p.OutletLengthMm - 2 * w, 0), false);
    Probe("inlet-wall", new(p.InletRadiusMm + w / 2, 0, h + p.InletNeckLengthMm / 2), true);
    for (int i = 0; i < 8; ++i) Probe($"scroll-{i}", Polar(r, MathF.Tau * (i + .5f) / 8, 0), false);
    var files = new List<object>();
    void Save(string name, Voxels solid)
    {
        using Mesh mesh = new(solid);
        solid.CalculateProperties(out float volume, out BBox3 bounds);
        Require(mesh.nTriangleCount() > 0 && float.IsFinite(volume) && volume > 0, $"Empty {name}.");
        string path = Path.Combine(output, name + ".stl");
        mesh.SaveToStlFile(path, Mesh.EStlUnit.MM);
        files.Add(new { file = name + ".stl", triangles = mesh.nTriangleCount(), voxel_volume_mm3 = volume,
            bounds_min_mm = new[] { bounds.vecMin.X, bounds.vecMin.Y, bounds.vecMin.Z },
            bounds_max_mm = new[] { bounds.vecMax.X, bounds.vecMax.Y, bounds.vecMax.Z },
            sha256 = Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(path))).ToLowerInvariant() });
    }
    Save("housing", housing); Save("flow-domain", flow);
    float sectionX = .37f * p.VoxelMm;
    using Voxels halfspace = Sdf.Vox(lib, q => Sdf.Box(q, new((extent + sectionX) / 2, 0, front / 2),
        new((extent - sectionX) / 2, 2 * extent, 2 * extent)), min, max);
    using Voxels section = housing.voxBoolIntersect(halfspace);
    Save("section", section);
    File.WriteAllText(Path.Combine(output, "report.json"), JsonSerializer.Serialize(new {
        schema_version = 1, status = "concept_geometry_generated", units = "mm", kernel = Library.strVersion(),
        parameters = p, parameters_sha256 = Convert.ToHexString(SHA256.HashData(parameterBytes)).ToLowerInvariant(),
        measured_interfaces = false, engineering_validated = false, manufacturing_authorized = false,
        section_plane = "positive X retained from section_plane_x_mm", section_plane_x_mm = sectionX,
        regularization = new { method = "PicoGK Smoothen / TripleOffset", distance_mm = p.VoxelMm,
            nominal_flow_domain_unchanged = true, exact_solver_fluid_domain = false }, native_probes = probes, files,
        note = "Hypothetical compressor housing; bionic ribs are design features, not optimized or validated load paths."
    }, json) + "\n");
    Console.WriteLine("GEOMETRY_PASS: housing, flow-domain, section and native occupancy probes.");
    return 0;
}
catch (Exception error)
{
    if (output is not null) File.WriteAllText(Path.Combine(output, "FAILED.json"), JsonSerializer.Serialize(new {
        status = "failed", error = error.Message, manufacturing_authorized = false }, json));
    Console.Error.WriteLine(error.Message);
    return 1;
}

sealed record Parameters(float VoxelMm, float WallMm, float InletRadiusMm, float RearOpeningRadiusMm,
    float ChamberHeightMm, float InletNeckLengthMm, float DiffuserHeightMm, float VoluteCenterRadiusMm,
    float VoluteStartRadiusMm, float VoluteEndRadiusMm, float OutletLengthMm, float RibRadiusMm, int RibCount);
