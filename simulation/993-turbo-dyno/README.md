# Références de banc et modèle 0D

[`dyno-reference.json`](dyno-reference.json) rassemble des points publiés dans
des pages de préparateurs, des articles et des comptes rendus de forums. Les
feuilles de banc et les images originales ne sont pas copiées dans le dépôt ;
les valeurs restent attachées à leur source et à leur niveau de preuve.

Les données utiles comprennent notamment :

- les points de couple du RUF Turbo R rapportés sur banc moteur ;
- la comparaison annoncée sur le même moteur entre K16 Stage 3 et K24RS ;
- le point Powerhaus K24 à `5000 tr/min`, `500 whp` et `525 lb-ft`, avec environ
  `1 bar` de boost rapporté ;
- un essai châssis d'une 993 à K16 reconstruits, avec `324 whp` à `6000 tr/min`
  et `329 lb-ft` à `4600 tr/min` ;
- les cibles Cargraphic K16/24 et la borne K26 d'un projet AP Car Design, qui
  restent des références déclarées ou contextuelles.

Le script [`model_turbo_dyno_0d.py`](../../scripts/model_turbo_dyno_0d.py) :

1. conserve les unités de publication et les convertit en Nm/kW ;
2. calcule la puissance issue du couple et le BMEP du moteur 3,6 l ;
3. compare les lignes puissance/couple lorsqu'elles partagent un régime ;
4. ajoute une enveloppe de débit par turbo issue des hypothèses de pression,
   température, VE et partage des bancs ;
5. signale les incohérences sans corriger silencieusement la source.

Cette sortie est un normalisateur 0D et un jeu d'ancres de comparaison. Elle ne
constitue pas une carte compresseur/turbine, n'identifie pas la vitesse d'arbre
et ne calibre pas encore le CFD. Les conditions de banc manquantes doivent être
obtenues avant toute régression physique.

## Utilisation

```bash
make turbo-dyno
make turbo-dyno-check
```

Le résultat généré est
[`derived-dyno-curves.json`](derived-dyno-curves.json). Un point interpolé ne
doit pas être extrapolé hors de la plage publiée et aucune cible de puissance ne
doit être utilisée pour libérer une pièce moteur.
