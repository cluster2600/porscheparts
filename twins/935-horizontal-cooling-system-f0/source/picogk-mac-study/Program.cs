using System.Numerics;
using System.Security.Cryptography;
using System.Text.Json;
using PicoGK;
using Leap71.ShapeKernel;
using Leap71.LatticeLibrary;
using Leap71.Simulation;

if (!((args.Length == 2 && args[0] == "witness") ||
      (args.Length == 3 && (args[0] == "roots" || args[0] == "simulation" || args[0] == "thickness" || args[0] == "fea-fields"))))
    throw new ArgumentException("Usage: witness NEW_PRIVATE_OUTPUT | roots|simulation|thickness|fea-fields CASE NEW_PRIVATE_OUTPUT");
string output = Path.GetFullPath(args[^1]);
if (Directory.Exists(output) || File.Exists(output)) throw new IOException("New private output required");
bool allowed = false;
for (DirectoryInfo p = new(output); p != null; p = p.Parent)
{
    if (p.LinkTarget != null) throw new IOException("No output symlink ancestry");
    if (Directory.Exists(Path.Combine(p.FullName,".git")) || File.Exists(Path.Combine(p.FullName,".git")))
    { allowed = Path.GetRelativePath(p.FullName,output).StartsWith("work"+Path.DirectorySeparatorChar); break; }
}
if (!allowed) throw new IOException("Private output must stay in ignored work/");
Directory.CreateDirectory(output);
using JsonDocument caseDocument = args.Length == 3 ? JsonDocument.Parse(File.ReadAllText(args[1])) : null;
JsonElement config = caseDocument == null ? default : caseDocument.RootElement;
float voxel = args[0] == "simulation" ? 2 : .6f;
using Library lib = new(voxel); Library.RegisterGlobalLibrary(lib);
using LogFile log = new(Path.Combine(output,"pico.log"),false); Library.RegisterGlobalLog(log);
try
{
    if (args[0] == "witness") Witness();
    else
    {
        if (config.GetProperty("purpose").GetString() != "hypothesis_screen" ||
            config.GetProperty("scale_verified").GetBoolean() || config.GetProperty("scale_mm_per_source_unit").GetSingle()!=1)
            throw new InvalidDataException("Explicit uncalibrated 1 mm/source hypothesis required");
        string source = config.GetProperty("rotor_stl_path").GetString();
        string expected = config.GetProperty("rotor_stl_sha256").GetString();
        if (Hash(source) != expected) throw new InvalidDataException("Rotor hash mismatch");
        using Mesh input = Mesh.mshFromStlFile(source,Mesh.EStlUnit.MM,libSet:lib);
        using Voxels rotor = new(input);
        if (rotor.bIsEmpty()) throw new InvalidDataException("Empty rotor");
        if (args[0] == "roots") Roots(rotor,expected);
        else if (args[0] == "thickness") Thickness(rotor,expected);
        else if (args[0] == "fea-fields") FeaFields(rotor,expected);
        else Simulation(rotor,expected);
        if (Hash(source) != expected) throw new InvalidDataException("Input changed during native study");
        File.Copy(args[1],Path.Combine(output,"case.json"));
    }
}
finally { Library.UnregisterGlobalLog(); Library.UnregisterGlobalLibrary(); }

