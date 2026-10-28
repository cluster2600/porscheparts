using System.Numerics;
using System.Security.Cryptography;
using System.Text.Json;
using PicoGK;
using Leap71.ShapeKernel;
using Leap71.LatticeLibrary;

if (args.Length != 2) throw new ArgumentException("PINNED_REPORT NEW_OUTPUT_DIRECTORY");
string inputHash = Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(args[0]))).ToLowerInvariant();
if (inputHash != "d79861b0d17441208aafc2ef8fe5ec2b63aac1e645fbbdd1b890434ccfbe99e9")
    throw new InvalidDataException("Only the archived nine-cell experiment is admitted");
if (File.Exists(args[1]) || Directory.Exists(args[1])) throw new IOException("Output already exists");
using var document = JsonDocument.Parse(File.ReadAllText(args[0]));
var input = document.RootElement;
Vector3 Vec(JsonElement e) { float[] v = e.EnumerateArray().Select(x => x.GetSingle()).ToArray(); return new(v[0],v[1],v[2]); }
Vector3 low = Vec(input.GetProperty("study_min_mm")), high = Vec(input.GetProperty("study_max_mm"));
var cells = input.GetProperty("cells").EnumerateArray().ToArray();
Directory.CreateDirectory(args[1]);
foreach (float pitch in new[]{0.5f, 0.25f})
foreach (bool local in new[]{false, true})
{
    string label = (local ? "local" : "global") + (pitch == 0.5f ? "-050" : "-025");
    string output = Path.Combine(args[1], label);
    Directory.CreateDirectory(output);
    Vector3 origin = local ? (low+high)/2 : Vector3.Zero;
    using Library lib = new(pitch);
    Library.RegisterGlobalLibrary(lib);
    try
    {
        using Voxels envelope = new BaseBox(new BBox3(low-origin, high-origin)).voxConstruct();
        Lattice lattice = new(lib);
        try
        {
            foreach (var row in cells)
            {
                Vector3 p = Vec(row.GetProperty("min_mm"))-origin;
                Vector3 x = new(12,0,0), y = new(0,12,0), z = new(0,0,12);
                var cell = new CuboidCell(p,p+x,p+x+y,p+y,p+z,p+x+z,p+x+y+z,p+y+z);
                float diameter = row.GetProperty("diameter_mm").GetSingle();
                new BodyCentreLattice().AddCell(ref lattice, cell, new ConstantBeamThickness(diameter), 2);
            }
            using Voxels solid = new(lattice);
            solid.BoolIntersect(envelope);
            solid.CalculateProperties(out float volume, out BBox3 box);
            if (!float.IsFinite(volume) || volume <= 0) throw new InvalidDataException("Invalid volume");
            using Mesh mesh = new(solid);
            mesh.SaveToStlFile(Path.Combine(output,"raw.stl"), Mesh.EStlUnit.MM);
            solid.oMetaData().SetValue("study.local_to_F0_translation_mm", origin);
            solid.oMetaData().SetValue("study.frame", local ? "local_X_forward_Y_left_Z_up" : "F0_GLOBAL_X_forward_Y_left_Z_up");
            using (OpenVdbFile file = new(lib))
            { file.nAdd(solid,"graded_probe"); file.SaveToFile(Path.Combine(output,"raw.vdb")); }
            using OpenVdbFile read = new(lib,Path.Combine(output,"raw.vdb"));
            using Voxels after = read.voxGet("graded_probe");
            if (!solid.bIsEqual(after) || read.fPicoGKVoxelSizeMM() != pitch ||
                !after.oMetaData().bGetValueAt("study.local_to_F0_translation_mm", out Vector3 storedOrigin) || storedOrigin != origin)
                throw new InvalidDataException("VDB field or transformation changed");
            foreach (var row in cells)
                if (!after.bIsInside(Vec(row.GetProperty("min_mm"))-origin+new Vector3(6)))
                    throw new InvalidDataException("A prescribed BCC cell centre is outside");
            var result = new { case_id = label, input_report_sha256 = inputHash, voxel_mm = pitch,
                local_to_F0_translation_mm = new[]{origin.X,origin.Y,origin.Z},
                volume_mm3 = volume, triangles = mesh.nTriangleCount(),
                bounds_min_mm = new[]{box.vecMin.X,box.vecMin.Y,box.vecMin.Z},
                bounds_max_mm = new[]{box.vecMax.X,box.vecMax.Y,box.vecMax.Z},
                cell_count = cells.Length, cell_centres_inside = true, vdb_roundtrip_equal = true,
                original_design_parameters_changed = false, mesh_repaired = false,
                structural_analysis_executed = false, manufacturing_authorized = false };
            File.WriteAllText(Path.Combine(output,"native.json"),JsonSerializer.Serialize(result,new JsonSerializerOptions {WriteIndented=true})+"\n");
            Console.WriteLine($"{label}: {mesh.nTriangleCount()} triangles; {volume} mm3; VDB verified");
        }
        finally { lattice.Dispose(); }
    }
    finally { Library.UnregisterGlobalLibrary(); }
}
