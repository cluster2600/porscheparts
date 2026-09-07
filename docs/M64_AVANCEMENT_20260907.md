# M64 turbo 4V — état des preuves au 7 septembre 2026

**Le projet n'a pas encore livré une culasse fonctionnelle, qualifiée ou
autorisée à imprimer.** Les contrôles logiciels, les contrôles de géométrie et
les calculs physiques ci-dessous portent sur des objets différents. Ils ne
s'additionnent pas en une validation globale du moteur.

## Résultats livrés

| Objet exact | Résultat démontré | Ce qui n'en découle pas |
|---|---|---|
| [Corps privé F43 avec quatre logements](M64_FOUR_SEAT_BODY_CAD_AUDIT.md) | STEP monobloc fermé, contrôles BRep/BOP exécutés sans défaut après correction locale des p-curves ; huit positions discrètes soupape/corps sans intersection volumique. | Interfaces M64, conduits, chambre finale, distribution, résistance, refroidissement ou imprimabilité. |
| [Module indépendant quatre soupapes V2](M64_FOUR_VALVE_DISTRIBUTION_MODULE_20260907.md) | Douze composants séparés : quatre soupapes, quatre sièges et quatre guides ; géométrie et contrôles de packaging documentés. | Serrages à chaud, ressorts, lois de came, piston, fatigue ou performances moteur. |
| [Coupon AdditiveFOAM F58](917_F58_COUPON_ENERGY_DIAGNOSTIC.md) | Deux calculs thermiques à 100 et 50 ns jusqu'à 120 µs ; bilan discret recomputé. Le limiteur retire environ 10,6 % de l'énergie laser absorbée. | Simulation d'impression de la culasse complète, recette LPBF fournisseur, distorsion globale ou qualification du matériau. |
| [Chaîne NVIDIA distante](../twins/m64-cylinder-head/remote-simready/README.md) | Les opérations réellement exécutées et leurs échecs sont consignés séparément dans les reçus de cette chaîne. | Une affectation de matériaux visuels ou de corps rigides n'est pas une simulation CFD/CHT ou un calcul de contraintes. |

Le dernier essai GPU a effectivement réussi le précontrôle NVIDIA, la
conversion du STEP V2 et le contrôle minimal USD. Un contre-contrôle local
des instances composées confirme douze composants, les unités mm et Z-up,
avec un écart maximal de boîtes au STEP de 1,804e-6 mm. Il ne s'agit ni d'un
contrôle de déviation complète des surfaces ni d'une tolérance de fabrication.
Le [USD converti conservé](../twins/m64-cylinder-head/evidence/omniverse-static-v2-20260907/converted-assembly.usd)
ne contient pas le corps de culasse et n'a pas reçu d'affectation matériau
ou physique réussie.

Material Agent a échoué avec `material_pipeline_failed`, étape précise non
identifiée. Son statut rapporte 60 rendus et la préparation de douze entrées,
mais aucun USD final ni artefact téléchargeable n'a été livré. Les 60 images
ne figurent pas dans la collecte ; elles ne sont donc pas présentées comme
des preuves visuelles inspectées. Physics Agent, conformance et validations
finales n'ont pas été exécutés. La location a été supprimée et son absence
vérifiée indépendamment ; la collecte opérateur contient 29 fichiers.

Le corps conserve comme référence la silhouette issue du scan 935 ; il n'est
pas rebaptisé géométrie OEM M64. L'échelle 1 unité/mm et le recalage Z −90° / Z+3
restent des hypothèses. Les perçages ont des effets locaux mesurés sur la peau :
aucune forme ovale de substitution n'a été introduite, mais aucune identité
stricte de toute la peau extérieure n'est revendiquée.

Le scan, le corps dérivé et ses images détaillées restent privés. Les reçus
publics contiennent nos contrôles numériques et les empreintes des fichiers,
pas les sources propriétaires. Le STEP du module V2 indépendant constitue un
autre artefact ; ses résultats ne qualifient pas le corps privé.

## Chemin critique restant

1. Définir les conduits et la chambre sur cette géométrie, puis le porte-arbres,
   les ressorts et commandes, les galeries d'huile, les filetages et reprises
   d'usinage. Consigner les interfaces et dimensions choisies comme hypothèses
   lorsque leur provenance M64 n'est pas établie.
2. Vérifier tout le cycle mécanique avec le piston et les dilatations ; choisir
   et justifier les serrages des sièges/guides, les matériaux et leurs cartes
   à chaud. Un ajustement nominal sans intersection n'est pas un montage
   réalisable ni un transfert thermique qualifié.
3. Construire les vrais domaines gaz, solide et air de refroidissement de
   cette version complète pour CFD/CHT et résistance. Les anciens calculs sur
   coupons, volumes simplifiés ou autres itérations ne sont pas transférables
   automatiquement à son SHA256.
4. Corriger et calibrer le modèle LPBF sur des données cohérentes de procédé,
   puis contrôler supports, évacuation de poudre, distorsion de construction,
   usinage et inspection sur la géométrie finale. Le petit résidu de F58 ne
   rend pas physique le puits d'énergie artificiel identifié.

Les données manquantes ne seront pas remplacées par des valeurs annoncées
comme mesurées. Sans preuve de compatibilité moteur, qualification matériau /
procédé et revue professionnelle documentée, aucune autorisation d'impression
pour fonctionnement moteur ou de démarrage ne sera émise.

## Vérification du lot

`make check` a réussi après intégration du diagnostic F58 et du correctif de
sélection SSH : la découverte générale a exécuté 1 989 tests, puis les cibles
complémentaires du dépôt ont réussi. Ce décompte est celui des tests logiciels,
pas celui d'essais moteur. Le journal complet est conservé localement ; les
rapports spécialisés liés ci-dessus définissent la portée de chaque résultat.

La documentation sépare délibérément source, hypothèse, opération exécutée,
résultat numérique et autorisation de fabrication. Le workflow NVIDIA impose
également des contrôles USD explicites plutôt que de considérer une image ou
un code de retour comme une preuve de physique moteur.
