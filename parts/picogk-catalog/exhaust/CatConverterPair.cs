using System.Numerics;
using PicoGK;

namespace PicoGKCatalog;

/// Catalytic converter pair (PET 202-15 pos 14/15), flow axis X: inlet at
/// x = 0, outlet at x = total length. Each converter is one revolved flow
/// volume swept along a centreline that S-bends outboard in the inlet pipe and
/// runs straight through the can: pipe, smooth diffuser cone, can with two
/// rolled-in stiffening beads, smooth nozzle cone, outlet pipe. The wall is a
/// uniform offset of the flow volume, so the beads stay inside the can
/// diameter. A spherical ball-joint collar sits on the inlet pipe, a lobed
/// two-bolt flange on the outlet and an oxygen-sensor boss on the inlet cone
/// (outboard). The substrate is a separate insert and is not modelled: each
/// can is hollow and open at both ends. The pair stands side by side, joined
/// by two organic display ties that are not part of either converter.
public sealed class CatConverterPair : IPartGenerator
{
    public string Name => "catalytic_converter_pair";

    static Vector3 Cubic(Vector3 a, Vector3 b, Vector3 c, Vector3 d, float t)
    {
        float u = 1f - t;
        return u * u * u * a + 3f * u * u * t * b + 3f * u * t * t * c + t * t * t * d;
    }

