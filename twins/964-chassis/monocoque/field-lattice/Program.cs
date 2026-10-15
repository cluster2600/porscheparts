using System.Numerics;
using System.Security.Cryptography;
using System.Text.Json;
using PicoGK;
using Leap71.ShapeKernel;
using Leap71.LatticeLibrary;

if (args.Length != 2) throw new ArgumentException("SAMPLES_JSON NEW_OUTPUT_DIRECTORY");
using var document = JsonDocument.Parse(File.ReadAllText(args[0]));
var input = document.RootElement;
if (input.GetProperty("schema_version").GetInt32() != 1 ||
    input.GetProperty("voxel_mm").GetSingle() != 0.5f ||
    input.GetProperty("frame").GetString() != "F0_GLOBAL_X_forward_Y_left_Z_up" ||
    input.GetProperty("value_unit").GetString() != "MPa")
    throw new InvalidDataException("Unsupported field contract");
float[][] rows = input.GetProperty("rows").EnumerateArray()
    .Select(r => r.EnumerateArray().Select(v => v.GetSingle()).ToArray()).ToArray();
if (rows.Length == 0 || rows.Length > 200000 || rows.Any(r => r.Length != 6 ||
    r.Any(v => !float.IsFinite(v)) || r.Take(3).Any(v => Math.Abs(v) > 5000 || v*2 != MathF.Round(v*2)) ||
    r[3] < 0 || r[4] < 0 || r[5] < 1 || r[5] != MathF.Round(r[5])))
    throw new InvalidDataException("Invalid sparse samples");
Vector3 Point(float[] row) => new(row[0], row[1], row[2]);
if (rows.Select(Point).Distinct().Count() != rows.Length)
    throw new InvalidDataException("Duplicate sparse positions");
