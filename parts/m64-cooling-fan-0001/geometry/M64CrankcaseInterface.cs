// M64CrankcaseInterface — parametric crankcase/collector interface body for
// the ventilated crankcase (carter ventilé) feeding the m64-cooling-fan-0001
// housing. Wave-2 lane wt-fan, second geometry source next to M64Fan.cs;
// same conventions: units mm, every physical input configurable through the
// JSON config, PicoGK implicit (IImplicit) bodies only, voxel size from the
// config, and no PicoGK API beyond what the pinned managed assembly
// (/app/PicoGK.dll, PicoGK 26.2) is verified to expose: Library, Voxels,
// IImplicit, BBox3, Mesh, CalculateProperties, SaveToStlFile. No B-Rep and
// no STEP claim anywhere.
//
// Provenance of defaults (see fan-config.json "parameter_evidence"): the
// flange bolt circle and envelope are ENGINEERING ASSUMPTIONS sized to mate
// with the fan housing inlet (outer 300 mm, hub bore 70 mm, six spokes at
// 12 mm width in fan-config.json). Nothing here is measured; see
// ../STEP_EXCHANGE.md for what the pipeline can and cannot export.
//
// Topology (one closed implicit body):
//   - annular inlet flange (front face z=0) that bolts to the fan-housing
//     inlet plane and centres on the alternator-hub bore;
//   - short inlet duct around the collector mouth (mandrel + annulus);
//   - bellmouth lip at the duct entry (torus, smooths the intake by
//     construction, radius configurable);
//   - N stub ports on a bolt circle, tilted outward by a configurable
//     angle, representing the crankcase collector branches.
//
// Like M64Fan.cs this program validates its inputs, refuses to overwrite a
// previous output directory, emits per-part volumes, and writes a
// generation.json carrying an explicit non-validation status.
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
            Console.Error.WriteLine("Usage: M64CrankcaseInterface crankcase-interface-config.json new-output-directory");
            return 2;
        }
        s_data = JsonDocument.Parse(File.ReadAllText(args[0])).RootElement;

        float voxel = Read("voxel_mm");
        float wall = Read("wall_mm");
        if (voxel <= 0 || voxel > wall / 3)
            throw new ArgumentException("Voxel too coarse for interface wall thickness");
        string output = Path.GetFullPath(args[1]);
        if (Directory.Exists(output)) throw new IOException("Output exists; preserve prior run");
        Directory.CreateDirectory(output);

        // Interface rule by construction (same spirit as the fan throat rule):
        // the flange must clear the fan-housing outer radius it bolts to, and
        // the pilot must fit the housing hub bore configured in
        // fan-config.json. These are cross-checked against values read from
        // this config, not baked in.
        float flangeR = Read("flange_outer_diameter_mm") / 2;
        if (flangeR <= Read("mating_fan_housing_outer_radius_mm") + Read("interface_gap_mm"))
            throw new ArgumentException(
                "Flange must clear the mating fan-housing outer radius plus the configured interface gap");
        if (Read("pilot_radius_mm") >= Read("housing_hub_bore_radius_mm") - 0.5f)
            throw new ArgumentException("Pilot would not fit the housing hub bore");

        using Library library = new(voxel);
        var reports = new List<object>();
        (string part, IImplicit field, BBox3 box)[] parts = {
            ("crankcase-interface", CheckedBody(),
                new BBox3(new Vector3(-flangeR - 10, -flangeR - 10, -1),
                          new Vector3(flangeR + 10, flangeR + 10,
                                      Read("duct_length_mm") + Read("port_length_mm") + 10))),
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
            role = "ventilated-crankcase collector interface to the m64-cooling-fan-0001 housing; "
                 + "placeholder topology, no measured crankcase surface is represented",
            parameters = s_data,
            parts = reports,
            dimensionally_validated = false,
            flow_validated = false,
            manufacturing_authorized = false,
        }, new JsonSerializerOptions { WriteIndented = true }));
        Console.WriteLine("DONE");
        return 0;
    }

    static CrankcaseInterface CheckedBody() { var b = new CrankcaseInterface(Read); b.Check(); return b; }
}

sealed class CrankcaseInterface : IImplicit {
    // Annular inlet flange + duct + bellmouth + N tilted stub ports, as one
    // implicit body. Composed only from analytic signed-distance primitives
    // (tube, box, torus, rotated cylinders); no PicoGK call beyond voxelising
    // the field.
    readonly Func<string, float> get;
    readonly float flangeR, flangeT, pilotR, pilotBoreR, pilotLen, ductLen, ductInR, ductOutR,
        wall, portBCR, portR, portLen, portTilt, bellmouthR, ports;

    public CrankcaseInterface(Func<string, float> getter) {
        get = getter;
        flangeR = get("flange_outer_diameter_mm") / 2;
        flangeT = get("flange_thickness_mm");
        pilotR = get("pilot_radius_mm");
        pilotBoreR = get("central_bore_radius_mm");
        pilotLen = get("pilot_length_mm");
        ductLen = get("duct_length_mm");
        ductInR = get("duct_inner_radius_mm");
        ductOutR = get("duct_outer_radius_mm");
        wall = get("wall_mm");
        portBCR = get("port_bolt_circle_radius_mm");
        portR = get("port_radius_mm");
        portLen = get("port_length_mm");
        portTilt = get("port_tilt_deg") * MathF.PI / 180;
        bellmouthR = get("bellmouth_radius_mm");
        ports = get("port_count");
    }

