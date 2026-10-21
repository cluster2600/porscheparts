# Hypothetical mechanical birth/history/support release; mm, MPa, N, K.
[Problem]
  material_coverage_check = false
[]
[GlobalParams]
  displacements = 'disp_x disp_y disp_z'
[]
[Mesh]
  [base]
    type = GeneratedMeshGenerator
    dim = 3
    xmax = 1
    ymax = 1
    zmax = 20
    nx = 1
    ny = 1
    nz = 4
    subdomain_ids = 1
  []
  [old]
    type = SubdomainBoundingBoxGenerator
    input = base
    block_id = 2
    bottom_left = '0 0 0'
    top_right = '1 1 10'
  []
  [origin]
    type = BoundingBoxNodeSetGenerator
    input = old
    new_boundary = origin
    bottom_left = '-1e-8 -1e-8 -1e-8'
    top_right = '1e-8 1e-8 1e-8'
  []
  [rotation]
    type = BoundingBoxNodeSetGenerator
    input = origin
    new_boundary = rotation
    bottom_left = '.99999999 -1e-8 -1e-8'
    top_right = '1.00000001 1e-8 1e-8'
  []
  [axial_start]
    type = BoundingBoxNodeSetGenerator
    input = rotation
    new_boundary = axial_start
    bottom_left = '-1e-8 -1e-8 -1e-8'
    top_right = '1.00000001 1.00000001 1e-8'
  []
  [internal]
    type = BoundingBoxNodeSetGenerator
    input = axial_start
    new_boundary = internal
    bottom_left = '-1e-8 -1e-8 9.99999999'
    top_right = '1.00000001 1.00000001 10.00000001'
  []
  [axial_end]
    type = BoundingBoxNodeSetGenerator
    input = internal
    new_boundary = axial_end
    bottom_left = '-1e-8 -1e-8 19.99999999'
    top_right = '1.00000001 1.00000001 20.00000001'
  []
[]
[Variables/inactive_placeholder]
  block = 1
  initial_condition = 0
[]
[Kernels/inactive_placeholder]
  displacements = ''
  type = ADTimeDerivative
  variable = inactive_placeholder
  block = 1
[]
[Physics/SolidMechanics/QuasiStatic/bar]
  block = 2
  strain = SMALL
  incremental = true
  use_automatic_differentiation = true
  add_variables = true
  eigenstrain_names = thermal_eigenstrain
  save_in = 'rx ry rz'
[]
[ICs]
  [disp_x]
    type = FunctionIC
    variable = disp_x
    function = 'if(t<2.5,0,-.001*x)'
    block = 2
  []
  [disp_y]
    type = FunctionIC
    variable = disp_y
    function = 'if(t<2.5,0,-.001*y)'
    block = 2
  []
  [disp_z]
    type = FunctionIC
    variable = disp_z
    function = 'if(t<2.5,0,.0025*z)'
    block = 2
  []
[]
[Functions]
  [axial_history]
    type = PiecewiseLinear
    x = '0 1 2 6'
    y = '0 .03 .025 .025'
  []
  [temperature]
    type = ParsedFunction
    expression = 'if(t<4,300,260)'
  []
[]
[BCs]
  [origin_x]
    type = ADDirichletBC
    variable = disp_x
    boundary = origin
    value = 0
  []
  [origin_y]
    type = ADDirichletBC
    variable = disp_y
    boundary = origin
    value = 0
  []
  [rotation_y]
    type = ADDirichletBC
    variable = disp_y
    boundary = rotation
    value = 0
  []
  [axial_base]
    type = ADDirichletBC
    variable = disp_z
    boundary = axial_start
    value = 0
  []
  [internal]
    type = ADFunctionDirichletBC
    variable = disp_z
    boundary = internal
    function = axial_history
  []
  [top]
    type = ADDirichletBC
    variable = disp_z
    boundary = axial_end
    value = .05
    enable = false
  []
[]
[Controls]
  [internal]
    type = TimePeriod
    enable_objects = 'BCs/internal'
    start_time = 0
    end_time = 3
    execute_on = 'INITIAL TIMESTEP_BEGIN'
  []
  [top]
    type = TimePeriod
    enable_objects = 'BCs/top'
    start_time = 3
    end_time = 5
    execute_on = 'INITIAL TIMESTEP_BEGIN'
  []
[]
[MeshModifiers/birth]
  type = TimedSubdomainModifier
  times = 3
  blocks_from = 1
  blocks_to = 2
  reinitialize_subdomains = 2
  reinitialize_variables = 'disp_x disp_y disp_z'
  reinitialization_strategy = IC
  restore_overridden_dofs = true
  execution_order_group = -100
  execute_on = TIMESTEP_BEGIN
