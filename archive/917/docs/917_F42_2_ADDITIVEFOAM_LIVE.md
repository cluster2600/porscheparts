# Porsche 917 — F42.2, AdditiveFOAM exécuté sur deux hôtes

## Verdict

La matrice F42 a été réellement exécutée sur deux hôtes x86 indépendants avec
les révisions OpenFOAM et AdditiveFOAM verrouillées. Chaque exécution couvre
`27` points nominaux et les `6` raffinements nécessaires aux trois comparaisons
grossier/nominal/fin. Le rapport inter-hôtes vérifie les `33` couples de
résultats métrique par métrique.

Cette preuve établit la reproductibilité du calcul de coupon LPBF. Elle ne
simule pas la distorsion de la culasse complète, ne génère ni supports ni
fichier BLT signé, et ne qualifie pas l'AlSi10Mg à chaud. L'autorisation
d'impression et l'autorisation de démarrage restent donc à `false`.

| Contrôle | Hôte A | Hôte B | Verdict croisé |
|---|---:|---:|---:|
| exécutions présentes | 33/33 | 33/33 | PASS |
| cas nominaux | 27/27 | 27/27 | PASS |
| plage T99 nominale | 329,300–392,168 K | 329,300–392,168 K | PASS |
| saturations à 3 300 K | 0 | 0 | PASS |
| convergences nominal/fin | 3/3 | 3/3 | PASS |
| cas reproduits dans les tolérances | — | — | 33/33 |

L'écart absolu inter-hôtes maximal sur T99 vaut
`3,0517578125e-5 K`; les autres maxima comparés sont identiques à la précision
publiée. Ce résultat extrêmement proche démontre la déterminisme du cas et de
son post-traitement, pas l'exactitude physique du modèle.

![Résultats AdditiveFOAM — hôte A](../twins/reference-917-engine/evidence/f42-2-additivefoam-live/917-head-f42-2-results-host-a.png)

![Résultats AdditiveFOAM — hôte B](../twins/reference-917-engine/evidence/f42-2-additivefoam-live/917-head-f42-2-results-host-b.png)

![Comparaison inter-hôtes](../twins/reference-917-engine/evidence/f42-2-additivefoam-live/917-head-f42-2-cross-host.png)

## Portée des mesures

Les températures maximale et P99 sont extraites exclusivement des VTK
volumiques `layer1_*.vtk`. Les exports `POLYDATA` de patches sont exclus. Les
dimensions longueur/largeur/profondeur proviennent du moniteur
`meltPoolDimensions` pendant le calcul. Les VTK étant des instantanés après
refroidissement, un volume liquide final nul n'annule pas l'observation en
ligne du bain thermique.

Les seuils de comparaison sont de `0,5 %` ou `1 K` pour les températures,
`1 %` pour les grandeurs de bain et `1 %` pour le nombre de Courant, avec un
seuil absolu adapté à chaque grandeur. Une valeur absente, non finie ou un jeu
de cas différent ferme la gate de reproductibilité.

## Limites qui restent bloquantes

- la reconstruction B-Rep monobloc échoue encore au contrôle de round-trip et
  au maillage Gmsh ;
- aucune carte fournisseur complète à chaud, aucun coupon, CT/CND ou fatigue
  thermomécanique corrélée ne sont disponibles ;
- les supports réels, le projet slicer, le contrôle recoater et le fichier
  machine signé n'existent pas ;
- la répétition sur deux hôtes du même solveur ne remplace pas une seconde
  méthode physique indépendante ;
- aucune de ces simulations n'est un banc de flux ou un banc moteur.

Les résultats et leurs SHA-256 sont publiés dans
`twins/reference-917-engine/evidence/f42-2-additivefoam-live/`.
