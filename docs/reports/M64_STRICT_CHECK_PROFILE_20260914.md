# M64 — profil du contrôle strict et réconciliation volumique (14/09/2026)

Suite du [pilote CAD agent](M64_CAD_AGENT_PILOT_20260912.md) : R0,1 en
`strict-approximation-v1` a atteint la limite de 300 s (sortie 137) après
l'écriture du BRep, alors que `default` passait en ~5,5 s.

## Conclusion courte

**La phase lente n'est pas reproduite sans la géométrie privée.** Sur les
témoins publics, aucune phase du contrôle ne dépasse 1 s de calcul. Aucune
option plus rapide n'est proposée. La seule substitution candidate
(BRepCheck non exact) est **rejetée** : elle ne rend pas le même résultat.
Rien n'est promu. Le contour maître et `build_local_port_junction_fillet.py`
sont inchangés.

## Machine et limites

Mesures sur **machine locale WSL2** : i7-1260P, 16 cœurs logiques, 15 GiB,
OCP 7.9.3.1, Python 3.14.7 via `uv`. **Ce n'est pas Kali** : pas de SSH, pas
de conteneur 2 CPU / 4 GiB. Les temps ne sont pas comparables à ceux du pilote.
Le négatif d'admission privé et le scan étaient indisponibles.

## Outil

`twins/m64-cylinder-head/source/profile_strict_check.py` rejoue une à une
les phases qui suivent la construction dans `run()`. Chaque phase tourne dans
un sous-processus séparé, avec délai externe et `RLIMIT_CPU`, sans proxy dans
l'environnement. Chaque sous-processus relit la forme : `read_seconds` est
mesuré à part de `phase_seconds`. La sortie est un JSON.

Phases : `read`, `brepcheck_exact` (identique à `CAD.valid`),
`brepcheck_default`, `tolerances` (BRep_Tool + ShapeAnalysis),
`bop_full` (identique à `ports.bop_check`), `bop_only_<option>` pour chacune
des 5 options, `bop_none`, `write_reread`, `bbox_optimal`,
`volume_adaptive_1e-11` (identique à `adaptive_volume`), `volume_adaptive_1e-9`
et `volume_gauss_default`.

Un délai dépassé ou une phase manquante donne `incomplete`, jamais `pass`.
L'échantillonnage de tangence n'est pas rejoué : il demande l'historique
`maker.Generated`, absent d'un BRep relu.

À lancer sur Kali avec le négatif et le candidat strict privés :

```sh
python3 twins/m64-cylinder-head/source/profile_strict_check.py \
  --shape source=/prive/negatif.brep \
  --shape strict=/prive/intake-junction-prototype.brep \
  --timeout 300 --scratch /prive/scratch --output /prive/profil.json
```

## Mesures (temps de calcul de la phase, hors relecture)

| Témoin | BRepCheck exact | BOP complet | dont SelfInter | Volume 1e-11 | Relecture + volume |
|---|---:|---:|---:|---:|---:|
| Analytique R0,1 default | 0,002 s | 0,006 s | 0,004 s | 0,007 s | 0,006 s |
| Analytique R0,1 strict | 0,002 s | 0,004 s | 0,004 s | 0,005 s | 0,006 s |
| NURBS R0,1 source | 0,014 s | 0,149 s | 0,141 s | 0,007 s | 0,008 s |
| NURBS R0,1 default | 0,030 s | 0,899 s | 0,837 s | 0,224 s | 0,229 s |
| NURBS R0,1 strict | 0,083 s | 0,861 s | 0,947 s | 0,150 s | 0,159 s |
| STEP v1 `closed` | 0,021 s | 0,858 s | 1,015 s | 0,056 s | 0,061 s |
| STEP v2 `closed` | 0,026 s | 0,888 s | 0,841 s | 0,063 s | 0,054 s |
| STEP v2 `simultaneous_100pct` | 0,020 s | 0,658 s | 0,644 s | 0,052 s | 0,060 s |

La relecture STEP ou BRep coûte environ 0,5 à 0,9 s par sous-processus, dont
l'import d'OCP. Les quatre autres options BOP restent sous 0,08 s. Le temps de
construction du congé est de 0,001 s sur le témoin analytique, 0,017 s en
default et 0,027 s en strict sur le témoin NURBS.

