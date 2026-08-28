# Contribuer

## Avant de commencer

1. Ouvrir une issue « Nouvelle pièce ».
2. Confirmer que la pièce n’existe pas déjà dans `catalog/parts/`.
3. Décrire la provenance des données et la licence envisagée.
4. Choisir la classe de sécurité la plus prudente.

## Ajouter une pièce

```bash
cp templates/part-record.json catalog/parts/993-xxx-0001.json
mkdir -p parts/993-xxx-0001/{source,derived,evidence}
make check
```

Règles :

- Le nom de dossier doit correspondre à `part_id` en minuscules.
- Les sources modifiables vont dans `source/`.
- Les exports STEP, 3MF ou STL vont dans `derived/`.
- Les rapports, mesures et photographies autorisées vont dans `evidence/`.
- Aucun fichier ne doit être présenté comme validé avant essai documenté.
- Ne pas ajouter de gros binaire sans discussion préalable dans l’issue.

## Pull request

La PR doit indiquer :

- ce qui est ajouté ou modifié ;
- les sources et licences ;
- la classe de sécurité ;
- les validations réellement effectuées ;
- les validations encore manquantes ;
- le résultat de `make check`.

Le maintien d’un statut prudent est préférable à une affirmation non vérifiée.
