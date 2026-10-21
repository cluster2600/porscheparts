# HELD imported TET4 software witness; x:mm, w:mm^2. No physical temperature.
[Mesh]
  [cube]
    type = FileMeshGenerator
    file = imported-cube.msh
  []
[]
[Variables]
  [w]
    family = LAGRANGE
    order = FIRST
    initial_condition = 0
  []
[]
[Functions]
  [zero]
    type = ParsedFunction
    expression = 0
  []
  [unit]
    type = ParsedFunction
    expression = 1
  []
[]
[Kernels]
  [diffusion]
    type = ADHeatConduction
    variable = w
    use_displaced_mesh = false
  []
  [source]
    type = ADMatHeatSource
    variable = w
    material_property = normalized_source
  []
[]
[BCs]
  [all_boundary]
    type = FunctionDirichletBC
    variable = w
    boundary = all_boundary
    function = zero
    preset = false
  []
[]
[Materials]
  [unit_operator]
    type = ADHeatConductionMaterial
    temperature = w
    thermal_conductivity_temperature_function = unit
  []
  [unit_source]
    type = ADGenericConstantMaterial
    prop_names = normalized_source
    prop_values = 1
  []
  [flux_coefficient]
    type = GenericConstantMaterial
    prop_names = unit_diffusivity
    prop_values = 1
  []
[]
[VectorPostprocessors]
  [nodes]
    type = NodalValueSampler
    variable = w
    sort_by = id
    execute_on = FINAL
  []
[]
[Postprocessors]
  [raw_outward_gradient_flux]
    type = SideDiffusiveFluxIntegral
    variable = w
    diffusivity = unit_diffusivity
    boundary = all_boundary
    execute_on = FINAL
  []
[]
[Preconditioning]
  [full]
    type = SMP
    full = true
  []
[]
[Executioner]
  type = Steady
  solve_type = NEWTON
  nl_rel_tol = 1e-12
  nl_abs_tol = 1e-12
  nl_max_its = 1
  l_tol = 1e-12
  l_abs_tol = 1e-13
  l_max_its = 100
  petsc_options = '-ksp_converged_reason -snes_converged_reason -ksp_monitor_true_residual -ksp_error_if_not_converged'
  petsc_options_iname = '-ksp_type -pc_type -pc_hypre_type -pc_hypre_boomeramg_cycle_type -pc_hypre_boomeramg_max_iter -pc_hypre_boomeramg_tol -ksp_gmres_restart -ksp_view -ksp_view_mat -ksp_view_pmat -ksp_view_rhs -ksp_view_solution -ksp_view_final_residual'
  petsc_options_value = 'gmres hypre boomeramg V 1 0 30 ascii:ksp.txt ascii:operator.m:ascii_matlab ascii:preconditioner.m:ascii_matlab ascii:rhs.m:ascii_matlab ascii:correction.m:ascii_matlab ascii:true_residual.txt'
[]
[Outputs]
  file_base = imported-cube
  exodus = true
  [csv]
    type = CSV
    precision = 17
    execute_on = FINAL
  []
  [console]
    type = Console
    output_postprocessors = false
  []
[]
