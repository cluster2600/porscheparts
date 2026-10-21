# Software witness: imposed thermal cycle, stress-free birth in a predeformed pose,
# incremental J2 equilibrium, and restraint release in one continuous state.
# Units: mm, MPa, s, K. Main bar: 10 x 1 x 1 mm. Dummy block seeds future block2.
[GlobalParams]
  displacements = 'disp_x disp_y disp_z'
[]
[Problem]
  material_coverage_check = false
[]
[Mesh]
  [bar]
    type = GeneratedMeshGenerator
    dim = 3
    xmax = 10
    ymax = 1
    zmax = 1
    nx = 10
    ny = 1
    nz = 1
    subdomain_ids = 1
  []
  [dummy]
    type = GeneratedMeshGenerator
    dim = 3
    xmin = -2
    xmax = -1.999
    ymax = 0.001
    zmax = 0.001
    subdomain_ids = 2
  []
  [combined]
    type = CombinerGenerator
    inputs = 'bar dummy'
  []
  [bar_left]
    type = BoundingBoxNodeSetGenerator
    input = combined
    new_boundary = bar_left
    bottom_left = '-1e-08 -1e-08 -1e-08'
    top_right = '1e-08 1.00000001 1.00000001'
  []
  [bar_right]
    type = BoundingBoxNodeSetGenerator
    input = bar_left
    new_boundary = bar_right
    bottom_left = '9.99999999 -1e-08 -1e-08'
    top_right = '10.00000001 1.00000001 1.00000001'
  []
  [bar_front]
    type = BoundingBoxNodeSetGenerator
    input = bar_right
    new_boundary = bar_front
    bottom_left = '-1e-08 -1e-08 -1e-08'
    top_right = '10.00000001 1e-08 1.00000001'
  []
  [bar_bottom]
    type = BoundingBoxNodeSetGenerator
    input = bar_front
    new_boundary = bar_bottom
    bottom_left = '-1e-08 -1e-08 -1e-08'
    top_right = '10.00000001 1.00000001 1e-08'
  []
  [dummy_fixed]
    type = BoundingBoxNodeSetGenerator
    input = bar_bottom
    new_boundary = dummy_fixed
    bottom_left = '-3 -1 -1'
    top_right = '-1 2 2'
  []
[]
[Variables]
  [disp_x]
    block = '1 2'
  []
  [disp_y]
    block = '1 2'
  []
  [disp_z]
    block = '1 2'
  []
[]
[AuxVariables]
  [plastic_xx]
    family = MONOMIAL
    order = CONSTANT
    block = 2
  []
  [temperature]
    initial_condition = 300
  []
[]
[Functions]
  [initial_pose]
    type = ParsedFunction
    expression = 'if(x<0,0,0.0005*x)'
  []
  [thermal_cycle]
    type = PiecewiseLinear
    x = '0 1 2 3 4 5 6'
    y = '300 300 600 300 300 300 300'
  []
[]
[ICs]
  [initial_pose]
    type = FunctionIC
    variable = disp_x
    function = initial_pose
  []
[]
[AuxKernels]
  [plastic_xx]
    type = ADRankTwoAux
    variable = plastic_xx
    rank_two_tensor = plastic_strain
    index_i = 0
    index_j = 0
    block = 2
    execute_on = TIMESTEP_END
  []
  [temperature]
    type = FunctionAux
    variable = temperature
    function = thermal_cycle
    execute_on = 'INITIAL TIMESTEP_BEGIN'
  []
[]
[Kernels]
  [quiet_x]
    type = ADDiffusion
    variable = disp_x
    block = 1
  []
  [quiet_y]
    type = ADDiffusion
    variable = disp_y
    block = 1
  []
  [quiet_z]
    type = ADDiffusion
    variable = disp_z
    block = 1
  []
[]
[Physics/SolidMechanics/QuasiStatic]
  [active]
    block = 2
    strain = SMALL
    incremental = true
    use_automatic_differentiation = true
    eigenstrain_names = 'thermal_eigenstrain'
    generate_output = 'stress_xx stress_yy stress_zz'
  []
[]
[BCs]
  [left_x]
    type = ADDirichletBC
    variable = disp_x
    boundary = bar_left
    value = 0
  []
  [right_x]
    type = ADDirichletBC
    variable = disp_x
    boundary = bar_right
    value = 0.005
  []
  [front_y]
    type = ADDirichletBC
    variable = disp_y
    boundary = bar_front
    value = 0
  []
  [bottom_z]
    type = ADDirichletBC
    variable = disp_z
    boundary = bar_bottom
    value = 0
  []
  [dummy_x]
    type = ADDirichletBC
    variable = disp_x
    boundary = dummy_fixed
    value = 0
  []
  [dummy_y]
    type = ADDirichletBC
    variable = disp_y
    boundary = dummy_fixed
    value = 0
  []
  [dummy_z]
    type = ADDirichletBC
    variable = disp_z
    boundary = dummy_fixed
    value = 0
  []
[]
[Materials]
  [elasticity]
    type = ADComputeIsotropicElasticityTensor
    youngs_modulus = 200000
    poissons_ratio = 0.3
    block = 2
  []
  [thermal]
    type = ADComputeThermalExpansionEigenstrain
    stress_free_temperature = 300
    thermal_expansion_coeff = 1e-5
    temperature = temperature
    eigenstrain_name = thermal_eigenstrain
    block = 2
  []
  [stress]
    type = ADComputeMultipleInelasticStress
    inelastic_models = 'plasticity'
    perform_finite_strain_rotations = false
    block = 2
  []
  [plasticity]
    type = ADIsotropicPlasticityStressUpdate
    yield_stress = 200
    hardening_constant = 0
    relative_tolerance = 1e-10
    absolute_tolerance = 1e-10
    block = 2
  []
[]
[MeshModifiers]
  [birth]
    type = TimedSubdomainModifier
    times = 1
    blocks_from = 1
    blocks_to = 2
    reinitialize_subdomains = '2'
    execute_on = TIMESTEP_BEGIN
  []
[]
[Controls]
  [release]
    type = TimePeriod
    enable_objects = 'BCs::right_x'
    start_time = 0
    end_time = 4.5
    execute_on = 'INITIAL TIMESTEP_BEGIN'
  []
[]
[Preconditioning]
  [full]
    type = SMP
    full = true
  []
[]
[Executioner]
  type = Transient
  solve_type = NEWTON
  petsc_options_iname = '-ksp_type -pc_type'
  petsc_options_value = 'preonly lu'
  line_search = none
  dt = 1
  end_time = 6
  nl_rel_tol = 1e-10
  nl_abs_tol = 1e-9
  nl_max_its = 30
[]
[Postprocessors]
  [temperature_bar]
    type = PointValue
    variable = temperature
    point = '5.25 0.5 0.5'
    execute_on = TIMESTEP_END
  []
  [plastic_xx_bar]
    type = PointValue
    variable = plastic_xx
    point = '5.25 0.5 0.5'
    execute_on = TIMESTEP_END
  []
  [u_right]
    type = PointValue
    variable = disp_x
    point = '10 0.5 0.5'
    execute_on = 'INITIAL TIMESTEP_END'
  []
  [stress_bar]
    type = PointValue
    variable = stress_xx
    point = '5.25 0.5 0.5'
    execute_on = TIMESTEP_END
  []
[]
[Outputs]
  csv = true
  exodus = true
  print_linear_residuals = true
[]
