//
// M64 valvetrain components — parametric PicoGK signed-distance field functions
// and CLI export driver.
//
// Parts record: parts/m64-valvetrain-0001
// Layout-grade (F1_envelope) geometry for the M64/60 digital twin. NOTHING here
// is measured, fitted, tested, safe or manufacturing-ready. Engine-critical
// parts are `prohibited_pending_engineering` per SAFETY.md: a calculation never
// authorizes manufacturing.
//
// Evidence gate (see parts/m64-valvetrain-0001/README.md, provenance.json and
// docs/research/m64-public-engine-data-2026-09-27.md):
//   [SOURCED]     registered public source (declaration or manual OCR fragment,
//                 status SINGLE_SOURCE / ocr_unreviewed where applicable).
//   [ASSUMPTION]  engineering inference; a design variable, not a claim.
//   [UNKNOWN]     absent from the public domain (M64-ACQ-0002 blocks the cam
//                 profile); implemented as a configurable parameter whose
//                 default is a placeholder that metrology must replace.
//
// Coordinate convention: local per component, axis along Z, units mm.
// Valve: z=0 at the head back face, head material at z<0, tip at
// z=+fOverallLengthMm. Cam: axis along Z centred at z=0.
//

using System.Diagnostics;
using System.Globalization;
using System.Numerics;
using System.Security.Cryptography;
using System.Text.Json;
using PicoGK;

namespace M64Valvetrain;

/// <summary>Small exact SDF primitive helpers (mm).</summary>
static class SdfPrims
{
    /// <summary>Distance from the point to the Z axis.</summary>
    public static float RadialDist(in Vector3 vec)
        => MathF.Sqrt(vec.X * vec.X + vec.Y * vec.Y);

    /// <summary>Capsule SDF between two spheres.</summary>
    public static float Capsule(in Vector3 vec, Vector3 vecA, Vector3 vecB, float fR)
    {
        Vector3 ba = vecB - vecA;
        Vector3 pa = vec - vecA;
        float h = Math.Clamp(Vector3.Dot(pa, ba) / MathF.Max(1e-6f, ba.LengthSquared()), 0f, 1f);
        return (pa - ba * h).Length() - fR;
    }
}

/// <summary>
/// Poppet-valve envelope: faceted head, stem, keeper groove. Head Ø and stem Ø
/// are sourced per variant; functional length, seat width, head thickness and
/// tip geometry are UNKNOWN/ASSUMPTION — each one is a constructor parameter.
/// Status: F1_envelope layout proxy. Not the original part.
/// </summary>
public sealed class Valve : IBoundedImplicit
{
    // ---- Geometry parameters (mm unless noted); evidence tags in provenance.json ----
    public readonly float fHeadDiameterMm;      // [SOURCED] 49.0 intake / 43.5 exhaust-Turbo variant (declarations)
    public readonly float fStemDiameterMm;      // [SOURCED, declared Ø8]
    public readonly float fOverallLengthMm;     // [UNKNOWN] functional length; ~109/110.1 envelope hints only
    public readonly float fHeadThicknessMm;     // [ASSUMPTION]
    public readonly float fSeatFaceAngleDeg;    // [SOURCED, ocr_unreviewed] 45 deg face (manual 15-8d)
    public readonly float fSeatWidthMm;         // [UNKNOWN]
    public readonly float fTipDiameterMm;       // [ASSUMPTION]
    public readonly float fTipLengthMm;         // [ASSUMPTION]

    readonly float m_fRimInnerR;                // derived: seat-face intersection with the face plane
    readonly BBox3 m_oBounds;

