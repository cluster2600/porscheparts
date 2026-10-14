using System.Numerics;
using System.Security.Cryptography;
using System.Text.Json;
using PicoGK;

namespace Vehicle911917;

internal static partial class Program
{
    private const string VehicleConfig = "twins/vehicle-911-917/full-vehicle-study-f15.json";
    private static (Matrix4x4 Matrix, Vector3 Min, Vector3 Max, string Sha256, JsonElement Receipt)? ScanAlignment;

    private static void ValidateVehicleInputs()
    {
        using JsonDocument doc = LoadJson(VehicleConfig);
        JsonElement c = doc.RootElement;
        if (c.GetProperty("phase").GetString() != "F15" || c.GetProperty("units").GetString() != "mm" ||
            !float.IsFinite(VoxelMm) || VoxelMm != c.GetProperty("voxel_size_mm").GetSingle())
            throw new InvalidDataException("F15 requires its declared millimetre resolution");
        foreach (var gate in c.GetProperty("release_gates").EnumerateObject())
            if (gate.Value.ValueKind != JsonValueKind.False)
                throw new InvalidDataException("F15 cannot authorize physical release");
        foreach (var value in c.GetProperty("unknowns").EnumerateObject())
            if (value.Value.ValueKind != JsonValueKind.Null)
                throw new InvalidDataException("Unknown interfaces need an independent evidence contract");
        foreach (string key in new[] {"rear_axle_x_mm", "front_track_mm", "rear_track_mm", "axle_z_mm",
            "wheel_radius_mm", "wheel_width_mm", "vertical_travel_mm", "clearance_mm", "firewall_clearance_mm",
            "firewall_thickness_mm", "body_skin_half_thickness_mm", "front_floor_width_mm"})
            if (!float.IsFinite(c.GetProperty(key).GetSingle()) || c.GetProperty(key).GetSingle() <= 0)
                throw new InvalidDataException("Positive finite dimensions required: " + key);
        float last = float.NegativeInfinity;
        foreach (JsonElement station in c.GetProperty("body_stations_x_halfwidth_shoulder_roof_mm").EnumerateArray())
        {
            float[] row = station.EnumerateArray().Select(v => v.GetSingle()).ToArray();
            if (row.Length != 4 || row.Any(v => !float.IsFinite(v)) || row[0] <= last || row[1] <= 0 || row[2] < 240 || row[3] < row[2])
                throw new InvalidDataException("Body stations must be ordered and finite");
            last = row[0];
        }
        if (c.GetProperty("body_stations_x_halfwidth_shoulder_roof_mm").GetArrayLength() < 3)
            throw new InvalidDataException("At least three body stations required");
        foreach (string key in new[] { "engine_bounds_mm" })
        {
            Vector3 lo = Vec3(c.GetProperty(key)[0]), hi = Vec3(c.GetProperty(key)[1]);
            if (!Finite(lo) || !Finite(hi) || lo.X >= hi.X || lo.Y >= hi.Y || lo.Z >= hi.Z)
                throw new InvalidDataException("Ordered finite bounds required");
        }
        foreach (JsonElement box in c.GetProperty("equipment_reservations").EnumerateArray().Prepend(c.GetProperty("floor")))
        {
            Vector3 size = Vec3(box.GetProperty("size_mm")), centre = Vec3(box.GetProperty("centre_mm"));
            if (!Finite(size) || !Finite(centre) || MathF.Min(size.X, MathF.Min(size.Y, size.Z)) <= 0)
                throw new InvalidDataException("Invalid equipment box");
        }
        float steer = c.GetProperty("front_steering_sweep_deg").GetSingle();
        if (!float.IsFinite(steer) || steer < 0 || steer > 45)
            throw new InvalidDataException("Steering sensitivity must be in [0,45] degrees");
        using JsonDocument wheelSource = LoadJson("twins/vehicle-911-917/picogk-full-vehicle-f12.json");
        JsonElement wheel = wheelSource.RootElement.GetProperty("wheel_reservation");
        if (c.GetProperty("front_axle_x_mm").GetSingle() != 0 ||
            c.GetProperty("axle_z_mm").GetSingle() != wheel.GetProperty("centre_z_mm").GetSingle() ||
            c.GetProperty("wheel_radius_mm").GetSingle() * 2 != wheel.GetProperty("outer_diameter_mm").GetSingle() ||
            c.GetProperty("wheel_width_mm").GetSingle() != wheel.GetProperty("width_mm").GetSingle())
            throw new InvalidDataException("F15 and reused wheel geometry disagree");
        Vector3 floorSize = Vec3(c.GetProperty("floor").GetProperty("size_mm")), floorCentre = Vec3(c.GetProperty("floor").GetProperty("centre_mm"));
        float transition = c.GetProperty("floor_width_transition_x_mm").GetSingle();
        if (!float.IsFinite(transition) || transition <= floorCentre.X - floorSize.X / 2 || transition >= floorCentre.X + floorSize.X / 2 ||
            c.GetProperty("front_floor_width_mm").GetSingle() >= floorSize.Y)
            throw new InvalidDataException("Front floor relief must lie within the floor reservation");
        if (File.Exists(Path.Combine(Output, "vehicle-report-f15.json")))
            throw new InvalidDataException("Retain previous results; choose a new PICOGK_OUTPUT_DIR");
        string? alignmentPath = Environment.GetEnvironmentVariable("PICOGK_F13_ALIGNMENT");
        if (alignmentPath != null)
            ScanAlignment = ValidatedF13Alignment(alignmentPath, Path.Combine(Input, "917-engine-oriented-f10.stl"));
    }

