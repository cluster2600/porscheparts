using System.Diagnostics;
using System.Globalization;
using System.Numerics;
using System.Security.Cryptography;
using System.Text.Json;
using PicoGK;

// Nouveau témoin seulement. La marge intérieure n'est pas une preuve de protection.
if(args.Length!=4 || args[0]!="--witness" ||
   !float.TryParse(args[3],NumberStyles.Float,CultureInfo.InvariantCulture,out float h) || h!=0.2f)
{ Console.Error.WriteLine("Usage: BufferedJunction --witness CRITERIA NEW_DIR 0.2"); return 2; }
string policyPath=Path.GetFullPath(args[1]), output=Path.GetFullPath(args[2]);
if(!File.Exists(policyPath)||Directory.Exists(output)||File.Exists(output))return 2;
using JsonDocument policy=JsonDocument.Parse(File.ReadAllText(policyPath));
var p=policy.RootElement;
bool Sequence(JsonElement e,float[] expected)=>e.EnumerateArray().Select(v=>v.GetSingle()).SequenceEqual(expected);
if(p.GetProperty("voxel_world_units").GetSingle()!=h ||
   p.GetProperty("radius_world_units").GetSingle()!=1 ||
   p.GetProperty("interior_margin_voxels").GetInt32()!=3 ||
   !Sequence(p.GetProperty("authorized_ROI_low"),[-8,-3,-8]) ||
   !Sequence(p.GetProperty("authorized_ROI_high"),[8,3,8]) ||
   !p.GetProperty("synthetic_witness_only").GetBoolean() ||
   new[]{"outside_ROI_occupancy_changes_allowed","protected_occupancy_changes_allowed",
         "source_gas_occupancy_losses_allowed","addition_at_ROI_boundary_allowed"}.Any(k=>p.GetProperty(k).GetInt32()!=0))return 2;
