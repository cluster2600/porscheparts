using System.Globalization;
using System.Numerics;
using System.Text.Json;
using PicoGK;

// M64 exhaust-wave parametric field functions: ManifoldRunner, DownpipeRunner,
// HeatShield, ExhaustTip, OilReturnPipe. Signed-distance field functions only;
// voxel render, boolean and STL export use the PicoGK 26.2 API verified in
// containers/picogk-m64.Dockerfile (/upstream/PicoGK).
//
// Every dimension is tagged in provenance.json. Nothing here is a measured
// envelope: the exhaust lines of twins/m64-engine-system/bom/m64-bom-v1.json
// carry dims=missing, and vendor sources declare envelopes only.

if (args.Length < 1 || args.Length > 2 ||
    !int.TryParse(args.Length == 2 ? args[1] : "0.4", NumberStyles.Integer, CultureInfo.InvariantCulture, out int voxelTenthMm) ||
    voxelTenthMm < 1 || voxelTenthMm > 10)
{
    Console.Error.WriteLine("Usage: ExhaustVoxels OUTPUT_DIR [VOXEL_TENTHS_OF_MM 1..10]");
    return 2;
}

string output = Path.GetFullPath(args[0]);
if (Directory.Exists(output) || File.Exists(output))
{
    Console.Error.WriteLine("Output directory must not exist (no overwrite).");
    return 2;
}
Directory.CreateDirectory(output);
float voxelMm = voxelTenthMm / 10f;

const float IN625_DENSITY_G_PER_MM3 = 0.00844f; // 8.44 g/cm3, screening value from the IN625 F0 manifold dossier

