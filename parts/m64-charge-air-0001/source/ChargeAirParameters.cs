using System.Numerics;

namespace M64DigitalTwin.ChargeAir;

// Every physical input of the charge-air path geometry study, tagged with its
// evidence class. Charge-air line dimensions are MISSING in the wave-1 master
// BOM: vendor product envelopes (FVD, TA Technix, AKS DASIS) are packaging
// bounds of aftermarket parts, not OEM interface dimensions, so nearly every
// size below is an ASSUMPTION. Boost pressure is a public FACT but does not
// size any geometry in this file.
//
// Evidence classes:
//   FACT_public        — published, attributable, non-dimensional here.
//   SOURCED_ENVELOPE   — third-party product envelope, reference-only.
//   ASSUMPTION         — engineering placeholder, order of magnitude only.
//   DERIVED            — computed from other entries; see comment.
public sealed class ChargeAirParameters
{
    // ---- Voxelisation (configurable inputs) --------------------------------
    // ASSUMPTION: voxel size chosen for envelope-level studies, same scale as
    // twins/m64-engine-system (5 mm) but finer for tube features; 1.0 mm is a
    // study setting, not a manufacturing resolution.
    public float fVoxelSizeMm = 1.0f;

    // ASSUMPTION: nominal wall of hard charge-air tubing and plenum shell.
    public float fWallThicknessMm = 2.0f;

    // ASSUMPTION: radial clearance between mating hose/coupling parts
    // (sealing design undefined; not a tolerance fit).
    public float fRadialClearanceMm = 1.5f;

    // ASSUMPTION: minimum bend radius of routed hoses, order of magnitude for
    // corrugated boost hoses; no vendor publishes a bend-radius law.
    public float fHoseMinBendRadiusMm = 120.0f;

    // ---- Interfaces ---------------------------------------------------------
    // SOURCED_ENVELOPE: TA Technix aftermarket intercooler declares 66 mm
    // outer / 68 mm inner connector stubs (SRC-TA-TECHNIX-993-INTERCOOLER-
    // DIMENSIONS). Not OEM. Used here only to set a nominal duct scale.
    public float fNominalDuctOuterDiaMm = 66.0f;   // DERIVED basis below

    // ASSUMPTION (DERIVED): nominal flow bore inside hard tubes.
    // fNominalDuctOuterDiaMm - 2*fWallThicknessMm = 62.0 mm.
    public float fNominalDuctBoreDiaMm => fNominalDuctOuterDiaMm - 2.0f * fWallThicknessMm;

    // ASSUMPTION: coupling (sleeve) that joins a hard tube to a hose: plain
    // cylindrical sleeve, length and over-diameter have no source.
    public float fCouplingLengthMm = 60.0f;
    public float fCouplingOverDiaMm = 12.0f;       // DERIVED: +6 mm radially vs duct
    public float fCouplingOuterDiaMm => fNominalDuctOuterDiaMm + fCouplingOverDiaMm;

    // ---- Compressor-outlet-to-throttle tube (per bank) ----------------------
    // ASSUMPTION: tube run geometry. Waypoints are a routing hypothesis inside
    // the engine-bay envelope of twins/m64-engine-system; no OEM charge-air
    // line drawing exists in the repository. Bank +Y shown; -Y mirrored.
    // Turbo compressor outlet assumed near the turbine-side layout sphere
    // (fTurboEnvelopeR = 130 mm, ASSUMPTION in the layout scaffold).
    public Vector3[] aTubeWaypointsPosBank =
    {
        new(-330.0f, 190.0f, 60.0f),    // compressor outlet (ASSUMPTION)
        new(-260.0f, 210.0f, 140.0f),   // ASSUMPTION routing point
        new(-140.0f, 220.0f, 170.0f),   // ASSUMPTION routing point
        new( -40.0f, 215.0f, 160.0f),   // ASSUMPTION pre-plenum tangent
    };

    // ASSUMPTION: intercooler core position; the OEM intercooler sits ahead of
    // the engine (PET locates it, publishes no coordinates). Values keep the
    // duct inside a front packaging zone consistent with the layout scaffold.
    public Vector3 vecIntercoolerCentre = new(-560.0f, 0.0f, 120.0f);

