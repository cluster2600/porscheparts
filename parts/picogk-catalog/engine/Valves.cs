using System.Numerics;
using PicoGK;

namespace PicoGKCatalog;

/// Poppet valve profile in (r, z), face at z = 0, tip at z = L: flat face,
/// cylindrical margin, 45 degree seat, tulip underhead (one concave radius
/// tangent to the seat top and to the stem), stem, keeper grooves and tip
/// chamfer.
public readonly record struct ValveDims(
    float HeadR, float Margin, float Seat, float StemR, float Length,
    int Grooves, float GrooveR, float GroovePitch, float GrooveFromTip, float TipChamfer)
{
    public static ValveDims From(PartSpec s, string prefix = "") => new(
        s.P(prefix + "head_diameter_mm") / 2f, s.P("head_margin_mm"), s.P("seat_radial_width_mm"),
        s.P("stem_diameter_mm") / 2f, s.P(prefix + "overall_length_mm"),
        s.N("keeper_groove_count"), s.P("keeper_groove_radius_mm"), s.P("keeper_groove_pitch_mm"),
        s.P("keeper_groove_from_tip_mm"), s.P("tip_chamfer_mm"));

    public float TulipRadius => HeadR - Seat - StemR;
    public float NeckZ => Margin + Seat + TulipRadius;
}

public static class ValveShape
{
    public static float Profile(float r, float z, in ValveDims v)
    {
        float rSeat = v.HeadR - v.Seat, zSeat = v.Margin + v.Seat;
        float Rf = v.TulipRadius, zf = v.NeckZ;
        float face = Es.SMax(-z, r - v.HeadR, 0.4f);   // softened face edge
        float lower = MathF.Max(MathF.Max(face, z - zSeat), (r + (z - v.Margin) - v.HeadR) * Es.InvSqrt2);
        float tulip = MathF.Max(MathF.Max(r - rSeat, v.Margin - z), MathF.Max(z - zf, Rf - Es.Len2(r - rSeat, z - zf)));
        float stem = MathF.Max(MathF.Max(r - v.StemR, z - v.Length), v.Margin - z);
        stem = MathF.Max(stem, (r + z - (v.Length + v.StemR - v.TipChamfer)) * Es.InvSqrt2);
        float d = MathF.Min(MathF.Min(lower, tulip), stem);
        for (int i = 0; i < v.Grooves; i++)
        {
            float zg = v.Length - v.GrooveFromTip - i * v.GroovePitch;
            d = MathF.Max(d, -(Es.Len2(r - v.StemR - 0.2f * v.GrooveR, z - zg) - v.GrooveR));
        }
        return d;
    }

    public static float At(Vector3 p, float cx, in ValveDims v) => Profile(Es.Len2(p.X - cx, p.Y), p.Z, v);
}

/// One solid poppet valve (F1 intake proxy).
public sealed class SolidValve : IPartGenerator
{
    public string Name => "poppet_valve";

    public Voxels Build(Library lib, PartSpec s)
    {
        ValveDims v = ValveDims.From(s);
        Sdf.Stage(s.PartId, "valve field");
        return Sdf.Vox(lib, p => ValveShape.At(p, 0f, v),
            new Vector3(-v.HeadR - 1f, -v.HeadR - 1f, -1f), new Vector3(v.HeadR + 1f, v.HeadR + 1f, v.Length + 1f));
    }
}

/// Two poppet valves of one record side by side (e.g. Carrera and Turbo
/// exhaust), tied at the face by a small display/print bridge so the file is
/// one body; the bridge is not part of either valve.
public sealed class ValvePair : IPartGenerator
{
    public string Name => "poppet_valve_pair";

    public Voxels Build(Library lib, PartSpec s)
    {
        ValveDims a = ValveDims.From(s, "a_"), b = ValveDims.From(s, "b_");
        float gap = s.P("display_gap_mm"), tieW = s.P("display_tie_width_mm") / 2f;
        float ca = -(a.HeadR + gap / 2f), cb = b.HeadR + gap / 2f;
        float tieH = MathF.Min(a.Margin, b.Margin) * 0.8f;

        float F(Vector3 p)
        {
            float d = MathF.Min(ValveShape.At(p, ca, a), ValveShape.At(p, cb, b));
            float tie = Sdf.RoundBox(p, new Vector3(0f, 0f, tieH / 2f), new Vector3(gap / 2f + 2f, tieW, tieH / 2f), 0.3f);
            return Es.SMin(d, tie, 0.8f);
        }

        Sdf.Stage(s.PartId, "valve pair field");
        float R = MathF.Max(a.HeadR, b.HeadR), Lmax = MathF.Max(a.Length, b.Length);
        return Sdf.Vox(lib, F, new Vector3(ca - a.HeadR - 1f, -R - 1f, -1f), new Vector3(cb + b.HeadR + 1f, R + 1f, Lmax + 1f));
    }
}

/// Hollow LPBF valve: conformal head cavity (constant wall under the tulip,
/// minimum ligament over the face) split by radial internal ribs, and an
/// axial stem bore open at the tip so every rib sector drains through the
/// bore. Exterior as the solid valve.
public sealed class HollowValve : IPartGenerator
{
    public string Name => "poppet_valve_hollow";

    public Voxels Build(Library lib, PartSpec s)
    {
        ValveDims v = ValveDims.From(s);
        float wall = s.P("head_wall_mm"), lig = s.P("head_cavity_bottom_z_mm");
        float rCav = s.P("head_cavity_bottom_radius_mm"), zCavTop = s.P("head_cavity_top_z_mm");
        float rBore = s.P("hollow_bore_diameter_mm") / 2f;
        float ribT = s.P("internal_web_thickness_mm") / 2f;
        int ribs = s.N("internal_radial_web_count");
        var normals = new List<Vector2>();
        for (int i = 0; i < ribs / 2; i++)   // each slab through the axis gives two radial webs
        {
            float a = i * MathF.PI / (ribs / 2);
            normals.Add(new Vector2(-MathF.Sin(a), MathF.Cos(a)));
        }

        float F(Vector3 p)
        {
            float r = Es.Len2(p.X, p.Y);
            float d = ValveShape.Profile(r, p.Z, v);
            float cav = Es.SMax(Es.SMax(d + wall, lig - p.Z, 1f), r - rCav, 2f);
            cav = MathF.Max(cav, p.Z - zCavTop);
            float rib = float.MaxValue;
            foreach (Vector2 n in normals) rib = MathF.Min(rib, MathF.Abs(p.X * n.X + p.Y * n.Y) - ribT);
            cav = Es.SMax(cav, -rib, 0.4f);
            float bore = MathF.Max(r - rBore, lig + 0.8f - p.Z);
            return MathF.Max(d, -MathF.Min(cav, bore));
        }

        Sdf.Stage(s.PartId, "hollow valve field");
        return Sdf.Vox(lib, F, new Vector3(-v.HeadR - 1f, -v.HeadR - 1f, -1f), new Vector3(v.HeadR + 1f, v.HeadR + 1f, v.Length + 1f));
    }
}
