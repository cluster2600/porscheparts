using System.Numerics;
using PicoGK;

namespace PicoGKCatalog;

/// 993 Turbo engine carrier, shape study only (safety critical, interfaces
/// unmeasured). Axis X along the car's width, Z up. A bowed, closed
/// rounded-box beam (two pressed half shells, seam flanges top and bottom)
/// blends through gusset-like fillets into two vertical end bosses with
/// hypothetical bores and top recesses. Two round openings with formed rims
/// pierce both side walls and vent the closed section; two drain holes at
/// the bottom. A flat central pad marks where the engine bracket sits: the
/// four PET M10 sites are NOT drawn because their positions are unmeasured.
public sealed class EngineCarrier : IPartGenerator
{
    public string Name => "engine_carrier_box_beam";

    public Voxels Build(Library lib, PartSpec s)
    {
        float Lo = s.P("overall_length_mm"), Hb = s.P("overall_height_mm"), Db = s.P("boss_diameter_mm");
        float bore = s.P("boss_bore_mm") / 2f, recR = s.P("boss_recess_diameter_mm") / 2f, recD = s.P("boss_recess_depth_mm");
        float Wb = s.P("beam_width_mm"), hE = s.P("beam_height_end_mm"), hM = s.P("beam_height_mid_mm");
        float bow = s.P("beam_bow_mm"), wall = s.P("wall_mm"), rc = s.P("section_corner_radius_mm");
        float tFl = s.P("seam_flange_thickness_mm"), hFl = s.P("seam_flange_height_mm");
        float kG = s.P("gusset_blend_mm");
        float xo = s.P("opening_offset_mm"), ro = s.P("opening_diameter_mm") / 2f, rimW = s.P("opening_rim_width_mm"), rimH = s.P("opening_rim_height_mm");
        float padL = s.P("pad_length_mm"), padW = s.P("pad_width_mm"), padT = s.P("pad_raise_mm");
        float xd = s.P("drain_offset_mm"), rd = s.P("drain_diameter_mm") / 2f;

        float Rb = Db / 2f, xc = Lo / 2f - Rb;
        float H(float x) { float u = Math.Clamp(x / xc, -1f, 1f); return hE + (hM - hE) * (1f - u * u); }
        float Zc(float x) { float u = Math.Clamp(x / xc, -1f, 1f); return bow * (1f - u * u); }
        float cavLim = xc - Rb - 6f;
        float padTop = Zc(0) + hM / 2f + padT;

        float Field(Vector3 p)
        {
            float x = p.X, y = p.Y, z = p.Z;
            float h = H(x), zc = Zc(x);
            float dSec = BodyKit.RoundRect(y, z - zc, Wb / 2f, h / 2f, rc);
            float dBeam = MathF.Max(dSec, MathF.Abs(x) - xc);
            float dBoss = MathF.Min(BodyKit.RoundCylZ(p, -xc, 0, Rb, -Hb / 2f, Hb / 2f, 3f),
                                    BodyKit.RoundCylZ(p, xc, 0, Rb, -Hb / 2f, Hb / 2f, 3f));
            float outer = BodyKit.SMin(dBeam, dBoss, kG);

            // seam flanges: plate in the XZ mid-plane, standing proud of the section
            float dFl = MathF.Max(MathF.Max(MathF.Abs(y) - tFl / 2f, MathF.Abs(z - zc) - (h / 2f + hFl)), MathF.Abs(x) - xc);
            outer = BodyKit.SMin(outer, dFl, 1.5f);

            // central bracket pad (flat top), blended into the beam
            float zPadC = 0.5f * (padTop + Zc(0) + hM / 2f - wall);
            float dPad = Sdf.RoundBox(p, new Vector3(0, 0, zPadC), new Vector3(padL / 2f, padW / 2f, 0.5f * (padTop - (Zc(0) + hM / 2f - wall))), 3f);
            outer = BodyKit.SMin(outer, dPad, 6f);

            // formed rims around the two side openings
            for (int sgn = -1; sgn <= 1; sgn += 2)
            {
                float ox = sgn * xo, oz = Zc(ox);
                float rho = MathF.Sqrt((x - ox) * (x - ox) + (z - oz) * (z - oz));
                float dRim = BodyKit.RoundI(rho - (ro + rimW), MathF.Abs(y) - (Wb / 2f + rimH), 1f);
                outer = BodyKit.SMin(outer, dRim, 1.5f);
            }

            // closed-section cavity, stopping short of the bosses
            float dCav = BodyKit.RoundI(BodyKit.RoundRect(y, z - zc, Wb / 2f - wall, h / 2f - wall, MathF.Max(rc - wall, 1f)),
                                        MathF.Abs(x) - cavLim, 8f);
            float d = MathF.Max(outer, -dCav);

            // holes: side openings, boss bores, boss recesses, drains
            float holes = float.MaxValue;
            for (int sgn = -1; sgn <= 1; sgn += 2)
            {
                float ox = sgn * xo, oz = Zc(ox);
                float rho = MathF.Sqrt((x - ox) * (x - ox) + (z - oz) * (z - oz));
                holes = MathF.Min(holes, rho - ro);
                float bx = sgn * xc;
                float rb = MathF.Sqrt((x - bx) * (x - bx) + y * y);
                holes = MathF.Min(holes, rb - bore);
                holes = MathF.Min(holes, MathF.Max(rb - recR, Hb / 2f - recD - z));
                float dx = sgn * xd;
                float rdd = MathF.Sqrt((x - dx) * (x - dx) + y * y);
                holes = MathF.Min(holes, MathF.Max(rdd - rd, z - Zc(dx)));
            }
            return BodyKit.SMax(d, -holes, 0.8f);
        }

        Sdf.Stage(s.PartId, "render");
        Vector3 lo = new(-Lo / 2f - 1f, -Db / 2f - 1f, -Hb / 2f - 1f), hi = new(Lo / 2f + 1f, Db / 2f + 1f, Hb / 2f + 1f);
        return Sdf.Vox(lib, Field, lo, hi);
    }
}
