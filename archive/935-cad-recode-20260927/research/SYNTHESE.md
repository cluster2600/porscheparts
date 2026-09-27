# Recherche OpenClaw — culasse du scan 935

Cible confirmée par le propriétaire : `935-xtreme-cylinder-head.obj`. Les photos FVD 993 GT2 Evo servent uniquement de comparaison. Recherche du 27 septembre 2026 (Europe/Zurich).

## Conclusions contrôlées

| Sujet | Fait établi dans la source | Application à notre pièce |
|---|---|---|
| Désignation Wolfe | La fiche décrit une culasse conçue pour une voiture de course 935, livrée en OBJ. [Wolfe](https://www.wolfeclassics.com/shop/p/p-car-billet-cylinder-head-scan) | Étaye la désignation 935 du fournisseur. N’identifie ni la variante exacte, ni le fabricant, ni les dimensions du fichier. |
| Fabrication | Wolfe emploie « billet ». Xtreme décrit ses programmes actuels comme des moulages à cire perdue en RR350, traités HIP. [Xtreme](https://www.xtremecylinderheads.com/programs) | Divergence à éclaircir. Le nom de fichier « xtreme » ne suffit pas à attribuer l’alliage ou le procédé à la pièce scannée. |
| Variantes | Porsche distingue notamment 1976, 1977, Baby et 935/78. Cette dernière possède des culasses à eau et quatre soupapes. [Porsche](https://newsroom.porsche.com/en/2026/history/porsche-heritage-moments-935-norbert-singer-timo-bernhard-42018.html) | Aucune identification de notre scan comme Baby ou Moby Dick. Ne pas reconstruire des circuits d’eau à partir de cette seule histoire. |
| Scan K4 | Wolfe vend séparément un scan de moteur 935 K4 dont il signale des difficultés de profondeur et l’absence de préparation au scan. [Wolfe K4](https://www.wolfeclassics.com/shop/p/p-car-935k4-engine-scan) | Aucun lien démontré entre ce moteur et la culasse isolée. Les réserves propres au scan K4 ne décrivent pas automatiquement le scan de culasse. |
| Acquisition | Wolfe annonce un Creaform Handyscan 700 et un Einstar Vega. [Services Wolfe](https://www.wolfeclassics.com/services) | Ne prouve pas quel appareil a produit notre fichier, sa calibration, son unité ou son incertitude. |
| Données internes | Xtreme annonce des sondes Renishaw sur ses Rottler pour numériser conduits/chambres et un banc Superflow SF 750. [Atelier Xtreme](https://www.xtremecylinderheads.com/ourshop) | Piste pour obtenir des données natives et des mesures si le fabricant est confirmé. Aucun fichier interne ou résultat de débit de notre pièce obtenu. |

## Ce qui peut servir à la CAO

Continuer la reconstruction sur le scan 935 conservé, avec les réparations et surfaces déjà contrôlées. Les informations documentaires servent à identifier les fonctions et à éviter les confusions de versions ; elles ne donnent pas de nouvelles dimensions admissibles.

L’unité OBJ, le facteur d’échelle, l’alliage, la variante, les cotes d’emboîtement, entraxes, angles de soupapes, volumes de chambre et géométries internes restent inconnus. La fermeture locale des lacunes de scan n’autorise pas à boucher les passages fonctionnels ou à inventer les surfaces cachées. Les résidus de reconstruction exprimés en unités OBJ ne deviennent pas des millimètres par convention d’affichage.

## Questions ciblées à Wolfe / au fabricant — brouillon, aucun envoi

1. Quelle marque, référence, révision et application moteur exactes correspondent à la culasse scannée ? Existe-t-il un marquage photographiable ?
2. Le terme « billet » décrit-il le procédé réel de cette pièce ? Peut-on confirmer le matériau et le procédé par une référence fabricant ?
3. Quelle unité et quel facteur d’export pour l’OBJ ? Fournir au moins une cote physique étalon, idéalement plusieurs mesures indépendantes dans trois directions.
4. Quel scanner, quelle calibration, quelle préparation de surface et quel traitement du maillage ? Les captures brutes et le projet natif sont-ils disponibles, avec les droits d’usage ?
5. Fournir les dimensions mesurées des interfaces : emboîtement cylindre, plan de joint, entraxes des goujons, admission, échappement, porte-arbres et logements des bougies, avec leurs références géométriques et tolérances.
6. Les données natives de conduits/chambre, les angles et diamètres de sièges/guides, le volume de chambre, les passages d’huile et leurs contrôles sont-ils disponibles pour cette référence précise ?

## Exécution et revue

24 missions OpenClaw distinctes, sur le modèle local `nemotron-cad`, exécutées deux par deux. Les URLs initiales ont été trouvées par Codex puis confiées aux agents pour consultation. Il ne s’agit pas de 24 modèles indépendants ni de 24 confirmations indépendantes.

Les rapports bruts sont conservés séparément, marqués non validés. Seules les conclusions contrôlées ci-dessus font autorité pour cette recherche. Les reçus d’exécution et les consultations `web_fetch` figurent dans `execution-evidence.json`. Bilan vérifié : 24 agents, 24 consultations web confirmées par leurs reçus, 24 réponses complètes après 8 reprises (dont 5 sorties initialement tronquées). Ces nombres décrivent l’exécution, pas une validation scientifique des rapports.

Erreurs déjà rejetées : attribution à Wolfe de l’avis juridique de Xtreme ; identification sans preuve du scan comme 935 Baby ; transfert de la vitesse de Moby Dick à Baby ; suggestion de créer des circuits d’eau dans la cible ; affirmation que la page Xtreme ne contient aucun procédé, alors que son contenu contrôlé en indique ; assimilation des capacités d’une machine à des données géométriques disponibles pour notre pièce.

Autres propositions rejetées : calibrer le scan avec un calibre virtuel sans cote physique ; déduire les attaches de la culasse des ailettes ; conclure à un régime moteur limité sous 5 000 tr/min à partir d’une description de son comportement. Les extractions OpenClaw de certaines pages Xtreme étaient incomplètes et FVD a renvoyé une erreur 403 dans plusieurs missions. Le contrôle direct des sources corrige ces limites de récupération.

Cette recherche n’apporte ni plan coté exact de la pièce, ni validation de fabrication, d’assemblage ou de tenue mécanique.

## Rapports bruts par mission

Tous les rapports ci-dessous restent non validés ; utiliser les conclusions contrôlées en tête de document.

| Agent | Mission | Rapport |
|---|---|---|
| research935-01 | Identité du scan de culasse vendu par Wolfe; ce que le titre prouve et ne prouve pas | [Lire](reports/research935-01/findings.md) |
| research935-02 | Provenance, unités, précision et licence publique du scan; limites des scanners annoncés | [Lire](reports/research935-02/findings.md) |
| research935-03 | Xtreme: fonderie ou usinage dans la masse, alliage et HIP; contradiction éventuelle avec billet | [Lire](reports/research935-03/findings.md) |
| research935-04 | Xtreme: numérisation des conduits et chambres, machines CNC et banc de débit | [Lire](reports/research935-04/findings.md) |
| research935-05 | Culasse Porsche 935 de 1976: architecture documentée et inconnues | [Lire](reports/research935-05/findings.md) |
| research935-06 | Porsche 935 de 1977: changements réels de motorisation et de culasse | [Lire](reports/research935-06/findings.md) |
| research935-07 | 935 Baby: caractéristiques propres; pourquoi ne pas transférer ses dimensions | [Lire](reports/research935-07/findings.md) |
| research935-08 | 935/78 Moby Dick: refroidissement et soupapes, distinction impérative avec scan à ailettes | [Lire](reports/research935-08/findings.md) |
| research935-09 | 935 K3: identité moteur et limites de transfert vers scan Wolfe | [Lire](reports/research935-09/findings.md) |
| research935-10 | 935 K4: lien éventuel entre scan moteur Wolfe et scan de culasse; ne pas supposer identité | [Lire](reports/research935-10/findings.md) |
| research935-11 | Comparaison FVD 993 GT2 Evo et cible 935: éléments externes comparables, aucune cote transférable | [Lire](reports/research935-11/findings.md) |
| research935-12 | Alésage, emboîtement cylindre et dimensions publiées: applicabilité exacte au scan | [Lire](reports/research935-12/findings.md) |
| research935-13 | Soupapes: diamètres, angles et sièges; ne rapporter aucune cote sans source exacte | [Lire](reports/research935-13/findings.md) |
| research935-14 | Chambre: volume, compression et usinage; ce qui reste à mesurer | [Lire](reports/research935-14/findings.md) |
| research935-15 | Admission: conduits et débit; différence entre méthode de mesure et valeurs cibles | [Lire](reports/research935-15/findings.md) |
| research935-16 | Échappement: interfaces et dimensions documentées ou inconnues | [Lire](reports/research935-16/findings.md) |
| research935-17 | Refroidissement: ailettes, guides air et distinction versions eau/air | [Lire](reports/research935-17/findings.md) |
| research935-18 | Passages internes huile et géométrie cachée: preuves disponibles et mesures nécessaires | [Lire](reports/research935-18/findings.md) |
| research935-19 | Goujons, perçages et interfaces de fixation: données exactes versus inconnues | [Lire](reports/research935-19/findings.md) |
| research935-20 | Simple/double allumage: variante 935 cible non identifiée, comparaison FVD | [Lire](reports/research935-20/findings.md) |
| research935-21 | Alliage et traitement: distinguer RR350 Xtreme documenté et matériau inconnu du scan | [Lire](reports/research935-21/findings.md) |
| research935-22 | Métrologie: protocole minimal pour rendre le scan exploitable en CAO mesurée | [Lire](reports/research935-22/findings.md) |
| research935-23 | Audit contradictions: billet/cast, 935/993, Moby Dick/culasse ailettée; sources prioritaires | [Lire](reports/research935-23/findings.md) |
| research935-24 | Questions précises à poser à Wolfe et Xtreme pour identifier la culasse et ses interfaces; brouillon sans envoi | [Lire](reports/research935-24/findings.md) |
