using System.Globalization;
using System.Numerics;
using System.Security.Cryptography;
using System.Text.Json;
using PicoGK;

namespace PicoGKCatalog;

// Actual solver samples on the explicit VDB frame, not the native geometric gradient.
public static class FlowFieldsRunner
{
    sealed class ScalarCount : ITraverseScalarField
    {
        public int Count;
        public void InformActiveValue(in Vector3 p, float value)
        {
            if (!float.IsFinite(value)) throw new InvalidDataException("Nonfinite scalar");
            Count++;
        }
    }
    sealed class VectorCount : ITraverseVectorField
    {
        public int Count;
        public void InformActiveValue(in Vector3 p, in Vector3 value)
        {
            if (!float.IsFinite(value.Length())) throw new InvalidDataException("Nonfinite velocity");
            Count++;
        }
    }
    static string Hash(string path) => Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(path))).ToLowerInvariant();

    public static void Main(string[] args)
    {
        if (args.Length != 3 || Directory.Exists(args[2]))
            throw new ArgumentException("Use cell-fields.csv, flow-report.json and a new output directory");
        using JsonDocument flow = JsonDocument.Parse(File.ReadAllText(args[1]));
        if (Hash(args[0]) != flow.RootElement.GetProperty("cell_fields").GetProperty("sha256").GetString() ||
            !flow.RootElement.GetProperty("numerical_flow_screen_passed").GetBoolean())
            throw new InvalidDataException("Missing bound, numerically screened solver fields");
        using Library lib = new(.5f);
        using ScalarField pressure = new(lib);
        using VectorField velocity = new(lib);
        var rows = new List<(Vector3 point, float pressure, Vector3 velocity)>();
        var positions = new HashSet<Vector3>();
        double maxPressureRounding = 0, maxVelocityRounding = 0;
        string[] lines = File.ReadAllLines(args[0]);
        if (lines[0] != "x_mm,y_mm,z_mm,pressure_gauge_pa,ux_m_s,uy_m_s,uz_m_s")
            throw new InvalidDataException("Unknown field units");
        foreach (string line in lines.Skip(1))
        {
            double[] raw = line.Split(',').Select(v => double.Parse(v, CultureInfo.InvariantCulture)).ToArray();
            if (raw.Length != 7 || raw.Any(v => !double.IsFinite(v))) throw new InvalidDataException("Invalid sample");
            float[] v = raw.Select(v => (float)v).ToArray();
            if (v.Any(v => !float.IsFinite(v))) throw new InvalidDataException("Float32 overflow");
            Vector3 point = new(v[0], v[1], v[2]);
            if (v.Take(3).Any(v => Math.Abs(v * 2 - Math.Round(v * 2)) > 1e-4) || !positions.Add(point))
                throw new InvalidDataException("Duplicate or misaligned field location");
            Vector3 u = new(v[4], v[5], v[6]);
            pressure.SetValue(point, v[3]); velocity.SetValue(point, u);
            rows.Add((point, v[3], u));
            maxPressureRounding = Math.Max(maxPressureRounding, Math.Abs(raw[3] - v[3]));
            for (int i = 4; i < 7; i++) maxVelocityRounding = Math.Max(maxVelocityRounding, Math.Abs(raw[i] - v[i]));
        }
        if (rows.Count == 0 || rows.Count != flow.RootElement.GetProperty("cell_fields").GetProperty("count").GetInt32())
            throw new InvalidDataException("Missing solver samples");
        Directory.CreateDirectory(args[2]);
        string path = Path.Combine(args[2], "coolant-cfd-fields.vdb");
        using (OpenVdbFile writer = new(lib))
        {
            writer.nAdd(pressure, "pressure_gauge_pa"); writer.nAdd(velocity, "velocity_m_s"); writer.SaveToFile(path);
        }
        using OpenVdbFile reader = new(lib, path);
        if (reader.nFieldCount() != 2 || reader.fPicoGKVoxelSizeMM() != .5f)
            throw new InvalidDataException("Field frame changed");
        using ScalarField restoredPressure = reader.oGetScalarField("pressure_gauge_pa");
        using VectorField restoredVelocity = reader.oGetVectorField("velocity_m_s");
        foreach (var row in rows)
            if (!restoredPressure.bGetValue(row.point, out float p) || p != row.pressure ||
                !restoredVelocity.bGetValue(row.point, out Vector3 u) || u != row.velocity)
                throw new InvalidDataException("Physics field changed in VDB roundtrip");
        var scalarCount = new ScalarCount(); var vectorCount = new VectorCount();
        restoredPressure.TraverseActive(scalarCount); restoredVelocity.TraverseActive(vectorCount);
        if (scalarCount.Count != rows.Count || vectorCount.Count != rows.Count)
            throw new InvalidDataException("Active topology changed");
        var report = new { status = "actual_cfd_fields_exchanged_not_physical_validation", samples = rows.Count,
            csv_sha256 = Hash(args[0]), flow_report_sha256 = Hash(args[1]), vdb_sha256 = Hash(path),
            voxel_mm = .5, sample_coordinates = "mm", pressure = "Pa gauge", velocity = "m/s",
            float32_pressure_max_rounding_pa = maxPressureRounding,
            float32_velocity_max_rounding_m_s = maxVelocityRounding,
            all_float32_samples_roundtrip_exact = true, active_topology_preserved = true,
            interpretation = "Sparse, cell-constant CFD samples; missing locations remain missing; no conservative interpolation claim",
            hydraulic_performance_validated = false, manufacturing_authorized = false };
        File.WriteAllText(Path.Combine(args[2], "physics-fields-report.json"),
            JsonSerializer.Serialize(report, new JsonSerializerOptions { WriteIndented = true }) + "\n");
        Console.WriteLine(JsonSerializer.Serialize(report));
    }
}