Directory.CreateDirectory(output);
var watch=Stopwatch.StartNew();
string Sha(string path){using var f=File.OpenRead(path);return Convert.ToHexString(SHA256.HashData(f)).ToLowerInvariant();}
string policySha=Sha(policyPath);
void TimeGuard(){if(watch.Elapsed.TotalSeconds>250)throw new TimeoutException("Native audit 250 second guard reached");}
void Stage(string name)=>Console.WriteLine(JsonSerializer.Serialize(new{stage=name,seconds=watch.Elapsed.TotalSeconds}));
try
{
    using Library lib=new(h);
    using Voxels branch=new(lib,new CylinderSdf(-10,2,5));
    using Voxels trunk=new(lib,new CylinderSdf(0,10,10));
    using Voxels original=branch.voxBoolAdd(trunk);
    Vector3 low=new(-8,-3,-8),high=new(8,3,8);
    float margin=3*h;
    var authorized=new BoxSdf(low,high);
    var innerShape=new BoxSdf(low+new Vector3(margin),high-new Vector3(margin));
    using Voxels inner=new(lib,innerShape);
    Stage("closing_and_union_clipped_by_inner_mask");
    using Voxels closed=original.voxFillet(1f);
    using Voxels closedInner=closed.voxBoolIntersect(inner);
    using Voxels candidate=original.voxBoolAdd(closedInner);
    using Voxels rawAdded=closed.voxBoolSubtract(original);
    using Voxels added=rawAdded.voxBoolIntersect(inner);
    var fields=new Dictionary<string,Voxels>{["original_A"]=original,["closing_C"]=closed,
        ["ROI_inner"]=inner,["C_intersect_inner_ROI"]=closedInner,
        ["buffered_candidate"]=candidate,["diagnostic_added"]=added};
    string vdb=Path.Combine(output,"native-fields.vdb");
    Stage("serialize_six_fields_then_compare_exact_values");
    using(OpenVdbFile file=new(lib)){foreach(var f in fields)file.nAdd(f.Value,f.Key);file.SaveToFile(vdb);}
    string vdbSha=Sha(vdb);
    var roundtrip=new Dictionary<string,object>();
    using(OpenVdbFile file=new(lib,vdb))
    {
        if(file.nFieldCount()!=6 || MathF.Abs(file.fPicoGKVoxelSizeMM()-h)>1e-6f)
            throw new InvalidDataException("VDB field count or metadata voxel scale mismatch");
        foreach(var entry in fields)
        {
            using Voxels restored=file.voxGet(entry.Key);
            var a=new SliceReader(entry.Value);var b=new SliceReader(restored);
            if(!a.Dimensions.SequenceEqual(b.Dimensions))throw new InvalidDataException("VDB field lattice bounding box mismatch");
            long compared=0,differences=0;double maxDelta=0;
            for(int z=a.Z;z<a.Z+a.Nz;z++)
            {
                TimeGuard();a.Load(z);b.Load(z);
                for(int y=a.Y;y<a.Y+a.Ny;y++)for(int x=a.X;x<a.X+a.Nx;x++)
                {
                    float first=a.Value(x,y),second=b.Value(x,y);
                    if(!float.IsFinite(first)||!float.IsFinite(second))throw new InvalidDataException("Non-finite VDB comparison");
                    compared++;
                    if(BitConverter.SingleToInt32Bits(first)!=BitConverter.SingleToInt32Bits(second))differences++;
                    maxDelta=Math.Max(maxDelta,Math.Abs((double)first-second));
                }
            }
            roundtrip[entry.Key]=new{compared_native_bbox_nodes=compared,bitwise_value_differences=differences,
                max_abs_delta_world_units=maxDelta,bbox_indices_equal=true,exact_value_comparison_pass=differences==0,
                outside_active_bbox_values_compared=false};
            if(differences!=0)throw new InvalidDataException("VDB values changed on serialization");
        }
    }
    Stage("export_unmodified_native_surfaces");
    object Export(Voxels field,string name)
    {
        TimeGuard();using Mesh mesh=new(field);string path=Path.Combine(output,name+".stl");
        mesh.SaveToStlFile(path,Mesh.EStlUnit.MM);
        return new{filename=Path.GetFileName(path),sha256=Sha(path),triangles=mesh.nTriangleCount()};
    }
    var exports=new Dictionary<string,object>{["before"]=Export(original,"before"),
        ["after"]=Export(candidate,"after"),["added"]=Export(added,"added")};
    Stage("compare_occupancy_and_values_against_unchanged_authorized_ROI");
    var before=new SliceReader(original);var after=new SliceReader(candidate);
    int minX=Math.Min(before.X,after.X),maxX=Math.Max(before.X+before.Nx,after.X+after.Nx);
    int minY=Math.Min(before.Y,after.Y),maxY=Math.Max(before.Y+before.Ny,after.Y+after.Ny);
    int minZ=Math.Min(before.Z,after.Z),maxZ=Math.Max(before.Z+before.Nz,after.Z+after.Nz);
    long tested=0,finite=0,unavailable=0,outsideSdf=0,protectedSdf=0;
    long[] changed=new long[2],outside=new long[2],protection=new long[2],lost=new long[2],boundary=new long[2];
    double maxOutside=0,maxProtected=0;var samples=new List<object>();
    for(int z=minZ;z<maxZ;z++)
    {
        TimeGuard();before.Load(z);after.Load(z);
        for(int y=minY;y<maxY;y++)for(int x=minX;x<maxX;x++)
        {
            float a=after.Value(x,y),b=before.Value(x,y);
            if(float.IsNaN(a)||float.IsNaN(b))throw new InvalidDataException("NaN SDF");
            var point=new Vector3(x*h,y*h,z*h);tested++;
            bool inROI=authorized.fSignedDistance(point)<=0;
            bool onBoundary=MathF.Abs(authorized.fSignedDistance(point))<=h;
            bool isProtected=MathF.Abs(point.Y+10)<=h/2||MathF.Abs(point.Y-10)<=h/2||
                (MathF.Abs(point.Y)<=h/2&&MathF.Abs(MathF.Sqrt(point.X*point.X+point.Z*point.Z)-10)<=h);
            if(float.IsFinite(a)&&float.IsFinite(b))
            {
                finite++;double delta=Math.Abs((double)a-b);
                if(delta>0&&!inROI){outsideSdf++;maxOutside=Math.Max(maxOutside,delta);}
                if(delta>0&&isProtected){protectedSdf++;maxProtected=Math.Max(maxProtected,delta);}
                if(delta>0&&(!inROI||isProtected)&&samples.Count<24)
                    samples.Add(new{position_world_units=new[]{point.X,point.Y,point.Z},before=b,after=a,in_authorized_ROI=inROI,protected_point=isProtected});
            }
            else unavailable++;
            for(int k=0;k<2;k++)
            {
                bool was=k==0?b<0:b<=0,now=k==0?a<0:a<=0;
                if(was==now)continue;
                changed[k]++;if(!inROI)outside[k]++;if(isProtected)protection[k]++;
                if(was&&!now)lost[k]++;if(!was&&now&&onBoundary)boundary[k]++;
            }
        }
    }
    bool pass=outside.All(n=>n==0)&&protection.All(n=>n==0)&&lost.All(n=>n==0)&&
        boundary.All(n=>n==0)&&changed.All(n=>n>0);
    if(Sha(policyPath)!=policySha||Sha(vdb)!=vdbSha)throw new InvalidDataException("Policy or VDB changed during audit");
    var report=new{schema="m64-picogk-local-junction-buffered-witness/v1",
        status=pass?"occupancy_pass_raw_and_normalized_surface_audits_required":"rejected_occupancy_guard",
        policy_sha256=policySha,assembly_sha256=Sha(typeof(BoxSdf).Assembly.Location),
        native_sha256=Sha("/app/picogk.26.2.so"),radius_world_units=1,voxel_world_units=h,
        authorized_ROI_low=new[]{low.X,low.Y,low.Z},authorized_ROI_high=new[]{high.X,high.Y,high.Z},
        inner_ROI_low=new[]{low.X+margin,low.Y+margin,low.Z+margin},inner_ROI_high=new[]{high.X-margin,high.Y-margin,high.Z-margin},
        margin_voxels=3,margin_world_units=margin,margin_is_not_extraction_proof=true,
        operation="A_union_C_intersect_inner_ROI_where_C_is_closing_A",difference_shell_used_for_candidate=false,
        runtime_RebuildGrid_is_noop_in_pinned_source=true,
        native_VDB=new{filename="native-fields.vdb",sha256=vdbSha,named_fields=6,roundtrip_bitwise_comparison=roundtrip},
        exports,tested_native_lattice_nodes=tested,zero_conventions=new[]{"strict_negative_inside","zero_inside"},
        changed_nodes=changed,outside_ROI_changed_nodes=outside,protected_changed_nodes=protection,
        lost_original_gas_nodes=lost,added_nodes_touching_ROI_boundary=boundary,
        SDF_comparison=new{units="native_world_length_MM_for_synthetic_witness",finite_comparable_pairs=finite,
            unavailable_pairs=unavailable,outside_ROI_value_changes=outsideSdf,protected_value_changes=protectedSdf,
            max_abs_outside_ROI_delta_world_units=maxOutside,max_abs_protected_delta_world_units=maxProtected,
            outside_ROI_sampled_values_unchanged=outsideSdf==0&&unavailable==0,
            protected_sampled_values_unchanged=protectedSdf==0&&unavailable==0,
            not_a_continuous_isosurface_displacement_bound=true,examples=samples},
        elapsed_seconds=watch.Elapsed.TotalSeconds,peak_working_set_bytes=Process.GetCurrentProcess().PeakWorkingSet64,
        source_master_modified=false,private_head_processed=false,finer_resolution_executed=false,
        exact_BRep_created=false,CFD_qualified=false,manufacturing_authorized=false};
    File.WriteAllText(Path.Combine(output,"run-report.json"),JsonSerializer.Serialize(report,new JsonSerializerOptions{WriteIndented=true}));
    Console.WriteLine(JsonSerializer.Serialize(new{report.status,tested,outside,protection,lost,boundary,outsideSdf,protectedSdf,report.elapsed_seconds,report.peak_working_set_bytes}));
    return pass?0:3;
}
catch(Exception error)
{
    File.WriteAllText(Path.Combine(output,"FAILED.json"),JsonSerializer.Serialize(new{status="failed",error=error.ToString(),elapsed_seconds=watch.Elapsed.TotalSeconds,manufacturing_authorized=false}));
    Console.Error.WriteLine(error.ToString());return 1;
}

