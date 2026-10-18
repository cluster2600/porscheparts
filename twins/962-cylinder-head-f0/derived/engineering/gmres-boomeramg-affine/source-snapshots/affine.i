# Synthetic harmonic diffusion software witness. No head or material data.
[Mesh]
  [cube]
    type = GeneratedMeshGenerator
    dim = 3
    xmin = 1
    xmax = 2
    ymin = 1
    ymax = 2
    zmin = 1
    zmax = 2
    nx = 3
    ny = 3
    nz = 3
    elem_type = HEX8
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
  [exact]
    type = ParsedFunction
    expression = 'x+2*y+3*z'
  []
[]
[Kernels]
  [diffusion]
    type = Diffusion
    variable = w
  []
[]
[BCs]
  [all_boundary]
    type = FunctionDirichletBC
    variable = w
    boundary = 'left right bottom top back front'
    function = exact
    preset = false
  []
[]
[Materials]
  [unit_diffusivity]
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
  [flux_left]
    type = SideDiffusiveFluxIntegral
    variable = w
    diffusivity = unit_diffusivity
    boundary = left
    execute_on = FINAL
  []
  [flux_right]
    type = SideDiffusiveFluxIntegral
    variable = w
    diffusivity = unit_diffusivity
    boundary = right
    execute_on = FINAL
  []
  [flux_bottom]
    type = SideDiffusiveFluxIntegral
    variable = w
    diffusivity = unit_diffusivity
    boundary = bottom
    execute_on = FINAL
  []
  [flux_top]
    type = SideDiffusiveFluxIntegral
    variable = w
    diffusivity = unit_diffusivity
    boundary = top
    execute_on = FINAL
  []
  [flux_back]
    type = SideDiffusiveFluxIntegral
    variable = w
    diffusivity = unit_diffusivity
    boundary = back
    execute_on = FINAL
  []
  [flux_front]
    type = SideDiffusiveFluxIntegral
    variable = w
    diffusivity = unit_diffusivity
    boundary = front
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
  file_base = affine
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
