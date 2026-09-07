# F48 — domaines CFD analytiques 2V / 4V

F48 isole un problème vérifiable : construire des **volumes fluides**, sans
importer ni approximer la peau extérieure du scan. Le résultat est un domaine
gaz 2V, un domaine gaz 4V et un domaine huile commun, tous générés nativement
avec Gmsh/OpenCASCADE à partir des hypothèses géométriques F47.

La porte géométrie/maillage CFD passe pour ce périmètre de recherche. Ce n'est
pas un calcul d'écoulement, une validation CHT, une preuve de culasse solide ou
une autorisation de fabrication.

## Résultats gaz

| Variante | Niveau | Taille max | Tétraèdres | minSICN min | minSICN p01 | <= 0 | < 0,1 |
|---|---|---:|---:|---:|---:|---:|---:|
| 2V | coarse | 6,0 | 7 496 | 0,3019 | 0,3704 | 0 | 0 |
| 2V | medium | 4,0 | 22 063 | 0,2722 | 0,3627 | 0 | 0 |
| 2V | fine | 2,5 | 83 767 | 0,2424 | 0,3733 | 0 | 0 |
| 4V | coarse | 6,0 | 9 660 | 0,2966 | 0,3680 | 0 | 0 |
| 4V | medium | 4,0 | 25 951 | 0,2926 | 0,3669 | 0 | 0 |
| 4V | fine | 2,5 | 95 381 | 0,2715 | 0,3682 | 0 | 0 |

Le volume géométrique vaut 260 701,005 unités scan³ en 2V et 291 788,011 en
4V, sans variation entre les trois maillages. La surface frontière totale vaut
36 808,495 puis 47 894,809 unités scan². Chaque surface est affectée exactement
une fois à `intake`, `exhaust`, `valve`, `chamber`, `deck`, `bore` ou `walls`.
Le domaine est complet à 360° : un patch `symmetry` serait non physique et
n'est donc pas créé.

## Domaine huile

Le domaine huile est une galerie de lubrification séparée avec deux extrémités
et deux accès de nettoyage ouverts au sens des conditions aux limites. Le
maillage medium contient 1 937 tétraèdres, minSICN minimal 0,3107, p01 0,4156,
et zéro élément inversé. Il n'est jamais traité comme une chemise d'eau ou un
refroidissement liquide.

## Géométrie et nuance OpenCASCADE

Le constructeur appelle exclusivement des cylindres circulaires fonctionnels
et des fusions. Il n'appelle aucune primitive de profil ou surface elliptique,
ovale, boîte ou enveloppe proxy. OpenCASCADE peut nommer `Ellipse` certaines
courbes coniques créées automatiquement à l'intersection oblique de deux
cylindres circulaires. Ce nom de courbe d'intersection ne correspond pas à un
port ou une enveloppe elliptique conçu par F48.

## Fichiers

- `f48-cfd-domain-report.json` : géométrie, patches, qualités et hashes;
- `publication.json` : empreintes du paquet public;
- `917-f48-cfd-domain-overview.png` : patches 2V/4V;
- `917-f48-cfd-domain-sections.png` : coupes du maillage medium et huile;
- contrat : `twins/reference-917-engine/cfd-domain-contract-f48.json`;
- constructeur et renderer : `twins/reference-917-engine/source/`.

Les BREP et MSH analytiques sont reproductibles mais restent hors Git. Aucun
scan, STEP privé ou maillage dérivé du scan n'est publié.

```bash
python3 twins/reference-917-engine/source/build_cfd_domains_f48.py \
  --contract twins/reference-917-engine/cfd-domain-contract-f48.json \
  --output work/917-f48-cfd-domains/domains \
  --report work/917-f48-cfd-domains/report.json
make 917-f48-cfd-domain-test
```

Toutes les cotes restent des hypothèses de recherche sous convention d'unité
du scan. Les portes fitment OEM, solide, épaisseur, FEA, CHT, impression métal
et démarrage moteur restent fermées.