    public Voxels Build(Library lib, PartSpec s)
    {
        float Rb = s.P("body_diameter_mm") / 2f, Lb = s.P("body_length_mm");
        float rpo = s.P("pipe_outer_diameter_mm") / 2f, w = s.P("wall_mm");
        float Lci = s.P("inlet_cone_length_mm"), Lco = s.P("outlet_cone_length_mm");
        float Lin = s.P("inlet_pipe_length_mm"), offY = s.P("inlet_offset_y_mm"), Lout = s.P("outlet_pipe_length_mm");
        int nBead = s.N("bead_count");
        float bD = s.P("bead_depth_mm"), bW = s.P("bead_width_mm");
        float ballR = s.P("ball_collar_radius_mm"), ballX = s.P("ball_collar_x_mm");
        float oR = s.P("outlet_flange_radius_mm"), oT = s.P("outlet_flange_thickness_mm"), oB = s.P("outlet_bolt_offset_mm");
        float boltR = s.P("bolt_hole_diameter_mm") / 2f, bossR = s.P("bolt_boss_radius_mm");
        float o2R = s.P("o2_boss_radius_mm"), o2Bore = s.P("o2_bore_mm") / 2f, o2L = s.P("o2_boss_length_mm");
        float gap = s.P("pair_spacing_mm"), tieR = s.P("tie_radius_mm"), fil = s.P("fillet_mm");

        float rp = rpo - w, Rf = Rb - w;              // flow radii
        float x1 = Lin, x2 = x1 + Lci, x3 = x2 + Lb, x4 = x3 + Lco, xEnd = x4 + Lout;
        float RFlow(float x)
        {
            if (x <= x1) return rp;
            if (x <= x2) return rp + (Rf - rp) * FlowKit.Smooth((x - x1) / Lci);
            if (x <= x3)
            {
                float r = Rf;
                for (int k = 0; k < nBead; k++)
                {
                    float xb = x2 + Lb * (k + 1f) / (nBead + 1f);
                    float u = (x - xb) / (bW / 2f);
                    if (MathF.Abs(u) < 1f) r -= bD * 0.5f * (1f + MathF.Cos(MathF.PI * u));
                }
                return r;
            }
            if (x <= x4) return Rf + (rp - Rf) * FlowKit.Smooth((x - x3) / Lco);
            return rp;
        }

        // Centreline of one converter, flow axis along +X; the inlet pipe S-bends by side*offY.
        List<Vector3> Path(float y0, float side)
        {
            List<Vector3> p = new() { new(-4f, y0 + side * offY, 0f) };
            Vector3 a = new(0f, y0 + side * offY, 0f), d = new(x1, y0, 0f);
            for (int i = 0; i <= 40; i++) p.Add(Cubic(a, a + new Vector3(0.45f * x1, 0, 0), d - new Vector3(0.45f * x1, 0, 0), d, i / 40f));
            // Straight run: knots only where the radius changes (each fat beam
            // voxelizes its whole box, so constant stretches are one beam).
            List<float> xk = new();
            for (float x = x1 + 2.5f; x <= x2; x += 2.5f) xk.Add(x);
            for (int k = 0; k < nBead; k++)
            {
                float xb = x2 + Lb * (k + 1f) / (nBead + 1f);
                for (float x = xb - bW / 2f; x <= xb + bW / 2f + 0.01f; x += 1f) xk.Add(x);
            }
            for (float x = x3; x <= x4; x += 2.5f) xk.Add(x);
            xk.Add(x4);
            xk.Add(xEnd);
            foreach (float x in xk.Distinct().OrderBy(v => v)) p.Add(new Vector3(x, y0, 0f));
            p.Add(new Vector3(xEnd + 4f, y0, 0f));
            return p;
        }

        Sdf.Stage(s.PartId, "flow volume");
        // One lattice per converter: a lattice voxelizes over its whole bounding box.
        Voxels? flow = null;
        List<(float y0, float side, List<Vector3> path)> units = new();
        foreach (float side in new[] { 1f, -1f })
        {
            float y0 = side * gap / 2f;
            List<Vector3> path = Path(y0, side);
            Lattice flowLat = new(lib);
            FlowKit.Sweep(flowLat, path, i => RFlow(path[i].X), true);
            Voxels one = new(flowLat);
            if (flow is null) flow = one; else flow.BoolAdd(one);
            units.Add((y0, side, path));
        }

        Sdf.Stage(s.PartId, "walls");
        Voxels body = flow!.voxOffset(w);
        Lattice extra = new(lib);
        foreach (var (y0, side, path) in units)
        {
            // Spherical ball-joint collar on the inlet pipe: a sphere of radius ballR
            // around the pipe axis leaves a spherical band on the pipe.
            int kb = path.FindIndex(q => q.X >= ballX);
            Vector3 cb = path[kb], tb = Vector3.Normalize(path[kb + 1] - path[kb - 1]);
            extra.AddBeam(cb - tb * 0.5f, cb + tb * 0.5f, ballR, ballR, true);
            // Oxygen-sensor boss on the inlet cone, outboard.
            float xo = x1 + 0.5f * Lci;
            Vector3 co = new(xo, y0, 0f), dir = new(0, side, 0);
            extra.AddBeam(co + dir * (RFlow(xo) - 4f), co + dir * (RFlow(xo) + w + o2L), o2R, o2R, false);
        }
        // Display ties between the two cans.
        foreach (float xt in new[] { x2 + 0.25f * Lb, x2 + 0.75f * Lb })
        {
            Vector3 pa = new(xt, gap / 2f, 0f), pb = new(xt, -gap / 2f, 0f), mid = new(xt, 0f, -0.15f * Rb);
            extra.AddBeam(pa, mid, tieR, tieR * 0.8f, true);
            extra.AddBeam(mid, pb, tieR * 0.8f, tieR, true);
        }
        body.BoolAdd(new Voxels(extra));

        Sdf.Stage(s.PartId, "flanges");
        float Out2(Vector2 q) => FlowKit.Smin(q.Length() - oR,
            MathF.Min((q - new Vector2(-oB, 0)).Length(), (q - new Vector2(oB, 0)).Length()) - bossR, 10f);
        foreach (var (y0, _, _) in units)
        {
            float ox = oB + bossR + 2f;
            body.BoolAdd(Sdf.Vox(lib, p => FlowKit.Extrude(Out2(new(p.Y - y0, p.Z)), p.X, xEnd - oT, xEnd, 1.2f),
                new(xEnd - oT - 1f, y0 - ox, -oR - 2f), new(xEnd + 1f, y0 + ox, oR + 2f)));
        }

        Sdf.Stage(s.PartId, "fillet");
        body.Fillet(fil);

        Sdf.Stage(s.PartId, "cut flow");
        body.BoolSubtract(flow);
        Lattice holes = new(lib);
        foreach (var (y0, side, _) in units)
        {
            float xo = x1 + 0.5f * Lci;
            Vector3 co = new(xo, y0, 0f), dir = new(0, side, 0);
            holes.AddBeam(co, co + dir * (RFlow(xo) + w + o2L + 2f), o2Bore, o2Bore, false);
            foreach (float dy in new[] { -oB, oB })
            {
                Vector3 c = new(xEnd, y0 + dy, 0f);
                holes.AddBeam(c + new Vector3(-oT - 1f, 0, 0), c + new Vector3(2f, 0, 0), boltR, boltR, false);
                holes.AddBeam(c + new Vector3(-oT - 30f, 0, 0), c + new Vector3(-oT, 0, 0), bossR - 0.5f, bossR - 0.5f, false);
            }
        }
        body.BoolSubtract(new Voxels(holes));
        // Tight trim box: Trim intersects with a box solid, whose surface costs memory.
        BBox3 bb = body.oCalculateBoundingBox();
        body.Trim(new BBox3(new Vector3(0f, bb.vecMin.Y - 1f, bb.vecMin.Z - 1f), new Vector3(xEnd, bb.vecMax.Y + 1f, bb.vecMax.Z + 1f)));
        return body;
    }
}
