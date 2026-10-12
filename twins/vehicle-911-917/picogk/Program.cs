using System.Numerics;
using System.Text.Json;
using PicoGK;

namespace Vehicle911917;

internal static partial class Program
{
    private static readonly bool VehicleStudy = Environment.GetEnvironmentVariable("PICOGK_VEHICLE_F15") == "1";
    private static readonly bool AxleStudy = Environment.GetEnvironmentVariable("PICOGK_STUDY_F14") == "1";
    private static readonly string Root = Environment.GetEnvironmentVariable("REPOSITORY_ROOT")
        ?? throw new InvalidOperationException("REPOSITORY_ROOT absent");
    private static readonly string Input = Environment.GetEnvironmentVariable("PICOGK_INPUT_DIR")
        ?? Path.Combine(Root, "work", "911-917-picogk-f10");
    private static readonly string Output = Environment.GetEnvironmentVariable("PICOGK_OUTPUT_DIR")
        ?? Path.Combine(Root, "work", VehicleStudy ? "911-917-picogk-f15" : AxleStudy ? "911-917-picogk-f14" : "911-917-picogk-f13");
    private static readonly float VoxelMm = float.Parse(
        Environment.GetEnvironmentVariable("PICOGK_VOXEL_MM") ?? (AxleStudy ? "2" : "5"),
        System.Globalization.CultureInfo.InvariantCulture);

    private static void Main()
    {
        if (VehicleStudy && AxleStudy)
            throw new InvalidDataException("Select only one study");
        if (VehicleStudy)
            ValidateVehicleInputs();
        Directory.CreateDirectory(Output);
        Library.Go(
            VoxelMm,
            VehicleStudy ? RunVehicleStudy : AxleStudy ? RunAxleStudy : Run,
            strLogFilePath: Path.Combine(Output, VehicleStudy ? "picogk-f15.log" : AxleStudy ? "picogk-f14.log" : "picogk-f13.log"),
            bEndAppWithTask: true,
            strWindowTitle: VehicleStudy ? "911-917 Vehicle Packaging F15" : "911-917 Mechanical Assembly F13");
    }

