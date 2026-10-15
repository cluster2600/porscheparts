using System.Numerics;
using System.Security.Cryptography;
using System.Text.Json;
using Leap71.ShapeKernel;
using Leap71.LatticeLibrary;
using PicoGK;

// F15 is read-only context: do not regenerate or mutate its receipt here.
internal static class Program
{
    static string Output = "", Baseline = "";
    static JsonElement Config, Vehicle, Receipt;
    static readonly JsonSerializerOptions JsonOptions = new() { WriteIndented = true };
    static string Hash(string p) { using var f = File.OpenRead(p); return Convert.ToHexString(SHA256.HashData(f)).ToLowerInvariant(); }
    static Vector3 Vec(JsonElement a) => new(a[0].GetSingle(), a[1].GetSingle(), a[2].GetSingle());
    static float Volume(Voxels v) { v.CalculateProperties(out float volume, out _); return volume; }
    static Voxels Box(Vector3 size, Vector3 centre) => new BaseBox(new LocalFrame(centre - new Vector3(0, 0, size.Z / 2)), size.Z, size.X, size.Y).voxConstruct();

    static void Main(string[] args)
    {
        if (args.Length != 1) throw new ArgumentException("Pass a verified F16 input receipt");
        Receipt = JsonDocument.Parse(File.ReadAllText(args[0])).RootElement.Clone();
        foreach (var input in Receipt.GetProperty("files").EnumerateArray())
            if (Hash(input.GetProperty("path").GetString()!) != input.GetProperty("sha256").GetString())
                throw new InvalidDataException("Input changed after preflight");
        Config = JsonDocument.Parse(File.ReadAllText(Receipt.GetProperty("config").GetString()!)).RootElement.Clone();
        Vehicle = JsonDocument.Parse(File.ReadAllText(Receipt.GetProperty("vehicle_config").GetString()!)).RootElement.Clone();
        Baseline = Receipt.GetProperty("baseline").GetString()!;
        Output = Receipt.GetProperty("output").GetString()!;
        if (Directory.Exists(Output)) throw new IOException("Refusing to overwrite an existing run");
        if (Config.GetProperty("voxel_size_mm").GetSingle() != 5 || Config.GetProperty("units").GetString() != "mm")
            throw new InvalidDataException("F16 requires the F15 5 mm grid");
        foreach (string key in new[] { "supplier_ports_measured", "coolant_circuit_designed", "fluid_solver_executed", "structural_solver_executed", "manufacturing_authorized" })
            if (Config.GetProperty(key).ValueKind != JsonValueKind.False) throw new InvalidDataException("Physical gate cannot be promoted");
        Directory.CreateDirectory(Output);
        Library.Go(5, Run, strLogFilePath: Path.Combine(Output, "native.log"), bEndAppWithTask: true, strWindowTitle: "911 / 917 — ShapeKernel + LatticeLibrary F16");
        if (!File.Exists(Path.Combine(Output, "report.json"))) throw new IOException("Native run did not complete");
    }