    // Provenance, input digests and rigidity are F13's own rules (ScanAlignment.cs); F15 adds the scan size and bounds.
    private static (Matrix4x4, Vector3, Vector3, string, JsonElement) ValidatedF13Alignment(string alignmentPath, string scanPath)
    {
        using JsonDocument doc = JsonDocument.Parse(File.ReadAllText(alignmentPath));
        JsonElement r = doc.RootElement;
        Matrix4x4 matrix = ValidatedAlignment(r, Root, scanPath);
        byte[] header = new byte[84];
        using (var stream = File.OpenRead(scanPath)) stream.ReadExactly(header);
        uint count = BitConverter.ToUInt32(header, 80);
        if (new FileInfo(scanPath).Length != 84 + 50L * count || r.GetProperty("triangle_count").GetInt64() != count)
            throw new InvalidDataException("F13 receipt triangle count differs from the scan");
        Vector3 lo = Vec3(r.GetProperty("bounds_min_mm")), hi = Vec3(r.GetProperty("bounds_max_mm"));
        if (!Finite(lo) || !Finite(hi) || lo.X > hi.X || lo.Y > hi.Y || lo.Z > hi.Z)
            throw new InvalidDataException("F13 receipt bounds must be ordered and finite");
        return (matrix, lo, hi, Hash(alignmentPath), r.Clone());
    }

    private static bool Finite(Vector3 v) => float.IsFinite(v.X) && float.IsFinite(v.Y) && float.IsFinite(v.Z);
    private static string Hash(string path) { using var stream = File.OpenRead(path); return Convert.ToHexString(SHA256.HashData(stream)).ToLowerInvariant(); }

