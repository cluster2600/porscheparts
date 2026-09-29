using System.Globalization;
using System.Numerics;
using System.Text.Json;
using PicoGK;

// M64 exhaust-wave parametric field functions: ManifoldRunner, HeatShield,
// ExhaustTip, OilReturnPipe. Signed-distance field functions only; voxel render,
// boolean and STL export use the PicoGK 26.2 API verified in
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

    void Build(string partKey, IImplicit implicit, BBox3 bounds, object parameters, string[] tag)
    {
        Voxels voxels = new(library);
        voxels.RenderImplicit(implicit, bounds);
        voxels.CalculateProperties(out float volumeCubicMm, out BBox3 renderedBounds);
        if (volumeCubicMm <= 0) throw new InvalidDataException($"{partKey}: nonpositive voxel volume");
        Mesh mesh = new(voxels);
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
        voxels.Dispose();
        mesh.Dispose();
        Console.WriteLine($"{partKey}: volume={volumeCubicMm:F0} mm3 screening mass={massGrams:F1} g, tris={records.Count}");
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
        AxialLengthTargetMm = 215.0f        // F0 synthetic axial length
    };
    ManifoldRunner runner = new(manifold);
    Build("manifold_runner_bank", runner, runner.Bounds, manifold,
        ["sourced_synthetic_core_34_56_1p2_215", "assumed_paths_and_flanges",
         "ar_8p00_supplier_declaration_not_design_dim", "dims_missing_in_bom"]);

    // ------------------------------------------------------------------
    // 2. HeatShield — shell over the FVD-declared product envelope
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
    Build("heat_shield_left", heatShield, heatShield.Bounds, shield,
        ["envelope_declared_105x160x110", "thickness_assumed",
         "interfaces_missing", "polymer_vs_metal_open_see_printability"]);

    // ------------------------------------------------------------------
    // 3. ExhaustTip — round-to-oval transition to the FVD-declared
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
    Build("exhaust_tip_oval", exhaustTip, exhaustTip.Bounds, tip,
        ["outlet_declared_120x85", "inlet_length_assumed",
         "family_mismatch_narrowbody_vs_turbo"]);

    // ------------------------------------------------------------------
    // 4. OilReturnPipe — gravity scavenge line stub, turbo down to sump.
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
    Build("oil_return_pipe", oilReturn, oilReturn.Bounds, oil,
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
    readonly float m_fBendStub;

    public SdSegment(Vector3 vecA, Vector3 vecB, float fRadA, float fRadB, float fBendStub = 0f)
    {
        m_vecA = vecA; m_vecB = vecB; m_fRadA = fRadA; m_fRadB = fRadB; m_fBendStub = fBendStub;
    }

    public float fSignedDistance(in Vector3 vec)
    {
        Vector3 ba = m_vecB - m_vecA;
        Vector3 pa = vec - m_vecA;
        float h = Math.Clamp(Vector3.Dot(pa, ba) / ba.LengthSquared(), 0f, 1f);
        Vector3 proj = pa - h * ba;
        float r = m_fRadA + h * (m_fRadB - m_fRadA);
        float d = proj.Length() - r;
        if (m_fBendStub > 0f)
            // Round the junction so unions of segments stay manifold-ish at F0.
            d = SmoothMinSphere(d, (vec - (m_vecA + h * ba)).Length() * 0f - 0f, m_fBendStub);
        return d;
    }

    static float SmoothMinSphere(float fA, float fB, float fK)
    {
        float r = fB + fK;
        float d = fA + fK;
        if (d >= 0f || r >= 0f) return Math.Min(fA, fB);
        return d * d / (4f * fK);
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
        Vector3 q = Vector3.Abs(vec - m_vecCentre) - m_vecHalf + m_fRadius;
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
        float k = Vector2.Dot(p / new Vector2(rx, ry), p / new Vector2(rx, ry)).Length();
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

        m_oOuter = new SdUnion([.. aOuter]);
        m_oInner = new SdUnion([.. aInner]);
    }

    public float fSignedDistance(in Vector3 vec)
        => Math.Max(m_oOuter.fSignedDistance(vec), -m_oInner.fSignedDistance(vec));

    public BBox3 Bounds
    {
        get
        {
            float fPad = m_oParams.HeaderStubOuterMm * 0.5f + 2f;
            float fLen = m_oParams.HeaderStubLengthMm + m_oParams.CollectorLengthMm
                       + m_oParams.TurbineInletStubLengthMm;
            float fHalfY = (m_oParams.RunnerCount - 1) * 0.5f * m_oParams.HeaderPortPitchMm;
            return new BBox3(
                new Vector3(-m_oParams.HeaderStubLengthMm - fPad, -fHalfY - fPad, -fPad),
                new Vector3(fLen + fPad, fHalfY + fPad, fPad));
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
                                 vecHalf - oParams.WallMm,
                                 Math.Max(oParams.CornerRadiusMm - oParams.WallMm, 0.1f));
        m_oShell = new SdShell(outer, inner);
    }

    public float fSignedDistance(in Vector3 vec) => m_oShell.fSignedDistance(vec);

    public BBox3 Bounds => new(
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

    public BBox3 Bounds => new(
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

    public BBox3 Bounds => new(
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
