using System.Numerics;
using PicoGK;

namespace PicoGKCatalog;

// Unmeasured single-cylinder study; the gas passages and cam interfaces need donor metrology.
public sealed class Head962Study : IPartGenerator
{
    public string Name => "962_4v_twin_plug_water_head_study";

    public Voxels Build(Library lib, PartSpec s)
    {
        string[] keys = { "bore_mm", "deck_mm", "wall_mm", "valve_x_mm", "valve_y_mm",
            "port_radius_mm", "ring_radius_mm", "channel_radius_mm", "spark_half_span_mm",
            "spark_radius_mm", "height_mm", "export_mode" };
        if (s.Status != "shape_study_only_unmeasured_interfaces_no_manufacturing" ||
            s.SafetyClass != "prohibited_pending_engineering" || s.DensityGCm3 != 0 ||
            s.Parameters.Count != keys.Length || keys.Any(k => !s.Parameters.ContainsKey(k)) ||
            s.Parameters.Any(p => !double.IsFinite(p.Value.Value) || p.Value.Basis != "assumption" ||
                p.Value.Value < 0 || p.Value.Value > 200 ||
                p.Value.Unit != (p.Key == "export_mode" ? "1" : "mm")) ||
            !float.IsFinite(s.VoxelMm) || s.VoxelMm < .25f || s.VoxelMm > .75f)
            throw new ArgumentException("Only bounded, unqualified 962 study assumptions are accepted.");
        float bore = s.P("bore_mm"), deck = s.P("deck_mm"), wall = s.P("wall_mm");
        float vx = s.P("valve_x_mm"), vy = s.P("valve_y_mm"), port = s.P("port_radius_mm");
        float ring = s.P("ring_radius_mm"), water = s.P("channel_radius_mm");
        float spark = s.P("spark_half_span_mm"), plug = s.P("spark_radius_mm"), height = s.P("height_mm");
        float mode = s.P("export_mode");
        if (mode != MathF.Truncate(mode) || mode > 2 || wall < 4 * s.VoxelMm ||
            water < 3 * s.VoxelMm || bore < 90 || bore > 100 || deck < 10 || deck > 14 ||
            wall < 4 || wall > 5 || vx != 22 || vy != 32 || ring != 16 || port != 8 ||
            water != 3 || spark != 9 || plug != 4 || height != 90)
            throw new ArgumentException("Study layout is bounded to the inspected F0; new layouts need a new audit.");

        var horizontal = new List<(Vector2 a, Vector2 b, float z, float r)>();
        var risers = new List<(Vector3 a, Vector3 b)>();
        var loops = new List<Vector2>();
        void Line(Vector2 a, Vector2 b, float z, float r) => horizontal.Add((a, b, z, r));
        Line(new(-80, -68), new(48, -68), 24, water + 1);
        Line(new(-60, 68), new(80, 68), 70, water + 1);
        foreach (float sx in new[] { -1f, 1f })
        {
            Line(new(sx * 48, -68), new(sx * 48, 16), 24, water);
            Line(new(sx * 60, -32), new(sx * 60, 68), 70, water);
            foreach (float sy in new[] { -1f, 1f })
            {
                Vector2 c = new(sx * vx, sy * vy);
                loops.Add(c);
                Line(c - new Vector2(0, ring), new(sx * 48, c.Y - ring), 24, water);
                Vector2 outlet = c + new Vector2(sx * ring, 0);
                risers.Add((new(outlet, 24), new(outlet, 70)));
                Line(outlet, new(sx * 60, c.Y), 70, water);
            }
        }
        float Section(float lateral, float z, float radius)
        {
            float circle = new Vector2(lateral, z).Length() - radius;
            float roof = MathF.Max(lateral + z - MathF.Sqrt(2) * radius, radius / MathF.Sqrt(2) - z);
            return MathF.Min(circle, roof);
        }
        float Water(Vector3 p)
        {
            float d = float.MaxValue;
            foreach (var tube in horizontal)
            {
                Vector2 ab = tube.b - tube.a, ap = new Vector2(p.X, p.Y) - tube.a;
                float t = Math.Clamp(Vector2.Dot(ap, ab) / ab.LengthSquared(), 0, 1);
                float lateral = (ap - t * ab).Length(), z = p.Z - tube.z;
                d = MathF.Min(d, Section(lateral, z, tube.r));
            }
            foreach (Vector2 c in loops)
                d = MathF.Min(d, Section(MathF.Abs((new Vector2(p.X, p.Y) - c).Length() - ring), p.Z - 24, water));
            foreach (var tube in risers)
                d = MathF.Min(d, Sdf.Capsule(p, tube.a, tube.b, water));
            return d;
        }
        float Dry(Vector3 p)
        {
            float d = Sdf.Sphere(p, new(0, 0, -25), bore / 2);
            foreach (float sx in new[] { -1f, 1f })
            {
                d = MathF.Min(d, Sdf.CylZ(p, sx * spark, 0, plug, 8, height + 8));
                foreach (float sy in new[] { -1f, 1f })
                {
                    Vector3 seat = new(sx * vx, sy * vy, 8), knee = new(sx * vx, sy * vy, 44);
                    d = MathF.Min(d, Sdf.Capsule(p, seat, knee, port));
                    d = MathF.Min(d, Sdf.Capsule(p, knee, new(sx * vx, sy * 80, 54), port));
                    d = MathF.Min(d, Sdf.CylZ(p, sx * vx, sy * vy, 4, 44, height + 8));
                }
            }
            return d;
        }
        float Solid(Vector3 p)
        {
            float dry = Dry(p), wet = Water(p);
            float body = Sdf.CylZ(p, 0, 0, bore / 2 + wall + 4, 0, deck);
            body = MathF.Min(body, wet - wall);
            foreach (float sx in new[] { -1f, 1f })
            {
                body = MathF.Min(body, Sdf.CylZ(p, sx * spark, 0, plug + wall, 8, height));
                foreach (float sy in new[] { -1f, 1f })
                {
                    Vector3 seat = new(sx * vx, sy * vy, 8), knee = new(sx * vx, sy * vy, 44);
                    body = MathF.Min(body, Sdf.Capsule(p, seat, knee, port + wall));
                    body = MathF.Min(body, Sdf.Capsule(p, knee, new(sx * vx, sy * 80, 54), port + wall));
                    body = MathF.Min(body, Sdf.CylZ(p, sx * vx, sy * vy, 4 + wall, 44, height));
                    body = MathF.Min(body, Sdf.Capsule(p, new(sx * spark, 0, 56),
                        new(sx * vx, sy * vy, 60), wall));
                }
            }
            body = MathF.Max(body, MathF.Max(-p.Z, p.Z - height));
            body = MathF.Max(body, MathF.Abs(p.Y) - 80);
            body = MathF.Max(body, MathF.Abs(p.X) - 80);
            return MathF.Max(body, -MathF.Min(dry, wet));
        }
        Func<Vector3, float> field = mode == 0 ? Solid : mode == 1 ? Water : Dry;
        return Sdf.Vox(lib, field, new(-90, -95, -80), new(90, 95, 100));
    }
}