void FeaFields(Voxels rotor,string expected)
{
    string assessment=config.GetProperty("assessment_path").GetString();
    if(Hash(assessment)!=config.GetProperty("assessment_sha256").GetString()) throw new InvalidDataException("Assessment hash mismatch");
    using JsonDocument audit=JsonDocument.Parse(File.ReadAllText(assessment));JsonElement a=audit.RootElement;
    if(a.GetProperty("geometry_sha256").GetString()!=expected || a.GetProperty("scale_verified").GetBoolean() || !a.GetProperty("reaction_balance_pass").GetBoolean() ||
       a.GetProperty("nodes").GetInt32()!=config.GetProperty("displacement_samples").GetInt32() ||
       a.GetProperty("elements").GetInt32()!=config.GetProperty("stress_samples").GetInt32() ||
       a.GetProperty("sparse_csv_sha256").GetProperty("node-displacement.csv").GetString()!=config.GetProperty("displacement_csv_sha256").GetString() ||
       a.GetProperty("sparse_csv_sha256").GetProperty("element-peak-stress.csv").GetString()!=config.GetProperty("stress_csv_sha256").GetString())
        throw new InvalidDataException("Result fields must reference the audited rotor and CSVs");
    using ScalarField stress=new(lib);using VectorField displacement=new(lib);
    int scalarCount=0,vectorCount=0;Vector3 probe=new();float probeValue=0;
    foreach(float[] row in ReadCsv("stress",4))
    {
        if(row[3]<0) throw new InvalidDataException("Negative von Mises stress");
        probe=new Vector3(row[0],row[1],row[2]);probeValue=row[3];stress.SetValue(probe,probeValue);scalarCount++;
    }
    foreach(float[] row in ReadCsv("displacement",6))
    {displacement.SetValue(new Vector3(row[0],row[1],row[2]),new Vector3(row[3],row[4],row[5]));vectorCount++;}
    stress.oMetaData().SetValue("935.unit","MPa");displacement.oMetaData().SetValue("935.unit","conditional_mm");
    stress.oMetaData().SetValue("935.method","maximum of 8 C3D8 integration points at each element centre; sparse, no interpolation");
    using OpenVdbFile file=new(lib);file.nAdd(rotor,"Geometry.Rotor");file.nAdd(stress,"FEA.ElementPeakVonMises_MPa");file.nAdd(displacement,"FEA.NodalDisplacement_mm");
    string path=Path.Combine(output,"935-fea-results.vdb");file.SaveToFile(path);
    using OpenVdbFile restored=new(lib,path);using ScalarField checkedStress=restored.oGetScalarField("FEA.ElementPeakVonMises_MPa");
    if(restored.nFieldCount()!=3||!checkedStress.bGetValue(probe,out float value)||value!=probeValue)
        throw new InvalidDataException("Sparse stress roundtrip failed");
    Save("receipt.json",new {classification="sparse_conditional_C3D8_results_not_continuous_stress_solution",input_sha256=expected,
        field_voxel_mm=voxel,scalar_samples=scalarCount,vector_samples=vectorCount,vdb_sha256=Hash(path),roundtrip_passed=true,
        source_stress_csv_sha256=config.GetProperty("stress_csv_sha256").GetString(),
        source_displacement_csv_sha256=config.GetProperty("displacement_csv_sha256").GetString(),
        assessment_sha256=Hash(assessment),material_id=a.GetProperty("material_id").GetString(),rotor_rpm=a.GetProperty("rotor_rpm").GetSingle(),
        scale_verified=false,mesh_convergence_established=false,manufacturing_authorized=false,physical_validation=false});
}