[]
[Materials]
  [elasticity]
    type = ADComputeIsotropicElasticityTensor
    youngs_modulus = 1000
    poissons_ratio = 0
    block = 2
  []
  [thermal]
    type = ADComputeThermalExpansionEigenstrain
    thermal_expansion_coeff = 1e-5
    stress_free_temperature = 300
    temperature = temperature
    eigenstrain_name = thermal_eigenstrain
    block = 2
  []
  [stress]
    type = ADComputeMultipleInelasticStress
    inelastic_models = plasticity
    perform_finite_strain_rotations = false
    block = 2
  []
  [plasticity]
    type = ADIsotropicPlasticityStressUpdate
    yield_stress = 1
    hardening_constant = 0
    relative_tolerance = 1e-11
    absolute_tolerance = 1e-11
    block = 2
  []
[]
[AuxVariables]
  [temperature]
    initial_condition = 300
    block = 2
  []
  [rx]
    block = 2
  []
  [ry]
    block = 2
  []
  [rz]
    block = 2
  []
[]
[AuxKernels]
  [temperature]
    type = FunctionAux
    variable = temperature
    function = temperature
    execute_on = 'INITIAL TIMESTEP_BEGIN'
  []
[]
[VectorPostprocessors]
  [begin]
    type = NodalValueSampler
    variable = 'disp_x disp_y disp_z temperature'
    block = 2
    sort_by = id
    execution_order_group = 100
    execute_on = 'INITIAL TIMESTEP_BEGIN'
  []
  [end]
    type = NodalValueSampler
    variable = 'disp_x disp_y disp_z temperature rx ry rz'
    block = 2
    sort_by = id
    execute_on = 'INITIAL TIMESTEP_END'
  []
  [fields]
    type = ElementMaterialSampler
    property = 'stress_xx stress_yy stress_zz stress_xy stress_xz stress_yz plastic_strain_xx plastic_strain_yy plastic_strain_zz plastic_strain_xy plastic_strain_xz plastic_strain_yz mechanical_strain_xx mechanical_strain_yy mechanical_strain_zz mechanical_strain_xy mechanical_strain_xz mechanical_strain_yz total_strain_xx total_strain_yy total_strain_zz total_strain_xy total_strain_xz total_strain_yz'
    block = 2
    execute_on = 'INITIAL TIMESTEP_END'
  []
[]
[Postprocessors/temperature_max]
  type = NodalExtremeValue
  variable = temperature
  block = 2
  value_type = max
  execute_on = 'INITIAL TIMESTEP_END'
[]
[Preconditioning/full]
  type = SMP
  full = true
[]
[Executioner]
  [Quadrature]
    type = GAUSS
    order = SECOND
  []
  type = Transient
  solve_type = NEWTON
  petsc_options_iname = '-ksp_type -pc_type'
  petsc_options_value = 'preonly lu'
  line_search = none
  dt = 1
  end_time = 6
  nl_rel_tol = 1e-11
  nl_abs_tol = 1e-10
  nl_max_its = 30
[]
[Outputs]
  file_base = mechanical
  csv = true
  exodus = true
  [console]
    type = Console
    output_postprocessors = false
  []
[]
[Materials/audit_tensors]
  type = RankTwoTensorMaterialADConverter
  ad_props_in = 'stress plastic_strain mechanical_strain total_strain'
  reg_props_out = 'audit_stress audit_plastic_strain audit_mechanical_strain audit_total_strain'
  block = 2
[]
[Materials/audit_stress_xx]
  type = RankTwoCartesianComponent
  rank_two_tensor = audit_stress
  property_name = stress_xx
  index_i = 0
  index_j = 0
  block = 2
[]
[Materials/audit_stress_yy]
  type = RankTwoCartesianComponent
  rank_two_tensor = audit_stress
  property_name = stress_yy
  index_i = 1
  index_j = 1
  block = 2
[]
[Materials/audit_stress_zz]
  type = RankTwoCartesianComponent
  rank_two_tensor = audit_stress
  property_name = stress_zz
  index_i = 2
  index_j = 2
  block = 2
[]
[Materials/audit_stress_xy]
  type = RankTwoCartesianComponent
  rank_two_tensor = audit_stress
  property_name = stress_xy
  index_i = 0
  index_j = 1
  block = 2
[]
[Materials/audit_stress_xz]
  type = RankTwoCartesianComponent
  rank_two_tensor = audit_stress
  property_name = stress_xz
  index_i = 0
  index_j = 2
  block = 2
