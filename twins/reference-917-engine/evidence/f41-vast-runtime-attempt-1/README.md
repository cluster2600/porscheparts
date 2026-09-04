# F41 — première tentative runtime Vast

La première qualification supervisée de l'image CAD F41 a été lancée le
3 septembre 2026 depuis le commit public
`35aed0b63b3fe642c0b32155deb0f3d995a4ebad`. Elle a échoué avant le transfert
du bundle et avant toute génération CAO : le wrapper a vu l'instance en état
`running`, mais son ancien probe n'a pas distingué un timeout de transport SSH,
un défaut d'authentification ou un échec de `/workspace/READY`.

L'instance 49700054 n'est plus présente. Après l'échec, le superviseur a
conservé 30 inventaires complets et valides, espacés sur 59 secondes. Ils sont
identiques au baseline antérieur au lancement et ne contiennent ni cet ID, ni
le label exact de tentative, ni aucun membre de la famille F41. Un inventaire
indépendant ultérieur confirme encore cette absence. Cela lève le risque de
facturation de cette tentative, sans la transformer en succès.

Le code critique 97 venait d'un défaut de protocole : le child avait effectué
son rollback, mais n'en transmettait la preuve que par une note d'exception non
rendue par la CLI. Le correctif suivant ajoute un reçu JSON strict après DELETE
confirmé et absence paginée, puis exige encore cinq inventaires complets côté
superviseur. Le probe SSH utilise désormais des catégories fixes, une lecture
bornée et un état `onstart` atomique. Un nouvel essai doit employer un autre
hôte, un nouveau label et un nouveau dossier de sortie.

Aucun STEP, STL, 3MF, USD, rendu ou résultat de simulation n'a été produit par
cette tentative. Les captures runtime restent hors du dépôt car elles incluent
l'inventaire d'autres locations sans rapport avec F41. Seule leur synthèse
textuelle et leurs empreintes non réversibles sont versionnées ici.