IEnumerable<float[]> ReadCsv(string key,int columns)
{
    string path=config.GetProperty(key+"_csv_path").GetString(),expected=config.GetProperty(key+"_csv_sha256").GetString();
    int required=config.GetProperty(key+"_samples").GetInt32(),count=0;
    if(required<=0||required>1000000||Hash(path)!=expected) throw new InvalidDataException("Bounded pinned result CSV required");
    foreach(string line in File.ReadLines(path))
    {
        float[] row=line.Split(',').Select(x=>float.Parse(x,System.Globalization.CultureInfo.InvariantCulture)).ToArray();
        if(row.Length!=columns||row.Any(x=>!float.IsFinite(x))||++count>required) throw new InvalidDataException("Malformed or unexpected result row");
        yield return row;
    }
    if(count!=required||Hash(path)!=expected) throw new InvalidDataException("Incomplete or changed result CSV");
}
string Hash(string p) => Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(p))).ToLowerInvariant();
void Save(string file, object value) => File.WriteAllText(Path.Combine(output,file),JsonSerializer.Serialize(value,new JsonSerializerOptions{WriteIndented=true})+"\n");
void Witness()
{
    using Voxels pipe = new BasePipe(new LocalFrame(),40,20,30).voxConstruct();
    pipe.CalculateProperties(out float volume,out _);
    double analytic = Math.PI*(30*30-20*20)*40;
    if (Math.Abs(volume/analytic-1) > .03) throw new InvalidDataException("ShapeKernel pipe witness volume mismatch");
    Vector3 inner = pipe.vecRayCastToSurface(new Vector3(0,0,20),Vector3.UnitX);
    Vector3 outer = pipe.vecRayCastToSurface(new Vector3(40,0,20),-Vector3.UnitX);
    float thickness = (outer-inner).Length();
    if (Math.Abs(thickness-10) > 1.2) throw new InvalidDataException("Ray thickness witness mismatch");
    using Voxels fluid = new BaseCylinder(new LocalFrame(),40,20).voxConstruct();
    using ScalarField density = new(fluid,1.2f); using ScalarField viscosity = new(fluid,1.5e-5f);
    using VectorField velocity = new(fluid,new Vector3(0,0,-1));
    using OpenVdbFile vdb = new(lib);
    vdb.nAdd(fluid,"Simulation.Domain_fluid"); vdb.nAdd(pipe,"Simulation.Domain_solid");
    vdb.nAdd(density,"Simulation.Field_density"); vdb.nAdd(viscosity,"Simulation.Field_viscosity"); vdb.nAdd(velocity,"Simulation.Field_velocity");
    string path = Path.Combine(output,"witness.vdb"); vdb.SaveToFile(path);
    _ = new SimpleFluidSimulationInput(path);
    using OpenVdbFile read = new(lib,path); using ScalarField restored = read.oGetScalarField("Simulation.Field_density");
    if (!restored.bGetValue(new Vector3(0,0,20),out float rho) || Math.Abs(rho-1.2f)>1e-6 || restored.bGetValue(new Vector3(60,0,20),out _))
        throw new InvalidDataException("Named scalar field roundtrip failed");
    var cells = new RegularCellArray(pipe,10,10,10,0); var type = new BodyCentreLattice();
    var beams = new ConstantBeamThickness(2); beams.SetBoundingVoxels(pipe);
    Lattice lattice = new(lib);
    foreach (var cell in cells.aGetUnitCells()) { beams.UpdateCell(cell); type.AddCell(ref lattice,cell,beams,2); }
    using (lattice) using (Voxels network = new(lattice))
    {
        network.BoolIntersect(pipe); network.CalculateProperties(out float latticeVolume,out _);
        if (latticeVolume<=0 || latticeVolume>=volume) throw new InvalidDataException("Lattice witness invalid");
        using Mesh mesh = network.mshAsMesh(); mesh.SaveToStlFile(Path.Combine(output,"lattice-witness.stl"));
        File.WriteAllText(Path.Combine(output,"receipt.json"),JsonSerializer.Serialize(new {
            classification="library_witness_not_935_geometry",shape_kernel_volume_error=Math.Abs(volume/analytic-1),
            ray_thickness_mm=thickness,lattice_volume_mm3=latticeVolume,vdb_fields=read.nFieldCount(),
            official_simulation_reader_passed=true,scalar_roundtrip_passed=true,viewer_used=false,
            manufacturing_authorized=false,physical_validation=false
        },new JsonSerializerOptions{WriteIndented=true})+"\n");
    }
}