try
{
    using Library library = new(voxelMm);
    List<object> records = [];

    void Build(string partKey, IImplicit xImplicit, BBox3 bounds, object parameters, string[] tag)
    {
        using Voxels voxels = new(library);
        voxels.RenderImplicit(xImplicit, bounds);
        voxels.CalculateProperties(out float volumeCubicMm, out BBox3 renderedBounds);
        if (volumeCubicMm <= 0) throw new InvalidDataException($"{partKey}: nonpositive voxel volume");
        using Mesh mesh = new(voxels);
        string stlPath = Path.Combine(output, $"{partKey}.stl");
        mesh.SaveToStlFile(stlPath, Mesh.EStlUnit.MM);
        float massGrams = volumeCubicMm * IN625_DENSITY_G_PER_MM3;
        records.Add(new
        {
            part_key = partKey,
            voxel_size_mm = voxelMm,
            parameters,
            volume_cubic_mm = Math.Round(volumeCubicMm, 1),
            in625_mass_g_screening = Math.Round(massGrams, 1),
            bbox_min = new[] { renderedBounds.vecMin.X, renderedBounds.vecMin.Y, renderedBounds.vecMin.Z },
            bbox_max = new[] { renderedBounds.vecMax.X, renderedBounds.vecMax.Y, renderedBounds.vecMax.Z },
            triangles = mesh.nTriangleCount(),
            provenance_tags = tag
        });
        Console.WriteLine($"{partKey}: volume={volumeCubicMm:F0} mm3 screening mass={massGrams:F1} g, tris={mesh.nTriangleCount()}");
    }

    // ------------------------------------------------------------------
    // 1. ManifoldRunner — header stubs -> merged collector -> K16 turbine
    //    inlet stub. Runner paths and spacings are ASSUMED; the only sourced
    //    numbers are the F0 synthetic core diameters (34/56/1.2/215) of
    //    docs/993/993_EXHAUST_MANIFOLD_IN625_F0.md and the supplier-declared
    //    A/R 8.00, which is carried as metadata, not as a driving dimension.
    // ------------------------------------------------------------------
    ManifoldRunnerParams manifold = new()
    {
        RunnerCount = 3,                    // 3-into-1 layout of the F0 core (synthetic)
        PrimaryInnerDiaMm = 34.0f,          // F0 synthetic core, revisable assumption
        CollectorInnerDiaMm = 56.0f,        // F0 synthetic core, revisable assumption
        WallMm = 1.2f,                      // F0 synthetic nominal wall
        HeaderPortPitchMm = 46.0f,          // ASSUMED: header port pitch unknown (PET 107-20 gap)
        HeaderStubLengthMm = 18.0f,         // ASSUMED
        HeaderStubOuterMm = 48.0f,          // ASSUMED
        CollectorLengthMm = 120.0f,         // sized so overall path stays near the F0 215 mm
        RunnerBendRadiusMm = 60.0f,         // ASSUMED bend strategy marker
        TurbineInletStubDiaMm = 54.0f,      // ASSUMED: K16 turbine inlet face unmeasured
        TurbineInletStubLengthMm = 14.0f,   // ASSUMED
        TurbineOutletStubDiaMm = 60.0f,     // ASSUMED: K16 turbine outlet face unmeasured
        TurbineOutletStubLengthMm = 16.0f,  // ASSUMED
        AxialLengthTargetMm = 215.0f        // F0 synthetic axial length
    };
    ManifoldRunner runner = new(manifold);
    Build("manifold_runner_bank", runner, runner.oBounds, manifold,
        ["sourced_synthetic_core_34_56_1p2_215", "assumed_paths_and_flanges",
         "ar_8p00_supplier_declaration_not_design_dim", "dims_missing_in_bom"]);

    // ------------------------------------------------------------------
    // 2. DownpipeRunner — turbine outlet -> routed runner -> tip inlet.
    //    The whole route (BOM M64B-IN-004, dims=missing, identity=missing)
    //    is ASSUMED; bend radii are configurable parameters so the layout
    //    can be revised when the Fabspeed scan lead is extracted.
    //    Inlet outer diameter = turbine-outlet stub outer (60) + 2 x wall.
    // ------------------------------------------------------------------
    DownpipeParams downpipe = new()
    {
        InletOuterDiaMm = manifold.TurbineOutletStubDiaMm + 2f * manifold.WallMm,
        OutletOuterDiaMm = manifold.TurbineOutletStubDiaMm + 2f * manifold.WallMm,
        WallMm = 1.2f,                      // ASSUMED (F0 study value)
        AxialLengthMm = 420.0f,             // ASSUMED route length
        BendRadiusA_Mm = 150.0f,            // ASSUMED: first bend, configurable
        BendRadiusB_Mm = 150.0f,            // ASSUMED: second bend, configurable
        BendRadiusMid_Mm = 240.0f,          // ASSUMED: mid-sweep radius, configurable
        BendRadiusCat_Mm = 320.0f,          // ASSUMED: cat-section radius, configurable
        DropMm = 90.0f,                     // ASSUMED: descent toward underfloor
        LateralOffsetMm = 60.0f,            // ASSUMED: inboard step to tip line
        FlangeOuterMm = 74.0f,              // ASSUMED; ball-clamp geometry unmeasured
        FlangeThicknessMm = 6.0f            // ASSUMED
    };
    DownpipeRunner downpipeRunner = new(downpipe);
    Build("downpipe_turbine_outlet_to_tip", downpipeRunner, downpipeRunner.oBounds, downpipe,
        ["all_dims_assumed", "bend_radii_configurable", "route_unknown_pending_laser_scan",
         "cat_insert_omitted_identity_missing", "dims_missing_in_bom"]);

    // ------------------------------------------------------------------
    // 3. HeatShield — shell over the FVD-declared product envelope
    //    105 x 160 x 110 mm (H x L x W), ref 993 123 113 51. Only the
    //    envelope is vendor-declared; thickness, fixings and hot face are
    //    ASSUMED.
    // ------------------------------------------------------------------
    HeatShieldParams shield = new()
    {
        EnvelopeHeightMm = 105.0f,          // SRC-FVD-993-TURBO-HEAT-SHIELD (declared)
        EnvelopeLengthMm = 160.0f,          // declared
        EnvelopeWidthMm = 110.0f,           // declared
        WallMm = 1.5f,                      // ASSUMED
        MountTabDiameterMm = 0.0f,          // interfaces missing -> no invented tabs
        CornerRadiusMm = 12.0f              // ASSUMED
    };
    HeatShield heatShield = new(shield);
    Build("heat_shield_left", heatShield, heatShield.oBounds, shield,
        ["envelope_declared_105x160x110", "thickness_assumed",
         "interfaces_missing", "polymer_vs_metal_open_see_printability"]);

    // ------------------------------------------------------------------
    // 4. ExhaustTip — round-to-oval transition to the FVD-declared
    //    120 (wide) x 85 (high) outlet. Inlet, length, wall and ties follow
    //    the repo oval-tip IN625 F0 study (docs/993/993_OVAL_EXHAUST_TIP_IN625_F0.md):
    //    0.8 mm shell, eight radial ties, open air gap.
    //    NOTE: FVD11199300 is declared for narrow-body 993 C2/C4/RS, not the
    //    Turbo — carried as an adjacent-family envelope, see provenance.
    // ------------------------------------------------------------------
    ExhaustTipParams tip = new()
    {
        OutletWidthMm = 120.0f,             // SRC-FVD-993-EXHAUST-TIPS (declared)
        OutletHeightMm = 85.0f,             // declared
        InletDiameterMm = 60.0f,            // ASSUMED, revisable per the F0 study
        LengthMm = 180.0f,                  // ASSUMED
        WallMm = 0.8f,                      // study value
        TieCount = 8,                       // study value
        TieDiameterMm = 5.0f                // ASSUMED
    };
    ExhaustTip exhaustTip = new(tip);
    Build("exhaust_tip_oval", exhaustTip, exhaustTip.oBounds, tip,
        ["outlet_declared_120x85", "inlet_length_assumed",
         "family_mismatch_narrowbody_vs_turbo"]);

    // ------------------------------------------------------------------
    // 5. OilReturnPipe — gravity scavenge line stub, turbo down to sump.
    //    No source publishes any dimension (Patrick Motorsports describes
    //    fit-as-installed practice); every value below is ASSUMED.
    // ------------------------------------------------------------------
    OilReturnPipeParams oil = new()
    {
        InnerDiaMm = 24.0f,                 // ASSUMED
        WallMm = 1.2f,                      // ASSUMED
        DropMm = 140.0f,                    // ASSUMED routing
        HorizontalRunMm = 160.0f,           // ASSUMED
        BendRadiusMm = 34.0f,               // ASSUMED, >= 1.5x centreline radius
        EndFlangeOuterMm = 38.0f,           // ASSUMED; real clamps unknown
        EndFlangeThicknessMm = 6.0f         // ASSUMED
    };
    OilReturnPipe oilReturn = new(oil);
    Build("oil_return_pipe", oilReturn, oilReturn.oBounds, oil,
        ["all_dims_assumed", "fit_as_installed_practice", "pet_107_family_identity_gap"]);

    string summaryPath = Path.Combine(output, "geometry-summary.json");
    File.WriteAllText(summaryPath, JsonSerializer.Serialize(new
    {
        generated_by = "parts/m64-exhaust-0001/source/picogk (PicoGK 26.2 headless)",
        voxel_size_mm = voxelMm,
        in625_density_g_per_cm3 = 8.44,
        note = "Screening masses assume full-density IN625; as-built LPBF density, supports and skin effects excluded. Authored F0 geometry, not a measured part.",
        parts = records
    }, new JsonSerializerOptions { WriteIndented = true }));
    Console.WriteLine($"WROTE {summaryPath}");
    return 0;
}
catch (Exception exception)
{
    Console.Error.WriteLine($"EXHAUST_GEOMETRY_FAIL {exception.GetType().Name}: {exception.Message}");
    return 1;
}

