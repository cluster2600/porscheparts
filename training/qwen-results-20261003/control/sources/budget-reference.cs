// Human-authored layout for output-size audit only. Not compiled or validated.
#nullable enable
using System;
using System.Numerics;
using PicoGK;

public static class GeneratedSpacer
{
    public static Voxels Build(Library library, float? outerDiameterMm,
        float? innerDiameterMm, float? thicknessMm, string? unit)
    {
        if (unit != "mm" || outerDiameterMm is null ||
            innerDiameterMm is null || thicknessMm is null)
            throw new ArgumentException("Known millimeter parameters required");
        float od = outerDiameterMm.Value, id = innerDiameterMm.Value;
        float t = thicknessMm.Value;
        if (!float.IsFinite(od) || !float.IsFinite(id) || !float.IsFinite(t) ||
            !(od > id && id > 0 && t > 0))
            throw new ArgumentException("Finite positive dimensions; inner < outer");
        var shell = new Lattice(library);
        shell.AddBeam(Vector3.Zero, od / 2, new Vector3(0, 0, t), od / 2, false);
        var solid = new Voxels(shell);
        var bore = new Lattice(library);
        bore.AddBeam(new Vector3(0, 0, -t), id / 2,
            new Vector3(0, 0, 2 * t), id / 2, false);
        var cutter = new Voxels(bore);
        solid.BoolSubtract(cutter);
        return solid;
    }
}
