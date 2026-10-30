using System.Numerics;
using System.Security.Cryptography;
using System.Text.Json;
using PicoGK;

if (args.Length != 2) throw new ArgumentException("Usage: FROZEN_PLAN NEW_OUTPUT_DIR");
string planPath = Path.GetFullPath(args[0]);
using JsonDocument plan = JsonDocument.Parse(File.ReadAllText(planPath));
var p = plan.RootElement;
string input = Path.GetFullPath(Path.Combine(Path.GetDirectoryName(planPath)!, p.GetProperty("input_file").GetString()!));
string expectedHash = p.GetProperty("input_stl_sha256").GetString()!;
if (Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(input))).ToLowerInvariant() != expectedHash)
    throw new InvalidDataException("Frozen input hash mismatch");
string output = Path.GetFullPath(args[1]);
float h = p.GetProperty("voxel_mm").GetSingle();
float radius = p.GetProperty("opening_radius_mm").GetSingle();
float retreat = p.GetProperty("retreat_mm").GetSingle();
if (Directory.Exists(output) || h != .01f || radius != .1f || retreat != .02f)
    throw new ArgumentException("Fresh output and admitted pilot settings required");
Directory.CreateDirectory(output);
using Library library = new(h);
using Mesh source = Mesh.mshFromStlFile(input, Mesh.EStlUnit.MM, libSet: library);
using Voxels field = new(source);
field.CalculateProperties(out float before, out _);
field.DoubleOffset(-(radius + retreat), radius);
if (field.bIsEmpty()) throw new InvalidDataException("Opening removed the entire source void");
field.CalculateProperties(out float after, out BBox3 bounds);
using Mesh result = new(field);
result.SaveToStlFile(Path.Combine(output, "opened.stl"), Mesh.EStlUnit.MM);
File.WriteAllText(Path.Combine(output, "runtime.json"), JsonSerializer.Serialize(new {
    status = "void_opening_candidate_generated_checks_pending", input_stl_sha256 = expectedHash,
    voxel_mm = (double)h, opening_radius_mm = (double)radius, retreat_mm = (double)retreat,
    erosion_mm = (double)(radius + retreat), dilation_mm = (double)radius,
    input_triangles = source.nTriangleCount(), output_triangles = result.nTriangleCount(),
    before_voxel_volume_mm3 = before, after_voxel_volume_mm3 = after,
    bounds_min_mm = new[] {bounds.vecMin.X, bounds.vecMin.Y, bounds.vecMin.Z},
    bounds_max_mm = new[] {bounds.vecMax.X, bounds.vecMax.Y, bounds.vecMax.Z},
    picogk = "2.3.0", mechanical_admissibility_established = false, manufacturing_authorized = false
}, new JsonSerializerOptions {WriteIndented = true}));
