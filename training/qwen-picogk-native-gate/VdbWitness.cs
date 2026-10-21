using System.Text.Json;
using PicoGK;

// Serialize the original native field, without rebuilding it from STL.
static class VdbWitness
{
    public static void SaveAndCheck(Voxels solid, Library lib, string path)
    {
        using (OpenVdbFile output = new(lib))
        {
            output.nAdd(solid, "model_geometry");
            output.SaveToFile(path);
        }
        using OpenVdbFile input = new(lib, path);
        using Voxels restored = input.voxGet("model_geometry");
        solid.CalculateProperties(out float before, out BBox3 beforeBox);
        restored.CalculateProperties(out float after, out BBox3 afterBox);
        bool metadata = restored.oMetaData().bGetValueAt("PicoGK.VoxelSize", out float meters);
        bool equal = solid.bIsEqual(restored);
        bool passed = input.nFieldCount() == 1 && input.strFieldName(0) == "model_geometry" &&
            input.eFieldType(0) == OpenVdbFile.EFieldType.Voxels && input.bIsPicoGKCompatible() &&
            input.fPicoGKVoxelSizeMM() == lib.fVoxelSize && metadata &&
            meters == lib.fVoxelSize / 1000f && equal && before > 0 && before == after &&
            beforeBox.vecMin == afterBox.vecMin && beforeBox.vecMax == afterBox.vecMax;
        File.WriteAllText(path + ".json", JsonSerializer.Serialize(new {
            passed, field_name = input.strFieldName(0), field_type = input.strFieldType(0),
            voxel_mm = input.fPicoGKVoxelSizeMM(), voxel_metadata_m = meters,
            native_fields_equal = equal, before_volume_mm3 = before, after_volume_mm3 = after,
            bounds_equal = beforeBox.vecMin == afterBox.vecMin && beforeBox.vecMax == afterBox.vecMax,
            original_field_serialized = true, reconstructed_from_stl = false
        }));
        if (!passed) throw new InvalidDataException("Native VDB roundtrip failed");
    }
}
