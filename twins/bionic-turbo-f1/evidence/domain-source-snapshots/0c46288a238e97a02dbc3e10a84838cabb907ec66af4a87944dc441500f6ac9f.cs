using System.Buffers.Binary;
using System.Numerics;
using System.Security.Cryptography;
using System.Text.Json;
using System.Text.Json.Serialization;
using PicoGK;
using PicoGKCatalog;

static class Program
{
    const float SourceVoxel = .5f, Voxel = .25f, MaskExpansion = 1, InletZ = 44, OutletY = 80, OutletPretrimY = 81;
    const float RearSealRadius = 35.5f, FluidRegularization = .125f, RequiredSurfaceProximity = .65f;
    static readonly Dictionary<string, string> RotorHashes = new()
    {
        ["compressor-wheel"] = "4bf63312713c244d35773172f693ab35a4b8c119c2f14dad584a78ebe145aa19",
        ["shaft"] = "a4171345a1e0f4b2483ee8a40c0ab00fdf8c46f198f06fd8c1475fa65d226348",
        ["compressor-nut"] = "b30889e417fd3281ffcb78e2748a8bfca0c1154ce6661034805de0b3ab4738a6"
    };
    static readonly JsonSerializerOptions Json = new()
    {
        PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower,
        UnmappedMemberHandling = JsonUnmappedMemberHandling.Disallow,
        RespectRequiredConstructorParameters = true,
        WriteIndented = true
    };
    static void Require(bool condition, string message)
    { if (!condition) throw new InvalidDataException(message); }
    static string Sha(byte[] bytes) => Convert.ToHexString(SHA256.HashData(bytes)).ToLowerInvariant();
    static float RearSeal(Vector3 p) => Sdf.CylZ(p, 0, 0, RearSealRadius, -100, -3.75f);
    static float Extension(Vector3 p) => RotKit.Rod(p, new(49, 40, 0), new(49, OutletPretrimY, 0), 14);
    static float InletHalfSpace(Vector3 p) => p.Z - InletZ;
    static float OutletBeyond(Vector3 p) => MathF.Max(OutletY - p.Y,
        new Vector2(p.X - 49, p.Z).Length() - 16);
    static void ValidateParameters(Parameters p)
    {
        Require(p == new Parameters(SourceVoxel, 3.5f, 22, 34, 28, 18, 8, 49, 6, 14, 42.25f, 2.2f, 8,
                p.VoluteLaw, p.ChamberProfile, p.ShroudRadialClearanceMm, p.RegularizationMm)
            && (p.VoluteLaw is null ? p.ChamberProfile is null && p.ShroudRadialClearanceMm is null && p.RegularizationMm is null
                : p.VoluteLaw is "radius_linear" or "area_affine" && p.ChamberProfile is "conical" or "wheel_shroud"
                    && p.ShroudRadialClearanceMm == 1.5f && p.RegularizationMm is float distance
                    && float.IsFinite(distance) && distance >= .5f && distance <= 1 && distance <= p.WallMm / 4),
            "Unsupported housing parameters: only the fixed F0/F1 source geometry at 0.5 mm is supported.");
    }
    static Parameters ReadParameters(JsonElement report)
    {
        JsonElement element = report.GetProperty("parameters");
        string[] keys = element.EnumerateObject().Select(x => x.Name).ToArray();
        Require(keys.Distinct().Count() == keys.Length, "Duplicate housing parameter.");
        Parameters p = JsonSerializer.Deserialize<Parameters>(element, Json)
            ?? throw new InvalidDataException("Missing housing parameters.");
        ValidateParameters(p);
        return p;
    }
    static string NewTarget(string path)
    {
        string target = Path.GetFullPath(path);
        Require(!File.Exists(target) && !Directory.Exists(target), "Output exists; refusing to overwrite.");
        return target;
    }
    static int BinaryTriangles(byte[] bytes)
    {
        Require(bytes.Length >= 84, "Truncated binary STL.");
        uint count = BinaryPrimitives.ReadUInt32LittleEndian(bytes.AsSpan(80, 4));
        Require(count > 0 && count <= int.MaxValue && bytes.LongLength == 84L + count * 50L,
            "Expected nonempty binary STL with exact triangle record length.");
        return (int)count;
    }
    static byte[] Asset(string directory, JsonElement report, string filename, string? pinned = null)
    {
        JsonElement[] entries = report.GetProperty("files").EnumerateArray()
            .Where(x => x.GetProperty("file").GetString() == filename).ToArray();
        Require(entries.Length == 1, "Missing or duplicate file in report: " + filename);
        byte[] bytes = File.ReadAllBytes(Path.Combine(directory, filename));
        string actual = Sha(bytes);
        Require(actual == entries[0].GetProperty("sha256").GetString(), "Report hash mismatch: " + filename);
        Require(pinned is null || actual == pinned, "F0 rotor identity mismatch: " + filename);
        int triangles = BinaryTriangles(bytes);
        Require(triangles == entries[0].GetProperty("triangles").GetInt32(), "Report triangle count mismatch: " + filename);
        return bytes;
    }
    static int SelfTest()
    {
        Require(SourceVoxel == .5f && Voxel == .25f && FluidRegularization == .125f,
            "Source/fluid resolution separation self-test failed.");
        var p = new Parameters(SourceVoxel, 3.5f, 22, 34, 28, 18, 8, 49, 6, 14, 42.25f, 2.2f, 8, "area_affine", "wheel_shroud", 1.5f, .625f);
        ValidateParameters(p);
        foreach (string law in new[] { "radius_linear", "area_affine" })
            foreach (string chamber in new[] { "conical", "wheel_shroud" })
            {
                using JsonDocument report = JsonDocument.Parse(JsonSerializer.Serialize(new
                { parameters = p with { VoluteLaw = law, ChamberProfile = chamber } }, Json));
                ReadParameters(report.RootElement);
            }
        ValidateParameters(p with { VoluteLaw = null, ChamberProfile = null, ShroudRadialClearanceMm = null, RegularizationMm = null });
        void Reject(Action operation)
        {
            bool rejected = false;
            try { operation(); } catch (InvalidDataException) { rejected = true; } catch (JsonException) { rejected = true; }
            Require(rejected, "Expected rejection in self-test.");
        }
        Reject(() => ValidateParameters(p with { VoxelMm = .75f }));
        Reject(() => ValidateParameters(p with { VoxelMm = Voxel }));
        Reject(() => ValidateParameters(p with { VoluteLaw = "unknown" }));
        Reject(() => ValidateParameters(p with { ChamberProfile = "unknown" }));
        Reject(() => ValidateParameters(p with { ChamberProfile = null }));
        Reject(() => ValidateParameters(p with { ShroudRadialClearanceMm = null }));
        Reject(() => ValidateParameters(p with { ShroudRadialClearanceMm = 2 }));
        Reject(() => ValidateParameters(p with { RegularizationMm = null }));
        Reject(() => ValidateParameters(p with { RegularizationMm = float.NaN }));
        Reject(() => ValidateParameters(p with { RegularizationMm = .25f }));
        Reject(() => ValidateParameters(p with { RegularizationMm = .9f }));
        Reject(() => ValidateParameters(p with { InletRadiusMm = float.NaN }));
        string serialized = JsonSerializer.Serialize(p, Json);
        Reject(() => JsonSerializer.Deserialize<Parameters>(serialized.Replace("\"rib_count\"", "\"rib_typo\""), Json));
        Require(RearSeal(new(20, 0, -5)) < 0 && RearSeal(new(36, 0, -5)) > 0
            && RearSeal(new(34.6f, 0, -8)) < 0
            && RearSeal(new(20, 0, -3.75f)) == 0, "Rear sealing field self-test failed.");
        Require(InletHalfSpace(new(15, 0, 44)) == 0 && InletHalfSpace(new(15, 0, 43)) < 0,
            "Inlet plane self-test failed.");
        Require(Extension(new(49, 80, 0)) < 0 && Extension(new(49, 81, 0)) == 0
            && Extension(new(49, 82, 0)) > 0 && Extension(new(64, 60, 0)) > 0,
            "Outlet extension field self-test failed.");
        Require(OutletBeyond(new(49, 80, 0)) == 0 && OutletBeyond(new(49, 81, 0)) < 0
            && OutletBeyond(new(0, 60, 0)) > 0, "Local outlet recapping self-test failed.");
        byte[] stl = new byte[134];
        BinaryPrimitives.WriteUInt32LittleEndian(stl.AsSpan(80, 4), 1);
        Require(BinaryTriangles(stl) == 1, "Binary STL self-test failed.");
        Reject(() => BinaryTriangles(stl[..133]));
        Reject(() => NewTarget(AppContext.BaseDirectory));
        DirectoryInfo temporary = Directory.CreateTempSubdirectory("bionic-cfd-selftest-");
        try
        {
            File.WriteAllBytes(Path.Combine(temporary.FullName, "sample.stl"), stl);
            using JsonDocument report = JsonDocument.Parse(JsonSerializer.Serialize(new
            {
                files = new[] { new { file = "sample.stl", sha256 = Sha(stl), triangles = 1 } }
            }));
            Require(Asset(temporary.FullName, report.RootElement, "sample.stl", Sha(stl)).Length == 134,
                "Asset hash self-test failed.");
            Reject(() => Asset(temporary.FullName, report.RootElement, "sample.stl", new string('0', 64)));
            stl[0] = 1;
            File.WriteAllBytes(Path.Combine(temporary.FullName, "sample.stl"), stl);
            Reject(() => Asset(temporary.FullName, report.RootElement, "sample.stl"));
        }
        finally
        {
            File.Delete(Path.Combine(temporary.FullName, "sample.stl"));
            temporary.Delete();
        }
        Console.WriteLine("SELF_TEST_PASS: source/fluid resolution separation, fixed parameters, cuts, extension, STL structure, input hashes and no-overwrite checks; no native geometry.");
        return 0;
    }
    public static int Main(string[] args)
    {
        if (args is ["--self-test"]) return SelfTest();
        if (args.Length != 3)
        {
            Console.Error.WriteLine("Usage: CfdGeometry HOUSING_RUN F0_ASSEMBLY_RUN NEW_OUTPUT_DIR | --self-test");
            return 2;
        }
        string? output = null;
        try
        {
            string target = NewTarget(args[2]);
            byte[] housingReportBytes = File.ReadAllBytes(Path.Combine(args[0], "report.json"));
            byte[] assemblyReportBytes = File.ReadAllBytes(Path.Combine(args[1], "report.json"));
            using JsonDocument housingReport = JsonDocument.Parse(housingReportBytes);
            using JsonDocument assemblyReport = JsonDocument.Parse(assemblyReportBytes);
            JsonElement h = housingReport.RootElement, a = assemblyReport.RootElement;
            Require(h.GetProperty("status").GetString() == "concept_geometry_generated"
                && h.GetProperty("units").GetString() == "mm", "Unsupported housing report.");
            Require(a.GetProperty("status").GetString() == "concept_assembly_generated"
                && a.GetProperty("units").GetString() == "mm" && a.GetProperty("voxel_mm").GetSingle() == SourceVoxel,
                "Unsupported assembly report.");
            Parameters parameters = ReadParameters(h);
            var sources = new Dictionary<string, byte[]>
            {
                ["housing-final.stl"] = Asset(args[0], h, "housing.stl"),
                ["flow-domain-source.stl"] = Asset(args[0], h, "flow-domain.stl")
            };
            foreach (var (id, hash) in RotorHashes) sources[id + "-source.stl"] = Asset(args[1], a, id + ".stl", hash);
            Directory.CreateDirectory(target);
            output = target;
            var files = new List<object>();
            foreach (var (name, bytes) in sources)
            {
                File.WriteAllBytes(Path.Combine(output, name), bytes);
                files.Add(new { file = name, sha256 = Sha(bytes), triangles = BinaryTriangles(bytes), role = "exact_input_copy" });
            }
            File.WriteAllBytes(Path.Combine(output, "housing-input-report.json"), housingReportBytes);
            File.WriteAllBytes(Path.Combine(output, "assembly-input-report.json"), assemblyReportBytes);
            using Library lib = new(Voxel);
            Voxels Load(string name)
            {
                using Mesh mesh = Mesh.mshFromStlFile(Path.Combine(output, name), Mesh.EStlUnit.MM, libSet: lib);
                return new Voxels(mesh);
            }
            void Save(string name, Voxels voxels, string role)
            {
                using Mesh mesh = new(voxels);
                voxels.CalculateProperties(out float volume, out BBox3 bounds);
                Require(mesh.nTriangleCount() > 0 && float.IsFinite(volume) && volume > 0, "Empty geometry: " + name);
                string path = Path.Combine(output, name);
                mesh.SaveToStlFile(path, Mesh.EStlUnit.MM);
                byte[] bytes = File.ReadAllBytes(path);
                Require(BinaryTriangles(bytes) == mesh.nTriangleCount(), "Export triangle mismatch: " + name);
                files.Add(new { file = name, sha256 = Sha(bytes), triangles = mesh.nTriangleCount(), role,
                    voxel_volume_mm3 = volume, bounds_min_mm = new[] { bounds.vecMin.X, bounds.vecMin.Y, bounds.vecMin.Z },
                    bounds_max_mm = new[] { bounds.vecMax.X, bounds.vecMax.Y, bounds.vecMax.Z } });
            }
            using Voxels housing = Load("housing-final.stl");
            using Voxels nominal = Load("flow-domain-source.stl");
            using Voxels mask = nominal.voxOffset(MaskExpansion);
            using Voxels rotor = Load("compressor-wheel-source.stl");
            foreach (string id in new[] { "shaft", "compressor-nut" })
            {
                using Voxels part = Load(id + "-source.stl");
                rotor.BoolAdd(part);
            }
            using Voxels extension = Sdf.Vox(lib, Extension, new(33, 38, -16), new(65, 82, 16));
            using Voxels seal = Sdf.Vox(lib, RearSeal, new(-38, -38, -102), new(38, 38, -1));
            using Voxels inlet = Sdf.Vox(lib, InletHalfSpace, new(-100, -100, -110), new(100, 100, 60));
            using Voxels outletBeyond = Sdf.Vox(lib, OutletBeyond, new(31, 78, -18), new(67, 90, 18));
            using Voxels fluid = mask.voxDuplicate();
            fluid.BoolAdd(extension);
            fluid.BoolSubtract(seal);
            // Final imported solids, not the nominal mask, define actual walls wherever they bound this ideal domain.
            fluid.BoolSubtract(housing);
            fluid.BoolSubtract(rotor);
            fluid.CalculateProperties(out float unregularizedVolume, out _);
            // Remove voxel-scale Boolean remnants in the volume; never repair or discard extracted triangles.
            fluid.Smoothen(FluidRegularization);
            // Cut only after smoothing: an earlier cap would leave a rounded rim below the final plane.
            fluid.BoolIntersect(inlet);
            fluid.BoolSubtract(outletBeyond);
            fluid.CalculateProperties(out float regularizedVolume, out _);
            var probes = new List<object>();
            void Probe(string id, Vector3 point, bool expected)
            {
                bool actual = fluid.bIsInside(point);
                Require(actual == expected, "Fluid occupancy probe failed: " + id);
                probes.Add(new { id, point_mm = new[] { point.X, point.Y, point.Z }, expected_fluid = expected, actual_fluid = actual, passed = true });
            }
            Probe("connected-domain-seed", new(15, 0, 40), true);
            Probe("outlet-extension", new(49, 70, 0), true);
            Probe("shaft-solid", new(0, 0, 10), false);
            Probe("wheel-solid", new(10, 0, -1), false);
            Probe("rear-ideal-seal", new(20, 0, -6), false);
            Probe("former-rear-pocket", new(-34.25f, 0, -7.5f), false);
            Probe("above-inlet-cap", new(15, 0, 46), false);
            Probe("beyond-outlet-cap", new(49, 82, 0), false);
            Probe("external-space", new(80, 0, 0), false);
            Save("nominal-mask.stl", mask, "expanded_nominal_clipping_mask_for_proximity_audit");
            Save("outlet-extension.stl", extension, "ideal_outlet_extension_before_final_cap");
            Save("rear-seal.stl", seal, "ideal_rear_closure_not_a_real_component");
            Save("rotor-union.stl", rotor, "imported_rotating_obstacles_may_be_disconnected");
            Save("fluid.stl", fluid, "ideal_compressor_fluid_pending_independent_qa");
            File.WriteAllText(Path.Combine(output, "report.json"), JsonSerializer.Serialize(new
            {
                schema_version = 1, status = "ideal_fluid_geometry_generated_pending_qa", units = "mm", voxel_mm = Voxel,
                source_voxel_mm = SourceVoxel,
                kernel = Library.strVersion(), exact_real_assembly = false, engineering_validated = false,
                manufacturing_authorized = false, performance_gain_validated = false, housing_parameters = parameters,
                construction = new { nominal_mask_expansion_mm = MaskExpansion, inlet_cap_z_mm = InletZ,
                    outlet_extension_x_mm = 49, outlet_extension_z_mm = 0, outlet_extension_radius_mm = 14,
                    outlet_extension_y_start_mm = 40, outlet_extension_pretrim_y_end_mm = OutletPretrimY,
                    outlet_cap_y_mm = OutletY, outlet_cap_applies_to = "extension_only",
                    rear_seal_radius_mm = RearSealRadius, rear_seal_top_z_mm = -3.75, final_fluid_smoothing = true,
                    final_fluid_regularization_mm = FluidRegularization,
                    unregularized_volume_mm3 = unregularizedVolume, regularized_volume_mm3 = regularizedVolume,
                    cap_planes_applied_only_after_regularization = true,
                    volume_method = "PicoGK CalculateProperties; not equivalent to net signed STL volume with obstacle boundaries",
                    required_source_surface_proximity_mm = RequiredSurfaceProximity,
                    source_surface_proximity_verified = false,
                    operations = "(offset(nominal,1mm) union outlet_extension_to_y81) minus rear_seal, imported_final_housing and imported_rotor_union; Smoothen(0.125mm), then cut z44 and extension-local y80" },
                input_report_sha256 = new { housing = Sha(housingReportBytes), assembly = Sha(assemblyReportBytes) },
                pinned_f0_rotor_sha256 = RotorHashes, native_probes = probes, files,
                limitations = new[] {
                    "This is an intentionally sealed compressor-only numerical domain, not the real 39-part assembly.",
                    "The 1 mm expanded nominal domain is only a clipping mask; independent proximity QA must reject unintended mask-bounded walls.",
                    "Source STL surfaces generated at 0.5 mm are revoxelized at 0.25 mm; exact source copies permit independent surface-deviation inspection. Finer fluid voxels do not increase the source geometry accuracy.",
                    "Fluid regularization by 0.125 mm moves boundary surfaces; independent QA must enforce 0.65 mm proximity to source housing/rotor outside explicit idealizations.",
                    "The rear ideal seal extends to radius 35.5 mm to remove the nominal-mask lip and disconnected rear fluid pockets observed in run 001.",
                    "Rear closure and extended outlet are declared idealizations; the extension alone ends at y80, without cutting the scroll.",
                    "PicoGK CalculateProperties volumes are kernel diagnostics, not interchangeable with independently computed net signed STL fluid volume.",
                    "Rotor parts remain separate where their original assumed clearances separate them; no artificial solid bridges are added.",
                    "Point occupancy does not establish connected fluid topology, patch correctness, boundary-layer resolution or solver readiness.",
                    "No flow, efficiency, rotation, heat transfer or bearing behavior has been simulated." }
            }, Json) + "\n");
            Console.WriteLine("IDEAL_FLUID_GENERATED: independent topology, proximity and patch QA required.");
            return 0;
        }
        catch (Exception error)
        {
            if (output is not null) File.WriteAllText(Path.Combine(output, "FAILED.json"),
                JsonSerializer.Serialize(new { status = "failed", error = error.Message, exact_real_assembly = false }, Json));
            Console.Error.WriteLine(error.Message);
            return 1;
        }
    }
}

sealed record Parameters(float VoxelMm, float WallMm, float InletRadiusMm, float RearOpeningRadiusMm,
    float ChamberHeightMm, float InletNeckLengthMm, float DiffuserHeightMm, float VoluteCenterRadiusMm,
    float VoluteStartRadiusMm, float VoluteEndRadiusMm, float OutletLengthMm, float RibRadiusMm, int RibCount,
    string? VoluteLaw = null, string? ChamberProfile = null, float? ShroudRadialClearanceMm = null, float? RegularizationMm = null);