    public Valve(   float fHeadDiameterMm,
                    float fStemDiameterMm,
                    float fOverallLengthMm,
                    float fHeadThicknessMm = 5.5f,
                    float fSeatFaceAngleDeg = 45f,
                    float fSeatWidthMm = 1.5f,
                    float fTipDiameterMm = 6.5f,
                    float fTipLengthMm = 6.0f)
    {
        this.fHeadDiameterMm = fHeadDiameterMm;
        this.fStemDiameterMm = fStemDiameterMm;
        this.fOverallLengthMm = fOverallLengthMm;
        this.fHeadThicknessMm = fHeadThicknessMm;
        this.fSeatFaceAngleDeg = fSeatFaceAngleDeg;
        this.fSeatWidthMm = fSeatWidthMm;
        this.fTipDiameterMm = fTipDiameterMm;
        this.fTipLengthMm = fTipLengthMm;

        float halfAngle = fSeatFaceAngleDeg * MathF.PI / 180f;
        m_fRimInnerR = fHeadDiameterMm / 2f - fSeatWidthMm / MathF.Cos(halfAngle);
        if (m_fRimInnerR <= fStemDiameterMm / 2f)
            throw new ArgumentException("Seat width eats the head: rim inner radius below stem radius");
        if (fTipDiameterMm >= fStemDiameterMm)
            throw new ArgumentException("Tip diameter must be below stem diameter for a groove");

        float rMax = fHeadDiameterMm / 2f;
        m_oBounds = new BBox3(
            -rMax - 1, -rMax - 1, -fHeadThicknessMm - 1,
            rMax + 1, rMax + 1, fOverallLengthMm + 1);
    }

    /// <summary>Intake proxy, head Ø 49 mm [SOURCED declaration; manual 15-8d 49±0.1, ocr_unreviewed].</summary>
    public static Valve CreateIntake()
        => new(fHeadDiameterMm: 49.0f,
               fStemDiameterMm: 8.0f,           // declared Ø8 (manual 7.970 -0.012, ocr_unreviewed)
               fOverallLengthMm: 110.1f);       // [UNKNOWN] manual 15-8d 110.1±0.1 (Carrera 2V) — placeholder default

    /// <summary>Exhaust Turbo-variant proxy, head Ø 43.5 mm [SOURCED declaration, no tolerance].</summary>
    public static Valve CreateExhaustTurbo()
        => new(fHeadDiameterMm: 43.5f,
               fStemDiameterMm: 8.0f,
               fOverallLengthMm: 109.0f);       // [UNKNOWN] ~108.9–109 stated envelope (SINGLE_SOURCE) — placeholder default

    public BBox3 oBounds => m_oBounds;

    public float fSignedDistance(in Vector3 vec)
    {
        float r = SdfPrims.RadialDist(vec);
        float z = vec.Z;
        float rStem = fStemDiameterMm / 2f;
        float rHead = fHeadDiameterMm / 2f;
        float h = fHeadThicknessMm;
        float tanA = MathF.Tan(fSeatFaceAngleDeg * MathF.PI / 180f);
        
        // Stem: cylinder r_stem, from the head back face (z=0, embedded in the
        // head by the union) to the tip, with a step down to the tip pilot.
        float zTipStart = fOverallLengthMm - fTipLengthMm;
        float dStemMain = MathF.Max(r - rStem,
                        MathF.Max(z - fOverallLengthMm, -z));
        float dTip = MathF.Max(r - fTipDiameterMm / 2f,
                    MathF.Max(z - fOverallLengthMm, zTipStart - z));
        float dStemBody = MathF.Min(dStemMain, dTip);

        // Keeper groove ring (ASSUMPTION): shallow annular cut below the tip.
        float zGrooveMid = zTipStart - 1.5f;
        float dGroove = MathF.Max(MathF.Abs(r - (rStem - 0.75f)) - 0.75f,
                                  MathF.Abs(z - zGrooveMid) - 1.0f);
        dStemBody = MathF.Max(dStemBody, -dGroove);   // subtract groove

        // Head: disc z in [-h, 0] with a seat-face bevel on the underside.
        // Inside the trapezoidal meridian section, CW, edges:
        //   top: z = 0                -> inside where z <= 0
        //   outer: r = rHead          -> inside where r <= rHead
        //   bevel through (rHead, -h) and (rimInnerR, 0)
        //                   -> inside where r <= rHead - (z + h) * tanA
        //   inner: r = rStem          -> inside where r >= rStem
        // Each exact half-plane distance; the 90-deg corners are exact under
        // max (Lipschitz-1). The two far half-planes are masked off (they do
        // not bound the section) and the bevel half-plane never binds inside
        // the masked region, so the max is the exact SDF of the revolved
        // section (conservative to Lipschitz-1 in 3D).
        float dTop = z;                                   // inside: z <= 0
        float dOuter = r - rHead;                         // inside: r <= rHead
        float dBevel = ((r - rHead) + (z + h) * tanA) * MathF.Cos(fSeatFaceAngleDeg * MathF.PI / 180f);
        float dBevelMasked = MathF.Max(dBevel, m_fRimInnerR - r);   // mask outboard of the rim
        dBevelMasked = MathF.Max(dBevelMasked, dTop);               // mask above the back face
        float dInner = rStem - r;                                   // mask (never binds on the head)
        float dHead = MathF.Max(MathF.Max(dTop, dOuter), MathF.Max(dBevelMasked, dInner));

        return MathF.Min(dStemBody, dHead);
    }
}