    private static void RunVehicleStudy()
    {
        using JsonDocument doc = LoadJson(VehicleConfig);
        using JsonDocument mechanical = LoadJson("twins/vehicle-911-917/picogk-mechanical-f13.json");
        using JsonDocument wheels = LoadJson("twins/vehicle-911-917/picogk-full-vehicle-f12.json");
        JsonElement c = doc.RootElement, f13 = mechanical.RootElement;
        var sources = new[] {VehicleConfig, "twins/vehicle-911-917/picogk/Program.cs",
            "twins/vehicle-911-917/picogk/FullVehicleStudy.cs", "twins/vehicle-911-917/picogk/Vehicle911917Packaging.csproj",
            "twins/vehicle-911-917/picogk-mechanical-f13.json", "twins/vehicle-911-917/picogk-full-vehicle-f12.json",
            c.GetProperty("source_vehicle_reference").GetString()!};
        var inputs = sources.Select(path => new { path, sha256 = Hash(Path.Combine(Root, path)) }).ToArray();
        Library lib = Library.oLibrary();
        float rear = c.GetProperty("rear_axle_x_mm").GetSingle(), z = c.GetProperty("axle_z_mm").GetSingle();
        float frontTrack = c.GetProperty("front_track_mm").GetSingle(), rearTrack = c.GetProperty("rear_track_mm").GetSingle();
        float firewallX = c.GetProperty("firewall_x_mm").GetSingle();
        Vector3 engineMin = Vec3(c.GetProperty("engine_bounds_mm")[0]), engineMax = Vec3(c.GetProperty("engine_bounds_mm")[1]);
        var layers = new List<(string Key, Voxels Geometry, string Colour, string System)>();
        void Add(string key, Voxels vox, string colour, string system) => layers.Add((key, vox, colour, system));
        Voxels Get(string key) => layers.Single(v => v.Key == key).Geometry;
        using Mesh bodyMesh = VehicleBodyMesh(lib, c);
        using Voxels bodyVolume = new(bodyMesh);
        Voxels shell = Voxels.voxMeshShell(lib, bodyMesh, c.GetProperty("body_skin_half_thickness_mm").GetSingle());
        using Voxels wheelSweep = VehicleWheelKeepout(lib, c);
        shell.BoolSubtract(wheelSweep);
        using Voxels windshieldCut = Box(lib, new(470, 1320, 520), new(495, 0, 1110));
        using Voxels sideWindowCut = Box(lib, new(560, 2200, 330), new(1040, 0, 1055));
        shell.BoolSubtract(windshieldCut); shell.BoolSubtract(sideWindowCut);
        foreach (float side in new[] { -1f, 1f })
        {
            using Voxels inlet = Frustum(lib, new(1665, side * 790, 980), new(1665, side * 1050, 980), 120, 120);
            shell.BoolSubtract(inlet);
            using Voxels tailFeed = Box(lib, new(250, 220, 320), new(3170, side * 470, 850));
            shell.BoolSubtract(tailFeed);
        }
        Add("body_shell", shell, "44647D", "body");
        Add("front_glazing", VehicleGlazing(lib), "6096A988", "body");
        Voxels floor = BoxFrom(lib, c.GetProperty("floor"));
        Vector3 floorSize = Vec3(c.GetProperty("floor").GetProperty("size_mm")), floorCentre = Vec3(c.GetProperty("floor").GetProperty("centre_mm"));
        float floorStart = floorCentre.X - floorSize.X / 2, transition = c.GetProperty("floor_width_transition_x_mm").GetSingle();
        float frontWidth = c.GetProperty("front_floor_width_mm").GetSingle();
        foreach (float side in new[] { -1f, 1f })
        {
            using Voxels relief = Box(lib, new(transition - floorStart, floorSize.Y - frontWidth, floorSize.Z + 20),
                new((floorStart + transition) / 2, side * floorSize.Y / 2, floorCentre.Z));
            floor.BoolSubtract(relief);
        }
        Add("floor", floor, "64748B", "structure");
        Voxels wall = Box(lib, new(c.GetProperty("firewall_thickness_mm").GetSingle(), 2300, 1600), new(firewallX, 0, 800));
        wall.BoolIntersect(bodyVolume);
        Add("firewall", wall, "BF5A49", "occupant_separation");
        Voxels frame = new(lib);
        foreach (JsonElement centre in c.GetProperty("rail_centres_mm").EnumerateArray())
            AddBox(frame, lib, Vec3(c.GetProperty("rail_size_mm")), Vec3(centre));
        AddBox(frame, lib, new(90, 1490, 130), new(3440, 0, 590));
        Add("rear_structure_corridors", frame, "62738C", "structure");
        Voxels frontFrame = new(lib);
        foreach (float side in new[] { -1f, 1f })
            AddBox(frontFrame, lib, new(1460, 80, 100), new(150, side * 420, 220));
        foreach (float x in new[] { -150f, 220f }) AddBox(frontFrame, lib, new(70, 920, 90), new(x, 0, 220));
        Add("front_structure_corridors", frontFrame, "62738C", "structure");
        Add("engine_service_envelope", Box(lib, engineMax - engineMin, (engineMax + engineMin) / 2), "E4AE5030", "keepout");
        Add("engine_topology_proxy", VehicleEngineProxy(lib, engineMin, engineMax), "B8A17E", "powertrain");
        float gearboxStart = c.GetProperty("gearbox_bounds_x_mm")[0].GetSingle(), gearboxEnd = c.GetProperty("gearbox_bounds_x_mm")[1].GetSingle();
        Add("transaxle_schematic", BuildTransmission(lib, f13.GetProperty("transaxle"), gearboxStart, gearboxEnd, rear, 500, z), "AA853F", "powertrain");
        Add("rear_halfshafts", BuildHalfshafts(lib, f13, rear, rearTrack, z), "3B9A85", "driveline");
        Add("wheels_and_hubs", BuildRunningGear(lib, wheels.RootElement.GetProperty("wheel_reservation"), frontTrack, rearTrack, rear), "263343", "wheels");
        Add("wheel_motion_keepouts", wheelSweep.voxDuplicate(), "CB7F3A33", "keepout");
        foreach (float side in new[] { -1f, 1f })
        {
            string sideName = side < 0 ? "left" : "right";
            Add("seat_" + sideName, VehicleSeat(lib, side * 355), "334B64", "cabin");
            Add("turbo_" + sideName, BuildTurbo(lib, f13.GetProperty("turbos"), new(2320, side * 470, 590)), "B85C37", "forced_induction");
            Add("quarter_intake_" + sideName, VehicleTube(lib, 82, 8, new[] {
                new Vector3(1630, side * 915, 980), new Vector3(1830, side * 710, 920),
                new Vector3(2245, side * 670, 790), new Vector3(2245, side * 470, 590)}), "32A4B5", "air_path");
            Add("exhaust_" + sideName, VehicleTube(lib, 55, 8, new[] {
                new Vector3(2395, side * 470, 590), new Vector3(2500, side * 560, 760),
                new Vector3(3160, side * 560, 760), new Vector3(3300, side * 850, 760),
                new Vector3(3540, side * 850, 400)}), "A56948", "hot_path");
            Add("tail_cooling_duct_" + sideName, VehicleTube(lib, 70, 8, new[] {
                new Vector3(1840, side * 740, 875), new Vector3(2400, side * 770, 730),
                new Vector3(2940, side * 600, 710), new Vector3(3170, side * 470, 730),
                new Vector3(3260, side * 470, 890)}), "358EA1", "cooling");
            foreach ((float x, float track, string name) in new[] { (0f, frontTrack, "front"), (rear, rearTrack, "rear") })
            {
                float y = side * track / 2;
                Add(name + "_brake_" + sideName, VehicleBrake(lib, x, y, z, side), "BE6655", "brakes");
                // shortcut: visual link corridors only; replace with measured pivots before solving suspension motion.
                Voxels suspension = new(lib);
                foreach (float height in new[] { 230f, 480f })
                {
                    Vector3 outboard = new(x, y - side * 100, height);
                    foreach (float dx in new[] { -210f, 210f })
                        AddFrustum(suspension, lib, new(x + dx, side * (name == "front" ? 430 : 670), height + 15), outboard, 18, 18);
                }
                AddFrustum(suspension, lib, new(x, y - side * 100, 215), new(x, y - side * 100, 505), 40, 40);
                Add("suspension_corridor_" + name + "_" + sideName, suspension, "718AA2", "suspension");
                Voxels damper = Frustum(lib, new(x, y - side * 190, 270), new(x + 90, y - side * 220, 720), 33, 33);
                Add("spring_damper_reservation_" + name + "_" + sideName, damper, "D0A950", "suspension");
            }
        }
        foreach (JsonElement box in c.GetProperty("equipment_reservations").EnumerateArray())
            Add(box.GetProperty("id").GetString()!, BoxFrom(lib, box), "729989", "equipment");
        Voxels steering = Frustum(lib, new(150, -525, 300), new(150, 525, 300), 30, 30);
        AddFrustum(steering, lib, new(150, -370, 300), new(610, -370, 690), 20, 20);
        foreach (float side in new[] { -1f, 1f })
            AddFrustum(steering, lib, new(150, side * 525, 300), new(80, side * (frontTrack / 2 - 100), 330), 15, 15);
        Add("steering_reservations", steering, "A38B5D", "steering");
        Add("dashboard", Box(lib, new(220, 1460, 170), new(590, 0, 750)), "3E4D5C", "cabin");
        JsonElement tail = c.GetProperty("tail");
        Voxels plenum = BoxFrom(lib, tail.GetProperty("plenum"));
        Vector3 plenumSize = Vec3(tail.GetProperty("plenum").GetProperty("size_mm"));
        using (Voxels hollow = Box(lib, plenumSize - new Vector3(24, 24, 24), Vec3(tail.GetProperty("plenum").GetProperty("centre_mm")))) plenum.BoolSubtract(hollow);
        using (Voxels inlet = Box(lib, new(400, 1300, 80), new(3330, 0, 970))) plenum.BoolSubtract(inlet);
        using (Voxels outlet = Box(lib, new(100, 1100, 100), new(3690, 0, 900))) plenum.BoolSubtract(outlet);
        Add("tail_plenum", plenum, "577C73", "tail");
        Add("tail_heat_exchanger", BoxFrom(lib, tail.GetProperty("heat_exchanger")), "C9AD63", "cooling");
        using Mesh lipMesh = new(lib);
        float a = tail.GetProperty("lip_front_x_mm").GetSingle(), b = tail.GetProperty("lip_rear_x_mm").GetSingle();
        float za = tail.GetProperty("lip_front_z_mm").GetSingle(), zb = tail.GetProperty("lip_rear_z_mm").GetSingle(), hw = tail.GetProperty("lip_half_span_mm").GetSingle();
        lipMesh.nAddTriangle(new Vector3(a, -hw, za), new Vector3(b, -hw, zb), new Vector3(b, hw, zb));
        lipMesh.nAddTriangle(new Vector3(a, -hw, za), new Vector3(b, hw, zb), new Vector3(a, hw, za));
        Add("fixed_930_style_tail", Voxels.voxMeshShell(lib, lipMesh, tail.GetProperty("lip_half_thickness_mm").GetSingle()), "334638", "tail");
        Add("front_and_rear_lighting", VehicleLights(lib), "B45B54", "body");

        object? privateScan = null;
        if (ScanAlignment is { } alignment)
        {
            string scanPath = Path.Combine(Input, "917-engine-oriented-f10.stl"), alignmentPath = Environment.GetEnvironmentVariable("PICOGK_F13_ALIGNMENT")!;
            if (Hash(scanPath) != alignment.Receipt.GetProperty("input_stl_sha256").GetString() || Hash(alignmentPath) != alignment.Sha256)
                throw new InvalidDataException("Private scan or F13 receipt changed after validation");
            using Mesh scan = Mesh.mshFromStlFile(scanPath, Mesh.EStlUnit.MM, libSet: lib);
            using Mesh aligned = scan.mshCreateTransformed(alignment.Matrix);
            BBox3 box = aligned.oBoundingBox();
            Vector3 drift = Vector3.Max(Vector3.Abs(box.vecMin - alignment.Min), Vector3.Abs(box.vecMax - alignment.Max));
            if (MathF.Max(drift.X, MathF.Max(drift.Y, drift.Z)) > 1)
                throw new InvalidDataException("Aligned scan bounds differ from its F13 receipt");
            Add("private_engine_scan", Voxels.voxMeshShell(lib, aligned, VoxelMm / 2), "A6ADB3", "private_reference");
            privateScan = new { scan_sha256 = Hash(scanPath), alignment_sha256 = alignment.Sha256, scale_verified = false, physical_datum_verified = false, alignment = alignment.Receipt };
        }

        var checks = new Dictionary<string, object?>();
        foreach ((string left, string right) in new[] {("engine_service_envelope", "floor"), ("engine_service_envelope", "firewall"),
            ("engine_service_envelope", "rear_structure_corridors"), ("rear_halfshafts", "rear_structure_corridors"),
            ("transaxle_schematic", "rear_structure_corridors"), ("transaxle_schematic", "floor"),
            ("wheel_motion_keepouts", "rear_structure_corridors"), ("wheel_motion_keepouts", "front_structure_corridors"),
            ("wheel_motion_keepouts", "floor"), ("seat_left", "firewall"), ("seat_right", "firewall"),
            ("exhaust_left", "rear_structure_corridors"), ("exhaust_right", "rear_structure_corridors"),
            ("quarter_intake_left", "firewall"), ("quarter_intake_right", "firewall"),
            ("fuel_cell", "steering_reservations"), ("oil_tank", "transaxle_schematic"),
            ("engine_service_envelope", "body_shell"), ("transaxle_schematic", "body_shell"),
            ("quarter_intake_left", "body_shell"), ("quarter_intake_right", "body_shell"),
            ("tail_cooling_duct_left", "body_shell"), ("tail_cooling_duct_right", "body_shell")})
            checks[left + "__" + right] = Collision(Get(left), Get(right));
        using Voxels guardedEngine = Get("engine_service_envelope").voxOffset(c.GetProperty("clearance_mm").GetSingle() + 2 * VoxelMm);
        checks["engine_20mm_plus_numerical_guard__floor"] = Collision(guardedEngine, Get("floor"));
        checks["engine_20mm_plus_numerical_guard__body_shell"] = Collision(guardedEngine, Get("body_shell"));
        using Voxels guardedFirewallEngine = Get("engine_service_envelope").voxOffset(c.GetProperty("firewall_clearance_mm").GetSingle() + 2 * VoxelMm);
        checks["engine_50mm_plus_numerical_guard__firewall"] = Collision(guardedFirewallEngine, Get("firewall"));
        if (privateScan != null)
        {
            checks["private_scan__firewall"] = Collision(Get("private_engine_scan"), Get("firewall"));
            checks["private_scan__transaxle"] = Collision(Get("private_engine_scan"), Get("transaxle_schematic"));
        }
        var exported = new List<object>();
        foreach (var layer in layers)
        {
            if (layer.Geometry.bIsEmpty()) throw new InvalidDataException("Empty component: " + layer.Key);
            string vdb = layer.Key + ".vdb", stl = layer.Key + ".stl";
            layer.Geometry.SaveToVdbFile(Path.Combine(Output, vdb));
            using Mesh mesh = new(layer.Geometry);
            mesh.SaveToStlFile(Path.Combine(Output, stl));
            exported.Add(new
            {
                id = layer.Key,
                system = layer.System,
                status = layer.System == "private_reference" ? "observed_partial_scan_uncalibrated" : "hypothetical_packaging_geometry_not_manufacturing_part",
                properties = Properties(layer.Geometry),
                vdb,
                vdb_sha256 = Hash(Path.Combine(Output, vdb)),
                stl,
                stl_sha256 = Hash(Path.Combine(Output, stl))
            });
        }
        using Voxels assembly = Voxels.voxCombineAll(lib, layers.Where(layer => layer.System != "keepout" &&
            !(privateScan != null && layer.Key == "engine_topology_proxy")).Select(layer => layer.Geometry).ToArray());
        assembly.SaveToVdbFile(Path.Combine(Output, "vehicle-inspection-assembly.vdb"));
        using (Mesh mesh = new(assembly)) mesh.SaveToStlFile(Path.Combine(Output, "vehicle-inspection-assembly.stl"));
        var views = VehicleViews(layers, privateScan != null);
        foreach (var source in inputs)
            if (Hash(Path.Combine(Root, source.path)) != source.sha256) throw new InvalidDataException("Source changed during run");
        File.WriteAllText(Path.Combine(Output, "vehicle-report-f15.json"), JsonSerializer.Serialize(new
        {
            phase = "F15",
            status = "produced_packaging_study_not_accepted_vehicle",
            kernel = Library.strVersion(),
            voxel_size_mm = VoxelMm,
            assembly_sha256 = Hash(typeof(Program).Assembly.Location),
            inputs,
            components = exported,
            checks,
            views,
            private_scan = privateScan,
            inspection_assembly = new
            {
                vdb = "vehicle-inspection-assembly.vdb",
                stl = "vehicle-inspection-assembly.stl",
                vdb_sha256 = Hash(Path.Combine(Output, "vehicle-inspection-assembly.vdb")),
                stl_sha256 = Hash(Path.Combine(Output, "vehicle-inspection-assembly.stl"))
            },
            nominal_engine_floor_gap_mm = engineMin.Z - (Vec3(c.GetProperty("floor").GetProperty("centre_mm")).Z + Vec3(c.GetProperty("floor").GetProperty("size_mm")).Z / 2),
            nominal_engine_firewall_gap_mm = engineMin.X - firewallX - c.GetProperty("firewall_thickness_mm").GetSingle() / 2,
            wheelbase_mm = rear,
            rear_tyre_outer_width_mm = rearTrack + c.GetProperty("wheel_width_mm").GetSingle(),
            nominal_tyre_bottom_z_mm = z - c.GetProperty("wheel_radius_mm").GetSingle(),
            all_functional_components_modelled = false,
            mounting_interfaces_measured = false,
            release_gates = c.GetProperty("release_gates").Clone(),
            unknowns = c.GetProperty("unknowns").Clone(),
            limitations = new[] {"Body stations are design hypotheses, not a measured 911 or 930 surface.",
                "Wheel arches are cut by their own motion reservation: this is construction, not independent suspension validation.",
                "Links and dampers are visual corridors with no measured hardpoints. They do not drive wheel motion.",
                "Fuel, brakes, steering, restraints and structure are not released components. Mounts and small hardware are not designed.",
                "Air and exhaust tubes are spatial routes, not validated ports, heat shielding or flow capacity.",
                "No mass, strength, fatigue, traction, cooling or downforce capability follows from this geometry."}
        }, new JsonSerializerOptions { WriteIndented = true }) + "\n");
        foreach (var layer in layers) layer.Geometry.Dispose();
        Library.EndTask();
    }