// ======================================================================
// Field functions. All SDFs return signed millimetres, negative inside.
// ======================================================================

/// <summary>Capped (optionally tapered) segment SDF, per-segment exact for cylinders.</summary>
sealed class SdSegment : IImplicit
{
    readonly Vector3 m_vecA;
    readonly Vector3 m_vecB;
    readonly float m_fRadA;
    readonly float m_fRadB;

    public SdSegment(Vector3 vecA, Vector3 vecB, float fRadA, float fRadB)
    {
        m_vecA = vecA; m_vecB = vecB; m_fRadA = fRadA; m_fRadB = fRadB;
    }

    public float fSignedDistance(in Vector3 vec)
    {
        Vector3 ba = m_vecB - m_vecA;
        Vector3 pa = vec - m_vecA;
        float h = Math.Clamp(Vector3.Dot(pa, ba) / ba.LengthSquared(), 0f, 1f);
        Vector3 proj = pa - h * ba;
        float r = m_fRadA + h * (m_fRadB - m_fRadA);
        return proj.Length() - r;
    }
}

/// <summary>Rounded box SDF.</summary>
sealed class SdRoundedBox : IImplicit
{
    readonly Vector3 m_vecHalf;
    readonly float m_fRadius;
    readonly Vector3 m_vecCentre;

    public SdRoundedBox(Vector3 vecCentre, Vector3 vecHalf, float fRadius)
    {
        m_vecCentre = vecCentre; m_vecHalf = vecHalf; m_fRadius = fRadius;
    }

    public float fSignedDistance(in Vector3 vec)
    {
        Vector3 q = Vector3.Abs(vec - m_vecCentre) - m_vecHalf + new Vector3(m_fRadius);
        return Math.Min(Math.Max(Math.Max(q.X, q.Y), q.Z), 0f) +
               Vector3.Max(q, Vector3.Zero).Length() - m_fRadius;
    }
}

/// <summary>
/// Axis-aligned superellipse duct lofting from a round inlet at Z=0 to a
/// rectangular (rounded) outlet at Z=LengthMm. The per-section SDF uses the
/// ellipse-style approximation (length(p/r)-1)*min(rx,ry); exact on the axes,
/// a bounded approximation off them, which is acceptable for an F0 screen.
/// </summary>
sealed class SdOvalLoft : IImplicit
{
    readonly float m_fInletR;
    readonly float m_fOutHalfW;
    readonly float m_fOutHalfH;
    readonly float m_fLength;
    readonly float m_fOutCorner;
    readonly float m_fWallInset; // >0 shrinks section (inner duct), 0 = outer skin

