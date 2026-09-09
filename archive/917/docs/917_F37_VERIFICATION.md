# Vérification indépendante de la définition de fabrication F37

## Verdict

F37 fournit une **définition fonctionnelle CAO contrôlable**, mais pas une
culasse libérée pour fabrication. Les six familles de formes OCCT générées sont
fermées et valides, leurs STEP sont réimportés sans dérive de volume mesurable,
et chaque fichier STEP/STL est lié au rapport par taille et SHA-256. Le rapport
est lui-même lié au contrat F37 courant et à la peau locale F36-013.

Ces résultats valident la reproductibilité des formes analytiques exportées.
Ils ne valident ni l'échelle du scan, ni l'ajustement sur un moteur Porsche 917,
ni la résistance en fatigue, ni la dissipation thermique corrélée, ni le procédé
LPBF. Toutes les autorisations de fabrication et de démarrage restent donc à
`false`.

## Contrôles exécutés

| Domaine | Résultat vérifié | Limite du contrôle |
| --- | --- | --- |
| Traçabilité | SHA-256 du contrat courant identique à `inputs.contract_sha256`; SHA parent identique à F36-013 | La dimension physique de F36-013 n'est pas confirmée |
| Topologie OCCT | six familles présentes; formes créées et STEP réimportés valides, manifold et fermés | La peau de culasse complète n'est pas un B-Rep monobloc |
| Comptage | porte-axes 1 solide, culbuteurs 4 solides, axes 2 solides, noyau d'huile 1 solide | Un compte de solides ne démontre pas la fonction mécanique |
| Intégrité fichiers | tailles et SHA-256 de tous les STEP/STL conformes au rapport; en-têtes STEP déterministes | Les STL sont des dérivés de visualisation |
| Surépaisseurs | toutes strictement positives; stock radial axe et goujons cohérent avec les diamètres déclarés | Gammes d'usinage et capabilités machine non définies |
| Huile | réseau CAO connexe; 1,968 kPa au cas chaud et 11,912 kPa à l'écran froid; cinq accès déclarés traversent la peau parent selon l'échantillonnage axial | Le contrôle des accès est numérique et unidimensionnel; aucune métrologie, CT ni aucun banc huile |
| Cinématique | quatre cas; rapport lié au rapport CAO; interférences statiques CAO déclarées nulles | Profil de came, contact, flexion et spintron absents |
| Porte-axes | rail H24 × Y34, fenêtre Y36; charge ressort dynamique 1 898 N et enveloppe de magnitude de réaction pivot 2,15× = 4 080,7 N; écran poutre avec FoS chaud 2,46 et flèche 0,1388 mm | La direction réelle de la résultante pivot reste inconnue; pas de contact non linéaire, précharge, thermique ni fatigue corrélée |
| Porte-axes CalculiX | trois maillages jusqu'à 1,25 mm; enveloppe 4 080,7 N appliquée suivant les axes-écran ±18°; p95 = 32,24 MPa, p99 = 50,79 MPa, déplacement = 0,09325 mm; variations finales 0,0345 % et 1,065 %; cible de flèche 0,15 mm passée | Statique linéaire C3D4; maximum local 208,73 MPa dépasse la limite-écran de 200 MPa et n'est pas convergé; direction réelle, galeries/entailles, contact, matériau et encastrement restent idéalisés |
| Fabrication LPBF | rapport relié au STL F37 exact; enveloppe conditionnelle compatible; masse 2,842938 kg | 0,184 cm³ de vide fermé au criblage; 1,259 % sans appui; épaisseur p01 0,75 mm; modèle procédé calibré absent |

## Points bloquants identifiés

1. `whole_head_single_brep` est `false`. Les interfaces analytiques ne sont pas
   fusionnées à une peau de culasse de production traçable.
2. L'absence d'interférence entre le porte-axes et la peau F36 n'est pas
   calculée. Le contrôle `carrier_within_parent_xy_bounds` ne prouve ni l'assise
   ni le jeu tridimensionnel.