    private static Mesh VehicleBodyMesh(Library lib, JsonElement c)
    {
        var stations = c.GetProperty("body_stations_x_halfwidth_shoulder_roof_mm").EnumerateArray().Select(row =>
        {
            float x = row[0].GetSingle(), w = row[1].GetSingle(), s = row[2].GetSingle(), h = row[3].GetSingle();
            return new[] {new Vector3(x,-w*.86f,140),new Vector3(x,-w,240),new Vector3(x,-w,s),
                new Vector3(x,-w*.72f,MathF.Max(s,h-35)),new Vector3(x,-w*.45f,h),new Vector3(x,w*.45f,h),
                new Vector3(x,w*.72f,MathF.Max(s,h-35)),new Vector3(x,w,s),new Vector3(x,w,240),new Vector3(x,w*.86f,140)};
        }).ToArray();
        // Smooth only the declared styling stations; this does not add measured surface evidence.
        var rings = new List<Vector3[]>();
        for (int i = 0; i < stations.Length - 1; i++)
            for (int step = 0; step < 8; step++)
            {
                float t = step / 8f;
                var control = Enumerable.Range(0, stations[0].Length).Select(j =>
                    Curve(stations[Math.Max(0, i - 1)][j], stations[i][j], stations[i + 1][j], stations[Math.Min(stations.Length - 1, i + 2)][j], t)).ToArray();
                rings.Add(Enumerable.Range(0, control.Length * 4).Select(j =>
                {
                    int k = j / 4, n = control.Length;
                    return Curve(control[(k + n - 1) % n], control[k], control[(k + 1) % n], control[(k + 2) % n], (j % 4) / 4f);
                }).ToArray());
            }
        rings.Add(Enumerable.Range(0, stations[0].Length * 4).Select(j =>
        {
            int k = j / 4, n = stations[0].Length; Vector3[] row = stations[^1];
            return Curve(row[(k + n - 1) % n], row[k], row[(k + 1) % n], row[(k + 2) % n], (j % 4) / 4f);
        }).ToArray());
        Mesh mesh = new(lib);
        for (int i = 1; i < rings.Count; i++)
            for (int j = 0; j < rings[i].Length; j++)
            {
                int k = (j + 1) % rings[i].Length;
                mesh.nAddTriangle(rings[i - 1][j], rings[i][j], rings[i][k]);
                mesh.nAddTriangle(rings[i - 1][j], rings[i][k], rings[i - 1][k]);
            }
        foreach (int i in new[] { 0, rings.Count - 1 })
        {
            Vector3 centre = new(rings[i][0].X, 0, (rings[i].Max(p => p.Z) + 140) / 2);
            for (int j = 0; j < rings[i].Length; j++)
            {
                int k = (j + 1) % rings[i].Length;
                if (i == 0) mesh.nAddTriangle(centre, rings[i][j], rings[i][k]);
                else mesh.nAddTriangle(centre, rings[i][k], rings[i][j]);
            }
        }
        return mesh;
    }

