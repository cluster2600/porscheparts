using System.Numerics;
using PicoGK;

namespace PicoGKCatalog;

/// 993 front impact support, AlSi10Mg graded-core concept. Axis X: solid
/// rear plate at x = 0..plate, elliptical crush shell to x = length, open at
/// the front. A cruciform core, graded continuously from core_t_rear to
/// core_t_front, splits the shell into four open channels (depowdering and
/// inspection path). The shell flares into the plate (root fillet) and the
/// webs are filleted into the shell. No mounting hole: no interface measured.
public sealed class FrontImpactSupport : IPartGenerator
{
    public string Name => "front_impact_support_graded";

    public Voxels Build(Library lib, PartSpec s)
    {
        float L = s.P("length_mm"), W = s.P("width_mm"), H = s.P("height_mm");
        float tp = s.P("base_plate_mm"), rc = s.P("plate_corner_radius_mm");
        float a = s.P("shell_semi_axis_y_mm"), b = s.P("shell_semi_axis_z_mm"), ts = s.P("shell_wall_mm");
        float t0 = s.P("core_t_rear_mm"), t1 = s.P("core_t_front_mm");
        float flare = s.P("root_flare_mm"), flareLen = s.P("root_flare_length_mm");
        float kf = s.P("web_fillet_mm");
        float lip = s.P("front_lip_round_mm");

        float Field(Vector3 p)
        {
            float x = p.X, y = p.Y, z = p.Z;
            // rear plate: rounded rectangle in YZ, thickness tp along X, edges softened
            float dPlate = BodyKit.RoundI(BodyKit.RoundRect(y, z, W / 2f, H / 2f, rc), MathF.Abs(x - tp / 2f) - tp / 2f, 0.6f);

            float xe = MathF.Max(x - tp, 0f);
            float e = flare * MathF.Exp(-xe / flareLen);
            float dOutE = BodyKit.Ellipse(y, z, a + e, b + e);
            float dTube = BodyKit.RoundI(dOutE, MathF.Max(tp - 0.5f - x, x - L), lip);
            float dIn = MathF.Max(BodyKit.Ellipse(y, z, a - ts, b - ts), tp - x);
            float shell = MathF.Max(dTube, -dIn);

            float u = Math.Clamp((x - tp) / (L - tp), 0f, 1f);
            float t = t0 + (t1 - t0) * u;
            float web = MathF.Min(MathF.Abs(y), MathF.Abs(z)) - t / 2f;
            float core = MathF.Max(web, dTube);

            return MathF.Min(dPlate, BodyKit.SMin(shell, core, kf));
        }

        Sdf.Stage(s.PartId, "render");
        Vector3 lo = new(-1f, -W / 2f - 1f, -H / 2f - 1f), hi = new(L + 1f, W / 2f + 1f, H / 2f + 1f);
        return Sdf.Vox(lib, Field, lo, hi);
    }
}
