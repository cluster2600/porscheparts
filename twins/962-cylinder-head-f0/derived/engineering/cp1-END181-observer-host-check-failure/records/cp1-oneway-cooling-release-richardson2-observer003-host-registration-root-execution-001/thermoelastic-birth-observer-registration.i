# Unqualified one-way prescribed cooling/build-clamp/release case; SI m,Pa,N,K,s.
[Problem]
  material_coverage_check = false
  register_objects_from = CouponEnd181ObserverApp
  library_path = '/Users/maxime/.codex/worktrees/962-faithful-displacements/3dprinting993/work/962-engineering/cp1-oneway-cooling-release-richardson2-END181-dof-map-observer-prep-003/build-005'
  library_name = libcoupon_end181_observer-opt.la
[]
[GlobalParams]
  displacements = 'disp_x disp_y disp_z'
[]
[Mesh]
  add_subdomain_ids = '3'
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
  [origin]
    type = BoundingBoxNodeSetGenerator
    input = old
    new_boundary = origin
    bottom_left = '-1e-12 -1e-12 -1e-12'
    top_right = '1e-12 1e-12 1e-12'
  []
  [axis_x]
    type = BoundingBoxNodeSetGenerator
    input = origin
    new_boundary = axis_x
    bottom_left = '.999999999999 -1e-12 -1e-12'
    top_right = '1.000000000001 1e-12 1e-12'
  []
  [axis_y]
    type = BoundingBoxNodeSetGenerator
    input = axis_x
    new_boundary = axis_y
    bottom_left = '-1e-12 .999999999999 -1e-12'
    top_right = '1e-12 1.000000000001 1e-12'
  []
  [build_plane]
    type = BoundingBoxNodeSetGenerator
    input = axis_y
    new_boundary = build_clamp
    bottom_left = '-1e-12 -1e-12 -1e-12'
    top_right = '2.000000000001 1.000000000001 1e-12'
  []
[]
# This donor placeholder holds inactive block1 at zero, not physical inertia.
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
[Physics/SolidMechanics/QuasiStatic/coupon]
  block = '2 3'
  strain = SMALL
  incremental = true
  use_automatic_differentiation = true
  add_variables = true
  eigenstrain_names = thermal_eigenstrain
  save_in = 'rx ry rz'
[]
[AuxVariables]
  [temperature]
    family = LAGRANGE
    order = FIRST
    block = '2 3'
  []
  [born_reference_temperature]
    family = LAGRANGE
    order = FIRST
    block = 3
  []
  [rx]
    block = '2 3'
  []
  [ry]
    block = '2 3'
  []
  [rz]
    block = '2 3'
  []
[]
[Functions]
  [old_end]
    type = PiecewiseMultilinear
    data_file = old-end.grid
  []
  [born_end]
    type = PiecewiseMultilinear
    data_file = born-end.grid
  []
  [born_begin80]
    type = PiecewiseMultilinear
    data_file = born-begin80.grid
  []
[]
[ICs]
  [disp_x]
    type = FunctionIC
    variable = disp_x
    function = 0
    block = '2 3'
  []
  [disp_y]
    type = FunctionIC
    variable = disp_y
    function = 0
    block = '2 3'
  []
  [disp_z]
    type = FunctionIC
    variable = disp_z
    function = 0
    block = '2 3'
  []
  [old_temperature]
    type = FunctionIC
    variable = temperature
    function = 400
    block = 2
  []
  [born_temperature]
    type = FunctionIC
    variable = temperature
    function = born_begin80
    block = 3
  []
  [born_reference]
    type = FunctionIC
    variable = born_reference_temperature
    function = born_begin80
    block = 3
  []
[]
[AuxKernels]
  [old_temperature]
    type = FunctionAux
    variable = temperature
    function = old_end
    block = 2
    execute_on = 'INITIAL TIMESTEP_BEGIN'
  []
  [born_temperature]
    type = FunctionAux
    variable = temperature
    function = born_end
    block = 3
    execute_on = 'INITIAL TIMESTEP_BEGIN'
  []
[]
[MeshModifiers/birth]
  type = TimedSubdomainModifier
  times = 0.2
  blocks_from = 1
  blocks_to = 3
  reinitialize_subdomains = 3
  reinitialize_variables = 'disp_x disp_y disp_z temperature born_reference_temperature'
  reinitialization_strategy = IC
  restore_overridden_dofs = 'true true true true false'
  force_preaux = true
  execution_order_group = -100
  execute_on = TIMESTEP_BEGIN
