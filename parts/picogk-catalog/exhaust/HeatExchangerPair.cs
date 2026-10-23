using System.Numerics;
using PicoGK;

namespace PicoGKCatalog;

/// Turbo exhaust heat exchanger pair (PET 202-10 pos 1/2), X along the
/// crankshaft (rear +X), Y across, Z up; z = 0 is the head-side face of the
/// port flanges. Per bank, three primaries drop from per-port lobed flanges,
/// fan out into lateral lanes so they pass each other clear, and converge
/// into a collector cone; the collector runs rearward and S-bends outboard
/// and upward to a lobed two-bolt outlet flange (turbine side, normal +X).
/// The merge and the front of the collector sit inside a bulging heater
/// jacket, open at both ends for the heating air and tied to the gas tubes by
/// staggered pin fins, so the air gap is one connected, drained channel. Gas
/// tubes and flanges are filleted as one solid before the jacket and pins are
/// added and the bores are cut. The two mirrored units stand side by side,
/// joined at their port flanges by two display ties that are not part of
/// either heat exchanger.
public sealed class HeatExchangerPair : IPartGenerator
{
    public string Name => "turbo_heat_exchanger_pair";

    static Vector3 Cubic(Vector3 a, Vector3 b, Vector3 c, Vector3 d, float t)
    {
        float u = 1f - t;
        return u * u * u * a + 3f * u * u * t * b + 3f * u * t * t * c + t * t * t * d;
    }

