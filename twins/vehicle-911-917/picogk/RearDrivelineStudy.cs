using System.Numerics;
using System.Text.Json;
using PicoGK;

namespace Vehicle911917;

internal static partial class Program
{
    private static void RunAxleStudy()
    {
        using JsonDocument input = JsonDocument.Parse(File.ReadAllText(Path.Combine(Output, "study-inputs-f14.json")));
        JsonElement c = input.RootElement;
        foreach (JsonElement entry in c.GetProperty("inputs").EnumerateArray())
        {
            using var stream = File.OpenRead(Path.Combine(Root, entry.GetProperty("path").GetString()!));
            if (!Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(stream)).Equals(
                    entry.GetProperty("sha256").GetString(), StringComparison.OrdinalIgnoreCase))
                throw new InvalidDataException("F14 inputs changed; rerun analytical preparation");
        }
        if (VoxelMm > 2 || VoxelMm <= 0 || !float.IsFinite(VoxelMm))
            throw new InvalidDataException("F14 requires voxel size in (0, 2] mm");
        using JsonDocument f12 = LoadJson("twins/vehicle-911-917/picogk-full-vehicle-f12.json");
        using JsonDocument f13 = LoadJson("twins/vehicle-911-917/picogk-mechanical-f13.json");
        Library lib = Library.oLibrary();
        float x = c.GetProperty("rear_axle_x_mm").GetSingle(), z = c.GetProperty("axle_z_mm").GetSingle();
        float travel = c.GetProperty("wheel_vertical_travel_cases_mm").EnumerateArray().Max(v => v.GetSingle());
        float clearance = c.GetProperty("required_clearance_mm").GetSingle();
        float step = c.GetProperty("sample_step_mm").GetSingle();
        // Each linear-motion sample covers its neighbours by step/2; the voxel guard is additional.
        float allowance = clearance + step / 2 + VoxelMm * c.GetProperty("voxel_guard_cells").GetSingle();
        Vector3 min = Vec3(c.GetProperty("inspection_bounds_mm")[0]), max = Vec3(c.GetProperty("inspection_bounds_mm")[1]);
        using Voxels clip = Box(lib, max - min, (max + min) / 2);
        using Voxels transmission = BuildTransmission(lib, f13.RootElement.GetProperty("transaxle"),
            c.GetProperty("gearbox_bounds_x_mm")[0].GetSingle(), c.GetProperty("gearbox_bounds_x_mm")[1].GetSingle(),
            x, f13.RootElement.GetProperty("shaft_reference_z_mm").GetSingle(), z);
        var cases = new Dictionary<string, object?>();
        Viewer viewer = Library.oViewer();
        viewer.SetBackgroundColor("F3F4F6");
        viewer.SetFov(MathF.PI / 6);
        viewer.SetGroupMaterial(0, "64748B", 0.15f, 0.65f);
        viewer.SetGroupMaterial(1, "22A89CAA", 0.1f, 0.7f);
        viewer.SetGroupMaterial(2, "D52E36", 0, 0.7f);
        viewer.SetGroupMaterial(3, "27364A", 0.1f, 0.7f);
        viewer.SetGroupMaterial(4, "C99A4F", 0.1f, 0.7f);
        foreach (string name in new[] {"baseline", "candidate"})
        {
            bool candidate = name == "candidate";
            float track = c.GetProperty(name + "_rear_track_mm").GetSingle();
            using Voxels frame = StudyFrame(lib, f12.RootElement.GetProperty("rear_structure_corridors"), c, candidate);
            frame.BoolIntersect(clip);
            using Voxels nominal = BuildHalfshafts(lib, f13.RootElement, x, track, z);
            using Voxels sweep = ShaftSweep(lib, c, track, travel, step, 0);
            using Voxels keepout = ShaftSweep(lib, c, track, travel, step, allowance);
            using Voxels clash = sweep & frame;
            using Voxels wheels = new(lib);
            float width = c.GetProperty("wheel_width_mm").GetSingle(), radius = c.GetProperty("wheel_radius_mm").GetSingle();
            foreach (float side in new[] {-1f, 1f})
            {
                using Voxels tyre = Frustum(lib, new(x, side * track / 2 - width / 2, z), new(x, side * track / 2 + width / 2, z), radius, radius);
                using Voxels hole = Frustum(lib, new(x, side * track / 2 - width / 2 - 5, z), new(x, side * track / 2 + width / 2 + 5, z), 190, 190);
                tyre.BoolSubtract(hole);
                wheels.BoolAdd(tyre);
            }
            // Conservative continuous tyre sweep: solid bounding boxes, including required clearance and voxel guard.
            using Voxels wheelKeepout = new(lib);
            foreach (float side in new[] {-1f, 1f})
                AddBox(wheelKeepout, lib, new(2 * (radius + allowance), width + 2 * allowance, 2 * (radius + travel + allowance)), new(x, side * track / 2, z));
            cases[name] = new Dictionary<string, object?> {
                ["track_mm"] = track,
                ["nominal_shafts_vs_frame"] = Collision(nominal, frame),
                ["sampled_sweep_vs_frame"] = Collision(sweep, frame),
                ["continuous_clearance_keepout_vs_frame"] = Collision(keepout, frame),
                ["swept_tyre_box_keepout_vs_frame"] = Collision(wheelKeepout, frame),
                ["transaxle_schematic_vs_frame"] = Collision(transmission, frame)
            };
            foreach (var layer in new[] {("frame", frame), ("nominal-shafts", nominal), ("swept-shafts", sweep), ("clearance-keepout", keepout), ("interference", clash)})
            {
                layer.Item2.SaveToVdbFile(Path.Combine(Output, $"{name}-{layer.Item1}-f14.vdb"));
                if (!layer.Item2.bIsEmpty())
                {
                    using Mesh mesh = new(layer.Item2);
                    mesh.SaveToStlFile(Path.Combine(Output, $"{name}-{layer.Item1}-f14.stl"));
                }
            }
            viewer.RemoveAllObjects();
            viewer.Add(frame, 0); viewer.Add(sweep, 1); viewer.Add(clash, 2); viewer.Add(wheels, 3); viewer.Add(transmission, 4);
            Capture(viewer, viewer.qOrientationHome, $"{name}-isometric-f14.tga");
            Capture(viewer, viewer.qOrientationRight, $"{name}-rear-f14.tga");
        }
        File.WriteAllText(Path.Combine(Output, "picogk-driveline-report-f14.json"), JsonSerializer.Serialize(new {
            phase = "F14", kernel = Library.strVersion(), voxel_size_mm = VoxelMm,
            input_sha256 = Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(File.ReadAllBytes(Path.Combine(Output, "study-inputs-f14.json")))),
            continuous_keepout_allowance_mm = allowance,
            inspection_bounds_mm = c.GetProperty("inspection_bounds_mm").Clone(),
            scope = "rear_bay_only_linear_vertical_hub_motion_not_suspension_validation",
            cases, release_gates = c.GetProperty("release_gates").Clone()
        }, new JsonSerializerOptions { WriteIndented = true }) + "\n");
        Library.EndTask();
    }

    private static Voxels StudyFrame(Library lib, JsonElement frame, JsonElement c, bool candidate)
    {
        Voxels result = new(lib);
        Vector3 railSize = Vec3(frame.GetProperty("rail_size_mm"));
        foreach (JsonElement item in frame.GetProperty("rail_centres_mm").EnumerateArray())
        {
            Vector3 centre = Vec3(item);
            if (candidate) centre = new(centre.X, MathF.Sign(centre.Y) * c.GetProperty("candidate_rail_y_mm").GetSingle(), c.GetProperty("candidate_rail_z_mm").GetSingle());
            AddBox(result, lib, railSize, centre);
        }
        foreach (JsonElement item in (candidate ? c.GetProperty("candidate_crossmember_x_mm") : frame.GetProperty("crossmember_x_mm")).EnumerateArray())
            AddBox(result, lib, Vec3(frame.GetProperty("crossmember_size_mm")), new(item.GetSingle(), 0, candidate ? c.GetProperty("candidate_rail_z_mm").GetSingle() : 255));
        AddBox(result, lib, new(2351, candidate ? c.GetProperty("candidate_floor_width_mm").GetSingle() : 1575, 20),
            new(2540.5f, 0, candidate ? c.GetProperty("candidate_floor_z_mm").GetSingle() : 180));
        return result;
    }

    private static Voxels ShaftSweep(Library lib, JsonElement c, float track, float travel, float step, float allowance)
    {
        Voxels result = new(lib);
        float x = c.GetProperty("rear_axle_x_mm").GetSingle(), z = c.GetProperty("axle_z_mm").GetSingle();
        float shaft = c.GetProperty("shaft_radius_mm").GetSingle() + allowance;
        float joint = c.GetProperty("joint_radius_mm").GetSingle() + allowance;
        int samples = (int)MathF.Ceiling(2 * travel / step);
        foreach (float side in new[] {-1f, 1f})
        {
            Vector3 inner = new(x, side * c.GetProperty("flange_half_span_mm").GetSingle(), z);
            using Voxels innerJoint = Voxels.voxSphere(lib, inner, joint);
            result.BoolAdd(innerJoint);
            for (int i = 0; i <= samples; i++)
            {
                Vector3 outer = new(x, side * track / 2, z - travel + 2 * travel * i / samples);
                using Voxels beam = Voxels.voxLatticeBeam(lib, inner, shaft, outer, shaft);
                using Voxels outerJoint = Voxels.voxSphere(lib, outer, joint);
                result.BoolAdd(beam); result.BoolAdd(outerJoint);
            }
        }
        return result;
    }
}