    // SOURCED_ENVELOPE: AKS DASIS OE-matched core 260 x 270 x 60 mm and Albert
    // Motorsport / TA Technix 260 x 260 x 100 mm cores (SRC-AKS-DASIS-...,
    // SRC-ALBERT-MOTORSPORT-..., SRC-TA-TECHNIX-...). Envelope only; used for
    // the plenum-to-cooler stub length, not for core geometry.
    public float fIntercoolerCoreLenMm = 260.0f;
    public float fIntercoolerCoreWidthMm = 270.0f;
    public float fIntercoolerCoreDepthMm = 100.0f;

    // ---- Per-bank plenum form ----------------------------------------------
    // ASSUMPTION: plenum as a rounded box feeding three runners per bank
    // (the three-runner intake is itself a concept: 46 x 42 x 100 mm kit
    // designation, no interface geometry published).
    public float fPlenumLengthMm = 380.0f;
    public float fPlenumWidthMm = 90.0f;
    public float fPlenumHeightMm = 110.0f;
    public float fPlenumCentreYPosBank = 215.0f;    // ASSUMPTION bank station
    public float fPlenumCornerRadiusMm = 25.0f;     // ASSUMPTION
    // ASSUMPTION (DERIVED): plenum bore = outer minus wall on all sides.
    public float fPlenumInnerLenMm => fPlenumLengthMm - 2.0f * fWallThicknessMm;
    public float fPlenumInnerWidthMm => fPlenumWidthMm - 2.0f * fWallThicknessMm;
    public float fPlenumInnerHeightMm => fPlenumHeightMm - 2.0f * fWallThicknessMm;

    // ASSUMPTION: throttle-body interface as a circular opening per bank,
    // one runner spaced at stroke + clearance like the layout scaffold.
    public float fThrottleBoreDiaMm = 60.0f;
    public float[] aRunnerOffsetsY = { -86.4f, 0.0f, 86.4f }; // DERIVED: +- (stroke 76.4 + 10 mm gap, layout-scaffold ASSUMPTION)

    // ---- Interconnect hose routing (centerlines) ------------------------------
    // SOURCED_ENVELOPE anchor: FVD replacement hose declares 430 mm length,
    // 70 x 115 mm (left, 99311063356) and 70 x 90 mm (right, 99311063256)
    // product envelopes; the reinforced kit declares 410 mm connection length,
    // 43/57 mm declared diameters (SRC-FVD-...-HOSE-LEFT / -RIGHT / -KIT).
    // These are product bounds of aftermarket parts; OEM routing is unknown.
    // ASSUMPTION: hose centerline from intercooler outlet to plenum inlet,
    // polyline waypoints per bank; arc length is checked against the 410-430
    // mm vendor envelope band below, not set by it.
    public Vector3[] aHoseWaypointsPosBank =
    {
        new(-430.0f, 150.0f, 130.0f),   // cooler outlet (ASSUMPTION)
        new(-360.0f, 190.0f, 150.0f),   // ASSUMPTION
        new(-260.0f, 210.0f, 165.0f),   // ASSUMPTION merge with tube start
    };
    // ASSUMPTION: hose swept radius, between the FVD kit declared 43/57 mm
    // diameters: (57 mm envelope upper / 2) ~ 28 mm used as outer bound.
    public float fHoseOuterRadiusMm = 28.5f;        // DERIVED: 57/2, envelope bound
    public float fHoseWallMm = 3.0f;                // ASSUMPTION
    public float fHoseFlowRadiusMm => fHoseOuterRadiusMm - fHoseWallMm;

    // Vendor envelope band for centerline length sanity reporting only
    // (SOURCED_ENVELOPE: 410-430 mm, FVD kit and left/right hose fiches).
    public float fHoseEnvelopeMinLenMm = 410.0f;
    public float fHoseEnvelopeMaxLenMm = 430.0f;

    // ---- Non-dimensional facts -----------------------------------------------
    // FACT_public: M64/60 base 993 Turbo max boost is 0.8 bar
    // (SRC-PORSCHE-CHRISTOPHORUS-993-TURBO-DATA); the 3.6 L twin-turbo study
    // brief targets 1.0 bar. Either way, pressure is a load input, NOT a
    // geometric driver here; wall sizing is untouched by it.
    public const float fBoostTargetBar = 1.0f;      // FACT_public, non-sizing
    public const float fBoostOemBar = 0.8f;         // FACT_public, non-sizing
}
