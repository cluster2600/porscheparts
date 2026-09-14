# Porsche 917 — audit LPBF et structure scan-only F39

F39 ne crée aucune cote de culasse. Il audite le maillage exact F37, lié au
SHA-256 `3c7159d47be2cd4632ae823a272f73514c784b0659207c002e34c9dc7e49fbbb`,
et réutilise les résultats F38 sans les promouvoir en validation. L'échelle
absolue, les interfaces avec le moteur et la CAO de production restent
inconnues.

Le [rapport F39](../twins/reference-917-engine/evidence/f39-lpbf-structural/f39-lpbf-scan-only-report.json)
et son [image de synthèse](../twins/reference-917-engine/evidence/f39-lpbf-structural/f39-lpbf-scan-only-audit.png)
concluent donc **NON IMPRIMABLE / NON AUTORISÉ**.

## Carte d'épaisseur exhaustive

VTK construit un localisateur spatial sur les `857 330` triangles du scan. Pour
chaque triangle, le script part de son centroïde, se décale vers l'intérieur et
cherche la première intersection avec la surface opposée suivant la normale de
facette. Les `857 330` cordes ont été calculées et résolues : la couverture du
domaine discret est donc de 100 %.

Cette exhaustivité a une définition précise : elle couvre **toutes les
facettes**, mais ne prouve pas une épaisseur continue, une distance à l'axe
médian, une tolérance dimensionnelle ou un contrôle CT. Sur l'hypothèse non
confirmée `1 unité scan = 1 mm`, la carte donne :

| Indicateur | Résultat F39 |
|---|---:|
| minimum | 0,000410 mm |
| p01 | 0,707107 mm |
| p05 | 2,250000 mm |
| médiane | 19,445436 mm |
| aire résolue sous le seuil-écran F38 hérité de 1,5 mm | 3,0950 % |

Le seuil de 1,5 mm est repris de F38 comme filtre de criblage ; ce n'est pas une
nouvelle cote F39. La carte complète compressée reste locale, car elle est
dérivée du scan. Son empreinte est enregistrée dans le rapport.

## Cavités et dépoudrage

La surface est rasterisée de façon déterministe avec
`vtkPolyDataToImageStencil`, puis le vide extérieur est propagé avec une
connectivité à six voisins. Les composantes qui ne rejoignent pas le bord de la
grille sont conservées comme cavités candidates.

| Pas voxel conditionnel | Composantes fermées | Volume fermé conditionnel |
|---:|---:|---:|
| 2,0 mm | 31 | 576,0 mm³ |
| 1,5 mm | 53 | 445,5 mm³ |
| 1,0 mm | 49 | 172,0 mm³ |

L'étude ne converge pas : la variation entre les deux dernières résolutions est
de 159,0 %. Elle constitue une alerte de reconstruction, pas une mesure de
cavité. Chaque composante persistante devra être reliée à une ouverture de
service, puis contrôlée par CT et par un essai physique de dépoudrage. Aucun
diamètre minimal d'évacuation n'est inventé sans distribution granulométrique,
recette machine et échelle qualifiées.

## Orientation, supports et surépaisseurs

Dix-huit orientations sont comparées avec toutes les normales de triangles. Le
score additionne aire projetée descendante et hauteur de colonne. La candidate
`scan_y_down` entre conditionnellement dans l'enveloppe héritée
`250 × 250 × 325 mm`, avec 5,6393 % d'aire de faces descendantes. Ce calcul ne
génère pas de supports, ne tranche pas les couches et ne simule pas le contact
support–pièce.

Les zones à reprendre sont recensées — deck, poches de sièges, alésages de
guides, siège/filetage de bougie, alésages du porte-axes, brides et fixations —
mais toutes les surépaisseurs numériques restent `null`. Il faut d'abord
reconstruire les surfaces fonctionnelles, choisir les datums et fermer la chaîne
de tolérances.

## Simulation d'impression

Le runtime a recherché des solveurs dédiés de couche activée et de déformation
additive. Aucun solveur LPBF dédié ni jeu calibré machine–matière–stratégie de
balayage n'était disponible. La simulation inherent-strain n'a donc pas été
exécutée. Le retrait libre ou le calcul historique de plaque bloquée ne sont pas
présentés comme simulation de procédé.

## Correction structurelle du porte-axes

Le calcul F38 reste le point de départ : `137,030 MPa` au maximum brut,
`31,628 MPa` au p99 et `0,06018 mm` de déplacement au maillage fin. Le p99 est
stable, mais le maximum brut varie encore de `16,54 %`, au-dessus de la cible de
10 %. La carte matière, le contact et les efforts réels ne sont pas qualifiés.

Le prochain modèle doit :

1. conserver exactement le même résultant sur les trois maillages et le
   distribuer sur les surfaces de contact de palier, plutôt que sur des couronnes
   de nœuds ;
2. séparer le porte-axes, les deux axes, les quatre culbuteurs et l'interface de
   culasse ;
3. employer des contacts surface–surface, les jeux mesurés et la précharge réelle
   des fixations ;
4. raffiner indépendamment les contacts et raccords courbes ;
5. suivre maximum brut, p99, déplacement, énergie de déformation et p99 de
   pression de contact ;
6. corriger le rayon ou la transition physique si le maximum reste singulier,
   puis répéter toute la séquence.

Les efforts résultants, jeux, précharges et corrections géométriques restent
volontairement `null` : ils ne sont pas mesurables sur la seule peau du scan.

## Reproduction

Le script requiert Python, NumPy, SciPy, Matplotlib et VTK :

```bash
python3 twins/reference-917-engine/source/f39-lpbf-scan-only-audit.py \
  --contract twins/reference-917-engine/f39-lpbf-scan-only-contract.json \
  --head work/917-scan-conforming-f37/head-mesh-proof/917-head-f37-printable-proof.local.stl \
  --f37-lpbf-report work/917-scan-conforming-f37/lpbf-exact/lpbf-printability-report.json \
  --f38-lpbf-report twins/reference-917-engine/evidence/f38-brep-lpbf/f38-brep-lpbf-report.json \
  --f38-carrier-cad-report work/917-rocker-carrier-f38/cad/f38-rocker-carrier-cad-report.json \
  --f38-carrier-report work/917-rocker-carrier-f38/calculix/f38-carrier-calculix-report.json \
  --output work/917-lpbf-structural-f39 \
  --publish-dir twins/reference-917-engine/evidence/f39-lpbf-structural
```

Jusqu'à reconstruction CAO, simulation procédé calibrée, carte matière à chaud,
CT/CMM/CND, épreuve d'étanchéité, essais de dépoudrage et revue professionnelle,
`metal_print_authorized` et `engine_start_authorized` restent à `false`.
