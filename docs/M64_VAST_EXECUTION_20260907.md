# M64 — essai Vast du 7 septembre 2026

## Autorité et budget

L'utilisateur annonce **20 USD restants** et autorise la suite. Ce montant
est le plafond de travail, pas un solde vérifié via API. Aucune recharge.
Une seule instance payante créée pendant cet essai.

## Préparation

- Correctif GET HTTP 429 et cadence SimReady : 87 tests unitaires réussis.
- Wrapper installé identique au wrapper testé ; accès par OpenBao existant.
- Clé privée approuvée vérifiée et clé publique enregistrée par le wrapper.
- Image GHCR immuable vérifiée :
  `ghcr.io/cluster2600/3dprinting993-simready-local-ai@sha256:5a69a6805a275ef708e264600cb933663159a2846b069eafe0459c28e5f69699`.
- CI de cette image : exécution `33730827271`, conclusion `success`.
- Deux demandes visant l'offre Washington `48366367` ont été refusées avant
  création : offre absente de la recherche admissible au moment du lancement.

## Instance réellement créée

| Champ | Observation fournisseur |
|---|---|
| Offre / instance | `47185008` / `50126532` |
| Région | Thaïlande |
| GPU | RTX PRO 6000 WS, 97 887 Mo annoncés |
| CPU / RAM | 64 CPU effectifs / 128 726 Mo |
| Disque alloué | 500 Go |
| Tarif horaire annoncé, stockage inclus | 1,470888889 USD/h |
| Transfert entrant / sortant | 0,002604167 / 0,00390625 USD/Go |
| Label | `3dprinting993-simready-local-ai-cd13434ab2b657259f64` |

Un garde-fou local de suppression ciblée à 45 minutes a été lancé. Il a été
arrêté après confirmation de suppression anticipée. Ce garde-fou dépend de
l'accès au fournisseur ; il ne constitue pas une garantie de facturation.

## Résultat : échec avant les calculs

L'instance est passée de `loading` à `running`, mais le contrôle SSH a échoué
avec `ssh_authentication_failed`. Le fichier `/workspace/READY` n'a pas été
vérifié. Aucun transfert de culasse, rendu Omniverse, entraînement PhysicsNeMo
ou calcul thermique/mécanique de culasse n'est démontré par cet essai.

Le contrôleur a supprimé l'instance automatiquement : acquittement fournisseur
reçu, puis **cinq instantanés d'absence consécutifs**. Une lecture indépendante
finale `openbao-vastai instances` retourne `[]`.

Le montant réellement débité n'est pas disponible dans les résultats de ce
wrapper : il n'est ni inventé ni assimilé à zéro. Pas de nouvelle location
payante à l'aveugle après cet échec. Le diagnostic SSH est poursuivi hors ligne.

Le diagnostic a reproduit un défaut d'appariement hôte/port : proxy et connexion
directe pouvaient être mélangés lorsque le port proxy était absent. Correction
dans le dépôt et dans le wrapper installé, identiques par `cmp` ; **90 tests
wrapper réussis**. Faute de métadonnées brutes de l'endpoint, ce défaut n'est
pas établi comme cause de l'échec `50126532`. Aucun nouvel essai payé après
ce correctif.

## Vérification du dépôt

`make check` a été exécuté : les contrôles ont passé jusqu'au manifeste de
préparation F46, devenu périmé à cause du changement de hash du wrapper.
Ce manifeste a été régénéré avec son générateur : seuls taille et SHA-256 du
wrapper ont changé, sans nouvelle autorité physique. La cible interrompue et
toutes les cibles restantes de `check` ont ensuite été rejouées avec succès.
La suite wrapper finale a été relancée séparément : 90 tests réussis.

La cible reste le **M64 turbo 964/993**. Les anciens résultats 917 et les
géométries de recherche issues du scan 935 ne valident pas ses interfaces.
`simulation_validated=false`, `manufacturing_authorized=false`.
