# M64 — tentatives Vast du 6 septembre 2026

## Résultat réel

Deux instances ont été créées puis supprimées par le contrôleur de protection.
Les deux suppressions ont été acquittées et l'absence vérifiée sur cinq
inventaires successifs. Aucun test GPU, calcul culasse ou rendu Omniverse
n'a été obtenu de ces tentatives. Ne pas réessayer automatiquement en boucle.

| Instance | Offre | Tarif annoncé, calcul + 500 Go | Résultat |
| --- | --- | --- | --- |
| 50100733 | 47719142, Utah, RTX PRO 6000 WS, 128 cœurs effectifs annoncés, 128104 Mo RAM | 1,505185 USD/h | Chargement puis état `offline` avant vérification SSH READY ; suppression vérifiée |
| 50101149 | 49942717, Hong Kong, RTX PRO 6000 WS, 24 cœurs effectifs annoncés, 128638 Mo RAM | 1,585185 USD/h | API Vast HTTP 429 pendant le lancement supervisé ; suppression vérifiée |

L'état `offline` ne prouve pas la cause de l'échec de la première machine.
Le HTTP 429 signale un refus API, pas un échec du solveur ou de CUDA.
L'image téléchargée comporte 34 624 357 174 octets de couches compressées.
Les coûts de transfert s'ajoutent au tarif horaire. La facture effective et le
solde ne sont pas disponibles via les opérations du wrapper interrogées ;
aucun total dépensé n'est présenté comme une valeur facturée.

## Contrôles effectués avant location

- Wrapper approuvé `/Users/maxime/.local/bin/openbao-vastai` : contrôle lecteur
  et authentification réussis, inventaire initial vide.
- Clé SSH locale déjà approuvée vérifiée et enregistrée, sans lecture de son contenu.
- Digest GHCR relu :
  `ghcr.io/cluster2600/3dprinting993-simready-local-ai@sha256:5a69a6805a275ef708e264600cb933663159a2846b069eafe0459c28e5f69699`.
- Workflow GitHub 33730827271 relu : `completed`, `success`, révision
  `009a880b93232f0a43876a98fcc3d2e0740299b4`.
- Le dossier F49 contient les preuves de build linux/amd64 et des tests CPU ;
  elles ne sont pas une preuve d'exécution GPU sur ces deux hôtes.
- Première tentative protégée en plus par un garde-fou local de suppression
  à 40 minutes, arrêté après confirmation de suppression anticipée.
- Aucun secret, scan ni fichier de culasse transféré dans ces tentatives.

## Suite avant nouvelle dépense

1. Contrôler le solde et la dépense cumulée dans la limite de l'autorisation.
2. Traiter la limitation API (cadence/backoff des contrôles) sans relancer
   de créations à l'aveugle ni affaiblir les contrôles de suppression.
3. Qualifier le runtime NVIDIA ; exiger des journaux de services et un calcul
   CUDA réel avant de lui attribuer un travail d'ingénierie.
4. Garder les développements et essais CPU sur Kali entre-temps.

La pile M64 n'est pas entièrement qualifiée. La CAO M64 complète, les champs
CHT, les contraintes et la simulation LPBF de la pièce restent à produire.