object Export(Voxels vox, string name)
{
    using Mesh raw = vox.mshAsMesh(); using Mesh clean = new(lib); int removed=0;
    for (int i=0;i<raw.nTriangleCount();i++)
    {
        raw.GetTriangle(i,out Vector3 a,out Vector3 b,out Vector3 c);
        Vector3 cross=Vector3.Cross(b-a,c-a);
        if (!float.IsFinite(cross.LengthSquared())) throw new InvalidDataException("Nonfinite mesh");
        if (cross.LengthSquared()==0) {removed++;continue;}
        clean.nAddTriangle(a,b,c);
    }
    if (removed>100 || clean.nTriangleCount()==0) throw new InvalidDataException("Unexpected degenerate mesh");
    clean.SaveToStlFile(Path.Combine(output,name)); vox.CalculateProperties(out float volume,out _);
    return new {file=name,sha256=Hash(Path.Combine(output,name)),conditional_volume_mm3=volume,
        triangles=clean.nTriangleCount(),exact_zero_area_triangles_removed=removed};
}

void Roots(Voxels rotor,string expected)
{
    string sections=config.GetProperty("sections_path").GetString();
    if (Hash(sections)!=config.GetProperty("sections_sha256").GetString()) throw new InvalidDataException("Section hash mismatch");
    using JsonDocument data=JsonDocument.Parse(File.ReadAllText(sections));
    float minStation=float.PositiveInfinity; var bladeIds=new HashSet<string>();
    foreach (JsonElement blade in data.RootElement.GetProperty("blades").EnumerateArray())
    {
        if(!bladeIds.Add(blade.GetProperty("blade_id").GetString())) throw new InvalidDataException("Duplicate blade identifier");
        float bladeMin=float.PositiveInfinity;
        var stations=blade.GetProperty("stations_source_units").EnumerateArray().ToArray();
        var provenance=blade.GetProperty("provenance").EnumerateArray().ToArray();
        if (stations.Length!=provenance.Length) throw new InvalidDataException("Section provenance length mismatch");
        for (int i=0;i<stations.Length;i++)
            if (provenance[i].GetProperty("classification").GetString()=="registered_acquired_reference_section")
                bladeMin=MathF.Min(bladeMin,stations[i].GetSingle());
        if(!float.IsFinite(bladeMin)) throw new InvalidDataException("Every blade must have acquired sections");
        minStation=MathF.Min(minStation,bladeMin);
    }
    if (bladeIds.Count!=9 || !float.IsFinite(minStation) || minStation<98) throw new InvalidDataException("Nine observed blades and guarded measured stations required");
    // shortcut: 1 mm per source unit remains conditional until two independent dimensions are measured.
    using Voxels roi=new BasePipe(new LocalFrame(new Vector3(0,0,-30)),70,25,95).voxConstruct();
    using Voxels bore=new BaseCylinder(new LocalFrame(new Vector3(0,0,-40)),90,24).voxConstruct();
    var variants=new List<object>();
    foreach (float radius in new float[]{0,.6f,1.2f})
    {
        using Voxels candidate=rotor.voxDuplicate(); using Voxels added=rotor.voxDuplicate();
        if (radius>0) added.Fillet(radius);
        added.BoolSubtract(rotor); added.BoolIntersect(roi); candidate.BoolAdd(added);
        using Voxels removed=rotor.voxBoolSubtract(candidate);
        using Voxels forbidden=added.voxBoolSubtract(roi); using Voxels boreChange=added.voxBoolIntersect(bore);
        if (!removed.bIsEmpty() || !forbidden.bIsEmpty() || !boreChange.bIsEmpty()) throw new InvalidDataException("Protected rotor occupancy changed");
        added.CalculateProperties(out float addedVolume,out _);
        variants.Add(new {closing_radius_mm=radius,added_conditional_volume_mm3=addedVolume,
            original_occupancy_preserved=true,changes_outside_guarded_roi=false,bore_material_added=false,
            mesh=Export(candidate,$"rotor-root-{radius.ToString(System.Globalization.CultureInfo.InvariantCulture)}.stl")});
    }
    Save("receipt.json",new {classification="missing_root_addition_hypotheses_not_historical_fillets",input_sha256=expected,
        sections_sha256=Hash(sections),field_voxel_mm=voxel,minimum_observed_station_source_units=minStation,
        guarded_roi=new {inner_radius_mm=25,outer_radius_mm=95,z_min_mm=-30,z_max_mm=40},variants,
        scale_verified=false,manufacturing_authorized=false,physical_validation=false});
}

