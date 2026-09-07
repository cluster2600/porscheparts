# M64 4V — passages de gaz et enveloppes de mouvement

Ce lot travaille les **fonctions de la pièce**, à partir du corps privé à
quatre logements. Il ne remplace pas la silhouette par une nouvelle enveloppe.
La référence reste issue d'un scan 935 ; le recalage vers le module 4V est
une hypothèse de conception, pas une interface M64 certifiée.

**Résultat du premier candidat découpé : non retenu.** Le B-Rep natif est
monobloc et passe les cinq contrôles BOP exécutés, mais l'interpolation du
tronc admission crée une excroissance réelle et son STEP présente 55 défauts
de p-curves après lecture. Le maître de départ n'est ni remplacé ni modifié.
Le [reçu de l'essai 04](../twins/m64-cylinder-head/evidence/scan-seeded-ports-trial-04-20260907.json)
conserve les empreintes et distingue ces contrôles de la validation moteur.

**Dernière exécution : essai 05, tronc à interpolation réglée.** La correction
a été réellement reconstruite et découpée, en 374 s sur processeur local.
Le [reçu de l'essai 05](../twins/m64-cylinder-head/evidence/scan-seeded-ports-trial-05-ruled-20260907.json)
confirme un seul solide natif, aucun défaut BOP signalé dans les cinq modes
exécutés et une relecture `.brep` cohérente. Le STEP présente encore **26 défauts
de p-curves** et reste rejeté. Ce candidat privé n'est pas promu en maître ni
en fichier de fabrication ; le contrôle des ouvertures est distinct.

Ce contrôle a ensuite été exécuté sur l'essai 05, sans réutiliser les contacts
de l'ancienne géométrie : **zéro portion de face et zéro aire hors des
enveloppes définies**, côté admission comme échappement. Les partitions d'aire
passent sans changer les seuils. L'enveloppe réglée est cette fois identique
au nouveau tronc : ce résultat reste relatif à ces régions et ne prouve ni
la conformité OEM des bouches ni l'absence d'une poche à l'intérieur d'une
région autorisée. Tous les contacts bruts restent conservés.

## Course complète des quatre soupapes

Les quatre volumes d'exclusion natifs couvrent toutes les positions entre
fermé et levée maximale, pas seulement quelques images d'une animation.
Leur intersection avec le corps de départ est topologiquement vide : aucun
solide, aucune coque, face, arête ou sommet commun dans les booléens exécutés.
Le [reçu public](../twins/m64-cylinder-head/evidence/continuous-valve-envelopes-20260907.json)
lie le maître, le module, les quatre enveloppes et le code par SHA-256.

La preuve exploite le profil réellement utilisé : rayon positif, non croissant
avec Z, et **base cylindrique initiale de hauteur positive**. Pour une course
axiale rigide L vers la chambre, prolonger cette base de L couvre l'union de
toutes les positions. Le volume ajouté vaut `π R² L`. Sept tests natifs couvrent
notamment un obstacle rencontré au milieu de course alors que les extrémités
sont libres, et le rejet d'un profil conique initial auquel cet algorithme ne
s'applique pas. Ce dernier cas a été ajouté après relecture indépendante.

Les levées sont les candidats V2 : 11,5 admission / 9,6 échappement, sous
l'hypothèse de recalage 1 unité du scan par mm. Le corps n'est pas transformé
une seconde fois. Ces volumes n'ajoutent **aucune marge de dilatation, flexion
ou guidage**, et ne contiennent ni piston, ni ressort, ni came. L'absence de
collision nominale n'établit pas un jeu positif suffisant à chaud.

## Raccordements issus des sections du scan

Le corps de départ comporte seulement les quatre logements étagés siège/guide :
ses anciens conduits ont été comblés lors de la reconstruction de peau.
Dix sections circulaires ajustées au scan ont été retrouvées : trois côté
`low_B`, sept côté `high_B`. Elles servent de contraintes de construction,
**pas de surfaces intérieures intégralement mesurées ni de brides usinées**.
Les résidus d'ajustement ne sont pas une incertitude métrologique totale.

Le nouveau modèle relie deux gorges par banque à un conduit commun, puis aux
sections correspondantes. Les axes et diamètres sont liés au même module V2,
au reçu d'intégration, à sa correction locale et au SHA du corps final.
Les choix de courbure et de protection des guides restent exploratoires.

L'affectation `admission → high_B`, `échappement → low_B` suit la banque V2
actuelle. Elle est **nouvelle, non OEM et opposée aux noms du vieux builder
F36**. Il ne faut pas transférer silencieusement ce dernier comme preuve.

Les bouches ne sont pas élargies pour obtenir artificiellement un résultat
favorable. L'aire minimale des cercles de la branche admission représente
environ 67,6 % de la somme des deux gorges ; côté échappement, environ 98,0 %.
C'est un écran géométrique, sans tige, bossage ni coefficient de débit : il
signale un étranglement potentiel à examiner, pas une performance calculée.

## Essais rejetés et correction de la jonction

Les premières branches aboutissaient au même cercle terminal. Une fusion
échappement a produit quatre solides et un volume inférieur à celui d'un
opérande : cet essai a été rejeté avant toute découpe du corps. Un simple
chevauchement axial n'a pas suffi. Le code vérifie désormais la monotonie
volumique des unions, différences et intersections, en plus du BRepCheck.

La correction géométrique conserve le rayon de gorge dans chaque branche.
Les deux extrémités sont distinctes et entièrement enfouies dans le tronc :
elles ne partagent plus trois bouchons coplanaires presque confondus.
Chaque banque native passe alors les cinq modes BOP contrôlés. Les résultats
STEP doivent rester séparés de ces résultats natifs.

## B-Rep natif et export STEP : autorités différentes

Les noyaux natifs et leurs réimports `.brep` sont conservés. Leur export STEP
signale encore des p-curves incohérentes après lecture. Les essais documentés
avec ou sans p-curves, préférence pour les courbes 3D et export de la tolérance
native maximale n'ont pas éliminé les défauts des deux noyaux de diagnostic.
Les réglages essayés sont ceux du
[traducteur STEP OCCT](https://occt3d.com/dev/doc/overview/html/occt_user_guides__step.html).

Sur ces noyaux de diagnostic, le maximum **échantillonné** de l'écart 3D/2D
reste de l'ordre de 2 × 10⁻⁶ unité. Le lecteur réduit certaines tolérances
locales natives de 5 × 10⁻⁶ sous cet écart. Cette observation explique les
signalements sans démontrer une borne continue ; elle n'autorise pas à
masquer le défaut en augmentant globalement les tolérances.

La découpe exploratoire utilise donc les B-Rep natifs, pas les STEP rejetés.
Un export rejeté reste archivé pour diagnostic, jamais présenté comme fichier
de fabrication. La géométrie source du corps et les mesures du scan restent
inchangées et privées.

## Dépassement détecté par contre-contrôle

Le premier écran de peau autorisait le même loft que celui utilisé pour le
conduit commun. Il rendait zéro contact hors de cette enveloppe, mais ne
pouvait pas détecter un défaut partagé par les deux constructions.

Le contre-contrôle remplace seulement l'enveloppe d'autorisation par une
interpolation **réglée entre les mêmes cercles**, sans agrandir leurs rayons.
Il révèle côté admission 130 portions de faces, totalisant environ
690,82 unités², hors de cette enveloppe indépendante. La reconstruction séparée
localise l'excroissance dans le tronc, pas dans les deux branches ; des sections
natives confirment que ce n'est pas uniquement une boîte englobante conservative.
Le résultat échappement de ce contre-contrôle reste indéterminé après échec
de conservation d'aire ; le seuil n'est pas relâché pour obtenir un succès.
Les [reçus du contre-contrôle et du rendu](../twins/m64-cylinder-head/evidence/scan-seeded-ports-counterchecks-20260907.json)
conservent résultats, échecs et empreintes, sans les coordonnées privées.

Une reprise limitée sur les trois mêmes surfaces échappement utilise une
quadrature adaptative explicite. Les écarts de partition passent alors sous
le seuil inchangé pour ε = 10⁻⁷, 10⁻⁹ et 10⁻¹¹. Cependant, certaines aires
varient encore entre les deux derniers réglages. Les estimateurs internes ne
sont pas des bornes rigoureuses : cette reprise explique la sensibilité
numérique, sans remplacer le verdict initial par une conformité des ouvertures.

La correction suivante porte donc sur l'interpolation du tronc uniquement.
Les raccordements réglés constituent un témoin géométrique borné, pas une
validation de pertes de charge ni des rayons de raccordement finaux.

Le générateur propose `--trunk-interpolation ruled` pour cet essai contrôlé ;
le mode `smooth` reste disponible pour reproduire l'essai rejeté. Le choix est
enregistré dans le contexte et le rapport. Les branches gardent leur loft
lisse ; aucune section du scan, aucun rayon et aucune tolérance ne changent.
Les jonctions du tronc réglé sont seulement C0. Elles ne constituent pas les
surfaces fluidiques définitives.

Sur la tessellation réelle de l'essai 05, la borne latérale positive du
négatif admission diminue de 31,50 unités de scan : l'excroissance signalée
dans l'essai 04 n'est plus présente. Cette comparaison locale ne prouve pas
la bonne implantation de toutes les ouvertures ni l'épaisseur des parois.

## Contrôles restant à fermer sur la pièce

- Ouvertures de peau : inventorier toutes les faces touchées, puis les portions
  hors des zones de bouches et logements explicitement examinées. Une boîte
  englobante identique ne prouve pas la conservation de la peau.
- Communication entre volumes, inserts de sièges et guides, ligaments et
  épaisseurs : des noyaux disjoints ne prouvent pas l'absence de liaison
  indirecte dans l'assemblage complet.
- Chambre finale, distribution et huile, matériaux et interfaces moteur :
  toujours à compléter ou qualifier.
- Débit, thermique, résistance, fatigue et LPBF : aucun gain ni imprimabilité
  ne sont déduits de ce seul lot de géométrie.

Les [entrées CHT](M64_CHT_HEAD_INPUT_AUDIT.md) ont été actualisées pour ne plus
laisser croire que l'ancien inventaire F53 ou ses maillages s'appliquent au
corps courant. La [carte Mermaid d'exécution](../diagrams/m64-700ps-execution.mmd)
situe ce lot dans la préparation CAO, avant les calculs de pièce.

## Exécution et accès

- [Générateur des enveloppes continues](../twins/m64-cylinder-head/source/build_continuous_valve_envelopes.py).
- [Générateur de conduits sous hypothèses](../twins/m64-cylinder-head/source/build_scan_seeded_ports.py).
- [Contre-contrôle des ouvertures](../twins/m64-cylinder-head/source/audit_port_skin_openings.py),
  avec conservation des contacts bruts et contre-exemple de poche cachée.
- [Tests des enveloppes](../tests/test_continuous_valve_envelopes.py) et
  [tests des raccordements](../tests/test_m64_scan_seeded_ports.py), complétés
  par les [témoins de contrôle de peau](../tests/test_m64_port_skin_openings.py).

Toutes les géométries liées au scan, coupes et images de ce lot restent privées.
Seuls code, hypothèses et reçus sans coordonnées privées sont publiables.
Aucune autorisation de fabrication ou de fonctionnement moteur n'est acquise.

Les premières vues privées proviennent des 4 837 faces de l'essai 04, toutes
tessellées, sans lissage ou décimation : extérieur, demi-vue avec noyaux
colorés et coupe plane. Le bleu/orange distingue les conduits, **pas des
températures ou vitesses calculées**. Le [script de rendu](../twins/m64-cylinder-head/source/render_scan_seeded_ports.py)
lie les maillages, images et avertissements au reçu de calcul.

Les vues actualisées de l'essai 05 représentent ses **4 892 faces et 70 386
triangles**, avec le même cadrage et les mêmes avertissements. Leurs empreintes
et celles de la coupe sont liées au B-Rep exact dans le reçu de l'essai 05.

## Vérifications logicielles de ce lot

`make check` termine avec sortie 0 ; sa découverte principale exécute
2 095 tests, dont 68 explicitement ignorés dans le runtime par défaut.
Les trois suites ciblées sont aussi exécutées dans le runtime OCP qualifié :
7 tests d'enveloppes continues, 10 de raccordement et 2 de contrôle de peau,
tous réussis, aucun ignoré. Le [reçu des vérifications](../twins/m64-cylinder-head/evidence/port-geometry-software-checks-20260907.json)
conserve l'empreinte du journal. Ces tests de logiciel et de géométrie ne sont
pas des essais physiques de la culasse.