[]
[Materials/audit_stress_yz]
  type = RankTwoCartesianComponent
  rank_two_tensor = audit_stress
  property_name = stress_yz
  index_i = 1
  index_j = 2
  block = 2
[]
[Materials/audit_plastic_strain_xx]
  type = RankTwoCartesianComponent
  rank_two_tensor = audit_plastic_strain
  property_name = plastic_strain_xx
  index_i = 0
  index_j = 0
  block = 2
[]
[Materials/audit_plastic_strain_yy]
  type = RankTwoCartesianComponent
  rank_two_tensor = audit_plastic_strain
  property_name = plastic_strain_yy
  index_i = 1
  index_j = 1
  block = 2
[]
[Materials/audit_plastic_strain_zz]
  type = RankTwoCartesianComponent
  rank_two_tensor = audit_plastic_strain
  property_name = plastic_strain_zz
  index_i = 2
  index_j = 2
  block = 2
[]
[Materials/audit_plastic_strain_xy]
  type = RankTwoCartesianComponent
  rank_two_tensor = audit_plastic_strain
  property_name = plastic_strain_xy
  index_i = 0
  index_j = 1
  block = 2
[]
[Materials/audit_plastic_strain_xz]
  type = RankTwoCartesianComponent
  rank_two_tensor = audit_plastic_strain
  property_name = plastic_strain_xz
  index_i = 0
  index_j = 2
  block = 2
[]
[Materials/audit_plastic_strain_yz]
  type = RankTwoCartesianComponent
  rank_two_tensor = audit_plastic_strain
  property_name = plastic_strain_yz
  index_i = 1
  index_j = 2
  block = 2
[]
[Materials/audit_mechanical_strain_xx]
  type = RankTwoCartesianComponent
  rank_two_tensor = audit_mechanical_strain
  property_name = mechanical_strain_xx
  index_i = 0
  index_j = 0
  block = 2
[]
[Materials/audit_mechanical_strain_yy]
  type = RankTwoCartesianComponent
  rank_two_tensor = audit_mechanical_strain
  property_name = mechanical_strain_yy
  index_i = 1
  index_j = 1
  block = 2
[]
[Materials/audit_mechanical_strain_zz]
  type = RankTwoCartesianComponent
  rank_two_tensor = audit_mechanical_strain
  property_name = mechanical_strain_zz
  index_i = 2
  index_j = 2
  block = 2
[]
[Materials/audit_mechanical_strain_xy]
  type = RankTwoCartesianComponent
  rank_two_tensor = audit_mechanical_strain
  property_name = mechanical_strain_xy
  index_i = 0
  index_j = 1
  block = 2
[]
[Materials/audit_mechanical_strain_xz]
  type = RankTwoCartesianComponent
  rank_two_tensor = audit_mechanical_strain
  property_name = mechanical_strain_xz
  index_i = 0
  index_j = 2
  block = 2
[]
[Materials/audit_mechanical_strain_yz]
  type = RankTwoCartesianComponent
  rank_two_tensor = audit_mechanical_strain
  property_name = mechanical_strain_yz
  index_i = 1
  index_j = 2
  block = 2
[]
[Materials/audit_total_strain_xx]
  type = RankTwoCartesianComponent
  rank_two_tensor = audit_total_strain
  property_name = total_strain_xx
  index_i = 0
  index_j = 0
  block = 2
[]
[Materials/audit_total_strain_yy]
  type = RankTwoCartesianComponent
  rank_two_tensor = audit_total_strain
  property_name = total_strain_yy
  index_i = 1
  index_j = 1
  block = 2
[]
[Materials/audit_total_strain_zz]
  type = RankTwoCartesianComponent
  rank_two_tensor = audit_total_strain
  property_name = total_strain_zz
  index_i = 2
  index_j = 2
  block = 2
[]
[Materials/audit_total_strain_xy]
  type = RankTwoCartesianComponent
  rank_two_tensor = audit_total_strain
  property_name = total_strain_xy
  index_i = 0
  index_j = 1
  block = 2
[]
[Materials/audit_total_strain_xz]
  type = RankTwoCartesianComponent
  rank_two_tensor = audit_total_strain
  property_name = total_strain_xz
  index_i = 0
  index_j = 2
  block = 2
[]
[Materials/audit_total_strain_yz]
  type = RankTwoCartesianComponent
  rank_two_tensor = audit_total_strain
  property_name = total_strain_yz
  index_i = 1
  index_j = 2
  block = 2
[]
