# M64 — prévol du chargement Vast, 7 septembre 2026

## Ce que les données permettent de savoir

La commande approuvée `heavy-offers`, interrogée en lecture seule, expose déjà
le débit entrant `inet_down_mbps`, l'espace annoncé `disk_space_gb`, les coûts
de transfert et le tarif incluant le stockage demandé. Le schéma officiel
contient aussi `disk_bw` et `disk_name`, masqués jusque-là par `safe_offer` :
le patch proposé expose `disk_read_bw_mb_s` et `disk_model`. Il ne change ni
les requêtes, ni les critères d'éligibilité, ni le classement des offres.
`disk_bw` est un débit de **lecture** disque, pas une mesure de décompression
ou d'écriture concurrente. [Schéma des offres Vast](https://docs.vast.ai/api-reference/search/search-offers).

Le schéma consulté ne fournit pas la preuve que le digest GHCR exact est
présent dans le cache de l'hôte. La requête actuelle ne comporte d'ailleurs
aucun digest d'image. L'espace de l'offre ne prouve ni le quota effectif de
notre futur conteneur ni l'espace de travail disponible au démon Docker.
Cache, débit réel depuis GHCR, taille décompressée et durée de démarrage
restent inconnus avant location.

## Image réellement relue

Le manifeste GHCR du digest `5a69a6805a275ef708e264600cb933663159a2846b069eafe0459c28e5f69699`
a été relu avec `docker buildx imagetools inspect --raw` :

- 54 couches compressées, **34 624 357 174 octets** au total ;
- plus grosse couche : **4 706 752 993 octets** ;
- le Dockerfile embarque le VLM Qwen en cinq shards et deux environnements
  PyTorch/CUDA isolés (PhysicsNeMo et vLLM).

Le découpage en couches existe déjà ; l'image n'est pas un simple runtime
SSH. Les tests CPU et la vérification du digest n'ont pas mesuré un démarrage
à froid de cette image sur l'hôte Vast concerné.

À débit constant égal à l'annonce, le seul transfert théorique dure
`8 × octets / (Mbps × 10^6)` secondes. Exemples observés lors de cette lecture :

| Offre | Débit annoncé | Transfert théorique seul | Coût d'un transfert unique, Go décimaux |
| --- | ---: | ---: | ---: |
| 47185008 | 642,5 Mbps | 7,19 min | 0,090 USD |
| 49094462 | 4 489,4 Mbps | 1,03 min | 0,361 USD |
| 37117681 | 723,2 Mbps | 6,38 min | 0,676 USD |

Ces calculs sont des scénarios, pas des ETA ni des factures : ils excluent
partage réseau, limitation GHCR, reprises, vérifications, décompression et
démarrage des services. Aucune offre n'a été louée pour cet audit.

## Correction des horloges, sans budget illimité

Vast indique qu'un chargement peut durer plusieurs heures avec une grosse
image et que l'état `Loading` n'est pas facturé comme calcul. L'arrêt de
50128235 à 30 minutes, encore en chargement, n'est donc pas une nouvelle
erreur d'authentification. Le détail des frais reste à vérifier sur la facture.
[Gestion des instances Vast](https://docs.vast.ai/guides/instances/manage-instances).

Le prévol a désormais deux limites non renouvelables :

1. **2 heures au total**, dès l'entrée dans le prévol SSH/READY ;
2. **30 minutes après la première observation `running`**, même si l'instance
   repasse ensuite en `loading`.

La première limite atteinte s'applique. Aucun READY reçu après la limite
n'est accepté. Les erreurs terminales d'authentification, de clé d'hôte et de
services, ainsi que la suppression sur échec, restent inchangées. Les reprises
GET 429 restent bornées à trois délais 20/40/60 secondes ; les deadlines sont
revérifiées après l'appel. Un appel déjà engagé peut dépasser l'instant limite
de son délai réseau : ce contrôleur n'est pas à lui seul une horloge de
destruction stricte.

Avant location, **un garde externe à 2 heures depuis la création** doit donc
borner la durée réelle puis vérifier la suppression. À 2,50 USD/h maximum,
cela représente au plus 5 USD de tarif horaire conservateur avant transferts
et marge de suppression. Une enveloppe cible inférieure à 6 USD exige de
réserver moins de 1 USD pour ces frais ; ce n'est pas une garantie si des
transferts sont répétés sans mesure. Le plafond autorisé reste **20 USD**,
sans recharge ni nouvelle location automatique sur échec.

Les tests à horloge simulée couvrent un chargement de 35 minutes autorisé,
les deux expirations, un retour en chargement sans réinitialisation, un READY
tardif et les 429 bornés. Ils ne prouvent pas un calcul GPU ou une culasse.