/// <summary>
/// Valve spring seat: annular pad the outer spring bears on. Registered facts
/// are the installed-length spec only (A = 36.7 / 35.7 +0.3 mm, manual
/// 15 65 06 / 15-8f, SINGLE_SOURCE, ocr_unreviewed). Seat diameters are
/// [UNKNOWN]; height is [ASSUMPTION].
/// </summary>
public sealed class SpringSeat : IBoundedImplicit
{
    public readonly float fOuterDiameterMm;     // [UNKNOWN] configurable
    public readonly float fInnerDiameterMm;     // [UNKNOWN] configurable (head clearance)
    public readonly float fHeightMm;            // [ASSUMPTION]

    /// <summary>Installed spring length A, intake, M64/05..08 [SOURCED, SINGLE_SOURCE ocr_unreviewed].</summary>
    public const float InstalledLengthIntakeMm = 36.7f;
    /// <summary>Installed spring length A, exhaust, M64/05..08 [SOURCED, SINGLE_SOURCE ocr_unreviewed].</summary>
    public const float InstalledLengthExhaustMm = 35.7f;
    /// <summary>Printed tolerance on A (+0.3, no minus) [SOURCED, ocr_unreviewed].</summary>
    public const float InstalledLengthToleranceMm = 0.3f;

    readonly BBox3 m_oBounds;

    public SpringSeat(  float fOuterDiameterMm = 36.0f,   // [ASSUMPTION] placeholder
                        float fInnerDiameterMm = 22.0f,   // [ASSUMPTION]
                        float fHeightMm = 4.0f)           // [ASSUMPTION]
    {
        if (fInnerDiameterMm >= fOuterDiameterMm)
            throw new ArgumentException("Seat inner diameter must be below outer diameter");
        this.fOuterDiameterMm = fOuterDiameterMm;
        this.fInnerDiameterMm = fInnerDiameterMm;
        this.fHeightMm = fHeightMm;
        float r = fOuterDiameterMm / 2f;
        m_oBounds = new BBox3(-r - 1, -r - 1, -1, r + 1, r + 1, fHeightMm + 1);
    }

    public BBox3 oBounds => m_oBounds;

    public float fSignedDistance(in Vector3 vec)
    {
        float r = SdfPrims.RadialDist(vec);
        // Annular prism = outside-of-outer-cylinder (r - rOut) MINUS
        // inside-of-inner-cylinder (signed: rIn - r, positive outside the
        // hole) intersected with the slab [0, h].
        float dOuter = r - fOuterDiameterMm / 2f;
        float dInner = fInnerDiameterMm / 2f - r;
        return MathF.Max(MathF.Max(dOuter, dInner),
                         MathF.Max(-vec.Z, vec.Z - fHeightMm));
    }
}