3. Le noyau d'huile est connexe et les cinq axes d'accès déclarés croisent la
   peau parent dans le contrôle numérique F37. Ce contrôle par échantillonnage
   de l'axe central ne démontre toutefois ni les tolérances de perçage, ni la
   nettoyabilité, ni l'obturation. Ces fonctions restent à vérifier sur la
   géométrie finale par inspection CT/endoscopique puis physiquement.
4. L'ajustement porte-axes–axe `14 H7/g6` est seulement candidat. Ses limites
   numériques, la dilatation différentielle et le mode de rétention de l'axe ne
   sont pas confirmés.
5. Le jeu radial de 0,05 mm concerne l'enveloppe culbuteur–axe. Il n'est pas un
   empilage de tolérances validé à chaud.
6. Le porte-axes reprend désormais les quatre centres de goujons F36 plutôt que
   des vis M8 flottantes. Le goujon allongé et tout l'empilage de bridage restent
   toutefois non libérés. Les filetages, inserts, sièges et guides restent des
   candidats; données fournisseur, profondeurs d'engagement, traitements et
   couples de serrage manquent encore.
7. Les deux calculs de perte de charge sont cohérents, mais Hagen–Poiseuille et
   Darcy–Weisbach avec `f = 64/Re` sont algébriquement équivalents en régime
   laminaire. Leur accord contrôle l'implémentation; il ne constitue pas une
   validation indépendante du circuit réel.
8. La réaction au pivot n'est pas égale à la seule charge de ressort. L'écran
   retient `F_ressort = 1 460 × 1,3 = 1 898 N`, `F_came = 1,15 × F_ressort`
   et borne sa magnitude par `|R_pivot| <= F_ressort + F_came = 4 080,7 N`.
   Cette borne de magnitude est appliquée suivant l'axe de soupape pour le cas
   numérique, mais sa direction réelle ne peut être obtenue sans profil de came
   et géométrie de contact. Les portes `actual_resultant_direction_complete` et
   `rocker_pivot_resultant_load_complete` restent donc à `false`.
9. La convergence du déplacement et du p95 du CalculiX porte-axes est acquise
   pour cet écran et la flèche fine de 0,09325 mm passe la cible de 0,15 mm. Le
   maximum local augmente toutefois de 199,89 à 208,73 MPa entre les deux
   mailles les plus fines et dépasse la limite-écran de 200 MPa : les galeries,
   perçages et rayons d'entaille n'ont pas de convergence locale démontrée. Les
   portes `nonlinear_contact_complete` et `qualified_material_card` restent à
   `false`; ce résultat ne qualifie ni le contact/précharge, ni la fatigue, ni
   la tenue avec une carte matière à chaud.

## Test reproductible

Depuis la racine du dépôt :

```bash
python3 tests/test_917_f37_manufacturing_definition.py -v
```

Pour vérifier un bundle déplacé hors de `work/` :

```bash
F37_EVIDENCE_DIR=/chemin/vers/cad \
  python3 tests/test_917_f37_manufacturing_definition.py -v
```

Le test est volontairement fail-closed : un rapport absent provoque un skip
explicite, tandis qu'un SHA périmé, un fichier modifié, un compte de solides
inattendu ou une autorisation passée à `true` provoque un échec.

## Conditions minimales avant une impression métal fonctionnelle

- confirmer l'échelle et les références de montage par métrologie externe;
- construire et vérifier le B-Rep complet, y compris les interfaces
  porte-axes–culasse et les débouchés d'huile;
- publier les ajustements et l'empilage de tolérances à froid et à chaud;
- qualifier les cartes matériau/procédé, coupons, orientation, supports,
  traitement thermique, HIP si retenu et usinage final;
- corréler CHT et fatigue thermomécanique avec mesures;
- réaliser CT/CND, épreuve d'huile, banc de flux, spintron puis banc moteur.

Jusqu'à fermeture de ces points, F37 doit rester classée
`analytic_functional_definition_around_scan_mesh_not_whole_head_production_brep`.
