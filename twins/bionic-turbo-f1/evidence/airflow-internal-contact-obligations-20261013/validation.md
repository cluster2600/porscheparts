# Validation et limites

Primaire code 0 en 4,582642 s ; lecteur indépendant code 0 en 6,059296 s. Les nouveaux prédicats d'incidence, tous les tétraèdres orientés et leurs cellules, ainsi que toutes les intersections de sous-complexes concordent. Aucun ancien polynôme ni parcours géométrique n'a été recalculé. Les 19 manifestes et 520 entrées héritées sont ancrés à la base Git ; les documents, programmes et références figés avant application sont inchangés.

Six références par programme avant application : deux tétraèdres joints correctement, doublon rejeté, orientation incohérente rejetée, multiplicité trois rejetée, carré triangulé cohérent et arête inversée rejetée. Aucun refus ni correction pendant l'application au turbo. Les tests généraux ont commencé après les deux lecteurs. Ces durées ne sont pas des benchmarks CFD.

Ran 109 tests in 15.473s
OK (skipped=1)
Ran 3992 tests in 216.384s
FAILED (failures=2, errors=4, skipped=178)

Les six labels hors turbo sont identiques à PR254 selon test-comparison.json. Le code global make check reste 2 ; ne pas présenter tous les tests locaux comme réussis.

La preuve rédigée utilise la multiplicité locale de chaînes positives pour passer des intérieurs aux strates de dimension inférieure. Le contrôle indépendant porte sur ses hypothèses finies et leur jointure aux certificats hérités ; il n'est pas un prouveur automatique de la démonstration. La référence Lipman éclaire l'inversion simpliciale, mais son hypothèse de variété n'est pas déduite d'Euler ou du seul comptage d'incidences.

Conclusion limitée à la réalisation partagée PR241 sur l'enveloppe fermée des 153 boîtes. Ni égalité des premiers moments/centres, ni transfert à une autre triangulation native. Les deux indécisions de déterminants restent présentes. Les conversions writePrecision 16, les accumulations flottantes, la configuration et le binaire restent ouverts. Aucun candidat, natif, solveur, CFD, débit, puissance ou calibration. Docker et le volume source sont préservés ; aucun cas 084 rejoué.