    public SdOvalLoft(float fInletR, float fOutHalfW, float fOutHalfH,
                      float fLength, float fOutCorner, float fWallInset = 0f)
    {
        m_fInletR = fInletR; m_fOutHalfW = fOutHalfW; m_fOutHalfH = fOutHalfH;
        m_fLength = fLength; m_fOutCorner = fOutCorner; m_fWallInset = fWallInset;
    }

    public float fSignedDistance(in Vector3 vec)
    {
        float t = Math.Clamp(vec.Z / m_fLength, 0f, 1f);
        float smooth = t * t * (3f - 2f * t); // smoothstep loft
        float rx = m_fInletR + smooth * (m_fOutHalfW - m_fInletR) - m_fWallInset;
        float ry = m_fInletR + smooth * (m_fOutHalfH - m_fInletR) - m_fWallInset;
        if (rx <= 0f || ry <= 0f) return 1000f;
        Vector2 p = new(vec.X, vec.Y);
        float k = (p / new Vector2(rx, ry)).Length();
        float sdSection = (k - 1f) * Math.Min(rx, ry);
        // Blend the section SDF with the slab along Z (capped loft).
        float sdZ = Math.Abs(vec.Z - m_fLength * 0.5f) - m_fLength * 0.5f;
        return Math.Max(sdSection, sdZ);
    }
}

sealed class SdUnion : IImplicit
{
    readonly IImplicit[] m_aParts;
    public SdUnion(params IImplicit[] aParts) { m_aParts = aParts; }
    public float fSignedDistance(in Vector3 vec)
    {
        float f = float.MaxValue;
        foreach (IImplicit p in m_aParts) f = Math.Min(f, p.fSignedDistance(vec));
        return f;
    }
}

sealed class SdShell : IImplicit
{
    readonly IImplicit m_oOuter;
    readonly IImplicit m_oInner;
    public SdShell(IImplicit oOuter, IImplicit oInner) { m_oOuter = oOuter; m_oInner = oInner; }
    public float fSignedDistance(in Vector3 vec)
        => Math.Max(m_oOuter.fSignedDistance(vec), -m_oInner.fSignedDistance(vec));
}

// ======================================================================
// Parts
// ======================================================================

record ManifoldRunnerParams
{
    public required int RunnerCount { get; init; }
    public required float PrimaryInnerDiaMm { get; init; }
    public required float CollectorInnerDiaMm { get; init; }
    public required float WallMm { get; init; }
    public required float HeaderPortPitchMm { get; init; }
    public required float HeaderStubLengthMm { get; init; }
    public required float HeaderStubOuterMm { get; init; }
    public required float CollectorLengthMm { get; init; }
    public required float RunnerBendRadiusMm { get; init; }
    public required float TurbineInletStubDiaMm { get; init; }
    public required float TurbineInletStubLengthMm { get; init; }
    public required float TurbineOutletStubDiaMm { get; init; }
    public required float TurbineOutletStubLengthMm { get; init; }
    public required float AxialLengthTargetMm { get; init; }
}

/// <summary>
/// Three header stubs on a common plane bend into a shared collector and end
/// in a K16 turbine-inlet stub. Solid outer minus duct inner => open both ends
/// (powder-evacuation-friendly, mirrors the F0 rule of three inlets/one outlet).
/// </summary>
sealed class ManifoldRunner : IBoundedImplicit
{
    readonly ManifoldRunnerParams m_oParams;
    readonly SdUnion m_oOuter;
    readonly SdUnion m_oInner;

