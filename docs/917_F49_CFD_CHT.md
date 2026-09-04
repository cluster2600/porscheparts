# Porsche 917 — F49 CFD/CHT comparative 2V/4V

## Verdict

F49 exécute des écrans CFD statiques et comparables sur les volumes gaz
analytiques F48. Il ne valide ni une culasse, ni une combustion, ni un cycle
moteur. Le solide F43 n'est ni importé ni modifié. En l'absence d'un domaine
solide sain, de contacts et d'une carte matériau à chaud, aucune CHT conjuguée,
température métal ou contrainte thermomécanique n'est calculable.

Le paquet prépare douze cas OpenFOAM 14 : deux variantes, trois grilles et deux
sens d'écoulement. Huit cas coarse/medium ont été exécutés dans l'image F47
linux/amd64 locale sur Kali, puis les quatre cas coarse ont été répétés avec le
profil correctif borné F49. Les deux échappements coarse ont enfin été répétés
sans arrêt résiduel anticipé, soit quatorze tentatives solveur. Les cas fine
restent préparés mais non exécutés.

## Géométrie et traçabilité

- Domaine : volumes gaz F48 obtenus uniquement par fusion de cylindres
  circulaires fonctionnels.
- Variantes : 2V et 4V de la même révision F48.
- Patches : `intake`, `exhaust`, `valve`, `chamber`, `deck`, `bore`, `walls`.
- Échelle : hypothèse héritée `1 scan unit = 1 mm`, non métrologiquement
  certifiée.
- Peau externe F43 : absente du calcul F49 et inchangée.
- Solide de culasse/ailettes : absent du domaine F48.

Le diagnostic p-curve F48 du STEP privé ne sert pas de géométrie de calcul. F49
ne contourne donc pas une erreur B-Rep en la déclarant acceptable : il reste un
criblage gaz analytique séparé.

## Conditions aux limites communes

Le calcul est un RANS compressible transitoire `kOmegaSST`, gaz parfait, avec
`Cp = 1005 J/(kg.K)`, `mu = 1,82e-5 Pa.s` et `Pr = 0,71`. Ces constantes sont
des hypothèses de criblage, pas une carte de propriétés haute température.
L'horizon d'observation est de 5 ms. L'exécution initiale utilisait
`maxCo = 0,5`; le profil correctif coarse utilise `maxCo = 0,1`, un pas initial
de 10 ns, un pas maximal de 2 µs, des schémas advectifs upwind bornés et une
sous-relaxation explicite. Le maximum de Courant observé exact est publié ; le
contrôle admet seulement la tolérance explicite de 0,5 % du régulateur, soit
`Co <= 0,1005`. Tout dépassement supérieur échoue. Une contrainte numérique OpenFOAM borne la
température entre 250 et 1 200 K. Son activation n'étant pas comptée cellule par
cellule, elle interdit à elle seule tout claim de convergence physique : cette
garde n'écrête jamais un résultat afin de le déclarer valide.

| Écran | Source | Pression totale source | Température source | Sortie | Pression statique sortie |
|---|---|---:|---:|---|---:|
| Admission | `intake` | 283,7 kPa abs | 325 K | `deck` | 273,7 kPa abs |
| Échappement | `deck` | 306,0 kPa abs | 950 K | `exhaust` | 296,0 kPa abs |

La différence de 10 kPa est imposée et non prédite. Elle permet de comparer la
conductance des variantes à pression identique. Elle ne constitue ni une perte
de charge moteur ni un point de fonctionnement corrélé. Le patch opposé et les
autres surfaces sont fermés; une température de paroi uniforme de 475 K est
appliquée comme hypothèse F46 non mesurée.

Les enveloppes F47 servent uniquement à comparer a posteriori les ordres de
grandeur. Une enveloppe point par point min/max n'est pas une trajectoire
thermodynamique réalisable et n'est donc pas imposée comme condition limite.

## Chaîne réellement exécutée

Pour chaque cas :

1. vérification SHA-256 du `.msh` local contre le rapport public F48 ;
2. conversion déterministe Gmsh 4.1 vers MSH 2.2 ;
3. `gmshToFoam`, puis mise à l'échelle SI par `transformPoints` ;
4. conversion des seuls patches `noSlip` en type OpenFOAM `wall`, puis audit
   automatique imposant que source et sortie restent `patch` et que
   `omegaWallFunction` n'apparaisse jamais sur un port ;
5. `checkMesh` et conservation du code retour/log ;
6. `foamRun -solver fluid` dans OpenFOAM Foundation 14 ;
7. bilans de masse, énergie totale approximative, pression et température.

