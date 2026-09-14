using System.Numerics;
using System.Security.Cryptography;
using System.Text.Json;
using PicoGK;

const string PartId = "993-ENG-PISTON-CP1-GALLERY-F0-0001";
const float DensityGPerCm3 = 2.67f;
const float BaselineGalleryDiameterMm = 7.0f;
const float BaselineCrownLigamentMm = 5.5f;
const float ComparisonYieldMpa = 297.0f;
const float SyntheticPressureMpa = 12.0f;
const float CrownRadiusMm = 41.0f;
const float Poisson = 0.33f;
const float TargetAmbientYieldRatio = 1.50f;
const string NativeImageId = "sha256:f38695f9ecc99ceef65c5e1fe02adf5dbfa95ee1ae925f95fd47bdba9ebb6178";

if (args.Length != 3)
{
    Console.Error.WriteLine("Usage: PistonPicogkScreen INPUT_BINARY_STL OUTPUT_DIRECTORY REPORT_JSON");
    return 2;
}

string inputPath = Path.GetFullPath(args[0]);
string outputDirectory = Path.GetFullPath(args[1]);
string reportPath = Path.GetFullPath(args[2]);
Directory.CreateDirectory(outputDirectory);
Directory.CreateDirectory(Path.GetDirectoryName(reportPath)!);

Variant[] variants =
[
    new("P0_reference_voxelisee", 0, 0.0f, 7.0f, 0.0f),
    new("P1_six_poches", 6, 1.50f, 7.0f, 0.0f),
    new("P2_eight_poches", 8, 1.60f, 7.0f, 0.0f),
    new("P3_galerie_8_ribs", 6, 1.50f, 8.0f, 1.60f),
    new("P4_galerie_8p5_ribs", 8, 1.50f, 8.5f, 1.80f),
    new("P5_light_max_screen", 10, 1.70f, 9.0f, 1.60f),
];