float[] peaks = { rows.Max(r => r[3]), rows.Max(r => r[4]) };
if (peaks.Any(v => v <= 0)) throw new InvalidDataException("Empty demand");
string output = Path.GetFullPath(args[1]);
if (Directory.Exists(output) || File.Exists(output)) throw new IOException("Output already exists");
Directory.CreateDirectory(output);
using Library lib = new(0.5f);
Library.RegisterGlobalLibrary(lib);
try
{
    string[] names = { "torsion_vm_bin_max_MPa", "bending_vm_bin_max_MPa", "integration_point_count" };
    using (OpenVdbFile file = new(lib))
    {
        for (int i = 0; i < names.Length; i++)
        {
            using ScalarField field = new(lib);
            field.oMetaData().SetValue("study.unit", i < 2 ? "MPa" : "count");
            field.oMetaData().SetValue("study.frame", "F0_GLOBAL_X_forward_Y_left_Z_up");
            field.oMetaData().SetValue("study.scope", "F0 demand display; not CFRP failure or strength");
            foreach (var row in rows) field.SetValue(Point(row), row[i+3]);
            file.nAdd(field, names[i]);
        }
        file.SaveToFile(Path.Combine(output, "demand.vdb"));
    }
    using OpenVdbFile restored = new(lib, Path.Combine(output, "demand.vdb"));
    if (restored.nFieldCount() != 3 || !restored.bIsPicoGKCompatible() || restored.fPicoGKVoxelSizeMM() != 0.5f)
        throw new InvalidDataException("VDB structure mismatch");
    for (int i = 0; i < names.Length; i++)
    {
        using ScalarField field = restored.oGetScalarField(names[i]);
        var traversal = new Counter();
        field.TraverseActive(traversal);
        if (traversal.Count != rows.Length ||
            !field.oMetaData().bGetValueAt("study.unit", out string unit) || unit != (i < 2 ? "MPa" : "count") ||
            !field.oMetaData().bGetValueAt("study.frame", out string frame) || frame != "F0_GLOBAL_X_forward_Y_left_Z_up" ||
            field.bGetValue(new Vector3(9000), out _))
            throw new InvalidDataException("Active topology / metadata mismatch");
        foreach (var row in rows)
            if (!field.bGetValue(Point(row), out float value) || value != row[i+3])
                throw new InvalidDataException("Field changed on VDB roundtrip");
    }
    // Exercise active zero and signed coordinates separately from vehicle fields.
    using (ScalarField witness = new(lib))
    {
        witness.SetValue(new Vector3(-1, 2, -3), 0);
        witness.SetValue(new Vector3(1, -2, 3), -7.25f);
        using (OpenVdbFile file = new(lib))
        { file.nAdd(witness, "witness"); file.SaveToFile(Path.Combine(output, "exchange-witness.vdb")); }
        using OpenVdbFile fileIn = new(lib, Path.Combine(output, "exchange-witness.vdb"));
        using ScalarField field = fileIn.oGetScalarField("witness");
        if (!field.bGetValue(new Vector3(-1, 2, -3), out float zero) || zero != 0 ||
            !field.bGetValue(new Vector3(1, -2, 3), out float signed) || signed != -7.25f ||
            field.bGetValue(Vector3.Zero, out _)) throw new InvalidDataException("Zero / sign / inactivity lost");
    }
    Vector3 peak = Point(rows.MaxBy(r => r[4])!);
    Vector3 min = new(MathF.Floor(peak.X/12)*12-24, MathF.Floor(peak.Y/12)*12-24, MathF.Floor(peak.Z/12)*12-24);
    Vector3 max = min + new Vector3(48);
    using Voxels envelope = new BaseBox(new BBox3(min, max)).voxConstruct();
    using ScalarField torsion = restored.oGetScalarField(names[0]);
    using ScalarField bending = restored.oGetScalarField(names[1]);
    var demands = new Dictionary<(int X, int Y, int Z), float>();
    foreach (var row in rows)
    {
        Vector3 p = Point(row), q = (p-min)/12;
        if (q.X < 0 || q.Y < 0 || q.Z < 0 || q.X >= 4 || q.Y >= 4 || q.Z >= 4) continue;
        if (!torsion.bGetValue(p, out float t) || !bending.bGetValue(p, out float b))
            throw new InvalidDataException("Unknown demand cannot create a cell");
        var key = ((int)q.X, (int)q.Y, (int)q.Z);
        demands[key] = Math.Max(demands.GetValueOrDefault(key), Math.Max(t/peaks[0], b/peaks[1]));
    }
    if (demands.Count == 0) throw new InvalidDataException("No samples in study region");
    var cellReports = new List<object>();
    var geometryReports = new List<object>();
    using OpenVdbFile geometryFile = new(lib);
    geometryFile.nAdd(envelope, "study_envelope");
    foreach (bool graded in new[]{false, true})
    {
        Lattice lattice = new(lib);
        try
        {
            foreach (var (key, demand) in demands.OrderBy(kv => kv.Key))
            {
                Vector3 p = min + new Vector3(key.X, key.Y, key.Z)*12;
                Vector3 x = new(12,0,0), y = new(0,12,0), z = new(0,0,12);
                var cell = new CuboidCell(p,p+x,p+x+y,p+y,p+z,p+x+z,p+x+y+z,p+y+z);
                // shortcut: bounded display heuristic, not a stress-to-CFRP sizing law.
                float diameter = graded ? 2 + 4*MathF.Sqrt(demand) : 2;
                new BodyCentreLattice().AddCell(ref lattice, cell, new ConstantBeamThickness(diameter), 2);
                if (graded) cellReports.Add(new { min_mm = new[]{p.X,p.Y,p.Z}, demand, diameter_mm = diameter });
            }
            using Voxels solid = new(lattice);
            solid.BoolIntersect(envelope);
            solid.CalculateProperties(out float volume, out BBox3 bounds);
            if (!float.IsFinite(volume) || volume <= 0) throw new InvalidDataException("Empty lattice");
            string name = graded ? "graded_probe" : "uniform_probe";
            using Mesh mesh = new(solid);
            mesh.SaveToStlFile(Path.Combine(output, name+".stl"), Mesh.EStlUnit.MM);
            geometryFile.nAdd(solid, name);
            geometryReports.Add(new { name, volume_mm3 = volume, triangles = mesh.nTriangleCount(),
                bounds_min_mm = new[]{bounds.vecMin.X,bounds.vecMin.Y,bounds.vecMin.Z},
                bounds_max_mm = new[]{bounds.vecMax.X,bounds.vecMax.Y,bounds.vecMax.Z} });
        }
        finally { lattice.Dispose(); }
    }
    geometryFile.SaveToFile(Path.Combine(output, "probes.vdb"));
    using OpenVdbFile geometryRestored = new(lib, Path.Combine(output, "probes.vdb"));
    for (int i = 0; i < geometryFile.nFieldCount(); i++)
    {
        using Voxels original = geometryFile.voxGet(i);
        using Voxels after = geometryRestored.voxGet(geometryFile.strFieldName(i));
        if (!original.bIsEqual(after)) throw new InvalidDataException("Geometry VDB changed");
    }
    var report = new { schema_version = 1, active_bins_per_field = rows.Length,
        input_integration_points_per_case = rows.Sum(r => (double)r[5]), field_names = names,
        voxel_mm = 0.5f, all_sample_values_bitwise_equal = true, inactive_probe_passed = true,
        zero_signed_coordinate_witness_passed = true, geometry_vdb_equal = true,
        samples_sha256 = Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(args[0]))).ToLowerInvariant(),
        peak_bin_mm = new[]{peak.X,peak.Y,peak.Z}, study_min_mm = new[]{min.X,min.Y,min.Z},
        study_max_mm = new[]{max.X,max.Y,max.Z}, cell_side_mm = 12, cells = cellReports,
        geometry = geometryReports, design_rule = "diameter_mm = 2 + 4 sqrt(max(torsion/torsion_peak, bending/bending_peak))",
        structural_optimization = false, product_strength_validated = false, manufacturing_authorized = false,
        scope = "local field-driven geometric probe, not a fitted core or laminate; no load combination or new FEA" };
    File.WriteAllText(Path.Combine(output, "report.json"), JsonSerializer.Serialize(report, new JsonSerializerOptions { WriteIndented = true })+"\n");
    Console.WriteLine($"Verified {rows.Length} sparse bins in three fields; built {demands.Count} local BCC cells.");
}
finally { Library.UnregisterGlobalLibrary(); }

sealed class Counter : ITraverseScalarField
{
    public int Count;
    public void InformActiveValue(in Vector3 position, float value) { Count++; }
}
