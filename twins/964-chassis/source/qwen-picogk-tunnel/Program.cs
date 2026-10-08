// Local geometric interference study. No measured interfaces, laminate or release authority.
using System.Globalization;
using System.Numerics;
using System.Security.Cryptography;
using System.Text.Json;
using PicoGK;

if (args.Length != 3)
    throw new ArgumentException("Usage: Tunnel <input.json> <new-output-directory> <voxel-mm: 2|4>");
float voxel = float.Parse(args[2], CultureInfo.InvariantCulture);
if (voxel != 2 && voxel != 4) throw new ArgumentException("Use the fixed 2 or 4 mm study grids.");
if (Directory.Exists(args[1]) || File.Exists(args[1])) throw new ArgumentException("Output must be new.");
string Hash(string path) => Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(path))).ToLowerInvariant();
using JsonDocument document = JsonDocument.Parse(File.ReadAllText(args[0]));
JsonElement job = document.RootElement;
const float Scale = 50;
if (job.GetProperty("scale").GetSingle() != Scale || job.GetProperty("manufacturing_authorized").GetBoolean()
    || job.GetProperty("vehicle_fit_verified").GetBoolean()
    || job.GetProperty("status").GetString() != "hypothetical_tunnel_interference_study_not_oem")
    throw new ArgumentException("Invalid study scope.");
string receipt = Path.Combine(Path.GetDirectoryName(Path.GetFullPath(args[0]))!, "inference.json");
if (Hash(receipt) != job.GetProperty("inference_sha256").GetString())
    throw new ArgumentException("Inference receipt changed.");
using JsonDocument inference = JsonDocument.Parse(File.ReadAllText(receipt));
if (inference.RootElement.GetProperty("status").GetString() != "accepted_bounded_transcription")
    throw new ArgumentException("Qwen transcription was not accepted.");
var names = new HashSet<string> { "c2_shift_rod", "c4_central_tube", "c4_shift_guide" };
JsonElement accepted = job.GetProperty("accepted_beams_mm");
if (!names.SetEquals(accepted.EnumerateObject().Select(p => p.Name)))
    throw new ArgumentException("Incomplete driveline envelope set.");
foreach (string name in names)
    if (accepted.GetProperty(name).GetRawText() != job.GetProperty("expected_beams_mm").GetProperty(name).GetRawText())
        throw new ArgumentException("Accepted geometry differs from the reviewed specification.");

using Library lib = new(voxel / Scale);
float[] Numbers(JsonElement data, int count) {
    if (data.GetArrayLength() != count) throw new ArgumentException("Invalid primitive size.");
    float[] values = data.EnumerateArray().Select(v => v.GetSingle()).ToArray();
    if (values.Any(v => !float.IsFinite(v) || Math.Abs(v) > 3000))
        throw new ArgumentException("Primitive exceeds bounded study coordinates.");
    return values;
}
Voxels Box(JsonElement data) {
    float[] b = Numbers(data, 6);
    if (b.Skip(3).Any(v => v < 10)) throw new ArgumentException("Box too small for this grid.");
    Vector3 center = new(b[0]/Scale, b[1]/Scale, b[2]/Scale);
    Vector3 half = new(b[3]/(2*Scale), b[4]/(2*Scale), b[5]/(2*Scale));
    using Mesh cube = Utils.mshCreateCube(lib, new BBox3(center-half, center+half));
    return new Voxels(cube);
}
Voxels Beam(JsonElement data) {
    if (data.GetArrayLength() != 9 || data[8].GetBoolean())
        throw new ArgumentException("Exactly one flat-capped beam expected.");
    float[] b = data.EnumerateArray().Take(8).Select(v => v.GetSingle()).ToArray();
    if (b.Any(v => !float.IsFinite(v) || Math.Abs(v) > 3000) || b[3] < 10 || b[3] > 200 || b[7] != b[3])
        throw new ArgumentException("Invalid bounded cylinder.");
    using Lattice lattice = new(lib);
    lattice.AddBeam(new Vector3(b[0], b[1], b[2])/Scale, b[3]/Scale,
                    new Vector3(b[4], b[5], b[6])/Scale, b[7]/Scale, false);
    return new Voxels(lattice);
}
double Volume(Voxels solid) {
    if (solid.bIsEmpty()) return 0;
    solid.CalculateProperties(out float v, out BBox3 _);
    return (double)v*Scale*Scale*Scale;
}
void Export(Voxels solid, string name) {
    using Mesh mesh = new(solid);
    if (mesh.nTriangleCount() == 0) throw new InvalidOperationException("Empty mesh.");
    mesh.SaveToStlFile(Path.Combine(args[1], name + ".stl"), fScale: Scale);
}

