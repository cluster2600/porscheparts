# Essai local C2 : surface construite, renfort rejeté

Le renfort essayé sur le trajet isolé le plus mince restant a été **rejeté
avant toute construction de face ou de solide**. L'amplitude et les bords
sont respectés, mais la déformation forme une zone beaucoup trop pointue
pour ce contrôle géométrique exploratoire. Aucun nouveau calcul thermique,
mécanique, LPBF ou de rayons dans un solide n'a été lancé.

La source est toujours la reconstruction F53 issue du scan de référence
935, **pas une culasse M64 validée**. Toutes les longueurs ci-dessous sont
des unités du scan, dont l'échelle absolue n'est pas certifiée. L'essai est
séparé du [candidat Bernstein 10 × 11](M64_LOCAL_BERNSTEIN_REPAIR_20260907.md)
qui avait passé ses contrôles locaux. Les deux fichiers maîtres sont intacts.

## Construction effectivement exécutée

Le trajet initial vaut `1,0524179419`. Le point d'entrée de la surface a été
déplacé de `0,5475820581` suivant la direction opposée au rayon mesuré, avec
un objectif exploratoire de trajet `1,60`. **Cet objectif n'est pas un
nouveau résultat d'intersection d'un solide**, puisque l'essai s'arrête
avant cette étape.

Le support choisi est le plus grand rectangle UV centré sur le point cible
et contenu dans la face bilinéaire existante. Sur chaque direction locale,
le facteur est `b(t) = 64 t³(1−t)³`, et le déplacement est
`D = δ b(s) b(t)` à l'intérieur, nul à l'extérieur. La valeur et les deux
premières dérivées s'annulent aux frontières du support. OCCT a construit
une surface de degré 6 × 6 ; la suppression des multiplicités excédentaires
des nœuds intérieurs a réussi à `1e-12`, donnant une multiplicité 4, donc
une continuité paramétrique C2 de cette surface.

Le facteur de Bernstein `B₃⁶` atteint au plus `5/16` ; le produit atteint
au plus `25/256`. Le coefficient scalaire flottant enregistré, interprété
comme rationnel exact, donne donc la borne continue :

```text
|D| ≤ 2466090352735025 / 4503599627370496
    = 0,5475820580824797 < 1 unité du scan
```

Cette borne concerne le **champ scalaire avant la suppression native des
nœuds**, pas une borne globale des erreurs d'arrondi OCCT. L'accord entre
formule et surface native est vérifié séparément par échantillonnage.

## Résultats et arrêt

| Contrôle | Résultat |
|---|---:|
| Points d'évaluation natifs sur la surface | 14 641 |
| Écart maximal formule / OCCT | `7,45e-14` unité |
| Erreur du point cible déplacé | `1,59e-14` unité |
| Écart maximal des quatre courbes / surface, 121 points par courbe | `3,70e-12` unité |
| Déplacement natif maximal échantillonné | `0,5475820581` unité |
| Rapport d'orientation minimal échantillonné | `0,997802` — positif |
| Norme maximale du gradient tangent de déplacement | **`5,418716`** |
| Rotation maximale de la normale | **`79,5427°`** |
| Plus petit rayon principal échantillonné | **`0,0082114` unité** |
| Courbure principale absolue maximale, source / essai | `0,012124` / `121,781924` unité⁻¹ |

Le filtre de pente choisi **avant le résultat** est une norme du gradient
tangent au plus égale à 1. C'est un filtre géométrique exploratoire destiné
à exclure une pointe, **pas une limite matériau, une norme LPBF ou une preuve
de défaillance mécanique**. Lui seul échoue dans cette exécution. Les
rotations et courbures quantifient la dégradation ; leurs extrema sont
échantillonnés et ne constituent pas des bornes continues.

La réussite de C2 signifie continuité des dérivées ; elle ne garantit pas
une faible courbure. De même, une amplitude bornée et une orientation
positive ne suffisent pas à rendre ce renfort acceptable. Le candidat est
conservé comme diagnostic, sans couture, export STEP de solide, BOP ou
nouveau contrôle des 42 rayons.

## Les quatre bords ne sont pas quatre interfaces moteur démontrées

L'audit existant identifie quatre **limites isoparamétriques d'une face de
reconstruction**. Il ne leur attribue pas de fonction mécanique. Le
[générateur F43](../twins/reference-917-engine/source/build_scan_contour_patch_reconstruction_f43.py)
forme la peau externe par sections réglées entre contours polygonaux :
ce procédé introduit des limites de faces numériques. Les données lues ne
permettent pas de classer individuellement les quatre bords du présent
essai en interface physique, bord d'ailette ou simple couture.

Leur immobilisation était donc une **contrainte conservatrice de cet
essai**, pas une exigence Porsche établie. Le rejet n'établit ni
l'impossibilité d'épaissir la zone, ni la nécessité d'une pointe. Avant une
autre stratégie, il faut attribuer les frontières et les faces voisines
réelles ; on ne doit pas transformer une couture artificielle en frontière
physique intangible. Cette attribution supplémentaire n'a pas été exécutée
pendant la clôture de cet essai.

## Reproductibilité et intégrité

Script : [trial_isolated_transition_c2.py](../twins/m64-cylinder-head/trial_isolated_transition_c2.py).
Exécution native terminée avec code 0, statut `rejected_surface_quality`,
sur Kali, deux CPU, 4 Gio et plafond de 300 secondes. Code 0 signifie ici
que le diagnostic a terminé, **pas que le candidat est accepté**. L'essai
refuse un répertoire de sortie existant et ne modifie aucun STEP d'entrée.

Artefacts privés dans
`/tmp/917-f50/out/m64-isolated-transition-C2-1743-20260907/` :

- `surface-report.json`, SHA `db2f18928be6cb4e8760990848e1c44369b199f17baeb4f619c314b09765a306` ;
- `private-C2-surface.npz`, SHA `8704820f4f82411dbe3591628ff5f80b1be4a677981760ad545c22584cba46a3`.

Les hashes ont été revérifiés après l'essai : F53 reste
`700baea66bc72cdb6aee529e21b167270ebde11db94b06f8e1e55ee08bdd9bf2`,
et le solide Bernstein 10 × 11 reste
`42057011e25ecc48b215a58e979a0d9bcf4769f2f96f9690b751a81a7bde2cd8`.
Les coordonnées, pôles, fichiers STEP et NPZ demeurent privés.

Le [résumé expurgé](../twins/m64-cylinder-head/evidence/isolated-c2-surface-rejection-20260907.json)
conserve les seuls agrégats et les références de preuve. Le skill
`engineering:documentation` a guidé la présentation du résultat avant les
étapes et la séparation entre contrôles exécutés et étapes non réalisées.
