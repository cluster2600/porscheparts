using System.Numerics;
using System.Text.Json;
using PicoGK;

if (args.Length != 2) throw new ArgumentException("Usage: Reference reference.json new-output-directory");
var data = JsonDocument.Parse(File.ReadAllText(args[0])).RootElement;
float Read(string name) {
    float x = data.GetProperty(name).GetSingle();
    if (!float.IsFinite(x)) throw new ArgumentException(name);
    return x;
}
float voxel = Read("voxel_mm");
if (voxel <= 0 || voxel > Read("blade_thickness_mm") / 3) throw new ArgumentException("Unresolved thickness");
var rotor = new ReferenceRotor(Read);
rotor.Check();
string output = Path.GetFullPath(args[1]);
if (Directory.Exists(output)) throw new IOException("Output exists; preserve prior run");
Directory.CreateDirectory(output);
using Library library = new(voxel);
var reports = new List<object>();
foreach (string part in new[] { "rotor", "bearing-hub" }) {
    IImplicit field = part == "rotor" ? rotor : new BearingHub(Read);
    using Voxels volume = new(library, field, new BBox3(new Vector3(-128,-128,-65),new Vector3(128,128,45)));
    volume.CalculateProperties(out float mm3, out _);
    using Mesh raw = new(volume);
    using Mesh mesh = new(library);
    for(int i=0;i<raw.nTriangleCount();i++) {
        raw.GetTriangle(i,out Vector3 a,out Vector3 b,out Vector3 c);
        if(Vector3.Cross(b-a,c-a).LengthSquared() > 0) mesh.nAddTriangle(a,b,c);
    }
    if(mm3 <= 0 || mesh.nTriangleCount()==0) throw new InvalidOperationException("Empty geometry");
    mesh.SaveToStlFile(Path.Combine(output,part+"-mm.stl"),Mesh.EStlUnit.MM);
    reports.Add(new {part,volume_mm3=mm3,triangles=mesh.nTriangleCount()});
    Console.WriteLine($"GENERATED {part} triangles={mesh.nTriangleCount()}");
}
File.WriteAllText(Path.Combine(output,"generation.json"),JsonSerializer.Serialize(new {
    status="visual_reference_reconstruction",parameters=data,parts=reports,
    dimensionally_validated=false,flow_validated=false,manufacturing_authorized=false
},new JsonSerializerOptions{WriteIndented=true}));

