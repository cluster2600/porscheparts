using System.Globalization;
using System.Numerics;
using System.Security.Cryptography;
using System.Text.Json;
using PicoGK;

// A visual topology proxy, deliberately distinct from a recovered CAD master.
// It uses only the scan's PCA-plane extent to normalize its proportions. The
// unknown scan unit is never declared to be millimetres.
if (args.Length != 3)
    throw new ArgumentException("Usage: ScanGuidedRotorProxy prepared-scan.obj expected-sha256 new-private-output");

string source = Path.GetFullPath(args[0]);
string expectedHash = args[1].ToLowerInvariant();
string output = Path.GetFullPath(args[2]);
if (!System.Text.RegularExpressions.Regex.IsMatch(expectedHash, "^[0-9a-f]{64}$"))
    throw new ArgumentException("Expected a lowercase SHA-256 hash");
if (Hash(source) != expectedHash)
    throw new InvalidDataException("Input hash mismatch");
CreatePrivateDirectory(output);

var scan = ScanEnvelope.Read(source);
float voxelSize = scan.OuterRadius / 180f; // source-coordinate resolution, never mm.
using Library library = new(voxelSize);
var rotor = new ScanGuidedRotorProxy(scan.OuterRadius, scan.CentreXY);
rotor.Check();
float margin = scan.OuterRadius * 1.08f;
using Voxels field = new(library, rotor,
    new BBox3(new Vector3(scan.CentreXY.X - margin, scan.CentreXY.Y - margin, scan.MinZ - margin * 0.15f),
              new Vector3(scan.CentreXY.X + margin, scan.CentreXY.Y + margin, scan.MaxZ + margin * 0.15f)));
field.CalculateProperties(out float voxelVolume, out _);
using Mesh raw = new(field);
using Mesh clean = new(library);
for (int i = 0; i < raw.nTriangleCount(); i++)
{
    raw.GetTriangle(i, out Vector3 a, out Vector3 b, out Vector3 c);
    if (Vector3.Cross(b - a, c - a).LengthSquared() > 0)
        clean.nAddTriangle(a, b, c);
}
if (voxelVolume <= 0 || clean.nTriangleCount() == 0)
    throw new InvalidDataException("PicoGK created no visual proxy mesh");

string meshPath = Path.Combine(output, "scan-guided-rotor-visual-proxy.obj");
WriteTriangleSoupObj(clean, meshPath);
if (Hash(source) != expectedHash)
    throw new InvalidDataException("Input scan changed during processing");

var receipt = new
{
    status = "private_scan_guided_visual_topology_proxy",
    runtime = new { name = Library.strName(), version = Library.strVersion(), build = Library.strBuildInfo() },
    input_sha256 = expectedHash,
    input = new
    {
        pca_xy_centre_source_units = new[] { scan.CentreXY.X, scan.CentreXY.Y },
        pca_xy_outer_radius_source_units = scan.OuterRadius,
        pca_z_bounds_source_units = new[] { scan.MinZ, scan.MaxZ },
        source_unit = (string?)null
    },
    topology = new
    {
        blade_count = ScanGuidedRotorProxy.BladeCount,
        backing_disc_radius_ratio = ScanGuidedRotorProxy.BackingDiscRadiusRatio,
        hub_outer_radius_ratio = ScanGuidedRotorProxy.HubOuterRadiusRatio,
        blade_sweep_degrees_visual_hypothesis = ScanGuidedRotorProxy.BladeSweepDegrees,
        construction = "PicoGK implicit union of backing disc, raised hub and ten swept blades"
    },
    voxel_size_source_units = voxelSize,
    voxel_volume_source_units_cubed_conditional = voxelVolume,
    triangles = clean.nTriangleCount(),
    mesh_sha256 = Hash(meshPath),
    scan_geometry_preserved = false,
    dimensions_verified = false,
    blade_sections_verified = false,
    hub_bore_verified = false,
    interfaces_verified = false,
    solver_ready = false,
    manufacturing_authorized = false
};
File.WriteAllText(Path.Combine(output, "receipt.json"),
    JsonSerializer.Serialize(receipt, new JsonSerializerOptions { WriteIndented = true }) + "\n");
