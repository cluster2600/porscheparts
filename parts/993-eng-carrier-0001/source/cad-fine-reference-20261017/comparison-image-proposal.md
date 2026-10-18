# Proposition de planche — attendre la mesure réelle

Statut : proposition uniquement, aucun rendu et aucune valeur de distance
préremplie. La capsule CAD est complète sans cette image.

Titre proposé : **Référence CAD fine et surface retenue — comparaison globale
des maillages**.

Une planche paysage sobre comporterait deux vues réelles, côte à côte, puis
un axe de distance lisible sous les vues. La référence OCP serait bleue et le
STL retenu orange. Même caméra orthographique, même repère et mêmes limites
en millimètres ; les coordonnées originales seraient utilisées directement,
sans recalage ou changement d'échelle indépendant. Les surfaces complètes
seraient rendues ; la rasterisation des seules vues 3D dans SVG/PDF éviterait
de transformer 724 976 triangles en autant d'objets vectoriels.

Chaque vue porterait ses vrais comptes : référence 68 744 sommets/137 572 faces,
STL retenu 293 660 sommets/587 404 faces. La légende de la référence préciserait
« OCP, déflexion absolue demandée 0,01 mm, angle 0,10 rad ; 240 faces CAD extraites ».
Les empreintes courtes `c2aad5a8…` et `443b5ae2…` identifieraient les deux
entrées. Ces comptes ne seraient pas utilisés comme indicateurs de précision.

L'axe inférieur tracerait l'estimation et **l'intervalle réellement retourné**
par le wrapper, ainsi que le critère fixé 0,06 mm. Le libellé d'autorité serait
« Contrat d'erreur API CGAL 6.1.3, symétrique, epsilon 1e-4 mm » ; l'arrondi
extérieur ne serait présenté que pour l'arithmétique d±epsilon, sans certificat
indépendant de conversion interne. Une valeur hors échelle agrandirait l'axe,
sans être tronquée. Le verdict affiché suivrait les données : borne de l’API sous
le critère, intervalle entièrement au-dessus, ou intervalle traversant le
seuil. Aucun de ces cas ne serait renommé admission globale du carrier.

Les valeurs disponibles seraient un intervalle global ; une carte locale
demanderait des distances locales effectivement calculées. Le pied garderait
la portée numérique : « Comparaison de ces deux maillages ; le lien global
BREP↔référence n'est pas démontré par la déflexion demandée. »

## Conditions avant tout rendu

Utiliser uniquement le reçu **réel et complet** de la mesure : retour natif 0,
deux petits cas connus réussis, comptes d'entrées exacts, champs API finis,
sources/inputs/runtime inchangés et scopes propriétaires fermés. Un timeout,
OOM, stream partiel ou reçu absent conserve cette proposition sans image de
résultat. Une distance valide au-dessus du critère serait affichée honnêtement.

Le futur renderer et ses petites données incluraient les SHA de cette capsule,
des deux maillages et des reçus natifs. Il serait borné à 60 s, un thread et
zéro worker, avec sorties PNG/SVG/PDF reproductibles. Les fichiers d'origine
resteraient intacts. Aucune source de distance future n'est déclarée présente
ou substituée par 0 à ce stade.
