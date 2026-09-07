# F58 — bilan d'énergie du coupon AdditiveFOAM

## Résultat du 7 septembre 2026

Deux exécutions réelles sur Kali atteignent 120 µs, avec retours solveur zéro :
1 200 pas de 100 ns (59 s murales) et 2 400 pas de 50 ns (90 s murales).
Le maximum spatial de température est enregistré à **chaque pas**. Les deux
cas restent plafonnés à 3 300 K : ce diagnostic n'est pas une correction
physique du procédé ni une autorisation d'impression.

Le [reçu public F58 en JSON](../twins/reference-917-engine/evidence/f58-energy-diagnostic/energy-summary.json)
contient les deux pas temporels, les énergies et résidus recalculés, les
empreintes de provenance et les limites du diagnostic. Il reprend exactement
les résultats du reçu privé de contre-vérification ; aucun chemin privé,
maillage, coordonnée ni journal brut n'y figure.

| Énergie cumulée sur 120 µs | Pas 100 ns (mJ) | Pas 50 ns (mJ) |
|---|---:|---:|
| Apport laser absorbé | 31,55219 | 31,55755 |
| Stockage sensible discret | 28,33106 | 28,34062 |
| Stockage latent de fusion | 3,69231 | 3,69240 |
| Flux thermique net entrant aux frontières | 3,80816 | 3,80693 |
| Transport advectif sortant | 0 | 0 |
| Puits artificiel du limiteur | 3,33700 | 3,33147 |

L'intégrale de la valeur absolue du résidu, divisée par l'énergie laser,
vaut respectivement `3,77e-7` et `7,67e-7`. Elle ne permet pas aux erreurs de
signes opposés de s'annuler. Les écarts entre pas sont de 0,034 % sur le
stockage sensible, 0,0025 % sur le latent et 0,166 % sur le puits numérique.
Deux pas ne déterminent pas un ordre de convergence ni une convergence
spatiale. Les pics écrêtés ne constituent pas une preuve de convergence de T.

Le limiteur retire **10,58 % / 10,56 %** de l'énergie laser absorbée. Il reste
donc une intervention énergétique non physique importante dans ce calcul,
même lorsque l'équation discrète se ferme très précisément. Diminuer le pas
temporel ne supprime pas cette intervention.

Une seconde lecture indépendante des deux journaux recalcule désormais le
résidu par `fsum(sensible, latent, -diffusion, -laser, advection, limiteur)`.
La colonne résiduelle du solveur est seulement comparée à ce résultat ; elle
n'alimente plus les intégrales. Pour les 16 chiffres significatifs du journal,
la tolérance de cohérence d'écriture est explicitement
`1e-12 W + 5e-15 * somme(abs(termes en W))`. Ce n'est pas un seuil physique
d'acceptation. Une incohérence supérieure entraîne un refus du rapport.
Sur les 1 200 / 2 400 lignes réelles, les écarts maximaux valent
`1,58e-13 W` / `1,71e-13 W` : toutes les lignes sont cohérentes. Les chiffres
arrondis du tableau et du résidu restent inchangés après réintégration.

## Ce qui est réellement intégré

Le solveur copié conserve l'équation Euler explicite du commit ORNL
`9c05c5eb54db03faa342b14b0806efe740de8c44`. Le diagnostic intègre ses termes
avant/après chaque résolution :

`stockage_sensible + stockage_latent = diffusion_frontières + laser - advection - limiteur`.

- sensible : somme de `rho * Cp_ancien * (T_nouveau - T_ancien) * V / dt` ;
- latent : somme de `-rho * Lf * (alpha_solide_nouveau - alpha_solide_ancien) * V / dt` ;
- diffusion : intégrale volumique du **même opérateur conservatif**
  `fvc::laplacian(kappa,T)` que le solveur ; son intégrale donne le flux net
  aux frontières, avec les conditions thermiques existantes ;
- laser : intégrale du champ source réel `sources.qDot()` ;
- advection : intégrale de `rho*Cp*fvc::div(phi,T)` ;
- limiteur : intégrale du terme implicite `A*(T-Tmax)/dt` de la dernière
  correction thermique, séparée des pertes physiques.

Le stockage sensible est un terme de l'équation discrétisée utilisant le Cp
retardé du solveur. Ce n'est **ni** la pseudo-enthalpie `rho*Cp*T`, **ni** une
nouvelle loi calorique étalonnée. La fermeture mesurée est donc celle de
l'équation effectivement résolue, pas une validation thermodynamique externe.
Le flux net aux frontières est ici positif. Le champ initial est à 293,15 K
alors que les températures de référence aux frontières sont à 300 K ; ces
entrées héritées ont été conservées, pas harmonisées silencieusement.

