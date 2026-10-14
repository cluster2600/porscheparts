using System.Numerics;
using System.Text.Json;
using PicoGK;
using PicoGKCatalog;

static class CoolingProgram
{
    public static void Main(string[] args)
    {
        if (args.Length != 3) throw new ArgumentException("Usage: Cooling study.json repository-root new-output");
        var card = JsonDocument.Parse(File.ReadAllText(args[0])).RootElement;
        var g = card.GetProperty("geometry");
        float P(string key) => g.GetProperty(key).GetSingle();
        float wall = P("wall_mm"), voxel = P("voxel_mm"), zf = P("fan_centre_z_mm");
        float front = P("fan_front_y_mm"), rear = P("fan_rear_y_mm"), radius = P("fan_radius_mm") + P("tip_gap_mm");
        float cw = P("core_width_mm"), cl = P("core_length_mm"), ct = P("core_thickness_mm"), cb = P("core_bottom_z_mm"), cy = P("core_centre_y_mm");
        float ox = P("outlet_x_mm"), oz = P("outlet_z_mm"), or = P("outlet_radius_mm");
        float[] ys = g.GetProperty("outlet_y_mm").EnumerateArray().Select(v => v.GetSingle()).ToArray();
        foreach (var item in g.EnumerateObject().Where(v => v.Value.ValueKind == JsonValueKind.Number))
            if (!float.IsFinite(item.Value.GetSingle())) throw new ArgumentException("Nonfinite geometry");
        if (voxel <= 0 || wall < 2 * voxel || cw < 400 || cl < 300 || ct < 20 || radius <= P("fan_radius_mm") || ys.Length != 3)
            throw new ArgumentException("Unresolved or invalid study geometry");
        if (card.GetProperty("manufacturing_authorized").GetBoolean() || card.GetProperty("installed_fit_verified").GetBoolean())
            throw new ArgumentException("Unmeasured geometry cannot grant functional acceptance");
        string output = Path.GetFullPath(args[2]);
        if (Directory.Exists(output)) throw new IOException("Output exists; preserve earlier run");
        Directory.CreateDirectory(output);
        using Library lib = new(voxel);
        var reports = new List<object>();
        void Save(string name, Voxels volume)
        {
            using (volume) using (Mesh raw = new(volume)) using (Mesh mesh = new(lib))
            {
                for (int i = 0; i < raw.nTriangleCount(); i++)
                {
                    raw.GetTriangle(i, out Vector3 a, out Vector3 b, out Vector3 c);
                    if (Vector3.Cross(b-a,c-a).LengthSquared() > 0) mesh.nAddTriangle(a,b,c);
                }
                if (mesh.nTriangleCount() == 0) throw new InvalidOperationException("Empty " + name);
                mesh.SaveToStlFile(Path.Combine(output, name + ".stl"), Mesh.EStlUnit.MM);
                reports.Add(new {name, triangles=mesh.nTriangleCount()});
                Console.WriteLine("GENERATED " + name);
            }
        }
        void Field(string name, Func<Vector3,float> f, Vector3 lo, Vector3 hi) => Save(name, Sdf.Vox(lib,f,lo,hi));
        float CylY(Vector3 p, float r, float y0, float y1) => Sdf.CylZ(new Vector3(p.X,p.Z-zf,p.Y),0,0,r,y0,y1);
        float Alternator(Vector3 p) => CylY(p,P("alternator_radius_mm"),rear-30,P("alternator_rear_y_mm"));
        float Intake(Vector3 p)
        {
            float top = Sdf.RoundBox(p,new Vector3(0,cy,cb-48),new Vector3(cw/2,cl/2,48),12);
            float elbow = Sdf.RoundBox(p,new Vector3(0,-280,335),new Vector3(130,55,40),16);
            float down = Sdf.RoundBox(p,new Vector3(0,-325,255),new Vector3(130,55,93),22);
            return MathF.Min(MathF.Min(top,elbow),MathF.Min(down,CylY(p,radius,-325,front)));
        }
        float Delivery(Vector3 p)
        {
            float d = MathF.Min(CylY(p,radius,rear,-5),Sdf.RoundBox(p,new Vector3(0,125,155),new Vector3(255,175,70),30));
            foreach (float y in ys) foreach (int sign in new[]{-1,1})
                d = RotKit.SMin(d,RotKit.Cone(p,new Vector3(sign*170,y,135),new Vector3(sign*ox,y,oz-25),or+8,or),12);
            return d;
        }
        float IntakeShell(Vector3 p)
        {
            float d = MathF.Max(MathF.Max(Intake(p)-wall,-Intake(p)),p.Z-cb);
            return p.Z < zf+radius+wall+10 ? MathF.Max(d,p.Y-front) : d;
        }
        float DeliveryShell(Vector3 p) => MathF.Max(MathF.Max(Delivery(p)-wall,-Delivery(p)),MathF.Max(rear-p.Y,oz-p.Z));
        // Check open routes analytically before asking the voxel kernel to export them.
        foreach (float y in ys) foreach (int sign in new[]{-1,1})
            if (Delivery(new Vector3(sign*ox,y,oz+5)) >= 0) throw new Exception("Cooling branch closed");
        Field("intake-shroud",IntakeShell,new(-cw/2-8,-390,45),new(cw/2+8,cy+cl/2+8,cb+8));
        Field("engine-shroud",DeliveryShell,new(-285,rear-8,oz-8),new(285,310,315));
        Field("alternator-envelope",Alternator,new(-75,rear-35,zf-75),new(75,5,zf+75));
        Field("fan-housing",p=>MathF.Max(CylY(p,radius+wall,front,rear),-CylY(p,radius,front-5,rear+5)),new(-135,front-5,zf-135),new(135,rear+5,zf+135));
        Field("delivery-fluid-domain",p=>MathF.Max(MathF.Max(Delivery(p),-Alternator(p)),MathF.Max(rear-p.Y,oz-p.Z)),new(-285,rear-5,oz-5),new(285,310,315));
        Field("intercooler-core-envelope",p=>Sdf.Box(p,new Vector3(0,cy,cb+ct/2),new Vector3(cw/2,cl/2,ct/2)),new(-cw/2-3,cy-cl/2-3,cb-3),new(cw/2+3,cy+cl/2+3,cb+ct+3));
        foreach (int sign in new[]{-1,1})
        {
            Vector3 c = new(sign*(cw/2+27),cy,cb+ct/2);
            float Tank(Vector3 p)
            {
                float body = Sdf.RoundBox(p,c,new Vector3(27,cl/2,ct/2),12);
                float shell = MathF.Max(body,-(body+wall));
                foreach (float dy in sign < 0 ? new[]{-110f,110f} : new[]{0f})
                {
                    Vector3 a = c + new Vector3(sign*18,dy,0), b = a + new Vector3(sign*60,0,0);
                    float bore = RotKit.Rod(p,a-new Vector3(sign*10,0,0),b+new Vector3(sign*5,0,0),24);
                    shell = MathF.Max(MathF.Min(shell,RotKit.Rod(p,a,b,24+wall)),-bore);
                }
                // Open core-facing header; individual charge passages require a supplier core design.
                return MathF.Max(shell,sign>0 ? cw/2+wall-p.X : p.X+cw/2+wall);
            }
            Field(sign<0 ? "charge-inlet-header" : "charge-outlet-header",Tank,c-new Vector3(85,cl/2+5,ct/2+5),c+new Vector3(85,cl/2+5,ct/2+5));
        }
        foreach (float y in ys) foreach (int sign in new[]{-1,1})
            Field($"engine-envelope-{sign}-{y}",p=>Sdf.CylZ(p,sign*ox,y,52,-85,oz-8),new(sign*ox-55,y-55,-90),new(sign*ox+55,y+55,oz-5));
        // Reuse the existing editable blade/cup generator; these are separate aerodynamic hypotheses.
        foreach (float delta in new[]{0f,-4f,4f})
        {
            var spec = PartSpec.Load(Path.Combine(args[1],card.GetProperty("rotor_parameters").GetString()!));
            spec.VoxelMm = 0.8f;
            foreach (var (station,factor) in new[]{("mid",0.5f),("tip",1f)})
            {
                string key=$"blade_{station}_stagger_deg";
                spec.Parameters[key]=spec.Parameters[key] with {Value=spec.Parameters[key].Value+delta*factor};
            }
            using Library rotorLib = new(spec.VoxelMm);
            using Voxels rotor = new CupAxialImpeller().Build(rotorLib,spec);
            using Mesh mesh = new(rotor);
            mesh.SaveToStlFile(Path.Combine(output,$"rotor-twist-{delta}.stl"),Mesh.EStlUnit.MM);
            reports.Add(new {name=$"rotor-twist-{delta}",triangles=mesh.nTriangleCount(),tip_stagger_delta_deg=delta});
            Console.WriteLine("GENERATED rotor twist " + delta);
        }
        File.WriteAllText(Path.Combine(output,"generation.json"),JsonSerializer.Serialize(new {status="picogk_geometry_generated_not_fit_validated",kernel=Library.strVersion(),parts=reports,manufacturing_authorized=false},new JsonSerializerOptions{WriteIndented=true}));
    }
}
