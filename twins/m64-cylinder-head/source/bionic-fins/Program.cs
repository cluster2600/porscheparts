using System.Globalization;
using System.Numerics;
using System.Security.Cryptography;
using System.Text.Json;
using System.Text.Json.Serialization;
using Leap71.ShapeKernel;
using PicoGK;

var json = new JsonSerializerOptions { PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower,
    UnmappedMemberHandling = JsonUnmappedMemberHandling.Disallow, RespectRequiredConstructorParameters = true,
    WriteIndented = true };
void Require(bool ok, string message) { if (!ok) throw new InvalidDataException(message); }
void Validate(Design d, float step)
{
    Require(float.IsFinite(d.DepthMm) && d.DepthMm > 0 && d.DepthMm <= 100
        && float.IsFinite(d.PitchMm) && d.PitchMm > 0 && d.PitchMm <= 100, "Invalid coupon dimensions");
    Require(d.Edges is not null && d.Edges.Length >= 1 && d.Edges.Length <= 15, "Invalid tree size");
    var seen = new HashSet<Vector2> { Vector2.Zero }; var incoming = new HashSet<Vector2>();
    foreach (var e in d.Edges!)
    {
        Require(e.A is { Length: 2 } && e.B is { Length: 2 }, "Expected X/Z points");
        Require(e.A.Concat(e.B).Append(e.T0Mm).Append(e.T1Mm).All(float.IsFinite), "Non-finite edge");
        Vector2 a = new(e.A[0], e.A[1]), b = new(e.B[0], e.B[1]);
        Require(seen.Contains(a) && !incoming.Contains(b) && b.Y > a.Y && b.Y <= 40, "Invalid rooted tree");
        Require(MathF.Min(e.T0Mm, e.T1Mm) >= MathF.Max(1.2f, 4*step)
            && MathF.Max(e.T0Mm, e.T1Mm) <= 8, "Unresolved thickness");
        Require(MathF.Max(MathF.Abs(a.X)+e.T0Mm/2, MathF.Abs(b.X)+e.T1Mm/2) <= d.PitchMm/2-1,
            "Neighbor clearance envelope violated");
        seen.Add(b); incoming.Add(b);
    }
}
if (args is ["--self-test"])
{
    Design good = new("witness", 60, 14, [new([0, 0], [0, 28], 3, 3)]);
    Validate(good, .3f);
    foreach (Design bad in new[] { good with { DepthMm = float.NaN }, good with { Edges = [] },
        good with { Edges = [new([1, 0], [0, 28], 3, 3)] },
        good with { Edges = [new([0, 0], [0, 28], 3, 1)] } })
    {
        bool refused = false;
        try { Validate(bad, .3f); } catch (InvalidDataException) { refused = true; }
        Require(refused, "Invalid design was accepted");
    }
    Console.WriteLine("Bionic fin boundary self-checks passed"); return 0;
}
if (args.Length != 3 || !float.TryParse(args[2], NumberStyles.Float, CultureInfo.InvariantCulture, out float step)
    || !float.IsFinite(step) || (step != .3f && step != .15f))
{ Console.Error.WriteLine("Usage: BionicFins DESIGN_JSON NEW_OUTPUT_DIR 0.3_OR_0.15"); return 2; }
string input = Path.GetFullPath(args[0]), output = Path.GetFullPath(args[1]);
string Sha(string file) { using var stream = File.OpenRead(file); return Convert.ToHexString(SHA256.HashData(stream)).ToLowerInvariant(); }
try
{
    Require(File.Exists(input) && (File.GetAttributes(input)&FileAttributes.ReparsePoint) == 0, "Input must be a regular file");
    Require(!Directory.Exists(output) && !File.Exists(output), "Output must be new");
    string inputHash = Sha(input);
    Design d = JsonSerializer.Deserialize<Design>(File.ReadAllText(input), json) ?? throw new InvalidDataException("Missing design");
    Validate(d, step);
    Directory.CreateDirectory(output);
    using Library lib = new(step); Library.RegisterGlobalLibrary(lib);
    // A common non-integral sampling phase avoids aligned degeneracies; exports undo it.
    Vector3 phase = new(.173f, .119f, .071f);
    using Voxels fin = new(lib);
    foreach (var e in d.Edges)
    {
        Vector3 a = new(e.A[0], 0, e.A[1]), b = new(e.B[0], 0, e.B[1]);
        Vector3 axis = Vector3.Normalize(b-a), normal = Vector3.Cross(Vector3.UnitY, axis);
        var box = new BaseBox(new LocalFrame(a+phase, axis, normal), Vector3.Distance(a, b), e.T0Mm, d.DepthMm);
        box.SetWidth(new LineModulation(t => e.T0Mm+(e.T1Mm-e.T0Mm)*t));
        box.SetWidthSteps(5); box.SetLengthSteps(5);
        using Voxels sheet = box.voxConstruct(); fin.BoolAdd(sheet);
    }
    object Export(Voxels field, string name)
    {
        using Mesh grid = new(field);
        using Mesh mesh = grid.mshCreateTransformed(Vector3.One, -phase);
        Require(mesh.nTriangleCount() > 0, "Empty export");
        field.CalculateProperties(out float volume, out _);
        Require(float.IsFinite(volume) && volume > 0, "Invalid native volume");
        double signed = 0, area = 0;
        for (int i = 0; i < mesh.nTriangleCount(); i++)
        {
            mesh.GetTriangle(i, out Vector3 a, out Vector3 b, out Vector3 c);
            area += Vector3.Cross(b-a, c-a).Length()/2;
            signed += ((double)a.X*(b.Y*(double)c.Z-b.Z*(double)c.Y)
                + (double)a.Y*(b.Z*(double)c.X-b.X*(double)c.Z)
                + (double)a.Z*(b.X*(double)c.Y-b.Y*(double)c.X))/6;
        }
        string file = Path.Combine(output, name+".stl"); mesh.SaveToStlFile(file, Mesh.EStlUnit.MM);
        return new { filename = name+".stl", sha256 = Sha(file), triangles = mesh.nTriangleCount(),
            native_volume_mm3 = volume, oriented_mesh_volume_mm3 = signed, surface_area_mm2 = area };
    }
    var single = Export(fin, "fin");
    using Voxels bank = new(lib);
    for (int i = -1; i <= 1; i++)
    {
        using Mesh m = new(fin); using Mesh placed = m.mshCreateTransformed(Vector3.One, new(i*d.PitchMm, 0, 0));
        using Voxels copy = new(placed); bank.BoolAdd(copy);
    }
    using Voxels basePlate = new BaseBox(new LocalFrame(new Vector3(0, 0, -4)+phase), 4, 3*d.PitchMm, d.DepthMm).voxConstruct();
    bank.BoolAdd(basePlate);
    var coupon = Export(bank, "coupon");
    Require(Sha(input) == inputHash, "Input changed during execution");
    double nominal = d.DepthMm*d.Edges.Sum(e => Vector2.Distance(new(e.A[0], e.A[1]), new(e.B[0], e.B[1]))*(e.T0Mm+e.T1Mm)/2);
    var report = new { schema = "m64-bionic-fin-geometry/v1", design_id = d.Id,
        voxel_mm = step, input_sha256 = inputHash, program_sha256 = Sha(typeof(Design).Assembly.Location),
        picogk_sha256 = Sha(typeof(Library).Assembly.Location), native_version = Library.strVersion(),
        shape_kernel_revision = "7b9097842446a28bb5d49203724622e594ce7510",
        nominal_nonoverlap_volume_mm3 = nominal, single, coupon,
        source_master_modified = false, real_head_integrated = false,
        thermal_validated = false, manufacturing_authorized = false,
        status = "extruded_fin_coupon_not_a_cylinder_head", airflow_direction_hypothesis = "Y" };
    File.WriteAllText(Path.Combine(output, "geometry.json"), JsonSerializer.Serialize(report, json)+"\n");
    Library.UnregisterGlobalLibrary();
    Console.WriteLine("Bionic fin geometry generated; not an engineering acceptance"); return 0;
}
catch (Exception error) { Console.Error.WriteLine(error.GetType().Name+": "+error.Message); return 1; }

record Edge(float[] A, float[] B, float T0Mm, float T1Mm);
record Design(string Id, float DepthMm, float PitchMm, Edge[] Edges);
