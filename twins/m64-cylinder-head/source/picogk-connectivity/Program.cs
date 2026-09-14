using System.Diagnostics;
using System.Globalization;
using System.Numerics;
using System.Runtime.CompilerServices;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Text.Json;
using PicoGK;

// Reads existing named fields. Does not remesh, smooth, offset or edit the head.
bool witnessOnly = args.Length == 2 && args[0] == "--witness";
if (!witnessOnly && args.Length != 5)
{
    Console.Error.WriteLine("Usage: OccupancySampler INPUT_VDB SOURCE_REPORT NEW_DIR SAMPLE_STEP PHASE | --witness NEW_DIR");
    return 2;
}
string output = Path.GetFullPath(witnessOnly ? args[1] : args[2]);
if (Directory.Exists(output) || File.Exists(output)) return 2;
var timer = Stopwatch.StartNew();
string Sha(string path)
{
    using var stream = File.OpenRead(path);
    return Convert.ToHexString(SHA256.HashData(stream)).ToLowerInvariant();
}
float[] Components(Vector3 value) => [value.X, value.Y, value.Z];
Directory.CreateDirectory(output);
try
{
    float step = witnessOnly ? 1f : float.Parse(args[3], CultureInfo.InvariantCulture);
    float phase = witnessOnly ? 0.371f : float.Parse(args[4], CultureInfo.InvariantCulture);
    if (!float.IsFinite(step) || step < 0.3f || step > 6f || !float.IsFinite(phase) || phase <= 0 || phase >= 1)
        throw new InvalidDataException("Explicit finite spacing 0.3..6 and phase strictly inside (0,1) required");
    JsonDocument? sourceReport = witnessOnly ? null : JsonDocument.Parse(File.ReadAllText(args[1]));
    float voxel = witnessOnly ? 0.3f : sourceReport!.RootElement.GetProperty("voxel_mm").GetSingle();
    using Library library = new(voxel);
    bool Inside(Voxels field, Vector3 point) => NativeOccupancy.Inside(library, field, point);
    using Voxels outer = new(library, new BoxSdf(new BBox3(new Vector3(-10), new Vector3(10))));
    using Voxels inner = new(library, new BoxSdf(new BBox3(new Vector3(-6), new Vector3(6))));
    using Voxels hollow = outer.voxBoolSubtract(inner);
    bool[] expected = [false, true, false];
    bool[] actual = [Inside(hollow, Vector3.Zero), Inside(hollow, new Vector3(8, 0, 0)), Inside(hollow, new Vector3(20, 0, 0))];
    if (!actual.SequenceEqual(expected)) throw new InvalidDataException("Native one-byte bool witness failed");

    void Sample(Voxels body, Voxels voids, BBox3 bounds, string destination, string? vdbSha, string? sourceSha, string? reportSha, Action? verifyInputs = null)
    {
        Vector3 extent = bounds.vecMax - bounds.vecMin;
        int[] shape = [(int)MathF.Floor(extent.X / step), (int)MathF.Floor(extent.Y / step), (int)MathF.Floor(extent.Z / step)];
        long total = (long)shape[0] * shape[1] * shape[2];
        if (shape.Any(n => n < 3) || total <= 0 || total > 4_000_000)
            throw new InvalidDataException("Sample lattice exceeds fixed four-million-point bound or has an invalid dimension");
        byte[] mask = new byte[total];
        byte[] zeroAsVoidMask = new byte[total];
        int occupiedBody = 0, occupiedVoid = 0, overlap = 0, missing = 0, boundaryBody = 0;
        var overlapSignedValues = new List<object>();
        int exactZeroBoth = 0, strictNegativeOverlap = 0;
        float SignedAt(Voxels field, Vector3 point)
        {
            field.GetVoxelDimensions(out int ox, out int oy, out int oz, out int nx, out int ny, out int nz);
            int ix = (int)MathF.Round(point.X / voxel, MidpointRounding.AwayFromZero);
            int iy = (int)MathF.Round(point.Y / voxel, MidpointRounding.AwayFromZero);
            int iz = (int)MathF.Round(point.Z / voxel, MidpointRounding.AwayFromZero);
            if (ix < ox || ix >= ox+nx || iy < oy || iy >= oy+ny || iz < oz || iz >= oz+nz)
                throw new InvalidDataException("Overlap lies outside active-field slice bounds");
            ImageGrayScale image = field.imgAllocateSlice(out _);
            int slice = iz - oz;
            field.GetVoxelSlice(slice, ref image, Voxels.ESliceMode.SignedDistance);
            // Native GetZSlice writes X increasing, Y decreasing from bbox maximum.
            return image.fValue(ix - ox, oy + ny - 1 - iy);
        }
        for (int z = 0; z < shape[2]; z++)
        {
            if (timer.Elapsed.TotalSeconds > 240) throw new TimeoutException("Native sampling time budget exceeded");
            for (int y = 0; y < shape[1]; y++)
            for (int x = 0; x < shape[0]; x++)
            {
                Vector3 point = bounds.vecMin + new Vector3((x + phase) * step, (y + phase) * step, (z + phase) * step);
                bool solid = Inside(body, point), fluid = Inside(voids, point);
                bool exactSharedZero = false;
                if (solid) occupiedBody++;
                if (fluid) occupiedVoid++;
                if (solid && fluid)
                {
                    overlap++;
                    if (overlap > 4096) throw new InvalidDataException("Overlap diagnostic count exceeds fixed bound");
                    float bodySigned = SignedAt(body, point), voidSigned = SignedAt(voids, point);
                    exactSharedZero = bodySigned == 0 && voidSigned == 0;
                    if (exactSharedZero) exactZeroBoth++;
                    if (bodySigned < 0 && voidSigned < 0) strictNegativeOverlap++;
                    overlapSignedValues.Add(new { point_private = Components(point), body_sdf_native = bodySigned, void_sdf_native = voidSigned });
                }
                if (!solid && !fluid) missing++;
                if (solid && (x == 0 || y == 0 || z == 0 || x == shape[0]-1 || y == shape[1]-1 || z == shape[2]-1)) boundaryBody++;
                int index = x + shape[0] * (y + shape[1] * z);
                mask[index] = fluid && !exactSharedZero ? (byte)1 : (byte)0;
                zeroAsVoidMask[index] = fluid ? (byte)1 : (byte)0;
            }
        }
        Directory.CreateDirectory(destination);
        verifyInputs?.Invoke();
        string binary = Path.Combine(destination, "void-occupancy.bin");
        string sensitivityBinary = Path.Combine(destination, "void-occupancy-zero-as-void.bin");
        File.WriteAllBytes(binary, mask);
        File.WriteAllBytes(sensitivityBinary, zeroAsVoidMask);
        bool passed = overlap == exactZeroBoth && missing == 0 && boundaryBody == 0;
        var report = new
        {
            schema = "m64-picogk-occupancy-samples-private/v1",
            status = passed ? "native_sampling_passed_not_topology_qualification" : "native_partition_failed",
            VDB_sha256 = vdbSha, source_body_STL_sha256 = sourceSha, source_report_sha256 = reportSha,
            native_voxel_mm = voxel, sample_spacing_mm = step, sample_phase = phase,
            shape_xyz = shape, sample_count = total,
            index_order = "x + nx*(y + ny*z)",
            enclosure_bounds_private = new { min_mm = Components(bounds.vecMin), max_mm = Components(bounds.vecMax) },
            sample_position = "enclosure_min + (integer_index + phase)*sample_spacing; floor-sized inscribed lattice",
            occupied_body_samples = occupiedBody, occupied_void_samples = occupiedVoid,
            primary_strict_void_samples = occupiedVoid - exactZeroBoth,
            body_void_overlap_samples = overlap, body_void_missing_samples = missing,
            overlap_exact_zero_both_fields_samples = exactZeroBoth,
            overlap_strict_negative_both_fields_samples = strictNegativeOverlap,
            overlap_signed_values_private = overlapSignedValues,
            signed_value_units = "native narrow-band SDF voxel units; sign used only, not a distance in mm",
            primary_boundary_convention = "shared exact zero belongs to material; no epsilon or tolerance",
            sensitivity_boundary_convention = "shared exact zero belongs to void; no geometry is changed",
            other_overlap_contradictions = overlap - exactZeroBoth,
            occupied_body_samples_on_seed_boundary = boundaryBody,
            near_interface_samples_excluded = 0,
            native_byte_bool_witness_expected = expected, native_byte_bool_witness_actual = actual,
            occupancy_sha256 = Sha(binary),
            zero_as_void_occupancy_sha256 = Sha(sensitivityBinary),
            input_hashes_verified_after_sampling = vdbSha != null,
            application_assembly_sha256 = Sha(typeof(BoxSdf).Assembly.Location),
            native_library_sha256 = File.Exists("/app/picogk.26.2.so") ? Sha("/app/picogk.26.2.so") : null,
            elapsed_seconds = timer.Elapsed.TotalSeconds,
            peak_working_set_bytes = Process.GetCurrentProcess().PeakWorkingSet64,
            inputs_modified = false, channels_created = false,
            exhaustive_native_voxel_topology = false,
            CFD_domain_qualified = false, manufacturing_authorized = false
        };
        File.WriteAllText(Path.Combine(destination, "sampling-report.json"), JsonSerializer.Serialize(report, new JsonSerializerOptions { WriteIndented = true }));
        Console.WriteLine(JsonSerializer.Serialize(new { status = report.status, sample_count = total, overlap, missing, boundaryBody }));
        if (!passed) throw new InvalidDataException("Native partition/boundary screen failed; occupancy must not be flood-filled as valid");
    }

    if (witnessOnly)
    {
        BBox3 bounds = new(new Vector3(-14), new Vector3(14));
        using Voxels enclosure = new(library, new BoxSdf(bounds));
        using Voxels closedVoid = enclosure.voxBoolSubtract(hollow);
        Sample(hollow, closedVoid, bounds, Path.Combine(output, "hollow-cube"), null, null, null);
        using Voxels tunnel = new(library, new BoxSdf(new BBox3(new Vector3(-11, -1.5f, -1.5f), new Vector3(-5, 1.5f, 1.5f))));
        using Voxels opened = hollow.voxBoolSubtract(tunnel);
        using Voxels openedVoid = enclosure.voxBoolSubtract(opened);
        Sample(opened, openedVoid, bounds, Path.Combine(output, "cube-with-tunnel"), null, null, null);
    }
    else
    {
        string vdbSha = Sha(args[0]), reportSha = Sha(args[1]);
        if (vdbSha != sourceReport!.RootElement.GetProperty("openvdb").GetProperty("sha256").GetString())
            throw new InvalidDataException("Input VDB does not match its exact source report");
        var enclosureJson = sourceReport.RootElement.GetProperty("enclosure_bounds");
        Vector3 ReadVector(string name)
        {
            float[] values = enclosureJson.GetProperty(name).EnumerateArray().Select(e => e.GetSingle()).ToArray();
            if (values.Length != 3 || values.Any(v => !float.IsFinite(v))) throw new InvalidDataException("Invalid reported enclosure");
            return new Vector3(values[0], values[1], values[2]);
        }
        using OpenVdbFile fields = new(library, args[0]);
        if (fields.nFieldCount() != 4 || MathF.Abs(fields.fPicoGKVoxelSizeMM() - voxel) > 1e-6f)
            throw new InvalidDataException("Named VDB field count or voxel scale mismatch");
        using Voxels body = fields.voxGet("head_body");
        using Voxels voids = fields.voxGet("unclassified_void_complement");
        Sample(body, voids, new BBox3(ReadVector("min_mm"), ReadVector("max_mm")), output,
            vdbSha, sourceReport.RootElement.GetProperty("input_sha256").GetString(), reportSha,
            () => { if (Sha(args[0]) != vdbSha || Sha(args[1]) != reportSha) throw new InvalidDataException("Input bytes changed during sampling"); });
        if (Sha(args[0]) != vdbSha || Sha(args[1]) != reportSha) throw new InvalidDataException("Input bytes changed during sampling");
    }
    sourceReport?.Dispose();
    return 0;
}
catch (Exception error)
{
    File.WriteAllText(Path.Combine(output, "FAILED.json"), JsonSerializer.Serialize(new
    {
        status = "failed", error = error.Message, error_type = error.GetType().Name,
        elapsed_seconds = timer.Elapsed.TotalSeconds, manufacturing_authorized = false
    }));
    Console.Error.WriteLine(error.Message);
    return 1;
}

sealed class BoxSdf(BBox3 bounds) : IBoundedImplicit
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

// Isolated adapter for the pinned kernel's C++ bool (one byte), not default BOOL.
static class NativeOccupancy
{
    [UnsafeAccessor(UnsafeAccessorKind.Field, Name = "hThis")]
    private static extern ref LibHandle LibraryHandle(Library value);
    [UnsafeAccessor(UnsafeAccessorKind.Field, Name = "hThis")]
    private static extern ref VoxHandle VoxelHandle(Voxels value);
    [DllImport("picogk.26.2", CallingConvention = CallingConvention.Cdecl, EntryPoint = "Voxels_bIsInside")]
    private static extern byte InsideByte(LibHandle library, VoxHandle field, in Vector3 point);
    public static bool Inside(Library library, Voxels field, in Vector3 point)
    {
        byte value = InsideByte(LibraryHandle(library), VoxelHandle(field), point);
        if (value > 1) throw new InvalidDataException("Native bool returned a value outside 0/1");
        GC.KeepAlive(field);
        GC.KeepAlive(library);
        return value == 1;
    }
}