    public ManifoldRunner(ManifoldRunnerParams oParams)
    {
        m_oParams = oParams;
        float fPipeR = oParams.PrimaryInnerDiaMm * 0.5f;
        float fWall = oParams.WallMm;
        float fCollR = oParams.CollectorInnerDiaMm * 0.5f;

        List<IImplicit> aOuter = [];
        List<IImplicit> aInner = [];

        // Collector centreline along +X at Z=0.
        Vector3 vecCollStart = new(oParams.HeaderStubLengthMm, 0f, 0f);
        Vector3 vecCollEnd = vecCollStart + new Vector3(oParams.CollectorLengthMm, 0f, 0f);
        aOuter.Add(new SdSegment(vecCollStart, vecCollEnd, fCollR + fWall, fCollR + fWall));
        aInner.Add(new SdSegment(vecCollStart, vecCollEnd, fCollR, fCollR));

        // Runners: header stub along -X, two-segment bend into the collector.
        for (int n = 0; n < oParams.RunnerCount; n++)
        {
            float fY = (n - (oParams.RunnerCount - 1) * 0.5f) * oParams.HeaderPortPitchMm;
            Vector3 vecPort = new(0f, fY, 0f);
            Vector3 vecStubEnd = vecPort - new Vector3(oParams.HeaderStubLengthMm, 0f, 0f);
            Vector3 vecMerge = Vector3.Lerp(vecCollStart, vecCollEnd,
                (n + 1f) / (oParams.RunnerCount + 1f));

            aOuter.Add(new SdSegment(vecStubEnd, vecPort, fPipeR + fWall, fPipeR + fWall));
            aInner.Add(new SdSegment(vecStubEnd, vecPort, fPipeR, fPipeR));
            // Bend: drop toward the collector plane then merge tangentially.
            Vector3 vecMid = Vector3.Lerp(vecPort, vecMerge, 0.5f) - new Vector3(0f, 0f, 0f);
            aOuter.Add(new SdSegment(vecPort, vecMid, fPipeR + fWall, fPipeR + fWall));
            aOuter.Add(new SdSegment(vecMid, vecMerge, fPipeR + fWall, fPipeR + fWall));
            aInner.Add(new SdSegment(vecPort, vecMid, fPipeR, fPipeR));
            aInner.Add(new SdSegment(vecMid, vecMerge, fPipeR, fPipeR));
        }

        // K16 turbine-inlet stub (A/R 8.00 stays a supplier declaration; the
        // stub diameter is an assumption until the housing is measured).
        Vector3 vecStub = vecCollEnd + new Vector3(oParams.TurbineInletStubLengthMm, 0f, 0f);
        float fStubR = oParams.TurbineInletStubDiaMm * 0.5f;
        aOuter.Add(new SdSegment(vecCollEnd, vecStub, fStubR + fWall, fStubR + fWall));
        aInner.Add(new SdSegment(vecCollEnd, vecStub, fStubR * 0.9f, fStubR * 0.9f));

        // K16 turbine-outlet stub, coaxial with the collector centreline; the
        // DownpipeRunner starts where this stub ends. Diameter and length are
        // assumptions (the FVD source declares only the 210x280x190 turbo
        // envelope), so they are configured, not measured.
        float fOutStubR = oParams.TurbineOutletStubDiaMm * 0.5f;
        Vector3 vecOutStubEnd = vecStub + new Vector3(oParams.TurbineOutletStubLengthMm, 0f, 0f);
        aOuter.Add(new SdSegment(vecStub, vecOutStubEnd, fOutStubR + fWall, fOutStubR + fWall));
        aInner.Add(new SdSegment(vecStub, vecOutStubEnd, fOutStubR, fOutStubR));

        m_oOuter = new SdUnion([.. aOuter]);
        m_oInner = new SdUnion([.. aInner]);
    }

    public float fSignedDistance(in Vector3 vec)
        => Math.Max(m_oOuter.fSignedDistance(vec), -m_oInner.fSignedDistance(vec));

    public BBox3 oBounds
    {
        get
        {
            float fPad = m_oParams.HeaderStubOuterMm * 0.5f + 2f;
            float fLen = m_oParams.HeaderStubLengthMm + m_oParams.CollectorLengthMm
                       + m_oParams.TurbineInletStubLengthMm + m_oParams.TurbineOutletStubLengthMm;
            float fHalfY = (m_oParams.RunnerCount - 1) * 0.5f * m_oParams.HeaderPortPitchMm;
            return new BBox3(
                new Vector3(-m_oParams.HeaderStubLengthMm - fPad, -fHalfY - fPad, -fPad),
                new Vector3(fLen + fPad, fHalfY + fPad, fPad));
        }
    }
}

record DownpipeParams
{
    public required float InletOuterDiaMm { get; init; }
    public required float OutletOuterDiaMm { get; init; }
    public required float WallMm { get; init; }
    public required float AxialLengthMm { get; init; }
    public required float BendRadiusA_Mm { get; init; }
    public required float BendRadiusB_Mm { get; init; }
    public required float BendRadiusMid_Mm { get; init; }
    public required float BendRadiusCat_Mm { get; init; }
    public required float DropMm { get; init; }
    public required float LateralOffsetMm { get; init; }
    public required float FlangeOuterMm { get; init; }
    public required float FlangeThicknessMm { get; init; }
}

/// <summary>
/// Turbine-outlet-to-tip runner. The centreline is a three-arc routed
/// approximation (entry bend radius A, descent bend radius B, mid sweep
/// radius Mid, exit-cat bend radius Cat) built as a tangent polyline chain of
/// SdSegments plus junction spheres, so the pipe stays manifold at F0 while
/// every bend radius stays a configurable parameter. Solid outer minus duct
/// inner => open at both ends. The whole route is an ASSUMPTION; see
/// provenance.json.
/// </summary>
sealed class DownpipeRunner : IBoundedImplicit
{
    readonly DownpipeParams m_oParams;
    readonly SdShell m_oShell;
    readonly SdUnion m_oFlanges;
    readonly float m_fMaxRadius;

