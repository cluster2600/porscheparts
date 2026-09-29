# Mécanique, acquisition et optique

## Cahier des charges du scan

Périmètre : bandeau d'origine **démonté**, ses accessoires de fixation, joints,
porte-lampes et connecteurs présents sur la variante retenue ; relever aussi les
interfaces côté voiture par mesures indépendantes, avec son autorisation. Le
prestataire doit confirmer l'accès physique à cette pièce exacte, son volume de
scan et sa maîtrise des plastiques brillants/translucides. Une compétence scan de
bâtiment ne suffit pas. Ne pas reconstituer une pièce nominale depuis des photos.

1. État initial photographié : référence, marquages optiques, fissures, déformations,
   réparations ; confidentialité des identifiants du véhicule. Ne pas polir ni
   pulvériser sans accord ; proposer un matifiant réversible, son nettoyage et
   l'effet de son épaisseur sur l'incertitude.
2. Référentiel A/B/C établi sur les interfaces fonctionnelles, coordonnées en mm,
   orientation voiture documentée ; scanner extérieur, dos, portées, bossages,
   clips et bords. Distinguer surface directement observée et trou interpolé.
3. Mesures indépendantes aux instruments adaptés : entraxes, diamètres, plans,
   épaisseurs accessibles, angles, profondeur disponible, compressions de joint,
   emboîtements ; répétabilité de plusieurs poses. Aucune valeur nominale inventée.
4. Livrer acquisition **native/brute**, nuage PLY/XYZ/E57 selon appareil, maillage
   OBJ/STL propre à l'échelle, transformations, photos autorisées, certificat ou
   état d'étalonnage, paramètres et rapport de couverture/incertitude. Les données
   restent en stockage privé contrôlé ; le dépôt n'accueille que références de
   preuve et droits validés, jamais les scans bruts.
5. La CAO mécanique est réalisée par le porteur : natif paramétrique et STEP AP242
   si possible, historique, surfaces/rayons, datums et plans d'interface. Une
   reconstruction fournisseur n'est qu'une option distincte, pas le mandat de base.
   **STL = maillage ; STEP = échange géométrique, pas preuve de paramétricité.**
6. Réception CAO : rapport écart scan/CAO signé (distribution et maxima par zone,
   pas seulement moyenne globale), détails non acquis marqués inconnus ; contrôle
   des interfaces par mesure, puis gabarit et montage sur la voiture cible.

[measurements.csv](measurements.csv) est la fiche à compléter. Les colonnes vides
signifient « inconnu ». Avant acquisition, convenir d'une incertitude de mesure
sensiblement inférieure à la tolérance fonctionnelle (objectif de travail :
≤ un tiers, à négocier). Ne pas confondre résolution du scanner, précision,
répétabilité, tolérance de pièce et capacité du procédé. Les tolérances de contours,
entraxes, clips, jeu périphérique, planéité, joint et retrait ne seront fixées
qu'après analyse fonctionnelle ; aucune cote de la 993 n'est engagée ici.

## Taille des LED, pas et résolution

Une LED rouge Kingbright 0402 mesure 1,0 × 0,5 mm [S01]. Son boîtier n'inclut pas
l'espacement nécessaire pour soudure, routage, drivers et réparation. La préférence
≤1 mm est donc plausible en monochrome ; le boîtier RGB ≤1 mm reste **à sourcer et
à qualifier**, sans référence validée dans cette étude. Un pixel RGB comporte trois
canaux, même si le composant est unique.

Comparaison normalisée pour une **surface abstraite de 100 × 100 mm**, sans lien
avec les dimensions inconnues du bandeau. Calcul = floor(100/p)² ; indices par
rapport au pas 4 mm. Les indices représentent des pixels/canaux, pas un prix.

| Pas mm | Pixels sur cette surface | Indice pixels | Canaux mono / RGB | Choix exploratoire |
|---|---:|---:|---:|---|
| 1 | 10 000 | 16 | 10 000 / 30 000 | Très dense ; PCB, placement, rendement et chaleur à chiffrer, pas retenu au départ |
| 1,5 | 4 356 | 6,97 | 4 356 / 13 068 | Intermédiaire dense, devis fournisseur indispensable |
| 2 | 2 500 | 4 | 2 500 / 7 500 | Détail fin ; module rigide du commerce possible |
| 2,5 | 1 600 | 2,56 | 1 600 / 4 800 | Premier comparatif RGB disponible |
| 4 | 625 | 1 | 625 / 1 875 | Point de départ mono économique à comparer |

Pour la surface utile mesurée W×H : Nx=floor(W/p), Ny=floor(H/p), puis retrancher
les zones masquées/fonctionnelles ; ne pas appliquer directement à un rectangle
englobant courbe. Texte 5×7 avec une colonne d'espacement : N caractères visibles
≈floor(Nx/6), hauteur ≥7 pixels plus marges. Valider à distance réelle, pas sur écran.

