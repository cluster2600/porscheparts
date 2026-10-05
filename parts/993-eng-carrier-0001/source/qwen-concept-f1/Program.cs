// Concept for 993 115 021 53; all internal dimensions are design hypotheses.
// NON VALIDATED FOR MANUFACTURING. No measured mounting interfaces.
using System.Globalization;
using System.Numerics;
using System.Text.Json;
using PicoGK;

if (args.Length is < 1 or > 2)
    throw new ArgumentException("Usage: Carrier <output-directory> [voxel-size-mm]");
float voxelSizeMm = args.Length == 2 ? float.Parse(args[1], CultureInfo.InvariantCulture) : 0.5f;
if (!float.IsFinite(voxelSizeMm) || voxelSizeMm is < 0.25f or > 1f)
    throw new ArgumentException("Voxel size must be between 0.25 and 1 mm.");

// Model coordinates are at one tenth scale; export restores millimeters.
const float Scale = 10f;
const float BladeThicknessMm = 6f;
const float BossRadiusMm = 20f;
const float BossHeightMm = 50f;
const float BoreRadiusMm = 6.5f;
using Library lib = new(voxelSizeMm / Scale);
using Lattice lattice = new(lib);
// BEGIN QWEN: exact accepted responses, with the shared center edge repeated.
lattice.AddBeam(new Vector3(-28f, 0f, 0f), 0.6f, new Vector3(-20f, 0f, 1.9f), 0.6f, true);
lattice.AddBeam(new Vector3(-20f, 0f, 1.9f), 0.6f, new Vector3(0f, 0f, 0.9f), 0.6f, true);
lattice.AddBeam(new Vector3(0f, 0f, 0.9f), 0.6f, new Vector3(0f, 0f, -1.9f), 0.6f, true);
lattice.AddBeam(new Vector3(0f, 0f, -1.9f), 0.6f, new Vector3(-28f, 0f, 0f), 0.6f, true);
lattice.AddBeam(new Vector3(28f, 0f, 0f), 0.6f, new Vector3(20f, 0f, 1.9f), 0.6f, true);
lattice.AddBeam(new Vector3(20f, 0f, 1.9f), 0.6f, new Vector3(0f, 0f, 0.9f), 0.6f, true);
lattice.AddBeam(new Vector3(0f, 0f, 0.9f), 0.6f, new Vector3(0f, 0f, -1.9f), 0.6f, true);
lattice.AddBeam(new Vector3(0f, 0f, -1.9f), 0.6f, new Vector3(28f, 0f, 0f), 0.6f, true);
// END QWEN

// Reviewed scaffold: flatten the graph into a blade and add hypothetical bosses.
using Voxels solid = new(lattice);
solid.Trim(new BBox3(-31f, -BladeThicknessMm / (2 * Scale), -3f,
                     31f, BladeThicknessMm / (2 * Scale), 3f));
foreach (float x in new[] { -28f, 28f })
{
    using Lattice boss = new(lib);
    boss.AddBeam(new Vector3(x, 0, -BossHeightMm / (2 * Scale)), BossRadiusMm / Scale,
                 new Vector3(x, 0, BossHeightMm / (2 * Scale)), BossRadiusMm / Scale, false);
    using Voxels bossSolid = new(boss);
    solid.BoolAdd(bossSolid);
    using Lattice bore = new(lib);
    bore.AddBeam(new Vector3(x, 0, -3f), BoreRadiusMm / Scale,
                 new Vector3(x, 0, 3f), BoreRadiusMm / Scale, false);
    using Voxels boreSolid = new(bore);
    solid.BoolSubtract(boreSolid);
}
bool centerWeb = solid.bIsInside(Vector3.Zero);
bool leftWindowOpen = !solid.bIsInside(new Vector3(-10f, 0, 0));
bool rightWindowOpen = !solid.bIsInside(new Vector3(10f, 0, 0));
bool boresOpen = !solid.bIsInside(new Vector3(-28f, 0, 0)) && !solid.bIsInside(new Vector3(28f, 0, 0));
bool bossWalls = solid.bIsInside(new Vector3(-28f, 1f, 0)) && solid.bIsInside(new Vector3(28f, 1f, 0));
solid.CalculateProperties(out float volume, out BBox3 box);
using Mesh mesh = new(solid);
float[] minimum = { box.vecMin.X * Scale, box.vecMin.Y * Scale, box.vecMin.Z * Scale };
float[] maximum = { box.vecMax.X * Scale, box.vecMax.Y * Scale, box.vecMax.Z * Scale };
float[] boundsMm = Enumerable.Range(0, 3).Select(i => maximum[i] - minimum[i]).ToArray();
if (!(centerWeb && leftWindowOpen && rightWindowOpen && boresOpen && bossWalls) || volume <= 0 || mesh.nTriangleCount() == 0)
    throw new InvalidOperationException("Concept geometry witness failed.");
if (boundsMm[0] > 601 || boundsMm[1] > 51 || boundsMm[2] > 51)
    throw new InvalidOperationException("Concept exceeds the declared envelope allowance.");
Directory.CreateDirectory(args[0]);
mesh.SaveToStlFile(Path.Combine(args[0], "carrier-concept.stl"), fScale: Scale);
var metrics = new {
    status = "concept_native_geometry_only", voxel_size_mm = voxelSizeMm,
    volume_mm3 = volume * Scale * Scale * Scale, triangles = mesh.nTriangleCount(),
    minimum_mm = minimum, maximum_mm = maximum, bounds_mm = boundsMm,
    center_web = centerWeb, left_window_open = leftWindowOpen, right_window_open = rightWindowOpen,
    bores_open = boresOpen, boss_walls = bossWalls,
    is_oem_geometry = false, is_fitment_validated = false, is_manufacturing_release = false
};
string json = JsonSerializer.Serialize(metrics, new JsonSerializerOptions { WriteIndented = true });
File.WriteAllText(Path.Combine(args[0], "native-metrics.json"), json + "\n");
Console.WriteLine(json);