    public DownpipeRunner(DownpipeParams oParams)
    {
        m_oParams = oParams;
        if (oParams.BendRadiusA_Mm < oParams.InletOuterDiaMm ||
            oParams.BendRadiusB_Mm < oParams.InletOuterDiaMm ||
            oParams.BendRadiusMid_Mm < oParams.InletOuterDiaMm * 0.5f ||
            oParams.BendRadiusCat_Mm < oParams.OutletOuterDiaMm)
            throw new ArgumentException($"{nameof(DownpipeRunner)}: bend radius below pipe diameter");

        float fRIn = oParams.InletOuterDiaMm * 0.5f;
        float fROut = oParams.OutletOuterDiaMm * 0.5f;
        float fWall = oParams.WallMm;
        m_fMaxRadius = Math.Max(fRIn, fROut) + fWall;

        // Centreline chain: +X from the turbine outlet, descending, then
        // inboard (+Y) toward the tip line, exit facing +X at the tip plane.
        // Each arc is a pair of chords whose length scales with its bend
        // radius, so the bend radii are first-class geometry parameters.
        Vector3 vecStart = Vector3.Zero;
        Vector3 vecB = vecStart + new Vector3(oParams.BendRadiusA_Mm * 0.75f, 0f, -fWall * 2f);
        Vector3 vecMid = vecB + new Vector3(oParams.BendRadiusMid_Mm * 0.5f,
                                            0f,
                                            -oParams.DropMm * 0.5f);
        Vector3 vecDrop = vecMid + new Vector3(oParams.BendRadiusB_Mm * 0.25f,
                                               oParams.LateralOffsetMm * 0.5f,
                                               -oParams.DropMm * 0.5f);
        Vector3 vecCat = vecDrop + new Vector3(oParams.BendRadiusCat_Mm * 0.25f,
                                               oParams.LateralOffsetMm * 0.5f, 0f);
        Vector3 vecExit = vecCat + new Vector3(oParams.AxialLengthMm * 0.5f,
                                               0f, oParams.DropMm * 0.25f);
        Vector3 vecEnd = vecExit + new Vector3(oParams.AxialLengthMm * 0.5f, 0f, 0f);

        Vector3[] avec = [vecStart, vecB, vecMid, vecDrop, vecCat, vecExit, vecEnd];
        List<IImplicit> aOuter = [];
        List<IImplicit> aInner = [];
        for (int n = 0; n < avec.Length - 1; n++)
        {
            float fT = (float)n / (avec.Length - 2);
            float rA = fRIn + fT * (fROut - fRIn);
            float rB = fRIn + (n + 1f) / (avec.Length - 2) * (fROut - fRIn);
            aOuter.Add(new SdSegment(avec[n], avec[n + 1], rA + fWall, rB + fWall));
            aInner.Add(new SdSegment(avec[n], avec[n + 1], rA, rB));
            if (n > 0)
            {
                // Junction spheres keep the union (and the subtracted duct)
                // round at the chord joints; an exact swept-pipe SDF is
                // deferred until the route is measured.
                aOuter.Add(new SphereImplicit(avec[n], rA + fWall));
                aInner.Add(new SphereImplicit(avec[n], rA));
            }
        }
        m_oShell = new SdShell(new SdUnion([.. aOuter]), new SdUnion([.. aInner]));
        m_oFlanges = new SdUnion(
            new SdSegment(vecStart, vecStart + new Vector3(oParams.FlangeThicknessMm, 0f, 0f),
                          oParams.FlangeOuterMm * 0.5f, oParams.FlangeOuterMm * 0.5f),
            new SdSegment(vecEnd - new Vector3(oParams.FlangeThicknessMm, 0f, 0f), vecEnd,
                          oParams.FlangeOuterMm * 0.5f, oParams.FlangeOuterMm * 0.5f));
    }

    public float fSignedDistance(in Vector3 vec)
        => Math.Min(m_oShell.fSignedDistance(vec), m_oFlanges.fSignedDistance(vec));

    public BBox3 oBounds
    {
        get
        {
            float fPad = Math.Max(m_fMaxRadius, m_oParams.FlangeOuterMm * 0.5f) + 2f;
            float fXMin = -fPad;
            float fXMax = m_oParams.AxialLengthMm
                        + m_oParams.BendRadiusA_Mm * 0.75f
                        + m_oParams.BendRadiusMid_Mm * 0.5f
                        + m_oParams.BendRadiusB_Mm * 0.25f
                        + m_oParams.BendRadiusCat_Mm * 0.25f + fPad;
            float fYMin = -fPad;
            float fYMax = m_oParams.LateralOffsetMm + fPad;
            float fZMin = -m_oParams.DropMm - fPad;
            float fZMax = fPad;
            return new BBox3(new Vector3(fXMin, fYMin, fZMin), new Vector3(fXMax, fYMax, fZMax));
        }
    }
}

