using System.Numerics;
using PicoGK;

// Deliberately no Library.Go/viewer: test native geometry without a display.
// This sphere is a runtime witness, never a cylinder-head surrogate.
try
{
    using Library library = new(0.5f);
    Lattice lattice = new(library);
    lattice.AddSphere(Vector3.Zero, 5f);
    Voxels voxels = new(lattice);
    Mesh mesh = new(voxels);
    int triangles = mesh.nTriangleCount();
    if (triangles <= 0) throw new Exception("Empty runtime witness");
    Console.WriteLine($"NATIVE_GEOMETRY_SMOKE_PASS triangles={triangles}");
    return 0;
}
catch (Exception exception)
{
    Console.Error.WriteLine($"NATIVE_GEOMETRY_SMOKE_FAIL {exception.GetType().Name}: {exception.Message}");
    return 1;
}
