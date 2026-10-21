# HELD measured-conductivity software fixture; no native execution authorized.
# Units:mm,W,temperature in degC (increments equal kelvin); no radiation/storage.
# Strict per-material-evaluation range refusal remains UNVERIFIED:see PROTOCOL.md.
[Mesh]
  [bar]
    type = GeneratedMeshGenerator
    dim = 3
    xmax = 1
    ymax = 2
    zmax = 10
    nx = 1
    ny = 1
    nz = 16
    elem_type = HEX8
  []
[]
[Variables]
  [temperature]
    family = LAGRANGE
    order = FIRST
  []
[]
[Functions]
  [initial]
    type = ParsedFunction
    expression = '23+227*z/10'
  []
  [k_T]
    type = PiecewiseLinear
    x = '23 150 200 250'
    y = '0.1629 0.1636 0.1654 0.1605'
  []
[]
[ICs]
  [temperature]
    type = FunctionIC
    variable = temperature
    function = initial
  []
[]
[Kernels]
  [conduction]
    type = ADHeatConduction
    variable = temperature
    use_displaced_mesh = false
  []
[]
[BCs]
  [cold]
    type = ADDirichletBC
    variable = temperature
    boundary = back
    value = 23
  []
  [hot]
    type = ADDirichletBC
    variable = temperature
    boundary = front
    value = 250
  []
[]
[Materials]
  [thermal]
    type = ADHeatConductionMaterial
    temperature = temperature
    thermal_conductivity_temperature_function = k_T
  []
  [flux_export]
    type = MaterialADConverter
    ad_props_in = thermal_conductivity
    reg_props_out = k_for_flux
  []
[]
[AuxVariables]
  [k_seen]
    family = MONOMIAL
    order = CONSTANT
  []
[]
[AuxKernels]
  [k_seen]
    type = ADMaterialRealAux
    variable = k_seen
    property = thermal_conductivity
    execute_on = FINAL
  []
[]
[VectorPostprocessors]
  [nodes]
    type = NodalValueSampler
    variable = temperature
    sort_by = id
    execute_on = FINAL
  []
  [properties]
    type = ElementValueSampler
    variable = k_seen
    sort_by = id
    execute_on = FINAL
  []
[]
[Postprocessors]
  [cold_outward_W]
    type = SideDiffusiveFluxIntegral
    variable = temperature
    diffusivity = k_for_flux
    boundary = back
    execute_on = FINAL
  []
  [hot_outward_W]
    type = SideDiffusiveFluxIntegral
    variable = temperature
    diffusivity = k_for_flux
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
  [Quadrature]
    type = GAUSS
    order = SECOND
  []
  type = Steady
  solve_type = NEWTON
  petsc_options_iname = '-ksp_type -pc_type'
  petsc_options_value = 'preonly lu'
  nl_rel_tol = 1e-11
  nl_abs_tol = 1e-10
  nl_max_its = 30
[]
[Outputs]
  file_base = conductivity-z
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