/// <summary>
/// Cam follower (bucket tappet envelope, OHV-2V-lineage 901/911/964-type form).
/// The FORM is an [ASSUMPTION] for layout; hydraulic lash compensation is
/// public fact (FACT_public, Parts Guide + Carrera spec doc). No M64 bucket
/// dimensions are public: all diameters/heights are configurable placeholders.
/// </summary>
public sealed class CamFollower : IBoundedImplicit
{
    public readonly float fOuterDiameterMm;     // [UNKNOWN] configurable envelope
    public readonly float fHeightMm;            // [ASSUMPTION]
    public readonly float fWallThicknessMm;     // [ASSUMPTION] cup wall
    public readonly float fCrownSagittaMm;      // [ASSUMPTION] shallow crown on the contact face

    // Registered hydraulic-lifter travel, Carrera manual p.151 (15 59 04,
    // ocr_unreviewed): intake 0.2..1.85, exhaust 0.6..2.25 mm.
    public static readonly (float Min, float Max) LifterTravelIntakeMm = (0.2f, 1.85f);
    public static readonly (float Min, float Max) LifterTravelExhaustMm = (0.6f, 2.25f);

    readonly BBox3 m_oBounds;

    public CamFollower( float fOuterDiameterMm = 32.0f,   // [ASSUMPTION] placeholder
                        float fHeightMm = 40.0f,           // [ASSUMPTION]
                        float fWallThicknessMm = 3.0f,     // [ASSUMPTION]
                        float fCrownSagittaMm = 0.4f)      // [ASSUMPTION]
    {
        if (fWallThicknessMm * 2 >= fOuterDiameterMm)
            throw new ArgumentException("Cup wall thicker than the cup");
        this.fOuterDiameterMm = fOuterDiameterMm;
        this.fHeightMm = fHeightMm;
        this.fWallThicknessMm = fWallThicknessMm;
        this.fCrownSagittaMm = fCrownSagittaMm;
        float r = fOuterDiameterMm / 2f;
        m_oBounds = new BBox3(-r - 1, -r - 1, -1, r + 1, r + 1, fHeightMm + 1);
    }

    public BBox3 oBounds => m_oBounds;

    /// <summary>
    /// Hollow cup, axis Z, closed crown at +Z (toward the cam), open skirt at
    /// z=0. Crown carries a shallow parabolic dimple (ASSUMPTION) approximating
    /// a spherical contact face.
    /// </summary>
    public float fSignedDistance(in Vector3 vec)
    {
        float r = SdfPrims.RadialDist(vec);
        float rOut = fOuterDiameterMm / 2f;

        // Solid cup with the crown pushed down by a parabolic sagitta.
        float crownZ = fHeightMm - fCrownSagittaMm * (r * r) / (rOut * rOut);
        float dOuter = r - rOut;
        float dBottom = -vec.Z;
        float dTop = vec.Z - crownZ;
        float dSolid = MathF.Max(dOuter, MathF.Max(dBottom, dTop));

        // Cavity: cylinder of radius rCav with a flat ceiling at
        // crownZ - wall, unbounded below (open skirt). Signed distance of
        // that half-space intersection: max(r - rCav, z - ceiling); positive
        // outside, so dSolid MAX this subtracts the cavity.
        float cavityCeiling = crownZ - fWallThicknessMm;
        float dCav = MathF.Max(r - (rOut - fWallThicknessMm),
                               vec.Z - cavityCeiling);

        return MathF.Max(dSolid, dCav);
    }
}

