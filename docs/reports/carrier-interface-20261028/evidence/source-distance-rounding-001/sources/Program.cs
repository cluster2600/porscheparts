using System.Security.Cryptography;
using System.Text.Json;
using PicoGK;

if (args.Length != 2) throw new ArgumentException("Usage: PLAN NEW_OUTPUT_DIR");
string planPath = Path.GetFullPath(args[0]);
using JsonDocument plan = JsonDocument.Parse(File.ReadAllText(planPath));
var p = plan.RootElement;
string basePath = Path.GetDirectoryName(planPath)!;
string Resolve(string name) => Path.GetFullPath(Path.Combine(basePath, p.GetProperty(name).GetString()!));
string input = Resolve("input_file");
string hash = Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(input))).ToLowerInvariant();
if (hash != p.GetProperty("input_sha256").GetString()) throw new InvalidDataException("Input hash mismatch");
string scope = p.GetProperty("scope").GetString()!;
if (scope == "carrier_intermediate") {
    using JsonDocument domain = JsonDocument.Parse(File.ReadAllText(Resolve("domain_report")));
    using JsonDocument clearance = JsonDocument.Parse(File.ReadAllText(Resolve("clearance_report")));
    if (domain.RootElement.GetProperty("status").GetString() != "complete_strict_domain_containment_passed"
        || !domain.RootElement.GetProperty("whole_bounded_solid_containment_proved").GetBoolean()
        || clearance.RootElement.GetProperty("status").GetString() != "complete_clearance_budget_passed"
        || clearance.RootElement.GetProperty("minimum_complete_clearance_lower_mm").GetDouble() <= .125)
        throw new InvalidDataException("Independent input checks not admitted");
} else if (scope != "analytical_cube_control") throw new InvalidDataException("Unknown scope");
float h = p.GetProperty("voxel_mm").GetSingle();
float radius = p.GetProperty("dilation_mm").GetSingle();
string output = Path.GetFullPath(args[1]);
if (h != .01f || radius != .1f || Directory.Exists(output))
    throw new ArgumentException("Fixed settings and fresh output required");
using Library library = new(h);
using Mesh mesh = Mesh.mshFromStlFile(input, Mesh.EStlUnit.MM, libSet: library);
if (scope == "analytical_cube_control" && mesh.nTriangleCount() != 12)
    throw new InvalidDataException("Cube control has unexpected triangle count");
using Voxels field = new(mesh);
field.CalculateProperties(out float before, out _);
field.Offset(radius);
if (field.bIsEmpty()) throw new InvalidDataException("Unexpected empty dilation");
field.CalculateProperties(out float after, out BBox3 bounds);
using Mesh result = new(field);
Directory.CreateDirectory(output);
result.SaveToStlFile(Path.Combine(output, "dilated-local.stl"), Mesh.EStlUnit.MM);
File.WriteAllText(Path.Combine(output, "runtime.json"), JsonSerializer.Serialize(new {
    status = "dilation_candidate_generated_independent_checks_pending", scope,
    input_sha256 = hash, voxel_mm = (double)h, dilation_mm = (double)radius,
    input_triangles = mesh.nTriangleCount(), output_triangles = result.nTriangleCount(),
    before_voxel_volume_mm3 = before, after_voxel_volume_mm3 = after,
    bounds_min_local_mm = new[] {bounds.vecMin.X, bounds.vecMin.Y, bounds.vecMin.Z},
    bounds_max_local_mm = new[] {bounds.vecMax.X, bounds.vecMax.Y, bounds.vecMax.Z},
    picogk = "2.3.0", manufacturing_authorized = false
}, new JsonSerializerOptions {WriteIndented=true}));
