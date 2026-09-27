# Conformité et origine — portes de décision

Recherche préliminaire consultée le **27 septembre 2026** ; qualification juridique
et technique du produit **non obtenue**. Références officielles dans
[sources.md](sources.md). Le projet peut être arrêté ou limité au démonstrateur
si aucune voie acceptable n'est confirmée. CE, homologation routière et origine
suisse répondent à des questions différentes.

## Commencer par la pièce d'origine

Porsche décrit un bandeau arrière avec logo réfléchissant rouge [S20]. Cela
n'établit ni la classe réglementaire de chaque zone ni l'équipement de chaque
marché. Le fabricant d'un kit pour 993 documente un ensemble réflecteur/boîtier
antibrouillard et les feux antibrouillard arrière [S21] ; c'est une preuve de
fonctions présentes sur certaines configurations, **pas une preuve d'homologation
de la transformation du kit**. Ne pas transférer cette architecture à toute 993.

Avant de concevoir, relever sur la référence exacte : fonctions actives, ampoules,
câblage, surfaces réfléchissantes, marquages E/e et catégories, liens avec les
feux adjacents. Déterminer où se trouvent les catadioptres obligatoires et si le
bandeau en fait partie. Confirmer séparément présence d'antibrouillard, de recul
ou de toute autre fonction : **ne pas présumer que le bandeau central porte le
feu de recul ou qu'il est purement décoratif**. La pièce réelle et son dossier
variante doivent trancher. Photographier les marquages sans publier VIN/plaque.

Changer lentille, teinte, source ou géométrie peut invalider une fonction homologuée.
La copie d'un marquage existant est exclue ; conserver physiquement un composant
homologué ne garantit pas la conformité de son intégration. Même démontable et
éteint, un écran peut altérer réflexion, fonctions, couleur, visibilité et sécurité.

## Suisse, UE et Allemagne

| Domaine | Base / faits vérifiés ou statut | Travail à obtenir |
|---|---|---|
| Suisse véhicule | OETV RS 741.41 [S22] ; OFROU publie l'identification des feux/catadioptres [S23] | Version consolidée et articles applicables à faire relire ; exigences selon première mise en circulation, marché et variante ; réception/modification auprès service cantonal avec expertise compétente |
| Allemagne | StVZO §49a [S24] vise les installations lumineuses admises et inclut expressément l'affichage optique extérieur variable/dynamique autoéclairé ou rétroéclairé ; §19 traite conséquences des modifications sur l'autorisation [S25] | Avis écrit avant conception pleine largeur ; route d'approbation composant/installation, §22a/§21 le cas échéant, sans présumer qu'une réception individuelle admettra du texte animé |
| ONU / UE véhicule | Examiner UN R48 (installation), R148 (signalisation), R150 (rétroréflexion), R10 (CEM), ainsi que règlements historiques pertinents R38/R3/R7/R23 selon fonctions et droits transitoires | Laboratoire doit sélectionner séries d'amendements, photométrie/couleur/angles et marquages ; pas d'équivalence automatique vieux véhicule/nouveau composant |
| Radio UE | RED 2014/53/UE [S26] : sécurité, CEM, spectre et dossier produit radio | Laboratoire : EN 300 328, EN 301 489 et sécurité/exposition selon versions applicables ; déclaration UE, marquage, notice et traçabilité. Module préqualifié insuffisant à lui seul |
| Radio Suisse | OFCOM : exigences essentielles, évaluation, documentation, déclaration et informations/marquage [S27] | Confirmer OIT/règles en vigueur et reconnaissance du dossier UE, notice marchés visés |
| Cybersécurité / produit | Champ du règlement délégué RED 2022/30 et textes suivants, CRA, RoHS/DEEE, sécurité générale, obligations emballage/REP à examiner selon produit et date | Ne pas affirmer que BLE sans cloud dispense automatiquement des exigences ; téléphone relais et traitements de données à qualifier. Analyse légale et dates d'application restent ouvertes |
| Bluetooth | Bluetooth SIG impose la qualification avant vente/distribution [S28] | Choisir voie, frais actuels, nom de l'entité commercialisante et droits de marque ; qualification distincte du CE |

**Deux usages distincts :** coupon sur banc / exposition sur terrain privé fermé,
et installation destinée à la route. Un parking privé ouvert au public n'est pas
présumé hors droit routier. Une démonstration privée ne dispense pas de sécurité
électrique, d'autorisation du site, de maîtrise de l'éblouissement, ni des obligations
applicables à la mise sur le marché. L'interverrouillage « éteint en roulant » est
une réduction de risque éventuelle, **pas une voie d'homologation en soi**. Aucun
signal vitesse non validé n'est inventé, notamment pas de bus CAN présumé sur 993.

## Questions à l'organisme compétent

Envoyer après accord la RFQ réglementaire de [rfqs.md](rfqs.md), avec :
référence/variante, photos marquages, schéma des fonctions conservées/supprimées,
concept optique, matrice et puissance envisagées, modes défaut et alimentation.
Obtenir par écrit fonctions à préserver, textes/séries applicables, acceptabilité
même écran éteint, essais, échantillons, coût/délai et voie CH/DE/UE. TÜV n'est pas
un label universel permettant de contourner ces questions. DTC est une piste
suisse ; TÜV Rheinland Berlin publie une compétence spécifique en éclairage
[S18–S19]. Vérifier mandat/accréditation pour les essais effectivement commandés.

## Objectif « Made in Switzerland »

Selon l'IPI [S29–S30], un produit industriel doit notamment atteindre **60 % du
coût de revient admissible en Suisse**, réaliser en Suisse l'activité lui donnant
ses caractéristiques essentielles et y accomplir une étape physique de fabrication.
L'assemblage final seul n'établit aucune de ces conditions automatiquement.

Le registre [swissness.csv](swissness.csv) et le calcul de [budget.md](budget.md)
sont un modèle d'analyse, **pas une attestation**. Inclure coûts de production et
R&D admissibles selon allocation documentée ; ventiler composants importés,
transformation locale et main-d'œuvre. Examiner séparément contrôle qualité,
certification et amortissement avec les règles IPI. Emballage, distribution après
production et service après-vente sont exclus de ce calcul ; ils restent dans le
budget économique. Ne pas exclure automatiquement des LED importées au motif
qu'elles ne seraient pas fabriquées en Suisse : toute exception exige son fondement.

Dossier de preuve privé par lot : nomenclature et origine, factures ventilées,
site de fabrication, heures réellement travaillées, base d'amortissement R&D,
méthode comptable stable, opération essentielle décrite et rapport de revue.
Recalculer à changement fournisseur ou volume ; conserver références anonymisées
publiables. Un coût total de 250 CHF ne signifie pas 150 CHF suisses admissibles.

« Made in Switzerland » / « Swiss Made » est une indication d'origine ; un label
privé (par exemple une licence de marque Swiss Label) ajoute un règlement et des
droits distincts, sans remplacer la loi. Ni croix suisse, ni label, ni allégation
suisse ne figurent sur la maquette, la publicité ou l'emballage. La formulation
interne est **objectif d'origine suisse à démontrer**.