try
{
    const float voxelSizeMm = 0.50f;
    using Library library = new(voxelSizeMm);
    using Mesh sourceMesh = Mesh.mshFromStlFile(
        inputPath,
        Mesh.EStlUnit.MM,
        libSet: library);
    using Voxels sourceVoxels = new(sourceMesh);
    sourceVoxels.CalculateProperties(out float sourceVolumeMm3, out _);

    List<object> results = [];
    foreach (Variant variant in variants)
    {
        using Voxels candidate = new(sourceVoxels);

        if (variant.PocketCount > 0)
        {
            using Lattice pockets = BuildOpenSkirtPockets(library, variant);
            using Voxels pocketVoxels = new(pockets);
            candidate.BoolSubtract(pocketVoxels);
        }

        if (variant.GalleryDiameterMm > BaselineGalleryDiameterMm)
        {
            using Lattice gallery = BuildToroidalGallery(library, variant.GalleryDiameterMm);
            using Voxels galleryVoxels = new(gallery);
            candidate.BoolSubtract(galleryVoxels);
        }

        if (variant.RibRadiusMm > 0.0f)
        {
            using Lattice ribs = BuildPinToCrownRibs(library, variant.RibRadiusMm);
            using Voxels ribVoxels = new(ribs);
            candidate.BoolAdd(ribVoxels);
        }

        candidate.CalculateProperties(out float volumeMm3, out _);
        using Mesh candidateMesh = new(candidate);
        string outputPath = Path.Combine(outputDirectory, variant.Id + ".stl");
        candidateMesh.SaveToStlFile(outputPath, Mesh.EStlUnit.MM);

        float massG = volumeMm3 / 1000.0f * DensityGPerCm3;
        float crownLigamentMm = BaselineCrownLigamentMm
            - 0.5f * (variant.GalleryDiameterMm - BaselineGalleryDiameterMm);
        float plateFactor = (3.0f + Poisson) / 8.0f;
        float crownStressMpa = plateFactor * SyntheticPressureMpa
            * CrownRadiusMm * CrownRadiusMm
            / (crownLigamentMm * crownLigamentMm);
        float yieldRatio = ComparisonYieldMpa / crownStressMpa;
        float hydraulicPressureRatio = MathF.Pow(
            BaselineGalleryDiameterMm / variant.GalleryDiameterMm,
            4.0f);
        float galleryWettedAreaRatio =
            variant.GalleryDiameterMm / BaselineGalleryDiameterMm;
        float outsidePocketLigamentMm = variant.PocketCount == 0
            ? 8.5f
            : 49.5f - (45.25f + variant.PocketRadiusMm);
        bool structuralProxyPass = yieldRatio >= TargetAmbientYieldRatio;

        results.Add(new
        {
            variant_id = variant.Id,
            picogk_operations = new
            {
                open_skirt_pocket_count = variant.PocketCount,
                open_skirt_pocket_radius_mm = variant.PocketRadiusMm,
                gallery_hydraulic_diameter_mm = variant.GalleryDiameterMm,
                pin_to_crown_rib_radius_mm = variant.RibRadiusMm,
            },
            geometry = new
            {
                volume_mm3 = volumeMm3,
                mass_g = massG,
                mass_change_from_brep_percent =
                    100.0f * (massG - 681.32f) / 681.32f,
                triangle_count = candidateMesh.nTriangleCount(),
                outside_pocket_ligament_mm = outsidePocketLigamentMm,
                output_stl = Path.GetFileName(outputPath),
                output_sha256 = Sha256(outputPath),
            },
            thermal_hydraulic_proxies = new
            {
                gallery_wetted_area_ratio = galleryWettedAreaRatio,
                laminar_pressure_loss_ratio_at_equal_flow = hydraulicPressureRatio,
                limitation = "Geometric ratios only; no CHT, oil-jet capture, acceleration, boiling or measured boundary condition.",
            },
            structural_screen = new
            {
                analytical_crown_ligament_mm = crownLigamentMm,
                clamped_plate_stress_mpa = crownStressMpa,
                ambient_yield_to_stress_ratio = yieldRatio,
                target_ambient_yield_ratio = TargetAmbientYieldRatio,
                passes_target = structuralProxyPass,
                ribs_credited_in_equation = false,
                limitation = "The plate proxy cannot credit PicoGK ribs and is not hot nonlinear contact FEA or fatigue.",
            },
            eligible_for_selection = false,
            rejection_reason = structuralProxyPass
                ? "Hot strength, fatigue, interfaces and correlated thermal fields are still missing."
                : "Synthetic ambient plate margin is below the provisional 1.50 target.",
        });
    }

    var report = new
    {
        schema_version = "1.0.0",
        part_id = PartId,
        status = "picogk_f0_multiobjective_geometry_screen_no_selected_design",
        executed = true,
        runtime = new
        {
            picogk_version = "2.3.0",
            native_runtime_abi = "picogk.26.2",
            native_image_id = NativeImageId,
            execution_environment = "Kali linux/amd64 Docker with network disabled",
            voxel_size_mm = voxelSizeMm,
            source_mesh_sha256 = Sha256(inputPath),
            source_mesh_triangle_count = sourceMesh.nTriangleCount(),
            source_voxel_volume_mm3 = sourceVolumeMm3,
        },
        optimization_problem = new
        {
            objectives = new[]
            {
                "minimize CP1 mass",
                "maximize cooling-gallery wetted area",
                "minimize gallery pressure loss at equal oil flow",
            },
            constraints = new[]
            {
                "ambient analytical yield-to-stress ratio >= 1.50",
                "preserve all synthetic exterior, ring, pin and machining interfaces",
                "keep skirt pockets open for powder evacuation",
                "require hot nonlinear thermo-mechanical FEA and fatigue before selection",
            },
            authority = "All design volumes, loads and targets are F0 hypotheses, not measured Porsche 993 piston data.",
        },
        variants = results,
        decision = new
        {
            selected_variant = (string?)null,
            reason = "No variant can be honestly selected before hot material allowables, measured interfaces, transient loads, CHT and nonlinear fatigue analysis exist.",
            picogk_role = "Executed geometry generator and Boolean field kernel; not a structural or thermal solver.",
            manufacturing_authorized = false,
            engine_operation_authorized = false,
        },
    };

    File.WriteAllText(
        reportPath,
        JsonSerializer.Serialize(report, new JsonSerializerOptions { WriteIndented = true }) + Environment.NewLine);
    Console.WriteLine($"PICOGK_PISTON_SCREEN_PASS variants={variants.Length} selected=none");
    return 0;
}
catch (Exception exception)
{
    Console.Error.WriteLine($"PICOGK_PISTON_SCREEN_FAIL {exception.GetType().Name}: {exception.Message}");
    return 1;
}

