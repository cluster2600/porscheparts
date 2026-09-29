// PicoGK 2.3.0 probe 5 — exact BuildPiston replica (Annulus variant A:
// Voxelize inside using-block, no pre-created empty Voxels), then
// CalculateProperties / Mesh.
using System.Numerics;
using PicoGK;

static Voxels Voxelize(Library lib, Lattice lat)
{
    Voxels vox = new(lat);
    lat.Dispose();
    return vox;
}

static Voxels Annulus(Library lib, Vector3 a, Vector3 b, float rOuter, float rInner)
{
    Voxels outer;
    using (Lattice lat = new(lib))
    {
        lat.AddBeam(a, rOuter, b, rOuter, false);
        outer = Voxelize(lib, lat);
    }
    if (rInner > 0.0005f)
    {
        using Lattice lat = new(lib);
        lat.AddBeam(a, rInner, b, rInner, false);
        using Voxels inner = Voxelize(lib, lat);
        outer.BoolSubtract(inner);
    }
    return outer;
}

try
{
    using Library lib = new(2.0f);
    Vector3 centre = new(216, -5, 15);
    float rOut = 49.98f;
    float yTop = 60f, yBottom = 60f - 105f;

    using Voxels body = Annulus(lib, centre + new Vector3(0, yBottom, 0),
                                    centre + new Vector3(0, yTop, 0),
                                    rOut, rOut - 5f);
    Console.WriteLine("1 shell ok");
    using (Lattice lat = new(lib))
    {
        lat.AddBeam(centre + new Vector3(0, yTop - 10f, 0), rOut,
                    centre + new Vector3(0, yTop, 0), rOut, false);
        using Voxels cap = new(lat);
        body.BoolAdd(cap);
    }
    Console.WriteLine("2 crown ok");
    float[] gr = { 8f, 14f, 20f };
    for (int n = 0; n < gr.Length; n++)
    {
        float y = yTop - gr[n];
        using Voxels groove = Annulus(lib, centre + new Vector3(0, y - 1.5f, 0),
                                          centre + new Vector3(0, y + 1.5f, 0),
                                          rOut + 0.5f, rOut - 2.5f);
        body.BoolSubtract(groove);
    }
    Console.WriteLine("3 grooves ok");
    using (Lattice lat = new(lib))
    {
        lat.AddBeam(centre + new Vector3(0, 0, -105f), 11.505f,
                    centre + new Vector3(0, 0, 105f), 11.505f, false);
        body.BoolSubtract(Voxelize(lib, lat));
    }
    Console.WriteLine("4 pinbore ok");
    body.CalculateProperties(out float vol, out BBox3 bb);
    Console.WriteLine($"5 props ok vol={vol}");
    using Mesh mesh = new(body);
    Console.WriteLine($"6 mesh ok tris={mesh.nTriangleCount()}");
    Console.WriteLine("PROBE5_PASS");
    return 0;
}
catch (Exception e)
{
    Console.Error.WriteLine($"PROBE5_FAIL {e.GetType().Name}: {e.Message}");
    return 9;
}
