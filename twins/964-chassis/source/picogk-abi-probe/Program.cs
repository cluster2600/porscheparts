// Diagnostic of the pinned PicoGK 26.2 Boolean ABI; no vehicle geometry.
using System.Numerics;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Text.Json;
using PicoGK;

using Library lib = new(0.1f);
using Lattice lattice = new(lib);
lattice.AddBeam(new Vector3(0, 0, 0), 2, new Vector3(10, 0, 0), 2, false);
using Voxels solid = new(lattice);
var flags = BindingFlags.Instance | BindingFlags.NonPublic;
var lh = (LibHandle)typeof(Library).GetField("hThis", flags)!.GetValue(lib)!;
var vh = (VoxHandle)typeof(Voxels).GetField("hThis", flags)!.GetValue(solid)!;
var rows = new List<object>();
bool oneBytePassed = true, stockPassed = true;
foreach (var (point, expected) in new[] {
    (new Vector3(5, 0, 0), true), (new Vector3(5, 5, 0), false),
    (new Vector3(50, 50, 50), false) }) {
    bool stock = solid.bIsInside(point);
    bool oneByte = Native.Inside(lh, vh, point);
    oneBytePassed &= oneByte == expected;
    stockPassed &= stock == expected;
    rows.Add(new { point = new[] {point.X, point.Y, point.Z}, expected, stock, one_byte = oneByte });
}
Console.WriteLine(JsonSerializer.Serialize(new { diagnostic_only = true,
    stock_passed = stockPassed, one_byte_passed = oneBytePassed, probes = rows }));
// Nonzero preserves the failed production binding even if the diagnostic succeeds.
return stockPassed && oneBytePassed ? 0 : 1;

static class Native {
    [DllImport("picogk.26.2", EntryPoint = "Voxels_bIsInside", CallingConvention = CallingConvention.Cdecl)]
    [return: MarshalAs(UnmanagedType.I1)]
    public static extern bool Inside(LibHandle library, VoxHandle voxels, in Vector3 point);
}