    private static Vector3 Curve(Vector3 a, Vector3 b, Vector3 c, Vector3 d, float t) =>
        .5f * ((2 * b) + (-a + c) * t + (2 * a - 5 * b + 4 * c - d) * t * t + (-a + 3 * b - 3 * c + d) * t * t * t);

    private static Voxels VehicleWheelKeepout(Library lib, JsonElement c)
    {
        Voxels result = new(lib);
        float r = c.GetProperty("wheel_radius_mm").GetSingle(), halfWidth = c.GetProperty("wheel_width_mm").GetSingle() / 2;
        float guard = c.GetProperty("clearance_mm").GetSingle() + 2 * VoxelMm;
        float travel = c.GetProperty("vertical_travel_mm").GetSingle(), z = c.GetProperty("axle_z_mm").GetSingle();
        float steering = c.GetProperty("front_steering_sweep_deg").GetSingle() * MathF.PI / 180;
        foreach (bool front in new[] { true, false })
        {
            // Continuous yaw bounds of the tyre's bounding rectangle, including any interior extremum.
            float angle = front ? steering : 0;
            float ax = MathF.Min(angle, MathF.Atan2(halfWidth, r)), ay = MathF.Min(angle, MathF.Atan2(r, halfWidth));
            float halfX = r * MathF.Cos(ax) + halfWidth * MathF.Sin(ax) + guard;
            float halfY = halfWidth * MathF.Cos(ay) + r * MathF.Sin(ay) + guard;
            float track = c.GetProperty(front ? "front_track_mm" : "rear_track_mm").GetSingle();
            foreach (float side in new[] { -1f, 1f })
                AddBox(result, lib, new(halfX * 2, halfY * 2, 2 * (r + travel + guard)), new(front ? 0 : c.GetProperty("rear_axle_x_mm").GetSingle(), side * track / 2, z));
        }
        return result;
    }

