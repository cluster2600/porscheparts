#!/usr/bin/env python3
"""Deterministic merge of the three F1 oil-circuit topology guides into one
renderable line-and-fitting USD harness for the Omniverse assembly.

Inputs (read-only F1 topology contracts, non-spatial diagram coordinates):
  - twins/catalogue-parts/engineering/993-turbo-lubrication-control-topology-f1.usda
  - twins/catalogue-parts/engineering/993-oil-cooler-circuit-topology-f1.usda
  - twins/catalogue-parts/engineering/993-oil-tank-circuit-topology-f1.usda

Layout: each circuit diagram is placed in its own z-band; shared semantic
boundaries are cross-linked with explicit 'unknown_link' tubes. Radii come
from the two placeholder config constants below; they are tagged
'placeholder' and are NOT measurements.
"""
import hashlib
from pxr import Gf, Sdf, Usd, UsdGeom, Vt

INPUTS = [
    ("TurboLubricationControl",
     "twins/catalogue-parts/engineering/993-turbo-lubrication-control-topology-f1.usda",
     0.0),
    ("OilCoolerCircuit",
     "twins/catalogue-parts/engineering/993-oil-cooler-circuit-topology-f1.usda",
     10.0),
    ("OilTankCircuit",
     "twins/catalogue-parts/engineering/993-oil-tank-circuit-topology-f1.usda",
     20.0),
]
OUT = "twins/catalogue-parts/engineering/993-oil-circuit-topology-harness-f1.usda"

# Single placeholder radius configuration (tagged 'placeholder', not measured).
PLACEHOLDER_RADIUS_M = 0.080        # node marker sphere radius
PLACEHOLDER_TUBE_RADIUS_M = 0.0125  # edge tube radius

NODE_COLOR = Gf.Vec3f(0.85, 0.55, 0.20)
EDGE_COLOR_BY_KIND = {
    "oil":     Gf.Vec3f(0.75, 0.35, 0.10),
    "air":     Gf.Vec3f(0.35, 0.55, 0.80),
    "control": Gf.Vec3f(0.45, 0.75, 0.40),
    "other":   Gf.Vec3f(0.70, 0.70, 0.70),
}

# Cross-circuit semantic links: state = unknown (no measured routing yet).
CROSS_LINKS = [
    ("TurboLubricationControl", "OilReturnBoundary", "OilTankCircuit",
     "TurboLubricationReturnBoundary",
     "unknown_link_turbo_return_to_tank_return_hypothesis"),
    ("OilCoolerCircuit", "UpstreamOilBoundary", "TurboLubricationControl",
     "OilSourceBoundary",
     "unknown_link_cooler_upstream_to_turbo_supply_hypothesis"),
    ("OilCoolerCircuit", "DownstreamOilBoundary", "OilTankCircuit",
     "EnginePressureSupplyBoundary",
     "unknown_link_cooler_downstream_to_engine_supply_hypothesis"),
    ("TurboLubricationControl", "VentBoundary", "OilTankCircuit",
     "VentSystemBoundary",
     "unknown_link_vent_boundary_to_vent_system_hypothesis"),
    ("OilCoolerCircuit", "AmbientThermalBoundary", "OilTankCircuit",
     "AmbientThermalBoundary",
     "unknown_link_shared_ambient_thermal_hypothesis"),
]


def edge_kind(sem):
    s = str(sem).lower()
    if "oil" in s:
        return "oil"
    if "air" in s or "vent" in s or "breather" in s:
        return "air"
    if "control" in s or "signal" in s or "power" in s or "actuation" in s:
        return "control"
    return "other"


def set_custom_string(prim, name, value):
    attr = prim.CreateAttribute(name, Sdf.ValueTypeNames.String, custom=True)
    attr.Set(value)