    private static void Run()
    {
        try
        {
            using JsonDocument packaging = LoadJson("work/911-917-packaging-f1/packaging-report-f1.json");
            using JsonDocument concept = LoadJson("twins/vehicle-911-917/packaging-concept-f1.json");
            using JsonDocument model = LoadJson("twins/vehicle-911-917/picogk-full-vehicle-f12.json");
            using JsonDocument mechanical = LoadJson("twins/vehicle-911-917/picogk-mechanical-f13.json");
            using JsonDocument alignment = JsonDocument.Parse(File.ReadAllText(Path.Combine(Output, "scan-alignment-f13.json")));
            JsonElement layout = SelectedLayout(packaging.RootElement);
            JsonElement screening = packaging.RootElement.GetProperty("layout_screening");
            JsonElement vehicle = screening.GetProperty("vehicle_reference_mm");
            JsonElement engineEnvelope = screening.GetProperty("engine_service_envelope_mm");
            JsonElement body = concept.RootElement.GetProperty("body_and_occupant_screening_mm");
            JsonElement f12 = model.RootElement;
            JsonElement f13 = mechanical.RootElement;

            float serviceStart = layout.GetProperty("engine_service_bounds_x_mm")[0].GetSingle();
            float serviceEnd = layout.GetProperty("engine_service_bounds_x_mm")[1].GetSingle();
            float gearboxStart = layout.GetProperty("gearbox_bounds_x_mm")[0].GetSingle();
            float gearboxEnd = layout.GetProperty("gearbox_bounds_x_mm")[1].GetSingle();
            float rearAxle = layout.GetProperty("rear_axle_x_mm").GetSingle();
            float bodyFront = layout.GetProperty("body_front_x_mm").GetSingle();
            float bodyRear = layout.GetProperty("body_rear_x_mm").GetSingle();
            float bodyWidth = vehicle.GetProperty("overall_width").GetSingle();
            float bodyHeight = vehicle.GetProperty("overall_height").GetSingle();
            float frontTrack = vehicle.GetProperty("front_track").GetSingle();
            float rearTrack = vehicle.GetProperty("rear_track").GetSingle();
            float serviceWidth = engineEnvelope.GetProperty("width").GetSingle();
            float serviceHeight = engineEnvelope.GetProperty("height").GetSingle();
            float floorZ = body.GetProperty("powertrain_floor_z").GetSingle();
            float firewallX = body.GetProperty("powertrain_firewall_x").GetSingle();
            float occupantRearX = body.GetProperty("front_occupant_rear_limit_x").GetSingle();
            float firewallClearance = body.GetProperty("minimum_firewall_to_engine_service_clearance").GetSingle();

            Library lib = Library.oLibrary();
            string scanPath = Path.Combine(Input, "917-engine-oriented-f10.stl");
            using (var stream = File.OpenRead(scanPath))
                if (!Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(stream)).Equals(
                    alignment.RootElement.GetProperty("input_stl_sha256").GetString(), StringComparison.OrdinalIgnoreCase))
                    throw new InvalidDataException("Le scan diffère de celui du recalage F13");
            float[] matrix = alignment.RootElement.GetProperty("matrix4x4_row_vector").EnumerateArray()
                .SelectMany(row => row.EnumerateArray().Select(v => v.GetSingle())).ToArray();
            using Mesh sourceMesh = Mesh.mshFromStlFile(
                scanPath,
                Mesh.EStlUnit.MM,
                libSet: lib);
            using Mesh scanMesh = sourceMesh.mshCreateTransformed(new Matrix4x4(
                matrix[0], matrix[1], matrix[2], matrix[3], matrix[4], matrix[5], matrix[6], matrix[7],
                matrix[8], matrix[9], matrix[10], matrix[11], matrix[12], matrix[13], matrix[14], matrix[15]));
            using Voxels scan = Voxels.voxMeshShell(lib, scanMesh, VoxelMm / 2f);
            using Voxels service = Box(lib,
                new Vector3(serviceEnd - serviceStart, serviceWidth, serviceHeight),
                new Vector3((serviceStart + serviceEnd) / 2f, 0, floorZ + serviceHeight / 2f));
            using Mesh bodyMesh = BodyEnvelopeMesh(lib, bodyFront, bodyRear, bodyWidth, bodyHeight, rearAxle);
            using Voxels bodyShell = Voxels.voxMeshShell(lib, bodyMesh, 10);
            using Voxels bodyOutline = BuildBodyOutline(lib, bodyFront, bodyRear, bodyWidth, bodyHeight, rearAxle);
            using Voxels structure = BuildStructure(lib, f12.GetProperty("rear_structure_corridors"),
                bodyWidth, bodyHeight, bodyRear, floorZ, firewallX, firewallClearance,
                occupantRearX, serviceWidth, serviceHeight);
            float shaftZ = f13.GetProperty("shaft_reference_z_mm").GetSingle();
            float axleZ = f12.GetProperty("wheel_reservation").GetProperty("centre_z_mm").GetSingle();
            using Voxels transmission = BuildTransmission(lib, f13.GetProperty("transaxle"),
                gearboxStart, gearboxEnd, rearAxle, shaftZ, axleZ);
            JsonElement turboConfig = f13.GetProperty("turbos");
            using Voxels turboLeft = BuildTurbo(lib, turboConfig, Vec3(turboConfig.GetProperty("centres_mm")[0]));
            using Voxels turboRight = BuildTurbo(lib, turboConfig, Vec3(turboConfig.GetProperty("centres_mm")[1]));
            using Voxels exhaust = Paths(lib, f12.GetProperty("exhaust_routes"));
            using Voxels cooling = BuildCooling(lib, f12);
            using Voxels wing = BuildWing(lib, f12.GetProperty("wing_cooling_system"));
            using Voxels runningGear = BuildRunningGear(lib, f12.GetProperty("wheel_reservation"),
                frontTrack, rearTrack, rearAxle);
            using Voxels shafts = BuildHalfshafts(lib, f13, rearAxle, rearTrack, axleZ);
            using Voxels axisGuides = BuildAxisGuides(lib, serviceStart, gearboxEnd, frontTrack, rearTrack, rearAxle, axleZ, shaftZ);
            using Voxels shaftConflict = shafts & structure;

            var layers = new (string Key, Voxels Geometry, int Group, string Status)[]
            {
                ("engine_scan", scan, 0, "observed_open_scan_shell_scale_and_orientation_unverified"),
                ("complete_engine_envelope", service, 1, "unmeasured_screening_hypothesis"),
                ("body_shell", bodyShell, 2, "documentary_dimensions_hypothetical_profile"),
                ("structure_and_firewall", structure, 3, f12.GetProperty("rear_structure_corridors").GetProperty("status").GetString()!),
                ("transaxle_schematic", transmission, 4, f13.GetProperty("transaxle").GetProperty("status").GetString()!),
                ("turbo_left", turboLeft, 5, turboConfig.GetProperty("status").GetString()!),
                ("intake_and_cooling_ducts", cooling, 6, "unmeasured_flow_path_packaging_hypothesis"),
                ("fixed_wing_and_heat_exchanger", wing, 7, f12.GetProperty("wing_cooling_system").GetProperty("status").GetString()!),
                ("wheels_and_hubs", runningGear, 8, f12.GetProperty("wheel_reservation").GetProperty("status").GetString()!),
                ("turbo_right", turboRight, 9, turboConfig.GetProperty("status").GetString()!),
                ("rear_halfshafts_and_CV_joints", shafts, 10, f13.GetProperty("halfshafts").GetProperty("status").GetString()!),
                ("axis_reference_lines", axisGuides, 11, "reference_lines_not_physical_axles_or_crankshaft"),
                ("exhaust_routes", exhaust, 12, "routing_reservation_not_measured_manifold"),
                ("halfshaft_structure_interference", shaftConflict, 13, "unresolved_collision_inherited_structure_corridors"),
                ("body_profile_reference", bodyOutline, 14, "profile_reference_not_measured_surface")
            };

            ConfigureViewer(layers);
            CaptureViews(layers);
            foreach (var layer in layers)
                layer.Geometry.SaveToVdbFile(Path.Combine(Output, $"{layer.Key}-f13.vdb"));
            using Voxels assembly = Voxels.voxCombineAll(lib, layers.Where(layer => layer.Group < 11 || layer.Group == 12).Select(layer => layer.Geometry).ToArray());
            assembly.SaveToVdbFile(Path.Combine(Output, "911-917-mechanical-assembly-f13.vdb"));

            float residual = serviceStart - (firewallX + firewallClearance);
            var layerReport = layers.ToDictionary(
                layer => layer.Key,
                layer => (object?)new Dictionary<string, object?>
                {
                    ["status"] = layer.Status,
                    ["vdb"] = $"{layer.Key}-f13.vdb",
                    ["properties"] = Properties(layer.Geometry)
                });
            var report = new Dictionary<string, object?>
            {
                ["schema_version"] = "1.0.0",
                ["phase"] = "F13",
                ["status"] = "corrected_scan_alignment_and_schematic_mechanical_assembly",
                ["alignment"] = alignment.RootElement.Clone(),
                ["kinematic_references"] = new Dictionary<string, object?>
                {
                    ["rear_axle_x_mm"] = rearAxle,
                    ["differential_x_mm"] = rearAxle,
                    ["shaft_reference_z_mm"] = shaftZ,
                    ["differential_output_z_mm"] = axleZ,
                    ["rear_hub_centres_mm"] = new[] {new[] {rearAxle, -rearTrack / 2, axleZ}, new[] {rearAxle, rearTrack / 2, axleZ}},
                    ["halfshaft_outer_joint_centres_mm"] = new[] {new[] {rearAxle, -rearTrack / 2, axleZ}, new[] {rearAxle, rearTrack / 2, axleZ}}
                },
                ["kernel"] = new Dictionary<string, object?>
                {
                    ["name"] = "PicoGK",
                    ["package_version"] = "2.3.0",
                    ["runtime_version"] = Library.strVersion(),
                    ["voxel_size_mm"] = VoxelMm
                },
                ["scope"] = new Dictionary<string, object?>
                {
                    ["complete_vehicle_model"] = false,
                    ["all_components_dimensionally_verified"] = false,
                    ["scan_triangle_count"] = scanMesh.nTriangleCount(),
                    ["transaxle_selected"] = false,
                    ["transaxle_representation"] = "schematic_bellhousing_case_and_differential_not_supplier_CAD",
                    ["turbo_count"] = 2,
                    ["rear_halfshaft_count"] = 2,
                    ["front_driven_axle"] = false
                },
                ["layers"] = layerReport,
                ["checks"] = new Dictionary<string, object?>
                {
                    ["firewall_required_clearance_mm"] = firewallClearance,
                    ["firewall_residual_above_requirement_mm"] = residual,
                    ["firewall_clearance_resolved_at_voxel_size"] = residual >= VoxelMm,
                    ["engine_scan_vs_structure_and_firewall"] = Collision(scan, structure),
                    ["engine_scan_vs_transaxle"] = Collision(scan, transmission),
                    ["left_turbo_vs_engine_scan"] = Collision(turboLeft, scan),
                    ["right_turbo_vs_engine_scan"] = Collision(turboRight, scan),
                    ["halfshafts_vs_structure"] = Collision(shafts, structure)
                },
                ["images"] = new[]
                {
                    new Dictionary<string, string> { ["file"] = "picogk-mechanical-f13-top.tga", ["caption"] = "Dessus : moteur aligné, boîte-pont, deux turbos et demi-arbres" },
                    new Dictionary<string, string> { ["file"] = "picogk-mechanical-f13-isometric.tga", ["caption"] = "Assemblage mécanique sans coque ni enveloppe occultante" },
                    new Dictionary<string, string> { ["file"] = "picogk-mechanical-f13-side.tga", ["caption"] = "Profil : implantation mécanique dans la caisse" },
                    new Dictionary<string, string> { ["file"] = "picogk-mechanical-f13-full-top.tga", ["caption"] = "Dessus véhicule : roues, lignes d'essieux et transmission arrière" }
                },
                ["assembly_vdb"] = "911-917-mechanical-assembly-f13.vdb",
                ["limitations"] = f13.GetProperty("limitations").Clone(),
                ["release_gates"] = BoolMap(f12.GetProperty("release_gates"))
            };
            File.WriteAllText(
                Path.Combine(Output, "picogk-mechanical-report-f13.json"),
                JsonSerializer.Serialize(report, new JsonSerializerOptions { WriteIndented = true }) + "\n");
            Library.Log("911-917 PicoGK mechanical correction F13 exported\n");
            Library.EndTask();
        }
        catch (Exception exception)
        {
            Library.Log("ERROR: " + exception + "\n");
            Library.EndTask();
            throw;
        }
    }

    private static void ConfigureViewer((string Key, Voxels Geometry, int Group, string Status)[] layers)
    {
        Viewer viewer = Library.oViewer();
        viewer.SetBackgroundColor("F3F4F6");
        viewer.SetFov(MathF.PI / 5f);
        viewer.SetGroupMaterial(0, "94A3B8", 0.1f, 0.65f); // scan
        viewer.SetGroupMaterial(1, "F59E0B28", 0.05f, 0.65f); // engine envelope
        viewer.SetGroupMaterial(2, "4F78A838", 0.35f, 0.45f); // body
        viewer.SetGroupMaterial(3, "EF44448A", 0.15f, 0.45f); // structure/firewall
        viewer.SetGroupMaterial(4, "7C3AED", 0.1f, 0.6f); // transmission
        viewer.SetGroupMaterial(5, "EA580C", 0.1f, 0.6f); // turbo left
        viewer.SetGroupMaterial(6, "06B6D4CC", 0.2f, 0.35f);  // intake/cooling
        viewer.SetGroupMaterial(7, "10B981B0", 0.4f, 0.35f);  // wing/radiator
        viewer.SetGroupMaterial(8, "334155", 0.1f, 0.7f); // wheels/hubs
        viewer.SetGroupMaterial(9, "EA580C", 0.1f, 0.6f); // turbo right
        viewer.SetGroupMaterial(10, "16A34A", 0.1f, 0.6f); // halfshafts
        viewer.SetGroupMaterial(11, "DC2626", 0, 0.9f); // datum lines
        viewer.SetGroupMaterial(12, "92400E", 0.1f, 0.65f); // exhaust
        viewer.SetGroupMaterial(13, "EF4444", 0, 0.8f); // unresolved interference
        viewer.SetGroupMaterial(14, "475569", 0, 0.9f); // body outline
    }

    private static void CaptureViews((string Key, Voxels Geometry, int Group, string Status)[] layers)
    {
        Viewer viewer = Library.oViewer();
        foreach (var layer in layers.Where(v => new[] {0, 4, 5, 9, 10, 13}.Contains(v.Group)))
            viewer.Add(layer.Geometry, layer.Group);
        Capture(viewer, viewer.qOrientationTop, "picogk-mechanical-f13-top.tga");
        Capture(viewer, viewer.qOrientationHome, "picogk-mechanical-f13-isometric.tga");
        viewer.RemoveAllObjects();
        foreach (var layer in layers.Where(v => new[] {0, 4, 5, 7, 8, 9, 10, 11, 14}.Contains(v.Group)))
            viewer.Add(layer.Geometry, layer.Group);
        Capture(viewer, viewer.qOrientationFront, "picogk-mechanical-f13-side.tga");
        viewer.RemoveAllObjects();
        foreach (var layer in layers.Where(v => new[] {0, 4, 5, 8, 9, 10, 11, 13}.Contains(v.Group)))
            viewer.Add(layer.Geometry, layer.Group);
        Capture(viewer, viewer.qOrientationTop, "picogk-mechanical-f13-full-top.tga");
    }

    private static void Capture(Viewer viewer, Quaternion orientation, string filename)
    {
        string path = Path.Combine(Output, filename);
        if (File.Exists(path))
            File.Delete(path);
        viewer.qOrientation = orientation;
        viewer.ZoomToFit();
        viewer.RequestScreenShot(path);
        for (int attempt = 0; attempt < 300; attempt++)
        {
            if (File.Exists(path) && new FileInfo(path).Length > 18)
                return;
            Thread.Sleep(50);
        }
        throw new TimeoutException($"capture PicoGK absente: {path}");
    }

    private static Voxels BuildTransmission(Library lib, JsonElement config, float start, float end, float axleX, float shaftZ, float axleZ)
    {
        float bell = config.GetProperty("bell_length_mm").GetSingle();
        float radius = config.GetProperty("bell_radius_mm").GetSingle();
        float width = config.GetProperty("case_width_mm").GetSingle();
        float height = config.GetProperty("case_height_mm").GetSingle();
        float flange = config.GetProperty("output_flange_half_span_mm").GetSingle();
        Voxels result = new(lib);
        AddFrustum(result, lib, new(start, 0, shaftZ), new(start + bell, 0, shaftZ), radius, width / 2);
        AddBox(result, lib, new(end - start - bell, width, height), new((end + start + bell) / 2, 0, shaftZ));
        AddFrustum(result, lib, new(axleX, -flange + 30, axleZ), new(axleX, flange - 30, axleZ),
            config.GetProperty("differential_radius_mm").GetSingle(), config.GetProperty("differential_radius_mm").GetSingle());
        foreach (float side in new[] {-1f, 1f})
            AddFrustum(result, lib, new(axleX, side * (flange - 35), axleZ), new(axleX, side * flange, axleZ), 65, 65);
        for (float x = start + bell + 30; x < end - 15; x += 90)
            AddBox(result, lib, new(12, width + 20, height + 20), new(x, 0, shaftZ));
        return result;
    }

    private static Voxels BuildTurbo(Library lib, JsonElement config, Vector3 centre)
    {
        Voxels result = new(lib);
        float spacing = config.GetProperty("housing_spacing_mm").GetSingle();
        float radius = config.GetProperty("scroll_radius_mm").GetSingle();
        float tube = config.GetProperty("scroll_tube_radius_mm").GetSingle();
        AddFrustum(result, lib, centre - Vector3.UnitX * spacing / 2, centre + Vector3.UnitX * spacing / 2, 45, 45);
        foreach (float side in new[] {-1f, 1f})
        {
            Vector3 housing = centre + Vector3.UnitX * side * spacing / 2;
            for (int n = 0; n < 48; n++)
            {
                float a = n * 2 * MathF.PI / 48, b = (n + 1) * 2 * MathF.PI / 48;
                Vector3 p = housing + new Vector3(0, radius * MathF.Cos(a), radius * MathF.Sin(a));
                Vector3 q = housing + new Vector3(0, radius * MathF.Cos(b), radius * MathF.Sin(b));
                using Voxels segment = Voxels.voxLatticeBeam(lib, p, tube, q, tube);
                result.BoolAdd(segment);
            }
            AddFrustum(result, lib, housing - Vector3.UnitX * 25, housing + Vector3.UnitX * 25, radius, radius);
            using Voxels opening = Frustum(lib, housing + Vector3.UnitX * side * 5, housing + Vector3.UnitX * side * 80, 40, 40);
            result.BoolSubtract(opening);
            AddFrustum(result, lib, housing + new Vector3(0, radius, 0), housing + new Vector3(0, radius, 110), tube, tube);
        }
        return result;
    }

    private static Voxels BuildCooling(Library lib, JsonElement config)
    {
        using Voxels intakes = Paths(lib, config.GetProperty("quarter_intake_ducts"));
        JsonElement wing = config.GetProperty("wing_cooling_system");
        using Voxels wingDucts = Paths(lib, wing, "duct_radius_mm", "duct_paths_mm");
        using Voxels exchanger = BoxFrom(lib, wing.GetProperty("heat_exchanger"));
        return Voxels.voxCombineAll(lib, new[] { intakes, wingDucts, exchanger });
    }

    private static Voxels BuildWing(Library lib, JsonElement config)
    {
        using Voxels plenum = BoxFrom(lib, config.GetProperty("plenum"));
        using Voxels lip = BoxFrom(lib, config.GetProperty("raised_lip"));
        return Voxels.voxCombineAll(lib, new[] { plenum, lip });
    }

    private static Voxels BuildStructure(
        Library lib,
        JsonElement config,
        float bodyWidth,
        float bodyHeight,
        float bodyRear,
        float floorZ,
        float firewallX,
        float firewallClearance,
        float occupantRearX,
        float serviceWidth,
        float serviceHeight)
    {
        Voxels result = new(lib);
        AddBox(result, lib, new Vector3(10, bodyWidth, bodyHeight - floorZ),
            new Vector3(firewallX, 0, floorZ + (bodyHeight - floorZ) / 2f));
        AddBox(result, lib, new Vector3(10, bodyWidth, bodyHeight - floorZ),
            new Vector3(occupantRearX, 0, floorZ + (bodyHeight - floorZ) / 2f));
        AddBox(result, lib, new Vector3(firewallClearance, serviceWidth, serviceHeight),
            new Vector3(firewallX + firewallClearance / 2f, 0, floorZ + serviceHeight / 2f));
        AddBox(result, lib, new Vector3(bodyRear - occupantRearX, bodyWidth - 160, 20),
            new Vector3((occupantRearX + bodyRear) / 2f, 0, floorZ));

        Vector3 railSize = Vec3(config.GetProperty("rail_size_mm"));
        foreach (JsonElement centre in config.GetProperty("rail_centres_mm").EnumerateArray())
            AddBox(result, lib, railSize, Vec3(centre));
        Vector3 crossSize = Vec3(config.GetProperty("crossmember_size_mm"));
        foreach (JsonElement x in config.GetProperty("crossmember_x_mm").EnumerateArray())
            AddBox(result, lib, crossSize, new Vector3(x.GetSingle(), 0, floorZ + 75));
        return result;
    }

    private static Voxels BuildRunningGear(
        Library lib,
        JsonElement config,
        float frontTrack,
        float rearTrack,
        float rearAxle)
    {
        float radius = config.GetProperty("outer_diameter_mm").GetSingle() / 2f;
        float width = config.GetProperty("width_mm").GetSingle();
        float hubRadius = config.GetProperty("hub_opening_diameter_mm").GetSingle() / 2f;
        float z = config.GetProperty("centre_z_mm").GetSingle();
        Voxels result = new(lib);
        foreach ((float x, float track) in new[] { (0f, frontTrack), (rearAxle, rearTrack) })
        {
            foreach (float y in new[] { -track / 2f, track / 2f })
            {
                using Mesh outerMesh = CylinderYMesh(lib, new Vector3(x, y, z), radius, width, 48);
                using Mesh innerMesh = CylinderYMesh(lib, new Vector3(x, y, z), hubRadius, width + 20, 48);
                using Voxels outer = new(outerMesh);
                using Voxels inner = new(innerMesh);
                using Voxels wheel = outer - inner;
                result.BoolAdd(wheel);
                AddFrustum(result, lib, new Vector3(x, y - 35, z), new Vector3(x, y + 35, z), 82, 82);
                for (int spoke = 0; spoke < 5; spoke++)
                {
                    float angle = 2 * MathF.PI * spoke / 5;
                    using Voxels beam = Voxels.voxLatticeBeam(lib, new(x, y, z), 13,
                        new(x + hubRadius * MathF.Cos(angle), y, z + hubRadius * MathF.Sin(angle)), 13);
                    result.BoolAdd(beam);
                }
            }
        }
        return result;
    }

    private static Voxels BuildHalfshafts(Library lib, JsonElement config, float axleX, float track, float z)
    {
        float flange = config.GetProperty("transaxle").GetProperty("output_flange_half_span_mm").GetSingle();
        float radius = config.GetProperty("halfshafts").GetProperty("shaft_radius_mm").GetSingle();
        float joint = config.GetProperty("halfshafts").GetProperty("cv_joint_radius_mm").GetSingle();
        Voxels result = new(lib);
        foreach (float side in new[] {-1f, 1f})
        {
            Vector3 inner = new(axleX, side * flange, z);
            Vector3 outer = new(axleX, side * track / 2, z);
            AddFrustum(result, lib, inner, outer, radius, radius);
            foreach (Vector3 point in new[] {inner, outer})
            {
                using Voxels cv = Voxels.voxSphere(lib, point, joint);
                result.BoolAdd(cv);
            }
        }
        return result;
    }

    private static Voxels BuildAxisGuides(Library lib, float start, float end, float frontTrack, float rearTrack,
        float rearX, float axleZ, float shaftZ)
    {
        Voxels result = new(lib);
        foreach ((float x, float track) in new[] {(0f, frontTrack), (rearX, rearTrack)})
            for (float y = -track / 2 - 160; y < track / 2 + 160; y += 100)
                AddFrustum(result, lib, new(x, y, axleZ), new(x, y + 50, axleZ), 5, 5);
        for (float x = start - 120; x < end + 100; x += 100)
            AddFrustum(result, lib, new(x, 0, shaftZ), new(x + 50, 0, shaftZ), 5, 5);
        return result;
    }

    private static void AddFrustum(Voxels target, Library lib, Vector3 start, Vector3 end, float r0, float r1)
    {
        using Voxels shape = Frustum(lib, start, end, r0, r1);
        target.BoolAdd(shape);
    }

    private static Voxels Frustum(Library lib, Vector3 start, Vector3 end, float r0, float r1)
    {
        if (r0 <= 0 || r1 <= 0 || Vector3.Distance(start, end) < 1e-5f)
            throw new InvalidDataException("rayons positifs et segment non nul requis");
        Vector3 axis = Vector3.Normalize(end - start);
        Vector3 u = Vector3.Normalize(Vector3.Cross(axis, MathF.Abs(axis.Z) < 0.9f ? Vector3.UnitZ : Vector3.UnitY));
        Vector3 v = Vector3.Cross(axis, u);
        using Mesh mesh = new(lib);
        for (int index = 0; index < 48; index++)
        {
            float a = index * 2 * MathF.PI / 48, b = (index + 1) * 2 * MathF.PI / 48;
            Vector3 da = u * MathF.Cos(a) + v * MathF.Sin(a), db = u * MathF.Cos(b) + v * MathF.Sin(b);
            Vector3 p = start + da * r0, q = start + db * r0, r = end + da * r1, s = end + db * r1;
            mesh.nAddTriangle(p, q, s);
            mesh.nAddTriangle(p, s, r);
            mesh.nAddTriangle(start, q, p);
            mesh.nAddTriangle(end, r, s);
        }
        return new Voxels(mesh);
    }

    private static Voxels Paths(
        Library lib,
        JsonElement config,
        string radiusProperty = "radius_mm",
        string pathsProperty = "paths_mm")
    {
        float radius = config.GetProperty(radiusProperty).GetSingle();
        Voxels result = new(lib);
        foreach (JsonElement path in config.GetProperty(pathsProperty).EnumerateArray())
        {
            JsonElement[] points = path.EnumerateArray().ToArray();
            for (int index = 1; index < points.Length; index++)
            {
                using Voxels segment = Voxels.voxLatticeBeam(lib, Vec3(points[index - 1]), radius, Vec3(points[index]), radius);
                result.BoolAdd(segment);
            }
        }
        return result;
    }

    private static Mesh CylinderYMesh(Library lib, Vector3 centre, float radius, float length, int segments)
    {
        Mesh mesh = new(lib);
        Vector3 leftCentre = centre - Vector3.UnitY * length / 2f;
        Vector3 rightCentre = centre + Vector3.UnitY * length / 2f;
        for (int index = 0; index < segments; index++)
        {
            float angle0 = 2f * MathF.PI * index / segments;
            float angle1 = 2f * MathF.PI * (index + 1) / segments;
            Vector3 radial0 = new(MathF.Cos(angle0) * radius, 0, MathF.Sin(angle0) * radius);
            Vector3 radial1 = new(MathF.Cos(angle1) * radius, 0, MathF.Sin(angle1) * radius);
            Vector3 left0 = leftCentre + radial0;
            Vector3 left1 = leftCentre + radial1;
            Vector3 right0 = rightCentre + radial0;
            Vector3 right1 = rightCentre + radial1;
            mesh.nAddTriangle(left0, right1, left1);
            mesh.nAddTriangle(left0, right0, right1);
            mesh.nAddTriangle(leftCentre, left1, left0);
            mesh.nAddTriangle(rightCentre, right0, right1);
        }
        return mesh;
    }

    private static Mesh BodyEnvelopeMesh(
        Library lib,
        float front,
        float rear,
        float width,
        float height,
        float rearAxle)
    {
        Vector2[] profile = BodyProfile(front, rear, height, rearAxle);
        float halfWidth = width / 2f;
        Vector2 centre2d = new(profile.Average(point => point.X), profile.Average(point => point.Y));
        Mesh mesh = new(lib);
        for (int index = 0; index < profile.Length; index++)
        {
            int next = (index + 1) % profile.Length;
            Vector3 left0 = new(profile[index].X, -halfWidth, profile[index].Y);
            Vector3 left1 = new(profile[next].X, -halfWidth, profile[next].Y);
            Vector3 right0 = new(profile[index].X, halfWidth, profile[index].Y);
            Vector3 right1 = new(profile[next].X, halfWidth, profile[next].Y);
            mesh.nAddTriangle(left0, left1, right1);
            mesh.nAddTriangle(left0, right1, right0);
            mesh.nAddTriangle(new Vector3(centre2d.X, -halfWidth, centre2d.Y), left1, left0);
            mesh.nAddTriangle(new Vector3(centre2d.X, halfWidth, centre2d.Y), right0, right1);
        }
        return mesh;
    }

    private static Vector2[] BodyProfile(float front, float rear, float height, float rearAxle) => new Vector2[]
    {
        new(front, 190), new(front + 90, 480), new(front + 520, 720), new(-80, 890),
        new(520, height * 0.94f), new(1080, height), new(1530, height * 0.96f),
        new(1900, 1110), new(rearAxle - 420, 860), new(rear - 420, 730),
        new(rear, 500), new(rear, 180)
    };

    private static Voxels BuildBodyOutline(Library lib, float front, float rear, float width, float height, float axle)
    {
        Voxels result = new(lib);
        Vector2[] points = BodyProfile(front, rear, height, axle);
        for (int index = 0; index < points.Length; index++)
        {
            Vector2 a = points[index], b = points[(index + 1) % points.Length];
            using Voxels line = Voxels.voxLatticeBeam(lib, new(a.X, width / 2, a.Y), 6, new(b.X, width / 2, b.Y), 6);
            result.BoolAdd(line);
        }
        return result;
    }

    private static JsonDocument LoadJson(string relative) =>
        JsonDocument.Parse(File.ReadAllText(Path.Combine(Root, relative)));

    private static JsonElement SelectedLayout(JsonElement report)
    {
        JsonElement layouts = report.GetProperty("layout_screening");
        string selected = layouts.GetProperty("selected_layout_id").GetString()
            ?? throw new InvalidDataException("selected_layout_id absent");
        return layouts.GetProperty("trials").EnumerateArray()
            .Single(item => item.GetProperty("layout_id").GetString() == selected);
    }

    private static Vector3 Vec3(JsonElement value)
    {
        float[] values = value.EnumerateArray().Select(item => item.GetSingle()).ToArray();
        if (values.Length != 3)
            throw new InvalidDataException("vecteur 3D attendu");
        return new Vector3(values[0], values[1], values[2]);
    }

    private static Voxels BoxFrom(Library lib, JsonElement config) =>
        Box(lib, Vec3(config.GetProperty("size_mm")), Vec3(config.GetProperty("centre_mm")));

    private static Voxels Box(Library lib, Vector3 size, Vector3 center) =>
        new(Utils.mshCreateCube(lib, size, center));

    private static void AddBox(Voxels target, Library lib, Vector3 size, Vector3 center)
    {
        using Voxels box = Box(lib, size, center);
        target.BoolAdd(box);
    }

    private static Dictionary<string, bool> BoolMap(JsonElement value) =>
        value.EnumerateObject().ToDictionary(property => property.Name, property => property.Value.GetBoolean());

    private static Dictionary<string, object?> Properties(Voxels voxels)
    {
        voxels.CalculateProperties(out float volume, out BBox3 bounds);
        return new Dictionary<string, object?>
        {
            ["volume_mm3"] = volume,
            ["bounds_min_mm"] = new[] { bounds.vecMin.X, bounds.vecMin.Y, bounds.vecMin.Z },
            ["bounds_max_mm"] = new[] { bounds.vecMax.X, bounds.vecMax.Y, bounds.vecMax.Z }
        };
    }

    private static Dictionary<string, object?> Collision(Voxels left, Voxels right)
    {
        using Voxels overlap = left & right;
        bool empty = overlap.bIsEmpty();
        return new Dictionary<string, object?>
        {
            ["collision"] = !empty,
            ["overlap"] = empty ? null : Properties(overlap)
        };
    }
}
