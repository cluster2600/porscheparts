using System.Numerics;
using PicoGK;

namespace PicoGKCatalog;

/// Implicit wrapper: any signed-distance lambda (negative inside, mm).
/// Fields need only be distance-like near the surface; PicoGK re-levels the
/// narrow band when it voxelizes.
public sealed class Fn : IImplicit
{
    readonly Func<Vector3, float> _f;
    public Fn(Func<Vector3, float> f) => _f = f;
    public float fSignedDistance(in Vector3 vec) => _f(vec);
}

public static class Sdf
{
    public static Voxels Vox(Library lib, Func<Vector3, float> f, Vector3 min, Vector3 max) =>
        new(lib, new Fn(f), new BBox3(min, max));

    public static float Box(Vector3 p, Vector3 c, Vector3 half)
    {
        Vector3 q = Vector3.Abs(p - c) - half;
        return Vector3.Max(q, Vector3.Zero).Length() + MathF.Min(MathF.Max(q.X, MathF.Max(q.Y, q.Z)), 0f);
    }

    public static float RoundBox(Vector3 p, Vector3 c, Vector3 half, float r) =>
        Box(p, c, half - new Vector3(r)) - r;

    /// Cylinder along Z from z0 to z1.
    public static float CylZ(Vector3 p, float cx, float cy, float r, float z0, float z1)
    {
        float dr = MathF.Sqrt((p.X - cx) * (p.X - cx) + (p.Y - cy) * (p.Y - cy)) - r;
        float dz = MathF.Max(z0 - p.Z, p.Z - z1);
        return MathF.Min(MathF.Max(dr, dz), 0f) + new Vector2(MathF.Max(dr, 0f), MathF.Max(dz, 0f)).Length();
    }

    /// Generic capped cylinder between two points.
    public static float Capsule(Vector3 p, Vector3 a, Vector3 b, float r)
    {
        Vector3 pa = p - a, ba = b - a;
        float h = Math.Clamp(Vector3.Dot(pa, ba) / Vector3.Dot(ba, ba), 0f, 1f);
        return (pa - ba * h).Length() - r;
    }

    public static float Sphere(Vector3 p, Vector3 c, float r) => (p - c).Length() - r;

    /// Ellipse section (semi-axes a, b) in XY, extruded between z0 and z1;
    /// a and b may vary with z through the delegate. Approximate distance.
    public static float EllipseLoftZ(Vector3 p, Func<float, (float a, float b)> ab, float z0, float z1)
    {
        float z = Math.Clamp(p.Z, z0, z1);
        (float a, float b) = ab(z);
        float k = new Vector2(p.X / a, p.Y / b).Length();
        float dr = (k - 1f) * MathF.Min(a, b);
        float dz = MathF.Max(z0 - p.Z, p.Z - z1);
        return MathF.Min(MathF.Max(dr, dz), 0f) + new Vector2(MathF.Max(dr, 0f), MathF.Max(dz, 0f)).Length();
    }

    /// Superellipsoid-like dome: |x/a|^n + |y/b|^n + |z/c|^n = 1. Approximate distance.
    public static float SuperEllipsoid(Vector3 p, Vector3 c, Vector3 r, float n)
    {
        Vector3 q = Vector3.Abs(p - c) / r;
        float s = MathF.Pow(MathF.Pow(q.X, n) + MathF.Pow(q.Y, n) + MathF.Pow(q.Z, n), 1f / n);
        return (s - 1f) * MathF.Min(r.X, MathF.Min(r.Y, r.Z));
    }

    /// Sheet gyroid of period cell (mm) and wall thickness t (mm).
    public static float GyroidSheet(Vector3 p, float cell, float t)
    {
        float k = 2f * MathF.PI / cell;
        float x = p.X * k, y = p.Y * k, z = p.Z * k;
        float g = MathF.Sin(x) * MathF.Cos(y) + MathF.Sin(y) * MathF.Cos(z) + MathF.Sin(z) * MathF.Cos(x);
        // |grad g| <= ~1.5 k; scale to approximate millimetres.
        return MathF.Abs(g) / (1.5f * k) - t * 0.5f;
    }

    /// Open-cell BCC strut lattice confined to a region shrunk by skin.
    /// A strut lattice keeps its void space as one connected region, so a few
    /// drain holes evacuate all the powder; a clipped gyroid sheet leaves
    /// sealed pockets. Struts are native PicoGK lattice beams (fast).
    public static Voxels LatticeCore(Library lib, Voxels region, float skin, float cell, float strutD)
    {
        Voxels core = region.voxOffset(-skin);
        return LatticeIn(lib, core, cell, strutD);
    }

    public static Voxels LatticeIn(Library lib, Voxels region, float cell, float strutD)
    {
        BBox3 box = region.oCalculateBoundingBox();
        Lattice lat = new(lib);
        float r = strutD / 2f;
        int nx = (int)MathF.Ceiling((box.vecMax.X - box.vecMin.X) / cell) + 1;
        int ny = (int)MathF.Ceiling((box.vecMax.Y - box.vecMin.Y) / cell) + 1;
        int nz = (int)MathF.Ceiling((box.vecMax.Z - box.vecMin.Z) / cell) + 1;
        Vector3 o = box.vecMin - new Vector3(cell / 2f);
        for (int i = 0; i < nx; i++)
            for (int j = 0; j < ny; j++)
                for (int k = 0; k < nz; k++)
                {
                    Vector3 c = o + new Vector3(i + 0.5f, j + 0.5f, k + 0.5f) * cell;
                    for (int dx = -1; dx <= 1; dx += 2)
                        for (int dy = -1; dy <= 1; dy += 2)
                            for (int dz = -1; dz <= 1; dz += 2)
                                lat.AddBeam(c, c + new Vector3(dx, dy, dz) * (cell / 2f), r, r, true);
                }
        Voxels struts = new(lat);
        struts.BoolIntersect(region);
        return struts;
    }
    /// Stage trace on stderr, so a native exception can be located.
    public static void Stage(string part, string stage) => Console.Error.WriteLine($"  [{part}] {stage}");

    public static float Vol(Voxels v) { v.CalculateProperties(out float vol, out BBox3 _); return vol / 1000f; }

    public static Vector3 RotZ(Vector3 p, float deg)
    {
        float a = deg * MathF.PI / 180f, c = MathF.Cos(a), s = MathF.Sin(a);
        return new Vector3(c * p.X + s * p.Y, -s * p.X + c * p.Y, p.Z);
    }

    public static Vector3 Bezier(Vector3 a, Vector3 b, Vector3 c, float t) =>
        (1 - t) * (1 - t) * a + 2 * (1 - t) * t * b + t * t * c;
}
