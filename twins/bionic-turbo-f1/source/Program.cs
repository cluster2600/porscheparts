// Versioned F0 baseline with independently switchable scroll-law and wheel-shroud studies.
// F0 Program.cs SHA-256: 69159efc5aa6d349e9696ca4276788a85b1564627af8b82f0c0f24461d61b4ca
using System.Numerics;
using System.Security.Cryptography;
using System.Text.Json;
using System.Text.Json.Serialization;
using PicoGK;
using PicoGKCatalog;

var json = new JsonSerializerOptions { PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower,
    UnmappedMemberHandling = JsonUnmappedMemberHandling.Disallow, RespectRequiredConstructorParameters = true, WriteIndented = true };
// Native sampling phase is common to every variant; exports remain in the original world frame.
Vector3 gridPhase = new(.173f, .119f, .071f);
Vector3 ToGrid(Vector3 world) => world + gridPhase;
Vector3 ToWorld(Vector3 grid) => grid - gridPhase;
Matrix4x4 exportTransform = Matrix4x4.CreateTranslation(-gridPhase);
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
    Require(p.ChamberProfile is "conical" or "wheel_shroud", "chamber_profile must be conical or wheel_shroud.");
    Require(float.IsFinite(p.RegularizationMm) && p.RegularizationMm >= .5f && p.RegularizationMm <= 1
        && p.RegularizationMm <= p.WallMm / 4, "regularization_mm must be finite [0.5, 1] and at most wall_mm/4.");
    Require(float.IsFinite(p.ShroudRadialClearanceMm) && p.ShroudRadialClearanceMm >= 1 && p.ShroudRadialClearanceMm <= 3
        && p.ShroudRadialClearanceMm >= 3 * p.VoxelMm, "shroud_radial_clearance_mm must be finite [1, 3] and resolved by 3 voxels.");
    if (p.ChamberProfile == "wheel_shroud")
        Require(p.ChamberHeightMm > 23 && p.RearOpeningRadiusMm > 30.25f + p.ShroudRadialClearanceMm
            && p.InletRadiusMm >= 20.3f + p.ShroudRadialClearanceMm, "Wheel-shroud transition dimensions are inconsistent.");
    Require(p.VoluteLaw is "radius_linear" or "area_affine", "volute_law must be radius_linear or area_affine.");
    Require(p.WallMm >= 4 * p.VoxelMm && p.RibRadiusMm >= 2 * p.VoxelMm, "Wall/ribs are unresolved at this voxel size.");
    Require(p.RibCount >= 4 && p.RibCount <= 12, "rib_count must be 4..12.");
    Require(p.RearOpeningRadiusMm > p.InletRadiusMm + 5, "Rear opening must exceed inlet radius by 5 mm.");
    Require(p.VoluteCenterRadiusMm > p.RearOpeningRadiusMm + 10, "Diffuser radial span must exceed 10 mm.");
    Require(p.VoluteEndRadiusMm > p.VoluteStartRadiusMm + 3 && p.VoluteStartRadiusMm > p.DiffuserHeightMm / 2,
        "Volute must grow and overlap the diffuser height.");
}
float ScrollRadius(Parameters p, float t)
{
    Require(float.IsFinite(t) && t >= 0 && t <= 1, "Scroll fraction must be finite in [0, 1].");
    float start = p.VoluteStartRadiusMm, end = p.VoluteEndRadiusMm;
    return p.VoluteLaw == "radius_linear" ? start + (end - start) * t
        : MathF.Sqrt(start * start + (end * end - start * start) * t);
}
if (args is ["--self-test"])
{
    var good = new Parameters(.5f, 3.5f, 22, 34, 28, 18, 8, 49, 6, 14, 42.25f, 2.2f, 8, "radius_linear", "conical", 1.5f, .5f);
    Validate(good);
    foreach (Parameters bad in new[] { good with { VoxelMm = float.NaN }, good with { WallMm = 1 },
        good with { RibCount = 0 }, good with { InletRadiusMm = 33 }, good with { VoluteEndRadiusMm = 6 }, good with { VoluteLaw = "unknown" },
        good with { VoluteEndRadiusMm = float.PositiveInfinity }, good with { VoxelMm = 1 }, good with { ChamberProfile = "unknown" },
        good with { ShroudRadialClearanceMm = float.NaN }, good with { ShroudRadialClearanceMm = 1 },
        good with { RegularizationMm = float.NaN }, good with { RegularizationMm = .25f },
        good with { RegularizationMm = 1.25f }, good with { RegularizationMm = .9f } })
    {
        bool rejected = false;
        try { Validate(bad); } catch (InvalidDataException) { rejected = true; }
        Require(rejected, "Parameter rejection self-test failed.");
    }
    foreach (string law in new[] { "radius_linear", "area_affine" })
    {
        Parameters p = good with { VoluteLaw = law };
        Require(ScrollRadius(p, 0) == 6 && ScrollRadius(p, 1) == 14, "Scroll endpoint self-test failed.");
        float expected = law == "radius_linear" ? 10 : MathF.Sqrt(116);
        Require(MathF.Abs(ScrollRadius(p, .5f) - expected) < 1e-5f, "Scroll midpoint self-test failed.");
        for (int i = 1; i <= 1024; ++i)
            Require(ScrollRadius(p, i / 1024f) > ScrollRadius(p, (i - 1) / 1024f), "Scroll monotonicity self-test failed.");
    }
    var profile = new WheelShroudProfile(-7.5f, good.ChamberHeightMm, good.RearOpeningRadiusMm,
        good.InletRadiusMm, good.ShroudRadialClearanceMm);
    foreach (var (z, expected) in new[] { (-7.5f, 34f), (0f, 34f), (4.5f, 31.75f), (21f, 21.8f), (28f, 22f) })
        Require(MathF.Abs(profile.Radius(z) - expected) < 1e-4f, "Wheel-shroud station self-test failed.");
    for (int i = 0; i <= 100; ++i)
    {
        float z = -7.5f + 35.5f * i / 100;
        float radius = profile.Radius(z);
        Require(profile.Distance(new(radius - .5f, z)) < 0 && profile.Distance(new(radius + .5f, z)) > 0,
            "Wheel-shroud signed-distance self-test failed.");
        Require(MathF.Abs(profile.Distance(new(profile.OuterRadius(z, good.WallMm), z)) - good.WallMm) < 1e-4f,
            "Wheel-shroud wall-offset self-test failed.");
    }
    foreach (float z in new[] { 0f, 4.5f, 21f, 28f })
        Require(MathF.Abs(profile.Radius(z - 1e-6f) - profile.Radius(z + 1e-6f)) < .001f,
            "Wheel-shroud continuity self-test failed.");
    foreach (Vector3 world in new[] { Vector3.Zero, new Vector3(-28, -20, 7.5f),
        new Vector3(49, 42.25f, 0), new Vector3(.185f, 0, 11), new Vector3(-69.5f, 69.5f, 46) })
    {
        Vector3 grid = ToGrid(world);
        Require(Vector3.Distance(ToWorld(grid), world) < 1e-5f
            && Vector3.Distance(Vector3.Transform(grid, exportTransform), world) < 1e-5f,
            "Grid/export transform roundtrip self-test failed.");
        Require(MathF.Abs(Sdf.CylZ(ToWorld(grid), 0, 0, 22, 0, 46) - Sdf.CylZ(world, 0, 0, 22, 0, 46)) < 1e-5f,
            "Translated analytic field self-test failed.");
        Require(MathF.Abs((ToWorld(grid).X - .185f) - (world.X - .185f)) < 1e-5f,
            "Translated section-plane self-test failed.");
    }
    Vector3 boxMin = new(-69.5f, -69.5f, -20.5f), boxMax = new(69.5f, 69.5f, 52.5f);
    Require(Vector3.Distance(ToGrid(boxMax) - ToGrid(boxMin), boxMax - boxMin) < 1e-5f,
        "Translated field-bounds self-test failed.");
    string validJson = JsonSerializer.Serialize(good, json);
    foreach (string badJson in new[] { validJson.Replace("\"rib_count\": 8", "\"rib_count\": 8.5"),
        validJson.Replace("\"voxel_mm\":", "\"voxel_typo_mm\":"), validJson.Replace("\"volute_law\"", "\"unknown_law\"") })
    {
        bool rejected = false;
        try { JsonSerializer.Deserialize<Parameters>(badJson, json); } catch (JsonException) { rejected = true; }
        Require(rejected, "Strict JSON self-test failed.");
    }
    Require(Sdf.CylZ(new(0, 0, 5), 0, 0, 10, 0, 10) < 0 && Sdf.CylZ(new(11, 0, 5), 0, 0, 10, 0, 10) > 0,
        "Signed field self-test failed.");
    Console.WriteLine("SELF_TEST_PASS (strict parameters, scroll laws, shroud continuity/offsets, grid/export transforms and signed fields; no native geometry)");
    return 0;
}
if (args.Length != 2) { Console.Error.WriteLine("Usage: BionicTurboF1 PARAMETERS.json NEW_OUTPUT_DIR | --self-test"); return 2; }
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
    float a(float t) => ScrollRadius(p, t);
    WheelShroudProfile? wheelShroud = p.ChamberProfile == "wheel_shroud"
        ? new(rear, h, p.RearOpeningRadiusMm, p.InletRadiusMm, p.ShroudRadialClearanceMm) : null;
    Vector3 Polar(float radius, float theta, float z) => new(radius * MathF.Cos(theta), radius * MathF.Sin(theta), z);
    float Core(Vector3 q, float offset)
    {
        float radius = p.RearOpeningRadiusMm - slope * Math.Clamp(q.Z, 0, h) + offset * normal;
        float radialField = wheelShroud is null ? (RotKit.R(q) - radius) / normal
            : wheelShroud.Distance(new(RotKit.R(q), q.Z)) - offset;
        float chamber = MathF.Max(radialField, MathF.Max(rear - q.Z, q.Z - h));
        float neck = Sdf.CylZ(q, 0, 0, p.InletRadiusMm + offset, h - w, front);
        float diffuser = Sdf.CylZ(q, 0, 0, r + offset, -p.DiffuserHeightMm / 2 - offset, p.DiffuserHeightMm / 2 + offset);
        float outlet = RotKit.Rod(q, new(r, 0, 0), new(r, p.OutletLengthMm, 0), p.VoluteEndRadiusMm + offset);
        return MathF.Min(MathF.Min(chamber, neck), MathF.Min(diffuser, outlet));
    }
    float extent = r + p.VoluteEndRadiusMm + w + 3;
    Vector3 min = new(-extent, -extent, -p.VoluteEndRadiusMm - w - 3);
    Vector3 max = new(extent, MathF.Max(extent, p.OutletLengthMm + 3), front + w + 3);
    using Library lib = new(p.VoxelMm);
    Voxels Field(Func<Vector3, float> field, Vector3 lower, Vector3 upper)
        => Sdf.Vox(lib, q => field(ToWorld(q)), ToGrid(lower), ToGrid(upper));
    using Voxels housing = Field( q => Core(q, w), min, max);
    using Voxels flow = Field( q => Core(q, 0), min, max);
    // shortcut: circular growing scroll without an engineered tongue, replace after aero/interface measurements.
    foreach (bool outside in new[] { false, true })
    {
        using Lattice scroll = new(lib);
        const int segments = 128;
        for (int i = 0; i < segments; ++i)
        {
            float t0 = (float)i / segments, t1 = (float)(i + 1) / segments, offset = outside ? w : 0;
            scroll.AddBeam(ToGrid(Polar(r, MathF.Tau * t0, 0)), a(t0) + offset, ToGrid(Polar(r, MathF.Tau * t1, 0)), a(t1) + offset);
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
            ribs.AddBeam(ToGrid(curve(t0)), float.Lerp(radius0, radius1, t0), ToGrid(curve(t1)), float.Lerp(radius0, radius1, t1));
        }
    }
    for (int i = 0; i < p.RibCount; ++i)
    {
        float theta = MathF.Tau * (i + .5f) / p.RibCount, zEnd = h * .4f;
        float shellR(float z) => wheelShroud is null
            ? p.RearOpeningRadiusMm - slope * Math.Clamp(z, 0, h) + w * normal - .6f
            : (z > h ? p.InletRadiusMm + w : wheelShroud.OuterRadius(z, w)) - .6f;
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
    using Voxels ports = Field( q => MathF.Min(
        Sdf.CylZ(q, 0, 0, p.InletRadiusMm, front - 2 * w, front + 2 * w), MathF.Min(
        Sdf.CylZ(q, 0, 0, p.RearOpeningRadiusMm, rear - 2 * w, rear + 2 * w),
        RotKit.Rod(q, new(r, p.OutletLengthMm - 2 * w, 0), new(r, p.OutletLengthMm + 2 * w, 0), p.VoluteEndRadiusMm))),
        min - new Vector3(2 * w), max + new Vector3(2 * w));
    housing.BoolSubtract(ports);
    // Remove subvoxel Boolean slivers before extraction; this also moves nominal inner surfaces.
    housing.Smoothen(p.RegularizationMm);
    var probes = new List<object>();
    void Probe(string id, Vector3 point, bool material)
    {
        bool actual = housing.bIsInside(ToGrid(point)), inFlow = flow.bIsInside(ToGrid(point));
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
        using Mesh sampledMesh = new(solid);
        using Mesh mesh = sampledMesh.mshCreateTransformed(exportTransform);
        solid.CalculateProperties(out float volume, out BBox3 bounds);
        Vector3 worldMin = ToWorld(bounds.vecMin), worldMax = ToWorld(bounds.vecMax);
        Require(mesh.nTriangleCount() > 0 && float.IsFinite(volume) && volume > 0, $"Empty {name}.");
        string path = Path.Combine(output, name + ".stl");
        mesh.SaveToStlFile(path, Mesh.EStlUnit.MM);
        files.Add(new { file = name + ".stl", triangles = mesh.nTriangleCount(), voxel_volume_mm3 = volume,
            bounds_min_mm = new[] { worldMin.X, worldMin.Y, worldMin.Z },
            bounds_max_mm = new[] { worldMax.X, worldMax.Y, worldMax.Z },
            sha256 = Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(path))).ToLowerInvariant() });
    }
    Save("housing", housing); Save("flow-domain", flow);
    float sectionX = .37f * p.VoxelMm;
    using Voxels halfspace = Field( q => Sdf.Box(q, new((extent + sectionX) / 2, 0, front / 2),
        new((extent - sectionX) / 2, 2 * extent, 2 * extent)), min, max);
    using Voxels section = housing.voxBoolIntersect(halfspace);
    Save("section", section);
    File.WriteAllText(Path.Combine(output, "report.json"), JsonSerializer.Serialize(new {
        schema_version = 1, status = "concept_geometry_generated", units = "mm", kernel = Library.strVersion(),
        parameters = p, parameters_sha256 = Convert.ToHexString(SHA256.HashData(parameterBytes)).ToLowerInvariant(),
        measured_interfaces = false, engineering_validated = false, manufacturing_authorized = false,
        grid_phase_mm = new[] { gridPhase.X, gridPhase.Y, gridPhase.Z },
        grid_phase_note = "All fields, bounds, lattice beams and probes are translated before voxel sampling; mesh exports and reported bounds are translated back. Nominal geometry and engineering uncertainty are unchanged; discretization changes.",
        exported_coordinate_frame = "original world frame; global Z remains the rotor axis",
        section_plane = "positive X retained from section_plane_x_mm", section_plane_x_mm = sectionX,
        regularization = new { method = "PicoGK Smoothen / TripleOffset", distance_mm = p.RegularizationMm,
            nominal_flow_domain_unchanged = true, exact_solver_fluid_domain = false }, native_probes = probes, files,
        study = new { id = "bionic-turbo-f1", scroll_law = p.VoluteLaw,
            formula = p.VoluteLaw == "radius_linear" ? "a(t) = a0 + (a1-a0)*t" : "a(t) = sqrt(a0^2 + (a1^2-a0^2)*t)",
            law_changes = "Scroll section and its outer wall; existing rib attachment points follow the scroll roof.",
            chamber_profile = p.ChamberProfile, shroud_radial_clearance_mm = p.ShroudRadialClearanceMm,
            shroud_clearance_active = wheelShroud is not null,
            shroud_profile = new { ellipse_segments = WheelShroudProfile.EllipseSegments,
                radius_formula = "R(z) = 30.25 - 9.95*sqrt(1-((21-z)/16.5)^2) + radial_clearance, z in [4.5,21] mm",
                rear_transition = "Rear opening radius to z=0; straight segment to 30.25 + radial_clearance at z=4.5.",
                front_transition = "20.3 + radial_clearance at z=21; straight segment to inlet radius at chamber_height.",
                method = "Signed meridional distance to 64 ellipse chords plus explicit transition segments; outer wall is the distance offset.",
                clearance_note = "Assumed radial clearance; neither a normal running clearance nor a qualified interface. Final Smoothen moves surfaces.",
                wheel_source = "parts/picogk-catalog/rotating/CompressorWheel.cs",
                wheel_source_sha256 = WheelShroudProfile.WheelSourceSha256,
                inspiration_source = "https://github.com/QU01/Quasar-Phy-CC/blob/fd2b4f2066176265d77bfaa860bda7030578ffc6/CompressorDesigner/src/CompressorDesigner/ImpellerFlowPath.cs" },
            fixed_center_radius_mm = r, full_turns = 1, engineered_tongue = false,
            junction_limitation = "The 360-degree sweep endpoints share one center; the large end overlaps the small start. Nominal pi*a^2 is not the effective section near the junction or diffuser union.",
            performance_gain_validated = false,
            inspiration = "QUASAR Phy-CC area-growth principle only; no third-party code copied. Its moving center and clamped sqrt(t) law are not reproduced.",
            inspiration_source = "https://github.com/QU01/Quasar-Phy-CC/blob/fd2b4f2066176265d77bfaa860bda7030578ffc6/CompressorDesigner/src/CompressorDesigner/Volute.cs",
            baseline_source = "twins/bionic-turbo-f0/source/Program.cs", baseline_source_sha256 = "69159efc5aa6d349e9696ca4276788a85b1564627af8b82f0c0f24461d61b4ca" },
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
    float VoluteStartRadiusMm, float VoluteEndRadiusMm, float OutletLengthMm, float RibRadiusMm, int RibCount, string VoluteLaw, string ChamberProfile, float ShroudRadialClearanceMm, float RegularizationMm);
