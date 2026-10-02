// M64Fan — parametric N-blade M64/60 cooling fan rotor + housing, PicoGK C#.
// Wave-2 lane wt-fan. Implements the organic-study lessons (swept stacking
// line, spanwise twist, curved camber with configurable sign, rounded chord
// ends, implicit root blend) from twins/993-engine-cooling-fan-system-f0/
// ORGANIC_BLADE_STUDY.md, on the 11-blade Turbo M64.60 reference rebuild
// (REFERENCE_REBUILD.md). The housing throat is parametric and derived from
// the rotor diameter plus a configured radial clearance, which resolves the
// documented F0 Carrera clearance collision by construction (see README).
// Units: mm. Voxel size and all physical inputs come from the config file.
using System.Numerics;
using System.Text.Json;
using PicoGK;

internal static class Program {
    static JsonElement s_data;

    // Required float parameter; throws when missing or non-finite.
    static float Read(string name) {
        if (!s_data.TryGetProperty(name, out var value))
            throw new ArgumentException("Missing required parameter: " + name);
        float x = value.GetSingle();
        if (!float.IsFinite(x)) throw new ArgumentException("Non-finite parameter: " + name);
        return x;
    }

    static int Main(string[] args) {
        if (args.Length != 2) {
            Console.Error.WriteLine("Usage: M64Fan fan-config.json new-output-directory");
            return 2;
        }
        s_data = JsonDocument.Parse(File.ReadAllText(args[0])).RootElement;

        float voxel = Read("voxel_mm");
        float thickness = Read("blade_thickness_mm");
        if (voxel <= 0 || voxel > thickness / 3)
            throw new ArgumentException("Voxel too coarse for blade thickness");
        string output = Path.GetFullPath(args[1]);
        if (Directory.Exists(output)) throw new IOException("Output exists; preserve prior run");
        Directory.CreateDirectory(output);

        // F0 clearance-collision resolution by construction: the housing
        // throat is not a free parameter. It must equal the rotor diameter
        // plus twice the configured radial clearance (the integration-screen
        // rule that produced case B of the F0 study).
        float rotorR = Read("rotor_diameter_mm") / 2;
        float clearance = Read("radial_clearance_mm");
        float throatR = Read("housing_throat_diameter_mm") / 2;
        if (Math.Abs(throatR - (rotorR + clearance)) > 1e-3)
            throw new ArgumentException(
                "Housing throat must equal rotor radius + radial clearance (derived, not free)");
        if (Read("rotor_axial_offset_mm") < Read("cup_front_z_mm") + Read("housing_hub_depth_mm") + 10)
            throw new ArgumentException("Rotor cup would collide with the front alternator hub");

        using Library library = new(voxel);
        var reports = new List<object>();
        (string part, IImplicit field, BBox3 box)[] parts = {
            ("rotor", CheckedRotor(), new BBox3(new Vector3(-128, -128, Read("rotor_axial_offset_mm") - 70),
                                               new Vector3(128, 128, Read("rotor_axial_offset_mm") + 70))),
            ("housing", CheckedHousing(), new BBox3(new Vector3(-160, -160, 0),
                                                    new Vector3(160, 160, Read("housing_length_mm") + 1))),
        };
        foreach ((string part, IImplicit field, BBox3 box) in parts) {
            using Voxels volume = new(library, field, box);
            volume.CalculateProperties(out float mm3, out _);
            using Mesh raw = new(volume);
            using Mesh mesh = new(library);
            for (int i = 0; i < raw.nTriangleCount(); i++) {
                raw.GetTriangle(i, out Vector3 a, out Vector3 b, out Vector3 c);
                if (Vector3.Cross(b - a, c - a).LengthSquared() > 0) mesh.nAddTriangle(a, b, c);
            }
            if (mm3 <= 0 || mesh.nTriangleCount() == 0) throw new InvalidOperationException("Empty geometry: " + part);
            mesh.SaveToStlFile(Path.Combine(output, "m64-" + part + "-mm.stl"), Mesh.EStlUnit.MM);
            reports.Add(new { part, volume_mm3 = mm3, triangles = mesh.nTriangleCount(),
                              mass_g_at_2670 = mm3 * 2.670e-3 });
            Console.WriteLine($"GENERATED {part} volume_mm3={mm3:F1} triangles={mesh.nTriangleCount()}");
        }

        File.WriteAllText(Path.Combine(output, "generation.json"), JsonSerializer.Serialize(new {
            status = "parametric_reconstruction_unvalidated",
            collision_resolution = new {
                f0_carrera_pair = "documented F0 failure retained: Carrera rotor 280 vs Turbo-lineage throat 252, radial clearance -14 mm, BRep intersection 40388.378651 mm3",
                m64_derivation = new {
                    rotor_diameter_mm = Read("rotor_diameter_mm"),
                    radial_clearance_mm = clearance,
                    housing_throat_diameter_mm = Read("housing_throat_diameter_mm"),
                    rule = "throat = rotor diameter + 2 x radial clearance (F0 integration-screen rule, case B)",
                    hot_growth_note = "150 C case, alpha 21e-6/K, dT 130 K: throat radial growth +0.344 mm vs rotor radial growth +0.333 mm; hot clearance >= cold clearance",
                },
                resolved_by_construction = true,
            },
            parameters = s_data,
            parts = reports,
            dimensionally_validated = false,
            flow_validated = false,
            manufacturing_authorized = false,
        }, new JsonSerializerOptions { WriteIndented = true }));
        Console.WriteLine("DONE");
        return 0;
    }

