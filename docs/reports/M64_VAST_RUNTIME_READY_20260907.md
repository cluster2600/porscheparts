# Vast : accès rétabli et runtime prêt — 7 septembre 2026

Constat à 06:55 UTC, concernant uniquement l'instance **50130746**.
Lancement effectué par le wrapper approuvé
`/Users/maxime/.local/bin/openbao-vastai`, commande
`launch-simready-heavy 49094462`, avec un identifiant de tentative unique.
Aucune nouvelle recharge autorisée ; plafond utilisateur conservé : 20 USD.

## Résultat réel du lanceur

Le processus supervisé a terminé avec le code **0**. Son reçu confirme :

- image et contrat d'offre vérifiés ;
- paire SSH locale cohérente et clé approuvée listée par le fournisseur ;
- connexion SSH BatchMode réussie, contrôle strict de la clé d'hôte ;
- instance `running`, marqueur de disponibilité et services Content Agents prêts ;
- test d'exécution GPU PhysicsNeMo réussi.

Matériel : 64 CPU effectifs, 257 582 MB RAM et RTX PRO 6000 WS.
`nvidia-smi` a identifié une RTX PRO 6000 Blackwell Workstation Edition,
97 887 MiB et le pilote 595.84. Tarif annoncé de l'offre avec 500 GB de
stockage : **1,85185185185 USD/h**, hors transfert. Ce n'est pas une facture.
Un garde-fou séparé vise la suppression de cette tentative exacte à
**08:28:46 UTC** ; les délais d'API peuvent dépasser cette échéance.

## Cause du dernier blocage : initialisation, pas authentification

L'authentification SSH fonctionnait déjà. Le démarrage applicatif échouait
avec le code **80** et `simready runtime host-key marker rejected`.
Dans ce conteneur, `/usr/sbin/sshd` était un binaire ordinaire, pas le lien
attendu vers notre initialiseur. L'appel `sshd -T` ne créait donc pas le
marqueur applicatif requis. L'auteur de ce remplacement n'est pas établi.

L'initialiseur original `/usr/local/bin/simready-sshd-runtime-wrapper -T`
a été appelé explicitement, puis le script onstart original relancé.
Les empreintes des clés d'hôte publiques existantes sont restées identiques ;
aucune nouvelle clé publique et aucun redémarrage du listener n'ont été
nécessaires. Les services ont ensuite atteint l'état prêt.

La correction source remplace l'appel indirect par celui de l'initialiseur.
Un test fonctionnel reproduit le code 80 avec le chemin ancien, puis vérifie
le succès du nouveau chemin et l'absence de réinitialisation si le marqueur
existe. **7 tests `test_simready_local_ai.py` passent.**

## Traçabilité et limites

Image réellement exécutée, antérieure à cette correction source :

```text
ghcr.io/cluster2600/3dprinting993-simready-local-ai@sha256:5a69a6805a275ef708e264600cb933663159a2846b069eafe0459c28e5f69699
```

Le correctif n'est pas inclus dans ce digest : le runtime a été débloqué par
l'initialiseur déjà embarqué. Le test PhysicsNeMo prouve les imports et un
calcul tensoriel GPU, pas l'entraînement d'un modèle physique ni un calcul
de culasse. Le reçu conserve `simulation_validated=false` et
`manufacturing_authorized=false`. Aucune validation thermique, résistance,
fatigue, impression ou compatibilité M64 n'est déduite de ce succès.

Ne pas confondre cet incident avec la précédente instance **50128235**,
supprimée alors qu'elle chargeait encore son image : son expiration ne
constituait pas un échec d'authentification SSH.

## Suite de l'exécution : limite d'accès et arrêt demandé

Le contrôle d'accès d'un agent a refusé une commande SSH directe et demandé
une voie OpenBao approuvée. Aucun contournement n'a été tenté après ce refus.
L'inspection des wrappers existants confirme qu'ils exposent le lancement et
les contrôles de disponibilité, mais pas le transfert ou le traitement d'un
asset M64. `property_assignment_intent=run` dans le reçu est une intention,
pas la preuve d'une affectation de propriétés à la culasse.

Une demande d'arrêt a donc été envoyée par `openbao-vastai stop 50130746`
afin de ne pas laisser du calcul sans travail exploitable. Le relevé suivant
du fournisseur indique **`exited`**, pas encore `stopped` ; ce relevé seul ne
permet pas d'attester la suspension de la facturation GPU. Le garde-fou de
suppression de la tentative exacte reste actif. La CAO indépendante sur Kali
peut continuer ; aucune autre location n'a été lancée.

Le contrôle borné d'arrêt s'est ensuite terminé en erreur : l'état `stopped`
n'a pas été confirmé. L'instance exacte a donc été supprimée par
`openbao-vastai destroy 50130746 --confirm`. Le wrapper a confirmé
`destroyed=true` et `verified_absent=true`. Le conteneur et son disque de
travail sont supprimés ; aucun résultat de calcul de culasse n'y avait été
produit. Le source et les preuves enregistrées localement sont conservés.