/// <summary>
/// Per-bank camshaft: base-circle shaft + N identical configurable lobes at
/// even angular spacing. The M64 cam profile is NOT public (M64-ACQ-0002): the
/// lobe is a cosine-rise tangent placeholder driven by lift, duration and LCA
/// inputs, all [UNKNOWN]/[ASSUMPTION]. Layout hypothesis, never a claimed M64
/// profile. Not a released part.
/// </summary>
public sealed class CamshaftParametric : IBoundedImplicit
{
    public readonly float fBaseCircleDiameterMm;   // [UNKNOWN] configurable placeholder
    public readonly float fShaftDiameterMm;        // [ASSUMPTION]
    public readonly float fLobeLiftMm;             // [UNKNOWN] M64-ACQ-0002
    public readonly float fLobeDurationDeg;        // [UNKNOWN] cam degrees, [ASSUMPTION] default
    public readonly float fLobeWidthMm;            // [ASSUMPTION]
    public readonly int nLobeCount;                // [ASSUMPTION] per-bank layout hypothesis
    public readonly float fLobeSpacingMm;          // [ASSUMPTION] layout only
    public readonly float fLengthMm;               // [ASSUMPTION] derived envelope

    // Cam timing at 1 mm lift, 0 lash, 993 Carrera manual p.16 (page_checked):
    // intake opens 1 deg BTDC, closes 60 deg ABDC; exhaust opens 45 deg BBDC,
    // closes 6 deg ATDC (crank degrees). Reference for the 2V Carrera only —
    // transfer to the 4V M64/60 design target is forbidden without
    // justification. Kept so defaults are traceable, not invented.
    public const float RefIntakeOpenBTDCDeg = 1f;
    public const float RefIntakeCloseABDCDeg = 60f;
    public const float RefExhaustOpenBBDCDeg = 45f;
    public const float RefExhaustCloseATDCDeg = 6f;

    readonly float[] m_afLobeAngleDeg;
    readonly BBox3 m_oBounds;

    public CamshaftParametric(  float fBaseCircleDiameterMm = 34f,    // [UNKNOWN] placeholder
                                float fLobeLiftMm = 8f,                // [UNKNOWN] placeholder
                                float fLobeDurationDeg = 240f,         // [ASSUMPTION] cam deg
                                float fLobeLcaDeg = 0f,                // [ASSUMPTION] first-lobe offset
                                float fShaftDiameterMm = 25f,          // [ASSUMPTION]
                                float fLobeWidthMm = 28f,              // [ASSUMPTION]
                                float fLobeSpacingMm = 55f,            // [ASSUMPTION] layout
                                int nLobesPerBank = 6)                 // [ASSUMPTION] 4V/bank hypothesis
    {
        this.fBaseCircleDiameterMm = fBaseCircleDiameterMm;
        this.fLobeLiftMm = fLobeLiftMm;
        this.fLobeDurationDeg = fLobeDurationDeg;
        this.fShaftDiameterMm = fShaftDiameterMm;
        this.fLobeWidthMm = fLobeWidthMm;
        this.fLobeSpacingMm = fLobeSpacingMm;

        // Lobe count: a 4-valve 6-cylinder bank needs 12 lobes split over two
        // camshafts = 6 per bank (design target valves_per_cylinder = 4,
        // manual applicability record). Count is a parameter, not a claim.
        nLobeCount = Math.Max(1, nLobesPerBank);

        // Even angular spacing is a placeholder; the lobe map derived from the
        // firing order 1-6-2-4-3-5 (FACT_public) is not public.
        m_afLobeAngleDeg = new float[nLobeCount];
        for (int i = 0; i < nLobeCount; i++)
            m_afLobeAngleDeg[i] = fLobeLcaDeg + 360f * i / nLobeCount;

        fLengthMm = (nLobeCount - 1) * fLobeSpacingMm + 2 * (fLobeWidthMm + fLobeSpacingMm / 2f);
        float rMax = fBaseCircleDiameterMm / 2f + fLobeLiftMm;
        m_oBounds = new BBox3(-rMax - 1, -rMax - 1, -fLengthMm / 2f - 1,
                              rMax + 1, rMax + 1, fLengthMm / 2f + 1);
    }

