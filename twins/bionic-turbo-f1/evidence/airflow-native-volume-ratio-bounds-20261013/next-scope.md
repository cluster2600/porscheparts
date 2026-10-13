# Suite contrôlée

Les rapports de volumes sont désormais couverts dans le domaine publié.
Ne pas refaire cette application ni les anciens parcours PR238–245.
Aucun prochain candidat préparé; aucune sélection du paramètre v.

Prochaine priorité : poids de faces et skewness avec centres NATIFS. La source
polyMeshTools.C copiée sans modification montre pour les poids
min(dOwn,dNei)/(dOwn+dNei+VSMALL), distances projetées ABSOLUES, initialisation
1 sur les frontières non couplées et branche couplée distincte. Le seuil
d'appel est 0.05. Prescrire domaines, incidences, opérations et lecteur avant
calcul; les valeurs absolues ne remplacent pas les autres critères signés.

La skewness utilise plusieurs ROOTVSMALL et une normalisation par maximum
des projections vers les sommets; les branches interne et frontière diffèrent.
Lire également la définition exacte de normalised avant application frontière.
Ne pas remplacer le centre natif par celui de l'éventail de preuve, ni omettre
les max, normes ou termes additifs. Aucun de ces contrôles n'est acquis ici.

L'orthogonalité avec son additif, la décomposition native, les contacts internes
de dimension inférieure, le bilan flottant, les conversions writePrecision 16
et le futur binaire restent distincts. Conserver toutes les 153 boîtes, les
deux indécisions et les 113 boîtes non admises aux prédicats nécessaires passants.
Ni grille, subdivision, centres libres, aplanissement ou seuil assoupli.

Préserver stations, ruptures, fermetures, interfaces et sources immuables.
Aucun natif/solveur avant admission; les critères synthétiques ne qualifient
pas les surfaces physiques. Couches/repos/convergence/stabilité/indépendance
maillage-temps/CFD/calibration restent distincts. Ne jamais relancer, prolonger,
raccourcir ou régler 084. Aucun débit/puissance/calibration validé.

Avant les divisions de skewness, distinguer positivité exacte d'un très petit
terme additif et borne inférieure arrondie à zéro dans un noyau dyadique.
Ne pas diviser un intervalle contenant zéro, supprimer l'additif ou déclarer
la branche qualifiée sans justification d'encadrement appropriée.
