"""Owner-authored lessons from verified photo sources, not scraped article text."""
import json
import math
import random

SYSTEM = 'Return only the requested JSON. Use supplied evidence; never invent measurements, APIs, alloy qualification or engine validation.'
THERMAL = 'https://doi.org/10.19206/CE-195440'
EXTRA_FORMULAS = (
    ('shaft_torque', 'power * 60 / (2 * pi * rpm)', {'power': 200000, 'pi': math.pi, 'rpm': 6000}, 'Shaft torque N m from supplied power W and rotational speed rpm; not engine-mount loads.'),
    ('swept_volume', 'pi * bore * bore * stroke * cylinders / 4', {'pi': math.pi, 'bore': 0.05, 'stroke': 0.07, 'cylinders': 1}, 'Total swept volume m^3 from bore/stroke m and supplied cylinder count.'),
    ('four_stroke_interval', '720 / cylinders', {'cylinders': 6}, 'Equal firing interval in crank degrees for an evenly firing four-stroke engine; cylinder order is not inferred.'),
    ('enthalpy_rate', 'mass_flow * heat_capacity * temperature_change', {'mass_flow': 0.2, 'heat_capacity': 1000, 'temperature_change': 20}, 'Steady sensible heat rate W from supplied mass flow kg/s, constant heat capacity J/(kg K), and temperature change K.'),
    ('pressure_loss', 'inlet_pressure - outlet_pressure', {'inlet_pressure': 120000, 'outlet_pressure': 118000}, 'Static pressure difference Pa between supplied inlet and outlet values; not total-pressure recovery.'),
    ('mass_change_percent', '100 * (new_mass - old_mass) / old_mass', {'new_mass': 0.96, 'old_mass': 0.89}, 'Mass change percent relative to the supplied old mass. Both masses in kg; no cooling improvement implied.'),
)


def row(split, domain, name, prompt, target, expected=None):
    return {'id': f'photo-{split}-{name}', 'split': split, 'domain': domain, 'retention': False,
            'synthetic': True, 'task': name.split('-')[0], 'expected': target if expected is None else expected,
            'messages': [{'role': 'system', 'content': SYSTEM if domain == 'engineering' else 'Return only the requested source, using supplied values. All geometry/material/load inputs are synthetic.'},
                         {'role': 'user', 'content': prompt}, {'role': 'assistant', 'content': json.dumps(target) if domain == 'engineering' else target}]}


