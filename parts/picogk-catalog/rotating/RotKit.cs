using System.Numerics;
using PicoGK;

namespace PicoGKCatalog;

/// Signed-distance helpers for rotating machinery: smooth booleans (the
/// smooth union is what gives every blade its root fillet), revolved
/// profiles, cambered airfoil sections and blade rows. All distances in mm,
/// negative inside; fields are distance-like only near the surface.
public static class RotKit
{
    public const float Pi = MathF.PI;
    public static float Rad(float deg) => deg * Pi / 180f;
    public static float R(Vector3 p) => MathF.Sqrt(p.X * p.X + p.Y * p.Y);
    public static float Th(Vector3 p) => MathF.Atan2(p.Y, p.X);

    /// Polynomial smooth minimum; k is roughly the fillet radius.
    public static float SMin(float a, float b, float k)
    {
        if (k <= 0f) return MathF.Min(a, b);
        float h = Math.Clamp(0.5f + 0.5f * (b - a) / k, 0f, 1f);
        return b + (a - b) * h - k * h * (1f - h);
    }

    public static float SMax(float a, float b, float k) => -SMin(-a, -b, k);

    /// Angle (or length) folded to the nearest multiple of pitch, in [-pitch/2, pitch/2].
    public static float Near(float d, float pitch) => d - pitch * MathF.Round(d / pitch);

    /// Approximate signed distance to an axis-aligned 2D ellipse centred at the origin.
    public static float Ellipse(float x, float y, float a, float b)
    {
        float k0 = MathF.Sqrt(x * x / (a * a) + y * y / (b * b));
        float k1 = MathF.Sqrt(x * x / (a * a * a * a) + y * y / (b * b * b * b));
        if (k1 < 1e-9f) return -MathF.Min(a, b);
        return k0 * (k0 - 1f) / k1;
    }

    /// Approximate signed distance to a 2D superellipse |x/a|^n + |y/b|^n = 1.
    public static float SuperEllipse(float x, float y, float a, float b, float n)
    {
        float k = MathF.Pow(MathF.Pow(MathF.Abs(x) / a, n) + MathF.Pow(MathF.Abs(y) / b, n), 1f / n);
        return (k - 1f) * MathF.Min(a, b);
    }

    /// Rounded 2D rectangle [x0,x1] x [y0,y1] with corner radius rr.
    public static float Box2(float x, float y, float x0, float x1, float y0, float y1, float rr)
    {
        float hx = (x1 - x0) / 2f, hy = (y1 - y0) / 2f;
        rr = MathF.Min(rr, MathF.Min(hx, hy) * 0.999f);
        float qx = MathF.Abs(x - (x0 + x1) / 2f) - (hx - rr), qy = MathF.Abs(y - (y0 + y1) / 2f) - (hy - rr);
        return new Vector2(MathF.Max(qx, 0f), MathF.Max(qy, 0f)).Length() + MathF.Min(MathF.Max(qx, qy), 0f) - rr;
    }

    /// Annulus about Z (radii rIn..rOut, z0..z1) with rounded edges.
    public static float Annulus(Vector3 p, float rIn, float rOut, float z0, float z1, float rr) =>
        Box2(R(p), p.Z, rIn, rOut, z0, z1, rr);

    /// Capsule whose radius varies linearly from ra (at a) to rb (at b).
    public static float Cone(Vector3 p, Vector3 a, Vector3 b, float ra, float rb)
    {
        Vector3 pa = p - a, ba = b - a;
        float h = Math.Clamp(Vector3.Dot(pa, ba) / Vector3.Dot(ba, ba), 0f, 1f);
        return (pa - ba * h).Length() - (ra + (rb - ra) * h);
    }

    /// Flat-ended cylinder between a and b.
    public static float Rod(Vector3 p, Vector3 a, Vector3 b, float r)
    {
        Vector3 ba = b - a;
        float len = ba.Length();
        Vector3 axis = ba / len;
        Vector3 pa = p - a;
        float t = Vector3.Dot(pa, axis);
        float dr = (pa - axis * t).Length() - r;
        float dz = MathF.Abs(t - len / 2f) - len / 2f;
        return MathF.Min(MathF.Max(dr, dz), 0f) + new Vector2(MathF.Max(dr, 0f), MathF.Max(dz, 0f)).Length();
    }

    /// NACA 4-digit half thickness per unit thickness ratio (closed trailing edge).
    public static float Naca(float x) =>
        5f * (0.2969f * MathF.Sqrt(x) - 0.1260f * x - 0.3516f * x * x + 0.2843f * x * x * x - 0.1036f * x * x * x * x);

    /// Cambered airfoil section in an unwrapped cascade plane: y circumferential,
    /// x axial, chord centred on the origin and staggered by stagger (rad) from
    /// the axial direction. Parabolic camber line of camber angle camber (rad),
    /// NACA thickness of maximum tmax (mm), never thinner than 2 * minHalf.
    public static float Airfoil(float y, float x, float chord, float stagger, float camber, float tmax, float minHalf)
    {
        float s = MathF.Sin(stagger), c = MathF.Cos(stagger);
        float u = y * s + x * c + chord / 2f;
        float v = y * c - x * s;
        float xn = u / chord;
        if (xn <= 0f) return MathF.Sqrt(u * u + v * v) - minHalf;
        if (xn >= 1f) return MathF.Sqrt((u - chord) * (u - chord) + v * v) - minHalf;
        float h = chord / 2f * MathF.Tan(camber / 4f);
        float yc = 4f * h * xn * (1f - xn);
        float half = MathF.Max(tmax * Naca(xn), minHalf);
        return MathF.Abs(v - yc) - half;
    }

    /// Quadratic through three stations (hub, mid, tip), clamped to [x0, x2].
    public static float Q3(float x, float x0, float x1, float x2, float y0, float y1, float y2)
    {
        x = Math.Clamp(x, x0, x2);
        return y0 * (x - x1) * (x - x2) / ((x0 - x1) * (x0 - x2))
             + y1 * (x - x0) * (x - x2) / ((x1 - x0) * (x1 - x2))
             + y2 * (x - x0) * (x - x1) / ((x2 - x0) * (x2 - x1));
    }
}

/// Axial blade row: N airfoil blades stacked radially between rRoot and rTip,
/// sections given at hub/mid/tip radii and interpolated quadratically.
public sealed class AxialRow
{
    public int N;
    public float RRoot, RTip, ZMid, Phase, MinHalf;
    public float RHub, RMid, RTipSec;
    public float[] Chord = new float[3], Stagger = new float[3], Camber = new float[3], Tmax = new float[3];
    public float TipSweep;       // rad, circumferential offset of the tip section, grows with span^2

    float S(float[] a, float r) => RotKit.Q3(r, RHub, RMid, RTipSec, a[0], a[1], a[2]);

    public float Eval(Vector3 p)
    {
        float r = MathF.Max(RotKit.R(p), 1e-3f);
        float lim = MathF.Max(r - RTip, RRoot - r);
        if (lim > 4f) return lim;
        float span = Math.Clamp((r - RHub) / (RTipSec - RHub), 0f, 1f);
        float th = RotKit.Th(p) - Phase - TipSweep * span * span;
        float d = RotKit.Near(th, 2f * RotKit.Pi / N);
        float chord = S(Chord, r);
        float a = RotKit.Airfoil(r * d, p.Z - ZMid, chord, RotKit.Rad(S(Stagger, r)), RotKit.Rad(S(Camber, r)),
                                 S(Tmax, r), MinHalf);
        return MathF.Max(a, lim);
    }
}