    public Voxels Build(Library lib, PartSpec s)
    {
        float pitch = s.P("cylinder_pitch_mm");
        float rp = s.P("primary_bore_mm") / 2f, rc = s.P("collector_bore_mm") / 2f, w = s.P("wall_mm");
        float lane = s.P("lane_offset_mm"), zLane = s.P("lane_z_mm"), xm = s.P("merge_x_mm"), zm = s.P("merge_z_mm");
        float xBend = s.P("collector_bend_start_x_mm"), xEnd = s.P("collector_end_x_mm");
        float outb = s.P("collector_outboard_mm"), rise = s.P("collector_rise_mm");
        float fT = s.P("port_flange_thickness_mm"), fRim = s.P("port_flange_rim_mm"), studOff = s.P("stud_offset_mm");
        float studR = s.P("stud_hole_mm") / 2f, bossR = s.P("stud_boss_radius_mm");
        float oR = s.P("outlet_flange_radius_mm"), oT = s.P("outlet_flange_thickness_mm"), oB = s.P("outlet_bolt_offset_mm");
        float xj0 = s.P("jacket_start_x_mm"), xj1 = s.P("jacket_end_x_mm");
        float rjF = s.P("jacket_front_radius_mm"), rjR = s.P("jacket_rear_radius_mm"), rjB = s.P("jacket_bulge_mm"), wj = s.P("jacket_wall_mm");
        float pinR = s.P("pin_diameter_mm") / 2f, pinPitch = s.P("pin_pitch_mm");
        int nPin = s.N("pins_per_ring");
        float yd = s.P("display_bank_offset_mm"), tieR = s.P("tie_radius_mm"), fil = s.P("fillet_mm");
        float rpo = rp + w, rco = rc + w, rf = rpo + fRim;
        float[] xs = { -pitch, 0f, pitch };
        float[] laneY = { -lane, 0f, lane }, laneZ = { zLane, zLane - 8f, zLane };
        Vector2[] ends = { new(-8f, -4f), new(0f, 7f), new(8f, -4f) };

        // One set of lattices per unit: a lattice voxelizes over its whole
        // bounding box, so a lattice spanning both units costs twice the memory.
        Lattice ties = new(lib);
        List<Voxels> gasV = new(), boreV = new(), jacketV = new(), pinV = new();
        List<(float y0, float side, List<Vector3> col)> units = new();
        foreach (float side in new[] { 1f, -1f })
        {
            float y0 = side * yd;
            Lattice gasOuter = new(lib), bores = new(lib), pins = new(lib), jOut = new(lib), jIn = new(lib), jLip = new(lib);
            Sdf.Stage(s.PartId, $"primaries {side}");
            for (int i = 0; i < 3; i++)
            {
                float ly = side * laneY[i], lz = laneZ[i], x = xs[i];
                List<Vector3> cps = new() { new(x, y0, 0f), new(x, y0 + 0.35f * ly, -45f) };
                if (i < 2) { cps.Add(new(x + 30f, y0 + ly, lz + 12f)); cps.Add(new(x + 75f, y0 + ly, lz)); }
                else cps.Add(new(x + 35f, y0 + ly, lz + 6f));
                cps.Add(new(xm - 80f, y0 + 0.8f * ly, lz));
                cps.Add(new(xm, y0 + side * ends[i].X, zm + ends[i].Y));
                List<Vector3> path = FlowKit.CatmullRom(cps, new Vector3(0, 0, -20f), new Vector3(20f, 0, 0), 24);
                FlowKit.Sweep(gasOuter, path, _ => rpo, false);
                List<Vector3> bore = new() { new(x, y0, 4f) };
                bore.AddRange(path);
                FlowKit.Sweep(bores, bore, _ => rp, false);
            }
            // Collector centreline: straight along +X, then a smooth S-bend outboard and up.
            List<Vector3> col = new();
            for (float x = xj0 - 10f; x < xBend; x += 8f) col.Add(new Vector3(x, y0, zm));   // coarse knots: fat jacket beams voxelize their whole box
            Vector3 a = new(xBend, y0, zm), d = new(xEnd, y0 + side * outb, zm + rise);
            float hb = 0.4f * (xEnd - xBend);
            for (int k = 0; k <= 30; k++) col.Add(Cubic(a, a + new Vector3(hb, 0, 0), d - new Vector3(hb, 0, 0), d, k / 30f));
            List<Vector3> colGas = col.Where(q => q.X >= xm - 35f).ToList();
            float RCol(Vector3 q) => q.X >= xm + 10f ? rc : 0.65f * rp + (rc - 0.65f * rp) * FlowKit.Smooth((q.X - (xm - 35f)) / 45f);
            FlowKit.Sweep(gasOuter, colGas, i => RCol(colGas[i]) + w, true);
            List<Vector3> colBore = new(colGas) { d + new Vector3(4f, 0, 0) };
            FlowKit.Sweep(bores, colBore, i => RCol(colBore[i]), false);

            // Heater jacket along the collector axis, open at both ends.
            List<Vector3> jac = col.Where(q => q.X >= xj0 && q.X <= xj1).ToList();
            float RJ(Vector3 q)
            {
                float u = Math.Clamp((q.X - xj0) / (xj1 - xj0), 0f, 1f);
                return rjF + (rjR - rjF) * FlowKit.Smooth(u) + rjB * MathF.Sin(MathF.PI * u);
            }
            FlowKit.Sweep(jOut, jac, i => RJ(jac[i]) + wj, true);
            List<Vector3> jacIn = new() { jac[0] - new Vector3(5f, 0, 0) };
            jacIn.AddRange(jac);
            Vector3 tj = Vector3.Normalize(jac[^1] - jac[^2]);
            jacIn.Add(jac[^1] + tj * 5f);
            FlowKit.Sweep(jIn, jacIn, i => RJ(jacIn[i]), true);
            // Rolled lips (torus rings) round both open ends of the jacket.
            foreach (Vector3 e in new[] { jac[0], jac[^1] })
            {
                Vector3 te = Vector3.Normalize(jac[^1] - jac[0]);
                Vector3 u1 = Vector3.Normalize(Vector3.Cross(te, Vector3.UnitZ)), u2 = Vector3.Cross(u1, te);
                float rl = RJ(e) + 0.5f * wj;
                const int nl = 96;
                for (int k = 0; k < nl; k++)
                {
                    float a0 = k * 2f * MathF.PI / nl, a1 = (k + 1) * 2f * MathF.PI / nl;
                    jLip.AddBeam(e + rl * (MathF.Cos(a0) * u1 + MathF.Sin(a0) * u2),
                                 e + rl * (MathF.Cos(a1) * u1 + MathF.Sin(a1) * u2), 0.5f * wj + 0.4f, 0.5f * wj + 0.4f, true);
                }
            }
            // Staggered pin fins from the gas tubes to the jacket.
            int ring = 0;
            for (float xp = xj0 + 12f; xp <= xj1 - 10f; xp += pinPitch, ring++)
            {
                int k = jac.FindIndex(q => q.X >= xp);
                if (k <= 0) continue;
                float f = (xp - jac[k - 1].X) / MathF.Max(jac[k].X - jac[k - 1].X, 1e-3f);
                Vector3 c = Vector3.Lerp(jac[k - 1], jac[k], f), t = Vector3.Normalize(jac[k] - jac[k - 1]);
                Vector3 e1 = Vector3.Normalize(Vector3.Cross(t, Vector3.UnitZ)), e2 = Vector3.Cross(e1, t);
                for (int m = 0; m < nPin; m++)
                {
                    float ang = (m + 0.5f * (ring % 2)) * 2f * MathF.PI / nPin;
                    Vector3 dir = MathF.Cos(ang) * e1 + MathF.Sin(ang) * e2;
                    pins.AddBeam(c + dir * 4f, c + dir * (RJ(c) + 0.5f * wj), pinR, pinR, true);
                }
            }
            units.Add((y0, side, col));
            Sdf.Stage(s.PartId, $"voxelize unit {side}");
            gasV.Add(new Voxels(gasOuter));
            boreV.Add(new Voxels(bores));
            Voxels jacket = new(jOut);
            jacket.BoolSubtract(new Voxels(jIn));
            jacket.BoolAdd(new Voxels(jLip));
            jacketV.Add(jacket);
            pinV.Add(new Voxels(pins));
        }
        // Display ties between the two banks' front and rear port flanges.
        foreach (float x in new[] { -pitch, pitch })
            ties.AddBeam(new Vector3(x, yd - rf + 3f, -fT + 1f), new Vector3(x, -yd + rf - 3f, -fT + 1f), tieR, tieR, true);

        Sdf.Stage(s.PartId, "gas body");
        Voxels body = gasV[0];
        body.BoolAdd(gasV[1]);
        body.BoolAdd(new Voxels(ties));

        Sdf.Stage(s.PartId, "flanges");
        float Port2(Vector2 q) => FlowKit.Smin(q.Length() - rf,
            MathF.Min((q - new Vector2(-studOff, 0)).Length(), (q - new Vector2(studOff, 0)).Length()) - bossR, 8f);
        float px = studOff + bossR + 2f;
        foreach (var (y0, side, col) in units)
        {
            foreach (float x in xs)
                body.BoolAdd(Sdf.Vox(lib, p => FlowKit.Extrude(Port2(new(p.X - x, p.Y - y0)), p.Z, -fT, 0f, 1.2f),
                    new(x - px, y0 - rf - 2f, -fT - 1f), new(x + px, y0 + rf + 2f, 1f)));
            Vector3 d = col[^1];
            float Out2(Vector2 q) => FlowKit.Smin(q.Length() - oR,
                MathF.Min((q - new Vector2(0, -oB)).Length(), (q - new Vector2(0, oB)).Length()) - bossR, 8f);
            float oz = oB + bossR + 2f;
            body.BoolAdd(Sdf.Vox(lib, p => FlowKit.Extrude(Out2(new(p.Y - d.Y, p.Z - d.Z)), p.X, xEnd - oT, xEnd, 1.2f),
                new(xEnd - oT - 1f, d.Y - oR - 2f, d.Z - oz), new(xEnd + 1f, d.Y + oR + 2f, d.Z + oz)));
        }

        Sdf.Stage(s.PartId, "fillet");
        body.Fillet(fil);

        Sdf.Stage(s.PartId, "jacket and pins");
        foreach (Voxels v in jacketV) body.BoolAdd(v);
        foreach (Voxels v in pinV) body.BoolAdd(v);

        Sdf.Stage(s.PartId, "bores");
        foreach (Voxels v in boreV) body.BoolSubtract(v);
        Lattice holes = new(lib);
        foreach (var (y0, _, col) in units)
        {
            foreach (float x in xs)
                foreach (float dx in new[] { -studOff, studOff })
                {
                    holes.AddBeam(new Vector3(x + dx, y0, 2f), new Vector3(x + dx, y0, -fT - 1f), studR, studR, false);
                    holes.AddBeam(new Vector3(x + dx, y0, -fT), new Vector3(x + dx, y0, -fT - 10f), bossR - 0.5f, bossR - 0.5f, false);
                }
            Vector3 d = col[^1];
            foreach (float dz in new[] { -oB, oB })
            {
                Vector3 c = new(xEnd, d.Y, d.Z + dz);
                holes.AddBeam(c + new Vector3(-oT - 1f, 0, 0), c + new Vector3(2f, 0, 0), studR, studR, false);
                holes.AddBeam(c + new Vector3(-oT - 25f, 0, 0), c + new Vector3(-oT, 0, 0), bossR - 0.5f, bossR - 0.5f, false);
            }
        }
        body.BoolSubtract(new Voxels(holes));
        // Tight trim box: Trim intersects with a box solid, whose surface costs memory.
        BBox3 bb = body.oCalculateBoundingBox();
        body.Trim(new BBox3(new Vector3(bb.vecMin.X - 1f, bb.vecMin.Y - 1f, bb.vecMin.Z - 1f), new Vector3(xEnd, bb.vecMax.Y + 1f, 0f)));
        return body;
    }
}
