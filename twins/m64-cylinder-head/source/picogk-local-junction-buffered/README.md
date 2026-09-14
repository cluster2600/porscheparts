# Raccord local — témoin avec masque intérieur

Le témoin reste constitué des mêmes deux cylindres étagés, sans culasse
privée. Rayon de fermeture : 1 unité. Pas : 0,2. La région autorisée reste
`[-8,-3,-8] → [8,3,8]`. Le masque de construction est reculé de `3h`, soit
0,6 unité, sur ses six côtés. Ce recul est une hypothèse préenregistrée dans
`criteria.json`, pas une garantie mathématique de l'extraction.

La construction est `A ∪ (C ∩ Rintérieur)`, avec `C = fermeture(A)`.
L'ajout `(C \ A) ∩ Rintérieur` reste diagnostique, sans intervenir dans cette
construction. Les contrôles utilisent toujours la région autorisée extérieure.
Le runtime épinglé appelle `RebuildGrid`, mais cette méthode est un no-op :
aucune reconstruction effective ne lui est attribuée.

## Résultat du 8 septembre 2026

Le natif s'est terminé en **5,278 s**, pic processus **185 507 840 octets**,
sur Kali avec 2 CPU / 4 Gio, réseau désactivé, limite 300 s. La compilation
a réussi avec NU1900 : consultation des vulnérabilités NuGet indisponible
hors réseau, packages requis déjà présents.

Sur **1 157 625 nœuds** comparables, les deux conventions de zéro (`<0`,
`<=0`) donnent zéro changement hors ROI ou aux interfaces protégées, zéro
perte de gaz et zéro contact de l'ajout avec le bord autorisé. Respectivement
1 944 et 828 nœuds changent à l'intérieur. Les **valeurs SDF** comparées sont
aussi inchangées hors ROI et aux protections : maximum des différences nul.
Les longueurs sont déjà les unités monde, nommées MM par PicoGK pour ce témoin
synthétique ; aucune multiplication supplémentaire par le pas n'est appliquée.

Les six champs sauvegardés en VDB ont été relus et leurs valeurs float
comparées **bit à bit sur chacune de leurs boîtes natives englobantes** :
aucune différence. Les valeurs au-delà de ces boîtes n'ont pas été comparées.
Cette preuve de sérialisation n'est ni une preuve de qualité de la distance
signée, ni une validation physique.

| Surface | Faces brutes | Faces exactement nulles retirées dans la copie | Résultat normalisé |
|---|---:|---:|---|
| Avant | 89 708 | 0 | Une composante fermée orientée combinatoire |
| Après | 90 028 | 16 | Une composante fermée orientée combinatoire |
| Ajout diagnostique | 4 464 | 8 | Une composante fermée orientée combinatoire |

**Le rejet brut reste conservé.** La normalisation est une étape distincte :
suppression en mémoire des seuls triangles d'aire exactement nulle selon un
prédicat entier dyadique, sans déplacement, suppression de triangle non nul,
remplissage, retriangulation, réparation de normale ou composante écartée.
L'audit combinatoire inclut les liens de sommets, les incidences d'arêtes,
les faces dupliquées et les orientations.

Le multiensemble des triangles orientés normalisés trouve 5 804 faces retirées
et 6 108 ajoutées : **aucune n'a son support hors de la ROI autorisée**.
La ROI étant convexe, le contrôle de ses trois sommets contient le triangle
entier. C'est une preuve sur les deux surfaces triangulées données, pas sur
un B-Rep ou un champ continu sous-jacent. L'auto-intersection géométrique et
l'imbrication des coques ne sont pas qualifiées par cet audit combinatoire.

Le résidu `Vaprès − Vavant − Vajout` vaut **3,6186005274230206 unité³**.
Il reste inexpliqué et n'est pas masqué par le succès des gardes déclarés.
Les trois isosurfaces sont extraites séparément ; ce résidu n'est pas un
critère nul préenregistré de cette expérience.

## Stratégie de tests et portée

- Contrats rapides : région autorisée constante, marge 3h, rayon/pas figés,
  distinction masque/contrôle et arrêt avant toute géométrie privée.
- Intégration native : double convention d'occupation, comparaison des valeurs
  du champ et aller-retour VDB bit à bit sur les boîtes natives.
- Contre-calcul : réutilisation de `audit_surface_topology.py` et
  `audit_direct_union_surface.py`, avec empreintes des helpers dans le reçu.
- Régressions de décision : chaque garde d'occupation, de relecture VDB,
  de topologie normalisée ou de support hors ROI doit empêcher le succès.

Le statut obtenu est **`declared_exploratory_screen_pass` pour la chaîne
normalisée uniquement**. Aucune comparaison au pas 0,1 ni application à
l'admission privée n'a été exécutée ou autorisée automatiquement. Le témoin
ne prouve pas un raccord G1, un bénéfice CFD, une tenue mécanique/thermique
ou une imprimabilité.

Empreintes des reçus privés conservés :

- Natif `run-report.json` : `d883eb4796a733d1e05235608f898adb3d67c488e46d38bc00a7979df4de7504`.
- Audit `buffered-surface-audit.json` : `24efb04cfc3049300f97a95bf52f99993a61211fcd397812cd9756e032cb74f1`.
- VDB : `d724db69d3f92f511f06f8842f4597559448ac6c4128c7a0e028247f04ec9c61`.

Les originaux et sorties précédentes restent intacts. Aucun financement Vast
n'a été utilisé pour ce témoin.
