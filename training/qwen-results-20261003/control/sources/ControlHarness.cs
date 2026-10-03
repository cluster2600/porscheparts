// Executed deterministic synthetic control; derived from the preserved preparation harness.
#nullable enable
using System;
using System.Collections.Generic;
using System.IO;
using System.Numerics;
using System.Text.Json;
using PicoGK;

public static class ControlHarness
{
    private static void Require(bool condition, string message)
    {
        if (!condition) throw new InvalidOperationException(message);
    }

    private static object Inspect(Library library, float outerDiameterMm, string outputDirectory)
    {
        var solid = GeneratedSpacer.Build(library, outerDiameterMm, 20, 3, "mm");
        solid.CalculateProperties(out float volumeMm3, out BBox3 bounds);
        Require(float.IsFinite(volumeMm3) && volumeMm3 > 0, "Nonempty finite volume");
        var mesh = new Mesh(solid);
        Require(mesh.nTriangleCount() > 0, "Nonempty mesh");
        // A sampled axial bore check; not a proof of arbitrary mesh topology.
        for (int sample = -4; sample <= 16; ++sample)
            Require(!solid.bIsInside(new Vector3(0, 0, sample * 0.25f)),
                "Centered bore must stay empty through the thickness");
        float materialRadius = (outerDiameterMm + 20) / 4;
        Require(solid.bIsInside(new Vector3(materialRadius, 0, 1.5f)),
            "Annular material must be present");
        Require(!solid.bIsInside(new Vector3(outerDiameterMm / 2 + 1, 0, 1.5f)),
            "Point beyond outer diameter must stay outside");
        // Each circumferential bore point is inside the intended empty region.
        for (int angle = 0; angle < 360; angle += 10)
        {
            float theta = angle * MathF.PI / 180;
            Require(!solid.bIsInside(new Vector3(9 * MathF.Cos(theta), 9 * MathF.Sin(theta), 1.5f)),
                "Bore region sample must stay empty");
            Require(solid.bIsInside(new Vector3(11 * MathF.Cos(theta), 11 * MathF.Sin(theta), 1.5f)),
                "Material around bore must exist");
        }
        var unitNames = Enum.GetNames(typeof(Mesh.EStlUnit));
        string? mmName = Array.Find(unitNames, x => x.Equals("MM", StringComparison.OrdinalIgnoreCase));
        Require(mmName is not null, "Explicit MM STL enum required; no guessed numeric enum");
        var mm = (Mesh.EStlUnit)Enum.Parse(typeof(Mesh.EStlUnit), mmName!);
        string exportPath = Path.Combine(outputDirectory, $"synthetic-spacer-od{outerDiameterMm:0}-id20-t3-mm.stl");
        mesh.SaveToStlFile(exportPath, mm, null, 1);
        return new
        {
            outer_diameter_mm = outerDiameterMm, inner_diameter_mm = 20,
            thickness_mm = 3, unit = "mm", volume_mm3 = volumeMm3,
            analytic_volume_mm3 = Math.PI / 4 * (outerDiameterMm * outerDiameterMm - 400) * 3,
            bbox_min_mm = new[] { bounds.vecMin.X, bounds.vecMin.Y, bounds.vecMin.Z },
            bbox_max_mm = new[] { bounds.vecMax.X, bounds.vecMax.Y, bounds.vecMax.Z },
            triangles = mesh.nTriangleCount(), sampled_bore_empty = true,
            stl_export = exportPath, stl_unit_enum = mmName, stl_enum_names = unitNames,
            circumferential_bore_checks = 36, circumferential_material_checks = 36,
            numeric_discretization_gate = "Record and review bounds/volume against analytic references before model output"
        };
    }

    private static void ExpectRejected(string name, Func<Voxels> build, List<string> checks)
    {
        try
        {
            _ = build();
        }
        catch (ArgumentException)
        {
            checks.Add(name);
            return;
        }
        throw new InvalidOperationException("Input was not explicitly rejected: " + name);
    }

    public static void Main(string[] args)
    {
        Require(args.Length == 1 && Directory.Exists(args[0]), "Existing isolated export directory required");
        using var library = new Library(0.25f);
        var checks = new List<string>();
        ExpectRejected("unknown_outer", () => GeneratedSpacer.Build(library, null, 20, 3, "mm"), checks);
        ExpectRejected("unknown_inner", () => GeneratedSpacer.Build(library, 40, null, 3, "mm"), checks);
        ExpectRejected("unknown_thickness", () => GeneratedSpacer.Build(library, 40, 20, null, "mm"), checks);
        ExpectRejected("nan_inner", () => GeneratedSpacer.Build(library, 40, float.NaN, 3, "mm"), checks);
        ExpectRejected("infinite_thickness", () => GeneratedSpacer.Build(library, 40, 20, float.PositiveInfinity, "mm"), checks);
        ExpectRejected("negative_outer", () => GeneratedSpacer.Build(library, -40, 20, 3, "mm"), checks);
        ExpectRejected("zero_inner", () => GeneratedSpacer.Build(library, 40, 0, 3, "mm"), checks);
        ExpectRejected("inner_equals_outer", () => GeneratedSpacer.Build(library, 40, 40, 3, "mm"), checks);
        ExpectRejected("inner_exceeds_outer", () => GeneratedSpacer.Build(library, 40, 41, 3, "mm"), checks);
        ExpectRejected("wrong_unit", () => GeneratedSpacer.Build(library, 40, 20, 3, "cm"), checks);
        ExpectRejected("unknown_unit", () => GeneratedSpacer.Build(library, 40, 20, 3, null), checks);
        object nominal = Inspect(library, 40, args[0]), modified = Inspect(library, 45, args[0]);
        Console.WriteLine(JsonSerializer.Serialize(new
        {
            status = "control_runtime_checks_only",
            voxel_size_mm = 0.25, invalid_inputs_rejected = checks,
            nominal, modified, source_same_for_both_builds = true,
            mesh_topology_fully_checked = false,
            model_or_physical_qualification = false
        }));
    }
}
