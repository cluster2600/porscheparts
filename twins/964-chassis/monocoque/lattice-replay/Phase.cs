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
if (Directory.Exists(args[1]) || File.Exists(args[1])) throw new IOException("Output already exists");
using var document = JsonDocument.Parse(File.ReadAllText(args[0]));
var input = document.RootElement;
Vector3 Vec(JsonElement e) { float[] v = e.EnumerateArray().Select(x => x.GetSingle()).ToArray(); return new(v[0],v[1],v[2]); }
Vector3 low = Vec(input.GetProperty("study_min_mm")), high = Vec(input.GetProperty("study_max_mm"));
Directory.CreateDirectory(args[1]);
foreach (float pitch in new[]{0.5f, 0.25f})
{
    string label = pitch == 0.5f ? "phase-050" : "phase-025";
    string output = Path.Combine(args[1],label);
    Directory.CreateDirectory(output);
    // Same global design; an explicit subvoxel phase avoids grid-aligned clipping planes.
    Vector3 origin = (low+high)/2 + pitch*new Vector3(1f/3,2f/5,1f/7);
    using Library lib = new(pitch);
    Library.RegisterGlobalLibrary(lib);
    try
    {
        using Voxels envelope = new BaseBox(new BBox3(low-origin,high-origin)).voxConstruct();
        Lattice lattice = new(lib);
        try
        {
            foreach (var row in input.GetProperty("cells").EnumerateArray())
            {
                Vector3 p = Vec(row.GetProperty("min_mm"))-origin;
                Vector3 x = new(12,0,0), y = new(0,12,0), z = new(0,0,12);
                var cell = new CuboidCell(p,p+x,p+x+y,p+y,p+z,p+x+z,p+x+y+z,p+y+z);
                new BodyCentreLattice().AddCell(ref lattice,cell,new ConstantBeamThickness(row.GetProperty("diameter_mm").GetSingle()),2);
            }
            using Voxels solid = new(lattice);
            solid.BoolIntersect(envelope);
            solid.CalculateProperties(out float volume,out BBox3 box);
            using Mesh mesh = new(solid);
            mesh.SaveToStlFile(Path.Combine(output,"raw.stl"),Mesh.EStlUnit.MM);
            solid.oMetaData().SetValue("study.local_to_F0_translation_mm",origin);
            using (OpenVdbFile file = new(lib))
            { file.nAdd(solid,"graded_probe"); file.SaveToFile(Path.Combine(output,"raw.vdb")); }
            using OpenVdbFile fileIn = new(lib,Path.Combine(output,"raw.vdb"));
            using Voxels restored = fileIn.voxGet("graded_probe");
            if (!solid.bIsEqual(restored) || fileIn.fPicoGKVoxelSizeMM()!=pitch ||
                !restored.oMetaData().bGetValueAt("study.local_to_F0_translation_mm",out Vector3 saved) || saved!=origin)
                throw new InvalidDataException("VDB or frame changed");
            foreach (var row in input.GetProperty("cells").EnumerateArray())
                if (!restored.bIsInside(Vec(row.GetProperty("min_mm"))-origin+new Vector3(6)))
                    throw new InvalidDataException("Missing cell centre");
            var report = new {case_id=label,input_report_sha256=inputHash,voxel_mm=pitch,
                local_to_F0_translation_mm=new[]{origin.X,origin.Y,origin.Z},
                phase_fraction=new[]{1f/3,2f/5,1f/7},volume_mm3=volume,triangles=mesh.nTriangleCount(),
                bounds_min_mm=new[]{box.vecMin.X,box.vecMin.Y,box.vecMin.Z},bounds_max_mm=new[]{box.vecMax.X,box.vecMax.Y,box.vecMax.Z},
                cell_centres_inside=true,vdb_roundtrip_equal=true,original_design_parameters_changed=false,
                mesh_repaired=false,structural_analysis_executed=false,manufacturing_authorized=false};
            File.WriteAllText(Path.Combine(output,"native.json"),JsonSerializer.Serialize(report,new JsonSerializerOptions {WriteIndented=true})+"\n");
            Console.WriteLine($"{label}: {mesh.nTriangleCount()} raw triangles; VDB verified");
        }
        finally { lattice.Dispose(); }
    }
    finally { Library.UnregisterGlobalLibrary(); }
}
