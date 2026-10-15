# Suite après raccord — aucune opération supplémentaire préparée

Le raccord natif après projection 083 est admis et conserve exactement la région
tournante. Aucun test de repos n’est encore effectué sur cette topologie à deux
cellules radiales fixes. Les repos 064/076 concernent d’autres maillages. Un
éventuel nouveau contrôle doit conserver équations, pas, durée physique,
critères et budget préalables ; ne pas transformer un dépassement de budget ou
un plafond de pression en succès ni augmenter arbitrairement les tolérances.

La prochaine difficulté du vrai turbo reste la protection du raccord pendant
le raffinement et la création des sous-domaines contenant les parois physiques.
082/083 qualifient un raccord, pas cette protection. Inspecter les opérations
natives et leurs contraintes avant un témoin local distinct. limitRegions ne
protège pas toutes les étapes danglingCellRefine/consistentRefinement ; ne pas
utiliser minRefineCells=-1 pour masquer les défauts. Préserver quads du raccord,
faces partagées, volumes, géométrie tournante et qualité native, avec parenté
indépendante après toute renumérotation. Aucun snappy en bloc sur le vrai turbo.

Le modèle présent conserve une paroi extérieure synthétique gauchie et un volume
différent de la cible. La création des couches et la fidélité des surfaces
physiques restent ouvertes. Préserver les sources exactes, le profil 027/030,
l’anneau arrière et la séparation roue–écrou corrigée en 033. Aucun déplacement
de pièce ou changement de jeu/patch/connexion réel. Les cartes 078 valent pour
078 ; aucune carte héritée n’est un adressage global du maillage final.
