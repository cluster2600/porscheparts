using System.Numerics;
using System.Text.Json;
using PicoGK;

namespace ZesadMonocoque;

/// Implicit from a lambda: negative inside, roughly millimetres near the
/// zero level. PicoGK re-levels the narrow band when it voxelizes.
public sealed class Fn : IImplicit
{
    readonly Func<Vector3, float> _f;
    public Fn(Func<Vector3, float> f) => _f = f;
    public float fSignedDistance(in Vector3 vec) => _f(vec);
}

/// Per-station body data from prep_envelope.py. World frame: X = -d
/// (forward), Y left, Z up, millimetres; d is behind the plate 0 line.
public sealed class Stations
{
    public required double[] d, top, bottom, half_width, belt;
    public double front_axle_d, rear_axle_d, front_bulkhead_d, rear_bulkhead_d;
    public required double[] door_d, door_z;

    public static Stations Load(string path) =>
        JsonSerializer.Deserialize<Stations>(File.ReadAllText(path), new JsonSerializerOptions { IncludeFields = true })!;

    float At(double[] a, float dd)
    {
        if (dd <= d[0]) return (float)a[0];
        if (dd >= d[^1]) return (float)a[^1];
        int i = Array.BinarySearch(d, dd);
        if (i >= 0) return (float)a[i];
        i = ~i;
        double t = (dd - d[i - 1]) / (d[i] - d[i - 1]);
        return (float)(a[i - 1] + t * (a[i] - a[i - 1]));
    }
    public float Top(float dd) => At(top, dd);
    public float Bottom(float dd) => At(bottom, dd);
    public float Width(float dd) => At(half_width, dd);
    public float Belt(float dd) => At(belt, dd);
}

/// The aperture fields of build_shell.opening_fields(), sampled every 10 mm
/// on a half-car grid; > 0 inside the aperture. Trilinear, |y| symmetric.
public sealed class Apertures
{
    readonly float[][] _ch;
    readonly float _d0, _y0, _z0, _h;
    readonly int _nd, _ny, _nz;
    public readonly string[] Names;

    public Apertures(string dir)
    {
        using var meta = JsonDocument.Parse(File.ReadAllText(Path.Combine(dir, "fields.json")));
        var r = meta.RootElement;
        Names = r.GetProperty("channels").EnumerateArray().Select(e => e.GetString()!).ToArray();
        _d0 = r.GetProperty("d0").GetSingle(); _y0 = r.GetProperty("y0").GetSingle(); _z0 = r.GetProperty("z0").GetSingle();
        _h = r.GetProperty("step_mm").GetSingle();
        _nd = r.GetProperty("nd").GetInt32(); _ny = r.GetProperty("ny").GetInt32(); _nz = r.GetProperty("nz").GetInt32();
        byte[] raw = File.ReadAllBytes(Path.Combine(dir, "fields.bin"));
        int n = _nd * _ny * _nz;
        if (raw.Length != 4L * n * Names.Length) throw new Exception("fields.bin does not match fields.json");
        _ch = new float[Names.Length][];
        for (int k = 0; k < Names.Length; k++)
        {
            _ch[k] = new float[n];
            Buffer.BlockCopy(raw, 4 * n * k, _ch[k], 0, 4 * n);
        }
    }

    public int Index(string name) => Array.IndexOf(Names, name) is var i and >= 0 ? i : throw new Exception(name);

    /// Field value at a world point; far outside the grid, -1000 (no aperture).
    public float Value(int k, in Vector3 p)
    {
        float fd = (-p.X - _d0) / _h, fy = (MathF.Abs(p.Y) - _y0) / _h, fz = (p.Z - _z0) / _h;
        if (fd < 0 || fy < 0 || fz < 0 || fd > _nd - 1 || fy > _ny - 1 || fz > _nz - 1) return -1000f;
        int i = Math.Min((int)fd, _nd - 2), j = Math.Min((int)fy, _ny - 2), l = Math.Min((int)fz, _nz - 2);
        float u = fd - i, v = fy - j, w = fz - l;
        float[] a = _ch[k];
        int s = _ny * _nz, b = (i * _ny + j) * _nz + l;
        float c00 = a[b] * (1 - w) + a[b + 1] * w, c01 = a[b + _nz] * (1 - w) + a[b + _nz + 1] * w;
        float c10 = a[b + s] * (1 - w) + a[b + s + 1] * w, c11 = a[b + s + _nz] * (1 - w) + a[b + s + _nz + 1] * w;
        return (c00 * (1 - v) + c01 * v) * (1 - u) + (c10 * (1 - v) + c11 * v) * u;
    }

    /// World bounding box of the grid cells where channel k is positive.
    public BBox3 Bounds(int k, float pad)
    {
        float[] a = _ch[k];
        int i0 = _nd, i1 = -1, j1 = -1, l0 = _nz, l1 = -1;
        for (int i = 0; i < _nd; i++)
            for (int j = 0; j < _ny; j++)
                for (int l = 0; l < _nz; l++)
                    if (a[(i * _ny + j) * _nz + l] > 0)
                    {
                        i0 = Math.Min(i0, i); i1 = Math.Max(i1, i); j1 = Math.Max(j1, j);
                        l0 = Math.Min(l0, l); l1 = Math.Max(l1, l);
                    }
        if (i1 < 0) throw new Exception($"aperture {Names[k]} is empty");
        float ymax = _y0 + j1 * _h + pad;
        return new BBox3(new Vector3(-(_d0 + i1 * _h) - pad, -ymax, _z0 + l0 * _h - pad),
                         new Vector3(-(_d0 + i0 * _h) + pad, ymax, _z0 + l1 * _h + pad));
    }
}