    // Hollow tube between radii r0..r1 over z0..z1 (annulus when r0 > 0).
    static float SdTube(Vector3 p, float r0, float r1, float z0, float z1) {
        float r = MathF.Sqrt(p.X * p.X + p.Y * p.Y);
        return MathF.Max(MathF.Abs(r - (r0 + r1) / 2) - (r1 - r0) / 2,
            MathF.Max(z0 - p.Z, p.Z - z1));
    }

    float SdTorusXY(Vector3 p, float ringR, float tubeR) {
        float q = MathF.Sqrt(p.X * p.X + p.Y * p.Y) - ringR;
        return MathF.Sqrt(q * q + p.Z * p.Z) - tubeR;
    }

    // Port axis: starts at (portBCR, 0, 0) on the flange front face, tilted
    // outward by portTilt about the tangential axis, extended by portLen.
    float SdPort(Vector3 p) {
        float c = MathF.Cos(portTilt), s = MathF.Sin(portTilt);
        // Local frame: origin at port root, axis along (c, 0, s).
        Vector3 q = p - new Vector3(portBCR, 0, 0);
        Vector3 l = new(q.X * c + q.Z * s, q.Y, -q.X * s + q.Z * c);
        float r = MathF.Sqrt(l.X * l.X + l.Y * l.Y);
        return MathF.Max(r - portR, MathF.Max(-l.Z, l.Z - portLen));
    }

    public float fSignedDistance(in Vector3 p) {
        // Inlet flange annulus, z in [-flangeT, 0]. The fan-housing inlet
        // plane is the z = 0 interface; the pilot enters the housing hub
        // bore toward +z and the duct runs to +z into the crankcase side.
        float body = SdTube(p, pilotBoreR, flangeR, -flangeT, 0);
        // Locating pilot: fits the housing hub bore (radius pilotR <= bore).
        body = MathF.Min(body, SdTube(p, pilotBoreR, pilotR, 0, pilotLen));
        // Inlet duct shell around the collector mouth.
        body = MathF.Min(body, SdTube(p, ductOutR - wall, ductOutR, 0, ductLen));
        // Bellmouth lip at the duct entry (ring at the mean duct-mouth radius).
        body = MathF.Min(body, SdTorusXY(p, (ductInR + ductOutR) / 2, bellmouthR));
        // Central suction bore (through pilot and flange).
        float bore = MathF.Max(MathF.Sqrt(p.X * p.X + p.Y * p.Y) - pilotBoreR,
            MathF.Abs(p.Z + flangeT / 2) - (flangeT / 2 + pilotLen + ductLen));
        body = MathF.Max(body, -bore);
        // Stub ports on the bolt circle, drilled through the flange annulus.
        for (int i = 0; i < (int)ports; i++) {
            float a = 2 * MathF.PI * i / ports;
            float cs = MathF.Cos(a), sn = MathF.Sin(a);
            Vector3 lp = new(p.X * cs + p.Y * sn, -p.X * sn + p.Y * cs, p.Z);
            body = MathF.Max(body, -SdPort(lp));
        }
        return body;
    }

    public void Check() {
        if (ports < 2 || ports > 12) throw new ArgumentException("Invalid port count");
        if (flangeT <= 0 || pilotLen <= 0 || ductLen <= 0 || ductOutR <= ductInR || wall <= 0
            || bellmouthR <= 0 || portR <= 0 || portLen <= 0)
            throw new ArgumentException("Invalid crankcase-interface parameters");
        if (pilotR <= pilotBoreR) throw new ArgumentException("Pilot must surround the central bore");
        if (ductOutR - ductInR < wall) throw new ArgumentException("Duct wall thinner than configured wall");
        if (bellmouthR > (ductOutR - ductInR) / 2) throw new ArgumentException("Bellmouth lip exceeds duct wall band");
        if (ductInR <= pilotR) throw new ArgumentException("Duct must sit outside the pilot");
        if (portBCR + portR >= flangeR) throw new ArgumentException("Port breaks the flange rim");
        if (portBCR - portR <= ductOutR) throw new ArgumentException("Port root overlaps the duct");
        // Witness probes: flange ring solid, pilot solid, duct wall solid,
        // bore and a port axis void.
        if (fSignedDistance(new Vector3((pilotR + flangeR) / 2, 0, -flangeT / 2)) <= 0)
            throw new Exception("Flange missing");
        if (fSignedDistance(new Vector3((pilotBoreR + pilotR) / 2, 0, pilotLen / 2)) <= 0)
            throw new Exception("Pilot missing");
        if (fSignedDistance(new Vector3((ductInR + ductOutR) / 2, 0, ductLen / 2)) <= 0)
            throw new Exception("Duct wall missing");
        if (fSignedDistance(new Vector3(0, 0, -flangeT / 2)) >= 0)
            throw new Exception("Central bore closed");
        var pp = new Vector3(portBCR + portLen * MathF.Cos(portTilt) / 2, 0,
            portLen * MathF.Sin(portTilt) / 2);
        if (fSignedDistance(pp) >= 0)
            throw new Exception("Port channel closed");
    }
}