void Thickness(Voxels rotor,string expected)
{
    string sections=config.GetProperty("sections_path").GetString();
    if(Hash(sections)!=config.GetProperty("sections_sha256").GetString()) throw new InvalidDataException("Section hash mismatch");
    using JsonDocument data=JsonDocument.Parse(File.ReadAllText(sections));
    using ScalarField sdf=new(rotor); using ScalarField thickness=new(lib);
    var rows=new List<object>(); var values=new List<float>(); int requested=0;
    foreach(JsonElement blade in data.RootElement.GetProperty("blades").EnumerateArray())
    {
        var stations=blade.GetProperty("stations_source_units").EnumerateArray().ToArray();
        var profiles=blade.GetProperty("profiles").EnumerateArray().ToArray();
        var provenance=blade.GetProperty("provenance").EnumerateArray().ToArray();
        if(stations.Length!=profiles.Length||stations.Length!=provenance.Length) throw new InvalidDataException("Profile lengths differ");
        int[] acquired=Enumerable.Range(0,stations.Length).Where(i=>provenance[i].GetProperty("classification").GetString()=="registered_acquired_reference_section").ToArray();
        if(acquired.Length<5) throw new InvalidDataException("Three guarded acquired sections required per blade");
        foreach(int i in new[]{acquired[1],acquired[acquired.Length/2],acquired[^2]})
        {
            float station=stations[i].GetSingle();
            var profile=profiles[i].EnumerateArray().ToArray();
            if(profile.Length!=128) throw new InvalidDataException("Expected registered 128-point profile");
            for(int j=0;j<profile.Length;j+=8)
            {
                requested++; var p=profile[j].EnumerateArray().Select(x=>x.GetSingle()).ToArray();
                if(p.Length!=3||p.Any(x=>!float.IsFinite(x))) throw new InvalidDataException("Finite 3D profile point required");
                Vector3 surface=rotor.vecClosestPointOnSurface(new Vector3(p[0],p[1],p[2]));
                Vector3 normal=rotor.vecSurfaceNormal(surface); float length=normal.Length();
                float? value=null; string status="unresolved_normal_or_inside_probe";
                if(float.IsFinite(length)&&length>.5f)
                {
                    normal/=length; Vector3 inside=surface-normal*(voxel*.75f);
                    if(sdf.fSignedDistance(inside)<0&&rotor.bRayCastToSurface(inside,-normal,out Vector3 exit))
                    {
                        float distance=(exit-surface).Length();
                        if(float.IsFinite(distance)&&distance>voxel*.75f)
                        {value=distance;status="first_inward_normal_exit";values.Add(distance);thickness.SetValue(surface,distance);}
                        else status="unresolved_same_surface_hit";
                    }
                }
                rows.Add(new {blade_id=blade.GetProperty("blade_id").GetString(),station_source_units=station,
                    profile_vertex=j,surface_mm=new[]{surface.X,surface.Y,surface.Z},status,conditional_normal_ray_thickness_mm=value});
            }
        }
    }
    if(requested!=432||values.Count==0) throw new InvalidDataException("Missing acquired station probes");
    thickness.oMetaData().SetValue("935.unit","conditional_mm");thickness.oMetaData().SetValue("935.method","first inward normal exit at sampled acquired profiles");
    using OpenVdbFile file=new(lib);file.nAdd(rotor,"Geometry.Rotor");file.nAdd(thickness,"Inspection.NormalRayThickness_mm");
    string path=Path.Combine(output,"935-thickness.vdb");file.SaveToFile(path);
    values.Sort(); Save("receipt.json",new {classification="sampled_normal_ray_lengths_not_global_minimum_wall",input_sha256=expected,
        sections_sha256=Hash(sections),field_voxel_mm=voxel,requested_probes=requested,resolved_probes=values.Count,
        unresolved_probes=requested-values.Count,sampled_minimum_mm=values[0],sampled_median_mm=values[values.Count/2],
        sampled_maximum_mm=values[^1],vdb_sha256=Hash(path),rows,scale_verified=false,
        global_minimum_wall_established=false,manufacturing_authorized=false,physical_validation=false});
}

