# Inventaire des composants physiques du jumeau

## Règle d'admission

Un composant entre dans `catalog/components/` seulement si les quatre éléments
suivants sont sourcés : taille, masse, matière et application au 993. Une source
doit aussi identifier la pièce sans ambiguïté.

La géométrie est classée séparément :

- `interface_proxy` : seuls les paramètres nominaux connus sont représentés ;
- `envelope` : l'encombrement extérieur est documenté ;
- `detailed_solid` : la forme est assez complète pour des contrôles locaux ;
- `scan` : géométrie acquise, avec échelle et précision déclarées.

Un composant complet peut rejoindre un assemblage `logical` même si ses
transformations 3D sont inconnues. Il ne peut participer à un contrôle spatial
que si ses interfaces et leur précision sont connues.

## Premier lot admis

| Composant | Taille | Masse | Matière | Géométrie | Assemblage |
|---|---|---:|---|---|---|
| `COMP-FUCHS-37024.013` | 7J x 17 ET55 | 7,50 kg | aluminium forgé | proxy d'interface | essieu avant, quantité 2 |
| `COMP-FUCHS-37026.013` | 9J x 17 ET55 | 7,95 kg | aluminium forgé | proxy d'interface | essieu arrière, quantité 2 |

Source primaire : documentation publique du fabricant Otto Fuchs. Il s'agit de
roues compatibles, pas de fichiers CAO Porsche ni d'une affirmation qu'elles
étaient montées d'origine sur toutes les variantes.

## File d'acquisition

Les prochains lots sont recherchés par sous-ensemble : roues et pneumatiques,
freinage, roulements et joints standardisés, transmission, moteur, carrosserie,
habitacle. Une fiche incomplète reste dans le registre de sources ou dans une
issue de recherche ; elle ne reçoit pas de faux poids ou matériau par défaut.

