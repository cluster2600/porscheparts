using System.Numerics;
using PicoGK;

// Deterministic PicoGK STL-export smoke test (ADR 0004).
// Geometry: 30 x 20 x 10 mm box with an 8 mm-diameter through-hole
// (cylinder boolean subtraction via a flat-capped lattice beam).
// This is F1_envelope witness geometry only: a runtime/export smoke
// witness, never a cylinder-head surrogate or a dimensional reference.
try
{
    string strOutPath = args.Length > 0 ? args[0]
        : "m64-picogk-smoke-box-hole.stl";
    float fVoxelMM = args.Length > 1 ? float.Parse(args[1]) : 0.5f;

    using Library library = new(fVoxelMM);

    // Box via mesh primitive, rendered to voxels
    Mesh mshBox = Utils.mshCreateCube(
        library,
        new Vector3(30.0f, 20.0f, 10.0f),
        new Vector3(15.0f, 10.0f, 5.0f));
    Voxels vox = new(mshBox);

    // Through-hole: beam with flat caps so the hole is a true cylinder
    Lattice latHole = new(library);
    latHole.AddBeam(
        new Vector3(15.0f, 10.0f, -1.0f),
        new Vector3(15.0f, 10.0f, 11.0f),
        4.0f,
        4.0f,
        false);
    Voxels voxHole = new(latHole);

    vox.BoolSubtract(voxHole);

    if (vox.bIsEmpty()) throw new Exception("Smoke geometry is empty");

    vox.CalculateProperties(out float fVolumeCubicMM, out BBox3 oBBox);

    Mesh mshOut = new(vox);
    int nTriangles = mshOut.nTriangleCount();
    if (nTriangles <= 0) throw new Exception("Empty export mesh");

    mshOut.SaveToStlFile(strOutPath, Mesh.EStlUnit.MM);

    long nBytes = new FileInfo(strOutPath).Length;
    Console.WriteLine(
        $"PICOGK_STL_SMOKE_PASS voxelsizemm={fVoxelMM} " +
        $"triangles={nTriangles} volume_cubic_mm={fVolumeCubicMM:F1} " +
        $"bbox=({oBBox.vecMin.X:F2},{oBBox.vecMin.Y:F2},{oBBox.vecMin.Z:F2})" +
        $"to({oBBox.vecMax.X:F2},{oBBox.vecMax.Y:F2},{oBBox.vecMax.Z:F2}) " +
        $"file={strOutPath} bytes={nBytes}");
    return 0;
}
catch (Exception exception)
{
    Console.Error.WriteLine(
        $"PICOGK_STL_SMOKE_FAIL {exception.GetType().Name}: {exception.Message}");
    return 1;
}
