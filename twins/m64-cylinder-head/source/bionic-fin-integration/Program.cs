using System.Globalization;
using System.Numerics;
using System.Security.Cryptography;
using System.Text.Json;
using Leap71.ShapeKernel;
using PicoGK;

if (args.Length != 5 || !float.TryParse(args[4], NumberStyles.Float, CultureInfo.InvariantCulture, out float step)
    || !float.IsFinite(step) || (step != .3f && step != .15f))
{ Console.Error.WriteLine("Usage: Integration INPUT_DIR CONTRACT_JSON PROFILE_JSON NEW_OUTPUT_DIR 0.3_OR_0.15"); return 2; }
string input = Path.GetFullPath(args[0]), contractPath = Path.GetFullPath(args[1]), profilePath = Path.GetFullPath(args[2]), output = Path.GetFullPath(args[3]);
void Require(bool test, string message) { if (!test) throw new InvalidDataException(message); }
string Sha(string path) { using var file = File.OpenRead(path); return Convert.ToHexString(SHA256.HashData(file)).ToLowerInvariant(); }
Vector3 Vector(JsonElement e) => new(e[0].GetSingle(), e[1].GetSingle(), e[2].GetSingle());
var pins = new Dictionary<string, string>();
void Pin(string path, string expected)
{
    Require(File.Exists(path) && (File.GetAttributes(path)&FileAttributes.ReparsePoint) == 0 && Sha(path) == expected, "Input hash or type mismatch: "+Path.GetFileName(path));
    pins[path] = expected;
}
try
{
    Require(!Directory.Exists(output) && !File.Exists(output), "Output must be new");
    Pin(contractPath, Sha(contractPath));
    using var contract = JsonDocument.Parse(File.ReadAllText(contractPath)); var c = contract.RootElement;
    Require(c.GetProperty("schema").GetString() == "m64-bionic-fin-integration-contract/v1"
        && c.GetProperty("manufacturing_authorized").GetBoolean() == false
        && c.GetProperty("source_master_modified").GetBoolean() == false, "Research contract required");
    Require(c.GetProperty("depth").GetSingle() == 70 && c.GetProperty("root_abs_x").GetSingle() == 47.2f
        && c.GetProperty("tip_abs_x").GetSingle() == 59 && c.GetProperty("profile_radial_length").GetSingle() == 28
        && c.GetProperty("audit_halo").GetSingle() == .6f
        && c.GetProperty("root_z").EnumerateArray().Select(v => v.GetSingle()).SequenceEqual(new float[] { 16, 30, 44 }), "Exact bounded placement required");
    var zones = c.GetProperty("modified_zones").EnumerateArray().Select(z => (Min: Vector(z.GetProperty("min")), Max: Vector(z.GetProperty("max")))).ToArray();
    Require(zones.Length == 2 && zones[0] == (new Vector3(-61,-35,12), new Vector3(-48,35,48))
        && zones[1] == (new Vector3(48,-35,12), new Vector3(61,35,48)), "Independent modification mask required");
    Pin(Path.Combine(input,"inputs.json"), c.GetProperty("input_manifest_sha256").GetString()!);
    using var manifest = JsonDocument.Parse(File.ReadAllText(Path.Combine(input,"inputs.json")));
    var references = manifest.RootElement.GetProperty("parts").EnumerateArray().ToArray();
    Require(references.Length == 13 && references.Count(v => v.GetProperty("role").GetString() == "head") == 1, "Retained thirteen-part module required");
    foreach (var part in references)
    {
        string name = part.GetProperty("name").GetString()!, file = part.GetProperty("filename").GetString()!;
        Require(file == name+".stl" && Path.GetFileName(file) == file, "Local reference filename required");
        Pin(Path.Combine(input,file),part.GetProperty("sha256").GetString()!);
    }
    string headPath = Path.Combine(input,"head.stl"); Pin(headPath,c.GetProperty("head_stl_sha256").GetString()!);
    Pin(profilePath,c.GetProperty("profile_sha256").GetString()!);
    using var profile = JsonDocument.Parse(File.ReadAllText(profilePath)); var edges = profile.RootElement.GetProperty("edges").EnumerateArray().ToArray();
    Require(profile.RootElement.GetProperty("id").GetString() == "leaf-0.7-2.0-2.2-0.75", "Retained bionic profile required");
    Directory.CreateDirectory(output);
    using Library lib = new(step); Library.RegisterGlobalLibrary(lib);
    Vector3 phase = new(.173f,.119f,.071f);
    using Mesh source = Mesh.mshFromStlFile(headPath,Mesh.EStlUnit.MM,libSet:lib);
    using Mesh sampled = source.mshCreateTransformed(Vector3.One,phase);
    using Voxels baseline = new(sampled);
    using Voxels mask = new(lib); using Voxels halo = new(lib);
    foreach (var zone in zones)
    {
        using Voxels box = new BaseBox(new BBox3(zone.Min+phase,zone.Max+phase)).voxConstruct(); mask.BoolAdd(box);
        using Voxels grown = new BaseBox(new BBox3(zone.Min+phase-new Vector3(.6f),zone.Max+phase+new Vector3(.6f))).voxConstruct(); halo.BoolAdd(grown);
    }
    using Voxels retained = baseline.voxBoolSubtract(mask);
    using Voxels fins = new(lib);
    var attachments = new List<object>();
    foreach (int sign in new[] { -1, 1 }) foreach (float z in new float[] { 16,30,44 })
    {
        using Voxels leaf = new(lib);
        foreach (var edge in edges)
        {
            Vector3 Point(JsonElement p) => new(sign*(47.2f+p[1].GetSingle()*11.8f/28),0,z+p[0].GetSingle());
            Vector3 a = Point(edge.GetProperty("a")), b = Point(edge.GetProperty("b"));
            float t0 = edge.GetProperty("t0_mm").GetSingle(), t1 = edge.GetProperty("t1_mm").GetSingle();
            Vector3 axis = Vector3.Normalize(b-a), normal = Vector3.Normalize(Vector3.Cross(Vector3.UnitY,axis));
            var box = new BaseBox(new LocalFrame(a+phase,axis,normal),Vector3.Distance(a,b),t0,70);
            box.SetWidth(new LineModulation(t => t0+(t1-t0)*t)); box.SetWidthSteps(5); box.SetLengthSteps(5);
            using Voxels sheet = box.voxConstruct(); leaf.BoolAdd(sheet);
        }
        using Voxels overlap = leaf.voxBoolIntersect(retained);
        overlap.CalculateProperties(out float contact,out _);
        Require(float.IsFinite(contact) && contact > 0,"Unattached fin root");
        attachments.Add(new { side = sign, root_z = z, native_root_overlap_before_mask_clip = contact,
            physical_contact_or_load_capacity_verified = false });
        leaf.BoolIntersect(mask); fins.BoolAdd(leaf);
    }
    using Voxels candidate = retained.voxBoolAdd(fins);
    using Voxels added = candidate.voxBoolSubtract(baseline);
    using Voxels removed = baseline.voxBoolSubtract(candidate);
    int Triangles(Voxels field) { using Mesh mesh = new(field); return mesh.nTriangleCount(); }
    using Voxels addedOutside = added.voxBoolSubtract(halo);
    using Voxels removedOutside = removed.voxBoolSubtract(halo);
    int addedOutsideCount = Triangles(addedOutside), removedOutsideCount = Triangles(removedOutside);
    Require(addedOutsideCount == 0 && removedOutsideCount == 0,"Protected geometry changed outside mask halo");
    object Export(Voxels field,string name)
    {
        using Mesh grid = new(field); using Mesh mesh = grid.mshCreateTransformed(Vector3.One,-phase);
        Require(mesh.nTriangleCount() > 0,"Empty export: "+name);
        string path = Path.Combine(output,name+".stl"); mesh.SaveToStlFile(path,Mesh.EStlUnit.MM);
        field.CalculateProperties(out float volume,out _);
        BBox3 bounds = mesh.oBoundingBox();
        return new { filename = name+".stl", sha256 = Sha(path), triangles = mesh.nTriangleCount(),
            native_volume_scan_units_cubed = volume, min = new[] {bounds.vecMin.X,bounds.vecMin.Y,bounds.vecMin.Z},
            max = new[] {bounds.vecMax.X,bounds.vecMax.Y,bounds.vecMax.Z} };
    }
    var files = new[] { Export(baseline,"baseline"),Export(candidate,"head-bionic"),Export(fins,"fins"),Export(added,"added"),Export(removed,"removed") };
    foreach (var pin in pins) Require(Sha(pin.Key) == pin.Value,"Input changed during generation");
    var report = new { schema = "m64-bionic-head-integration/v1", status = "geometry_candidate_not_qualified",
        voxel_scan_units = step, units = "uncalibrated_scan_unit_assumed_mm", contract_sha256 = pins[contractPath],
        profile_sha256 = pins[profilePath], head_stl_sha256 = pins[headPath], input_manifest_sha256 = pins[Path.Combine(input,"inputs.json")],
        program_sha256 = Sha(typeof(IntegrationMarker).Assembly.Location),picogk_sha256 = Sha(typeof(Library).Assembly.Location),
        native_version = Library.strVersion(),shape_kernel_declared_revision = "7b9097842446a28bb5d49203724622e594ce7510",
        files,attachments,reference_parts = references.Select(v => new { name=v.GetProperty("name").GetString(),
            filename=v.GetProperty("filename").GetString(),sha256=v.GetProperty("sha256").GetString() }),
        outside_mask_halo_changes = new { added_triangles = addedOutsideCount,removed_triangles = removedOutsideCount },
        fin_count = 6, radial_compression = 11.8/28, profile_width_and_thickness_scaled = false,
        physical_root_attachment_verified = false, measured_interfaces_verified = false,
        core_preservation_is_at_voxel_resolution_only = true, reference_parts_unchanged = true,
        source_master_modified = false, full_functional_assembly = false, thermal_gain_transferred_from_coupon = false,
        thermal_simulation = false, structural_simulation = false, manufacturing_authorized = false };
    File.WriteAllText(Path.Combine(output,"integration.json"),JsonSerializer.Serialize(report,new JsonSerializerOptions { WriteIndented=true })+"\n");
    Library.UnregisterGlobalLibrary(); Console.WriteLine("Bionic fins integrated into a head copy; geometry qualification remains separate"); return 0;
}
catch (Exception error) { Console.Error.WriteLine(error.GetType().Name+": "+error.Message); return 1; }
class IntegrationMarker { }
