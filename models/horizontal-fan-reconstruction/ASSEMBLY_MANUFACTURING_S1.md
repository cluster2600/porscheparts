# Assemblage S1 et préparation de fabrication V2

L'assemblage d'étude S1 et le brut V2 avec surépaisseurs sont maintenant
éditables et contrôlés comme géométrie. Leur fabrication fonctionnelle reste
bloquée par les interfaces physiques et la qualification du procédé.
L'identité935/993, l'échelle275 mm et les neuf pales restent non vérifiées.
Ce dossier prolonge les calculs existants ; aucune amélioration de débit,
durée de vie ou aptitude au montage n'est déduite de ces nouvelles enveloppes.

[**Assemblage STEP S1**](results/assembly/S1/S1-assembly.step) ·
[Contrôles CAO](results/assembly/S1/geometry-report.json) ·
[Paramètres modifiables](parameters/assembly-study-S1.json) ·
[Nomenclature conditionnelle](results/assembly/S1-review-packet.json) ·
[Brut STEP avec surépaisseurs](results/lpbf/V2-stock-scenario/V2-stock-scenario.step) ·
[OpenUSD S1](omniverse/S1-layout.usda)

![Projections de la CAO réelle S1](results/assembly/S1-layout.png)

## Ce qui a été dessiné et ce qui reste à mesurer

La géométrie V2 d'origine est importée sans déplacement ni modification de ses
solides. Le nouveau plénum est une coque conique ouverte : profondeur101,75 mm,
rayon supérieur141,90 mm, rayon inférieur165 mm et épaisseur nominale2,5 mm,
tous choisis pour l'étude. Une exclusion centrale de60,5 mm est réservée
symboliquement au renvoi d'angle ; aucun tube central ni passage de culasse
mesuré n'est prétendu. Le passage latéral de rayon12 mm évite l'enveloppe de
l'arbre. Le contrôle BRep ne trouve aucune intersection volumique entre cette
coque et l'assemblage V2 d'origine.

Deux poulies sont représentées par leurs enveloppes de diamètre primitif80 mm,
entraxe180 mm et largeur20 mm. L'arbre d'entrée possède une prolongation
d'enveloppe ; la courroie suit le chemin primitif de poulies égales. Deux
barres20×15 mm représentent des stocks de support. Ces positions définissent
une variante de packaging ; elles ne sont pas des axes, perçages, portées ou
fixations relevés sur un moteur. Dentures, profils de courroie, roulements,
retenues, étanchéité du passage, collecteur de distribution et raccords des
culasses restent à définir. Les enveloppes du renvoi d'angle ne sont pas des
engrenages fabricables.

Les sept groupes contiennent19 solides. Tous les BRep sont valides et ont un
volume positif après export/réimport STEP. La coque conique présente une
différence volumique relative d'environ6,17×10⁻⁷ ; la borne de représentation
retenue pour S1 est10⁻⁶, distincte des contrôles historiques et sans valeur
de tolérance de fabrication. Aucune vérification de packaging moteur réel,
de frottement, de fixation ou de transmission sous charge n'est close.