sealed class ReferenceRotor(Func<string,float> get) : IImplicit {
    readonly float radius=get("rotor_diameter_mm")/2, cup=get("cup_radius_mm"), front=get("cup_front_z_mm"),
        rear=get("cup_rear_z_mm"), wall=get("wall_mm"), web=get("web_mm"), bore=get("bore_radius_mm"),
        ventR=get("vent_radius_mm"), ventW=get("vent_radial_halfwidth_mm"), ventT=get("vent_tangential_halfwidth_mm"),
        rootChord=get("blade_root_chord_mm"),tipChord=get("blade_tip_chord_mm"),pitch=get("blade_pitch_deg")*MathF.PI/180,
        thickness=get("blade_thickness_mm"), blades=get("blade_count"),vents=get("vent_count"),
        boltR=get("bolt_circle_radius_mm"), boltHole=get("bolt_hole_radius_mm");
    static float Fold(float angle,float count) {
        float period=2*MathF.PI/count; return angle-period*MathF.Round(angle/period);
    }
    public float fSignedDistance(in Vector3 p) {
        float r=MathF.Sqrt(p.X*p.X+p.Y*p.Y),theta=MathF.Atan2(p.Y,p.X);
        // Rounded outer cup transition; dimensions are explicitly visual hypotheses.
        float zWeb=front+8*MathF.Pow(Math.Clamp(r/cup,0,1),2);
        float disc=MathF.Max(MathF.Abs(p.Z-zWeb)-web/2,MathF.Max(bore-r,r-cup));
        float sleeve=MathF.Max(MathF.Abs(r-(cup-wall/2))-wall/2,MathF.Max(zWeb-p.Z,p.Z-rear));
        float ventTheta=Fold(theta,vents);
        float qx=MathF.Abs(r-ventR)-ventW+2.5f, qy=MathF.Abs(r*MathF.Sin(ventTheta))-ventT+2.5f;
        float opening=MathF.Min(MathF.Max(qx,qy),0)+MathF.Sqrt(MathF.Pow(MathF.Max(qx,0),2)+MathF.Pow(MathF.Max(qy,0),2))-2.5f;
        disc=MathF.Max(disc,-opening);
        // Ribs are on the rear web, between the ventilation openings.
        float ribTheta=Fold(theta-MathF.PI/vents,vents);
        float ribs=MathF.Max(MathF.Abs(r*MathF.Sin(ribTheta))-1.7f,
            MathF.Max(MathF.Abs(p.Z-zWeb-3)-3,MathF.Max(32-r,r-cup+wall)));
        float body=MathF.Min(MathF.Min(disc,sleeve),ribs);
        float boltTheta=Fold(theta,3);
        float bolt=MathF.Sqrt(MathF.Pow(r*MathF.Cos(boltTheta)-boltR,2)+MathF.Pow(r*MathF.Sin(boltTheta),2))-boltHole;
        body=MathF.Max(body,-bolt);
        float span=Math.Clamp((r-cup)/(radius-cup),0,1),chord=rootChord+(tipChord-rootChord)*span;
        float tangential=r*MathF.Sin(Fold(theta,blades));
        float u=tangential*MathF.Cos(pitch)+p.Z*MathF.Sin(pitch);
        float v=-tangential*MathF.Sin(pitch)+p.Z*MathF.Cos(pitch);
        float camber=2*(1-MathF.Pow(Math.Clamp(2*u/chord,-1,1),2));
        float blade=MathF.Max(MathF.Abs(v-camber)-thickness/2,
            MathF.Max(MathF.Abs(u)-chord/2,MathF.Max(cup-wall-r,r-radius)));
        return MathF.Min(body,blade);
    }
    public void Check() {
        if(blades!=11 || vents!=12 || radius<=cup || cup<=ventR+ventW || bore>=ventR-ventW)
            throw new ArgumentException("Invalid reference topology");
        if(fSignedDistance(new Vector3(0,0,front))<=0) throw new Exception("Bore closed");
        for(int i=0;i<12;i++) {
            float a=2*MathF.PI*i/12;
            var p=new Vector3(ventR*MathF.Cos(a),ventR*MathF.Sin(a),front+8*MathF.Pow(ventR/cup,2));
            if(fSignedDistance(p)<=0) throw new Exception("Vent closed");
        }
        if(fSignedDistance(new Vector3(cup-wall/2,0,10))>=0) throw new Exception("Cup missing");
        for(int i=0;i<11;i++) {
            float a=2*MathF.PI*i/11,r=(cup+radius)/2;
            if(fSignedDistance(new Vector3(r*MathF.Cos(a),r*MathF.Sin(a),2/MathF.Cos(pitch)))>=0) throw new Exception("Blade missing");
        }
    }
}
sealed class BearingHub(Func<string,float> get) : IImplicit {
    public float fSignedDistance(in Vector3 p) {
        float r=MathF.Sqrt(p.X*p.X+p.Y*p.Y), z=get("cup_front_z_mm");
        float flange=MathF.Max(r-get("hub_radius_mm"),MathF.Abs(p.Z-(z-6))-3.5f);
        float tube=MathF.Max(r-17,MathF.Max(z-2.5f-get("hub_length_mm")-p.Z,p.Z-z+3));
        float body=MathF.Max(MathF.Min(flange,tube),get("hub_bore_radius_mm")-r);
        float theta=MathF.Atan2(p.Y,p.X),period=2*MathF.PI/3;
        theta-=period*MathF.Round(theta/period);
        float hole=MathF.Sqrt(MathF.Pow(r*MathF.Cos(theta)-get("bolt_circle_radius_mm"),2)+MathF.Pow(r*MathF.Sin(theta),2))-get("bolt_hole_radius_mm");
        return MathF.Max(body,-hole);
    }
}