static Lattice BuildOpenSkirtPockets(Library library, Variant variant)
{
    Lattice lattice = new(library);
    for (int index = 0; index < variant.PocketCount; index++)
    {
        float angle = 2.0f * MathF.PI * index / variant.PocketCount;
        Vector3 bottom = new(
            45.25f * MathF.Cos(angle),
            45.25f * MathF.Sin(angle),
            -38.0f);
        Vector3 top = new(bottom.X, bottom.Y, 8.0f);
        lattice.AddBeam(bottom, variant.PocketRadiusMm, top, variant.PocketRadiusMm, true);
    }
    return lattice;
}

static Lattice BuildToroidalGallery(Library library, float diameterMm)
{
    Lattice lattice = new(library);
    const int segments = 128;
    const float majorRadiusMm = 34.0f;
    const float centerZMm = 26.0f;
    float minorRadiusMm = diameterMm / 2.0f;
    for (int index = 0; index < segments; index++)
    {
        float a0 = 2.0f * MathF.PI * index / segments;
        float a1 = 2.0f * MathF.PI * (index + 1) / segments;
        Vector3 start = new(
            majorRadiusMm * MathF.Cos(a0),
            majorRadiusMm * MathF.Sin(a0),
            centerZMm);
        Vector3 end = new(
            majorRadiusMm * MathF.Cos(a1),
            majorRadiusMm * MathF.Sin(a1),
            centerZMm);
        lattice.AddBeam(start, minorRadiusMm, end, minorRadiusMm, true);
    }
    return lattice;
}

static Lattice BuildPinToCrownRibs(Library library, float radiusMm)
{
    Lattice lattice = new(library);
    const int segments = 16;
    for (int index = 0; index < segments; index++)
    {
        float angle0 = 2.0f * MathF.PI * index / segments;
        float angle1 = 2.0f * MathF.PI * (index + 1) / segments;
        Vector3 skirt = new(
            39.5f * MathF.Cos(angle0),
            39.5f * MathF.Sin(angle0),
            8.0f);
        Vector3 crown0 = new(
            32.0f * MathF.Cos(angle0),
            32.0f * MathF.Sin(angle0),
            18.5f);
        Vector3 crown1 = new(
            32.0f * MathF.Cos(angle1),
            32.0f * MathF.Sin(angle1),
            18.5f);
        lattice.AddBeam(skirt, radiusMm, crown0, radiusMm, true);
        lattice.AddBeam(skirt, radiusMm, crown1, radiusMm, true);
    }

    Vector3 positiveBoss = new(22.0f, 0.0f, 4.0f);
    Vector3 negativeBoss = new(-22.0f, 0.0f, 4.0f);
    foreach (float angle in new[] { -0.55f, 0.55f })
    {
        Vector3 positiveCrown = new(
            30.0f * MathF.Cos(angle),
            30.0f * MathF.Sin(angle),
            18.5f);
        Vector3 negativeCrown = new(
            -30.0f * MathF.Cos(angle),
            30.0f * MathF.Sin(angle),
            18.5f);
        lattice.AddBeam(positiveBoss, radiusMm, positiveCrown, radiusMm, true);
        lattice.AddBeam(negativeBoss, radiusMm, negativeCrown, radiusMm, true);
    }
    return lattice;
}

static string Sha256(string path)
{
    using SHA256 algorithm = SHA256.Create();
    using FileStream stream = File.OpenRead(path);
    return Convert.ToHexString(algorithm.ComputeHash(stream)).ToLowerInvariant();
}

readonly record struct Variant(
    string Id,
    int PocketCount,
    float PocketRadiusMm,
    float GalleryDiameterMm,
    float RibRadiusMm);
