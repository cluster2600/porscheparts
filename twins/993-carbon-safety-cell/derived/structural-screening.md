# Présélection structurelle F1 — monocoque carbone 964/993

Statut : **screening_complete_not_validated**.

Ce calcul treillis linéaire classe des architectures originales. Il ne prouve ni une coque stratifiée, ni un crash, ni une aptitude route/circuit.

| Architecture | Matériaux primaires | Masse active (kg) | Torsion (Nm/deg) | Ratio / tub ouvert | Intrusion latérale (N/mm) |
|---|---|---:|---:|---:|---:|
| `open_tub_reference` | carbon_equivalent | 14.530 | 2868.5 | 1.000 | 8060.8 |
| `deep_sill_tunnel` | carbon_equivalent | 27.841 | 4411.0 | 1.538 | 12782.5 |
| `closed_carbon_cell` | carbon_equivalent | 30.909 | 8459.3 | 2.949 | 13826.2 |
| `hybrid_tube_safety_cell` | carbon_equivalent, steel_tube | 40.846 | 15380.5 | 5.362 | 18675.9 |
| `hybrid_multicell_reinforced` | carbon_equivalent, steel_tube | 57.275 | 21710.1 | 7.568 | 26304.6 |
| `all_carbon_multicell_x8` | carbon_equivalent | 69.648 | 19935.8 | 6.950 | 23930.6 |
| `all_carbon_multicell_x10` | carbon_equivalent | 78.079 | 21011.7 | 7.325 | 25238.5 |
| `all_carbon_multicell_x12` | carbon_equivalent | 86.509 | 21833.4 | 7.611 | 26515.9 |

## Sélection numérique

Candidat retenu pour la CAO conceptuelle : `all_carbon_multicell_x10`.

meilleure rigidite torsionnelle specifique parmi les candidats tout CFRP qui passent les portes provisoires

La masse véhicule de 1 200 kg est un objectif de conception. Elle produit une enveloppe préliminaire de 35 303,94 N à 3 g verticaux, sans encore répartir cette charge aux interfaces.

## Portes restant fermées

- `dimensional_scan_correlated`
- `laminate_allowables_from_coupons`
- `composite_shell_mesh_converged`
- `bonded_joint_models_correlated`
- `modal_and_fatigue_cases_passed`
- `roof_crush_case_correlated`
- `front_side_rear_crash_cases_passed`
- `prototype_torsion_test_correlated`
- `professional_engineering_review`
- `road_homologation`
- `track_eligibility`
