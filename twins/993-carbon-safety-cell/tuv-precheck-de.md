# Pré-dossier TÜV Allemagne — monocoque carbone 964/993

Date de recherche : 2 septembre 2026. Ce document suppose une réception en
Allemagne. Il ne vaut ni avis du TÜV, ni accord de fabrication, ni homologation.

## Résultat immédiatement exploitable

Les deux générations et leurs variantes de carrosserie doivent rester séparées :

| Variante allemande publiée | Longueur | Largeur | Hauteur | Empattement | Voie avant | Voie arrière |
|---|---:|---:|---:|---:|---:|---:|
| 964 Carrera 2 Coupé, étroite | 4 250 mm | 1 652 mm | 1 310 mm | 2 272 mm | 1 374 mm | 1 374 mm |
| 993 Carrera Cabriolet II, étroite | 4 245 mm | 1 735 mm | 1 300 mm | 2 272 mm | 1 405 mm | 1 444 mm |
| 993 Turbo S, large | 4 245 mm | 1 795 mm | 1 285 mm | 2 272 mm | non publiée | non publiée |

La ligne 964 vient d'une
[fiche officielle Porsche Finder Allemagne](https://finder.porsche.com/de/de-DE/details/porsche-911-carrera-2-coupe-gebraucht-W39O34).
Elle publie aussi 1 350 kg DIN, 1 425 kg CE et 1 690 kg de masse maximale. La
ligne 993 étroite vient d'une
[fiche officielle Porsche Finder Allemagne](https://finder.porsche.com/de/de-DE/details/porsche-911-carrera-cabriolet-gebraucht-Z5OOK2).
Elle publie aussi 1 370 kg DIN, 1 445 kg CE et 1 710 kg de masse maximale. La
troisième vient de [Porsche Newsroom Allemagne](https://newsroom.porsche.com/de/historie/porsche-historie-weisse-riesen-991-turbo-964-turbo-3-6-993-turbo-s-13822.html),
qui donne également 1 575 kg à vide selon les papiers du véhicule. Porsche
confirme par ailleurs que la carrosserie Turbo est plus large de 60 mm dans sa
[présentation des trente ans du 993](https://newsroom.porsche.com/de/pressemappen/60-Jahre-Porsche-911/30-Jahre-911-Carrera-der-Generation-993-%E2%80%93-Der-letzte-seiner-Art.html).

Ces nombres servent à contrôler l'enveloppe, l'empattement et la cohérence de
variante. Le même empattement de 2 272 mm ne prouve pas des ancrages communs :
la 993 de référence a 31 mm de voie avant et 70 mm de voie arrière de plus que
la 964 C2 publiée. Ils ne définissent pas une caisse autoporteuse.

## Ce que les sites allemands ne publient pas

Aucune source allemande publique trouvée ne donne un jeu exploitable de
coordonnées XYZ et de tolérances pour :

- les ancrages des trains avant et arrière et de la direction ;
- les supports moteur, boîte et transmission ;
- les sièges, ceintures, pédalier et colonne ;
- les charnières, gâches, baies et vitrages ;
- les traverses de choc, points de levage et remorquage ;
- le repère primaire de caisse et ses références métrologiques.

Le loueur allemand Tkaczyk confirme seulement le jeu de marbre
[Celette `564.330`, « 911 Carrera Typ 964 / Zusatz 993 »](https://richtsatz-mieten.de/richtsaetze/porsche/).
Il ne publie ni plan de piges, ni coordonnées, ni certificat de calibration.
Les manuels d'atelier Porsche 964 et 993 restent à acquérir légalement pour les
dimensions de construction et de réparation de caisse ; leurs planches
protégées ne sont pas reproduites dans ce dépôt.

## Route de réception à faire confirmer avant la CAO F2

Une nouvelle cellule autoporteuse n'est pas un simple accessoire couvert par
une ABE. La [FAQ TÜV SÜD](https://www.tuvsud.com/de-de/branchen/mobilitaet-und-automotive/tuning-eintragungen-und-aenderungsabnahmen/tuning-faq)
indique qu'une modification non couverte, ou combinée à d'autres changements,
relève d'une nouvelle autorisation selon les paragraphes 19(2) et 21 StVZO. Le
[paragraphe 21 StVZO](https://www.gesetze-im-internet.de/stvzo_2012/__21.html)
impose un rapport d'expert et des protocoles montrant que les essais nécessaires
ont été exécutés et réussis. La classification exacte — transformation d'une
964/993 existante ou véhicule individuel nouvellement construit — doit être décidée
par l'expert et l'autorité, en particulier parce que la structure portant
l'identité du véhicule serait remplacée.

Le premier jalon doit donc être une **Vorbesprechung** documentée avec un expert
officiellement reconnu. Les questions à lui faire valider sont :

1. base réglementaire, date de référence, identité du véhicule et traitement distinct des donneuses 964/993 ;
2. variante donneuse exacte et éléments d'origine obligatoirement conservés ;
3. règlements et procédures applicables aux sièges, ceintures, serrures,
   vitrages, freinage, bruit, émissions, compatibilité électromagnétique,
   incendie, choc et protection des occupants ;
4. essais virtuels recevables, niveau de validation du modèle et essais
   physiques destructifs exigés ;
5. organismes et laboratoires dont les rapports seront acceptés ;
6. exigences de qualité pour le composite, les collages, les inserts, le CND,
   la traçabilité et la réparation.

Si une immatriculation historique allemande est recherchée en plus de la
réception routière, la monocoque carbone est un obstacle distinct : le
[catalogue TÜV SÜD Classic](https://www.tuvsud.com/de-de/-/media/de/auto-service/pdf/download-flyer-anforderungskatalog-classic-2021_as_rz.pdf)
demande notamment l'aspect d'époque et le matériau d'origine pour la carrosserie.
Il ne faut donc pas budgéter le projet en supposant le maintien automatique du
statut `H`.

## Plan d'acquisition des vraies cotes

| Priorité | Action | Livrable exigé | État |
|---:|---|---|---|
| 1 | Geler Coupé/Cabriolet/Targa, étroite/large, C2/C4, millésime et véhicule donneur | fiche de configuration et identification | bloquant |
| 2 | Obtenir légalement le volume V Porsche et le Datenblatt lié au véhicule | registre de valeurs avec pages et variantes | à faire |
| 3 | Utiliser le Celette 564.330 + supplément 993 | relevé du montage, références et contrôle de calibration | à faire |
| 4 | Scan optique intérieur/extérieur + CMM des interfaces | nuage brut, rapport d'incertitude et surfaces nominales | à faire |
| 5 | Mesurer deux sous-châssis et une seconde caisse | répétabilité, dispersion véhicule et gabarits indépendants | à faire |
| 6 | Faire signer le schéma de datums par métrologie, structure et homologation | référentiel CAO F2 libéré | à faire |

Le [Datenblatt TÜV SÜD](https://www.tuvsud.com/de-de/branchen/mobilitaet-und-automotive/oldtimer/oldtimer-datenblattservice)
est actuellement annoncé à 159 € TTC pour un véhicule particulier jusqu'à
2000, avec un délai de deux à trois jours ouvrés plus l'envoi. Il est utile aux
données d'immatriculation et à l'identification liée au numéro de châssis. La
page ne dit pas qu'il comprend les points de marbre : il ne remplace donc pas la
campagne Celette/CMM.

## Place de la simulation

TÜV SÜD décrit la simulation de rigidité, résistance, fatigue, modes propres et
crash comme recevable dans certains processus, mais précise que les résultats
sont fréquemment comparés aux essais physiques et que les modèles matériau
doivent être ajustés par essais. Voir les
[méthodes virtuelles TÜV SÜD](https://www.tuvsud.com/de-de/branchen/mobilitaet-und-automotive/automotive/pruefloesungen-und-compliance-services/virtuelle-testmethoden).
Omniverse peut donc servir de scène et d'orchestrateur de résultats ; il ne
transforme pas le modèle F1 actuel en preuve TÜV.

Le registre machine lisible associé est
[`tuv-dimensions-de.json`](tuv-dimensions-de.json). Tant que ses groupes
structurels sont `blocked`, la conception détaillée, le moule, la fabrication,
la route et le circuit restent interdits par le contrat de validation du projet.
