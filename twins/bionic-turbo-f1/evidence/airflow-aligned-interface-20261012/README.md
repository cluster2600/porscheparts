# Interface radiale alignée : équilibre numérique reproduit

Le témoin 021 termine **200 pas de 0,1 µs** avec le code natif zéro, `Mesh OK.` et `End`. Il conserve le gaz au repos dans les trois seuils fixés avant calcul. Ce résultat valide une piste de correction de l'interface MRF sur un domaine simplifié ; il ne qualifie pas encore le maillage ni les performances du turbo.

| Grandeur sur les 200 historiques natifs | Maximum observé | Seuil préalable |
|---|---:|---:|
| Écart de pression à 101 325 Pa | 3,4000e-6 Pa | 1e-3 Pa |
| Écart de température à 298,15 K | 1,0001e-9 K | 1e-6 K |
| Vitesse absolue | 3,1228e-9 m/s | 1e-8 m/s |

Le contrôle indépendant relit les champs natifs `p`, `T` et `U` au temps 20 µs : 9 600 cellules finies par champ, empreintes concordantes avec le reçu terminal. Les arrondis d'écriture expliquent les très petits écarts entre les extrema des champs et ceux des historiques.

## Changement testé

Le préparateur `../../cfd/conformal_mrf_witness.py` réutilise le témoin de gaz immobile. Il crée une couronne facettisée de rayons 10, 20 et 40 mm, étendue de −40 à 40 mm suivant z, avec 32 secteurs et 64 blocs. La zone tournante comprend 3 200 cellules, séparées des cellules fixes par 640 faces radiales. Les faces ne sont pas subdivisées angulairement : leur normale est radiale au centre de face, donc tangente à la vitesse de rotation. Toutes les parois physiques restent fixes ; il n'y a ni rotor, ni écart de pression, ni apport thermique.

L'audit indépendant de la géométrie native trouve une composante normale maximale de rotation de 4,755e-9 m/s et une somme absolue des flux géométriques de 3,373e-11 m³/s. Ce résidu provient de la précision des coordonnées natives ; ce n'est ni un zéro exact ni un débit physique à travers les parois. Les comptages et le parallélogramme de chaque face sont vérifiés.

Les [quatre témoins précédents](../airflow-frame-equilibrium-20261012/README.md) isolaient le défaut en conservant le même cube. Cette couronne ajoute un exemple radial réalisable qui conserve l'équilibre, mais sa forme et son maillage diffèrent du cube : ne pas présenter la différence de vitesses comme une amélioration quantitative des performances du turbo.

## Tentative interrompue et reproduction

La tentative 020 atteint la limite de 240 secondes de calcul après 136 pas complets, code natif 124. Elle reste conservée. Le script `run_witness.py` prépare **un cas neuf 021**, avec une limite de 600 secondes. Les manifestes et tous les paramètres physiques et numériques de 020 et 021 sont identiques. Les 136 premières lignes des historiques minima et maxima sont également identiques. Seul le budget de temps machine augmente ; aucun critère ni tolérance n'est assoupli.

Le solveur de pression atteint **599 fois la limite de 1 000 itérations linéaires** dans 021. L'équilibre physique discret satisfait le témoin, mais la convergence linéaire n'est donc pas qualifiée. Les journaux complets restent disponibles. Aucune carte débit/pression/régime, puissance maximale, sensibilité au maillage ou calibration physique n'est validée.

## Reproduction et preuves

Depuis la racine du dépôt, avec Python, NumPy, Docker et l'image OpenCFD 2406 épinglée disponibles :

1. Restaurer les archives de la référence 015 et des témoins dans un espace de travail distinct. Les préparateurs refusent les destinations déjà existantes : pour rejouer cette campagne, conserver les preuves dans une autre copie et réserver des destinations neuves.
2. Le préparateur radial produit 020 ; `run_witness.py` conserve ses entrées et rejoue dans 021 avec une limite de calcul prolongée. Le parent est `work/bionic-airflow-20261012/baseline-interface-015`.
3. `read_fields.py` vérifie les champs finaux et leur reçu ; `interface_flux_parallelograms.py CHEMIN_DU_CAS` mesure la géométrie de l'interface.

`comparison.json`, les manifestes, rapports, champs relus et contrôles locaux détaillent les résultats. L'archive contient **63 fichiers**, y compris la tentative interrompue ; tous les contenus et cibles des liens physiques du TAR sont relus avant publication. SHA-256 de l'archive : `1118679de6f8ea087de323cf19e3a00771742f1f63948c6eba3fed0a503183c1`.

[Archive native publiée](https://github.com/cluster2600/porscheparts/releases/tag/bionic-turbo-aligned-interface-2026-10-12) ; `remote-verification.json` documente la vérification des tailles et empreintes distantes. Les fichiers identiques utilisent des liens physiques dans le TAR : copier indépendamment avant modification.

Validation logicielle : 64 tests ciblés réussis, un ignoré ; `make check` local découvre 3 745 tests et retrouve quatre problèmes hors turbo (deux dépendances optionnelles absentes et deux comparaisons flottantes exactes), sans nouvelle régression identifiée. La CI de la PR reste nécessaire avant fusion.

## Prochain travail autorisé

Construire un maillage du turbo avec une interface radiale conforme, sans déplacer les pales, modifier les jeux ou perdre une connexion fluide. Vérifier d'abord la géométrie, les patches et l'équilibre sans forçage, puis l'admission native et les couches de paroi. Les auditeurs cartésiens actuels ne suffisent pas à qualifier des faces non cartésiennes : conserver leurs preuves historiques et créer une validation adaptée. Comparer ensuite référence et candidate selon la même recette et démontrer un régime établi avant de chercher le débit et la puissance maximaux. Aucun nouveau calcul complet sur l'ancienne interface en escalier n'est justifié par ces résultats.
