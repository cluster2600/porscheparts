using System.Numerics;
using PicoGKCatalog;

// The old box includes r=10 protected points at its XZ corners.
static class ProtectedMask
{
    // Exclude unchanged zero sheets: smooth-min only adds material where |a-b| < k.
    public static float SmoothAddition(float a, float b, float k) =>
        MathF.Max(MathF.Max(Es.SMin(a,b,k), -MathF.Min(a,b)), MathF.Abs(a-b)-k);

    public static float Distance(Vector3 p) => MathF.Max(
        Sdf.Box(p, Vector3.Zero, new Vector3(7.4f, 2.4f, 7.4f)),
        Es.Cyl(p, new Vector3(0, -2.4f, 0), new Vector3(0, 2.4f, 0), 8.8f));

    public static void Check()
    {
        void Require(bool pass) { if (!pass) throw new InvalidDataException("Shared SDF regression failed"); }
        Require(Distance(new Vector3(5, 0, 0)) < 0);
        Require(Distance(new Vector3(6.7f, 0, 7.3f)) > 0);
        Require(SmoothAddition(0, 5, 1) > 0);
        Require(SmoothAddition(.1f, .1f, 1) < 0);
        Require(SmoothAddition(-.1f, -.1f, 1) > 0);
        foreach (float h in new[] { .2f, .1f })
            for (int x = -80; x <= 80; x++)
                for (int z = -80; z <= 80; z++)
                {
                    var p = new Vector3(x*h, 0, z*h);
                    if (MathF.Abs(p.Length()-10) <= h) Require(Distance(p) > 0);
                }
        // Shared curved-gallery primitive: endpoints and repeated-point segments.
        var curve = Es.CubicPts(new(-4,0,0), new(-4,2,0), new(4,2,0), new(4,0,0), 16);
        Require(curve.Count == 17 && curve[0] == new Vector3(-4,0,0) && curve[^1] == new Vector3(4,0,0));
        Require(MathF.Abs(Es.Tube(curve[8], curve, 1) + 1) < 1e-6f);
        Require(MathF.Abs(Es.Tube(new(2,0,0), new[] {Vector3.Zero, Vector3.Zero}, 1)-1) < 1e-6f);
    }
}
