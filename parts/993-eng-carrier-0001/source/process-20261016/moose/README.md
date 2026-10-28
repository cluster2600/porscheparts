# Moteur thermo-mécanique incrémental — état du 16 octobre 2026

Le binaire officiel MOOSE fonctionne sur Kali1 sans installation système. Le témoin analytique vérifie la naissance sans contrainte dans une configuration déjà déplacée, la conservation de l'histoire plastique, l'équilibre global à chaque incrément et le débridage dans le même état. Ce résultat rend le moteur exploitable ; il ne constitue pas encore une prédiction de déformation du support moteur.

## Distribution et exécution

Distribution officielle `idaholab/moose@sha256:47fc6c5bff5e86869e7c467f999e9585ece13af9ffd1f580fef5369728a93452`, architecture amd64, source MOOSE `167ee97da204df5e8643695e18b9b28910f0014b`, LGPL-2.1. Binaire SHA256 `c49e2c368799d80edf9ff858dd8960bd22f5430f48229ab49dcc0afd27afcc5b`. Téléchargement effectué : 1,917 Go compressés, 5,743 Go déployés sur Kali1, 121 s. Le reçu est dans `work/carrier-process-20261016/moose-runtime-20261016/receipt.json`. Aucun achat de calcul.

Le runtime existant est `/home/lolman/carrier-moose-20261016/runtime/rootfs`. Le lanceur portable est copié sur Kali1 dans `/home/lolman/carrier-moose-20261016/run_moose_portable.py`. Il impose 2 CPU, 8 GiB RAM, zéro swap, 256 tâches, 720 s, rootfs en lecture seule et réseau absent. Il conserve les SHA des entrées, du binaire, du lanceur et du journal, avant et après l'exécution. Chaque dossier/label doit être neuf.

```sh
python3 run_moose.py /path/to/runtime/rootfs /path/to/new/plastic native -- -i birth-cycle-release.i
python3 run_moose.py /path/to/runtime/rootfs /path/to/new/elastic native -- -i birth-cycle-release.i elastic-control.i
python3 assess_witness.py /path/to/new
```

Placer les deux fichiers `.i` dans chaque sous-dossier `plastic` et `elastic`, et `contract.json` dans le dossier parent. `elastic-control.i` est une surcharge : elle doit être passée après le fichier principal. `fetch_runtime.py NEW_RUNTIME_DIRECTORY` reconstruit le runtime épinglé sur Linux amd64 ; il vérifie chaque couche, applique les whiteouts et refuse les chemins sortant de la racine et les périphériques. Le lanceur utilise `bwrap` et `systemd-run --user` déjà disponibles sur Kali1.

## Résultat du témoin

Reçu portable complet : `work/carrier-process-20261016/moose-witness-007/assessment.json`, **26 contrôles réussis**. Barre 10 × 1 × 1 mm, E=200000 MPa, ν=0,3, α=10⁻⁵/K et plasticité J2 idéale à 200 MPa : ce sont les données synthétiques du témoin, pas des propriétés du titane. Déplacement imposé avant naissance à droite : 0,005 mm. Cycle prescrit 300 → 600 → 300 K.

| État | σxx plastique (MPa) | εp,xx | Déplacement droit (mm) |
| --- | ---: | ---: | ---: |
| Naissance à t=1 | ≈0 | 0 | 0,005 |
| Chauffe à t=2 | −200 | −0,002 | 0,005 |
| Refroidi, encore bridé à t=4 | +200 | −0,001 | 0,005 |
| Libéré à t=6 | ≈0 | −0,001 | −0,005 |

Le retrait par rapport à la configuration de naissance vaut −0,010 mm ; le contre-calcul élastique donne 0. Les six incréments de chacun des deux calculs convergent avec une norme finale du résidu inférieure à 10⁻⁹. Tolérances gelées avant calcul : 10⁻⁶ mm, 10⁻³ MPa et 10⁻⁶ de déformation plastique. La température est imposée dans ce témoin ; aucune équation de chaleur n'y est résolue. Les post-traitements thermiques à t=0 sont non exécutés et ne doivent pas être interprétés comme 0 K.