    private static Voxels VehicleEngineProxy(Library lib, Vector3 lo, Vector3 hi)
    {
        Voxels result = Box(lib, new(hi.X - lo.X - 100, 260, 290), new((lo.X + hi.X) / 2, 0, 475));
        for (int n = 0; n < 6; n++) foreach (float side in new[] { -1f, 1f })
            {
                float x = lo.X + 160 + n * (hi.X - lo.X - 320) / 5;
                AddFrustum(result, lib, new(x, side * 110, 500), new(x, side * 400, 500), 72, 72);
            }
        foreach (float side in new[] { -1f, 1f })
        {
            AddBox(result, lib, new(hi.X - lo.X - 100, 150, 170), new((lo.X + hi.X) / 2, side * 450, 500));
            AddFrustum(result, lib, new(lo.X + 160, side * 360, 750), new(hi.X - 160, side * 360, 750), 65, 65);
        }
        AddFrustum(result, lib, new(hi.X - 80, 0, 500), new(hi.X, 0, 500), 65, 65);
        using Voxels fan = Frustum(lib, new((lo.X + hi.X) / 2, 0, 790), new((lo.X + hi.X) / 2, 0, 855), 170, 170);
        using Voxels bore = Frustum(lib, new((lo.X + hi.X) / 2, 0, 780), new((lo.X + hi.X) / 2, 0, 865), 75, 75);
        fan.BoolSubtract(bore); result.BoolAdd(fan);
        return result;
    }

