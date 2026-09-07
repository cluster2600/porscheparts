using System.Diagnostics;
using System.Globalization;
using System.Numerics;
using System.Runtime.InteropServices;
using System.Runtime.CompilerServices;
using System.Security.Cryptography;
using System.Text.Json;
using PicoGK;

// Computational geometry on a COPY of the supplied head, not a physical
// cooling calculation and not permission to hollow out the remaining core.
if (args.Length != 3 ||
    !float.TryParse(args[2], NumberStyles.Float, CultureInfo.InvariantCulture, out float voxelMm) ||
    !float.IsFinite(voxelMm) || voxelMm < 0.1f || voxelMm > 1f)
{
    Console.Error.WriteLine("Usage: CoolingDomains INPUT_STL NEW_OUTPUT_DIR VOXEL_MM (0.1..1.0)");
    return 2;
}
string input = Path.GetFullPath(args[0]);
string output = Path.GetFullPath(args[1]);
if (!File.Exists(input) || Directory.Exists(output) || File.Exists(output))
{
    Console.Error.WriteLine("Input must exist and output must not exist; no master overwrite.");
    return 2;
}
const float enclosureMarginMm = 20f;
const float geometricClearanceMm = 1.5f;
const double volumeScreenRelativeTolerance = 0.02;
var timer = Stopwatch.StartNew();
string Sha(string path)
{
    using var stream = File.OpenRead(path);
    return Convert.ToHexString(SHA256.HashData(stream)).ToLowerInvariant();
}
float[] V(Vector3 v) => [v.X, v.Y, v.Z];
object Box(BBox3 b) => new { min_mm = V(b.vecMin), max_mm = V(b.vecMax) };
void Stage(string stage)
{
    Console.WriteLine(JsonSerializer.Serialize(new { stage, elapsed_seconds = timer.Elapsed.TotalSeconds }));
    Console.Out.Flush();
}
double SignedMeshVolume(Mesh mesh)
{
    // Divergence theorem, with a translated origin and compensated summation.
    // The interpretation as enclosed volume requires closed, consistent winding.
    BBox3 bounds = mesh.oBoundingBox();
    Vector3 origin = (bounds.vecMin + bounds.vecMax) * 0.5f;
    double sum = 0, compensation = 0;
    int count = mesh.nTriangleCount();
    for (int index = 0; index < count; index++)
    {
        mesh.GetTriangle(index, out Vector3 a, out Vector3 b, out Vector3 c);
        double ax = (double)a.X - origin.X, ay = (double)a.Y - origin.Y, az = (double)a.Z - origin.Z;
        double bx = (double)b.X - origin.X, by = (double)b.Y - origin.Y, bz = (double)b.Z - origin.Z;
        double cx = (double)c.X - origin.X, cy = (double)c.Y - origin.Y, cz = (double)c.Z - origin.Z;
        double term = (ax * (by * cz - bz * cy) + ay * (bz * cx - bx * cz) + az * (bx * cy - by * cx)) / 6;
        double corrected = term - compensation, next = sum + corrected;
        compensation = (next - sum) - corrected;
        sum = next;
    }
    if (!double.IsFinite(sum) || sum <= 0) throw new InvalidDataException("Oriented mesh volume is not positive");
    return sum;
}
double SignedFieldMeshVolume(Voxels voxels)
{
    using Mesh surface = new(voxels);
    return SignedMeshVolume(surface);
}
object Export(Voxels voxels, string filename, string interpretation, out float volume, out double signedVolume)
{
    using Mesh mesh = new(voxels);
    int triangles = mesh.nTriangleCount();
    if (triangles <= 0) throw new InvalidDataException("Empty geometry: " + filename);
    voxels.CalculateProperties(out volume, out BBox3 bounds);
    if (!float.IsFinite(volume) || volume <= 0) throw new InvalidDataException("Invalid volume: " + filename);
    string path = Path.Combine(output, filename);
    mesh.SaveToStlFile(path, Mesh.EStlUnit.MM);
    signedVolume = SignedMeshVolume(mesh);
    return new { filename, sha256 = Sha(path), triangles, native_resampled_volume_mm3 = volume,
                 oriented_mesh_volume_mm3 = signedVolume,
                 bounds = Box(bounds), interpretation, is_manufacturing_candidate = false };
}
Directory.CreateDirectory(output);
try
{
    string inputSha = Sha(input);
    Stage("load_head_stl_explicit_mm_identity_transform");
    using Library library = new(voxelMm);
    bool Inside(Voxels field, Vector3 point) => NativeOccupancy.Inside(library, field, point);
    object hollowCubeWitness;
    using (Voxels cubeOuter = new(library, new AxisAlignedBoxSdf(new BBox3(new Vector3(-10f), new Vector3(10f)))))
    using (Voxels cubeInner = new(library, new AxisAlignedBoxSdf(new BBox3(new Vector3(-6f), new Vector3(6f)))))
    using (Voxels hollowCube = cubeOuter.voxBoolSubtract(cubeInner))
    {
        const double analyticHollowCubeVolume = 20 * 20 * 20 - 12 * 12 * 12;
        hollowCube.CalculateProperties(out float nativeCubeVolume, out BBox3 _);
        double meshCubeVolume = SignedFieldMeshVolume(hollowCube);
        double meshError = Math.Abs(meshCubeVolume - analyticHollowCubeVolume) / analyticHollowCubeVolume;
        Vector3[] witnessPoints = [Vector3.Zero, new(8f, 0, 0), new(20f, 0, 0)];
        bool[] expectedOccupancy = [false, true, false];
        bool[] correctedOccupancy = witnessPoints.Select(p => Inside(hollowCube, p)).ToArray();
        bool[] upstreamOccupancy = witnessPoints.Select(p => hollowCube.bIsInside(p)).ToArray();
        if (!correctedOccupancy.SequenceEqual(expectedOccupancy))
            throw new InvalidDataException("Synthetic native byte-return occupancy witness failed");
        if (meshError > volumeScreenRelativeTolerance)
            throw new InvalidDataException("Synthetic hollow-cube oriented volume witness failed");
        hollowCubeWitness = new
        {
            scope = "synthetic_numerical_witness_not_a_head_design",
            outer_side_mm = 20,
            inner_side_mm = 12,
            analytic_volume_mm3 = analyticHollowCubeVolume,
            native_resampled_volume_mm3 = nativeCubeVolume,
            oriented_mesh_volume_mm3 = meshCubeVolume,
            oriented_mesh_relative_error = meshError,
            native_relative_error = Math.Abs(nativeCubeVolume - analyticHollowCubeVolume) / analyticHollowCubeVolume,
            oriented_mesh_witness_passed = true
            , occupancy_expected = expectedOccupancy
            , occupancy_native_byte_return = correctedOccupancy
            , occupancy_upstream_default_bool_return = upstreamOccupancy
            , occupancy_byte_return_witness_passed = true
        };
    }
    using Mesh source = Mesh.mshFromStlFile(input, Mesh.EStlUnit.MM, libSet: library);
    int sourceTriangles = source.nTriangleCount();
    if (sourceTriangles <= 0) throw new InvalidDataException("Input mesh is empty");
    BBox3 inputBounds = source.oBoundingBox();
    using Voxels body = new(source);
    body.CalculateProperties(out float bodyVolume, out BBox3 bodyBounds);
    if (!float.IsFinite(bodyVolume) || bodyVolume <= 0) throw new InvalidDataException("Input body volume is invalid");
    double bodyMeshVolume = SignedFieldMeshVolume(body);

    Stage("render_analytic_box_signed_distance_enclosure");
    BBox3 enclosureBounds = inputBounds;
    enclosureBounds.Grow(enclosureMarginMm);
    AxisAlignedBoxSdf boxSdf = new(enclosureBounds);
    using Voxels enclosure = new(library, boxSdf);
    enclosure.CalculateProperties(out float enclosureVolume, out BBox3 discretizedEnclosureBounds);
    Vector3 size = enclosureBounds.vecMax - enclosureBounds.vecMin;
    double analyticEnclosureVolume = (double)size.X * size.Y * size.Z;
    double enclosureMeshVolume = SignedFieldMeshVolume(enclosure);

    Stage("boolean_air_domain_enclosure_minus_body");
    using Voxels voids = enclosure.voxBoolSubtract(body);
    var fluidExport = Export(voids, "unclassified-void-complement.stl",
        "All voids in the enclosing box; connected external air and isolated/internal cavities are NOT yet separated", out float voidVolume, out double voidMeshVolume);

    Stage("negative_offset_geometric_clearance_core");
    using Voxels geometricCore = body.voxOffset(-geometricClearanceMm);
    // An intersection avoids carrying numerical outside remnants into this
    // diagnostic. Clearance alone never defines a structurally removable zone.
    geometricCore.BoolIntersect(body);
    var coreExport = Export(geometricCore, "geometric-clearance-core-1p5mm.stl",
        "Eroded body only; NOT a structurally admissible core, channel mask, or material-removal permission", out float coreVolume, out double coreMeshVolume);

    Stage("boolean_protected_geometric_skin");
    using Voxels skin = body.voxBoolSubtract(geometricCore);
    var skinExport = Export(skin, "geometric-protected-skin-1p5mm.stl",
        "Body minus eroded core; approximate geometric skin only, not a minimum safe wall or thickness measurement", out float skinVolume, out double skinMeshVolume);

    Stage("sample_signed_occupancy_partitions_not_exhaustive");
    const float sampleStepMm = 6f;
    float epsilon = voxelMm * 0.05f;
    int tested = 0, excluded = 0, bodyVoidOverlap = 0, bodyVoidMissing = 0, coreSkinOverlap = 0, coreSkinMissing = 0;
    Vector3[] directions = [new(epsilon, 0, 0), new(0, epsilon, 0), new(0, 0, epsilon)];
    Voxels[] sampledBoundaries = [enclosure, body, geometricCore];
    for (float x = enclosureBounds.vecMin.X + 0.371f * sampleStepMm; x < enclosureBounds.vecMax.X; x += sampleStepMm)
    for (float y = enclosureBounds.vecMin.Y + 0.371f * sampleStepMm; y < enclosureBounds.vecMax.Y; y += sampleStepMm)
    for (float z = enclosureBounds.vecMin.Z + 0.371f * sampleStepMm; z < enclosureBounds.vecMax.Z; z += sampleStepMm)
    {
        Vector3 point = new(x, y, z);
        bool nearInterface = false;
        foreach (Voxels boundary in sampledBoundaries)
        {
            bool centreInside = Inside(boundary, point);
            foreach (Vector3 direction in directions)
                if (Inside(boundary, point + direction) != centreInside || Inside(boundary, point - direction) != centreInside)
                    nearInterface = true;
        }
        if (nearInterface) { excluded++; continue; }
        tested++;
        bool inBox = Inside(enclosure, point), inBody = Inside(body, point), inVoid = Inside(voids, point);
        bool inCore = Inside(geometricCore, point), inSkin = Inside(skin, point);
        if (inBody && inVoid) bodyVoidOverlap++;
        if ((inBody || inVoid) != inBox) bodyVoidMissing++;
        if (inCore && inSkin) coreSkinOverlap++;
        if ((inCore || inSkin) != inBody) coreSkinMissing++;
    }

    Stage("save_named_openvdb_level_sets_and_verify_reload");
    string vdbPath = Path.Combine(output, "head-and-cooling-geometry-fields.vdb");
    using (OpenVdbFile fields = new(library))
    {
        fields.nAdd(body, "head_body");
        fields.nAdd(voids, "unclassified_void_complement");
        fields.nAdd(geometricCore, "geometric_clearance_core_1p5mm");
        fields.nAdd(skin, "geometric_protected_skin_1p5mm");
        fields.SaveToFile(vdbPath);
    }
    var fieldVolumes = new Dictionary<string, double>
    {
        ["head_body"] = bodyMeshVolume,
        ["unclassified_void_complement"] = voidMeshVolume,
        ["geometric_clearance_core_1p5mm"] = coreMeshVolume,
        ["geometric_protected_skin_1p5mm"] = skinMeshVolume
    };
    var reloadErrors = new Dictionary<string, double>();
    using (OpenVdbFile restored = new(library, vdbPath))
    {
        if (restored.nFieldCount() != 4 || MathF.Abs(restored.fPicoGKVoxelSizeMM() - voxelMm) > 1e-6f)
            throw new InvalidDataException("OpenVDB field count or voxel scale changed on reload");
        foreach (var item in fieldVolumes)
        {
            // Named retrieval is required: OpenVDB can reorder stored grids.
            using Voxels reloadedField = restored.voxGet(item.Key);
            double reloadedVolume = SignedFieldMeshVolume(reloadedField);
            double error = Math.Abs(reloadedVolume - item.Value) / item.Value;
            if (!double.IsFinite(error) || error > 1e-6)
                throw new InvalidDataException("OpenVDB field volume changed on reload: " + item.Key);
            reloadErrors[item.Key] = error;
        }
    }

    double enclosureError = Math.Abs(enclosureMeshVolume - analyticEnclosureVolume) / analyticEnclosureVolume;
    double voidPartitionError = Math.Abs(bodyMeshVolume + voidMeshVolume - enclosureMeshVolume) / enclosureMeshVolume;
    double skinPartitionError = Math.Abs(coreMeshVolume + skinMeshVolume - bodyMeshVolume) / bodyMeshVolume;
    double nativeVoidPartitionError = Math.Abs((double)bodyVolume + voidVolume - enclosureVolume) / enclosureVolume;
    double nativeSkinPartitionError = Math.Abs((double)coreVolume + skinVolume - bodyVolume) / bodyVolume;
    bool volumeScreenPass = enclosureError <= volumeScreenRelativeTolerance &&
                           voidPartitionError <= volumeScreenRelativeTolerance &&
                           skinPartitionError <= volumeScreenRelativeTolerance;
    bool occupancyScreenPass = tested > 0 && bodyVoidOverlap + bodyVoidMissing + coreSkinOverlap + coreSkinMissing == 0;
    if (Sha(input) != inputSha) throw new InvalidDataException("Master input changed during processing");
    var report = new
    {
        schema = "m64-picogk-cooling-domains-v1",
        status = "geometry_domains_generated_not_thermal_validation",
        utc_completed = DateTimeOffset.UtcNow,
        input_sha256 = inputSha,
        input_triangles = sourceTriangles,
        input_unchanged = true,
        units = "mm_under_unverified_1_scan_unit_per_mm_hypothesis",
        transform = "identity",
        voxel_mm = voxelMm,
        input_bounds = Box(inputBounds),
        body_voxel_volume_mm3 = bodyVolume,
        body_oriented_mesh_volume_mm3 = bodyMeshVolume,
        body_voxel_bounds = Box(bodyBounds),
        enclosure_margin_each_side_mm = enclosureMarginMm,
        enclosure_bounds = Box(enclosureBounds),
        enclosure_voxel_bounds = Box(discretizedEnclosureBounds),
        enclosure_analytic_volume_mm3 = analyticEnclosureVolume,
        enclosure_voxel_volume_mm3 = enclosureVolume,
        enclosure_oriented_mesh_volume_mm3 = enclosureMeshVolume,
        geometric_clearance_mm = geometricClearanceMm,
        synthetic_hollow_cube_witness = hollowCubeWitness,
        operations = new[] { "mesh_to_voxels", "bounded_analytic_signed_distance_box", "boolean_difference",
                             "negative_signed_distance_offset", "boolean_intersection", "voxel_to_stl" },
        outputs = new[] { fluidExport, coreExport, skinExport },
        openvdb = new
        {
            filename = Path.GetFileName(vdbPath),
            sha256 = Sha(vdbPath),
            bytes = new FileInfo(vdbPath).Length,
            named_fields = fieldVolumes.Keys,
            field_type = "OpenVDB_GRID_LEVEL_SET_narrow_band_not_full_domain_distance",
            named_reload_verified = true,
            reload_verification_method = "oriented_mesh_signed_volume_named_field_reconstruction",
            reload_volume_relative_errors = reloadErrors
        },
        volume_screen = new
        {
            relative_tolerance = volumeScreenRelativeTolerance,
            method = "compensated_oriented_triangle_divergence_integration_requires_closed_consistent_winding",
            threshold_scope = "coarse_numerical_smoke_only_not_physical_acceptance",
            analytic_box_relative_error = enclosureError,
            body_plus_void_partition_relative_error = voidPartitionError,
            core_plus_skin_partition_relative_error = skinPartitionError,
            passed = volumeScreenPass,
            proves_topology_or_mesh_convergence = false
        },
        native_volume_api_audit = new
        {
            method = "PicoGK_CalculateProperties_remesh_then_revoxelize",
            body_plus_void_partition_relative_error = nativeVoidPartitionError,
            core_plus_skin_partition_relative_error = nativeSkinPartitionError,
            discrepancy_flagged = nativeVoidPartitionError > volumeScreenRelativeTolerance || nativeSkinPartitionError > volumeScreenRelativeTolerance,
            warning = "Pinned CalculateProperties resamples each mesh independently and overestimates nested-cavity examples. Native values are preserved for audit, not used as hollow-domain volume truth. Exhaustive voxelwise partition remains unchecked."
        },
        sampled_occupancy_partition = new
        {
            method = "PicoGK_native_Voxels_bIsInside_byte_return_on_fixed_phase_6mm_sample_grid",
            interop_audit = "Pinned upstream C# declaration marshals C++ bool as default four-byte BOOL. A module-local byte-return declaration is checked against hollow-cube inside/outside witnesses; upstream image and kernel are not patched.",
            sample_step_mm = sampleStepMm,
            interface_probe_epsilon_mm = epsilon,
            tested_points = tested,
            near_interface_points_excluded = excluded,
            body_void_overlap_count = bodyVoidOverlap,
            body_void_union_mismatch_count = bodyVoidMissing,
            core_skin_overlap_count = coreSkinOverlap,
            core_skin_union_mismatch_count = coreSkinMissing,
            passed_at_sampled_points = occupancyScreenPass,
            exhaustive = false,
            fluid_connectivity_classified = false,
            warning = "Points with a classification change under small axis perturbations are excluded; sparse sampling does not prove voxelwise partition or topology."
        },
        topology_warning = "Complement includes external space plus every open/internal/isolated cavity (guides, seats, chamber). Occupancy/seed flood-fill, leaks, boundary labels and mesh quality must be audited before CFD. STL surface component count is NOT fluid-region count: an outer box and an inner solid boundary can enclose one connected fluid region.",
        core_warning = "1.5 mm is an exploratory geometric erosion only. No stress, temperature, material, print process, interfaces or machining allowances justify removing this core.",
        kernel_assembly_version = typeof(Library).Assembly.GetName().Version?.ToString(),
        native_library_sha256 = File.Exists("/app/picogk.26.2.so") ? Sha("/app/picogk.26.2.so") : null,
        application_assembly_sha256 = Sha(typeof(AxisAlignedBoxSdf).Assembly.Location),
        runtime = RuntimeInformation.FrameworkDescription,
        architecture = RuntimeInformation.ProcessArchitecture.ToString(),
        elapsed_seconds = timer.Elapsed.TotalSeconds,
        peak_working_set_bytes = Process.GetCurrentProcess().PeakWorkingSet64,
        master_modified = false,
        exterior_redesigned = false,
        channels_created = false,
        external_cooling_domain_qualified = false,
        fillets_created = false,
        structural_material_removal_authorized = false,
        thermal_simulation = false,
        structural_simulation = false,
        manufacturing_authorized = false
    };
    File.WriteAllText(Path.Combine(output, "cooling-domain-report.json"),
        JsonSerializer.Serialize(report, new JsonSerializerOptions { WriteIndented = true }) + "\n");
    Stage(volumeScreenPass && occupancyScreenPass ? "M64_PICOGK_COOLING_DOMAINS_GEOMETRY_PASS" : "M64_PICOGK_COOLING_DOMAINS_NUMERICAL_WARNING");
    return volumeScreenPass && occupancyScreenPass ? 0 : 3;
}
catch (Exception exception)
{
    File.WriteAllText(Path.Combine(output, "FAILED.json"), JsonSerializer.Serialize(new
    {
        status = "failed", error_type = exception.GetType().Name, error = exception.Message,
        elapsed_seconds = timer.Elapsed.TotalSeconds, manufacturing_authorized = false
    }, new JsonSerializerOptions { WriteIndented = true }));
    Console.Error.WriteLine($"M64_PICOGK_COOLING_DOMAINS_FAIL {exception.GetType().Name}: {exception.Message}");
    return 1;
}

