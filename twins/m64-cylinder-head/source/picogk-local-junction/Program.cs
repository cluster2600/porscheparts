using System.Diagnostics;
using System.Globalization;
using System.Numerics;
using System.Security.Cryptography;
using System.Text.Json;
using PicoGK;

// First native witness only. Real private inputs are deliberately not accepted
// until this identical operation passes its protection/occupancy guards.
if (args.Length != 4 || args[0] != "--witness" ||
    !float.TryParse(args[3], NumberStyles.Float, CultureInfo.InvariantCulture, out float h) ||
    (h != 0.2f && h != 0.1f))
{
    Console.Error.WriteLine("Usage: LocalJunction --witness CRITERIA_JSON NEW_DIR {0.2|0.1}");
    return 2;
}
string policyPath = Path.GetFullPath(args[1]), output = Path.GetFullPath(args[2]);
if (!File.Exists(policyPath) || Directory.Exists(output) || File.Exists(output)) return 2;
using JsonDocument policy = JsonDocument.Parse(File.ReadAllText(policyPath));
if (policy.RootElement.GetProperty("radius_scan_units").GetSingle() != 1f ||
    policy.RootElement.GetProperty("outside_ROI_occupancy_changes_allowed").GetInt32() != 0 ||
    !policy.RootElement.GetProperty("stop_before_private_geometry_if_witness_fails").GetBoolean()) return 2;