    public BBox3 oBounds => m_oBounds;

    /// <summary>
    /// Placeholder profile radius at fDeg angular distance from the lobe nose:
    /// cosine rise over half the duration — a kinematic shape, NOT an M64
    /// profile (M64-ACQ-0002).
    /// </summary>
    public float ProfileRadiusMm(float fDegFromNose)
    {
        float rB = fBaseCircleDiameterMm / 2f;
        float halfDur = fLobeDurationDeg / 2f;
        float beta = Math.Abs(fDegFromNose);
        if (beta >= halfDur)
            return rB;
        float s = beta / halfDur;
        return rB + 0.5f * fLobeLiftMm * (1f + MathF.Cos(MathF.PI * s));
    }

    public float fSignedDistance(in Vector3 vec)
    {
        float r = SdfPrims.RadialDist(vec);
        float theta = MathF.Atan2(vec.Y, vec.X) * 180f / MathF.PI;   // -180..180

        float dZEnds = MathF.Abs(vec.Z) - fLengthMm / 2f;
        // Base-circle body along the whole shaft (covers journals between lobes).
        float dResult = MathF.Max(r - fBaseCircleDiameterMm / 2f, dZEnds);
        // Thin shaft ends outboard of the outer lobes keep the body honest.
        float firstZ = -(nLobeCount - 1) * fLobeSpacingMm / 2f;
        float lastZ = firstZ + (nLobeCount - 1) * fLobeSpacingMm;
        float dEndShaft = MathF.Max(r - fShaftDiameterMm / 2f, dZEnds);
        float outboard = MathF.Max(firstZ - fLobeWidthMm / 2f - vec.Z,
                                   vec.Z - (lastZ + fLobeWidthMm / 2f));
        dResult = MathF.Min(dResult, MathF.Max(dEndShaft, -outboard));

        // Lobes: z-bounded slabs; radius from the cosine profile. The radial
        // distance is an approximation (Lipschitz ~1 on the cosine flanks at
        // these proportions) documented in validation/COMPILE_VERDICT.md.
        float halfWidth = fLobeWidthMm / 2f;
        for (int i = 0; i < nLobeCount; i++)
        {
            float dSlab = MathF.Abs(vec.Z - (firstZ + i * fLobeSpacingMm)) - halfWidth;
            if (dSlab > dResult)
                continue;   // cheap z rejection
            float dAng = theta - m_afLobeAngleDeg[i];
            while (dAng > 180f) dAng -= 360f;
            while (dAng < -180f) dAng += 360f;
            float dLobe = MathF.Max(r - ProfileRadiusMm(dAng), dSlab);
            dResult = MathF.Min(dResult, dLobe);
        }
        return dResult;
    }
}

/// <summary>
/// CLI driver: exports the five layout proxies as repository-standard PicoGK
/// meshes (STL, mm) with a run report. Authored blind against the PicoGK 2.3.0
/// API in /upstream; until a station run exists this lane is "authored, not
/// compiled" — never a faked mesh.
///   Usage: M64Valvetrain NEW_OUTPUT_DIR VOXEL_MM (0.2..2.0)
/// </summary>
public static class Program
{
    static string Sha(string path)
    {
        using var stream = File.OpenRead(path);
        return Convert.ToHexString(SHA256.HashData(stream)).ToLowerInvariant();
    }

    static float[] V(Vector3 value) => [value.X, value.Y, value.Z];

    static object Box(BBox3 value) => new { min = V(value.vecMin), max = V(value.vecMax) };

