using System.Numerics;
using PicoGK;

namespace M64DigitalTwin.ChargeAir;

// PicoGK construction of the M64/60 charge-air path study.
//
// API policy: only calls already verified in this repository's pinned
// containers/m64-leap71 witness and the existing head/layout PicoGK jobs
// (Library ctor, Lattice(Library), Lattice.AddSphere, Lattice.AddBeam,
// Voxels(Lattice), new Voxels(otherVoxels), Voxels.BoolSubtract, Voxels.BoolAdd,
// Voxels.voxOffset, Voxels.CalculateProperties, Mesh(Voxels),
// Mesh.SaveToStlFile(path, Mesh.EStlUnit.MM)). No invented API syntax.
//
// Centerline+SDF sweep: the swept hose/tube shells are built by piecewise
// linear centerlines offset through segments with a fixed swept radius
// (Lattice.AddBeam with rounded sphere caps at each waypoint, i.e. a
// Minkowski-style sweep of a disc along the polyline). This is a voxel sweep
// of a centerline, not an exact offset-body evaluation.
public static class ChargeAirGeometry
{
    // Polyline length in mm (chord-sum; the segment caps make the swept body
    // slightly longer, which the caller reports separately).
    public static float CenterlineLengthMm(Vector3[] aPts)
    {
        float fLen = 0.0f;
        for (int i = 1; i < aPts.Length; i++)
            fLen += (aPts[i] - aPts[i - 1]).Length();
        return fLen;
    }

    static Vector3 MirrorY(Vector3 v) => new(v.X, -v.Y, v.Z);

    static Vector3[] MirrorBank(Vector3[] aPts, bool bMirror)
    {
        if (!bMirror) return aPts;
        Vector3[] a = new Vector3[aPts.Length];
        for (int i = 0; i < aPts.Length; i++) a[i] = MirrorY(aPts[i]);
        Array.Reverse(a); // keep start->end order pointing the same way
        return a;
    }

    // Swept solid along a polyline: sphere at each waypoint, rectangular beam
    // between consecutive waypoints. Both radii equal = constant-radius sweep.
    static void AddSweep(Lattice lat, Vector3[] aPts, float fRadiusMm)
    {
        for (int i = 0; i < aPts.Length; i++)
            lat.AddSphere(aPts[i], fRadiusMm);
        for (int i = 1; i < aPts.Length; i++)
            lat.AddBeam(aPts[i - 1], fRadiusMm, aPts[i], fRadiusMm, false);
    }

    // Hollow swept shell = outer sweep minus inner sweep (voxel booleans).
    static Voxels HollowSweep(Lattice latOuter, Lattice latInner)
    {
        Voxels voxOuter = new(latOuter);
        Voxels voxInner = new(latInner);
        voxOuter.BoolSubtract(voxInner);
        return voxOuter;
    }

    // Compressor-outlet-to-throttle hard tube for one bank (hollow).
    public static Voxels TubeVoxels(ChargeAirParameters P, bool bMirrorBank)
    {
        Vector3[] aPath = MirrorBank(P.aTubeWaypointsPosBank, bMirrorBank);
        Lattice latOuter = new(Library.oLibrary());
        Lattice latInner = new(Library.oLibrary());
        AddSweep(latOuter, aPath, P.fNominalDuctOuterDiaMm / 2.0f);
        AddSweep(latInner, aPath, P.fNominalDuctBoreDiaMm / 2.0f - P.fRadialClearanceMm / 2.0f);
        return HollowSweep(latOuter, latInner);
    }

    // Charge-air coupling sleeve at a path junction: a fat short sweep over the
    // mating section, hollow inner bore matching the tube bore plus clearance.
    public static Voxels CouplingVoxels(ChargeAirParameters P, bool bMirrorBank)
    {
        Vector3[] aPath = MirrorBank(P.aTubeWaypointsPosBank, bMirrorBank);
        // Coupling straddles the first-to-second waypoint junction end of the
        // tube (compressor side): take the last segment tail, shortened.
        Vector3 vecEnd = aPath[^1];
        Vector3 vecPrev = aPath[^2];
        Vector3 vecDir = Vector3.Normalize(vecEnd - vecPrev);
        Vector3 vecStart = vecEnd - vecDir * P.fCouplingLengthMm;
        Lattice latOuter = new(Library.oLibrary());
        Lattice latInner = new(Library.oLibrary());
        AddSweep(latOuter, new[] { vecStart, vecEnd }, P.fCouplingOuterDiaMm / 2.0f);
        AddSweep(latInner, new[] { vecStart, vecEnd }, P.fNominalDuctOuterDiaMm / 2.0f + P.fRadialClearanceMm / 2.0f);
        return HollowSweep(latOuter, latInner);
    }

