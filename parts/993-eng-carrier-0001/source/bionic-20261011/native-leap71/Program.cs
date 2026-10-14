using System.Diagnostics;
using System.Numerics;
using System.Security.Cryptography;
using System.Text.Json;
using PicoGK;
using Leap71.ShapeKernel;
using Leap71.LatticeLibrary;

if (args.Length != 3) throw new ArgumentException("Usage: Carrier ORIGINAL_V5_STL SAMPLES_JSON NEW_OUTPUT");
string source = Path.GetFullPath(args[0]), samplesPath = Path.GetFullPath(args[1]), output = Path.GetFullPath(args[2]);
string Sha(string path) { using var stream = File.OpenRead(path); return Convert.ToHexString(SHA256.HashData(stream)).ToLowerInvariant(); }
void Require(bool condition, string message) { if (!condition) throw new InvalidDataException(message); }
using var samples = JsonDocument.Parse(File.ReadAllText(samplesPath));
var data = samples.RootElement;
string geometrySha = Sha(source);
Require(geometrySha == "22e8ba507dbd91827810bda54cfee7fcfe4723f98365100e5d567cb2d0d746f0"
    && data.GetProperty("geometry_sha256").GetString() == geometrySha, "Frozen geometry / field association mismatch");
Require(data.GetProperty("voxel_mm").GetSingle() == .5f, "Expected 0.5 mm diagnostic grid");
Require(!Directory.Exists(output) && !File.Exists(output), "Refusing to overwrite output");
Directory.CreateDirectory(output);
using Library lib = new(.5f);
using LogFile log = new(Path.Combine(output, "PicoGK.log"), false);
Library.RegisterGlobalLibrary(lib);
Library.RegisterGlobalLog(log);
var timer = Stopwatch.StartNew();
try
{
    Console.WriteLine("Voxelizing frozen V5 on native Mac runtime");
    using Mesh input = Mesh.mshFromStlFile(source, Mesh.EStlUnit.MM, libSet: lib);
    Require(input.nTriangleCount() > 0, "Empty source mesh");
    using Voxels baseline = new(input);
    Voxels Box(Vector3 low, Vector3 high) => new BaseBox(new BBox3(low, high)).voxConstruct();
    using Voxels protectedArea = Box(new(-80,-42,-22), new(80,42,32));
    foreach (float x in new[]{-280f,280f})
    {
        using Voxels end = Box(new(x-25,-30,-22), new(x+25,30,32));
        protectedArea.BoolAdd(end);
    }
    foreach (Vector3 centre in new[]{new Vector3(-160,-26,-22),new Vector3(-180,-23,-22)})
    {
        using Voxels access = new BaseCylinder(new LocalFrame(centre), 54, 8).voxConstruct();
        protectedArea.BoolAdd(access);
    }
    using Voxels region = Box(new(-245,-20,-12), new(-100,20,12));
    using (Voxels right = Box(new(100,-20,-12), new(245,20,12))) region.BoolAdd(right);
    region.BoolSubtract(protectedArea);
    Console.WriteLine("Constructing bounded BCC arm-bracing trial with LatticeLibrary");
    using Lattice lattice = new(lib);
    Lattice target = lattice;
    var cells = new RegularCellArray(region,16,16,16,0).aGetUnitCells();
    var bcc = new BodyCentreLattice();
    var diameter = new ConstantBeamThickness(2);
    foreach (var cell in cells) bcc.AddCell(ref target,cell,diameter,2);
    using Voxels latticeVoxels = new(lattice);
    using Voxels clipped = latticeVoxels.voxBoolIntersect(region);
    using Voxels candidate = baseline.voxBoolAdd(clipped);
    using Voxels addition = candidate.voxBoolSubtract(baseline);
    using Voxels beforeProtected = baseline.voxBoolIntersect(protectedArea);
    using Voxels afterProtected = candidate.voxBoolIntersect(protectedArea);
    bool protectedEqual = beforeProtected.bIsEqual(afterProtected);
    Require(protectedEqual, "Protected native fields changed");
    using ScalarField vm = new(lib);
    using VectorField displacement = new(lib);
    vm.m_oMetadata.SetValue("units", "MPa");
    vm.m_oMetadata.SetValue("semantics", "Sparse V5 C3D10 element maxima at binned centroids; no tensor/interpolation; absent means unknown");
    displacement.m_oMetadata.SetValue("units", "mm");
    displacement.m_oMetadata.SetValue("semantics", "Sparse V5 nodal bins retaining maximum-magnitude sample; absent means unknown");
    vm.m_oMetadata.SetValue("geometry_sha256", geometrySha);
    displacement.m_oMetadata.SetValue("geometry_sha256", geometrySha);
    Vector3 Position(JsonElement row) => new(row[0].GetSingle(),row[1].GetSingle(),row[2].GetSingle());
    var stressRows = data.GetProperty("element_peak_rows_xyz_mm_vm_MPa");
    var uRows = data.GetProperty("displacement_rows_xyz_ux_uy_uz_mm");
    var occupiedVM = new HashSet<Vector3>(); var occupiedU = new HashSet<Vector3>();
    foreach (var row in stressRows.EnumerateArray())
    {
        Vector3 p = Position(row); float v = row[3].GetSingle();
        Require(row.GetArrayLength()==4 && float.IsFinite(p.Length()) && float.IsFinite(v) && v>=0
            && occupiedVM.Add(p) && p*2==Vector3.Round(p*2), "Invalid or duplicate stress bin");
        vm.SetValue(p,v);
    }
    foreach (var row in uRows.EnumerateArray())
    {
        Vector3 p = Position(row), u = new(row[3].GetSingle(),row[4].GetSingle(),row[5].GetSingle());
        Require(row.GetArrayLength()==6 && float.IsFinite(p.Length()) && float.IsFinite(u.Length())
            && occupiedU.Add(p) && p*2==Vector3.Round(p*2), "Invalid or duplicate displacement bin");
        displacement.SetValue(p,u);
    }
    Require(occupiedVM.Count>0 && occupiedU.Count>0,"Empty solver fields");
    var fields = new Dictionary<string,Voxels> { ["V5.reference_geometry"] = baseline,
        ["Study.protected_interfaces"] = protectedArea, ["Study.arm_domain"] = region,
        ["Study.BCC_trial"] = candidate, ["Study.added_material"] = addition };
    string vdb = Path.Combine(output,"carrier-fields.vdb");
    using (OpenVdbFile file = new(lib))
    {
        foreach (var f in fields) file.nAdd(f.Value,f.Key);
        file.nAdd(vm,"V5.element_peak_VM_MPa"); file.nAdd(displacement,"V5.displacement_mm");
        file.SaveToFile(vdb);
    }
    Console.WriteLine("Reloading seven VDB fields and checking every transferred sample");
    using (OpenVdbFile loaded = new(lib,vdb))
    {
        Require(loaded.nFieldCount()==7 && loaded.fPicoGKVoxelSizeMM()==.5f,"VDB field count or scale changed");
        foreach (var f in fields)
        {
            using Voxels restored = loaded.voxGet(f.Key);
            Require(f.Value.bIsEqual(restored),"VDB geometry changed: "+f.Key);
        }
        using ScalarField restoredVM = loaded.oGetScalarField("V5.element_peak_VM_MPa");
        using VectorField restoredU = loaded.oGetVectorField("V5.displacement_mm");
        foreach (var row in stressRows.EnumerateArray())
            Require(restoredVM.bGetValue(Position(row),out float v) && v==row[3].GetSingle(),"Stress sample changed");
        foreach (var row in uRows.EnumerateArray())
            Require(restoredU.bGetValue(Position(row),out Vector3 u)
                && u==new Vector3(row[3].GetSingle(),row[4].GetSingle(),row[5].GetSingle()),"Displacement sample changed");
        Require(!restoredVM.bGetValue(new Vector3(1000),out _) && !restoredU.bGetValue(new Vector3(1000),out _),"Empty bin became data");
    }
    var exports = new Dictionary<string,object>();
    foreach (var (name,vox) in new[]{("baseline",baseline),("candidate",candidate),("addition",addition)})
    {
        using Mesh mesh = new(vox);
        string path = Path.Combine(output,name+".stl"); mesh.SaveToStlFile(path,Mesh.EStlUnit.MM);
        vox.CalculateProperties(out float volume,out BBox3 bounds);
        Require(float.IsFinite(volume) && volume>0,"Empty/nonfinite geometry");
        exports[name] = new{volume_mm3=volume, nominal_mass_kg=volume*4.42e-6,
            triangles=mesh.nTriangleCount(), sha256=Sha(path)};
    }
    candidate.CalculateProperties(out float candidateVolume,out _);
    var report = new { status = candidateVolume*4.42e-6>1.2 ? "rejected_mass_ceiling" : "unqualified_bracing_trial",
        native_architecture=System.Runtime.InteropServices.RuntimeInformation.ProcessArchitecture.ToString(),
        voxel_mm=.5, cell_mm=16, beam_diameter_mm=2, cells=cells.Count,
        source_geometry_sha256=geometrySha, source_samples_sha256=Sha(samplesPath),
        assembly_sha256=Sha(typeof(BodyCentreLattice).Assembly.Location),
        runtime_sha256=Sha(Path.Combine(AppContext.BaseDirectory,"picogk.26.2.dylib")),
        exports, protected_native_fields_equal=protectedEqual,
        vdb=new{sha256=Sha(vdb),fields=7,geometry_fields_roundtrip_equal=5,
            exact_scalar_samples=occupiedVM.Count,exact_vector_samples=occupiedU.Count,empty_bin_probe_pass=true},
        added_material_is="Unoptimised 2 mm BCC arm bracing clipped by assumed ShapeKernel masks",
        field_geometry="Frozen V5 only; these solver values do not describe the BCC trial",
        flat_print_orientation_preserved=true, new_solver_executed=false,
        candidate_strength_validated=false, candidate_fatigue_validated=false,
        fitment_validated=false, manufacturing_authorized=false,
        seconds=timer.Elapsed.TotalSeconds, peak_working_set_bytes=Process.GetCurrentProcess().PeakWorkingSet64 };
    File.WriteAllText(Path.Combine(output,"native-results.json"),JsonSerializer.Serialize(report,new JsonSerializerOptions{WriteIndented=true}));
    Console.WriteLine(JsonSerializer.Serialize(report));
}
finally { Library.UnregisterGlobalLog(); Library.UnregisterGlobalLibrary(); }