def add_circuit(stage, root, circuit_name, src_path, z_offset, src_hashes):
    with open(src_path, "rb") as fh:
        raw = fh.read()
    src_hashes[circuit_name] = hashlib.sha256(raw).hexdigest()
    src = Usd.Stage.Open(src_path)

    guide = next(p for p in src.TraverseAll()
                 if p.GetPath().name == "TopologyGuide")

    circ = stage.DefinePrim(f"{root.GetPath()}/{circuit_name}", "Scope")
    set_custom_string(circ, "circuit", circuit_name)
    set_custom_string(circ, "sourceFile", src_path)
    set_custom_string(circ, "sourceSha256", src_hashes[circuit_name])
    set_custom_string(circ, "coordinateSemantics",
                      "diagram_units_not_vehicle_coordinates")

    nodes = stage.DefinePrim(f"{circ.GetPath()}/Nodes", "Scope")
    edges = stage.DefinePrim(f"{circ.GetPath()}/Edges", "Scope")

    node_positions = {}
    for p in guide.GetAllChildren():
        sem = p.GetAttribute("topologySemantics").Get() \
            if p.HasAttribute("topologySemantics") else ""
        if p.IsA(UsdGeom.Sphere):
            tr = p.GetAttribute("xformOp:translate").Get()
            pos = Gf.Vec3d(tr[0], tr[1], z_offset)
            node_positions[p.GetName()] = pos
            sphere = UsdGeom.Sphere.Define(stage,
                                           f"{nodes.GetPath()}/{p.GetName()}")
            sphere.CreateRadiusAttr(PLACEHOLDER_RADIUS_M)
            sphere.AddTranslateOp().Set(pos)
            set_custom_string(sphere.GetPrim(), "topologySemantics", str(sem))
            set_custom_string(sphere.GetPrim(), "geometryState",
                              "placeholder_not_measurement")
            sphere.GetPrim().CreateAttribute(
                "displayColor", Sdf.ValueTypeNames.Color3fArray) \
                .Set(Vt.Vec3fArray([NODE_COLOR]))
        elif p.IsA(UsdGeom.BasisCurves):
            pts = p.GetAttribute("points").Get()
            path = f"{edges.GetPath()}/{p.GetName()}"
            tube = stage.DefinePrim(path, "Mesh")
            verts = [Gf.Vec3f(pt[0], pt[1], z_offset) for pt in pts]
            tube.CreateAttribute("points", Sdf.ValueTypeNames.Point3fArray) \
                .Set(Vt.Vec3fArray(verts))
            # tube radius encoded as custom scalar; consumers must treat it
            # as the single placeholder config value.
            rattr = tube.CreateAttribute("placeholderRadiusM",
                                         Sdf.ValueTypeNames.Double,
                                         custom=True)
            rattr.Set(PLACEHOLDER_TUBE_RADIUS_M)
            kind = edge_kind(sem)
            set_custom_string(tube, "topologySemantics", str(sem))
            set_custom_string(tube, "geometryState",
                              "placeholder_not_measurement")
            tube.CreateAttribute(
                "displayColor", Sdf.ValueTypeNames.Color3fArray) \
                .Set(Vt.Vec3fArray([EDGE_COLOR_BY_KIND[kind]]))
    return node_positions


def main():
    stage = Usd.Stage.CreateNew(OUT)
    layer = stage.GetRootLayer()
    layer.comment = ("M64-Z-OL F1 oil-circuit topology harness: placeholder "
                     "line-and-fitting guide merged from three F1 topology "
                     "USDA contracts. Radii are placeholder config values, "
                     "not measurements. Coordinates are diagram bands, not "
                     "vehicle positions.")
    root = stage.DefinePrim("/OilCircuitTopologyHarnessF1", "Xform")
    set_custom_string(root, "status",
                      "F1_placeholder_line_and_fitting_harness_"
                      "not_part_geometry_or_SimReady")
    set_custom_string(root, "radiusTag",
                      "placeholder_single_config_value_not_measurement")
    root.CreateAttribute("placeholderRadiusM", Sdf.ValueTypeNames.Double,
                         custom=True).Set(PLACEHOLDER_RADIUS_M)
    root.CreateAttribute("placeholderTubeRadiusM", Sdf.ValueTypeNames.Double,
                         custom=True).Set(PLACEHOLDER_TUBE_RADIUS_M)
    set_custom_string(root, "coordinateSemantics",
                      "diagram_bands_not_vehicle_coordinates")

    src_hashes = {}
    positions = {}
    for circuit_name, src_path, z in INPUTS:
        positions[circuit_name] = add_circuit(stage, root, circuit_name,
                                              src_path, z, src_hashes)

    root.CreateAttribute("sourceSha256ByCircuit",
                         Sdf.ValueTypeNames.StringArray, custom=True) \
        .Set(Vt.StringArray(
            [f"{name}={digest}"
             for name, digest in sorted(src_hashes.items())]))

    xlinks = stage.DefinePrim(f"{root.GetPath()}/UnknownCrossLinks", "Scope")
    for i, (ca, na, cb, nb, sem) in enumerate(CROSS_LINKS, 1):
        pa = positions[ca][na]
        pb = positions[cb][nb]
        tube = stage.DefinePrim(f"{xlinks.GetPath()}/UnknownLink{i:02d}",
                                "Mesh")
        tube.CreateAttribute("points", Sdf.ValueTypeNames.Point3fArray).Set(
            Vt.Vec3fArray([Gf.Vec3f(*pa), Gf.Vec3f(*pb)]))
        tube.CreateAttribute("placeholderRadiusM", Sdf.ValueTypeNames.Double,
                             custom=True).Set(PLACEHOLDER_TUBE_RADIUS_M)
        set_custom_string(tube, "topologySemantics", sem)
        set_custom_string(tube, "linkState", "unknown")
        set_custom_string(tube, "geometryState", "placeholder_not_measurement")
        tube.CreateAttribute("displayColor", Sdf.ValueTypeNames.Color3fArray) \
            .Set(Vt.Vec3fArray([Gf.Vec3f(0.90, 0.20, 0.20)]))

    stage.SetDefaultPrim(root)
    layer.Save()
    print("wrote", OUT)


if __name__ == "__main__":
    main()