[]
[BCs]
  [build_x]
    type = ADDirichletBC
    variable = disp_x
    boundary = build_clamp
    value = 0
  []
  [build_y]
    type = ADDirichletBC
    variable = disp_y
    boundary = build_clamp
    value = 0
  []
  [build_z]
    type = ADDirichletBC
    variable = disp_z
    boundary = build_clamp
    value = 0
  []
  [origin_x]
    type = ADDirichletBC
    variable = disp_x
    boundary = origin
    value = 0
    enable = false
  []
  [origin_y]
    type = ADDirichletBC
    variable = disp_y
    boundary = origin
    value = 0
    enable = false
  []
  [origin_z]
    type = ADDirichletBC
    variable = disp_z
    boundary = origin
    value = 0
    enable = false
  []
  [axis_x_y]
    type = ADDirichletBC
    variable = disp_y
    boundary = axis_x
    value = 0
    enable = false
  []
  [axis_x_z]
    type = ADDirichletBC
    variable = disp_z
    boundary = axis_x
    value = 0
    enable = false
  []
  [axis_y_z]
    type = ADDirichletBC
    variable = disp_z
    boundary = axis_y
    value = 0
    enable = false
  []
[]
[Controls]
  [release_build_clamp]
    type = TimePeriod
    enable_objects = 'BCs/origin_x BCs/origin_y BCs/origin_z BCs/axis_x_y BCs/axis_x_z BCs/axis_y_z'
    disable_objects = 'BCs/build_x BCs/build_y BCs/build_z'
    start_time = 0.4525
    reverse_on_false = true
    set_sync_times = true
    execute_on = 'INITIAL TIMESTEP_BEGIN'
  []
[]
[Materials]
  [elasticity]
    type = ADComputeIsotropicElasticityTensor
    youngs_modulus = 71e9
    poissons_ratio = 0.33
    block = '2 3'
  []
  [old_thermal]
    type = ADComputeThermalExpansionEigenstrain
    thermal_expansion_coeff = 1e-5
    stress_free_temperature = 400
    temperature = temperature
    eigenstrain_name = thermal_eigenstrain
    block = 2
  []
  [born_thermal]
    type = ADComputeThermalExpansionEigenstrain
    thermal_expansion_coeff = 1e-5
    stress_free_temperature = born_reference_temperature
    temperature = temperature
    eigenstrain_name = thermal_eigenstrain
    block = 3
  []
  [stress]
    type = ADComputeFiniteStrainElasticStress
    block = '2 3'
  []
[]
[Materials/audit_tensors]
  type = RankTwoTensorMaterialADConverter
  ad_props_in = 'stress elastic_strain mechanical_strain total_strain thermal_eigenstrain'
  reg_props_out = 'audit_stress audit_elastic_strain audit_mechanical_strain audit_total_strain audit_thermal_eigenstrain'
  block = '2 3'
[]
[Materials/audit_stress_xx]
  type = RankTwoCartesianComponent
  rank_two_tensor = audit_stress
  property_name = stress_xx
  index_i = 0
  index_j = 0
  block = '2 3'
[]
[Materials/audit_stress_yy]
  type = RankTwoCartesianComponent
  rank_two_tensor = audit_stress
  property_name = stress_yy
  index_i = 1
  index_j = 1
  block = '2 3'
[]
[Materials/audit_stress_zz]
  type = RankTwoCartesianComponent
  rank_two_tensor = audit_stress
  property_name = stress_zz
  index_i = 2
  index_j = 2
  block = '2 3'
[]
[Materials/audit_stress_xy]
  type = RankTwoCartesianComponent
  rank_two_tensor = audit_stress
  property_name = stress_xy
  index_i = 0
  index_j = 1
  block = '2 3'
[]
[Materials/audit_stress_xz]
  type = RankTwoCartesianComponent
  rank_two_tensor = audit_stress
  property_name = stress_xz
  index_i = 0
  index_j = 2
  block = '2 3'
[]
[Materials/audit_stress_yz]
  type = RankTwoCartesianComponent
  rank_two_tensor = audit_stress
  property_name = stress_yz
  index_i = 1
  index_j = 2
  block = '2 3'
[]
[Materials/audit_elastic_strain_xx]
  type = RankTwoCartesianComponent
  rank_two_tensor = audit_elastic_strain
  property_name = elastic_strain_xx
  index_i = 0
  index_j = 0
  block = '2 3'
[]
[Materials/audit_elastic_strain_yy]
  type = RankTwoCartesianComponent
  rank_two_tensor = audit_elastic_strain
  property_name = elastic_strain_yy
  index_i = 1
  index_j = 1
  block = '2 3'
[]
[Materials/audit_elastic_strain_zz]
  type = RankTwoCartesianComponent
  rank_two_tensor = audit_elastic_strain
  property_name = elastic_strain_zz
  index_i = 2
  index_j = 2
  block = '2 3'
