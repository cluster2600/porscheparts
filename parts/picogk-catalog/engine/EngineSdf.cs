using System.Numerics;

namespace PicoGKCatalog;

/// Signed-distance helpers for the engine group: smooth booleans (fillets
/// come from the blend radius k), 2D profiles, flat-capped cylinders, tubes
/// along curves and the two-circle "chain case" outline.
public static class Es
{
    public const float InvSqrt2 = 0.70710678f;

    /// Polynomial smooth minimum; k is roughly the fillet radius in mm.
    public static float SMin(float a, float b, float k)
    {
        if (k <= 0f) return MathF.Min(a, b);
        float h = Math.Clamp(0.5f + 0.5f * (b - a) / k, 0f, 1f);
        return b + (a - b) * h - k * h * (1f - h);
    }

    public static float SMax(float a, float b, float k) => -SMin(-a, -b, k);

    public static float Len2(float x, float y) => MathF.Sqrt(x * x + y * y);

    /// Rounded rectangle centred at (cx, cy), half sizes hx, hy, corner radius r.
    public static float Rect2(float px, float py, float cx, float cy, float hx, float hy, float r)
    {
        float qx = MathF.Abs(px - cx) - hx + r, qy = MathF.Abs(py - cy) - hy + r;
        return Len2(MathF.Max(qx, 0f), MathF.Max(qy, 0f)) + MathF.Min(MathF.Max(qx, qy), 0f) - r;
    }

    /// Combine two "outside" distances into a body whose shared edge is rounded by r
    /// (d2 = planform distance, dz = height distance, both negative inside).
    public static float RoundEdge(float d2, float dz, float r)
    {
        float qx = d2 + r, qz = dz + r;
        return Len2(MathF.Max(qx, 0f), MathF.Max(qz, 0f)) + MathF.Min(MathF.Max(qx, qz), 0f) - r;
    }

    /// Extrude a 2D distance between z0 and z1 (sharp edges).
    public static float Extrude(float d2, float z, float z0, float z1) =>
        RoundEdge(d2, MathF.Max(z0 - z, z - z1), 0f);

    /// Flat-capped cylinder of radius r between a and b (exact).
    public static float Cyl(Vector3 p, Vector3 a, Vector3 b, float r)
    {
        Vector3 ba = b - a, pa = p - a;
        float baba = Vector3.Dot(ba, ba), paba = Vector3.Dot(pa, ba);
        float x = (pa * baba - ba * paba).Length() - r * baba;
        float y = MathF.Abs(paba - baba * 0.5f) - baba * 0.5f;
        float x2 = x * x, y2 = y * y * baba;
        float d = MathF.Max(x, y) < 0f ? -MathF.Min(x2, y2) : (x > 0f ? x2 : 0f) + (y > 0f ? y2 : 0f);
        return MathF.Sign(d) * MathF.Sqrt(MathF.Abs(d)) / baba;
    }

    public static float Seg2(float px, float py, float ax, float ay, float bx, float by)
    {
        float pax = px - ax, pay = py - ay, bax = bx - ax, bay = by - ay;
        float h = Math.Clamp((pax * bax + pay * bay) / (bax * bax + bay * bay), 0f, 1f);
        return Len2(pax - bax * h, pay - bay * h);
    }

    public static Vector3 Cubic(Vector3 a, Vector3 b, Vector3 c, Vector3 d, float t)
    {
        float u = 1f - t;
        return u * u * u * a + 3f * u * u * t * b + 3f * u * t * t * c + t * t * t * d;
    }

    /// Polyline through a cubic Bezier, n segments.
    public static List<Vector3> CubicPts(Vector3 a, Vector3 b, Vector3 c, Vector3 d, int n)
    {
        var pts = new List<Vector3>();
        for (int i = 0; i <= n; i++) pts.Add(Cubic(a, b, c, d, i / (float)n));
        return pts;
    }

    /// Round tube of radius r along a polyline (capsule chain).
    public static float Tube(Vector3 p, IReadOnlyList<Vector3> pts, float r)
    {
        float best = float.MaxValue;
        for (int i = 0; i + 1 < pts.Count; i++)
            best = MathF.Min(best, Vector3.DistanceSquared(pts[i], pts[i + 1]) < 1e-8f
                ? Sdf.Sphere(p, pts[i], r)                       // zero-length segment: avoid 0/0
                : Sdf.Capsule(p, pts[i], pts[i + 1], r));
        return best;
    }

    /// Planform of two circles (big radius r1 at x = c1, small radius r2 at
    /// x = c2 > c1) joined by their outer tangents.
    public static float TwinCircle(float x, float y, float c1, float c2, float r1, float r2)
    {
        float px = MathF.Abs(y), py = x - c1, h = c2 - c1;
        float b = (r1 - r2) / h, a = MathF.Sqrt(1f - b * b);
        float k = -b * px + a * py;
        if (k < 0f) return Len2(px, py) - r1;
        if (k > a * h) return Len2(px, py - h) - r2;
        return a * px + b * py - r1;
    }

    /// Point and outward normal at fraction s01 along the TwinCircle contour.
    public static (Vector2 pt, Vector2 n) TwinContour(float s01, float c1, float c2, float r1, float r2)
    {
        float h = c2 - c1, b = (r1 - r2) / h, a = MathF.Sqrt(1f - b * b);
        float th0 = MathF.Atan2(a, b);
        float seg = h * a, big = r1 * (2f * MathF.PI - 2f * th0), small = r2 * 2f * th0;
        float s = (s01 - MathF.Floor(s01)) * (big + small + 2f * seg);
        if (s < small)
        {
            float t = -th0 + s / r2; Vector2 n = new(MathF.Cos(t), MathF.Sin(t));
            return (new Vector2(c2, 0f) + r2 * n, n);
        }
        s -= small;
        if (s < seg)
        {
            Vector2 p0 = new(c2 + b * r2, a * r2), p1 = new(c1 + b * r1, a * r1);
            return (Vector2.Lerp(p0, p1, s / seg), new Vector2(b, a));
        }
        s -= seg;
        if (s < big)
        {
            float t = th0 + s / r1; Vector2 n = new(MathF.Cos(t), MathF.Sin(t));
            return (new Vector2(c1, 0f) + r1 * n, n);
        }
        s -= big;
        Vector2 q0 = new(c1 + b * r1, -a * r1), q1 = new(c2 + b * r2, -a * r2);
        return (Vector2.Lerp(q0, q1, s / seg), new Vector2(b, -a));
    }
}
