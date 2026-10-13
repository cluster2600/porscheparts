# Repos du maillage raccordé — 084 incomplet au budget

084 atteint la limite de 1 200 secondes avant les 20 µs physiques demandées.
Le conteneur termine avec le code 124, sans OOM, après 1 201,298 s mesurées
par le lanceur. Le cas est TERMINÉ et conservé ; il ne doit pas être relancé
ou prolongé à l’identique. Ce résultat ne qualifie pas le repos sur 20 µs et
ne démontre pas une instabilité physique.

## Entrées et admission

Le cas reprend exactement le maillage 083 admis, de 33 920 cellules, avec
20 352 cellules tournantes et 6 784 faces MRF. Le précontrôle checkMesh étendu
passe avant le solveur. La preuve 083 conserve la géométrie tournante ; elle ne
remplace pas un contrôle d’écoulement propre à cette nouvelle topologie.

Le comparateur vérifie toutes les entrées préparées contre 076. Seuls huit
fichiers polyMesh changent ; meshModifiers s’ajoute et quatre diagnostics de
raffinement hérités disparaissent. Les entrées hors maillage, critères,
commande native et limites sont identiques : 200 pas de 1e−7 s jusqu’à 20 µs,
1 CPU, 2 GiB, timeout 1 200 s. Aucun réglage d’équation, tolérance, pas ou durée
physique. Les champs initiaux conservent l’entrée defaultFaces inutilisée.
Toutes les entrées ont été copiées AVANT lancement et leurs empreintes sont
vérifiées après arrêt. Le runtime original v2406 épinglé est conservé.

## Résultat réellement écrit

Les historiques minima/maxima contiennent 111 pas complets, jusqu’à 11,1 µs.
Le journal commence le pas 112 à 11,2 µs, mais ce pas n’a pas ses extrema complets.
Une lecture séparée vérifie exactement la séquence temporelle et les résolutions
pression : 444 dans les pas complets, puis deux dans le pas interrompu. Toutes
ces 446 résolutions atteignent 1 000 itérations. Il n’y a pas de convergence
linéaire qualifiée.

Sur les seuls 111 pas complets, les maxima d’écart sont :

- pression : 1,1059455574e−9 Pa ;
- température : 1,3585577108e−11 K ;
- vitesse : 2,8514800799e−12 m/s.

Ils restent sous les seuils inchangés de 0,001 Pa, 1e−6 K et 1e−8 m/s sur
cet intervalle écrit. Ils ne constituent pas une validation sur 20 µs. Le
Courant maximal consigné est 0,0859544233 ; ses 113 lignes incluent les sorties
d’initialisation et du pas interrompu, pas 113 pas complets.

L’écriture des champs était prévue au pas 200. Aucun répertoire temporel
non nul ni champ final p/T/U/rho/phi n’a donc été produit. Le lecteur vérifie
explicitement cette absence ; il ne remplace pas les champs absents par les
historiques ou par ceux d’un autre cas. Tous les payloads réellement présents,
les entrées, journaux et reçus sont relus et hachés.

## Portée et limites

C’est un arrêt au budget de temps mur, sans fin native `End`. Les autres travaux
locaux ont été préservés et les tests du dépôt ont aussi été exécutés pendant
cette phase. Le temps mesuré n’est pas un benchmark isolé et ne permet pas
d’attribuer le dépassement à une cause unique ou au seul nombre de cellules.
Aucune reprise, aucun budget supplémentaire et aucun changement de seuil ne
sont appliqués pour obtenir un succès.

Le maillage conserve les parois synthétiques projetées, leurs faces fixes
gauchies et un volume différent de la cible originale. Rotor et ports physiques
sont absents. Le raffinement protégé, les couches, les parois physiques et le
repos global du vrai turbo restent ouverts. Aucun débit, gain de puissance,
stabilité de perturbations ou jumeau calibré n’est validé.

## Archive

[Entrées, historiques et reçus du cas incomplet](https://github.com/cluster2600/porscheparts/releases/tag/bionic-turbo-coupled-equilibrium-2026-10-13). Cinq actifs vérifiés par tailles et digests GitHub ; tous les payloads relus localement, sans second téléchargement intégral distant.

```json
{
  "files": 64,
  "archive_bytes": 1772377,
  "archive_sha256": "593b91fcbe3d465ecf3023218b7e9603102a1473b80eaa318e789d4bd817d438",
  "manifest_sha256": "500769ffa514ea1c755cd4860f74f4f4a205736118fc3f7a9ee7dba9fdecc562",
  "all_payloads_verified": true,
  "performance_ranking_authorized": false,
  "scopes": [
    {
      "case": "work/bionic-airflow-20261012/coupled-equilibrium-084",
      "scope": "all_native_inputs_mesh_logs_histories_fields_and_receipts",
      "performance_accepted": false
    },
    {
      "case": "work/bionic-coupled-equilibrium-20261013",
      "scope": "budget_limited_rest_history_input_comparison_and_absent_final_fields",
      "performance_accepted": false
    }
  ]
}
```