    static M64Rotor CheckedRotor() { var r = new M64Rotor(Read); r.Check(); return r; }
    static FanHousing CheckedHousing() { var h = new FanHousing(Read); h.Check(); return h; }
}

sealed class M64Rotor(Func<string, float> get) : IImplicit {
    // Organic-study candidate-E morphology (negative camber variant),
    // parametrised for N blades with independent root/tip pitch and sweep.
    readonly float radius = get("rotor_diameter_mm") / 2, cup = get("cup_radius_mm"),
        front = get("cup_front_z_mm"), rear = get("cup_rear_z_mm"), wall = get("wall_mm"),
        web = get("web_mm"), bore = get("bore_radius_mm"),
        ventR = get("vent_radius_mm"), ventW = get("vent_radial_halfwidth_mm"),
        ventT = get("vent_tangential_halfwidth_mm"),
        rootChord = get("blade_root_chord_mm"), tipChord = get("blade_tip_chord_mm"),
        rootPitch = get("blade_root_pitch_deg") * MathF.PI / 180,
        tipPitch = get("blade_tip_pitch_deg") * MathF.PI / 180,
        thickness = get("blade_thickness_mm"),
        blades = get("blade_count"), vents = get("vent_count"),
        boltR = get("bolt_circle_radius_mm"), boltHole = get("bolt_hole_radius_mm"),
        sweep = get("tip_sweep_mm"), camberHeight = get("camber_height_mm"),
        blend = get("root_blend_mm"), zOffset = get("rotor_axial_offset_mm");

    static float Fold(float angle, float count) {
        float period = 2 * MathF.PI / count;
        return angle - period * MathF.Round(angle / period);
    }

