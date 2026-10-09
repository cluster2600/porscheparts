using System.Numerics;
using PicoGK;

namespace PicoGKCatalog;

/// Helpers for the exhaust / flow group: swept tubes as native lattice beams
/// (fast, smooth), centreline curves and 2D profile distances.
public static class FlowKit
{
    public static float Smooth(float t) { t = Math.Clamp(t, 0f, 1f); return t * t * (3f - 2f * t); }

    /// Polynomial smooth minimum (blend radius k, mm).
    public static float Smin(float a, float b, float k)
    {
        float h = Math.Clamp(0.5f + 0.5f * (b - a) / k, 0f, 1f);
        return b + (a - b) * h - k * h * (1f - h);
    }

    /// Adds a swept tube through the points; radius may vary per point.
    /// flatEnds: first and last segments get flat caps (the tube ends exactly
    /// on the end points), inner joints keep round caps for smooth bends.
    public static void Sweep(Lattice lat, IReadOnlyList<Vector3> pts, Func<int, float> r, bool flatEnds)
    {
        for (int i = 0; i + 1 < pts.Count; i++)
        {
            bool end = i == 0 || i == pts.Count - 2;
            lat.AddBeam(pts[i], pts[i + 1], r(i), r(i + 1), !(flatEnds && end));
        }
    }

    public static Voxels Tube(Library lib, IReadOnlyList<Vector3> pts, float r, bool flatEnds)
    {
        Lattice lat = new(lib);
        Sweep(lat, pts, _ => r, flatEnds);
        return new Voxels(lat);
    }

    public static List<Vector3> Bezier(Vector3 a, Vector3 b, Vector3 c, int n)
    {
        List<Vector3> pts = new();
        for (int i = 0; i <= n; i++) pts.Add(Sdf.Bezier(a, b, c, i / (float)n));
        return pts;
    }

    /// Centripetal-free uniform Catmull-Rom through the points; the end
    /// tangents are given explicitly (phantom points).
    public static List<Vector3> CatmullRom(IReadOnlyList<Vector3> p, Vector3 t0, Vector3 t1, int perSpan)
    {
        List<Vector3> q = new() { p[0] - t0 };
        q.AddRange(p);
        q.Add(p[^1] + t1);
        List<Vector3> pts = new();
        for (int s = 1; s + 2 < q.Count; s++)
            for (int i = 0; i < perSpan || (s + 3 == q.Count && i == perSpan); i++)
            {
                float t = i / (float)perSpan, t2 = t * t, t3 = t2 * t;
                pts.Add(0.5f * (2f * q[s] + (q[s + 1] - q[s - 1]) * t
                    + (2f * q[s - 1] - 5f * q[s] + 4f * q[s + 1] - q[s + 2]) * t2
                    + (-q[s - 1] + 3f * q[s] - 3f * q[s + 1] + q[s + 2]) * t3));
            }
        return pts;
    }

    /// Rounded rectangle, half sizes hx, hy, corner radius rc (2D, exact).
    public static float RoundRect(float x, float y, float hx, float hy, float rc)
    {
        rc = MathF.Min(rc, MathF.Min(hx, hy));
        float qx = MathF.Abs(x) - hx + rc, qy = MathF.Abs(y) - hy + rc;
        return new Vector2(MathF.Max(qx, 0f), MathF.Max(qy, 0f)).Length() + MathF.Min(MathF.Max(qx, qy), 0f) - rc;
    }

    /// Extrudes a 2D distance d2 between z0 and z1 with edge rounding re.
    public static float Extrude(float d2, float z, float z0, float z1, float re)
    {
        float dz = MathF.Abs(z - 0.5f * (z0 + z1)) - 0.5f * (z1 - z0);
        float a = d2 + re, b = dz + re;
        return new Vector2(MathF.Max(a, 0f), MathF.Max(b, 0f)).Length() + MathF.Min(MathF.Max(a, b), 0f) - re;
    }

    /// Distance to a 2D segment.
    public static float Seg2(Vector2 p, Vector2 a, Vector2 b)
    {
        Vector2 pa = p - a, ba = b - a;
        float h = Math.Clamp(Vector2.Dot(pa, ba) / Vector2.Dot(ba, ba), 0f, 1f);
        return (pa - ba * h).Length();
    }

    /// Distance to a 2D polyline.
    public static float Poly2(Vector2 p, IReadOnlyList<Vector2> pts)
    {
        float d = float.MaxValue;
        for (int i = 0; i + 1 < pts.Count; i++) d = MathF.Min(d, Seg2(p, pts[i], pts[i + 1]));
        return d;
    }

    /// Flat-capped cylinder along an arbitrary axis from a to b.
    public static float Cyl(Vector3 p, Vector3 a, Vector3 b, float r)
    {
        Vector3 ba = b - a;
        float L = ba.Length();
        Vector3 u = ba / L;
        float t = Vector3.Dot(p - a, u);
        float dr = (p - a - u * t).Length() - r;
        float dz = MathF.Abs(t - L / 2f) - L / 2f;
        return MathF.Min(MathF.Max(dr, dz), 0f) + new Vector2(MathF.Max(dr, 0f), MathF.Max(dz, 0f)).Length();
    }
}