Sur le témoin NURBS, le mode strict coûte 2,8 fois plus en BRepCheck exact
(0,083 s contre 0,030 s). Le volume adaptatif, lui, est plus rapide
(0,150 s contre 0,224 s). Il est plausible que ces écarts croissent avec la
complexité du vrai négatif, mais ce n'est **pas mesuré**. Les phases candidates
à surveiller sur Kali sont `bop_only_SelfInterMode`, `brepcheck_exact` et
`volume_adaptive_1e-11`.

## Réconciliation volumique

| Forme | Volume adaptatif 1e-11 | Candidat − source | Relu − mémoire | Gauss par défaut |
|---|---:|---:|---:|---:|
| Analytique source | 3926,990817 | 0 | 0 | 3926,990817 |
| Analytique default / strict | 3927,058537 | +0,067720 | 0 | 3927,058537 |
| NURBS source | 3926,990825 | 0 | 0 | **3934,283687** |
| NURBS default | 3927,058546 | +0,067721 | 0 | 3934,149045 |
| NURBS strict | 3927,058545 | +0,067720 | 0 | 3934,149039 |
| STEP v1/v2 `closed` (12 solides) | 45492,212291 | — | 7,3e-12 | 45492,212291 |
| STEP v2 `simultaneous_100pct` | 45492,212291 | — | 1,5e-11 | 45492,212292 |

Explication des écarts :

- **Congé.** Le candidat gagne +0,0677 unité³. Ce signe est attendu : le congé
  est concave sur un négatif de gaz, il ajoute de la matière au domaine.
  Default et strict diffèrent de 4,6e-7 sur NURBS, et de 0 sur le témoin
  analytique, où le mode strict n'a aucun effet.
- **Relecture.** La relecture BRep est exacte (0) sur les témoins. Sur les STEP,
  l'écart est de l'ordre de 1e-11, au niveau de l'arrondi flottant.
- **Méthode d'intégration.** Le volume GProp sans `eps` (Gauss d'ordre fixe) se
  trompe de **+7,29 unité³ (0,19 %)** dès qu'une face est B-spline. Il n'est
  exact que sur les surfaces analytiques. Ne jamais comparer une valeur Gauss à
  une valeur adaptative : c'est une cause possible de l'« incohérence de
  volume » du pilote, **non vérifiée** sur les rapports privés.
- **Orientation.** Aucun solide n'a de volume négatif ; toutes les orientations
  sont FORWARD.
- **Solides multiples.** Chaque STEP public contient 12 solides disjoints (des
  paires de volumes identiques). Le volume du composé est leur somme.
  Le contrôle mono-solide les rejette, comme attendu. `closed` porte en plus
  20 `BOPAlgo_SelfIntersect` entre solides ; `simultaneous_100pct` n'en a aucun.

## Substitution rapide : rejetée

Rien n'étant lent, la seule option testée est BRepCheck sans méthode exacte.
Sur le candidat NURBS default, **exact = invalide** et **non exact = valide**.
Le verdict global reste identique ici, parce que le BOP rejette déjà
(`GeomAbs_C0` ×2, `InvalidCurveOnSurface` ×1). Mais le résultat n'est pas le
même : la substitution **affaiblirait** le contrôle. Elle n'est donc pas
proposée.

Sur le candidat NURBS strict, le BOP compte `GeomAbs_C0` ×5 et
`SelfIntersect` ×1. Ce témoin est synthétique et hors conception : ce n'est
pas un jugement sur le mode strict de la culasse.

## Tests

`tests/test_m64_strict_check_profile.py` contient 10 tests :

- verdict fail-closed sur délai dépassé ou phase manquante, y compris un vrai
  délai de 0,05 s sur un STEP ;
- calculs de réconciliation ;
- verdict identique sur les témoins analytique, NURBS et STEP ;
- non-équivalence du BRepCheck non exact, verrouillée par un test ;
- écart supérieur à 0,1 % du volume Gauss.

Avec les 5 tests existants de `test_local_port_junction_fillet.py`, **15 tests
passent** en local :

```sh
uv run --no-project --with cadquery --with pytest python -m unittest \
  tests.test_m64_strict_check_profile tests.test_local_port_junction_fillet -v
```