    static void Run()
    {
        var layers = new Dictionary<string, Voxels>();
        var systems = new Dictionary<string, string>();
        var replacements = new HashSet<string> { "tail_heat_exchanger", "quarter_intake_left", "quarter_intake_right", "tail_cooling_duct_left", "tail_cooling_duct_right" };
        using var baselineDoc = JsonDocument.Parse(File.ReadAllText(Path.Combine(Baseline, "vehicle-report-f15.json")));
        foreach (var part in baselineDoc.RootElement.GetProperty("components").EnumerateArray())
        {
            string id = part.GetProperty("id").GetString()!, system = part.GetProperty("system").GetString()!;
            if (replacements.Contains(id)) continue;
            using OpenVdbFile input = new(Path.Combine(Baseline, part.GetProperty("vdb").GetString()!));
            if (input.fPicoGKVoxelSizeMM() != 5 || input.nFieldCount() != 1) throw new InvalidDataException("Incompatible baseline VDB");
            layers.Add(id, input.voxGet(0)); systems.Add(id, system);
        }
        var added = new List<string>();
        var fluid = new Dictionary<string, Voxels>();
        foreach (var duct in Config.GetProperty("ducts").EnumerateArray())
        foreach (float side in new[] { -1f, 1f })
        {
            string id = duct.GetProperty("id").GetString()! + (side < 0 ? "_left" : "_right");
            var points = duct.GetProperty("control_points_mm").EnumerateArray().Select(p => Vec(p) * new Vector3(1, side, 1)).ToList();
            var spine = new ControlPointSpline(points, 2).aGetPoints(120);
            var frames = new Frames(spine, Vector3.UnitZ, 5);
            float r0 = duct.GetProperty("inner_radius_mm")[0].GetSingle(), r1 = duct.GetProperty("inner_radius_mm")[1].GetSingle();
            float wall = Config.GetProperty("duct_wall_mm").GetSingle();
            float Radius(float phi, float t) => r0 + (r1 - r0) * t;
            var pipe = new BasePipe(frames);
            pipe.SetRadius(new SurfaceModulation(Radius), new SurfaceModulation((phi, t) => Radius(phi, t) + wall));
            pipe.SetPolarSteps(96); pipe.SetLengthSteps(160);
            layers.Add(id, pipe.voxConstruct()); systems.Add(id, "new_duct"); added.Add(id);
            var lumen = new BasePipe(frames);
            lumen.SetRadius(new SurfaceModulation(0), new SurfaceModulation(Radius));
            lumen.SetPolarSteps(96); lumen.SetLengthSteps(160);
            fluid.Add(id + "_air", lumen.voxConstruct());
        }
        var heat = Vehicle.GetProperty("tail").GetProperty("heat_exchanger");
        float inset = Config.GetProperty("lattice").GetProperty("boundary_inset_mm").GetSingle();
        using Voxels zone = Box(Vec(heat.GetProperty("size_mm")) - new Vector3(2 * inset), Vec(heat.GetProperty("centre_mm")));
        float cell = Config.GetProperty("lattice").GetProperty("cell_mm").GetSingle();
        float diameter = Config.GetProperty("lattice").GetProperty("beam_diameter_mm").GetSingle();
        using Lattice beams = new();
        Lattice target = beams;
        var cells = new RegularCellArray(zone, cell, cell, cell, 0).aGetUnitCells();
        var topology = new BodyCentreLattice();
        foreach (var unit in cells) topology.AddCell(ref target, unit, new ConstantBeamThickness(diameter), 2);
        using Voxels untrimmed = new(beams);
        Voxels core = untrimmed & zone;
        layers.Add("tail_lattice_insert", core); systems.Add("tail_lattice_insert", "new_core"); added.Add("tail_lattice_insert");
        fluid.Add("tail_core_air", zone - core);

        var checks = new Dictionary<string, object>();
        foreach (string id in added)
        foreach (string obstacle in new[] { "firewall", "body_shell", "rear_structure_corridors", "transaxle_schematic", "wheel_motion_keepouts", "exhaust_left", "exhaust_right", "tail_plenum", "fixed_930_style_tail" })
        {
            using Voxels clash = layers[id] & layers[obstacle];
            checks[id + "__" + obstacle] = new { collision = !clash.bIsEmpty(), volume_mm3 = Volume(clash) };
        }
        var exports = new List<object>();
        foreach (var pair in added.Select(id => KeyValuePair.Create(id, layers[id])).Concat(fluid))
        {
            if (pair.Value.bIsEmpty()) throw new InvalidDataException("Empty generated domain");
            string stl = pair.Key + ".stl", vdb = pair.Key + ".vdb";
            using Mesh mesh = new(pair.Value); mesh.SaveToStlFile(Path.Combine(Output, stl));
            pair.Value.SaveToVdbFile(Path.Combine(Output, vdb));
            using Voxels restored = Voxels.voxFromVdbFile(Path.Combine(Output, vdb));
            if (!pair.Value.bIsEqual(restored)) throw new InvalidDataException("Geometry VDB roundtrip differs");
            exports.Add(new { id = pair.Key, volume_mm3 = Volume(pair.Value), triangles = mesh.nTriangleCount(), stl, stl_sha256 = Hash(Path.Combine(Output, stl)), vdb, vdb_sha256 = Hash(Path.Combine(Output, vdb)), vdb_equal = true });
        }
        using ScalarField distance = new(core);
        using VectorField gradient = new(core);
        string exchange = Path.Combine(Output, "tail-fields.vdb");
        using (OpenVdbFile file = new())
        {
            file.nAdd(core, "solid"); file.nAdd(fluid["tail_core_air"], "air");
            file.nAdd(distance, "solid_sdf_voxel"); file.nAdd(gradient, "solid_sdf_gradient"); file.SaveToFile(exchange);
        }
        using OpenVdbFile read = new(exchange);
        using Voxels solidRead = read.voxGet("solid"), airRead = read.voxGet("air");
        using ScalarField scalarRead = read.oGetScalarField("solid_sdf_voxel");
        using VectorField vectorRead = read.oGetVectorField("solid_sdf_gradient");
        if (read.nFieldCount() != 4 || read.fPicoGKVoxelSizeMM() != 5 || !core.bIsEqual(solidRead) || !fluid["tail_core_air"].bIsEqual(airRead))
            throw new InvalidDataException("Exchange domain mismatch");
        var forward = new FieldCheck(scalarRead, vectorRead); distance.TraverseActive(forward); gradient.TraverseActive(forward);
        var reverse = new FieldCheck(distance, gradient); scalarRead.TraverseActive(reverse); vectorRead.TraverseActive(reverse);
        if (forward.Bad || reverse.Bad || forward.Scalars == 0 || forward.Vectors == 0 || forward.Scalars != reverse.Scalars || forward.Vectors != reverse.Vectors)
            throw new InvalidDataException("Scalar/vector field roundtrip differs");
        // Negative control: a value added outside the domain must not survive unnoticed.
        using ScalarField corruptedScalar = new(distance);
        using VectorField corruptedVector = new(gradient);
        corruptedScalar.SetValue(new Vector3(-5000), 17);
        corruptedVector.SetValue(new Vector3(-5000), Vector3.One);
        var negative = new FieldCheck(distance, gradient);
        corruptedScalar.TraverseActive(negative); corruptedVector.TraverseActive(negative);
        if (!negative.Bad) throw new InvalidDataException("Field comparison negative control failed");
        var views = Views(layers, systems, fluid);
        foreach (var input in Receipt.GetProperty("files").EnumerateArray())
            if (Hash(input.GetProperty("path").GetString()!) != input.GetProperty("sha256").GetString()) throw new InvalidDataException("Input changed during native run");
        var report = new { phase = "F16", status = "geometry_study_not_qualified_vehicle", kernel = Library.strVersion(), voxel_mm = 5,
            config = Config, input_receipt = Receipt, assembly_sha256 = Hash(typeof(Program).Assembly.Location),
            components = exports, context_components = layers.Count - added.Count, checks, views,
            lattice_cells_before_clipping = cells.Count, solid_fraction_in_zone = Volume(core) / Volume(zone),
            field_exchange = new { file = "tail-fields.vdb", sha256 = Hash(exchange), field_count = 4, solid_air_equal = true, scalar_active_values = forward.Scalars, vector_active_values = forward.Vectors, bidirectional_values_equal = true, added_value_negative_control_rejected = true, physical_solver_executed = false },
            manufacturing_authorized = false };
        File.WriteAllText(Path.Combine(Output, "report.json"), JsonSerializer.Serialize(report, JsonOptions));
        foreach (var vox in layers.Values.Concat(fluid.Values)) vox.Dispose();
    }