void Simulation(Voxels rotor,string expected)
{
    float rho=config.GetProperty("air_density_kg_m3").GetSingle(),nu=config.GetProperty("kinematic_viscosity_m2_s").GetSingle();
    float rpm=config.GetProperty("rotor_rpm").GetSingle(),flow=config.GetProperty("flow_m3_s").GetSingle();
    if (!float.IsFinite(rho)||!float.IsFinite(nu)||!float.IsFinite(rpm)||!float.IsFinite(flow)||rho<=0||nu<=0||rpm==0||flow<=0)
        throw new InvalidDataException("Finite positive operating hypotheses required");
    using Voxels fluid=new BaseCylinder(new LocalFrame(new Vector3(0,0,-120)),240,180).voxConstruct();
    fluid.BoolSubtract(rotor);
    float velocity=flow/(MathF.PI*.18f*.18f);
    using ScalarField density=new(fluid,rho); using ScalarField viscosity=new(fluid,nu);
    using VectorField speed=new(fluid,new Vector3(0,0,-velocity));
    rotor.oMetaData().SetValue("935.source_sha256",expected);
    rotor.oMetaData().SetValue("935.length_unit","conditional_mm");
    density.oMetaData().SetValue("935.unit","kg_per_m3"); viscosity.oMetaData().SetValue("935.unit","m2_per_s_kinematic");
    speed.oMetaData().SetValue("935.unit","m_per_s");
    using OpenVdbFile file=new(lib);
    file.nAdd(fluid,"Simulation.Domain_fluid");file.nAdd(rotor,"Simulation.Domain_solid");
    file.nAdd(density,"Simulation.Field_density");file.nAdd(viscosity,"Simulation.Field_viscosity");file.nAdd(speed,"Simulation.Field_velocity");
    string path=Path.Combine(output,"935-simulation-input.vdb");file.SaveToFile(path);
    _=new SimpleFluidSimulationInput(path);
    using OpenVdbFile restored=new(lib,path);using ScalarField checkedRho=restored.oGetScalarField("Simulation.Field_density");
    using VectorField checkedSpeed=restored.oGetVectorField("Simulation.Field_velocity");
    Vector3 probe=new(0,0,80);
    if(restored.nFieldCount()!=5||!checkedRho.bGetValue(probe,out float r)||MathF.Abs(r-rho)>1e-6f||
       !checkedSpeed.bGetValue(probe,out Vector3 v)||MathF.Abs(v.Z+velocity)>1e-5f)
        throw new InvalidDataException("Simulation field roundtrip failed");
    using Voxels overlap=fluid.voxBoolIntersect(rotor);
    if(!overlap.bIsEmpty()) throw new InvalidDataException("Fluid and solid overlap");
    Save("receipt.json",new {classification="cylindrical_test_domain_simulation_input_not_solver_result",input_sha256=expected,
        field_voxel_mm=voxel,vdb_sha256=Hash(path),named_fields=Enumerable.Range(0,restored.nFieldCount()).Select(restored.strFieldName).ToArray(),
        roundtrip_passed=true,fluid_solid_overlap=false,rpm,flow_m3_s=flow,air_density_kg_m3=rho,kinematic_viscosity_m2_s=nu,
        initial_axial_velocity_m_s=-velocity,rotating_wall_boundary_exported=false,
        scale_verified=false,CFD_solved=false,manufacturing_authorized=false,physical_validation=false});
}
