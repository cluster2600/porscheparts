using System.Numerics;
using System.Text.Json;
using PicoGK;
using PicoGKCatalog;

// Delivery fluid domain of the installed-cooling study, geometry revision R2c (issue #452).
//
// This is ../source-r2/Program.cs (R2) with one addition. R2 is pinned by the receipts
// of R2a and R2b and is not edited. Every R2 expression below is kept as it is, so a
// card without the new key regenerates what R2 generates from it.
//
// The addition is the optional key three_surface_corner_blend_mm = c. In R2b three
// pairwise blends meet where the alternator's rim, the plane y = -5 that the
// alternator's rear face shares with the fan cylinder's end, and the plenum top meet:
// the union seam (k), the alternator rim (k) and the alternator subtraction (s). The
// 2026-11-17 audit found 8.0 mm of re-entrant sharp edge left there. With c > 0 that
// corner is blended in one step:
//
//   RotKit.SMin(a, b, k) is exactly the mean of MathF.Min(a + t, b) for t uniform in
//   [-k, k]. R2c applies that same mean once to the hard Boolean of the three surfaces,
//   with t the position of the shared plane:
//
//     corner(v) = min(max(v, -side), max(box, min(-side, -v)))   v = y - alternator_rear_y - t
//     blended   = mean of corner(v) over t in [-c, c]
//
//   corner is piecewise linear in v with breaks at v = +-side, +-box and 0, so the mean
//   is integrated exactly. On each two-surface edge of the shared plane the mean is the
//   R2 blend itself: SMin(y - ay, box, c) on the seam, -SMax(side, y - ay, c) on the rim.
//
// The R2 union SMin(cylinder, box, k) is kept beside it, combined by MathF.Max. The
// mean is never below SMin(y - ay, box, c), so with k = c the maximum is the mean near
// the alternator and the R2 union elsewhere, including the fan cylinder's rear edge and
// its corners with the plenum, which are left as R2b has them.
//
// c is an unmeasured layout hypothesis, like k and s. R2c needs one radius (k = s = c)
// and the shared plane itself (alternator_rear_y_mm = -5, the cylinder's end below);
// the card cannot move the alternator's rear plane to clear the corner.
static class DeliveryR2cProgram
{
    static float Corner(float v, float box, float side) =>
        MathF.Min(MathF.Max(v, -side), MathF.Max(box, MathF.Min(-side, -v)));

    // Mean of Corner(u - t) over t in [-c, c], exact: trapezoids between the breaks.
    static float PlaneMean(float u, float box, float side, float c)
    {
        float lo = u - c, hi = u + c;
        Span<float> x = stackalloc float[7];
        x[0] = lo; x[1] = hi;
        x[2] = Math.Clamp(-side, lo, hi); x[3] = Math.Clamp(side, lo, hi);
        x[4] = Math.Clamp(box, lo, hi); x[5] = Math.Clamp(-box, lo, hi); x[6] = Math.Clamp(0f, lo, hi);
        x.Sort();
        float sum = 0f, previous = Corner(x[0], box, side);
        for (int i = 1; i < 7; i++)
        {
            float current = Corner(x[i], box, side);
            sum += 0.5f * (previous + current) * (x[i] - x[i-1]);
            previous = current;
        }
        return sum / (2f * c);
    }

