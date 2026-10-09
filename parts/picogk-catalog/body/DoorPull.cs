using System.Numerics;
using PicoGK;

namespace PicoGKCatalog;

/// Interior door pull handle. X along the handle, Z out of the door panel
/// (door surface at z = 0), Y across the grip. An elliptical grip section,
/// fuller at mid span, is swept along a cubic Bezier arch and flows into two
/// round mounting bosses; finger scallops on the underside; blind pilot
/// bores in the bosses, open at the door face.
public sealed class DoorPull : IPartGenerator
{
    public string Name => "door_pull_organic";

    static Vector3 Cubic(Vector3 a, Vector3 b, Vector3 c, Vector3 d, float t)
    {
        float u = 1 - t;
        return u * u * u * a + 3 * u * u * t * b + 3 * u * t * t * c + t * t * t * d;
    }

    public Voxels Build(Library lib, PartSpec s)
    {
        float L = s.P("length_mm"), gw = s.P("grip_width_mm"), gt = s.P("grip_thickness_mm"), Ht = s.P("height_mm");
        float bossD = s.P("boss_diameter_mm"), bossH = s.P("boss_height_mm");
        float pilotD = s.P("pilot_bore_mm"), pilotH = s.P("pilot_depth_mm");
        float swell = s.P("grip_swell_ratio");
        int nFing = s.N("finger_scallop_count");
        float fR = s.P("finger_scallop_radius_mm"), fDepth = s.P("finger_scallop_depth_mm"), fPitch = s.P("finger_scallop_pitch_mm");
        float blend = s.P("boss_blend_mm");

        float xb = L / 2f - bossD / 2f;
        float rMid = gt / 2f;                                  // in-plane semi-axis at mid span
        float rEnd = gt / 2f / (1f + swell);
        float ySc = (gt / 2f) / (gw / 2f);                     // y scaling that makes the section circular
        // arch: top of the grip at mid span reaches Ht
        float zEnd = bossH * 0.6f;
        float zTopC = Ht - rMid;                               // centreline height at mid span
        float zCtrl = (zTopC - 0.25f * zEnd) / 0.75f;
        Vector3 P0 = new(-xb, 0, zEnd), P1 = new(-xb * 0.85f, 0, zCtrl), P2 = new(xb * 0.85f, 0, zCtrl), P3 = new(xb, 0, zEnd);
        const int N = 64;
        var pts = new Vector3[N + 1];
        var rad = new float[N + 1];
        for (int i = 0; i <= N; i++)
        {
            float t = i / (float)N;
            pts[i] = Cubic(P0, P1, P2, P3, t);
            rad[i] = rEnd + (rMid - rEnd) * MathF.Sin(MathF.PI * t);
        }
        // finger scallop centres, following the local underside of the arch
        var fing = new Vector2[nFing];
        for (int k = 0; k < nFing; k++)
        {
            float fx = (k - (nFing - 1) / 2f) * fPitch;
            int best = 0;
            for (int i = 1; i <= N; i++) if (MathF.Abs(pts[i].X - fx) < MathF.Abs(pts[best].X - fx)) best = i;
            fing[k] = new Vector2(fx, pts[best].Z - rad[best] - fR + fDepth);
        }

        float Field(Vector3 p)
        {
            Vector3 q = new(p.X, p.Y * ySc, p.Z);
            float grip = float.MaxValue;
            for (int i = 0; i < N; i++)
            {
                Vector3 a = pts[i], b = pts[i + 1], ab = b - a, aq = q - a;
                float h = Math.Clamp(Vector3.Dot(aq, ab) / Vector3.Dot(ab, ab), 0f, 1f);
                float r = rad[i] + (rad[i + 1] - rad[i]) * h;
                grip = MathF.Min(grip, (aq - ab * h).Length() - r);
            }
            float boss = MathF.Min(BodyKit.RoundCylZ(p, -xb, 0, bossD / 2f, -2f, bossH, 2.5f),
                                   BodyKit.RoundCylZ(p, xb, 0, bossD / 2f, -2f, bossH, 2.5f));
            float d = BodyKit.SMin(grip, boss, blend);

            // finger scallops on the underside of the grip (cylinders along Y)
            for (int k = 0; k < nFing; k++)
            {
                float dc = new Vector2(p.X - fing[k].X, p.Z - fing[k].Y).Length() - fR;
                d = BodyKit.SMax(d, -dc, 2f);
            }
            // flat door face, pilot bores
            d = MathF.Max(d, -p.Z);
            for (int sgn = -1; sgn <= 1; sgn += 2)
            {
                float rho = new Vector2(p.X - sgn * xb, p.Y).Length();
                d = MathF.Max(d, -MathF.Max(rho - pilotD / 2f, p.Z - pilotH));
            }
            return d;
        }

        Sdf.Stage(s.PartId, "render");
        Vector3 lo = new(-L / 2f - 2f, -gw / 2f - 3f, -1f), hi = new(L / 2f + 2f, gw / 2f + 3f, Ht + 2f);
        return Sdf.Vox(lib, Field, lo, hi);
    }
}