[]
[Materials/audit_elastic_strain_xy]
  type = RankTwoCartesianComponent
  rank_two_tensor = audit_elastic_strain
  property_name = elastic_strain_xy
  index_i = 0
  index_j = 1
  block = '2 3'
[]
[Materials/audit_elastic_strain_xz]
  type = RankTwoCartesianComponent
  rank_two_tensor = audit_elastic_strain
  property_name = elastic_strain_xz
  index_i = 0
  index_j = 2
  block = '2 3'
[]
[Materials/audit_elastic_strain_yz]
  type = RankTwoCartesianComponent
  rank_two_tensor = audit_elastic_strain
  property_name = elastic_strain_yz
  index_i = 1
  index_j = 2
  block = '2 3'
[]
[Materials/audit_mechanical_strain_xx]
  type = RankTwoCartesianComponent
  rank_two_tensor = audit_mechanical_strain
  property_name = mechanical_strain_xx
  index_i = 0
  index_j = 0
  block = '2 3'
[]
[Materials/audit_mechanical_strain_yy]
  type = RankTwoCartesianComponent
  rank_two_tensor = audit_mechanical_strain
  property_name = mechanical_strain_yy
  index_i = 1
  index_j = 1
  block = '2 3'
[]
[Materials/audit_mechanical_strain_zz]
  type = RankTwoCartesianComponent
  rank_two_tensor = audit_mechanical_strain
  property_name = mechanical_strain_zz
  index_i = 2
  index_j = 2
  block = '2 3'
[]
[Materials/audit_mechanical_strain_xy]
  type = RankTwoCartesianComponent
  rank_two_tensor = audit_mechanical_strain
  property_name = mechanical_strain_xy
  index_i = 0
  index_j = 1
  block = '2 3'
[]
[Materials/audit_mechanical_strain_xz]
  type = RankTwoCartesianComponent
  rank_two_tensor = audit_mechanical_strain
  property_name = mechanical_strain_xz
  index_i = 0
  index_j = 2
  block = '2 3'
[]
[Materials/audit_mechanical_strain_yz]
  type = RankTwoCartesianComponent
  rank_two_tensor = audit_mechanical_strain
  property_name = mechanical_strain_yz
  index_i = 1
  index_j = 2
  block = '2 3'
[]
[Materials/audit_total_strain_xx]
  type = RankTwoCartesianComponent
  rank_two_tensor = audit_total_strain
  property_name = total_strain_xx
  index_i = 0
  index_j = 0
  block = '2 3'
[]
[Materials/audit_total_strain_yy]
  type = RankTwoCartesianComponent
  rank_two_tensor = audit_total_strain
  property_name = total_strain_yy
  index_i = 1
  index_j = 1
  block = '2 3'
[]
[Materials/audit_total_strain_zz]
  type = RankTwoCartesianComponent
  rank_two_tensor = audit_total_strain
  property_name = total_strain_zz
  index_i = 2
  index_j = 2
  block = '2 3'
[]
[Materials/audit_total_strain_xy]
  type = RankTwoCartesianComponent
  rank_two_tensor = audit_total_strain
  property_name = total_strain_xy
  index_i = 0
  index_j = 1
  block = '2 3'
[]
[Materials/audit_total_strain_xz]
  type = RankTwoCartesianComponent
  rank_two_tensor = audit_total_strain
  property_name = total_strain_xz
  index_i = 0
  index_j = 2
  block = '2 3'
[]
[Materials/audit_total_strain_yz]
  type = RankTwoCartesianComponent
  rank_two_tensor = audit_total_strain
  property_name = total_strain_yz
  index_i = 1
  index_j = 2
  block = '2 3'
[]
[Materials/audit_thermal_eigenstrain_xx]
  type = RankTwoCartesianComponent
  rank_two_tensor = audit_thermal_eigenstrain
  property_name = thermal_eigenstrain_xx
  index_i = 0
  index_j = 0
  block = '2 3'
[]
[Materials/audit_thermal_eigenstrain_yy]
  type = RankTwoCartesianComponent
  rank_two_tensor = audit_thermal_eigenstrain
  property_name = thermal_eigenstrain_yy
  index_i = 1
  index_j = 1
  block = '2 3'
[]
[Materials/audit_thermal_eigenstrain_zz]
  type = RankTwoCartesianComponent
  rank_two_tensor = audit_thermal_eigenstrain
  property_name = thermal_eigenstrain_zz
  index_i = 2
  index_j = 2
  block = '2 3'
