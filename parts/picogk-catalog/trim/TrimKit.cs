using System.Numerics;
using PicoGK;

namespace PicoGKCatalog;

/// Small SDF and voxel helpers shared by the trim generators.
public static class TrimKit
{
    public static float Smooth(float t) { t = Math.Clamp(t, 0f, 1f); return t * t * (3f - 2f * t); }

    /// Rounded rectangle in 2D (half sizes hx, hy, corner radius r), signed distance.
    public static float RoundRect(float x, float y, float hx, float hy, float r)
    {
        r = MathF.Min(r, MathF.Min(hx, hy));
        float qx = MathF.Abs(x) - hx + r, qy = MathF.Abs(y) - hy + r;
        return new Vector2(MathF.Max(qx, 0f), MathF.Max(qy, 0f)).Length() + MathF.Min(MathF.Max(qx, qy), 0f) - r;
    }

    /// Exact 2D intersection of a plan distance and an axial slab distance.
    public static float Extrude(float d2, float dz) =>
        MathF.Min(MathF.Max(d2, dz), 0f) + new Vector2(MathF.Max(d2, 0f), MathF.Max(dz, 0f)).Length();

    /// Polynomial smooth minimum (blend radius k).
    public static float SMin(float a, float b, float k)
    {
        float h = MathF.Max(k - MathF.Abs(a - b), 0f) / k;
        return MathF.Min(a, b) - h * h * k * 0.25f;
    }

    /// Rounds convex edges by r (inward then outward offset). Voxels.Fillet
    /// only fills concave corners.
    public static void Round(Voxels v, float r) => v.DoubleOffset(-r, r);

    /// Stadium (slot) in 2D: centre segment from -half to +half along u, radius r.
    public static float Stadium(float u, float v, float half, float r)
    {
        float du = MathF.Max(MathF.Abs(u) - half, 0f);
        return MathF.Sqrt(du * du + v * v) - r;
    }
}