sealed class SliceReader
{
    readonly Voxels field;ImageGrayScale image;bool active;
    public readonly int X,Y,Z,Nx,Ny,Nz;
    public int[] Dimensions=>[X,Y,Z,Nx,Ny,Nz];
    public SliceReader(Voxels f){field=f;f.GetVoxelDimensions(out X,out Y,out Z,out Nx,out Ny,out Nz);image=f.imgAllocateSlice(out _);}
    public void Load(int z){active=z>=Z&&z<Z+Nz;if(active)field.GetVoxelSlice(z-Z,ref image,Voxels.ESliceMode.SignedDistance);}
    public float Value(int x,int y)=>active&&x>=X&&x<X+Nx&&y>=Y&&y<Y+Ny?image.fValue(x-X,Y+Ny-1-y):float.PositiveInfinity;
}
sealed class BoxSdf(Vector3 low,Vector3 high):IBoundedImplicit
{
    public BBox3 oBounds{get;}=new(low,high);
    public float fSignedDistance(in Vector3 point){Vector3 q=Vector3.Abs(point-(low+high)*0.5f)-(high-low)*0.5f;return Vector3.Max(q,Vector3.Zero).Length()+MathF.Min(MathF.Max(q.X,MathF.Max(q.Y,q.Z)),0);}
}
sealed class CylinderSdf(float low,float high,float radius):IBoundedImplicit
{
    public BBox3 oBounds{get;}=new(new Vector3(-radius,low,-radius),new Vector3(radius,high,radius));
    public float fSignedDistance(in Vector3 point){Vector2 q=new(MathF.Sqrt(point.X*point.X+point.Z*point.Z)-radius,MathF.Abs(point.Y-(low+high)*0.5f)-(high-low)*0.5f);return Vector2.Max(q,Vector2.Zero).Length()+MathF.Min(MathF.Max(q.X,q.Y),0);}
}