record HeatShieldParams
{
    public required float EnvelopeHeightMm { get; init; }
    public required float EnvelopeLengthMm { get; init; }
    public required float EnvelopeWidthMm { get; init; }
    public required float WallMm { get; init; }
    public required float MountTabDiameterMm { get; init; }
    public required float CornerRadiusMm { get; init; }
}

/// <summary>
/// Hollow rounded-box shell matching the vendor-declared envelope of the left
/// turbo heat shield 993 123 113 51 (105 x 160 x 110 mm declared). Open on the
/// hot face (bottom) so it is a shield, not a sealed box; no fixings invented.
/// </summary>
sealed class HeatShield : IBoundedImplicit
{
    readonly HeatShieldParams m_oParams;
    readonly SdShell m_oShell;

    public HeatShield(HeatShieldParams oParams)
    {
        m_oParams = oParams;
        Vector3 vecHalf = new(oParams.EnvelopeWidthMm * 0.5f,
                              oParams.EnvelopeLengthMm * 0.5f,
                              oParams.EnvelopeHeightMm * 0.5f);
        Vector3 vecCentre = Vector3.Zero;
        SdRoundedBox outer = new(vecCentre, vecHalf, oParams.CornerRadiusMm);
        SdRoundedBox inner = new(vecCentre + new Vector3(0f, 0f, -oParams.WallMm),
                                 vecHalf - new Vector3(oParams.WallMm),
                                 Math.Max(oParams.CornerRadiusMm - oParams.WallMm, 0.1f));
        m_oShell = new SdShell(outer, inner);
    }

    public float fSignedDistance(in Vector3 vec) => m_oShell.fSignedDistance(vec);

    public BBox3 oBounds => new(
        new Vector3(-m_oParams.EnvelopeWidthMm * 0.5f - 1f,
                    -m_oParams.EnvelopeLengthMm * 0.5f - 1f,
                    -m_oParams.EnvelopeHeightMm * 0.5f - 1f),
        new Vector3(m_oParams.EnvelopeWidthMm * 0.5f + 1f,
                    m_oParams.EnvelopeLengthMm * 0.5f + 1f,
                    m_oParams.EnvelopeHeightMm * 0.5f + 1f));
}

record ExhaustTipParams
{
    public required float OutletWidthMm { get; init; }
    public required float OutletHeightMm { get; init; }
    public required float InletDiameterMm { get; init; }
    public required float LengthMm { get; init; }
    public required float WallMm { get; init; }
    public required int TieCount { get; init; }
    public required float TieDiameterMm { get; init; }
}

/// <summary>
/// Round-to-oval tip: outer skin minus inner duct (air gap open at both ends,
/// no captive powder — same rule as the repo oval-tip IN625 F0) joined with
/// radial ties. Outlet is the only declared dimension.
/// </summary>
sealed class ExhaustTip : IBoundedImplicit
{
    readonly ExhaustTipParams m_oParams;
    readonly SdUnion m_oAll;

    public ExhaustTip(ExhaustTipParams oParams)
    {
        m_oParams = oParams;
        SdOvalLoft outer = new(oParams.InletDiameterMm * 0.5f,
                               oParams.OutletWidthMm * 0.5f,
                               oParams.OutletHeightMm * 0.5f,
                               oParams.LengthMm, 8f);
        SdOvalLoft inner = new(oParams.InletDiameterMm * 0.5f - oParams.WallMm,
                               oParams.OutletWidthMm * 0.5f - oParams.WallMm,
                               oParams.OutletHeightMm * 0.5f - oParams.WallMm,
                               oParams.LengthMm, 8f, oParams.WallMm);
        SdShell shell = new(outer, inner);

        // Ties at the inlet plane join duct to skin; kept as thin Z beams.
        List<IImplicit> aParts = [shell];
        float fMidR = oParams.InletDiameterMm * 0.25f;
        for (int n = 0; n < oParams.TieCount; n++)
        {
            double fAng = 2.0 * Math.PI * n / oParams.TieCount;
            Vector3 dir = new((float)Math.Cos(fAng), (float)Math.Sin(fAng), 0f);
            Vector3 a = dir * fMidR;
            Vector3 b = dir * (oParams.InletDiameterMm * 0.5f - oParams.WallMm * 0.5f);
            aParts.Add(new SdSegment(a, b, oParams.TieDiameterMm * 0.5f,
                                     oParams.TieDiameterMm * 0.5f));
        }
        m_oAll = new SdUnion([.. aParts]);
    }

    public float fSignedDistance(in Vector3 vec) => m_oAll.fSignedDistance(vec);

