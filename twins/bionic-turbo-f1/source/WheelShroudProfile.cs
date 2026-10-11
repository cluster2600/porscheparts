using System.Numerics;

// Meridional profile derived from the existing F0 wheel, translated -3 mm along Z.
// The QUASAR shared-contour principle is an inspiration; no QUASAR code is copied.
sealed class WheelShroudProfile
{
    public const int EllipseSegments = 64;
    public const string WheelSourceSha256 = "4292d1a4c0c23ff4540f3b4a8d4f1d2898c0264d98c97f689bdbdd32e249e977";
    readonly Vector2[] points; // (radius, axial Z), monotonically ordered in Z.
    readonly float maxRadius;
    public WheelShroudProfile(float rear, float height, float rearRadius, float inletRadius, float clearance)
    {
        var p = new List<Vector2> { new(rearRadius, rear), new(rearRadius, 0), new(30.25f + clearance, 4.5f) };
        for (int i = 1; i <= EllipseSegments; ++i)
        {
            float angle = MathF.PI / 2 * (1f - i / (float)EllipseSegments);
            p.Add(new(30.25f - 9.95f * MathF.Cos(angle) + clearance, 21f - 16.5f * MathF.Sin(angle)));
        }
        p.Add(new(inletRadius, height));
        points = p.ToArray();
        maxRadius = points.Max(p => p.X);
    }
    public float Radius(float z)
    {
        if (z <= points[0].Y) return points[0].X;
        for (int i = 1; i < points.Length; ++i)
            if (z <= points[i].Y)
                return float.Lerp(points[i - 1].X, points[i].X, (z - points[i - 1].Y) / (points[i].Y - points[i - 1].Y));
        return points[^1].X;
    }
    public float Distance(Vector2 q)
    {
        float d2 = float.PositiveInfinity;
        for (int i = 1; i < points.Length; ++i)
        {
            Vector2 segment = points[i] - points[i - 1], delta = q - points[i - 1];
            float t = Math.Clamp(Vector2.Dot(delta, segment) / segment.LengthSquared(), 0, 1);
            d2 = MathF.Min(d2, (delta - t * segment).LengthSquared());
        }
        return MathF.CopySign(MathF.Sqrt(d2), q.X - Radius(q.Y));
    }
    public float OuterRadius(float z, float offset)
    {
        float low = Radius(z), high = maxRadius + offset + 1;
        for (int i = 0; i < 24; ++i)
        {
            float mid = (low + high) / 2;
            if (Distance(new(mid, z)) < offset) low = mid; else high = mid;
        }
        return (low + high) / 2;
    }
}