    public float fSignedDistance(in Vector3 p) {
        Vector3 q = new(p.X, p.Y, p.Z - zOffset);
        float r = MathF.Sqrt(q.X * q.X + q.Y * q.Y), theta = MathF.Atan2(q.Y, q.X);
        // Cup with domed web and rear ventilation vents (reference rebuild).
        float zWeb = front + 8 * MathF.Pow(Math.Clamp(r / cup, 0, 1), 2);
        float disc = MathF.Max(MathF.Abs(q.Z - zWeb) - web / 2, MathF.Max(bore - r, r - cup));
        float sleeve = MathF.Max(MathF.Abs(r - (cup - wall / 2)) - wall / 2, MathF.Max(zWeb - q.Z, q.Z - rear));
        float ventTheta = Fold(theta, vents);
        float qx = MathF.Abs(r - ventR) - ventW + 2.5f, qy = MathF.Abs(r * MathF.Sin(ventTheta)) - ventT + 2.5f;
        float opening = MathF.Min(MathF.Max(qx, qy), 0)
            + MathF.Sqrt(MathF.Pow(MathF.Max(qx, 0), 2) + MathF.Pow(MathF.Max(qy, 0), 2)) - 2.5f;
        disc = MathF.Max(disc, -opening);
        float ribTheta = Fold(theta - MathF.PI / vents, vents);
        float ribs = MathF.Max(MathF.Abs(r * MathF.Sin(ribTheta)) - 1.7f,
            MathF.Max(MathF.Abs(q.Z - zWeb - 3) - 3, MathF.Max(32 - r, r - cup + wall)));
        float body = MathF.Min(MathF.Min(disc, sleeve), ribs);
        float boltTheta = Fold(theta, 3);
        float bolt = MathF.Sqrt(MathF.Pow(r * MathF.Cos(boltTheta) - boltR, 2)
            + MathF.Pow(r * MathF.Sin(boltTheta), 2)) - boltHole;
        body = MathF.Max(body, -bolt);
        // Organic blade: swept stacking line, linear spanwise twist root->tip,
        // camber line with configurable sign, rounded chord/tip ends, root blend.
        float span = Math.Clamp((r - cup) / (radius - cup), 0, 1);
        float chord = rootChord + (tipChord - rootChord) * span;
        float localPitch = rootPitch + (tipPitch - rootPitch) * span;
        float sweepOffset = sweep * span * span;
        float tangential = r * MathF.Sin(Fold(theta - sweepOffset / MathF.Max(r, 1), blades));
        float u = tangential * MathF.Cos(localPitch) + q.Z * MathF.Sin(localPitch);
        float v = -tangential * MathF.Sin(localPitch) + q.Z * MathF.Cos(localPitch);
        float x = Math.Clamp(2 * u / chord, -1, 1);
        float camber = camberHeight * (1 - x * x) * (1 - 0.2f * x);
        float halfT = thickness / 2 * (0.65f + 0.35f * MathF.Sqrt(MathF.Max(0, 1 - x * x)));
        float qu = MathF.Abs(u) - (chord / 2 - 1.2f), qv = MathF.Abs(v - camber) - (halfT - 1.2f);
        float section = MathF.Min(MathF.Max(qu, qv), 0)
            + MathF.Sqrt(MathF.Pow(MathF.Max(qu, 0), 2) + MathF.Pow(MathF.Max(qv, 0), 2)) - 1.2f;
        float blade = MathF.Max(section, MathF.Max(cup - wall - r, r - radius));
        float h = MathF.Max(blend - MathF.Abs(body - blade), 0) / blend;
        return MathF.Min(body, blade) - h * h * blend * 0.25f;
    }

    public void Check() {
        if (blend <= 0 || thickness < 2 || blades < 5 || blades > 20 || vents < 2)
            throw new ArgumentException("Invalid rotor parameters");
        if (radius <= cup || cup <= ventR + ventW || bore >= ventR - ventW)
            throw new ArgumentException("Invalid reference topology");
        if (fSignedDistance(new Vector3(0, 0, zOffset + front)) <= 0) throw new Exception("Bore closed");
        for (int i = 0; i < (int)vents; i++) {
            float a = 2 * MathF.PI * i / vents;
            var p = new Vector3(ventR * MathF.Cos(a), ventR * MathF.Sin(a),
                zOffset + front + 8 * MathF.Pow(ventR / cup, 2));
            if (fSignedDistance(p) <= 0) throw new Exception("Vent closed");
        }
        if (fSignedDistance(new Vector3(cup - wall / 2, 0, zOffset + 10)) >= 0) throw new Exception("Cup missing");
        float midPitch = (rootPitch + tipPitch) / 2;
        for (int i = 0; i < (int)blades; i++) {
            float rMid = (cup + radius) / 2, a = 2 * MathF.PI * i / blades + sweep * 0.25f / rMid;
            var p = new Vector3(rMid * MathF.Cos(a), rMid * MathF.Sin(a),
                zOffset + camberHeight / MathF.Cos(midPitch));
            if (fSignedDistance(p) >= 0) throw new Exception("Blade missing");
        }
    }
}