    public BBox3 oBounds => new(
        new Vector3(-m_oParams.OutletWidthMm * 0.5f - 1f,
                    -m_oParams.OutletHeightMm * 0.5f - 1f, -1f),
        new Vector3(m_oParams.OutletWidthMm * 0.5f + 1f,
                    m_oParams.OutletHeightMm * 0.5f + 1f,
                    m_oParams.LengthMm + 1f));
}

record OilReturnPipeParams
{
    public required float InnerDiaMm { get; init; }
    public required float WallMm { get; init; }
    public required float DropMm { get; init; }
    public required float HorizontalRunMm { get; init; }
    public required float BendRadiusMm { get; init; }
    public required float EndFlangeOuterMm { get; init; }
    public required float EndFlangeThicknessMm { get; init; }
}

/// <summary>
/// Turbo oil scavenge stub: top inlet flange, drop, horizontal run, bottom
/// outlet flange (sump side first, per the fit-as-installed practice the
/// Patrick Motorsports page describes). Every value assumed; see provenance.
/// </summary>
sealed class OilReturnPipe : IBoundedImplicit
{
    readonly OilReturnPipeParams m_oParams;
    readonly SdShell m_oShell;
    readonly SdUnion m_oFlanges;

    public OilReturnPipe(OilReturnPipeParams oParams)
    {
        m_oParams = oParams;
        float fOuter = oParams.InnerDiaMm * 0.5f + oParams.WallMm;
        float fInner = oParams.InnerDiaMm * 0.5f;

        Vector3 vecTop = new(0f, 0f, 0f);
        Vector3 vecElbowTop = new(0f, 0f, -oParams.DropMm * 0.4f);
        Vector3 vecElbowBottom = new(oParams.BendRadiusMm, 0f, -oParams.DropMm);
        Vector3 vecBottom = new(oParams.HorizontalRunMm, 0f, -oParams.DropMm);

        IImplicit outer, inner;
        if (oParams.BendRadiusMm > 0.1f)
        {
            // Toroidal sweep proxy: approximate the elbow with two chamfered
            // segments plus a sphere at the elbow; adequate at F0.
            outer = new SdUnion(
                new SdSegment(vecTop, vecElbowTop, fOuter, fOuter),
                new SdSegment(vecElbowTop, vecElbowBottom, fOuter, fOuter),
                new SdSegment(vecElbowBottom, vecBottom, fOuter, fOuter),
                new SphereImplicit(vecElbowBottom, fOuter));
            inner = new SdUnion(
                new SdSegment(vecTop, vecElbowTop, fInner, fInner),
                new SdSegment(vecElbowTop, vecElbowBottom, fInner, fInner),
                new SdSegment(vecElbowBottom, vecBottom, fInner, fInner),
                new SphereImplicit(vecElbowBottom, fInner));
        }
        else
        {
            outer = new SdUnion(
                new SdSegment(vecTop, vecBottom, fOuter, fOuter));
            inner = new SdUnion(
                new SdSegment(vecTop, vecBottom, fInner, fInner));
        }
        m_oShell = new SdShell(outer, inner);
        m_oFlanges = new SdUnion(
            new SdSegment(vecTop, vecTop + new Vector3(0f, 0f, oParams.EndFlangeThicknessMm),
                          oParams.EndFlangeOuterMm * 0.5f, oParams.EndFlangeOuterMm * 0.5f),
            new SdSegment(vecBottom - new Vector3(0f, 0f, 0f),
                          vecBottom + new Vector3(oParams.EndFlangeThicknessMm, 0f, 0f),
                          oParams.EndFlangeOuterMm * 0.5f, oParams.EndFlangeOuterMm * 0.5f));
    }

    public float fSignedDistance(in Vector3 vec)
        => Math.Min(m_oShell.fSignedDistance(vec), m_oFlanges.fSignedDistance(vec));

    public BBox3 oBounds => new(
        new Vector3(-m_oParams.EndFlangeOuterMm, -m_oParams.EndFlangeOuterMm,
                    -m_oParams.DropMm - m_oParams.EndFlangeOuterMm),
        new Vector3(m_oParams.HorizontalRunMm + m_oParams.EndFlangeOuterMm,
                    m_oParams.EndFlangeOuterMm,
                    m_oParams.EndFlangeThicknessMm + m_oParams.EndFlangeOuterMm * 0.5f));
}

sealed class SphereImplicit : IImplicit
{
    readonly Vector3 m_vecCentre;
    readonly float m_fRadius;
    public SphereImplicit(Vector3 vecCentre, float fRadius)
    { m_vecCentre = vecCentre; m_fRadius = fRadius; }
    public float fSignedDistance(in Vector3 vec) => (vec - m_vecCentre).Length() - m_fRadius;
}