Directory.CreateDirectory(output);
var watch = Stopwatch.StartNew();
string Sha(string path)
{
    using var stream = File.OpenRead(path);
    return Convert.ToHexString(SHA256.HashData(stream)).ToLowerInvariant();
}
string policySha = Sha(policyPath);
void Stage(string stage) => Console.WriteLine(JsonSerializer.Serialize(new { stage, seconds = watch.Elapsed.TotalSeconds }));
try
{
    using Library lib = new(h);
    // Closed step-cylinder: small branch -10<=Y<=2, R5; trunk 0<=Y<=10, R10.
    // ROI excludes the outer cap circle and both axial end planes. Those are
    // explicit synthetic protected interfaces, not inferred Porsche dimensions.
    var small = new CylinderSdf(-10, 2, 5);
    var large = new CylinderSdf(0, 10, 10);
    using Voxels branch = new(lib, small);
    using Voxels trunk = new(lib, large);
    using Voxels original = branch.voxBoolAdd(trunk);
    var roiShape = new BoxSdf(new Vector3(-8, -3, -8), new Vector3(8, 3, 8));
    using Voxels roi = new(lib, roiShape);
    Stage("closing_then_masked_add_only");
    using Voxels closed = original.voxFillet(1f);
    using Voxels rawAdded = closed.voxBoolSubtract(original);
    using Voxels added = rawAdded.voxBoolIntersect(roi);
    using Voxels candidate = original.voxBoolAdd(added);
    var memory = new Dictionary<string, long> {
        ["original"] = original.nMemUsage(), ["closed"] = closed.nMemUsage(),
        ["raw_added"] = rawAdded.nMemUsage(), ["allowed_added"] = added.nMemUsage(),
        ["candidate"] = candidate.nMemUsage(), ["ROI"] = roi.nMemUsage() };
    Stage("export_native_surface_copies");
    object Export(Voxels field, string name)
    {
        using Mesh mesh = new(field);
        string path = Path.Combine(output, name + ".stl");
        mesh.SaveToStlFile(path, Mesh.EStlUnit.MM);
        // Signed triangle integration, not native remesh-and-revoxelize volume.
        double sum = 0, correction = 0;
        for (int i = 0; i < mesh.nTriangleCount(); i++)
        {
            mesh.GetTriangle(i, out Vector3 a, out Vector3 b, out Vector3 c);
            double term = ((double)a.X * ((double)b.Y*c.Z-(double)b.Z*c.Y) +
                           (double)a.Y * ((double)b.Z*c.X-(double)b.X*c.Z) +
                           (double)a.Z * ((double)b.X*c.Y-(double)b.Y*c.X))/6;
            double corrected = term-correction, next = sum+corrected;
            correction = (next-sum)-corrected; sum=next;
        }
        return new { filename=Path.GetFileName(path), sha256=Sha(path),
                     triangles=mesh.nTriangleCount(), signed_triangle_volume=sum,
                     interpretation_requires_independent_mesh_topology_audit=true };
    }
    var exports = new Dictionary<string, object> {
        ["before"] = Export(original,"before"), ["after"] = Export(candidate,"after"),
        ["added"] = Export(added,"added") };
    Stage("exhaustive_aligned_grid_sign_comparison");
    // Cache one native slice per field; integer grid is the kernel's own grid.
    // GetVoxelSlice has reversed Y order. Values outside the active bbox are
    // exterior, hence positive; no false zero is supplied for missing values.
    var before = new SliceReader(original); var after = new SliceReader(candidate);
    int minX=Math.Min(before.X,after.X), maxX=Math.Max(before.X+before.Nx,after.X+after.Nx);
    int minY=Math.Min(before.Y,after.Y), maxY=Math.Max(before.Y+before.Ny,after.Y+after.Ny);
    int minZ=Math.Min(before.Z,after.Z), maxZ=Math.Max(before.Z+before.Nz,after.Z+after.Nz);
    long tested=0; long[] changes=new long[2], outside=new long[2], protectedChanges=new long[2], losses=new long[2], addedAtBoundary=new long[2];
    var failures = new List<object>();
    for (int z=minZ; z<maxZ; z++)
    {
        if (watch.Elapsed.TotalSeconds>250) throw new TimeoutException("Occupancy audit time guard reached");
        before.Load(z); after.Load(z);
        for(int y=minY;y<maxY;y++) for(int x=minX;x<maxX;x++)
        {
            float b=before.Value(x,y), a=after.Value(x,y);
            if(float.IsNaN(a)||float.IsNaN(b)) throw new InvalidDataException("NaN native signed slice");
            var p=new Vector3(x*h,y*h,z*h); tested++;
            bool inROI=roiShape.fSignedDistance(p)<=0;
            bool onBoundary=MathF.Abs(roiShape.fSignedDistance(p))<=h;
            // Protected entire original end planes and original outer circle
            // neighborhood, with a half-voxel sampling slab declared explicitly.
            bool protectedPoint=MathF.Abs(p.Y+10)<=h/2 || MathF.Abs(p.Y-10)<=h/2 ||
                (MathF.Abs(p.Y)<=h/2 && MathF.Abs(MathF.Sqrt(p.X*p.X+p.Z*p.Z)-10)<=h);
            for(int k=0;k<2;k++)
            {
                bool was=k==0 ? b<0 : b<=0, now=k==0 ? a<0 : a<=0;
                if(was==now)continue;
                changes[k]++; if(!inROI)outside[k]++;
                if(protectedPoint)protectedChanges[k]++;
                if(was&&!now)losses[k]++;
                if(!was&&now&&onBoundary)addedAtBoundary[k]++;
                if(failures.Count<24 && (!inROI||protectedPoint||was))
                    failures.Add(new { convention=k, position_private=new[]{p.X,p.Y,p.Z},
                                       before_native_sdf=float.IsFinite(b)?(float?)b:null,
                                       after_native_sdf=float.IsFinite(a)?(float?)a:null,
                                       before_outside_field_bbox=!float.IsFinite(b),after_outside_field_bbox=!float.IsFinite(a),
                                       in_ROI=inROI,protected_point=protectedPoint });
            }
        }
    }
    bool pass=outside.All(n=>n==0)&&protectedChanges.All(n=>n==0)&&losses.All(n=>n==0)&&
              addedAtBoundary.All(n=>n==0)&&changes.All(n=>n>0);
    if(Sha(policyPath)!=policySha)throw new InvalidDataException("Preregistered policy changed during run");
    var report=new {
        schema="m64-picogk-local-junction-witness/v1", status=pass?"occupancy_guards_passed_mesh_audit_pending":"rejected_occupancy_protection_guard",
        policy_sha256=policySha, assembly_sha256=Sha(typeof(BoxSdf).Assembly.Location),
        native_sha256=File.Exists("/app/picogk.26.2.so")?Sha("/app/picogk.26.2.so"):null,
        radius_scan_units=1,voxel_scan_units=h, operation="union_then_closing_+1_-1_masked_addition_only",
        sign_conventions=new[]{"strict_negative_inside","zero_inside"}, tested_native_lattice_nodes=tested,
        changed_nodes=changes,outside_ROI_changed_nodes=outside,protected_changed_nodes=protectedChanges,
        lost_original_gas_nodes=losses,added_nodes_touching_ROI_boundary=addedAtBoundary,
        failure_examples_private=failures, raw_native_SDF_units="voxel_units_sign_only", exports,
        field_native_memory_bytes=memory,elapsed_seconds=watch.Elapsed.TotalSeconds,
        peak_working_set_bytes=Process.GetCurrentProcess().PeakWorkingSet64,
        master_modified=false,private_head_processed=false,exact_BRep_created=false,
        native_grid_nodes_not_a_continuous_surface_bound=true,CFD_qualified=false,manufacturing_authorized=false };
    File.WriteAllText(Path.Combine(output,"run-report.json"),JsonSerializer.Serialize(report,new JsonSerializerOptions { WriteIndented=true }));
    Console.WriteLine(JsonSerializer.Serialize(new{report.status,tested,outside,protectedChanges,losses,addedAtBoundary,report.elapsed_seconds,report.peak_working_set_bytes}));
    return pass?0:3;
}
catch(Exception error)
{
    File.WriteAllText(Path.Combine(output,"FAILED.json"),JsonSerializer.Serialize(new {status="failed",error=error.Message,elapsed_seconds=watch.Elapsed.TotalSeconds,manufacturing_authorized=false}));
    Console.Error.WriteLine(error.ToString());return 1;
}