    private static Voxels VehicleTube(Library lib, float radius, float wall, Vector3[] points)
    {
        using Voxels outer = new(lib), inner = new(lib);
        for (int i = 1; i < points.Length; i++)
        {
            using Voxels a = Voxels.voxLatticeBeam(lib, points[i - 1], radius, points[i], radius);
            using Voxels b = Voxels.voxLatticeBeam(lib, points[i - 1], radius - wall, points[i], radius - wall);
            outer.BoolAdd(a); inner.BoolAdd(b);
        }
        foreach (Vector3 p in new[] { points[0], points[^1] }) { using Voxels opening = Voxels.voxSphere(lib, p, radius + 2); inner.BoolAdd(opening); }
        return outer - inner;
    }

    private static Voxels VehicleSeat(Library lib, float y)
    {
        Voxels seat = Box(lib, new(480, 440, 120), new(1020, y, 390));
        AddBox(seat, lib, new(100, 440, 590), new(1250, y, 665));
        AddBox(seat, lib, new(100, 240, 160), new(1250, y, 1035));
        foreach (float side in new[] { -1f, 1f }) AddBox(seat, lib, new(420, 45, 160), new(1040, y + side * 210, 505));
        return seat;
    }

    private static Voxels VehicleBrake(Library lib, float x, float y, float z, float side)
    {
        float discY = y - side * 55;
        Voxels disc = Frustum(lib, new(x, discY - 16, z), new(x, discY + 16, z), 170, 170);
        using Voxels bore = Frustum(lib, new(x, discY - 20, z), new(x, discY + 20, z), 90, 90);
        disc.BoolSubtract(bore);
        AddBox(disc, lib, new(100, 100, 165), new(x + 155, discY, z));
        return disc;
    }

