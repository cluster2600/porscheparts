# HELD 3DOF imported TET4 affine elasticity software witness; mm,MPa,N.
# No physical alloy, thermal load, head/service/strength or manufacturing claim.
[GlobalParams]
  displacements = 'disp_x disp_y disp_z'
[]
[Mesh/cube]
  type = FileMeshGenerator
  file = imported-cube.msh
[]
[AuxVariables]
  [rx]
    family = LAGRANGE
    order = FIRST
  []
  [ry]
    family = LAGRANGE
    order = FIRST
  []
  [rz]
    family = LAGRANGE
    order = FIRST
  []
[]
[Functions]
  [ux]
    type = ParsedFunction
    expression = '0.001*x+0.0002*y'
  []
  [uy]
    type = ParsedFunction
    expression = '0.0002*x-0.0005*y+0.0003*z'
  []
  [uz]
    type = ParsedFunction
    expression = '0.0003*y+0.0008*z'
  []
[]
[Physics/SolidMechanics/QuasiStatic/cube]
  strain = SMALL
  incremental = false
  use_automatic_differentiation = true
  add_variables = true
  save_in = 'rx ry rz'
[]
[BCs]
  [affine_x]
    type = FunctionDirichletBC
    variable = disp_x
    boundary = all_boundary
    function = ux
    preset = false
  []
  [affine_y]
    type = FunctionDirichletBC
    variable = disp_y
    boundary = all_boundary
    function = uy
    preset = false
  []
  [affine_z]
    type = FunctionDirichletBC
    variable = disp_z
    boundary = all_boundary
    function = uz
    preset = false
  []
[]
[Materials]
  [elasticity]
    type = ADComputeIsotropicElasticityTensor
    youngs_modulus = 210000
    poissons_ratio = 0.26
  []
  [stress]
    type = ADComputeLinearElasticStress
  []
  [audit_tensors]
    type = RankTwoTensorMaterialADConverter
    ad_props_in = 'stress total_strain'
    reg_props_out = 'audit_stress audit_total_strain'
  []
  [stress_xx]
    type = RankTwoCartesianComponent
    rank_two_tensor = audit_stress
    property_name = stress_xx
    index_i = 0
    index_j = 0
  []
  [stress_yy]
    type = RankTwoCartesianComponent
    rank_two_tensor = audit_stress
    property_name = stress_yy
    index_i = 1
    index_j = 1
  []
  [stress_zz]
    type = RankTwoCartesianComponent
    rank_two_tensor = audit_stress
    property_name = stress_zz
    index_i = 2
    index_j = 2
  []
  [stress_xy]
    type = RankTwoCartesianComponent
    rank_two_tensor = audit_stress
    property_name = stress_xy
    index_i = 0
    index_j = 1
  []
  [stress_xz]
    type = RankTwoCartesianComponent
    rank_two_tensor = audit_stress
    property_name = stress_xz
    index_i = 0
    index_j = 2
  []
  [stress_yz]
    type = RankTwoCartesianComponent
    rank_two_tensor = audit_stress
    property_name = stress_yz
    index_i = 1
    index_j = 2
  []
  [total_strain_xx]
    type = RankTwoCartesianComponent
    rank_two_tensor = audit_total_strain
    property_name = total_strain_xx
    index_i = 0
    index_j = 0
  []
  [total_strain_yy]
    type = RankTwoCartesianComponent
    rank_two_tensor = audit_total_strain
    property_name = total_strain_yy
    index_i = 1
    index_j = 1
  []
  [total_strain_zz]
    type = RankTwoCartesianComponent
    rank_two_tensor = audit_total_strain
    property_name = total_strain_zz
    index_i = 2
    index_j = 2
  []
  [total_strain_xy]
    type = RankTwoCartesianComponent
    rank_two_tensor = audit_total_strain
    property_name = total_strain_xy
    index_i = 0
    index_j = 1
  []
  [total_strain_xz]
    type = RankTwoCartesianComponent
    rank_two_tensor = audit_total_strain
    property_name = total_strain_xz
    index_i = 0
    index_j = 2
  []
  [total_strain_yz]
    type = RankTwoCartesianComponent
    rank_two_tensor = audit_total_strain
    property_name = total_strain_yz
    index_i = 1
    index_j = 2
  []
[]
[VectorPostprocessors]
  [nodes]
    type = NodalValueSampler
    variable = 'disp_x disp_y disp_z rx ry rz'
    sort_by = id
    execute_on = FINAL
  []
  [fields]
    type = ElementMaterialSampler
    property = 'stress_xx stress_yy stress_zz stress_xy stress_xz stress_yz total_strain_xx total_strain_yy total_strain_zz total_strain_xy total_strain_xz total_strain_yz'
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
  automatic_scaling = true
  scaling_group_variables = 'disp_x disp_y disp_z'
  nl_rel_tol = 1e-11
  nl_abs_tol = 1e-10
  nl_max_its = 1
  line_search = none
  l_tol = 1e-11
  l_abs_tol = 1e-12
  l_max_its = 100
  petsc_options = '-ksp_converged_reason -snes_converged_reason -ksp_monitor_true_residual -ksp_error_if_not_converged'
  petsc_options_iname = '-ksp_type -pc_type -pc_hypre_type -pc_hypre_boomeramg_cycle_type -pc_hypre_boomeramg_max_iter -pc_hypre_boomeramg_tol -ksp_gmres_restart -ksp_view -ksp_view_mat -ksp_view_pmat -ksp_view_rhs -ksp_view_solution -ksp_view_final_residual'
  petsc_options_value = 'gmres hypre boomeramg V 1 0 30 ascii:ksp.txt ascii:operator.m:ascii_matlab ascii:preconditioner.m:ascii_matlab ascii:rhs.m:ascii_matlab ascii:correction.m:ascii_matlab ascii:true_residual.txt'
  [Quadrature]
    type = GAUSS
    order = FIRST
    element_order = FIRST
    side_order = FIRST
  []
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