Le solveur stationnaire initial a réellement échoué à la deuxième itération
dans la fonction de paroi `omega`; il n'est pas utilisé comme preuve positive.
Le passage transitoire avec contrôle de Courant est la correction numérique
retenue. La première répétition corrective contenait encore un
`PIMPLE.residualControl` : les deux échappements arrêtés avant 5 ms sont donc
conservés comme smokes échoués. Le générateur lié par SHA n'écrit plus ce bloc;
les deux échappements ont été reconstruits et relancés jusqu'à l'horizon fixe.
Les résidus restent des métriques, jamais une autorisation isolée d'arrêt
positif. Les logs et champs bruts restent sur le calculateur et ne sont pas
versionnés.

## Métriques et portes

Le bilan masse est évalué par :

\[
\epsilon_m = 100\,\frac{|\dot m_{source}+\dot m_{sortie}|}
{\max(|\dot m_{source}|,|\dot m_{sortie}|)}.
\]

La conductance de comparaison est `|m_dot| / 10 kPa`. Le bilan énergétique
correctif conserve la convention OpenFOAM `phi > 0` vers l'extérieur. Aux
ports, il somme l'enthalpie totale signée :

\[
\dot E_{ports}=\sum_i \dot m_i\left(C_pT_i+\frac{|U_i|^2}{2}\right).
\]

Le stockage transitoire est évalué par différence finie de
`∫rho*h dV + 1/2∫rho*|U|² dV`. Comme `hConst` emploie par défaut la référence
OpenFOAM `Tref = 298,15 K`, le stockage absolu ajoute exactement
`Cp*Tref*dM/dt`, avec `dM/dt = -(m_source + m_sortie)`, afin que le bilan ne
dépende pas du zéro d'enthalpie. Le résidu contrôlé est donc
`stockage + flux total sortant - wallHeatFlux rapporté`; aucun signe n'est
retourné pour forcer une fermeture. Ce bilan reste qualifié d'approximatif : il
ne remplace pas le flux énergétique conservatif d'un calcul multi-région. Les
seuils sont 1 % pour masse et énergie, 5 % coarse→medium et 5 %
interméthodes. Un seul défaut suffit à maintenir les conclusions fermées. La
comparaison coarse→medium est fermée après l'itération corrective, car ces deux
niveaux n'emploient plus les mêmes contrôles numériques.

Le post-traitement calcule une porte d'arrêt positive combinée : horizon minimal
atteint, plateau du débit sur la fenêtre finale, bilan masse, bilan enthalpie
totale et tous les résidus. Aucun de ces critères pris isolément ne peut arrêter
ou valider un cas, et aucun cas exécuté ne passe la combinaison.

Une seconde méthode indépendante calcule aussi la borne supérieure isentropique
1D d'un orifice de coefficient `Cd = 1`, à partir de la plus petite aire entre
source et sortie. Elle ne contient ni frottement, ni séparation, ni courbure et
ne peut donc pas être traitée comme une deuxième CFD. Le rapport donne le ratio
OpenFOAM/bornage idéal; le gate interméthodes reste fermé.

## Résultats exécutés

| Cas admission | Cellules | `checkMesh`/volume | Débit sortie | Bilan masse | Bilan énergie approx. | Résidu max final |
|---|---:|---|---:|---:|---:|---:|
| 2V coarse correctif | 7 496 | PASS / 0,899 % | 0,19567 kg/s | 2,927 % | 12,43 % | 3,55e-4 |
| 2V medium | 22 063 | PASS / 0,431 % | 0,19274 kg/s | 0,358 % | 42,10 % | 4,60e-4 |
| 4V coarse correctif | 9 660 | FAIL volume / 1,504 % | 0,22785 kg/s | 2,322 % | 2,85 % | 2,94e-4 |
| 4V medium | 25 951 | PASS / 0,767 % | 0,23172 kg/s | 2,651 % | 36,91 % | 1,35e-3 |

Le solveur retourne zéro pour ces quatre admissions, mais aucun cas ne passe
simultanément maillage, masse, énergie, Courant et résidus. À contrôle correctif
coarse, le débit 4V est supérieur de 16,45 % au 2V; à contrôle initial medium,
l'écart brut est 20,22 %. Ces valeurs ne forment pas une étude d'indépendance de
grille et ne sont pas un gain moteur validé. Les ratios medium
OpenFOAM/bornage idéal valent respectivement 0,778 et 0,831.

Les échappements medium initiaux ont échoué dans `omegaWallFunction`. Les deux
premiers correctifs coarse ont retourné zéro, mais se sont arrêtés à 2,2 et
1,8 ms par le critère résiduel prématuré; ils restent explicitement échoués.
Les répétitions sans arrêt résiduel ont franchi ces anciens points, puis leur pas
de temps s'est effondré :

| Rerun échappement coarse | Temps final | `dt` minimal | `Co` maximal | Verdict |
|---|---:|---:|---:|---|
| 2V | 2,212681 ms | 2,01e-39 s | 0,120051 | `TIME_STEP_COLLAPSE_FAIL` |
| 4V | 1,915030 ms | 6,78e-47 s | 0,121396 | `TIME_STEP_COLLAPSE_FAIL` |