    public static void Main(string[] args)
    {
        if (args.Length != 2) throw new ArgumentException("Usage: DeliveryR2c study.json new-output");
        var card = JsonDocument.Parse(File.ReadAllText(args[0])).RootElement;
        var g = card.GetProperty("geometry");
        float P(string key) => g.GetProperty(key).GetSingle();
        float wall = P("wall_mm"), voxel = P("voxel_mm"), zf = P("fan_centre_z_mm");
        float rear = P("fan_rear_y_mm"), radius = P("fan_radius_mm") + P("tip_gap_mm");
        float ox = P("outlet_x_mm"), oz = P("outlet_z_mm"), or = P("outlet_radius_mm");
        float ar = P("alternator_radius_mm"), ay = P("alternator_rear_y_mm");
        float k = g.TryGetProperty("reentrant_blend_mm", out var blend) ? blend.GetSingle() : 0f;
        float s = g.TryGetProperty("alternator_subtraction_blend_mm", out var subtraction) ? subtraction.GetSingle() : 0f;
        float c = g.TryGetProperty("three_surface_corner_blend_mm", out var corner) ? corner.GetSingle() : 0f;
        float[] ys = g.GetProperty("outlet_y_mm").EnumerateArray().Select(v => v.GetSingle()).ToArray();
        foreach (var item in g.EnumerateObject().Where(v => v.Value.ValueKind == JsonValueKind.Number))
            if (!float.IsFinite(item.Value.GetSingle())) throw new ArgumentException("Nonfinite geometry");
        if (voxel <= 0 || wall < 2 * voxel || radius <= P("fan_radius_mm") || ys.Length != 3)
            throw new ArgumentException("Unresolved or invalid study geometry");
        // A blend narrower than four voxels is not resolved by the kernel grid.
        foreach (float b in new[]{k,s,c})
            if (b < 0 || (b > 0 && b < 4 * voxel)) throw new ArgumentException("Unresolved blend");
        // The one-step corner blend replaces three blends of one radius at one shared plane.
        if (c > 0 && (k != c || s != c || ay != -5f))
            throw new ArgumentException("The corner blend needs k = s = c and the shared plane y = -5");
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
        // R2c: the R2 union beside the one-step mean of the three-surface corner, then the
        // branch cones as in Delivery. The alternator lies inside the fan cylinder, away from
        // the cones, so subtracting it before rather than after the cones changes nothing.
        float DeliveryR2c(Vector3 p)
        {
            float box = Sdf.RoundBox(p,new Vector3(0,125,155),new Vector3(255,175,70),30);
            float dx = p.X, dz = p.Z-zf;
            float side = MathF.Max(MathF.Sqrt(dx*dx+dz*dz)-ar,rear-30-p.Y);
            float d = MathF.Max(RotKit.SMin(CylY(p,radius,front,-5),box,k),PlaneMean(p.Y-ay,box,side,c));
            foreach (float y in ys) foreach (int sign in new[]{-1,1})
                d = RotKit.SMin(d,RotKit.Cone(p,new Vector3(sign*170,y,135),new Vector3(sign*ox,y,oz-25),or+8,or),12);
            return d;
        }
        float Fluid(Vector3 p) => c > 0
            ? MathF.Max(DeliveryR2c(p),MathF.Max(rear-p.Y,oz-p.Z))
            : MathF.Max(RotKit.SMax(Delivery(p),-Alternator(p),s),MathF.Max(rear-p.Y,oz-p.Z));

        // Check open routes analytically before asking the voxel kernel to export them.
        foreach (float y in ys) foreach (int sign in new[]{-1,1})
            if (Fluid(new Vector3(sign*ox,y,oz+5)) >= 0) throw new Exception("Cooling branch closed");
        int triangles;
        using (Voxels volume = Sdf.Vox(lib,Fluid,new(-285,rear-5,oz-5),new(285,310,315)))
        using (Mesh raw = new(volume)) using (Mesh mesh = new(lib))
        {
            for (int i = 0; i < raw.nTriangleCount(); i++)
            {
                raw.GetTriangle(i, out Vector3 a, out Vector3 b, out Vector3 cc);
                if (Vector3.Cross(b-a,cc-a).LengthSquared() > 0) mesh.nAddTriangle(a,b,cc);
            }
            if (mesh.nTriangleCount() == 0) throw new InvalidOperationException("Empty delivery-fluid-domain");
            mesh.SaveToStlFile(Path.Combine(output,"delivery-fluid-domain.stl"), Mesh.EStlUnit.MM);
            triangles = mesh.nTriangleCount();
            Console.WriteLine("GENERATED delivery-fluid-domain");
        }
        File.WriteAllText(Path.Combine(output,"generation.json"),JsonSerializer.Serialize(new {
            status="picogk_geometry_generated_not_fit_validated",kernel=Library.strVersion(),
            geometry_revision=c > 0 ? "R2c" : k > 0 || s > 0 ? "R2" : "R1",reentrant_blend_mm=k,alternator_subtraction_blend_mm=s,
            three_surface_corner_blend_mm=c,
            blend_basis=k > 0 || s > 0 || c > 0 ? "unmeasured_layout_hypothesis_chosen_for_numerical_admissibility" : "none",
            parts=new[]{new {name="delivery-fluid-domain",triangles}},manufacturing_authorized=false},
            new JsonSerializerOptions{WriteIndented=true}));
    }
}
