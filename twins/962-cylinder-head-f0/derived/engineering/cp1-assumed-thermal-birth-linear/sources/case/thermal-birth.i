# HYPOTHETICAL thermal activation/energy software witness; not a head model.
[Problem]
  material_coverage_check = false
[]
[Mesh]
  [base]
    type = GeneratedMeshGenerator
    dim = 3
    xmax = 2
    ymax = 1
    zmax = 1
    nx = 16
    ny = 4
    nz = 4
    subdomain_ids = 1
  []
  [old]
    type = SubdomainBoundingBoxGenerator
    input = base
    block_id = 2
    bottom_left = '0 0 0'
    top_right = '1 1 1'
  []
[]
[Variables]
  [inactive_placeholder]
    block = 1
    initial_condition = 0
  []
  [temperature]
    block = 2
  []
[]
[ICs]
  [birth_temperature]
    type = FunctionIC
    variable = temperature
    function = 'if(t<0.1,400,350)'
    block = 2
  []
[]
[Functions]
  [cp_T]
    type = ParsedFunction
    expression = '900+0*(t-300)'
  []
  [k_T]
    type = ParsedFunction
    expression = '187+0*(t-300)'
  []
  [beam_x]
    type = ParsedFunction
    expression = '0.4+3*t'
  []
[]
[Kernels]
  [inactive_placeholder]
    type = ADTimeDerivative
    variable = inactive_placeholder
    block = 1
  []
  [storage]
    type = ADHeatConductionTimeDerivative
    variable = temperature
    block = 2
    use_displaced_mesh = false
  []
  [conduction]
    type = ADHeatConduction
    variable = temperature
    block = 2
    use_displaced_mesh = false
  []
  [source]
    type = ADMatHeatSource
    variable = temperature
    material_property = volumetric_heat
    block = 2
  []
[]
[Materials]
  [thermal]
    type = ADHeatConductionMaterial
    temperature = temperature
    thermal_conductivity_temperature_function = k_T
    specific_heat_temperature_function = cp_T
    block = 2
  []
  [density]
    type = ADGenericConstantMaterial
    prop_names = density
    prop_values = 2700
    block = 2
  []
  [source]
    type = FunctionPathEllipsoidHeatSource
    power = 80
    efficiency = 0.5
    factor = 0.5
    rx = 0.5
    ry = 0.8
    rz = 0.8
    function_x = beam_x
    function_y = 0.5
    function_z = 0.5
    block = 2
  []
[]
[MeshModifiers]
  [birth]
    type = TimedSubdomainModifier
    times = 0.2
    blocks_from = 1
    blocks_to = 2
    reinitialize_subdomains = 2
    reinitialize_variables = temperature
    reinitialization_strategy = IC
    restore_overridden_dofs = true
    execution_order_group = -100
    execute_on = TIMESTEP_BEGIN
  []
[]
[AuxVariables]
  [k_seen]
    family = MONOMIAL
    order = CONSTANT
    block = 2
  []
  [cp_seen]
    family = MONOMIAL
    order = CONSTANT
    block = 2
  []
  [q_seen]
    family = MONOMIAL
    order = CONSTANT
    block = 2
  []
[]
[AuxKernels]
  [k_seen]
    type = ADMaterialRealAux
    variable = k_seen
    property = thermal_conductivity
    block = 2
    execute_on = 'INITIAL TIMESTEP_END'
  []
  [cp_seen]
    type = ADMaterialRealAux
    variable = cp_seen
    property = specific_heat
    block = 2
    execute_on = 'INITIAL TIMESTEP_END'
  []
  [q_seen]
    type = ADMaterialRealAux
    variable = q_seen
    property = volumetric_heat
    block = 2
    execute_on = 'INITIAL TIMESTEP_END'
  []
[]
[VectorPostprocessors]
  [begin]
    type = NodalValueSampler
    variable = temperature
    sort_by = id
    block = 2
    execute_on = 'INITIAL TIMESTEP_BEGIN'
  []
  [end]
    type = NodalValueSampler
    variable = temperature
    sort_by = id
    block = 2
    execute_on = 'INITIAL TIMESTEP_END'
  []
  [properties]
    type = ElementValueSampler
    variable = 'k_seen cp_seen q_seen'
    sort_by = id
    block = 2
    execute_on = 'INITIAL TIMESTEP_END'
  []
[]
[Postprocessors]
  [source_power]
    type = ADElementIntegralMaterialProperty
    mat_prop = volumetric_heat
    block = 2
    execute_on = 'INITIAL TIMESTEP_END'
  []
[]
[Preconditioning]
  [full]
    type = SMP
    full = true
  []
[]
[Executioner]
  [Quadrature]
    type = GAUSS
    order = SECOND
  []
  type = Transient
  solve_type = LINEAR
  petsc_options_iname = '-ksp_type -pc_type'
  petsc_options_value = 'preonly lu'
  dt = 0.01
  end_time = 0.4
  nl_rel_tol = 1e-11
  nl_abs_tol = 1e-10
  nl_max_its = 30
[]
[Outputs]
  file_base = thermal
  [csv]
    type = CSV
    precision = 17
  []
  [console]
    type = Console
    output_postprocessors = false
  []
[]