Ils ont été interrompus lorsque l'avancement physique est devenu numériquement
nul. Cela prouve une instabilité numérique de ces cas, pas une cause physique
dans une culasse réelle. Aucun débit échappement 2V/4V n'est donc comparé. Les
quatre binaires AATE retournent zéro en mode aide; aucun cas moteur AATE n'est
exécuté.

Le plan correctif borné est de localiser d'abord la première divergence de
`U`, `h`, `k` ou `omega`, vérifier les valeurs aux patches et le sens de flux,
remplacer le démarrage uniforme par une initialisation issue d'un calcul froid
conservatif, puis tester une rampe de température source et une formulation
turbulente de paroi adaptée. Chaque changement formera un nouveau contrat
numérique et les cas repartiront de zéro. Une machine Vast ne rendrait pas ce
modèle stable automatiquement : elle ne sera envisagée qu'après un smoke local
qui atteint 5 ms sans effondrement, sans relâcher les portes.

## AATE/ICengines

L'image contient les préprocesseurs AATE/ICengines à la révision
`c0f75f953d67cd325d28d1300672d14288f22934`. Aucun exécutable
`ICEEngineFoam` n'existe et aucun alias n'est créé.

Un cas moteur AATE honnête ne peut pas être généré depuis F48 : les surfaces
séparées de piston et soupapes mobiles, la loi mesurée de levée en angle
vilebrequin, la cinématique piston/bielle et la topologie de maillage dynamique
manquent. Le smoke des binaires ne compte donc pas comme deuxième méthode CFD.
Le seuil interméthodes reste fermé.

## Ce qui manque pour une CHT défendable

- B-Rep solide sans défaut de topologie et lié à la peau F43 inchangée ;
- volumes solides séparés, contacts sièges/guides/bougie et résistances de
  contact ;
- carte `k(T), Cp(T), rho(T)` du lot LPBF qualifié entre 260 et 350 °C ;
- flux de combustion corrélé ou cycle transitoire conservatif ;
- convection externe air/ailettes avec carénage et courbe ventilateur mesurée ;
- trois grilles résolues, indépendance de grille et deuxième méthode
  indépendante ;
- corrélation banc de flux, thermocouples et banc moteur.

## Reproduction locale

Les maillages F48 ne sont pas committés. Sur la machine qui les détient :

```bash
python3 twins/reference-917-engine/source/build_cfd_cases_f49.py \
  --project-root . \
  --domain-root /chemin/vers/domains-v2 \
  --output work/917-f49-cfd-cht \
  --correction twins/reference-917-engine/f49-cfd-cht-corrective-coarse.json
```

Le runner doit ensuite être lancé dans l'image F47 avec
`/opt/openfoam14/etc/bashrc` sourcé. Il refuse de démarrer si `WM_PROJECT_DIR`
ou `configDict` ne sont pas résolus :

```bash
source /opt/openfoam14/etc/bashrc
for variant in 2V 4V; do
  for screen in intake exhaust; do
    python3 twins/reference-917-engine/source/run_cfd_cases_f49.py \
      --project-root . \
      --work-root work/917-f49-cfd-cht \
      --levels coarse --variants "$variant" --screens "$screen" \
      --report-name "corrective-${variant}-coarse-${screen}.json" \
      --correction twins/reference-917-engine/f49-cfd-cht-corrective-coarse.json
  done
done
```

La publication expurgée agrège les huit tentatives initiales et les quatre
correctives avec :

```bash
python3 twins/reference-917-engine/source/publish_cfd_results_f49.py \
  --project-root . \
  --work-root work/917-f49-cfd-cht
```

Les deux PNG publiés sont des graphes issus des valeurs numériques réelles. Ce
ne sont ni des rendus conceptuels ni des champs CFD inventés.

## Option Vast non lancée

L'offre lue seule `39351028` (RTX PRO 6000 WS 97,9 GB, 32 cœurs,
2,00729 USD/h) n'a pas été louée. Si le filtre transfert nul était relâché, le
contrat borne 4,0 GB pour l'image, 0,1 GB d'entrées et 1,0 GB de résultats. En
facturant conservativement les 5,1 GB au tarif transfert maximal de
0,004 USD/GB et avec un TTL de 8 h, le plafond serait 16,07872 USD, sous le
budget F46 de 23 USD. Le lancement reste interdit tant qu'un digest registry
linux/amd64 et les cas exacts ne sont pas vérifiés. Si cette phase est un jour
autorisée, l'horizon physique sera adaptatif jusqu'à stationnarité, borné à
20 ms, avec fenêtre moyenne finale. L'arrêt positif exigera simultanément le
plateau du débit, les bilans masse et enthalpie totale sous leurs seuils de 1 %
inchangés, et tous les résidus sous leurs cibles. Le smoke local de 5 ms ne peut
pas remplir cette fonction et aucun seuil ne sera relâché pour le faire passer.
