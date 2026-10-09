using System.Numerics;
using PicoGK;

namespace PicoGKCatalog;

/// Signed-distance helpers shared by the body / structure generators.
public static class BodyKit
{
    public static float Smooth(float t) { t = Math.Clamp(t, 0f, 1f); return t * t * (3f - 2f * t); }

    /// Polynomial smooth union (blend radius k, mm).
    public static float SMin(float a, float b, float k)
    {
        if (k <= 0f) return MathF.Min(a, b);
        float h = Math.Clamp(0.5f + 0.5f * (b - a) / k, 0f, 1f);
        return b + (a - b) * h - k * h * (1f - h);
    }

    public static float SMax(float a, float b, float k) => -SMin(-a, -b, k);

    /// Intersection of two distance fields with the convex edge rounded by r.
    public static float RoundI(float a, float b, float r)
    {
        float qx = a + r, qy = b + r;
        return new Vector2(MathF.Max(qx, 0f), MathF.Max(qy, 0f)).Length() + MathF.Min(MathF.Max(qx, qy), 0f) - r;
    }

    /// 2D rounded rectangle centred on the origin (half sizes hu, hv, corner r).
    public static float RoundRect(float u, float v, float hu, float hv, float r)
    {
        r = MathF.Min(r, MathF.Min(hu, hv));
        float qx = MathF.Abs(u) - hu + r, qy = MathF.Abs(v) - hv + r;
        return new Vector2(MathF.Max(qx, 0f), MathF.Max(qy, 0f)).Length() + MathF.Min(MathF.Max(qx, qy), 0f) - r;
    }

    /// 2D ellipse, gradient-normalised approximate distance.
    public static float Ellipse(float u, float v, float a, float b)
    {
        float k = MathF.Sqrt(u * u / (a * a) + v * v / (b * b));
        if (k < 1e-6f) return -MathF.Min(a, b);
        float gx = u / (a * a) / k, gy = v / (b * b) / k;
        float g = MathF.Sqrt(gx * gx + gy * gy);
        return (k - 1f) / MathF.Max(g, 1e-6f);
    }

    /// Capped cylinder along Z with rounded edges (radius re).
    public static float RoundCylZ(Vector3 p, float cx, float cy, float r, float z0, float z1, float re)
    {
        float rho = MathF.Sqrt((p.X - cx) * (p.X - cx) + (p.Y - cy) * (p.Y - cy));
        float zm = 0.5f * (z0 + z1), hz = 0.5f * (z1 - z0);
        float dr = rho - (r - re), dz = MathF.Abs(p.Z - zm) - (hz - re);
        return new Vector2(MathF.Max(dr, 0f), MathF.Max(dz, 0f)).Length() + MathF.Min(MathF.Max(dr, dz), 0f) - re;
    }

    /// Renders a thin, gently curved panel tile by tile, each tile's Z range
    /// limited to where the panel is, so the implicit callback is not called
    /// across the whole empty bounding box. zRange returns null to skip a tile.
    public static Voxels Tiled(Library lib, Func<Vector3, float> f,
                               float x0, float x1, float y0, float y1, float tile,
                               Func<float, float, float, float, (float lo, float hi)?> zRange)
    {
        Voxels acc = new(lib);
        const float overlap = 2f;
        for (float x = x0; x < x1; x += tile)
            for (float y = y0; y < y1; y += tile)
            {
                float xa = x - overlap, xb = MathF.Min(x + tile, x1) + overlap;
                float ya = y - overlap, yb = MathF.Min(y + tile, y1) + overlap;
                var zr = zRange(xa, xb, ya, yb);
                if (zr is null) continue;
                Voxels t = Sdf.Vox(lib, f, new Vector3(xa, ya, zr.Value.lo), new Vector3(xb, yb, zr.Value.hi));
                acc.BoolAdd(t);
            }
        return acc;
    }
}

/// Signed distance to a closed 2D polygon, pre-sampled on a raster and read
/// back bilinearly (cheap per-voxel lookup for swept profiles).
public sealed class Raster2D
{
    readonly float[] _d;
    readonly int _nu, _nv;
    readonly float _u0, _v0, _h;

    public Raster2D(IReadOnlyList<Vector2> poly, float u0, float v0, float u1, float v1, float h)
    {
        _u0 = u0; _v0 = v0; _h = h;
        _nu = (int)MathF.Ceiling((u1 - u0) / h) + 1;
        _nv = (int)MathF.Ceiling((v1 - v0) / h) + 1;
        _d = new float[_nu * _nv];
        int n = poly.Count;
        Parallel.For(0, _nv, j =>
        {
            for (int i = 0; i < _nu; i++)
            {
                Vector2 p = new(u0 + i * h, v0 + j * h);
                float best = float.MaxValue;
                bool inside = false;
                for (int k = 0, m = n - 1; k < n; m = k++)
                {
                    Vector2 a = poly[m], b = poly[k];
                    Vector2 ab = b - a, ap = p - a;
                    float t = Math.Clamp(Vector2.Dot(ap, ab) / MathF.Max(Vector2.Dot(ab, ab), 1e-12f), 0f, 1f);
                    best = MathF.Min(best, (ap - ab * t).LengthSquared());
                    if ((a.Y > p.Y) != (b.Y > p.Y) && p.X < a.X + (p.Y - a.Y) / (b.Y - a.Y) * (b.X - a.X))
                        inside = !inside;
                }
                float d = MathF.Sqrt(best);
                _d[j * _nu + i] = inside ? -d : d;
            }
        });
    }

    public float this[float u, float v]
    {
        get
        {
            float fu = (u - _u0) / _h, fv = (v - _v0) / _h;
            float cu = Math.Clamp(fu, 0f, _nu - 1.001f), cv = Math.Clamp(fv, 0f, _nv - 1.001f);
            int i = (int)cu, j = (int)cv;
            float tu = cu - i, tv = cv - j;
            float a = _d[j * _nu + i], b = _d[j * _nu + i + 1];
            float c = _d[(j + 1) * _nu + i], d = _d[(j + 1) * _nu + i + 1];
            float val = (a * (1 - tu) + b * tu) * (1 - tv) + (c * (1 - tu) + d * tu) * tv;
            // outside the raster: add the distance to the raster border
            float ex = MathF.Max(MathF.Abs(fu - cu), 0f) * _h, ey = MathF.Max(MathF.Abs(fv - cv), 0f) * _h;
            return val + MathF.Sqrt(ex * ex + ey * ey);
        }
    }
}