Les essais antérieurs restent archivés : `003` perdait l'histoire à l'activation, corrigée par `reinitialize_subdomains = '2'` pour initialiser seulement les éléments nouvellement actifs ; `005/006` utilisaient la surcharge élastique seule et ont été refusés par le parseur. Aucune tolérance analytique n'a été changée. `004` et `007` passent le même contrat.

## Chaleur réellement résolue

`thermomech_step01.i` est la copie inchangée de l'exemple officiel MOOSE, source ci-dessous. Le dossier `work/carrier-process-20261016/moose-thermal-official-001` contient son exécution couplée native et une surcharge qui ajoute seulement des observations : conduction transitoire spatiale et thermoélasticité en déformations finies, 100 quadrilatères, cinq pas convergés. À t=5 : Tmin=300 K, Tmax=357,209367746 K et ux,max=0,135209770337 dans les unités synthétiques de l'exemple. Ce contrôle démontre l'intégration chaleur/mécanique ; sa source volumique uniforme ne représente pas un cycle laser LPBF.

L'exemple MALAMUTE cylindre DED a été vérifié mais le binaire officiel MOOSE ne contient pas son matériau personnalisé `ADFunctionPathGaussianHeatSource`. Le refus natif est conservé dans `malamute-cylinder-001`. Aucun transfert silencieux vers une autre source thermique n'a été fait.

## Sources primaires

- [Distribution officielle](https://mooseframework.inl.gov/getting_started/installation/docker.html).
- [Licence épinglée](https://github.com/idaholab/moose/blob/167ee97da204df5e8643695e18b9b28910f0014b/LICENSE), copie `LICENSE.moose`.
- [Activation et réinitialisation des matériaux](https://github.com/idaholab/moose/blob/167ee97da204df5e8643695e18b9b28910f0014b/framework/src/meshmodifiers/ElementSubdomainModifierBase.C).
- [Incrément de déformation avec état ancien](https://github.com/idaholab/moose/blob/167ee97da204df5e8643695e18b9b28910f0014b/modules/solid_mechanics/src/materials/ADComputeIncrementalStrain.C).
- [Retour plastique dans le calcul de contrainte AD](https://github.com/idaholab/moose/blob/167ee97da204df5e8643695e18b9b28910f0014b/modules/solid_mechanics/src/materials/ADComputeMultipleInelasticStress.C).
- [État plastique et limite élastique en fonction de T](https://github.com/idaholab/moose/blob/167ee97da204df5e8643695e18b9b28910f0014b/modules/solid_mechanics/src/materials/IsotropicPlasticityStressUpdate.C).
- [Commande temporelle du débridage](https://github.com/idaholab/moose/blob/167ee97da204df5e8643695e18b9b28910f0014b/test/tests/controls/time_periods/bcs/bcs.i).
- [Exemple chaleur/mécanique inchangé](https://github.com/idaholab/moose/blob/167ee97da204df5e8643695e18b9b28910f0014b/modules/combined/tutorials/introduction/thermal_mechanical/thermomech_step01.i).

Repères dans les sources épinglées : `ElementSubdomainModifierBase.C` [lignes669–735](https://github.com/idaholab/moose/blob/167ee97da204df5e8643695e18b9b28910f0014b/framework/src/meshmodifiers/ElementSubdomainModifierBase.C#L669-L735) sélectionne uniquement les éléments déplacés entre sous-domaines ; [lignes888–915](https://github.com/idaholab/moose/blob/167ee97da204df5e8643695e18b9b28910f0014b/framework/src/meshmodifiers/ElementSubdomainModifierBase.C#L888-L915) initialise leurs propriétés. `ADComputeIncrementalStrain.C` [lignes90–104](https://github.com/idaholab/moose/blob/167ee97da204df5e8643695e18b9b28910f0014b/modules/solid_mechanics/src/materials/ADComputeIncrementalStrain.C#L90-L104) soustrait le gradient ancien ; `ADComputeMultipleInelasticStress.C` [lignes163–203](https://github.com/idaholab/moose/blob/167ee97da204df5e8643695e18b9b28910f0014b/modules/solid_mechanics/src/materials/ADComputeMultipleInelasticStress.C#L163-L203) conserve les états ancien et incrémental. Le témoin natif complète cette lecture en contrôlant les résidus globaux.