| Technologie | Disponibilité vérifiée | Atouts | Limites / verdict provisoire |
|---|---|---|---|
| Mono rouge discret ≤1 mm | LED [S01], PCB sur mesure à développer | Spectre adapté au rouge, un canal/pixel, drivers plus simples | Beaucoup de joints ; efficacité et multiplexage à mesurer ; premier coupon recommandé |
| Matrice RGB HUB75 P2,5 64×32 | Waveshare [S02] : module 160×80 mm, 5 V/2,5 A, ≤12 W annoncé | Coupon achetable sans grand développement, import animations | Dimensions **du module**, pas de la 993 ; plat/intérieur, courbure et température non qualifiées ; boîtier LED ≤1 mm non établi |
| Matrice RGB P2 64×64 | Référence listée par Waveshare [S03] | Comparatif de densité | Profondeur, fixation et puissance ; pas 2 mm ≠ LED 1 mm |
| RGB PCB personnalisé | à deviser | Géométrie utile et zones indépendantes | Trois canaux/pixel, consommation, rendement de fabrication ; façade rouge détruit la fidélité couleur |
| OLED mono/RGB | Newhaven 1,5 pouces 128×128 [S04], exemple de petit écran | Pixels fins, noir et épaisseur | Ni format bandeau ni extérieur validés ; raccords entre écrans, brûlure image fixe, vieillissement/température, humidité et visibilité solaire ; OLED sur mesure = étude fournisseur distincte |

## Façade rouge

C'est un filtre spectral : elle transmet davantage certaines longueurs d'onde
rouges et absorbe une part du vert/bleu. Un pixel blanc RGB tend vers le rouge ;
aucune correction logicielle ne recrée une couleur que le matériau bloque.
Mesurer transmission par canal, haze/diffusion, reflets et contraste ambiant,
avant/après vieillissement. Une façade teintée, épaisse ou très diffusante exige
plus de flux ; augmenter le courant peut dégrader chaleur et durée de vie.
Le rouge monochrome est le compromis initial ; une zone moins filtrante peut
favoriser le RGB, au prix d'un aspect éteint moins proche de l'origine.

Comparer trois coupons : clair poli + teinte/vernis rouge ; translucide rouge ;
clair + film rouge remplaçable. Varier l'entrefer LED/façade sur un support réglable,
mesurer hotspots, fusion des pixels et angle de vision. Pas de reproduction de
logo Porsche ni de microprismes supposés équivalents à un catadioptre homologué.

## Procédés et tenue extérieure

| Procédé | Matériaux / coloration / finition | Usage conseillé et essais requis |
|---|---|---|
| SLA/DLP/MSLA | Résine claire, ex. Formlabs Clear V5 [S05] ; ponçage/polissage et vernis ou film rouge | Bon coupon de forme/optique. Post-cuisson contrôlée ; « clair » ou HDT ne prouve ni tenue UV ni résistance automobile. Essayer jaunissement, fissuration, lavage et fluage à chaud |
| PolyJet | VeroClear [S06] ; support à retirer, polissage ; couleur/mélange selon machine | Maquette visuelle ; photopolymère à qualifier en UV/chaleur/humidité, pas équivalent au PMMA massif |
| FFF | PETG ou PC transparent de grade documenté ; couches et vides diffusants | Coupon translucide et supports, qualité optique variable, étanchéité non intrinsèque. PC impose maîtrise séchage/température ; éviter PLA pour une pièce extérieure chauffée |
| SLS/MJF | PA translucide/opaque selon épaisseur, pas optique claire | Dos/support seulement ; texture/porosité, traitement d'étanchéité et vieillissement à tester |
| Maître imprimé + coulée sous vide | PU optique teinté, fiche grade indispensable | Petites séries ; bulles, retrait, variabilité du mélange et stabilité UV à caractériser |
| Thermoformage / usinage puis injection | PMMA ou PC grade extérieur, teinté masse et éventuellement hardcoat | Alternatives de série à chiffrer : PMMA optique/UV intéressant mais impact à examiner ; PC impact intéressant mais rayures/UV selon grade. Outillage et épaisseurs à définir |

Une finition commerciale « transparente » ne vaut pas qualification optique ou
photométrique [S05–S07]. Demander coût brut **et** finition, rebut et contrôle.
Retenir une façade remplaçable et un dos démontable avec vis/inserts, joint
compatible avec la teinte et les produits de lavage, compression maîtrisée,
dilatations libres et évent de pression si nécessaire. Éviter de noyer toute
l'électronique dans la résine ; vernis sélectif et interfaces réparables à comparer.
Qualifer vieillissement UV, chocs thermiques, condensation, eau, vibrations et
nettoyants sur le système complet, avec possibilité de changer joint et façade.