Sources primaires vérifiées :
[assemblage thermique ORNL](https://github.com/ORNL/AdditiveFOAM/blob/9c05c5eb54db03faa342b14b0806efe740de8c44/applications/solvers/additiveFoam/thermo/thermoScheme.H),
[fusion et pénalisation ORNL](https://github.com/ORNL/AdditiveFOAM/blob/9c05c5eb54db03faa342b14b0806efe740de8c44/applications/solvers/additiveFoam/thermo/TEqn.H),
[mise à jour des propriétés ORNL](https://github.com/ORNL/AdditiveFOAM/blob/9c05c5eb54db03faa342b14b0806efe740de8c44/applications/solvers/additiveFoam/updateProperties.H).

Contrôle direct des fichiers effectivement compilés : `additiveFoam.C` appelle
`updateProperties.H` à la ligne 97, puis inclut `TEqn.H` à la ligne 136,
avant le calcul du stockage ligne 141. Dans `updateProperties.H`, les lignes
22–24 affectent Cp. La lecture complète de `TEqn.H` et de ses deux inclusions
`thermoScheme.H` et `thermoSource.H` montre que Cp est seulement lu : les
corrections modifient T, la fraction solide, dFdT et T0, pas Cp. Le correcteur
de frontière `mixedTemperature::updateCoeffs` (lignes 149–175) lit kappa et
actualise les coefficients de T, sans modifier Cp. Le stockage après TEqn
utilise donc bien le même Cp que son assemblage ; aucune copie corrective
de Cp et aucun nouveau calcul n'étaient nécessaires pour ces journaux.
Les empreintes de `thermoSource.H` et `updateProperties.H` sont désormais
ajoutées aux verrous du préparateur, respectivement
`efab43bb4cd3f05b29eb326a2b2ead2508de43ff705bdf546ab7d58295a57b4f` et
`98e6e85e1a8cd2c10ee385864280a88ff6649d45e51148eeee47fd55b136da2a`.

## Périmètre et fidélité de la paire

Le cas source est la couche 0 plafonnée du diagnostic F55. Il s'agit du
coupon rectangulaire AlSi10Mg dérivé de F50, **pas du STEP d'une culasse**,
pas de l'ancien ovale, pas du nouveau module M64 et pas d'une carte CP1.
Le maillage compte 57 600 cellules et ne change pas pendant les deux calculs.
Le modèle Kelly, le faisceau, la carte matériau, les frontières, le maillage,
`nOuterCorrectors=0` et `Tmax=3300` restent inchangés. Le `controlDict` source
F55 contient bien `adjustTimeStep yes` (ligne 48) et `deltaT 1e-07` (ligne 28).
Son SHA-256 `339fc71cc01b94df5ff746cf5082ea6a80eae06cc6c6b14de53f18bcc4e57c05`
correspond au manifeste établi avant les calculs. F58 remplace ce pas adaptatif
par `adjustTimeStep no` dans les deux membres de la comparaison.
Entre eux, seule la valeur `deltaT` diffère dans `system/controlDict`.

Le moteur diagnostique refuse un maillage changeant, un schéma implicite ou
un pas adaptatif. Il mesure le latent mais n'ajoute aucun modèle de
vaporisation, de recul de vapeur ni de convection du bain fondu. Aucun résultat
de fatigue, de résistance de culasse ou de distorsion de construction complète
ne découle de cette paire.

## Reproductibilité et conservation

Le nouveau préparateur `additive_energy_diagnostic_f58.py` vérifie les cinq
empreintes des sources du solveur, copie dans un nouveau dossier privé et
crée les variantes `dt` et `dt_half`. Il refuse d'écraser un dossier existant.
Les sources originales et les anciens résultats F55 ne sont pas modifiés.
Le premier essai de compilation a échoué avant tout calcul sur l'appel de
précision du journal ; il reste conservé. Le second a compilé et exécuté les
deux calculs. Chacun avait un arrêt externe à 300 s ; tous les conteneurs
diagnostiques sont maintenant arrêtés et supprimés. Aucune location Vast.

- image locale : `a233511bef9b4fbf0653ca94258061d61b3fccbd6b4e3ef6d71c669d70de1c17` ;
- binaire instrumenté : `b13dacc72146e8df5ded9d20c4b20e7a21051dd21244f9598d441e81c871364d` ;
- carte AlSi10Mg : `65d464489b95dd60bffa61a30caee53e1ec951c4bd53dfed0d7d1ea0d435e3ea` ;
- rapport privé : `afabeb547951c603cfed34bf6f92e17c08bf2a67a73572aedcbe4dc30962ea6a` ;
- reçu privé de contre-vérification, distinct sans écraser le premier :
  `d8bbb8fd72db1f6e191614ed325e71cd6bd2f7ebf0dd6efe32463df25a4caf1d` ;
- journal pas 100 ns : `fd95a18b51c3e252f4e92d2625e62fe21b82b5ac66abbf6abc14877a5cf1a44c` ;
- journal pas 50 ns : `27f3733c41e8e4d448c94b6e3979a776164f43c7b01732f7bfc449b125d8f1bf`.

Le rapport complet, les entrées, champs et journaux restent privés. Les tests
ciblés vérifient les termes énergétiques, les échantillons manquants/non finis,
le contrat dt/2, l'absence d'écrasement et l'identité des entrées physiques.
Le reçu de contre-vérification distingue `time_series_complete` du code de
sortie : la seule lecture d'un journal ne vérifie pas un retour processus.
Ses champs `solver_exit_code=null` et `solver_exit_status_verified=false`
ne remplacent pas les retours zéro observés lors des deux exécutions initiales.
Le reçu public conserve cette distinction : il n'invente pas de code de sortie
dans les champs issus du parseur et indique que les observations d'exécution
proviennent d'une preuve séparée. Il ne contient pas de reçu machine autonome
des retours processus. Les métadonnées ajoutées sont des empreintes vérifiées,
les pas verrouillés de la paire et les rapports d'énergie calculés à partir
des valeurs sources, sans nouvelle simulation.

```sh
python3 -m unittest discover -s tests -p test_917_additive_energy_diagnostic_f58.py -v
```

## Décision suivante

Le diagnostic ne justifie pas une nouvelle location pour balayer aveuglément
puissance et absorption. Il faut maintenant examiner le modèle d'absorption,
le profil/profondeur de source et les pertes physiques du coupon avec données
de calibration cohérentes ; F55 avait déjà montré la sensibilité à l'absorption.
Ne pas sélectionner 0,35 comme vérité et ne pas supprimer le plafond pour
obtenir une gate verte. Toute future correction devra conserver ce bilan,
les pics à chaque pas et la comparaison temporelle, puis vérifier la
convergence spatiale. Fabrication et démarrage restent non autorisés.
