using System.Numerics;
using PicoGK;

namespace PicoGKCatalog;

/// Centrifugal compressor wheel, axis Z, back face at z = 0, nose up.
/// Hub: a concave trumpet (quarter ellipse) flaring from the inducer hub to
/// the backplate rim. Shroud contour: a second, concentric quarter ellipse
/// from the inducer tip (axial) to the exducer tip (radial). Main blades run
/// the whole passage, splitters start part-way; both are radial-element
/// blades with an inducer lean and a trailing-edge backsweep, tapered from
/// root to tip and fused to the hub by a smooth-union fillet. Through bore.
/// Used by the F0 (AlSi10Mg) and F1 (Al2139) records.
public sealed class CompressorWheel : IPartGenerator
{
    public string Name => "k16_compressor_wheel";

    public Voxels Build(Library lib, PartSpec s)
    {
        float R2 = s.P("exducer_diameter_mm") / 2f, R1t = s.P("inducer_diameter_mm") / 2f;
        float H = s.P("total_height_mm"), tb = s.P("backplate_thickness_mm");
        float r1h = s.P("inducer_hub_diameter_mm") / 2f, rNose = s.P("hub_top_radius_mm");
        float rBore = s.P("bore_diameter_mm") / 2f;
        float zLe = s.P("leading_edge_z_mm"), b2 = s.P("exit_blade_width_mm");
        int nMain = s.N("main_blade_count"), nSplit = s.N("splitter_blade_count");
        float rSplit = s.P("splitter_inner_radius_mm");
        float mT0 = s.P("main_root_thickness_mm"), mT1 = s.P("main_tip_thickness_mm");
        float sT0 = s.P("splitter_root_thickness_mm"), sT1 = s.P("splitter_tip_thickness_mm");
        float wrap = RotKit.Rad(s.P("inducer_wrap_deg")), sweep = RotKit.Rad(s.P("exit_backsweep_wrap_deg"));
        float fil = s.P("root_fillet_mm");
        float hubN = s.P("hub_profile_exponent");

        // Hub ellipse (passage inside it) and shroud ellipse (passage outside it), both centred (R2, zLe).
        float ah = R2 - r1h, bh = zLe - tb;
        float aS = R2 - R1t, bS = zLe - (tb + b2);
        // Splitter leading edge: where the hub reaches rSplit.
        float mSplit = MathF.Acos(Math.Clamp((R2 - rSplit) / ah, 0f, 1f)) / (RotKit.Pi / 2f);

        float M(float r, float z) =>
            Math.Clamp(MathF.Atan2(MathF.Max(zLe - z, 0f) / bh, MathF.Max(R2 - r, 1e-4f) / ah) / (RotKit.Pi / 2f), 0f, 1f);
        float Camber(float r, float z)
        {
            float m = M(r, z);
            return wrap * (1f - m) * (1f - m) - sweep * m * m;
        }

        float Field(Vector3 p)
        {
            float r = RotKit.R(p), z = p.Z, th = RotKit.Th(p);
            float eh = RotKit.SuperEllipse(r - R2, z - zLe, ah, bh, hubN);     // < 0 in the passage side
            float es = RotKit.Ellipse(r - R2, z - zLe, aS, bS);     // > 0 under the shroud
            // Hub + backplate (rounded rim) + nose boss.
            float rim = RotKit.SMax(r - R2, -z, 0.8f);
            float hub = MathF.Max(MathF.Max(-eh, z - zLe), rim);
            float nose = RotKit.Box2(r, z, -1f, rNose, zLe - 2f, H, 1.2f);
            hub = RotKit.SMin(hub, nose, 1.5f);

            // Passage region the blades live in (dips 0.6 mm into the hub for overlap).
            float region = MathF.Max(MathF.Max(eh - 0.6f, -es), MathF.Max(z - zLe, r - R2));
            float blades = 1e3f;
            if (region < 3f)
            {
                const float e = 0.05f;
                float tc = Camber(r, z);
                float gr = (Camber(r + e, z) - tc) / e, gz = (Camber(r, z + e) - tc) / e;
                float norm = MathF.Sqrt(1f + r * r * (gr * gr + gz * gz));
                float span = Math.Clamp(-eh / MathF.Max(-eh + es, 1e-3f), 0f, 1f);
                float m = M(r, z);

                float dM = RotKit.Near(th - tc, 2f * RotKit.Pi / nMain);
                float main = r * MathF.Abs(dM) / norm - (mT0 + (mT1 - mT0) * span) / 2f;
                main = RotKit.SMax(main, region, 0.3f);

                float dS = RotKit.Near(th - tc - RotKit.Pi / nSplit, 2f * RotKit.Pi / nSplit);
                float spl = r * MathF.Abs(dS) / norm - (sT0 + (sT1 - sT0) * span) / 2f;
                spl = RotKit.SMax(MathF.Max(spl, region), (mSplit - m) * 12f, 0.4f);
                blades = MathF.Min(main, spl);
            }
            float body = RotKit.SMin(hub, blades, fil);
            return MathF.Max(body, rBore - r);
        }

        Sdf.Stage(s.PartId, "wheel implicit");
        Vector3 lo = new(-R2 - 1f, -R2 - 1f, -1f), hi = new(R2 + 1f, R2 + 1f, H + 1f);
        return Sdf.Vox(lib, Field, lo, hi);
    }
}