    private static Voxels VehicleGlazing(Library lib)
    {
        using Mesh mesh = new(lib);
        mesh.nAddTriangle(new Vector3(290, -630, 895), new Vector3(695, -590, 1250), new Vector3(695, 590, 1250));
        mesh.nAddTriangle(new Vector3(290, -630, 895), new Vector3(695, 590, 1250), new Vector3(290, 630, 895));
        foreach (float s in new[] { -1f, 1f })
        {
            Vector3 a = new(770, s * 875, 885), b = new(770, s * 660, 1210), c = new(1300, s * 670, 1230), d = new(1300, s * 890, 895);
            mesh.nAddTriangle(a, b, c); mesh.nAddTriangle(a, c, d);
        }
        return Voxels.voxMeshShell(lib, mesh, 5);
    }

    private static Voxels VehicleLights(Library lib)
    {
        Voxels result = new(lib);
        foreach (float side in new[] { -1f, 1f }) AddFrustum(result, lib, new(-820, side * 690, 600), new(-750, side * 690, 640), 90, 90);
        AddBox(result, lib, new(35, 1540, 80), new(3700, 0, 420));
        return result;
    }

    private static List<object> VehicleViews(List<(string Key, Voxels Geometry, string Colour, string System)> layers, bool privateScan)
    {
        Viewer viewer = Library.oViewer();
        viewer.SetBackgroundColor("F3F4F6"); viewer.SetFov(MathF.PI / 6);
        var images = new List<object>();
        for (int i = 0; i < layers.Count; i++) viewer.SetGroupMaterial(i, layers[i].Colour, .15f, .6f);
        void View(string name, Quaternion orientation, Func<string, string, bool> show, bool section = false)
        {
            viewer.RemoveAllObjects();
            using Voxels cut = Box(Library.oLibrary(), new(6000, 1600, 2000), new(1500, 800, 900));
            var slices = new List<Voxels>();
            for (int i = 0; i < layers.Count; i++)
            {
                var layer = layers[i];
                if (!show(layer.Key, layer.System) || (privateScan && layer.Key == "engine_topology_proxy")) continue;
                if (section) { Voxels slice = layer.Geometry & cut; slices.Add(slice); viewer.Add(slice, i); }
                else viewer.Add(layer.Geometry, i);
            }
            string file = "vehicle-" + name + "-f15.tga";
            Capture(viewer, orientation, file);
            images.Add(new { id = name, file, sha256 = Hash(Path.Combine(Output, file)) });
            viewer.RemoveAllObjects(); foreach (Voxels slice in slices) slice.Dispose();
        }
        View("exterior", viewer.qOrientationHome, (key, system) => system != "keepout");
        View("side", viewer.qOrientationFront, (key, system) => system != "keepout");
        View("top", viewer.qOrientationTop, (key, system) => system != "body" && system != "tail" && system != "keepout");
        View("mechanical", viewer.qOrientationHome, (key, system) => system != "body" && system != "tail" && system != "keepout" && key != "dashboard");
        View("section", viewer.qOrientationFront, (key, system) => system != "keepout", true);
        View("rear", viewer.qOrientationRight, (key, system) => system != "keepout");
        return images;
    }
}
