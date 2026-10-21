# HYPOTHETICAL SOFTWARE VERIFICATION ONLY. No physical alloy or head model.
# Units: mm, MPa, K. Traction-free sides; axial ends blocked.
[GlobalParams]
  displacements = 'disp_x disp_y disp_z'
[]
[Mesh]
  [bar]
    type = GeneratedMeshGenerator
    dim = 3
    xmax = 1
    ymax = 2
    zmax = 10
    nx = 1
    ny = 1
    nz = 4
  []
  [origin]
    type = BoundingBoxNodeSetGenerator
    input = bar
    new_boundary = origin
    bottom_left = '-1e-8 -1e-8 -1e-8'
    top_right = '1e-8 1e-8 1e-8'
  []
  [rotation]
    type = BoundingBoxNodeSetGenerator
    input = origin
    new_boundary = rotation
    bottom_left = '0.99999999 -1e-8 -1e-8'
    top_right = '1.00000001 1e-8 1e-8'
  []
  [axial_start]
    type = BoundingBoxNodeSetGenerator
    input = rotation
    new_boundary = axial_start
    bottom_left = '-1e-8 -1e-8 -1e-8'
    top_right = '1.00000001 2.00000001 1e-8'
  []
  [axial_end]
    type = BoundingBoxNodeSetGenerator
    input = axial_start
    new_boundary = axial_end
    bottom_left = '-1e-8 -1e-8 9.99999999'
    top_right = '1.00000001 2.00000001 10.00000001'
  []
[]
[AuxVariables]
  [temperature]
    initial_condition = 300
  []
[]
[Functions]
  [thermal_cycle]
    type = PiecewiseLinear
    x = '0 1 2 3 4 5 6'
    y = '300 400 500 600 500 400 300'
  []
  [mean_alpha]
    type = ParsedFunction
    expression = '1e-5 + 2e-8*(t-300)'
  []
[]
[AuxKernels]
  [temperature]
    type = FunctionAux
    variable = temperature
    function = thermal_cycle
    execute_on = 'INITIAL TIMESTEP_BEGIN'
  []
[]
[Physics/SolidMechanics/QuasiStatic]
  [bar]
    strain = SMALL
    incremental = false
    use_automatic_differentiation = true
    add_variables = true
    eigenstrain_names = thermal_eigenstrain
    generate_output = 'stress_xx stress_yy stress_zz stress_xy stress_xz stress_yz'
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
  [axial]
    type = ADDirichletBC
    variable = disp_z
    boundary = 'axial_start axial_end'
    value = 0
  []
[]
[Materials]
  [young]
    type = ADParsedMaterial
    property_name = young_T
    coupled_variables = temperature
    expression = '210000-200*(temperature-300)'
  []
  [poisson]
    type = ADParsedMaterial
    property_name = poisson_T
    coupled_variables = temperature
    expression = '0.26+1e-4*(temperature-300)'
  []
  [elasticity]
    type = ADComputeVariableIsotropicElasticityTensor
    youngs_modulus = young_T
    poissons_ratio = poisson_T
  []
  [thermal]
    type = ADComputeMeanThermalExpansionFunctionEigenstrain
    stress_free_temperature = 300
    thermal_expansion_function = mean_alpha
    thermal_expansion_function_reference_temperature = 250
    temperature = temperature
    eigenstrain_name = thermal_eigenstrain
  []
  [stress]
    type = ADComputeLinearElasticStress
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
  nl_rel_tol = 1e-11
  nl_abs_tol = 1e-10
  nl_max_its = 30
[]
[Postprocessors]
  [stress_xx_min]
    type = ElementExtremeValue
    variable = stress_xx
    value_type = min
    execute_on = 'INITIAL TIMESTEP_END'
  []
  [stress_xx_max]
    type = ElementExtremeValue
    variable = stress_xx
    value_type = max
    execute_on = 'INITIAL TIMESTEP_END'
  []
  [stress_yy_min]
    type = ElementExtremeValue
    variable = stress_yy
    value_type = min
    execute_on = 'INITIAL TIMESTEP_END'
  []
  [stress_yy_max]
    type = ElementExtremeValue
    variable = stress_yy
    value_type = max
    execute_on = 'INITIAL TIMESTEP_END'
  []
  [stress_zz_min]
    type = ElementExtremeValue
    variable = stress_zz
    value_type = min
    execute_on = 'INITIAL TIMESTEP_END'
  []
  [stress_zz_max]
    type = ElementExtremeValue
    variable = stress_zz
    value_type = max
    execute_on = 'INITIAL TIMESTEP_END'
  []
  [stress_xy_min]
    type = ElementExtremeValue
    variable = stress_xy
    value_type = min
    execute_on = 'INITIAL TIMESTEP_END'
  []
  [stress_xy_max]
    type = ElementExtremeValue
    variable = stress_xy
    value_type = max
    execute_on = 'INITIAL TIMESTEP_END'
  []
  [stress_xz_min]
    type = ElementExtremeValue
    variable = stress_xz
    value_type = min
    execute_on = 'INITIAL TIMESTEP_END'
  []
  [stress_xz_max]
    type = ElementExtremeValue
    variable = stress_xz
    value_type = max
    execute_on = 'INITIAL TIMESTEP_END'
  []
  [stress_yz_min]
    type = ElementExtremeValue
    variable = stress_yz
    value_type = min
    execute_on = 'INITIAL TIMESTEP_END'
  []
  [stress_yz_max]
    type = ElementExtremeValue
    variable = stress_yz
    value_type = max
    execute_on = 'INITIAL TIMESTEP_END'
  []
  [disp_x_min]
    type = NodalExtremeValue
    variable = disp_x
    value_type = min
    execute_on = 'INITIAL TIMESTEP_END'
  []
  [disp_x_max]
    type = NodalExtremeValue
    variable = disp_x
    value_type = max
    execute_on = 'INITIAL TIMESTEP_END'
  []
  [disp_y_min]
    type = NodalExtremeValue
    variable = disp_y
    value_type = min
    execute_on = 'INITIAL TIMESTEP_END'
  []
  [disp_y_max]
    type = NodalExtremeValue
    variable = disp_y
    value_type = max
    execute_on = 'INITIAL TIMESTEP_END'
  []
  [disp_z_min]
    type = NodalExtremeValue
    variable = disp_z
    value_type = min
    execute_on = 'INITIAL TIMESTEP_END'
  []
  [disp_z_max]
    type = NodalExtremeValue
    variable = disp_z
    value_type = max
    execute_on = 'INITIAL TIMESTEP_END'
  []
  [temperature_min]
    type = NodalExtremeValue
    variable = temperature
    value_type = min
    execute_on = 'INITIAL TIMESTEP_END'
  []
  [temperature_max]
    type = NodalExtremeValue
    variable = temperature
    value_type = max
    execute_on = 'INITIAL TIMESTEP_END'
  []
[]
[Outputs]
  csv = true
  exodus = true
  print_linear_residuals = true
[]
