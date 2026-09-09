# M64 — champ de taille natif : remaillage toujours incomplet

**Le remplacement du callback Python par des champs Gmsh natifs ne termine
pas le remaillage dans le budget fixé. Aucun nouveau candidat ni gain de
qualité n'est établi. Le contour Porsche et le maître restent inchangés.**

Cet essai suit le [callback incomplet](M64_LOCAL_SIZE_TRIAL_20260909.md).
Les entrées sont les mêmes, avec un helper natif ajouté et épinglé par SHA.
Un seul lancement sur Kali : quatre CPU, 4 Gio, aucune nouvelle location Vast.

## Ce qui a changé

La loi de taille est exprimée par cinq champs Gmsh 4.15.2 :
deux `MathEval`, deux `Restrict`, puis un `Min`. Elle limite la taille
autour du sommet 51 sur les faces 30/37 et autour des deux segments de
l'arête 99 sur la seule face 37. La distance aux segments est analytique,
pas une distance à la courbe CAO continue.

La pente 0,25, le profil de l'arête 82 et le plancher de taille sont
conservés. C'est la même loi mathématique visée ; l'ordre des opérations
flottantes diffère, donc aucune identité binaire avec le callback n'est
revendiquée. Aucun callback Python de taille n'est installé.
Ces paramètres décrivent le maillage, pas des cotes de fabrication.

Le code vérifie les champs avant la génération et prévoit leur retrait
ensuite. Il journalise désormais les phases et la sortie native Gmsh.
Les tests logiciels ne prouvent pas à eux seuls l'évaluation native du champ.

## Résultat observé

| Étape | Temps mural depuis le début du worker |
|---|---:|
| Profil 1D temporaire vérifié | 1,100 s |
| Réinjection du maillage source vérifiée | 7,584 s |
| Remplacement 82 conforme aux enregistrements de référence | 9,521 s |
| Installation et relecture des champs atteintes avant génération 2D | 9,531 s |

La réinjection produit exactement le SHA source `7af7f207…`.
Le journal confirme ensuite le remaillage des faces 30 et 37. Sur 37,
Gmsh signale successivement **8, 18, 12 puis 6 éléments invalides**, des
auto-intersections du maillage 1D et des reprises avec raffinement des arêtes
bordantes. Ces nombres sont des états intermédiaires, pas un résultat final
ni une convergence démontrée. Le journal ne prouve pas des intersections
physiques de la culasse.

Le processus sort avec le **code 137**, après **250,146 s nettoyage compris**.
C'est compatible avec `SIGKILL` sous la limite CPU dure de 250 s ; ce n'est
pas un reçu indépendant identifiant la cause du signal. La limite souple
est de 240 s CPU cumulé ; le gestionnaire Python de signal peut être retardé
pendant un appel natif. Aucun timeout mural ni OOM n'est signalé.

Le conteneur exact a été supprimé et son absence revérifiée.
Les douze entrées, le worker et le lanceur sont inchangés.
**Aucun MSH brut/candidat ni rapport final du worker n'a été sauvegardé.**
Le retrait des champs, la conservation finale des arêtes, les contacts et
la qualité finale ne sont donc pas attestés. Le contrelecteur n'est pas
exécuté sans candidat. Aucun facteur d'accélération ne peut être calculé
à partir de ces deux essais inachevés.

## Décision et suite utile

Ne pas répéter ce même essai avec davantage de CPU en promettant un gain.
La voie native atteint encore les reprises de maillage de la face 37 :
le coût n'est pas attribuable au seul callback Python.

Le minimum historique de borne `0,888285…` sur la face 30 n'est **pas**
une exigence physique pour 700 ch. La borne théorique et le seuil
diagnostique `0,1` restent des indicateurs de suivi ; ils ne remplacent
ni la conformité du domaine ni les contrôles d'un maillage volumes finis.
Les refus antérieurs restent conservés, sans abaissement silencieux de garde.

La prochaine étape est un diagnostic du **domaine hybride complet** :

1. Réassembler sur copie le cœur `e873b8ae…` avec les 67 200 hexas et
   384 pyramides conservés, en vérifiant les raccordements et les labels.
   Les 1 536 triangles latéraux des pyramides doivent devenir internes,
   jamais des parois artificielles.
   Ne pas y incorporer les pilotes de surface `7af7f207…` ou `2de5fd52…` :
   ils ne correspondent plus à la frontière fixe du cœur `e873b8ae…`.
2. Exporter le domaine complet en MSH 2.2 ASCII et attribuer les groupes
   `inlet`, `receiver_outlet`, `walls`, `air` à partir des preuves source.
   Le cœur seul ne représente pas ce domaine.
3. Utiliser le parcours existant `check_openfoam_mesh.py`, sans solveur :
   conversion, échelle hypothétique 0,001 m/unité appliquée une seule fois,
   patches, puis `checkMesh -allTopology -allGeometry`.
   Son reçu doit attester ce maillage exact et ses frontières, sans inventer
   une autorisation CFD. Le superviseur doit limiter le temps total.

Ces trois étapes ne sont pas exécutées par le présent lot. Un éventuel
`Mesh OK.` resterait un diagnostic numérique, pas une validation des
interfaces M64, des charges biturbo, de la résistance ou de l'impression.

Les **42 tests logiciels distincts** passent : 21 worker, 11 champs natifs,
10 lanceur. `make check` termine avec le code 0 ; des tests optionnels sont
ignorés selon les dépendances disponibles.
Le [registre de preuves](../twins/m64-cylinder-head/evidence/geometry-checkpoint-20260908.json),
entrée `gas_native_2D_size_trial`, conserve les empreintes et les inconnues.
La [stack de la photo](M64_MULTIPHYSICS_EXECUTION.md) ne change pas ces limites :
Ditto/MQTT attendent des mesures de banc ; PhysicsNeMo attend des calculs
éligibles pour son entraînement et son évaluation.

```mermaid
flowchart LR
    A["Référence inchangée"] --> B["Champs natifs installés"]
    B --> C["Reprises répétées de la face 37"]
    C --> D["Arrêt 137 ; aucun candidat"]
    D --> E["Essai archivé ; aucun gain crédité"]
    E --> F["À faire : réassembler le domaine hybride"]
    F --> G["À faire : contrôle OpenFOAM sans solveur"]
```