sealed class FanHousing(Func<string, float> get) : IImplicit {
    // Re-derivation of the F0 housing concept (build123d master) as a PicoGK
    // implicit body; the throat diameter is a configurable input, so the F0
    // synthetic 252 mm value is not baked in.
    readonly float outer = get("housing_outer_diameter_mm") / 2, len = get("housing_length_mm"),
        shell = get("housing_shell_thickness_mm"), throat = get("housing_throat_diameter_mm") / 2,
        flange = get("housing_flange_thickness_mm"), hubR = get("housing_hub_outer_radius_mm"),
        hubBore = get("housing_hub_bore_radius_mm"), hubLen = get("housing_hub_depth_mm"),
        spokeW = get("spoke_width_mm"), spokeT = get("spoke_thickness_mm"),
        spokeEnd = get("spoke_outer_radius_mm"), mountR = get("mount_bolt_circle_radius_mm"),
        mountHole = get("mount_bore_radius_mm"), mounts = get("mount_bore_count");

    static float SdBox(Vector3 p, Vector3 h) {
        Vector3 d = new(MathF.Abs(p.X) - h.X, MathF.Abs(p.Y) - h.Y, MathF.Abs(p.Z) - h.Z);
        Vector3 c = new(MathF.Max(d.X, 0), MathF.Max(d.Y, 0), MathF.Max(d.Z, 0));
        return c.Length() + MathF.Min(MathF.Max(d.X, MathF.Max(d.Y, d.Z)), 0);
    }
    float SdTube(Vector3 p, float r0, float r1, float z0, float z1) {
        float r = MathF.Sqrt(p.X * p.X + p.Y * p.Y);
        return MathF.Max(MathF.Abs(r - (r0 + r1) / 2) - (r1 - r0) / 2,
            MathF.Max(z0 - p.Z, p.Z - z1));
    }

    public float fSignedDistance(in Vector3 p) {
        float body = SdTube(p, outer - shell, outer, 0, len);                    // shell
        body = MathF.Min(body, SdTube(p, throat, outer - shell, 0, flange));     // front flange
        body = MathF.Min(body, SdTube(p, hubBore, hubR, 0, hubLen));             // alternator hub
        float theta = MathF.Atan2(p.Y, p.X);
        float spoke = float.MaxValue;
        for (int i = 0; i < 6; i++) {
            float a = 2 * MathF.PI * i / 6;
            float cs = MathF.Cos(a), sn = MathF.Sin(a);
            Vector3 lp = new(p.X * cs + p.Y * sn, -p.X * sn + p.Y * cs, p.Z);
            spoke = MathF.Min(spoke, SdBox(lp - new Vector3((hubR + spokeEnd) / 2, 0, spokeT / 2),
                new Vector3((spokeEnd - hubR) / 2, spokeW / 2, spokeT / 2)));
        }
        body = MathF.Min(body, spoke);
        float hole = float.MaxValue;
        for (int i = 0; i < (int)mounts; i++) {
            float a = 2 * MathF.PI * i / mounts + MathF.PI / 6;
            Vector3 lp = p - new Vector3(mountR * MathF.Cos(a), mountR * MathF.Sin(a), flange / 2);
            float d = MathF.Sqrt(lp.X * lp.X + lp.Y * lp.Y);
            hole = MathF.Min(hole, MathF.Max(d - mountHole, MathF.Abs(lp.Z) - flange / 2 - 1));
        }
        return MathF.Max(body, -hole);
    }

    public void Check() {
        if (throat <= 0 || shell <= 0 || outer <= throat) throw new ArgumentException("Invalid housing");
        // Solid-interior probe points: inside material means negative signed
        // distance, so the failure sign is >= 0 (same convention as M64Rotor).
        if (fSignedDistance(new Vector3(outer - shell / 2, 0, len / 2)) >= 0) throw new Exception("Shell missing");
        if (fSignedDistance(new Vector3((throat + outer - shell) / 2, 0, flange / 2)) >= 0) throw new Exception("Flange missing");
        if (fSignedDistance(new Vector3((hubBore + hubR) / 2, 0, hubLen / 2)) >= 0) throw new Exception("Hub missing");
        if (fSignedDistance(new Vector3((hubR + spokeEnd) / 2, 0, spokeT / 2)) >= 0) throw new Exception("Spoke missing");
    }
}
