using System.Numerics;
using PicoGK;

namespace PicoGKCatalog;

/// Turbo intake distributor concept (PET 107-20 pos 1 with the pos 18/21
/// manifold branches), X along the crankshaft, Y across the banks, Z up;
/// z = 0 is the plane of the six head port faces. A pill-shaped plenum above
/// the engine centre is fed by a throttle-side neck at its front end
/// (x < 0, axis -X) and feeds three runners per bank that leave its flanks,
/// arc outboard and drop vertically onto lobed port flanges. The flow volume
/// is modelled first and its junctions filleted (bellmouth entries); the
/// walls are a uniform offset of it, filleted as one body with the flanges
/// before the flow volume is cut out again. Open at the six ports, the inlet
/// and the sensor boss; no sealed cavity.
public sealed class TurboIntakeTract : IPartGenerator
{
    public string Name => "turbo_intake_distributor";

    static Vector3 Cubic(Vector3 a, Vector3 b, Vector3 c, Vector3 d, float t)
    {
        float u = 1f - t;
        return u * u * u * a + 3f * u * u * t * b + 3f * u * t * t * c + t * t * t * d;
    }

    public Voxels Build(Library lib, PartSpec s)
    {
        float pitch = s.P("cylinder_pitch_mm"), yPort = s.P("bank_port_y_mm");
        float Lp = s.P("plenum_length_mm") / 2f, Wp = s.P("plenum_width_mm") / 2f, Hp = s.P("plenum_height_mm") / 2f;
        float zp = s.P("plenum_centre_z_mm"), nExp = s.P("plenum_shape_exponent");
        float rr = s.P("runner_bore_mm") / 2f, w = s.P("wall_mm");
        float fT = s.P("port_flange_thickness_mm"), fRim = s.P("port_flange_rim_mm");
        float studR = s.P("stud_hole_mm") / 2f, bossR = s.P("stud_boss_radius_mm");
        float ri = s.P("inlet_bore_mm") / 2f, neck = s.P("inlet_neck_length_mm");
        float iT = s.P("inlet_flange_thickness_mm"), iBolt = s.P("inlet_bolt_circle_mm") / 2f;
        int nInBolt = s.N("inlet_bolt_count");
        float sensR = s.P("sensor_boss_radius_mm"), sensBore = s.P("sensor_bore_mm") / 2f, sensX = s.P("sensor_boss_x_mm");
        float filIn = s.P("inner_fillet_mm"), fil = s.P("fillet_mm");
        float xIn = -Lp - neck;                       // inlet flange face

        float[] xs = { -pitch, 0f, pitch };
        Sdf.Stage(s.PartId, "flow volume");
        // Plenum: superellipsoid along X.
        Vector3 cP = new(0, 0, zp), rP = new(Lp, Wp, Hp);
        Voxels flow = Sdf.Vox(lib, p => Sdf.SuperEllipsoid(p, cP, rP, nExp),
            new Vector3(-Lp - 2f, -Wp - 2f, zp - Hp - 2f), new Vector3(Lp + 2f, Wp + 2f, zp + Hp + 2f));
        Lattice runners = new(lib), ext = new(lib);
        foreach (float sb in new[] { -1f, 1f })
            foreach (float x in xs)
            {
                Vector3 a = new(x, sb * 0.3f * Wp, zp), b = new(x, sb * (Wp + 0.55f * (yPort - Wp)), zp);
                Vector3 c = new(x, sb * yPort, 0.55f * zp), d = new(x, sb * yPort, 0f);
                List<Vector3> path = new();
                for (int i = 0; i <= 48; i++) path.Add(Cubic(a, b, c, d, i / 48f));
                FlowKit.Sweep(runners, path, _ => rr, true);
                ext.AddBeam(new Vector3(x, sb * yPort, 12f), new Vector3(x, sb * yPort, -4f), rr, rr, false);
            }
        // Inlet neck: straight along -X from inside the plenum to the flange face.
        runners.AddBeam(new Vector3(-Lp + 40f, 0, zp), new Vector3(-Lp + 10f, 0, zp), ri * 0.9f, ri, true);
        runners.AddBeam(new Vector3(-Lp + 10f, 0, zp), new Vector3(xIn, 0, zp), ri, ri, false);
        ext.AddBeam(new Vector3(xIn + 15f, 0, zp), new Vector3(xIn - 4f, 0, zp), ri, ri, false);
        // Sensor boss bore (pressure transmitter pos 14 context) on the plenum top.
        ext.AddBeam(new Vector3(sensX, 0, zp), new Vector3(sensX, 0, zp + Hp + w + 14f), sensBore, sensBore, false);
        flow.BoolAdd(new Voxels(runners));
        flow.Fillet(filIn);

        Sdf.Stage(s.PartId, "walls");
        Voxels body = flow.voxOffset(w);

        Sdf.Stage(s.PartId, "flanges");
        // Port flanges: one lobed bar per bank, studs between and beyond the ports.
        float rf = rr + w + fRim;
        List<float> studX = new() { -1.5f * pitch, -0.5f * pitch, 0.5f * pitch, 1.5f * pitch };
        studX[0] = -pitch - rf - bossR + 4f; studX[3] = pitch + rf + bossR - 4f;
        foreach (float sb in new[] { -1f, 1f })
        {
            float yc = sb * yPort;
            float Bar(Vector2 q)
            {
                float d = float.MaxValue;
                foreach (float x in xs) d = FlowKit.Smin(d, (q - new Vector2(x, yc)).Length() - rf, 10f);
                foreach (float x in studX) d = FlowKit.Smin(d, (q - new Vector2(x, yc)).Length() - bossR - 2f, 10f);
                // continuous web along the port row so every stud lobe is part of one bar
                float web = FlowKit.Seg2(q, new Vector2(studX[0], yc), new Vector2(studX[3], yc)) - (bossR + 1f);
                return FlowKit.Smin(d, web, 12f);
            }
            float hx = studX[3] + bossR + 4f, hy = rf + 4f;
            body.BoolAdd(Sdf.Vox(lib, p => FlowKit.Extrude(Bar(new(p.X, p.Y)), p.Z, 0f, fT, 1.5f),
                new(-hx, yc - hy, -1f), new(hx, yc + hy, fT + 1f)));
        }
        // Inlet flange: round with bolt lobes, normal -X.
        float rIF = ri + w + 6f;
        float Inlet2(Vector2 q)
        {
            float d = q.Length() - rIF;
            for (int k = 0; k < nInBolt; k++)
            {
                float a = (k + 0.5f) * 2f * MathF.PI / nInBolt;
                d = FlowKit.Smin(d, (q - iBolt * new Vector2(MathF.Cos(a), MathF.Sin(a))).Length() - bossR, 8f);
            }
            return d;
        }
        float rIx = iBolt + bossR + 2f;
        body.BoolAdd(Sdf.Vox(lib, p => FlowKit.Extrude(Inlet2(new(p.Y, p.Z - zp)), p.X, xIn, xIn + iT, 1.5f),
            new(xIn - 1f, -rIx, zp - rIx), new(xIn + iT + 1f, rIx, zp + rIx)));
        // Sensor boss.
        Lattice boss = new(lib);
        boss.AddBeam(new Vector3(sensX, 0, zp + Hp - 6f), new Vector3(sensX, 0, zp + Hp + w + 10f), sensR, sensR, false);
        body.BoolAdd(new Voxels(boss));

        Sdf.Stage(s.PartId, "fillet");
        body.Fillet(fil);

        Sdf.Stage(s.PartId, "cut flow");
        body.BoolSubtract(flow);
        body.BoolSubtract(new Voxels(ext));
        Lattice holes = new(lib);
        foreach (float sb in new[] { -1f, 1f })
            foreach (float x in studX)
            {
                holes.AddBeam(new Vector3(x, sb * yPort, -2f), new Vector3(x, sb * yPort, fT + 1f), studR, studR, false);
                holes.AddBeam(new Vector3(x, sb * yPort, fT), new Vector3(x, sb * yPort, fT + 40f), bossR - 0.5f, bossR - 0.5f, false);
            }
        for (int k = 0; k < nInBolt; k++)
        {
            float a = (k + 0.5f) * 2f * MathF.PI / nInBolt;
            Vector3 c = new(0, iBolt * MathF.Cos(a), zp + iBolt * MathF.Sin(a));
            holes.AddBeam(c + new Vector3(xIn - 2f, 0, 0), c + new Vector3(xIn + iT + 1f, 0, 0), studR, studR, false);
            holes.AddBeam(c + new Vector3(xIn + iT, 0, 0), c + new Vector3(xIn + iT + 30f, 0, 0), bossR - 0.5f, bossR - 0.5f, false);
        }
        body.BoolSubtract(new Voxels(holes));
        // Tight trim box: Trim intersects with a box solid, whose surface costs memory.
        BBox3 bb = body.oCalculateBoundingBox();
        body.Trim(new BBox3(new Vector3(xIn, bb.vecMin.Y - 1f, 0f), new Vector3(bb.vecMax.X + 1f, bb.vecMax.Y + 1f, bb.vecMax.Z + 1f)));
        return body;
    }
}
