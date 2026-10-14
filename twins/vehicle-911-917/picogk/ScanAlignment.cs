using System.Numerics;
using System.Security.Cryptography;
using System.Text.Json;

namespace Vehicle911917;

internal static partial class Program
{
    private static Matrix4x4 ValidatedAlignment(JsonElement alignment, string root, string scanPath)
    {
        if (alignment.GetProperty("phase").GetString() != "F13"
            || alignment.GetProperty("status").GetString() != "scan_row_alignment_corrected_not_physical_datum_validation"
            || new[] { "crankshaft_axis_measured", "mounting_face_measured", "scale_verified", "physical_orientation_verified" }
                .Any(key => alignment.GetProperty(key).GetBoolean()))
            throw new InvalidDataException("Unqualified F13 alignment receipt required");

        string Hash(string path)
        {
            using var stream = File.OpenRead(path);
            return Convert.ToHexString(SHA256.HashData(stream));
        }

        JsonElement inputs = alignment.GetProperty("inputs_sha256");
        foreach (string path in new[] {
            "work/911-917-packaging-f1/packaging-report-f1.json",
            "work/917-engine/scan-metrology-f13-report.json",
            "twins/vehicle-911-917/picogk-mechanical-f13.json",
            "work/911-917-picogk-f10/scan-preparation-report-f10.json",
            "twins/vehicle-911-917/source/prepare_picogk_scan_f10.py",
            "twins/vehicle-911-917/source/prepare_picogk_alignment_f13.py" })
            if (!Hash(Path.Combine(root, path)).Equals(inputs.GetProperty(path).GetString(), StringComparison.OrdinalIgnoreCase))
                throw new InvalidDataException($"F13 alignment input changed: {path}");
        if (!Hash(scanPath).Equals(alignment.GetProperty("input_stl_sha256").GetString(), StringComparison.OrdinalIgnoreCase))
            throw new InvalidDataException("F13 prepared scan changed");

        JsonElement rows = alignment.GetProperty("matrix4x4_row_vector");
        if (rows.GetArrayLength() != 4 || rows.EnumerateArray().Any(row => row.GetArrayLength() != 4))
            throw new InvalidDataException("F13 alignment must be a 4x4 matrix");
        float[] v = rows.EnumerateArray().SelectMany(row => row.EnumerateArray().Select(value => value.GetSingle())).ToArray();
        var matrix = new Matrix4x4(v[0], v[1], v[2], v[3], v[4], v[5], v[6], v[7],
            v[8], v[9], v[10], v[11], v[12], v[13], v[14], v[15]);
        var axes = new[] { new Vector3(v[0], v[1], v[2]), new Vector3(v[4], v[5], v[6]), new Vector3(v[8], v[9], v[10]) };
        if (v.Any(value => !float.IsFinite(value))
            || MathF.Abs(v[3]) > 1e-6f || MathF.Abs(v[7]) > 1e-6f || MathF.Abs(v[11]) > 1e-6f || MathF.Abs(v[15] - 1) > 1e-6f
            || axes.Any(axis => MathF.Abs(axis.LengthSquared() - 1) > 1e-6f)
            || MathF.Abs(Vector3.Dot(axes[0], axes[1])) > 1e-6f
            || MathF.Abs(Vector3.Dot(axes[0], axes[2])) > 1e-6f
            || MathF.Abs(Vector3.Dot(axes[1], axes[2])) > 1e-6f
            || MathF.Abs(matrix.GetDeterminant() - 1) > 1e-6f)
            throw new InvalidDataException("Finite rigid row-vector F13 alignment required");
        return matrix;
    }
}