Le [contrat indépendant](parameters/assembly-interface-contract.json) définit
neuf interfaces,52 caractéristiques à renseigner et les chemins d'efforts :
rotor→arbre→roulements→carter→support→moteur ; entraînement moteur→courroie→
poulie→arbre→roulements→renvoi d'angle→rotor ; carter/plénum→supports→moteur.
La [fiche de mesures vierge](results/assembly/S1-interface-measurement-sheet.csv)
demande valeurs, unités, incertitude, instrument/calibration, datums, référence,
preuve et revue. La variante catalogue exacte, les limites de fabrication et
la revue de mise en service manquent aussi :55 éléments non clos. Une sortie
CAO ne fournit pas ses propres preuves de mesure. Le
[contrôle d'admission](source/assembly_interface_gate.py) rejette toute
promotion fonctionnelle incompatible avec ce contrat.

## Dimensionnement conditionnel de l'entraînement et du plénum

Pour le scénario choisi,5 Nm à6000 rpm représentent3,142 kW. Une poulie80 mm
donne25,13 m/s de vitesse de courroie et125 N de différence de tension.
Avec200 N de prétension par brin, les tensions simplifiées deviennent262,5 /
137,5 N et la charge radiale de poulies égales400 N. Ces formules ignorent
raideur, tension dynamique, pertes, excitation, angle effectif et données
fabricant : aucun modèle de courroie, roulement ou arbre n'est sélectionné.
Le ratio idéal vaut1, la longueur primitive de courroie ouverte611,33 mm ;
la longueur commerciale et le tendeur restent à choisir après mesure.

L'aire annulaire disponible supposée en bas vaut0,07049 m². Le débit ponctuel
D2 non convergé de1,156 m³/s donnerait16,40 m/s à travers cette aire. Ce calcul
de continuité ne prédit ni répartition vers les culasses, ni pertes de charge,
ni efficacité du plénum. Les six débits de refroidissement et les résistances
des chemins installés restent des données à établir. S1 n'est pas le domaine
CFD D2 : sa coque n'a pas encore été maillée ou simulée.

## Brut de rotor et scénario LPBF

Le rotor [V2 original](V2-rotor.step) conserve sa géométrie finale supposée.
Le [brut d'étude](results/lpbf/V2-stock-scenario/V2-stock-scenario.step) ajoute
0,5 mm radial au bore et0,5 mm sur chaque face de moyeu. Les autres surfaces
restent identiques. Le bore du brut devient26,5 mm pour un bore final supposé
de27,5 mm ; aucun ajustement physique n'est établi. Le brut forme un solide
connecté valide, vérifié après réimport STEP.

Le volume passe de265377,43 à269123,98 mm³ ; la surépaisseur représente3746,55 mm³.
À la densité indicative2700 kg/m³, la masse passe de0,7165 à0,7266 kg. Ni cette
densité ni les0,5 mm ne sont des propriétés ou allowances approuvées pour un
lot AlSi10Mg. Les déformations de fabrication antérieures R0/V5 ne justifient
pas ces stocks et ne se transfèrent pas automatiquement à V2.

Le [screening du brut tessellé](results/lpbf/V2-stock-orientation-screen.json)
compare six orientations, sans support réel ou recette laser. À plat, le brut
mesure environ274,20×274,98×53,17 mm. Avec10 mm de marge par côté il ne rentre
pas dans le scénario conservateur250×250×300 mm ; il rentre nominalement dans
les enveloppes BLT de référence400/450×300×400 mm. Sur chant avec rotation
diagonale, sa boîte vaut212,77×215,22×274,98 mm : elle rentre dans les trois
scénarios avec la marge choisie. Le nombre géométrique de couches à50 µm passe
de1064 à5500. Ce n'est ni un temps de fabrication, ni une épaisseur qualifiée.
Le volume du STL diffère de0,189 % du BRep ; c'est un contrôle de représentation.
Les proxies de colonnes de supports peuvent se chevaucher et ne constituent
pas une géométrie de support imprimable.

Les variantes de machine restent des références. La version exacte S400,
le volume utile, le matériau/lot, le traitement et la recette doivent être
confirmés ; voir la [revue de fabrication et ses sources primaires](MANUFACTURING_REVIEW.md).
Les12 simulations élastiques antérieures évaluent une contraction supposée,
avec supports idéalisés, et ne simulent pas fusion, histoire thermique,
plasticité, scan laser ou porosité. Aucun nouveau solveur de procédé V2 n'a
été exécuté pour ce dossier.

## Gamme proposée pour la revue technique

| Étape | Entrée et preuve attendues | État |
| --- | --- | --- |
| Définition | Variante exacte, interfaces mesurées, datums et dessin tolérancé ; besoins de débit, régime et fatigue | Manquants |
| Matière/process | Lot AlSi10Mg et état final, machine/recette qualifiés, propriétés directionnelles et dépendantes de température | Candidats, non qualifiés |
| Préparation | Brut révisé, supports/plateau, zones de contact et accès de dépose, orientation, témoins représentatifs | Brut d'étude et screening disponibles |
| Calibration | Éprouvettes de distorsion et matériau, build indépendant de validation du modèle process | Aucune donnée physique |
| Construction | Fichier machine signé, journal d'atmosphère et paramètres, traçabilité matière/build | Aucune fabrication autorisée |
| Traitement/découpe | Séquence approuvée, enregistrement four, mesures avant/après libération, dépose accessible | À définir avec l'atelier |
| Usinage | Reprise bore/faces dans datums approuvés, accès et bridage, ébavurage sans réduction critique des racines | Stocks et accès d'étude seulement |
| Inspection | Dimensions/runout, CT ou méthode qualifiée, défauts/surface, matière et coupons ; limites fixées par l'ingénieur | Aucune acceptation physique |
| Équilibrage/service | Plans de correction, modal précontraint/gyroscopie, fatigue, essais de rotation contenus et revue professionnelle | Plan à approuver, aucun essai réel |

Le plénum et les stocks de supports ont des routes conventionnelles possibles ;
l'entraînement exige une définition mécanique et des composants adaptés.
La [nomenclature](results/assembly/S1-review-packet.json) laisse les quantités,
masses et fournisseurs inconnus à `null`, au lieu de transformer les
enveloppes visuelles en références de commande.

## OpenUSD et reproduction

L'[asset S1](omniverse/S1-layout.usda) sépare les19 solides sous leurs groupes,
en mètres, axe+Z, sans déformation. Les couleurs identifient les rôles visuels.
Il relie paramètres, contrat d'interfaces, CAO, diagnostic CFD et présent dossier.
Toutes les coordonnées issues des STL sont contrôlées contre leur stockage
float32. Les [contrôles OpenUSD](omniverse/S1-layout-validation.json) couvrent
composition, topologie, unités et liaisons de matériaux ; la règle shader Sdr
reste bloquée par les ressources absentes du runtime disponible. Aucun GPU,
Omniverse RTX, SimReady qualifié ou jumeau physique validé n'est revendiqué.
Le [workflow NVIDIA CAD→SimReady](https://github.com/NVIDIA/skills/tree/main/skills/omniverse-cad-to-simready)
requiert une chaîne GPU/Content Agents qui n'est pas disponible ici ; elle
n'a pas été installée.

Avec les bibliothèques CAO et OpenUSD déjà présentes, depuis ce dossier,
dans de nouveaux répertoires privés :

```sh
"$CAD_PYTHON" source/build_assembly_study.py . "$PRIVATE_FAN_WORKSPACE/S1"
"$CAD_PYTHON" source/prepare_v2_manufacturing_stock.py . "$PRIVATE_FAN_WORKSPACE/V2-stock"
python3 source/screen_v2_stock.py "$PRIVATE_FAN_WORKSPACE/V2-stock" "$PRIVATE_FAN_WORKSPACE/V2-stock-screen.json"
```

L'[exporteur OpenUSD/rendu](source/export_s1_layout.py) exige le runtime USD ;
la [génération du paquet de revue](source/build_s1_review_packet.py) exige
seulement les rapports publiés. Aucun de ces outils ne lance un solveur,
n'installe un logiciel ou ne contacte un atelier.
[Diagnostic D3 et budget de calcul indépendant](D3_ESTABLISHMENT_DIAGNOSTIC.md).
