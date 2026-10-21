# Independent second witness: same variable E/nu/mean-CTE, perfect J2 Y(T).
[Physics/SolidMechanics/QuasiStatic/bar]
  incremental = true
[]
[Functions/yield_T]
  type = ParsedFunction
  expression = '300-0.25*(t-300)'
[]
[Materials/stress]
  type = ADComputeMultipleInelasticStress
  inelastic_models = plasticity
  perform_finite_strain_rotations = false
[]
[Materials/plasticity]
  type = ADIsotropicPlasticityStressUpdate
  yield_stress_function = yield_T
  temperature = temperature
  hardening_constant = 0
  relative_tolerance = 1e-11
  absolute_tolerance = 1e-11
[]
[AuxVariables/plastic_zz]
  family = MONOMIAL
  order = CONSTANT
[]
[AuxKernels/plastic_zz]
  type = ADRankTwoAux
  variable = plastic_zz
  rank_two_tensor = plastic_strain
  index_i = 2
  index_j = 2
  execute_on = 'INITIAL TIMESTEP_END'
[]
[Postprocessors/plastic_zz_min]
  type = ElementExtremeValue
  variable = plastic_zz
  value_type = min
  execute_on = 'INITIAL TIMESTEP_END'
[]
[Postprocessors/plastic_zz_max]
  type = ElementExtremeValue
  variable = plastic_zz
  value_type = max
  execute_on = 'INITIAL TIMESTEP_END'
[]
