using System.Numerics;
using PicoGK;

namespace PicoGKCatalog;

/// Radial-inflow turbine wheel, axis Z, back face at z = 0, exducer up.
/// Blades are radial fibres at the inlet (tip edge parallel to the axis at
/// the inducer diameter) and wrap into an axial exducer; the hub is a concave
/// quarter ellipse to a nose boss; the back disc is scalloped between blades.
/// Root-to-tip taper, smooth-union root fillets.
public sealed class TurbineWheel : IPartGenerator
{
    public string Name => "k16_turbine_wheel";

    public Voxels Build(Library lib, PartSpec s)
    {
        float R1 = s.P("inducer_diameter_mm") / 2f, Rex = s.P("exducer_diameter_mm") / 2f;
        float H = s.P("total_height_mm"), zb = s.P("backface_thickness_mm"), b1 = s.P("tip_height_mm");
        float rShaft = s.P("shaft_diameter_mm") / 2f, rExh = s.P("exducer_hub_radius_mm"), zEx = s.P("exducer_plane_z_mm");
        int n = s.N("blade_count");
        float t0 = s.P("blade_root_thickness_mm"), t1 = s.P("blade_tip_thickness_mm");
        float wrap = RotKit.Rad(s.P("exducer_wrap_deg")), scal = s.P("backface_scallop_depth_mm");
        float fil = s.P("root_fillet_mm");
        float hubN = s.P("hub_profile_exponent");

        float ah = R1 - rExh, bh = zEx - zb;
        float aS = R1 - Rex, bS = zEx - (zb + b1);
        float rNose = rShaft + 1.3f;

        float M(float r, float z) =>
            Math.Clamp(MathF.Atan2(MathF.Max(R1 - r, 0f) / ah, MathF.Max(zEx - z, 1e-4f) / bh) / (RotKit.Pi / 2f), 0f, 1f);
        float Camber(float r, float z) { float m = M(r, z); return wrap * m * m; }

        float Field(Vector3 p)
        {
            float r = RotKit.R(p), z = p.Z, th = RotKit.Th(p);
            float eh = RotKit.SuperEllipse(r - R1, z - zEx, ah, bh, hubN);
            float es = RotKit.Ellipse(r - R1, z - zEx, aS, bS);
            float sn = MathF.Sin(n * th / 2f);
            float rSc = R1 - scal * sn * sn;
            float hub = MathF.Max(MathF.Max(-eh, z - zEx), RotKit.SMax(r - rSc, -z, 0.6f));
            float nose = RotKit.Box2(r, z, -1f, rNose, zEx - 2f, H, 1.0f);
            hub = RotKit.SMin(hub, nose, 1.5f);

            float tipDist = MathF.Min(es, R1 - r);
            float region = MathF.Max(MathF.Max(eh - 0.6f, -tipDist), z - zEx);
            float blades = 1e3f;
            if (region < 3f)
            {
                const float e = 0.05f;
                float tc = Camber(r, z);
                float gr = (Camber(r + e, z) - tc) / e, gz = (Camber(r, z + e) - tc) / e;
                float norm = MathF.Sqrt(1f + r * r * (gr * gr + gz * gz));
                float span = Math.Clamp(-eh / MathF.Max(-eh + MathF.Max(tipDist, 0f), 1e-3f), 0f, 1f);
                float d = RotKit.Near(th - tc, 2f * RotKit.Pi / n);
                blades = r * MathF.Abs(d) / norm - (t0 + (t1 - t0) * span) / 2f;
                blades = RotKit.SMax(blades, region, 0.3f);
            }
            return RotKit.SMin(hub, blades, fil);
        }

        Sdf.Stage(s.PartId, "wheel implicit");
        Vector3 lo = new(-R1 - 1f, -R1 - 1f, -1f), hi = new(R1 + 1f, R1 + 1f, H + 1f);
        return Sdf.Vox(lib, Field, lo, hi);
    }
}