Console.WriteLine(JsonSerializer.Serialize(receipt));

static string Hash(string path) => Convert.ToHexString(SHA256.HashData(File.ReadAllBytes(path))).ToLowerInvariant();

static void CreatePrivateDirectory(string path)
{
    if (Directory.Exists(path) || File.Exists(path))
        throw new IOException("Use a new output directory; do not overwrite an earlier run");
    for (DirectoryInfo? parent = new(path); parent != null; parent = parent.Parent)
        if (Directory.Exists(Path.Combine(parent.FullName, ".git")) || File.Exists(Path.Combine(parent.FullName, ".git")))
        {
            string relative = Path.GetRelativePath(parent.FullName, path);
            if (!relative.StartsWith("work" + Path.DirectorySeparatorChar, StringComparison.Ordinal))
                throw new IOException("Geometry generated inside a checkout must stay under ignored work/");
            break;
        }
    Directory.CreateDirectory(path);
}

static void WriteTriangleSoupObj(Mesh mesh, string path)
{
    using var writer = new StreamWriter(path);
    writer.WriteLine("# PRIVATE PicoGK visual topology proxy; source coordinate unit is unknown");
    int index = 1;
    for (int i = 0; i < mesh.nTriangleCount(); i++)
    {
        mesh.GetTriangle(i, out Vector3 a, out Vector3 b, out Vector3 c);
        foreach (Vector3 point in new[] { a, b, c })
            writer.WriteLine(FormattableString.Invariant($"v {point.X:R} {point.Y:R} {point.Z:R}"));
        writer.WriteLine($"f {index} {index + 1} {index + 2}");
        index += 3;
    }
}

sealed record ScanEnvelope(Vector2 CentreXY, float OuterRadius, float MinZ, float MaxZ)
{
    public static ScanEnvelope Read(string path)
    {
        float minX = float.PositiveInfinity, minY = float.PositiveInfinity, minZ = float.PositiveInfinity;
        float maxX = float.NegativeInfinity, maxY = float.NegativeInfinity, maxZ = float.NegativeInfinity;
        bool found = false;
        foreach (string line in File.ReadLines(path))
        {
            string[] columns = line.Split((char[]?)null, StringSplitOptions.RemoveEmptyEntries);
            if (columns.Length != 4 || columns[0] != "v") continue;
            float x = float.Parse(columns[1], CultureInfo.InvariantCulture);
            float y = float.Parse(columns[2], CultureInfo.InvariantCulture);
            float z = float.Parse(columns[3], CultureInfo.InvariantCulture);
            if (!float.IsFinite(x) || !float.IsFinite(y) || !float.IsFinite(z))
                throw new InvalidDataException("Non-finite scan coordinate");
            minX = MathF.Min(minX, x); maxX = MathF.Max(maxX, x);
            minY = MathF.Min(minY, y); maxY = MathF.Max(maxY, y);
            minZ = MathF.Min(minZ, z); maxZ = MathF.Max(maxZ, z);
            found = true;
        }
        if (!found) throw new InvalidDataException("No position records in scan");
        Vector2 centre = new((minX + maxX) / 2f, (minY + maxY) / 2f);
        float outer = 0;
        foreach (string line in File.ReadLines(path))
        {
            string[] columns = line.Split((char[]?)null, StringSplitOptions.RemoveEmptyEntries);
            if (columns.Length != 4 || columns[0] != "v") continue;
            float x = float.Parse(columns[1], CultureInfo.InvariantCulture) - centre.X;
            float y = float.Parse(columns[2], CultureInfo.InvariantCulture) - centre.Y;
            outer = MathF.Max(outer, MathF.Sqrt(x * x + y * y));
        }
        if (!float.IsFinite(outer) || outer <= 0 || maxZ <= minZ)
            throw new InvalidDataException("Degenerate scan envelope");
        return new(centre, outer, minZ, maxZ);
    }
}