sealed class SliceReader
{
    readonly Voxels field; ImageGrayScale image; bool active;
    public readonly int X,Y,Z,Nx,Ny,Nz;
    public SliceReader(Voxels source) { field=source;source.GetVoxelDimensions(out X,out Y,out Z,out Nx,out Ny,out Nz);image=source.imgAllocateSlice(out _); }
    public void Load(int z) { active=z>=Z&&z<Z+Nz; if(active)field.GetVoxelSlice(z-Z,ref image,Voxels.ESliceMode.SignedDistance); }
    public float Value(int x,int y) => active&&x>=X&&x<X+Nx&&y>=Y&&y<Y+Ny ? image.fValue(x-X,Y+Ny-1-y):float.PositiveInfinity;
}
sealed class BoxSdf(Vector3 low,Vector3 high) : IBoundedImplicit
{
    public BBox3 oBounds {get;}=new(low,high);
    public float fSignedDistance(in Vector3 point) { Vector3 q=Vector3.Abs(point-(low+high)*0.5f)-(high-low)*0.5f;return Vector3.Max(q,Vector3.Zero).Length()+MathF.Min(MathF.Max(q.X,MathF.Max(q.Y,q.Z)),0); }
}
sealed class CylinderSdf(float low,float high,float radius) : IBoundedImplicit
{
    public BBox3 oBounds {get;}=new(new Vector3(-radius,low,-radius),new Vector3(radius,high,radius));
    public float fSignedDistance(in Vector3 point) { Vector2 q=new(MathF.Sqrt(point.X*point.X+point.Z*point.Z)-radius,MathF.Abs(point.Y-(low+high)*0.5f)-(high-low)*0.5f);return Vector2.Max(q,Vector2.Zero).Length()+MathF.Min(MathF.Max(q.X,q.Y),0); }
}