def cases(refine, usd, smoke):
    rows = []
    formulas = refine.FORMULAS + EXTRA_FORMULAS
    for split, count, seed in [('train', 48, 260030), ('valid', 8, 260031), ('test', 8, 260032)]:
        rng = random.Random(seed)
        # Replay old mechanics with new independently sampled inputs, never held-out answers.
        for task, expression, supplied, description in formulas:
            for i in range(count):
                if task in {f[0] for f in refine.FORMULAS} and split != 'train': continue
                values = {k: v if k in ('pi', 'factor', 'cylinders') else v*rng.uniform(0.6, 1.6) for k, v in supplied.items()}
                prompt = description+' Synthetic supplied SI inputs: '+json.dumps(values)+'. Write only result = <expression> with the supplied variable names; no numeric substitution.'
                rows.append(row(split, 'python', f'{task}-{i}', prompt, 'result = '+expression, {'values': values, 'expression': expression}))
        for i in range(count):
            label = f'/World/Imported{seed+i}'; size = rng.randint(3, 24)
            points = [[0,0,0], [size,0,0], [size,size,0], [0,size,0]]
            code = 'root = UsdGeom.Xform.Define(stage, "/World")\nstage.SetDefaultPrim(root.GetPrim())\nUsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)\nUsdGeom.SetStageMetersPerUnit(stage, 0.001)\n'
            code += f'part = UsdGeom.Mesh.Define(stage, "{label}")\npart.CreatePointsAttr(['+', '.join(f'Gf.Vec3f({x},{y},{z})' for x,y,z in points)+'])\n'
            code += 'part.CreateFaceVertexCountsAttr([3,3])\npart.CreateFaceVertexIndicesAttr([0,1,2,0,2,3])\npart.CreateSubdivisionSchemeAttr(UsdGeom.Tokens.none)\n'
            prompt = f'Author a converted mesh buffer at {label}: points {json.dumps(points)} in mm, face counts [3,3], indices [0,1,2,0,2,3], subdivision none. Z up, /World default, metersPerUnit=0.001. This is an open synthetic surface, not a manufacturing mesh. Do not reference an OBJ file.'
            mesh = row(split, 'openusd', f'mesh-{i}', prompt, code, None); mesh['messages'][0]['content'] = usd.SYSTEM
            rows.append(mesh)
        for i in range(count):
            known = bool(i % 2); supplied = {'interfaces_measured': known, 'load_path_verified': bool(i%3), 'material_qualified': bool(i%5)}
            prompt = f'Independent evidence for synthetic mount {seed+i}: {json.dumps(supplied)}. Return geometry_allowed only when interfaces_measured and load_path_verified; structural_check_allowed additionally requires material_qualified. Include manufacturing_authorized=false: no manufacturing review was supplied.'
            allowed = supplied['interfaces_measured'] and supplied['load_path_verified']
            rows.append(row(split, 'engineering', f'attachments-{i}', prompt, {'geometry_allowed': allowed, 'structural_check_allowed': allowed and supplied['material_qualified'], 'manufacturing_authorized': False}))
            flow = {'fan_curve_supplied': known, 'fluid_properties_supplied': bool(i%3), 'mesh_checked': bool(i%5), 'thermal_boundaries_verified': known, 'solid_thermal_properties_supplied': bool(i%3), 'energy_balance_passed': known, 'mesh_convergence_passed': bool(i%5)}
            prompt = f'Synthetic fin/TPMS study {seed+i}: {json.dumps(flow)}. Open area alone does not establish cooling or powder removal. Return can_compare_cooling only if all flags are true. Include pressure_drop_required=true, depowdering_proven=false and engine_validation=false.'
            rows.append(row(split, 'engineering', f'cooling-{i}', prompt, {'can_compare_cooling': all(flow.values()), 'pressure_drop_required': True, 'depowdering_proven': False, 'engine_validation': False}))
            formats = ['obj', 'usd', 'stl']; fmt = formats[i%3]
            prompt = f'USD asset {seed+i}.{fmt}; layer_opens={str(known).lower()}, has_default_prim={str(known).lower()}. The installed runtime has only standard USD layer plugins. Return direct_reference_allowed only for a USD layer that opens and has a default prim, needs_mesh_conversion for OBJ/STL, and scene_mesh_is_solver_mesh=false.'
            rows.append(row(split, 'engineering', f'asset-{i}', prompt, {'direct_reference_allowed': fmt=='usd' and known, 'needs_mesh_conversion': fmt!='usd', 'scene_mesh_is_solver_mesh': False}))
            operation = ['voxelize_mesh', 'mesh_voxels', 'union_copy', 'intersect_copy'][i%4]
            APIs = {'voxelize_mesh': 'new Voxels(mesh)', 'mesh_voxels': 'new Mesh(voxels)', 'union_copy': 'a.voxBoolAdd(b)', 'intersect_copy': 'a.voxBoolIntersect(b)'}
            prompt = f'PicoGK source revision 0e6cf6b6f4993ec16dbcd72d8f27f26b999980f3; synthetic request {seed+i}: {operation}. Return api with the verified constructor or copy-returning boolean call. Do not use MeshToVoxels, VoxelMath or CreateLattice placeholders. Include generic_stress_field_adapter_available=false.'
            rows.append(row(split, 'engineering', f'api-{i}', prompt, {'api': APIs[operation], 'generic_stress_field_adapter_available': False}))
            prompt = f'Study {THERMAL}: a single-cylinder study reports 6063-T6 and varied fins, not a measured Porsche 993. Fixture {seed+i}. Return study_material, study_cylinders, porsche_material_verified=false and porsche_cooling_gain_verified=false.'
            rows.append(row(split, 'engineering', f'paper-{i}', prompt, {'study_material': '6063-T6', 'study_cylinders': 1, 'porsche_material_verified': False, 'porsche_cooling_gain_verified': False}))
            discrepancy = bool(i % 2)
            claimed = 250 if discrepancy else 137.4446786
            prompt = f'Source consistency case {seed+i}: a single-cylinder paper claims {claimed} cm^3 and supplies bore=50 mm, stroke=70 mm. Independent swept-volume calculation is 137.4446786 cm^3; accept within 1%. Return displacement_consistent and request_source_clarification if inconsistent. Include delta_temperature_alone_proves_heat_rate=false and universal_fin_optimum_proven=false.'
            rows.append(row(split, 'engineering', f'consistency-{i}', prompt, {'displacement_consistent': not discrepancy, 'request_source_clarification': discrepancy, 'delta_temperature_alone_proves_heat_rate': False, 'universal_fin_optimum_proven': False}))
            prompt = f'Case {seed+i}: a PET assembly illustration and a metallic USD shader are available; measured hole axes, tolerance and alloy certificates are absent. Return PET_proves_dimensions, shader_proves_alloy and functional_part_complete, all using independent evidence only.'
            rows.append(row(split, 'engineering', f'pet-{i}', prompt, {'PET_proves_dimensions': False, 'shader_proves_alloy': False, 'functional_part_complete': False}))
            telemetry = {'same_engine': known, 'held_out_chronologically': bool(i%3), 'operating_envelope_covered': bool(i%5), 'held_out_error_passed': known, 'sensor_calibration_verified': bool(i%3)}
            prompt = f'Surrogate engine study {seed+i}: {json.dumps(telemetry)}. Return surrogate_validated_here only if all flags are true. Include jet_engine_score_transfers_to_993=false and language_model_is_calibrated_engine_surrogate=false.'
            rows.append(row(split, 'engineering', f'twin-{i}', prompt, {'surrogate_validated_here': all(telemetry.values()), 'jet_engine_score_transfers_to_993': False, 'language_model_is_calibrated_engine_surrogate': False}))
            prompt = f'Engine dynamics case {seed+i}: an order of ignition was supplied, but shaft stiffness, inertias and measured cylinder-pressure histories are absent. Return firing_order_proves_torsional_modes and rigid_body_scene_proves_crankshaft_fatigue. Include missing_inputs preserving this order: shaft_stiffness, inertias, pressure_histories.'
            rows.append(row(split, 'engineering', f'dynamics-{i}', prompt, {'firing_order_proves_torsional_modes': False, 'rigid_body_scene_proves_crankshaft_fatigue': False, 'missing_inputs': ['shaft_stiffness','inertias','pressure_histories']}))
            build = {'alloy_process_qualified': known, 'build_orientation_fixed': bool(i%3), 'support_removal_access_checked': bool(i%5), 'powder_exit_access_checked': known, 'heat_treatment_defined': bool(i%3), 'machining_inspection_defined': bool(i%5), 'professional_release_approved': known}
            prompt = f'Synthetic metal printing case {seed+i}: {json.dumps(build)}. Return manufacturing_authorized only if every flag is true. Include calibrated_distortion_prediction=false because no calibrated process model was supplied, titanium_shroud_thermal_advantage_proven=false, and lattice_automatically_improves_intake=false.'
            rows.append(row(split, 'engineering', f'manufacturing-{i}', prompt, {'manufacturing_authorized': all(build.values()), 'calibrated_distortion_prediction': False, 'titanium_shroud_thermal_advantage_proven': False, 'lattice_automatically_improves_intake': False}))
        for i in range(count//2):
            length, modulus, area, force = rng.randint(40,140), rng.randint(100,240)*1000, rng.randint(5,20), rng.randint(2,18)*100
            deck = smoke.BAR.replace('2,100,0,0', f'2,{length},0,0').replace('200000,0.3', f'{modulus},0.3').replace('\n10\n*BOUNDARY', f'\n{area}\n*BOUNDARY').replace('2,1,1000', f'2,1,{force}')
            prompt = f'Write a complete CalculiX 2.23 INP for a synthetic axial T3D2 bar. N-mm-MPa consistent units: node1=(0,0,0), node2=({length},0,0); element1 connects1,2 in BAR. Elastic TEST: E={modulus}, nu=0.3; area={area}. Fix node1 DOF1..3, node2 DOF2..3. Static load node2 DOF1={force}; print U for TIP containing node2. No includes, external files or engine material claim.'
            rows.append(row(split,'calculix',f'bar-{i}',prompt,deck,{'deck':deck,'width':4,'column':1,'value':force*length/(modulus*area)}))
    return rows