using Voxels baseline = new(lib);
if (job.GetProperty("boxes_mm").GetArrayLength() != 5) throw new ArgumentException("Expected five tunnel/floor volumes.");
foreach (JsonElement data in job.GetProperty("boxes_mm").EnumerateArray()) {
    using Voxels panel = Box(data);
    baseline.BoolAdd(panel);
}
using Voxels relieved = new(baseline);
using Voxels envelopes = new(lib);
var results = new List<object>();
var envelopeSolids = new Dictionary<string, Voxels>();
try {
    foreach (string name in names) envelopeSolids.Add(name, Beam(accepted.GetProperty(name)));
    envelopeSolids.Add("c2_shifter_tower", Box(job.GetProperty("tower_box_mm")));
    foreach (var item in envelopeSolids) {
        using Voxels overlap = baseline.voxBoolIntersect(item.Value);
        double measured = Volume(overlap);
        double analytic = job.GetProperty("analytic_collision_mm3").GetProperty(item.Key).GetDouble();
        if ((analytic > 0) != (measured > 0)) throw new InvalidOperationException("Native and analytic interference signs disagree.");
        results.Add(new { feature = item.Key, baseline_collision_mm3 = measured,
            analytic_collision_mm3 = analytic, relative_volume_error = analytic == 0 ? 0 : (measured-analytic)/analytic });
        relieved.BoolSubtract(item.Value);
        envelopes.BoolAdd(item.Value);
    }
    using Voxels residual = relieved.voxBoolIntersect(envelopes);
    double residualVolume = Volume(residual);
    if (residualVolume != 0) throw new InvalidOperationException("Residual overlap after same-grid subtraction.");
    // These probes are independent geometric observations, not complete clearance tests.
    bool nosePassage = !relieved.bIsInside(new Vector3(430, 0, 310)/Scale);
    bool serviceOpening = !relieved.bIsInside(new Vector3(980, 0, 455)/Scale);
    bool wallsRemain = relieved.bIsInside(new Vector3(1100, 152, 300)/Scale)
                    && relieved.bIsInside(new Vector3(1100, -152, 300)/Scale);
    if (!(nosePassage && serviceOpening && wallsRemain)) throw new InvalidOperationException("Tunnel probes failed.");
    Directory.CreateDirectory(args[1]);
    Export(baseline, "tunnel-baseline");
    Export(relieved, "tunnel-relief-study");
    Export(envelopes, "driveline-envelopes");
    var report = new {
        status = "hypothetical_geometric_study_only", voxel_size_mm = voxel, scale = Scale,
        input_sha256 = Hash(args[0]), inference_sha256 = Hash(receipt),
        picogk_assembly_sha256 = Hash(typeof(Library).Assembly.Location), runtime = Environment.Version.ToString(),
        baseline_volume_mm3 = Volume(baseline), relieved_volume_mm3 = Volume(relieved),
        collisions = results, residual_same_grid_collision_mm3 = residualVolume,
        nose_passage_probe = nosePassage, service_opening_probe = serviceOpening, side_wall_probes = wallsRemain,
        geometry_note = "Five local tunnel/floor volumes only. C2/C4 are hypothetical packages, not measured 964/993 variants.",
        relief_note = "Same-grid subtraction has zero design allowance. It is not an independent clearance or tolerance verification.",
        structural_simulation_performed = false, dynamic_clearance_verified = false,
        manufacturing_authorized = false, vehicle_fit_verified = false
    };
    string json = JsonSerializer.Serialize(report, new JsonSerializerOptions { WriteIndented = true });
    File.WriteAllText(Path.Combine(args[1], "report.json"), json + "\n");
    Console.WriteLine(json);
} finally {
    foreach (Voxels solid in envelopeSolids.Values) solid.Dispose();
}