    public static int Main(string[] args)
    {
        if (args.Length != 2 ||
            !float.TryParse(args[1], NumberStyles.Float, CultureInfo.InvariantCulture, out float voxelMm) ||
            !float.IsFinite(voxelMm) || voxelMm < 0.2f || voxelMm > 2f)
        {
            Console.Error.WriteLine("Usage: M64Valvetrain NEW_OUTPUT_DIR VOXEL_MM (0.2..2.0)");
            return 2;
        }

        string output = Path.GetFullPath(args[0]);
        if (Directory.Exists(output) || File.Exists(output))
        {
            Console.Error.WriteLine("Output directory must not exist (no overwrite).");
            return 2;
        }
        Directory.CreateDirectory(output);

        var timer = Stopwatch.StartNew();
        void Stage(string stage)
        {
            Console.WriteLine(JsonSerializer.Serialize(new { stage, elapsed_seconds = timer.Elapsed.TotalSeconds }));
            Console.Out.Flush();
        }

        try
        {
            Stage("init_library");
            using Library library = new(voxelMm);

            var components = new (string Name, IBoundedImplicit Implicit, string Evidence)[]
            {
                ("valve-intake-49-proxy", Valve.CreateIntake(),
                 "head/stem SOURCED declared; length/seat/thickness UNKNOWN-ASSUMPTION"),
                ("valve-exhaust-43_5-turbo-proxy", Valve.CreateExhaustTurbo(),
                 "head/stem SOURCED declared (no tolerance); length/seat UNKNOWN-ASSUMPTION"),
                ("spring-seat-proxy", new SpringSeat(),
                 "diameters UNKNOWN; installed-length spec registered, geometry ASSUMPTION"),
                ("cam-follower-bucket-proxy", new CamFollower(),
                 "form ASSUMPTION (OHV-2V lineage); hydraulic lash compensation FACT_public"),
                ("camshaft-parametric-proxy", new CamshaftParametric(),
                 "base circle + cosine lobe ONLY; M64 profile UNKNOWN (M64-ACQ-0002)"),
            };

            var parts = new List<object>();
            foreach (var (name, implicitFn, evidence) in components)
            {
                Stage($"voxelize_{name}");
                using Voxels vox = new(library, implicitFn);
                vox.CalculateProperties(out float volume, out BBox3 bounds);
                if (!float.IsFinite(volume) || volume <= 0)
                    throw new InvalidDataException($"Nonpositive voxel volume for {name}");
                Stage($"mesh_{name}");
                using Mesh mesh = new(vox);
                string stlPath = Path.Combine(output, $"{name}.stl");
                mesh.SaveToStlFile(stlPath, Mesh.EStlUnit.MM);
                parts.Add(new
                {
                    id = name,
                    filename = $"{name}.stl",
                    sha256 = Sha(stlPath),
                    triangles = mesh.nTriangleCount(),
                    volume_mm3 = volume,
                    bounds_mm = Box(bounds),
                    evidence_note = evidence
                });
            }

            Stage("write_report");
            var report = new
            {
                schema = "m64-picogk-valvetrain-run-v1",
                status = "layout_geometry_job_completed_not_physics_validation",
                utc_completed = DateTimeOffset.UtcNow,
                voxel_mm = voxelMm,
                components = parts,
                evidence_gate = "SOURCED / ASSUMPTION / UNKNOWN per provenance.json; nothing measured, fitted, tested or released",
                dimensional_correctness_claimed = false,
                manufacturing_authorized = false
            };
            File.WriteAllText(Path.Combine(output, "run-report.json"),
                JsonSerializer.Serialize(report, new JsonSerializerOptions { WriteIndented = true }));
            Stage("M64_PICOGK_VALVETRAIN_PASS");
            return 0;
        }
        catch (Exception exception)
        {
            File.WriteAllText(Path.Combine(output, "FAILED.json"), JsonSerializer.Serialize(new
            {
                status = "failed",
                error_type = exception.GetType().Name,
                error = exception.Message,
                elapsed_seconds = timer.Elapsed.TotalSeconds,
                manufacturing_authorized = false
            }, new JsonSerializerOptions { WriteIndented = true }));
            Console.Error.WriteLine($"M64_PICOGK_VALVETRAIN_FAIL {exception.GetType().Name}: {exception.Message}");
            return 1;
        }
    }
}