    // Check both traversal directions: one-way probing would miss added active values.
    sealed class FieldCheck(ScalarField scalar, VectorField vector) : ITraverseScalarField, ITraverseVectorField
    {
        public long Scalars, Vectors;
        public bool Bad;
        public void InformActiveValue(in Vector3 p, float value) { Scalars++; Bad |= !float.IsFinite(value) || !scalar.bGetValue(p, out float actual) || actual != value; }
        public void InformActiveValue(in Vector3 p, in Vector3 value) { Vectors++; Bad |= !float.IsFinite(value.Length()) || !vector.bGetValue(p, out Vector3 actual) || actual != value; }
    }

    // The viewer writes the capture asynchronously: hashing as soon as the file exists
    // can digest a partial image. Wait for the size the uncompressed TGA header announces.
    static void WaitForCompleteTga(string path)
    {
        for (int attempt = 0; attempt < 600; attempt++, Thread.Sleep(50))
        {
            long length = new FileInfo(path).Length;
            if (length < 18) continue;
            var header = new byte[18];
            using (var f = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.ReadWrite)) f.ReadExactly(header);
            if (header[2] != 2) throw new InvalidDataException("Unexpected TGA encoding");
            long expected = 18 + (long)BitConverter.ToUInt16(header, 12) * BitConverter.ToUInt16(header, 14) * header[16] / 8;
            if (length < expected) continue;
            Thread.Sleep(200);
            if (new FileInfo(path).Length == length) return;
        }
        throw new IOException("Native capture never completed: " + path);
    }

    static List<object> Views(Dictionary<string, Voxels> layers, Dictionary<string, string> systems, Dictionary<string, Voxels> fluid)
    {
        Viewer v = Library.oViewer(); v.SetBackgroundColor("F3F4F6"); v.SetFov(MathF.PI / 6);
        var result = new List<object>();
        void Capture(string name, Quaternion orientation, IEnumerable<KeyValuePair<string, Voxels>> visible)
        {
            v.RemoveAllObjects(); int group = 0;
            foreach (var p in visible)
            {
                string colour = p.Key.Contains("lattice") ? "D49A40" : p.Key.Contains("air") ? "24A6C2" : systems.GetValueOrDefault(p.Key, "") == "new_duct" ? "24A6C2" : "7B8794";
                v.SetGroupMaterial(group, colour, .15f, .65f); v.Add(p.Value, group++);
            }
            string file = name + ".tga", path = Path.Combine(Output, file);
            v.qOrientation = orientation; v.ZoomToFit(); v.RequestScreenShot(path);
            for (int attempt = 0; attempt < 300 && !File.Exists(path); attempt++) Thread.Sleep(50);
            if (!File.Exists(path)) throw new IOException("Missing native capture");
            WaitForCompleteTga(path);
            result.Add(new { id = name, file, sha256 = Hash(path) });
        }
        Capture("mechanical", v.qOrientationHome, layers.Where(p => !new[] { "keepout", "body", "tail" }.Contains(systems[p.Key])));
        Capture("exterior", v.qOrientationHome, layers.Where(p => systems[p.Key] != "keepout"));
        Capture("air_paths", v.qOrientationHome, layers.Where(p => systems[p.Key] is "new_duct" or "new_core"));
        Capture("tail_core", v.qOrientationHome, layers.Where(p => p.Key == "tail_lattice_insert"));
        Capture("air_domains", v.qOrientationHome, fluid);
        v.RemoveAllObjects();
        return result;
    }
}
