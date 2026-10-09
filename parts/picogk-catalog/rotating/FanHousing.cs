using System.Numerics;
using PicoGK;

namespace PicoGKCatalog;

/// Stationary fan housing, axis Z, inlet face at z = depth (modelled at z = 0, then flipped). Cylindrical shell
/// with a thickened rear rim; front flange rolled into a bellmouth (quarter
/// torus shell) that ends in the throat sleeve; six rounded spokes carry the
/// alternator seat hub; mount pads with through holes on the flange. All
/// joints blended by smooth union; open annular pocket behind the throat.
public sealed class FanHousing : IPartGenerator
{
    public string Name => "fan_housing";

    public Voxels Build(Library lib, PartSpec s)
    {
        float Ro = s.P("outer_diameter_mm") / 2f, D = s.P("depth_mm"), t = s.P("shell_thickness_mm");
        float rT = s.P("throat_diameter_mm") / 2f, tf = s.P("front_flange_thickness_mm");
        float rHo = s.P("hub_outer_diameter_mm") / 2f, rHi = s.P("hub_bore_diameter_mm") / 2f, hD = s.P("hub_depth_mm");
        int nS = s.N("spoke_count");
        float sW = s.P("spoke_width_mm"), sT = s.P("spoke_thickness_mm");
        float rM = s.P("mount_radius_mm"), dM = s.P("mount_bore_diameter_mm");
        int nM = s.N("mount_count");
        float Rb = s.P("bellmouth_radius_mm"), lT = s.P("throat_land_length_mm"), rear = s.P("rear_rim_width_mm");
        float fil = s.P("fillet_mm");
        float zS = Rb + sT / 2f + 2f;              // spoke centre plane, just behind the throat start
        float hz0 = zS - hD / 2f;

        // Inlet face up (z = D) so the bellmouth, spokes and hub face the viewer.
        float Field(Vector3 pIn)
        {
            Vector3 p = new(pIn.X, pIn.Y, D - pIn.Z);
            float r = RotKit.R(p), z = p.Z, th = RotKit.Th(p);
            float shell = RotKit.Annulus(p, Ro - t, Ro, 0f, D, 1.2f);
            float rim = RotKit.Annulus(p, Ro - t - rear, Ro, D - rear, D, 1.5f);
            float flange = RotKit.Annulus(p, rT + Rb - 0.5f, Ro - 0.5f, 0f, tf, 1.5f);
            // Bellmouth: quarter-torus shell, flow side outside the torus.
            float cr = rT + Rb, cz = Rb;
            float dc = MathF.Sqrt((r - cr) * (r - cr) + (z - cz) * (z - cz));
            float bell = MathF.Max(MathF.Abs(dc - (Rb - t / 2f)) - t / 2f, MathF.Max(r - cr, z - cz));
            float sleeve = RotKit.Annulus(p, rT, rT + t, cz - 0.5f, lT, 1.2f);
            // Mount pads behind the flange.
            float dmA = RotKit.Near(th - RotKit.Pi / nM, 2f * RotKit.Pi / nM);
            float mx = r * MathF.Cos(dmA) - rM, my = r * MathF.Sin(dmA);
            float pad = MathF.Max(MathF.Sqrt(mx * mx + my * my) - (dM / 2f + 4f), MathF.Abs(z - 4.5f) - 4.5f);
            float hole = MathF.Sqrt(mx * mx + my * my) - dM / 2f;

            float body = RotKit.SMin(shell, flange, 3f);
            body = MathF.Min(body, rim);
            body = RotKit.SMin(body, bell, 2f);
            body = RotKit.SMin(body, sleeve, 2f);
            body = RotKit.SMin(body, pad, 2f);

            // Spokes and hub.
            float ds = RotKit.Near(th, 2f * RotKit.Pi / nS);
            float sx = r * MathF.Cos(ds), sy = r * MathF.Sin(ds);
            float spoke = MathF.Max(RotKit.Box2(sy, z, -sW / 2f, sW / 2f, zS - sT / 2f, zS + sT / 2f, 4f),
                                    MathF.Max(rHo - 2f - sx, sx - (rT + 1.5f)));
            float hub = RotKit.Annulus(p, rHi, rHo, hz0, hz0 + hD, 2f);
            float frame = RotKit.SMin(spoke, hub, fil);
            body = RotKit.SMin(body, frame, fil);

            // Keep the flow side of the bellmouth clear, drill the mounts, no bulge past the shell.
            float cove = MathF.Max(MathF.Max(r - cr, z - cz), Rb - dc);
            body = MathF.Max(body, -cove);
            body = MathF.Max(body, -hole);
            body = MathF.Max(body, MathF.Max(r - Ro, -z));
            return body;
        }

        Sdf.Stage(s.PartId, "housing implicit");
        return Sdf.Vox(lib, Field, new Vector3(-Ro - 1, -Ro - 1, -1), new Vector3(Ro + 1, Ro + 1, D + 1));
    }
}
