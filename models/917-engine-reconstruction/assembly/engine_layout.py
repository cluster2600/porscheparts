"""Explicit concept geometry; reuse the earlier engine layout and slider-crank."""
import importlib.util
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


F1 = module("engine_f1", ROOT / "twins/reference-917-engine/source/build_complete_engine_parts.py")
F3 = module("engine_f3", ROOT / "twins/reference-917-engine/source/build_detail_expansion_f3.py")
HYP = module("engine_hypotheses", HERE.parent / "hypothesis/run.py")
FIA = module("engine_fia_reference", HERE.parent / "fia/run.py")


def beam(a, b, radius, rounded=False):
    return {"kind": "beam", "a": list(a), "b": list(b), "r": radius, "round": rounded}


def box(center, half):
    return {"kind": "box", "center": list(center), "half": list(half)}


def tube(radius, inner, length, axis=2):
    a, b, ca, cb = [0]*3, [0]*3, [0]*3, [0]*3
    a[axis], b[axis] = -length/2, length/2
    ca[axis], cb[axis] = -length/2-5, length/2+5
    return [beam(a,b,radius)], [beam(ca,cb,inner)]


def transform(translation=(0,0,0), rotation=(0,0,0)):
    import numpy as np
    import trimesh
    matrix = trimesh.transformations.euler_matrix(*map(math.radians,rotation),axes="sxyz")
    matrix[:3,3] = translation
    return np.asarray(matrix)


def head_transform(x, bank, deck):
    import numpy as np
    matrix = np.eye(4)
    # Proper rotations keep both intake mouths above and exhaust mouths below.
    matrix[:3,:3] = [[-bank,0,0],[0,0,bank],[0,1,0]]
    matrix[:3,3] = [x,bank*deck,0]
    return matrix


