using System.Numerics;
using System.Text.Json;
using PicoGK;
using PicoGKCatalog;

// Delivery fluid domain of the installed-cooling study, geometry revision R2 (issue #452).
//
// Every dimension and every expression is that of ../source/Program.cs (R1). The
// additions are two blend parameters read from the study card's geometry block,
// both applied with RotKit's polynomial blend, the one the branch cones already
// use with 12 mm:
//
//   reentrant_blend_mm = k              the two joins that leave re-entrant edges in R1:
//                                         fan cylinder / plenum box union    SMin(cylinder, box, k)
//                                         alternator envelope, side / end    SMax(side, end, k)
//   alternator_subtraction_blend_mm = s the alternator's subtraction from the duct:
//                                         SMax(duct, -alternator, s)
//
// A parameter that is absent or 0 leaves the hard MathF.Min / MathF.Max of R1
// (RotKit.SMin returns MathF.Min for k <= 0). With both absent the R1 fluid domain
// is regenerated expression for expression.
//
// Both are unmeasured layout hypotheses chosen for numerical admissibility, like the
// joins they blend. The inlet and outlet planes stay hard cuts: they are patch
// boundaries. Only the fluid domain is generated here; the R1 bodies are untouched.
static class DeliveryR2Program
{
    public static void Main(string[] args)
    {
        if (args.Length != 2) throw new ArgumentException("Usage: DeliveryR2 study.json new-output");
        var card = JsonDocument.Parse(File.ReadAllText(args[0])).RootElement;
        var g = card.GetProperty("geometry");
        float P(string key) => g.GetProperty(key).GetSingle();
        float wall = P("wall_mm"), voxel = P("voxel_mm"), zf = P("fan_centre_z_mm");
        float rear = P("fan_rear_y_mm"), radius = P("fan_radius_mm") + P("tip_gap_mm");
        float ox = P("outlet_x_mm"), oz = P("outlet_z_mm"), or = P("outlet_radius_mm");
        float ar = P("alternator_radius_mm"), ay = P("alternator_rear_y_mm");
        float k = g.TryGetProperty("reentrant_blend_mm", out var blend) ? blend.GetSingle() : 0f;
        float s = g.TryGetProperty("alternator_subtraction_blend_mm", out var subtraction) ? subtraction.GetSingle() : 0f;
        float[] ys = g.GetProperty("outlet_y_mm").EnumerateArray().Select(v => v.GetSingle()).ToArray();
        foreach (var item in g.EnumerateObject().Where(v => v.Value.ValueKind == JsonValueKind.Number))
            if (!float.IsFinite(item.Value.GetSingle())) throw new ArgumentException("Nonfinite geometry");
        if (voxel <= 0 || wall < 2 * voxel || radius <= P("fan_radius_mm") || ys.Length != 3)
            throw new ArgumentException("Unresolved or invalid study geometry");
        // A blend narrower than four voxels is not resolved by the kernel grid.
        foreach (float b in new[]{k,s})
            if (b < 0 || (b > 0 && b < 4 * voxel)) throw new ArgumentException("Unresolved blend");
        if (card.GetProperty("manufacturing_authorized").GetBoolean() || card.GetProperty("installed_fit_verified").GetBoolean())
            throw new ArgumentException("Unmeasured geometry cannot grant functional acceptance");
        string output = Path.GetFullPath(args[1]);
        if (Directory.Exists(output)) throw new IOException("Output exists; preserve earlier run");
        Directory.CreateDirectory(output);
        using Library lib = new(voxel);

        float CylY(Vector3 p, float r, float y0, float y1) => Sdf.CylZ(new Vector3(p.X,p.Z-zf,p.Y),0,0,r,y0,y1);
        float Alternator(Vector3 p)
        {
            if (k <= 0) return CylY(p,ar,rear-30,ay);
            float dx = p.X, dz = p.Z-zf;
            float side = MathF.Max(MathF.Sqrt(dx*dx+dz*dz)-ar,rear-30-p.Y);
            return RotKit.SMax(side,p.Y-ay,k);
        }
        // In R1 the fan cylinder's front cap lies in the inlet plane. A blended alternator
        // subtraction would round that cap into the alternator and move the inlet's inner
        // rim, so with s > 0 the cylinder starts at the alternator's own front plane
        // (rear - 30) and the inlet plane alone cuts it. The cut domain is the same set.
        float front = s > 0 ? rear-30 : rear;
        float Delivery(Vector3 p)
        {
            float d = RotKit.SMin(CylY(p,radius,front,-5),Sdf.RoundBox(p,new Vector3(0,125,155),new Vector3(255,175,70),30),k);
            foreach (float y in ys) foreach (int sign in new[]{-1,1})
                d = RotKit.SMin(d,RotKit.Cone(p,new Vector3(sign*170,y,135),new Vector3(sign*ox,y,oz-25),or+8,or),12);
            return d;
        }
        float Fluid(Vector3 p) => MathF.Max(RotKit.SMax(Delivery(p),-Alternator(p),s),MathF.Max(rear-p.Y,oz-p.Z));

        // Check open routes analytically before asking the voxel kernel to export them.
        foreach (float y in ys) foreach (int sign in new[]{-1,1})
            if (Fluid(new Vector3(sign*ox,y,oz+5)) >= 0) throw new Exception("Cooling branch closed");
        int triangles;
        using (Voxels volume = Sdf.Vox(lib,Fluid,new(-285,rear-5,oz-5),new(285,310,315)))
        using (Mesh raw = new(volume)) using (Mesh mesh = new(lib))
        {
            for (int i = 0; i < raw.nTriangleCount(); i++)
            {
                raw.GetTriangle(i, out Vector3 a, out Vector3 b, out Vector3 c);
                if (Vector3.Cross(b-a,c-a).LengthSquared() > 0) mesh.nAddTriangle(a,b,c);
            }
            if (mesh.nTriangleCount() == 0) throw new InvalidOperationException("Empty delivery-fluid-domain");
            mesh.SaveToStlFile(Path.Combine(output,"delivery-fluid-domain.stl"), Mesh.EStlUnit.MM);
            triangles = mesh.nTriangleCount();
            Console.WriteLine("GENERATED delivery-fluid-domain");
        }
        File.WriteAllText(Path.Combine(output,"generation.json"),JsonSerializer.Serialize(new {
            status="picogk_geometry_generated_not_fit_validated",kernel=Library.strVersion(),
            geometry_revision=k > 0 || s > 0 ? "R2" : "R1",reentrant_blend_mm=k,alternator_subtraction_blend_mm=s,
            blend_basis=k > 0 || s > 0 ? "unmeasured_layout_hypothesis_chosen_for_numerical_admissibility" : "none",
            parts=new[]{new {name="delivery-fluid-domain",triangles}},manufacturing_authorized=false},
            new JsonSerializerOptions{WriteIndented=true}));
    }
}