sealed class ScanGuidedRotorProxy : IImplicit
{
    readonly float radius;
    readonly Vector2 centreXY;
    public const int BladeCount = 10;
    public const float BackingDiscRadiusRatio = 0.59f;
    public const float HubOuterRadiusRatio = 0.27f;
    public const float BladeSweepDegrees = -23f;
    const float BoreRadiusRatio = 0.055f;
    const float BladeRootRadiusRatio = 0.43f;
    const float BladeOuterRadiusRatio = 0.985f;
    const float DiscHalfThicknessRatio = 0.075f;
    const float BladeBottomRatio = -0.065f;
    const float BladeTopRatio = 0.285f;
    const float HubBottomRatio = 0.05f;
    const float HubTopRatio = 0.31f;

    public ScanGuidedRotorProxy(float radius, Vector2 centreXY)
    {
        this.radius = radius;
        this.centreXY = centreXY;
    }

    static float Fold(float angle)
    {
        float period = 2 * MathF.PI / BladeCount;
        return angle - period * MathF.Round(angle / period);
    }

    public float fSignedDistance(in Vector3 p)
    {
        float x = p.X - centreXY.X;
        float y = p.Y - centreXY.Y;
        float r = MathF.Sqrt(x * x + y * y);
        float bore = BoreRadiusRatio * radius - r;
        float disc = MathF.Max(MathF.Abs(p.Z) - DiscHalfThicknessRatio * radius,
            r - BackingDiscRadiusRatio * radius);
        // The hub is an annular raised cap; this opening is visual, not a measured bore.
        float hub = MathF.Max(MathF.Max(HubBottomRatio * radius - p.Z, p.Z - HubTopRatio * radius),
            MathF.Max(BoreRadiusRatio * radius - r, r - HubOuterRadiusRatio * radius));
        float body = MathF.Min(disc, hub);
        float span = Math.Clamp((r - BladeRootRadiusRatio * radius) /
                                ((BladeOuterRadiusRatio - BladeRootRadiusRatio) * radius), 0, 1);
        float centreline = BladeSweepDegrees * MathF.PI / 180f * span * span;
        float tangential = r * MathF.Sin(Fold(MathF.Atan2(y, x) - centreline));
        float chord = radius * (0.14f + 0.12f * span);
        float blade = MathF.Max(MathF.Abs(tangential) - chord / 2,
            MathF.Max(BladeRootRadiusRatio * radius - r,
                MathF.Max(r - BladeOuterRadiusRatio * radius,
                    MathF.Max(BladeBottomRatio * radius - p.Z, p.Z - BladeTopRatio * radius))));
        body = MathF.Min(body, blade);
        return MathF.Max(body, bore);
    }

    public void Check()
    {
        if (!float.IsFinite(radius) || radius <= 0) throw new ArgumentException("Invalid scan-derived radius");
        float sampleR = 0.78f * radius;
        float span = (sampleR / radius - BladeRootRadiusRatio) /
                     (BladeOuterRadiusRatio - BladeRootRadiusRatio);
        float bladeAngle = BladeSweepDegrees * MathF.PI / 180f * span * span;
        if (fSignedDistance(new Vector3(centreXY.X + sampleR * MathF.Cos(bladeAngle), centreXY.Y + sampleR * MathF.Sin(bladeAngle), 0.12f * radius)) >= 0)
            throw new InvalidDataException("Expected blade is absent");
        float gapAngle = bladeAngle + MathF.PI / BladeCount;
        if (fSignedDistance(new Vector3(centreXY.X + sampleR * MathF.Cos(gapAngle), centreXY.Y + sampleR * MathF.Sin(gapAngle), 0.12f * radius)) <= 0)
            throw new InvalidDataException("Expected inter-blade gap is closed");
        if (fSignedDistance(new Vector3(centreXY.X, centreXY.Y, 0)) <= 0)
            throw new InvalidDataException("Visual bore is closed");
    }
}