// Exact analytic signed-distance function of an axis-aligned box. Rendering
// this through IBoundedImplicit uses the real PicoGK field implementation.
sealed class AxisAlignedBoxSdf(BBox3 bounds) : IBoundedImplicit
{
    public BBox3 oBounds { get; } = bounds;
    private readonly Vector3 centre = (bounds.vecMin + bounds.vecMax) * 0.5f;
    private readonly Vector3 halfSize = (bounds.vecMax - bounds.vecMin) * 0.5f;
    public float fSignedDistance(in Vector3 point)
    {
        Vector3 q = Vector3.Abs(point - centre) - halfSize;
        return Vector3.Max(q, Vector3.Zero).Length() + MathF.Min(MathF.Max(q.X, MathF.Max(q.Y, q.Z)), 0f);
    }
}

// This narrow ABI adapter is tied to the pinned PicoGK 2.3 sources and
// picogk.26.2 native runtime. C++ bool returns one byte, not Windows BOOL.
// No upstream assembly, kernel, or published image is modified.
static class NativeOccupancy
{
    [UnsafeAccessor(UnsafeAccessorKind.Field, Name = "hThis")]
    private static extern ref LibHandle LibraryHandle(Library instance);
    [UnsafeAccessor(UnsafeAccessorKind.Field, Name = "hThis")]
    private static extern ref VoxHandle VoxelHandle(Voxels instance);
    [DllImport("picogk.26.2", CallingConvention = CallingConvention.Cdecl, EntryPoint = "Voxels_bIsInside")]
    private static extern byte IsInsideByte(LibHandle library, VoxHandle voxels, in Vector3 point);
    public static bool Inside(Library library, Voxels voxels, in Vector3 point)
    {
        byte result = IsInsideByte(LibraryHandle(library), VoxelHandle(voxels), point);
        if (result > 1) throw new InvalidDataException("Native bool occupancy byte is invalid");
        GC.KeepAlive(voxels);
        GC.KeepAlive(library);
        return result == 1;
    }
}