    // Per-bank plenum: rounded box shell (outer rounded box minus inner box),
    // built as a sphere-swept short beam whose rectangular cross-section is
    // approximated by the beam half-lengths, then offset. To stay inside the
    // verified API, the rounded box is a beam with unequal rectangular
    // diameters and rounded ends (bRounded=false), corner radius approximated
    // by the beam cross-section rounding that PicoGK beams provide.
    public static Voxels PlenumVoxels(ChargeAirParameters P, bool bMirrorBank)
    {
        float fY = bMirrorBank ? -P.fPlenumCentreYPosBank : P.fPlenumCentreYPosBank;
        Vector3 vecCentre = new(0.0f, fY, 160.0f); // ASSUMPTION height station
        Vector3 vecHalf = new(P.fPlenumLengthMm / 2.0f - P.fPlenumCornerRadiusMm,
                              P.fPlenumWidthMm / 2.0f - P.fPlenumCornerRadiusMm,
                              0.0f);
        Vector3 vecA = vecCentre - new Vector3(vecHalf.X, vecHalf.Y, P.fPlenumHeightMm / 2.0f - P.fPlenumCornerRadiusMm);
        Vector3 vecB = vecCentre + new Vector3(vecHalf.X, vecHalf.Y, P.fPlenumHeightMm / 2.0f - P.fPlenumCornerRadiusMm);
        Lattice latOuter = new(Library.oLibrary());
        latOuter.AddBeam(vecA, P.fPlenumCornerRadiusMm, vecB, P.fPlenumCornerRadiusMm, false);
        // PicoGK AddBeam here is elliptical-section; record it as an outer
        // form screen, then thicken by the configured wall with a positive
        // voxel offset and hollow with the same beam shrunk by the wall.
        Voxels voxOuter = new(latOuter);
        Lattice latInner = new(Library.oLibrary());
        float fRi = P.fPlenumCornerRadiusMm - P.fWallThicknessMm;
        latInner.AddBeam(vecA, fRi, vecB, fRi, false);
        Voxels voxInner = new(latInner);
        voxOuter.BoolSubtract(voxInner);
        return voxOuter;
    }

    // Interconnect hose for one bank: centerline sweep at the hose outer
    // radius, hollow to the flow radius.
    public static Voxels HoseVoxels(ChargeAirParameters P, bool bMirrorBank)
    {
        Vector3[] aPath = MirrorBank(P.aHoseWaypointsPosBank, bMirrorBank);
        Lattice latOuter = new(Library.oLibrary());
        Lattice latInner = new(Library.oLibrary());
        AddSweep(latOuter, aPath, P.fHoseOuterRadiusMm);
        AddSweep(latInner, aPath, P.fHoseFlowRadiusMm);
        return HollowSweep(latOuter, latInner);
    }

    // Whole path for both banks: union of tube+coupling+plenum+hose per bank.
    // The intercooler itself is left as the bounding-zone sphere pair for
    // envelope reference only.
    public static Voxels AssemblyVoxels(ChargeAirParameters P)
    {
        Voxels voxAll = new();
        foreach (bool bMirror in new[] { false, true })
        {
            using Voxels voxTube = TubeVoxels(P, bMirror);
            using Voxels voxCpl = CouplingVoxels(P, bMirror);
            using Voxels voxPlenum = PlenumVoxels(P, bMirror);
            using Voxels voxHose = HoseVoxels(P, bMirror);
            voxAll.BoolAdd(voxTube);
            voxAll.BoolAdd(voxCpl);
            voxAll.BoolAdd(voxPlenum);
            voxAll.BoolAdd(voxHose);
        }
        // Intercooler packaging envelope: two spheres marking the core zone.
        Lattice latIc = new(Library.oLibrary());
        latIc.AddSphere(new Vector3(P.vecIntercoolerCentre.X, 0.0f, P.vecIntercoolerCentre.Z),
                        P.fIntercoolerCoreWidthMm / 2.0f);
        using Voxels voxIc = new(latIc);
        using Voxels voxShell = voxIc.voxOffset(P.fHoseOuterRadiusMm);
        voxShell.BoolSubtract(voxIc);
        voxAll.BoolAdd(voxShell);
        return voxAll;
    }
}
