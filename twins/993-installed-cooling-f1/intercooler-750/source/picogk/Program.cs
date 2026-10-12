using System.Numerics;
using System.Text.Json;
using PicoGK;
using PicoGKCatalog;

if (args.Length != 2) throw new ArgumentException("Usage: Core sizing.json new-output");
var report=JsonDocument.Parse(File.ReadAllText(args[0])).RootElement;
var g=report.GetProperty("selected_geometry");
if (g.ValueKind != JsonValueKind.Object) throw new ArgumentException("No candidate in sizing result");
foreach(var item in report.GetProperty("acceptance").EnumerateObject())
    if (item.Value.GetBoolean()) throw new ArgumentException("Coupon cannot grant engineering acceptance");
float P(string name) => g.GetProperty(name).GetSingle();
float h=P("hot_gap_mm"), c=P("cold_gap_mm"), t=P("fin_mm"), wall=P("wall_mm");
float hp=P("hot_pitch_mm"), cp=P("cold_pitch_mm"), strip=P("strip_length_mm");
float voxel=report.GetProperty("basis").GetProperty("assumed").GetProperty("coupon_voxel_mm").GetSingle();
foreach(float value in new[]{h,c,t,wall,hp,cp,strip,voxel})
    if (!float.IsFinite(value) || value<=0) throw new ArgumentException("Invalid geometry");
if (t<4*voxel-1e-6 || wall<4*voxel || hp<=t || cp<=t || strip<5 || strip>30) throw new ArgumentException("Unresolved channels");
string output=Path.GetFullPath(args[1]);
if (Directory.Exists(output)) throw new IOException("Output exists; preserve previous run");
Directory.CreateDirectory(output);
float x=2*strip, z=2*strip, period=h+2*wall+c, y=3*(h+2*wall)+2*c;
float Box(Vector3 p,Vector3 lo,Vector3 hi)=>Sdf.Box(p,(lo+hi)/2,(hi-lo)/2);
float Repeat(float v,float origin,float pitch)=>MathF.Abs(v-origin-pitch*MathF.Round((v-origin)/pitch))-t/2;
float Core(Vector3 p,bool offset)
{
    float value=float.PositiveInfinity;
    for(int i=0;i<3;i++)
    {
        float y0=i*period;
        float shell=MathF.Max(Box(p,new(0,y0,0),new(x,y0+h+2*wall,z)),
            -Box(p,new(-1,y0+wall,wall),new(x+1,y0+wall+h,z-wall)));
        value=MathF.Min(value,shell);
        for(int s=0;s<2;s++)
        {
            // Overlap roots into the separator so unions have volume rather than a shared face.
            float phase=offset && s%2==1 ? hp/2 : 0;
            float fin=MathF.Max(Repeat(p.Z,wall+hp-t/2+phase,hp),Box(p,new(s*strip,y0+wall-2*voxel,wall),new((s+1)*strip,y0+wall+h+2*voxel,z-wall)));
            value=MathF.Min(value,fin);
        }
        if(i==2) continue;
        float low=y0+h+2*wall;
        value=MathF.Min(value,Box(p,new(0,low-2*voxel,0),new(wall,low+c+2*voxel,z)));
        value=MathF.Min(value,Box(p,new(x-wall,low-2*voxel,0),new(x,low+c+2*voxel,z)));
        for(int s=0;s<2;s++)
        {
            float phase=offset && s%2==1 ? cp/2 : 0;
            float fin=MathF.Max(Repeat(p.X,wall+cp-t/2+phase,cp),Box(p,new(wall,low-2*voxel,s*strip),new(x-wall,low+c+2*voxel,(s+1)*strip)));
            value=MathF.Min(value,fin);
        }
    }
    return value;
}
using Library lib=new(voxel);
var parts=new List<object>();
foreach(bool offset in new[]{false,true})
{
    string name=offset ? "offset-fin-coupon" : "plain-fin-control";
    using Voxels v=Sdf.Vox(lib,p=>Core(p,offset),new(-voxel),new(x+voxel,y+voxel,z+voxel));
    using Mesh mesh=new(v);
    mesh.SaveToStlFile(Path.Combine(output,name+".stl"),Mesh.EStlUnit.MM);
    parts.Add(new {name,triangles=mesh.nTriangleCount()});
    Console.WriteLine("GENERATED "+name);
}
File.WriteAllText(Path.Combine(output,"generation.json"),JsonSerializer.Serialize(new {
    status="native_picogk_channel_coupons_not_pressure_qualified",kernel=Library.strVersion(),voxel_mm=voxel,
    dimensions_mm=new[]{x,y,z},hot_flow_axis="X",cold_flow_axis="Z",build_direction=new[]{1/Math.Sqrt(2),0,1/Math.Sqrt(2)},
    geometry=g,parts,manufacturing_authorized=false,full_core_generated=false,
    limitation="Two strip lengths only; channel dimensions match sizing, finite edge channels differ; no headers or bench adapters."
},new JsonSerializerOptions{WriteIndented=true}));