[]
[Materials/audit_thermal_eigenstrain_xy]
  type = RankTwoCartesianComponent
  rank_two_tensor = audit_thermal_eigenstrain
  property_name = thermal_eigenstrain_xy
  index_i = 0
  index_j = 1
  block = '2 3'
[]
[Materials/audit_thermal_eigenstrain_xz]
  type = RankTwoCartesianComponent
  rank_two_tensor = audit_thermal_eigenstrain
  property_name = thermal_eigenstrain_xz
  index_i = 0
  index_j = 2
  block = '2 3'
[]
[Materials/audit_thermal_eigenstrain_yz]
  type = RankTwoCartesianComponent
  rank_two_tensor = audit_thermal_eigenstrain
  property_name = thermal_eigenstrain_yz
  index_i = 1
  index_j = 2
  block = '2 3'
[]
[VectorPostprocessors]
  [begin]
    type = NodalValueSampler
    variable = 'disp_x disp_y disp_z temperature'
    block = '2 3'
    sort_by = id
    force_preaux = true
    execution_order_group = -50
    execute_on = 'INITIAL TIMESTEP_BEGIN'
  []
  [end]
    type = NodalValueSampler
    variable = 'disp_x disp_y disp_z temperature rx ry rz'
    block = '2 3'
    sort_by = id
    execute_on = 'INITIAL TIMESTEP_END'
  []
  [reference_begin]
    type = NodalValueSampler
    variable = born_reference_temperature
    block = 3
    sort_by = id
    force_preaux = true
    execution_order_group = -50
    execute_on = 'INITIAL TIMESTEP_BEGIN'
  []
  [reference_end]
    type = NodalValueSampler
    variable = born_reference_temperature
    block = 3
    sort_by = id
    execute_on = 'INITIAL TIMESTEP_END'
  []
  [begin_fields]
    type = ElementMaterialSampler
    property = 'stress_xx stress_yy stress_zz stress_xy stress_xz stress_yz elastic_strain_xx elastic_strain_yy elastic_strain_zz elastic_strain_xy elastic_strain_xz elastic_strain_yz mechanical_strain_xx mechanical_strain_yy mechanical_strain_zz mechanical_strain_xy mechanical_strain_xz mechanical_strain_yz total_strain_xx total_strain_yy total_strain_zz total_strain_xy total_strain_xz total_strain_yz thermal_eigenstrain_xx thermal_eigenstrain_yy thermal_eigenstrain_zz thermal_eigenstrain_xy thermal_eigenstrain_xz thermal_eigenstrain_yz'
    block = '2 3'
    force_preaux = true
    execution_order_group = -50
    execute_on = 'INITIAL TIMESTEP_BEGIN'
  []
  [end_fields]
    type = ElementMaterialSampler
    property = 'stress_xx stress_yy stress_zz stress_xy stress_xz stress_yz elastic_strain_xx elastic_strain_yy elastic_strain_zz elastic_strain_xy elastic_strain_xz elastic_strain_yz mechanical_strain_xx mechanical_strain_yy mechanical_strain_zz mechanical_strain_xy mechanical_strain_xz mechanical_strain_yz total_strain_xx total_strain_yy total_strain_zz total_strain_xy total_strain_xz total_strain_yz thermal_eigenstrain_xx thermal_eigenstrain_yy thermal_eigenstrain_zz thermal_eigenstrain_xy thermal_eigenstrain_xz thermal_eigenstrain_yz'
    block = '2 3'
    execute_on = 'INITIAL TIMESTEP_END'
  []
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
  solve_type = LINEAR
  petsc_options = '-snes_monitor -ksp_monitor_true_residual -ksp_converged_reason'
  petsc_options_iname = '-ksp_type -pc_type -snes_norm_schedule -ksp_richardson_scale -ksp_richardson_self_scale -ksp_norm_type -ksp_convergence_test -ksp_max_it -snes_monitor_solution -snes_monitor_residual -snes_monitor_solution_update'
  petsc_options_value = 'richardson lu always 1 false unpreconditioned skip 2 binary:physical-X.petsc::append binary:physical-F.petsc::append binary:physical-Y.petsc::append'
  line_search = none
  dt = 0.0025
  end_time = 0.455
  nl_rel_tol = 1e-11
  nl_abs_tol = 1e-10
  nl_max_its = 30
[]
[Outputs]
  file_base = thermoelastic
  exodus = true
  [csv]
    type = CSV
    precision = 17
  []
  [console]
    type = Console
    output_postprocessors = false
  []
  [rich2_END181_dof_map]
    type = CouponEnd181DofMap
    file_base = rich2-END181-dof-map
    execute_on = TIMESTEP_END
    start_step = 181
    end_step = 181
    use_displaced = false
  []
[]
