# M64 — essai de taille locale incomplet

**Le calcul natif s'arrête sans nouveau maillage candidat ni rapport final.
Aucun gain de qualité n'est établi et aucune géométrie n'est promue.**
Le contour Porsche et le maître restent inchangés.

Ce lot teste la piste annoncée après le
[remaillage conjoint précédent](M64_EDGE82_JOINT_REMESH_20260909.md) :
même recette d'arête 82, puis champ de taille 2D limité aux faces 30/37,
autour du sommet 51 et des deux petits segments de l'arête 99.

## Ce qui est établi

- Un seul lancement natif sur Kali, quatre CPU, 4 Gio ; aucune location Vast.
- Checkpoint de génération 1D temporaire atteint à 1,098 s depuis le début
  du worker. Même profil à 64 nœuds,
  dernier segment 82 / segment voisin 93 = 0,96736.
- Réinjection vérifiée à 7,587 s depuis le début du worker. Le fichier réinjecté est identique octet
  par octet à la référence `7af7f207…`.
- Processus terminé avec le code **152**, après **239,935 s nettoyage compris**.
  Ce code est compatible avec `SIGXCPU` (`128 + 24`) sous la limite CPU
  configurée à 240 s souple / 250 s dure de temps CPU cumulé du processus,
  distinct du délai mural. C'est une attribution cohérente,
  pas un reçu indépendant du signal. Aucun dépassement du délai mural
  ni OOM n'est signalé.
- Conteneur exact supprimé ; absence revérifiée. Entrées et lanceur inchangés.

## Ce qui manque

Le dernier checkpoint précède l'installation du callback et l'appel 2D.
Il porte encore `generate2_calls = 0` : c'est son état à cet instant, pas
une preuve que l'appel n'a jamais commencé ensuite.
Il n'existe ni MSH brut/candidat, ni rapport final, ni compteur d'appels au
callback sauvegardé. Le retrait final du callback n'est donc pas attesté,
même si son chemin `finally` est testé en logiciel ; le processus est arrêté.

Les qualités finales, la conservation finale et les contacts sont **inconnus**,
pas nuls. Le contrelecteur indépendant est prêt, mais n'est pas exécuté sans
candidat. Aucune comparaison chiffrée à trois états n'est possible pour ce lot.

Le champ préparé utilise une croissance de taille de 0,25 par unité de
distance et abaisse le plancher au plus petit segment source de 99.
Ces nombres sont des réglages du maillage, **pas des cotes de fabrication**.
Le code restitue les 63 IDs de lignes 82 du candidat précédent par bijection
d'enregistrements ; cette restitution est contrôlée en lecture pure avant
l'essai, mais aucune sortie finale ne permet ici de la constater après calcul.

## Suite et limites

Avant une relance, instrumenter explicitement l'entrée dans la génération 2D
et sauvegarder une progression bornée des appels de taille. Il faut localiser
le coût avant de choisir entre champ natif, réglage différent et budget CPU
supérieur. L'absence de résultat ne prouve ni une insuffisance mémoire ni
qu'un GPU résoudrait le problème. Ne pas relancer les mêmes entrées inchangées
en prétendant qu'un gain de qualité est déjà obtenu.

Les **52 tests logiciels distincts** passent : 22 worker, 10 lanceur,
7 extension de contrelecture et 13 parent figé. Ils contrôlent le logiciel,
pas la résistance de la culasse. Les empreintes et inconnues explicites sont
dans le [registre de preuves](../twins/m64-cylinder-head/evidence/geometry-checkpoint-20260908.json),
entrée `gas_local_2D_size_trial`. `make check` termine avec le code 0 ; des
tests optionnels sont ignorés selon les dépendances disponibles.

La [stack moteur de la photo](M64_MULTIPHYSICS_EXECUTION.md) reste pertinente,
mais n'est pas une chaîne couplée déjà validée : Elmer est un candidat au
contre-calcul, PhysicsNeMo un modèle à entraîner/évaluer et Ditto/MQTT une
future liaison aux mesures. Aucun résultat CFD, thermique, mécanique,
LPBF, de puissance moteur ou de fabrication n'est crédité par ce lot.

```mermaid
flowchart LR
    A["Référence inchangée"] --> B["1D terminée puis réinjection identique"]
    B --> C["Phase suivante sans trace intermédiaire"]
    C --> D["Arrêt code 152 ; aucun candidat"]
    D --> E["Nettoyage vérifié ; résultat incomplet"]
    E --> F["Instrumenter et profiler avant relance"]
```