def build(config, f1):
    d = FIA.validate_reference(config["core_assumptions"],
                               __import__("json").loads((HERE.parent/"fia/source-review.json").read_text()))
    if config["classification"] != "modern_4v_biturbo_hypothesis_assembly_not_historical_replica":
        raise ValueError("Explicit modern hypothesis classification required")
    if config["manufacturing_authorized"] is not False or config["engine_start_authorized"] is not False:
        raise ValueError("Physical release cannot be granted by geometry")
    if config["head_deck_mm"] != d["cylinder_base"]+d["cylinder_length"]:
        raise ValueError("Head/cylinder datum mismatch")
    p,g = d["regular_pitch"],d["central_pitch"]
    xs = [-g/2-2*p,-g/2-p,-g/2,g/2,g/2+p,g/2+2*p]
    parts, instances = {}, []

    def part(name, add, subtract=(), intersect=(), route="steel", level="geometric_hypothesis"):
        if name in parts:
            raise ValueError("Duplicate family: " + name)
        parts[name] = {"id":name,"add":list(add),"subtract":list(subtract),"intersect":list(intersect),
                       "material_route":route,"detail_level":level}

    def add(name, pos=(0,0,0), rot=(0,0,0), bank=None):
        instances.append({"family":name,"translation_mm":list(pos),"rotation_xyz_deg":list(rot),"bank":bank})

    def ring(name, radius, inner, length, route="steel", axis=2):
        a,b = tube(radius,inner,length,axis); part(name,a,b,route=route)

    # Bionic rule: webs branch from bearing stations to cylinder roots; no optimized-stress claim.
    bearing_x = [-375,-263.5,-145.5,-35,35,145.5,263.5,375]
    for bank in (-1,1):
        name = "crankcase_negative" if bank < 0 else "crankcase_positive"
        a,b = tube(94.125,84.125,770,axis=0)
        webs=[]
        for x in bearing_x:
            webs += [beam((x,0,0),(x,bank*74,48),7,True),
                  beam((x,bank*74,48),(x-18,bank*87,30),5,True),
                  beam((x,bank*74,48),(x+18,bank*87,30),5,True),
                  beam((x-6,0,0),(x+6,0,0),39)]
        for x in xs:
            x -= bank*d["bank_stagger"]/2
            a += [beam((x,bank*65,0),(x,bank*85,0),54.125)]
            b += [beam((x,0,0),(x,bank*110,0),d["bore"]/2+2)]
        part(name,a,b,[box((0,bank*110,0),(410,110,150))],route="light_structure",level="bionic_load_path_hypothesis")
        parts[name]["post_add"]=webs
        parts[name]["final_subtract"]=[beam((-400,0,0),(400,0,0),30.25)]
        add(name,bank=bank)
    crank = []
    ends = [-378.5,*[v for x in xs for v in (x-32,x+32)],378.5]
    for a,b in zip(ends[::2],ends[1::2]):
        crank.append(beam((a,0,0),(b,0,0),30.0))
    for x,phase in zip(xs,config["core_assumptions"]["crank_pair_phases_deg"]):
        y,z,_ = HYP.position(d,phase,1)
        crank.append(beam((x-29.25,y,z),(x+29.25,y,z),d["crankpin_diameter"]/2))
        for side in (-1,1):
            xx = x+side*32
            crank += [beam((xx-3.125,y/2,z/2),(xx+3.125,y/2,z/2),43.125)]
    part("crankshaft",crank); add("crankshaft")
    ring("main_bearing",32.125,30.125,18,"bearing",axis=0)
    for x in bearing_x: add("main_bearing",(x,0,0))
    # Reuse the four prior native generators, with a new explicit barrel hypothesis.
    for family,route in [("cylinder","light_structure"),("piston","piston"),("rod","rod"),("pin","steel")]:
        parts[family] = {"id":family,"import_core":True,"material_route":route,"detail_level":"parametric_hypothesis"}
    grooved={"id":"piston","source_core":"piston","add":[],"subtract":[],"intersect":[],
             "material_route":"piston","detail_level":"hypothetical_ring_grooves_on_preserved_core"}
    for y in (31,35,39):
        grooved["subtract"].append({"kind":"annular_beam","a":[0,y-.95,0],"b":[0,y+.95,0],
                                   "r":46,"inner":40.05,"round":False})
    parts["piston"]=grooved
    for bank in (-1,1):
        for x,phase in zip(xs,config["core_assumptions"]["crank_pair_phases_deg"]):
            xx=x-bank*d["bank_stagger"]/2
            y,z,wrist=HYP.position(d,phase,bank)
            add("cylinder",(xx,bank*d["cylinder_base"],0),(0,0,180 if bank<0 else 0),bank)
            add("piston",(xx,wrist,0),(0,0,180 if bank<0 else 0),bank)
            add("pin",(xx,wrist,0),bank=bank)
            angle=math.degrees(math.atan2(-z,wrist-y))
            add("rod",(xx,y,z),(angle,0,0),bank)

    ring("piston_ring",(d["bore"]-.1)/2,(d["bore"]-.1)/2-2,1.5,axis=1)
    ring("rod_bearing",28.125,26.125,17.0,"bearing",axis=0)
    ring("pin_clip",11.5,10.0,1.25,axis=0)
    # Purchased valve hardware stays geometrical envelopes: no fake spring or fastener rating.
    ring("valve_stem_seal",6,3.6,8,"seal")
    ring("lower_spring_seat",15.5,7.7,2)
    ring("upper_spring_retainer",14,3.65,5)
    ring("valve_keeper_pair",5.0,3.6,5)
    part("valve_shim",[beam((0,0,-1.25),(0,0,1.25),6)])
    ring("head_gasket",56.5,45.5,1.25,"seal")
    for name,r,length in [("head_stud",5,190),("location_dowel",4,16),("rocker_shaft",6,90),
                          ("case_bolt",4,205),("rod_bolt",3.5,42)]:
        part(name,[beam((0,0,-length/2),(0,0,length/2),r)],level="unthreaded_hardware_envelope")
    ring("head_nut",8,5.2,8)
    # Closed individual wire springs; no combined disconnected dual-spring STL.
    for name,radius,wire,turns in [("outer_valve_spring",12.5,2.25,5),("inner_valve_spring",8.5,1.5,6)]:
        points=[(radius*math.cos(i*math.tau/48),radius*math.sin(i*math.tau/48),45*i/(turns*48)) for i in range(turns*48+1)]
        part(name,[beam(a,b,wire,True) for a,b in zip(points,points[1:])],route="spring")
    part("rocker",[beam((-22,0,0),(22,0,0),7,True),beam((0,-7,0),(0,7,0),10)],
         [beam((0,-15,0),(0,15,0),6.2)])
    a=[box((0,0,0),(54.125,54.125,6.125))]
    b=[box((0,0,0),(46.125,46.125,11.125))]
    a += [beam((-50,-50,6),(0,0,26),5.125,True),beam((50,50,6),(0,0,26),5.125,True),
          beam((-50,50,6),(0,0,26),5.125,True),beam((50,-50,6),(0,0,26),5.125,True)]
    part("rocker_carrier",a,b,route="light_structure",level="bionic_load_path_hypothesis")
    part("valve_cover",[box((0,0,0),(56,58,10))],[box((0,0,-5),(52,54,11))],route="light_structure")
    for bank in (-1,1):
        for x,phase in zip(xs,config["core_assumptions"]["crank_pair_phases_deg"]):
            xx=x-bank*d["bank_stagger"]/2; y,z,wrist=HYP.position(d,phase,bank)
            for offset in (31,35,39): add("piston_ring",(xx,wrist+bank*offset,0),bank=bank)
            add("rod_bearing",(xx,y,z),bank=bank)
            for side in (-1,1):
                add("pin_clip",(xx+side*28,wrist,0),bank=bank)
                add("rod_bolt",(xx,y+side*31,z),(0,90,0),bank)
            add("head_gasket",(xx,bank*config["head_deck_mm"],0),(90,0,0),bank)
            # Four hardware stacks; actual inherited valves/guides/seats retain their own axes.
            for a in (-22.5,22.5):
                for b in (-22.5,22.5):
                    for family,height in [("valve_stem_seal",58),("lower_spring_seat",62),
                        ("outer_valve_spring",64),("inner_valve_spring",64),("upper_spring_retainer",109),
                        ("valve_keeper_pair",109),("valve_shim",116),("rocker",120)]:
                        add(family,(xx+a,bank*(config["head_deck_mm"]+height),-bank*b),(90 if bank<0 else -90,0,0),bank)
            for a in (-43,43):
                for b in (-43,43):
                    add("head_stud",(xx+a,bank*205,b),(90,0,0),bank)
                    add("head_nut",(xx+a,bank*303,b),(90,0,0),bank)
            for a in (-36,36):
                add("location_dowel",(xx+a,bank*208,0),(90,0,0),bank)
                add("rocker_shaft",(xx,bank*330,a),(0,90,0),bank)
            add("rocker_carrier",(xx,bank*294,0),(90,0,0),bank)
            add("valve_cover",(xx,bank*353,0),(90,0,0),bank)

    cam = [beam((-375,0,0),(375,0,0),13)]
    for x in xs:
        for dx in (-22.5,22.5): cam.append(beam((x+dx-5,4,0),(x+dx+5,4,0),19))
    part("camshaft",cam,level="lobes_without_timing_law")
    for bank in (-1,1):
        for z in (-25,25): add("camshaft",(0,bank*340,z),bank=bank)
    for name,r,inner,length,axis in [("cam_drive_gear",34,10,14,0),("central_output_gear",72,30.3,24,0),
                ("flywheel",105,18.3,22,0),("output_shaft",18,5,260,0),
                ("cooling_blower_drive_shaft",10,3,180,2),("cam_drive_intermediate_shaft",12,4,220,0),
                ("cooling_blower_bevel_gear",36,10.2,24,2)]:
        ring(name,r,inner,length,axis=axis)
        parts[name]["detail_level"]="shaft_or_gear_blank_no_tooth_contact_definition"
    # Preserve documented auxiliary positions, but no older core/head/turbo substitutes.
    common={"cam_drive_gear","central_output_gear","output_shaft","cooling_blower_drive_shaft",
            "cam_drive_intermediate_shaft","cooling_blower_bevel_gear"}
    for item in F1.placements(f1)+F3.placements():
        if item["family"] in common:
            # New shaft/gear blanks have their final axis already in the recipe.
            add(item["family"],item["translation_mm"])
    add("flywheel",(410,0,-140))
    for x in (-350,-250,-150,-50,50,150,250,350):
        for z in (-70,70): add("case_bolt",(x,0,z),(90,0,0))

    # Service systems: purchased devices and custom hollow housings are explicitly distinguished.
    for name,half,route in [("alternator",(42,42,45),"purchase"),("starter_motor",(35,35,80),"purchase"),
            ("ecu",(80,50,15),"purchase"),("oil_cooler",(150,24,50),"purchase"),
            ("intercooler",(110,60,40),"purchase"),("throttle",(24,24,18),"purchase")]:
        part(name,[box((0,0,0),half)],route=route,level="purchased_envelope")
    for name,r,length in [("injector",5,48),("spark_plug",5,55),("ignition_coil",12,45),("oil_filter",38,105),
            ("oil_thermostat",32,55),("pressure_sensor",8,22),("temperature_sensor",6,20)]:
        part(name,[beam((0,0,-length/2),(0,0,length/2),r)],route="purchase",level="purchased_envelope")
    add("alternator",(0,0,305)); add("starter_motor",(420,-110,-90),(0,90,0)); add("ecu",(390,0,210))
    add("oil_cooler",(-490,0,-75)); add("oil_filter",(-450,-130,-90)); add("oil_thermostat",(-425,140,-90))
    for bank in (-1,1):
        add("intercooler",(150,bank*270,180),bank=bank)
        add("throttle",(340,bank*200,195),(0,90,0),bank)
        add("pressure_sensor",(70,bank*165,135),bank=bank)
        add("temperature_sensor",(200,bank*165,135),bank=bank)
        for x in xs:
            xx=x-bank*d["bank_stagger"]/2
            add("injector",(xx,bank*235,75),(0,0,0),bank)
            for a in (-12,12):
                add("spark_plug",(xx+a,bank*260,0),(90,0,0),bank)
                add("ignition_coil",(xx+a,bank*310,80),bank=bank)
    # Seven pumps each have a body, cover, two gear blanks and shaft.
    part("oil_pump_body",[box((0,0,0),(37,25,18))],[box((0,0,7),(30,18,18))],route="light_structure")
    part("oil_pump_cover",[box((0,0,0),(37,25,3))],route="light_structure")
    part("oil_pump_gear",[beam((0,0,-7),(0,0,7),14.5)],level="gear_blank_no_tooth_definition")
    part("oil_pump_shaft",[beam((0,0,-25),(0,0,25),5)])
    for i in range(7):
        pos=(-330+i*100,0,-125)
        add("oil_pump_body",pos); add("oil_pump_cover",(pos[0],0,-102))
        for x in (-15,15): add("oil_pump_gear",(pos[0]+x,0,-120))
        add("oil_pump_shaft",(pos[0]-15,0,-125))
    part("sump_cover",[box((0,0,0),(390,82,6))],route="light_structure");add("sump_cover",(0,0,-155))
    a,b=tube(70,64,280);part("oil_tank",a,b,route="light_structure");add("oil_tank",(-550,0,110))
    ring("fuel_rail",10,5,700,"light_structure",axis=0)
    ring("oil_gallery_rail",10,5,700,"light_structure",axis=0)
    ring("oil_hose",9,5,150,"purchase")
    ring("turbo_oil_feed",6,3,120,"purchase")
    ring("turbo_oil_drain",10,7,180,"purchase")
    for bank in (-1,1):
        add("fuel_rail",(0,bank*220,100),bank=bank)
        add("oil_gallery_rail",(0,bank*72,75),bank=bank)
        for x in xs: add("oil_hose",(x,bank*90,-10),bank=bank)
        add("turbo_oil_feed",(480,bank*330,-60),bank=bank)
        add("turbo_oil_drain",(455,bank*330,-260),bank=bank)
    blower=[beam((0,0,-14),(0,0,14),24)]
    for i in range(12):
        a=i*math.tau/12
        blower.append(beam((20*math.cos(a),20*math.sin(a),0),(100*math.cos(a+.15),100*math.sin(a+.15),0),5,True))
    part("cooling_blower",blower,route="light_structure",level="blade_design_hypothesis");add("cooling_blower",(0,0,190))
    ring("blower_shroud",118.125,109.125,38,"light_structure");add("blower_shroud",(0,0,190))
    # One joined bifurcating duct per bank; six branches. All mouths/radii are interface hypotheses.
    for bank in (-1,1):
        for domain,route,z,outer,inner in [("exhaust","hot",-85,22,18),("intake","light_structure",100,24,20)]:
            name=domain+("_negative" if bank<0 else "_positive")
            a=[];b=[]
            nodes=[(x-bank*d["bank_stagger"]/2,bank*280,z) for x in xs]
            trunk=[(-360,bank*370,z),(0,bank*370,z),(380,bank*370,z)]
            paths=[trunk]+[[node,(node[0],bank*330,z), (node[0],bank*370,z)] for node in nodes]
            terminal=(400.25,bank*386.25,-160-bank*43) if domain=="exhaust" else (500,bank*372.25,-160-bank*49)
            paths += [[trunk[-1],(terminal[0],terminal[1],z),terminal]]
            for path in paths:
                for start,end in zip(path,path[1:]):
                    # A flat turbo mouth avoids isolated voxel slivers at a perforated spherical cap.
                    a.append(beam(start,end,outer,end!=terminal));b.append(beam(start,end,inner,True))
            # Open all six head mouths and the turbo mouth; otherwise the rounded paths trap a closed void.
            for node in nodes:
                b.append(beam(node,(node[0],node[1]-bank*50,node[2]),inner,True))
            end=paths[-1][-1];previous=paths[-1][-2]
            length=math.dist(end,previous)
            extension=tuple(end[i]+50*(end[i]-previous[i])/length for i in range(3))
            b.append(beam(end,extension,inner,True))
            part(name,a,b,route=route,level="bionic_branched_open_duct_hypothesis");add(name,bank=bank)
    ring("exhaust_outlet",25,21,200,"hot",axis=0)
    for bank in (-1,1):add("exhaust_outlet",(260,bank*330,-160),bank=bank)
    return {"classification":"hypothetical_engine_components_not_manufacturing_geometry",
            "parts":[item for item in parts.values() if "import_core" not in item]}, parts, instances, xs
