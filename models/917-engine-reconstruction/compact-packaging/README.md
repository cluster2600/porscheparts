# Carters longitudinaux et suralimentation plus compacte

Cette étape applique les observations des [trois vidéos](../museum-reference-analysis.md)
au moteur 4V biturbo, après la fusion de la PR #196. Les vidéos donnent les
formes générales ; aucune cote n'est extraite de leurs images.

## Construction native sur le Mac

Le [programme C#](Bank.cs) emploie PicoGK 2.3, les champs implicites `Sdf.Vox`,
les boîtes arrondies, les poutres `Lattice.AddBeam`, les courbes de Bézier et les
booléens sur VDB natifs. Les solides sont exportés à 1 et 0,5 mm. Le
[générateur](run.py) conserve les sources réellement utilisées dans chaque
dossier d'exécution avant de lancer le noyau. Les sorties restent sous `work/`
et une exécution refuse d'écraser un dossier existant.

- Deux carters longitudinaux remplacent les douze capots individuels. Le toit
  comporte deux volumes arrondis autour des lignes de cames, reliés par une peau
  continue ; les cavités sont retranchées après les nervures.
- Deux plaques d'adaptation présentent six ouvertures alignées sur les culasses
  candidates par banc. Les centres et poses proviennent de l'assemblage hérité,
  et non d'une estimation sur les vues éclatées du musée.
- Les branches sont projetées sur la peau extérieure avant voxelisation pour
  conserver une liaison continue entre les racines et le sommet. Leur forme
  n'est pas le résultat d'une analyse de contraintes.
- Quatorze positions de vis par banc reprennent le prototype natif de vis déjà
  généré, avec des bossages qui dégagent leurs têtes du collet. Les alésages,
  les poses et un espace candidat pour une rondelle sont
  représentés ; filetage, portées, rondelles, précharge et retenue restent à définir.
- Les champs natifs du carter de distribution et les enveloppes des roues sont
  réservés autour des nouveaux carters. La transition avant du banc négatif est
  arrêtée au plan candidat X = 389,37 mm. Son raccord et son étanchéité avec le
  carter de distribution restent ouverts. La dernière ouverture de la plaque
  rejoint son bord avant : le périmètre de joint n'est pas fermé à cet endroit.
  Une transition de carter doit résoudre ce défaut avant une enceinte fonctionnelle.
- Les deux conduits de suralimentation conservent leurs extrémités et leurs
  rayons d'entrée/sortie ; leur grand tronçon passe de Z = 335 à 270 mm. Le
  maximum de la ligne centrale passe de 335 à 295 mm, à cause du port final
  conservé. La longueur de ligne centrale diminue d'environ 3,05 % et 2,86 %
  suivant le banc. Ces gains ne démontrent ni débit accru ni perte de charge réduite.

Les culasses, les soupapes, les turbos et leurs poses sont protégés par les
hashes de la livraison précédente et par une comparaison des enregistrements
d'assemblage. La distribution actuelle reste en bout : l'architecture centrale
repérée dans les références demande encore des sources mécaniques indépendantes.

## Comparaison de matière et contrôles

Les parois nominales de 3 mm sont comparées à un témoin de 5 mm, aux mêmes
enveloppes extérieures, nervures, fixations, réserves et interfaces candidates.
Les volumes proviennent des triangles natifs audités. La comparaison porte sur
la matière du carter ; elle ne classe pas les variantes par résistance ou fatigue.
Les plaques d'adaptation ne sont pas amincies dans cette comparaison.

Le [reçu du 13 octobre](execution-20261013.json) décrit l'exécution locale sur
le Mac ARM64 : **157 prototypes / 1 419 occurrences**, 12 culasses, 48 soupapes
et 39 prototypes de turbo conservés. Les 1 387 enregistrements hérités après
retrait des anciens capots conservent leurs poses et métadonnées.

| Carter | Volume à 3 mm, mm³ | Témoin à 5 mm, mm³ | Réduction de volume |
|---|---:|---:|---:|
| Banc positif | 1 013 150,52 | 1 644 654,24 | 38,40 % |
| Banc négatif | 950 896,00 | 1 545 564,05 | 38,48 % |

Les 640 groupes de contrôle passent : 520 groupes sont disjoints par boîtes
englobantes et 120 intersections booléennes de triangles donnent zéro volume.
Les 12 contrôles de raccordement passent aussi. Les sorties inchangées reprennent
leur témoin topologique lié aux mêmes STL ; les autres reçoivent un nouvel audit.
Les contacts d'assemblage sont tous recalculés dans cette étape.

![Assemblage à surfaces opaques](engine-surfaces.png)

![Carters et plaques d'adaptation](bank-inspection-0.5.png)

L'audit réutilise le témoin indépendant du dépôt : coordonnées finies, volume
positif, fermeture, orientation, absence de faces répétées et une seule
composante de surface par solide. Seules les faces exactement nulles peuvent
être retirées, sans déplacer les sommets ou supprimer une petite composante.
Les deux réserves de cames par banc sont exportées séparément, chacune connexe.

Les nouveaux carters et plaques sont comparés à toutes les familles héritées
aux poses froides enregistrées. Les boîtes englobantes transformées servent
uniquement à exclure les paires disjointes ; les autres paires passent par un
booléen de triangles. Les cames ont aussi une réserve conservatrice de rotation.
Les contacts des conduits modifiés et les contrôles de raccordement sont refaits.
Les paires inchangées, le cycle complet soupape–piston et les effets à chaud ne
sont pas revérifiés ici. La conservation des triangles et des poses est contrôlée
lors de l'export GLB.

Le premier essai de carters a été rejeté : fragments détachés et petites surfaces
résiduelles près des jonctions de champs. La correction distingue les niveaux du
toit et de sa cavité et reprend la transition avant. Un essai suivant a arrêté le
générateur hérité de conduits, qui n'acceptait que 0,5 mm ; la nouvelle étape
génère les conduits dans son propre programme à deux résolutions sans modifier
cette source héritée. Un essai a ensuite été interrompu avant assemblage pour
projeter les nervures sur la peau et ajouter le témoin de paroi. Les fichiers,
reçus et sources de ces essais restent dans les diagnostics privés.
La première paroi de 3 mm a aussi été rejetée : le corps arrondi ne rejoignait
plus la bride. Un collet natif raccorde ces deux régions avant la soustraction
de la cavité ; aucune composante détachée n'est supprimée du maillage.
L'essai suivant passe les audits de surface mais échoue à l'assemblage : environ
1 106,67 mm³ de recouvrement avec les chapeaux de paliers et 854,9 mm³ avec les
têtes de vis par banc. La cavité centrale est rehaussée pour les chapeaux
existants et des bossages déplacent les portées candidates des têtes de vis.
Le contrôle suivant dégage les chapeaux mais détecte encore environ 996 mm³
de recouvrement entre les têtes de vis et la paroi par banc. Les vis passent
sur des brides élargies, à l'extérieur de la paroi, sans changer leur prototype.
Un dernier contrôle localise encore environ 16,6 mm³ par banc sur quatre
racines de nervures au contact des têtes de vis. Les racines sont déplacées
longitudinalement pour dégager la visserie ; les parois restent continues.

L'option `--audit-from work/ancienne-execution` peut reprendre un audit de pièce
si les STL nouvellement générés ont les mêmes SHA-256 que les sorties déjà
auditées. Le VDB nouveau est contrôlé contre son propre reçu de génération ;
aucune équivalence des VDB n'est déduite de la reprise du témoin STL.
Le témoin des faces orientées est revérifié ; toute pièce modifiée
reçoit un nouvel audit complet. Les reçus distinguent les témoins repris des
contrôles refaits. Cette reprise ne concerne pas les contacts d'assemblage.

## Reproduction

```sh
PYTHONPATH=work/917-head-clearance-20261012/runtime \
work/917-picogk-20261010/qa-venv/bin/python \
models/917-engine-reconstruction/compact-packaging/run.py \
  --previous /chemin/vers/la/livraison/917-mechanical-detail-20261012 \
  --output work/917-compact-new-run \
  --dotnet /chemin/vers/dotnet

PYTHONPATH=work/917-solid-surfaces-20261011/runtime \
work/917-picogk-20261010/qa-venv/bin/python \
models/917-engine-reconstruction/compact-packaging/render.py \
work/917-compact-new-run
```

Les interfaces mesurées et leur qualification restent ouvertes dans le
[contrat](interface-contract.json). Alliage, procédé, dépoudrage, état de surface,
usinage, lubrification, étanchéité, tenue mécanique et validation professionnelle
ne sont pas établis. Ces fichiers sont une étude reproductible, sans autorisation
de fabrication pour service moteur ni de démarrage.
