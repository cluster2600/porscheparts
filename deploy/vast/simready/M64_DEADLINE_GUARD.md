# Garde local de l'échéance M64

Ce programme ne loue rien et n'exécute aucune phase. Après un lancement réussi,
il surveille uniquement l'instance déjà indiquée dans le manifeste :

```sh
python3 deploy/vast/simready/m64-deadline-guard.py \
  --manifest /chemin/absolu/au/bundle/job-manifest.json \
  --state-dir /nouveau/dossier/prive/du-garde
```

Le seul outil de commande autorisé est le wrapper local **installé**
`/Users/maxime/.local/bin/openbao-vastai`, avec quatre commandes : `show`,
`m64-collect`, `destroy --confirm`, `instances`. Aucun SSH, appel API brut,
changement de clé, relancement ou autre mutation n'est exposé.

Le dossier d'état est créé en 0700, ses reçus en 0600. Le manifeste et le wrapper
sont épinglés par SHA256 à l'armement. Le délai du manifeste, au maximum deux
heures depuis sa création, n'est jamais renouvelé. Un second délai monotone
empêche un recul de l'horloge de prolonger la surveillance.

Toutes les 30 secondes, le garde vérifie l'identité exacte ID/label/image. À
l'échéance :

1. Revérification de l'identité et collecte dans `deadline-collection`, limitée
   à 300 secondes. Un échec de collecte reste signalé, sans empêcher l'arrêt.
2. Nouvelle vérification de l'identité, puis suppression de cet ID uniquement.
3. Vérification du reçu de suppression **et** d'un inventaire indépendant.

Les commandes de lecture sont bornées à 45 secondes, la suppression à 90
secondes : la récupération et les contrôles de fermeture peuvent dépasser
l'échéance de calcul. Ils ne constituent pas un budget illimité. `final.json`
indique séparément la collecte et l'absence vérifiées ; tout échec de fermeture
retourne un code non nul.

## Arrêt anticipé

Après avoir collecté avec le wrapper, puis supprimé et vérifié l'instance,
créer `stop.json` en 0600 dans le dossier d'état :

```json
{
  "job_id": "valeur exacte du manifeste",
  "instance_id": 123456,
  "label": "valeur exacte du manifeste",
  "image": "digest exact du manifeste",
  "manifest_sha256": "empreinte exacte enregistrée dans guard.json",
  "collection_receipt": "/chemin/absolu/collection-receipt.json"
}
```

Le garde vérifie l'identité du reçu de collecte et l'absence distante. Un fichier
vide, un reçu différent, ou un marqueur alors que l'instance existe encore ne
désarme pas la protection. Ne pas réinstaller le wrapper pendant la garde : un
changement de son empreinte provoque une alerte, jamais une exécution aveugle.

## Limite importante

C'est une protection **locale**, pas un coupe-circuit du fournisseur. Le Mac et
le processus doivent rester éveillés, supervisés et connectés. Une extinction,
une suspension ou une indisponibilité réseau peut empêcher la suppression
distante ; aucun reçu d'absence n'est alors revendiqué. Le garde ne constitue
ni une preuve de facturation globale, ni une validation de fabrication.
