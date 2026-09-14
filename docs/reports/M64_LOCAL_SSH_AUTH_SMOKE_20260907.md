# Authentification SSH locale réelle — 7 septembre 2026

**Résultat : réussi**, sur Kali x86 dans l'image parent exacte déjà présente :
`ghcr.io/cluster2600/3dprinting993-simready-workflow@sha256:79e76882a8f493012eb4cc9ab061bce0ca2d075cd505d6e33a5200e7e1e9b126`.
Le wrapper sshd embarqué a le même SHA256 que le script du dépôt.

Contrairement au précédent test `sshd -T`, celui-ci lance réellement sshd et
effectue des connexions SSH en BatchMode avec vérification stricte de clé
d'hôte. Deux paires de clés **synthétiques et éphémères** sont générées dans
le conteneur ; aucune clé utilisateur, aucun secret OpenBao ou Keychain n'y
est utilisé. Le transport SSH habituel vers Kali reste extérieur au test.

## Vérifications obtenues

- Sans `authorized_keys`, la clé est refusée.
- Après injection du fichier en root:root/0600 et du répertoire en 0700,
  **la même clé réussit, sans redémarrage de sshd**.
- Une autre identité est refusée.
- Le passage de `authorized_keys` à 0666 entraîne un refus, avec diagnostic
  serveur de permissions incorrectes.
- Les opérations chown/chmod équivalentes au bloc SSH du onstart rétablissent
  l'authentification ; le onstart complet et ses services GPU ne sont pas lancés.
- Une mauvaise clé d'hôte dans le fichier connu est refusée.

Le mécanisme d'un refus transitoire avant injection/correction des permissions
est donc **reproduit localement**. Cela ne prouve pas que ce mécanisme s'est
produit sur Vast, ni l'ordre réel de son lanceur, ni le comportement de son
proxy. L'image complète local-ai n'est pas exécutée ici : son parent SSH est
testé. Aucun script de production n'a été modifié.

## Corrections à étudier, non appliquées

1. Préparer les permissions de `.ssh` et de la clé injectée avant l'ouverture
   du listener, lorsque l'ordre du lanceur le permet.
2. Traiter explicitement les modes `sshd -T` / `-t` : le onstart invoque déjà
   `sshd -T` avant son bloc de permissions. Ajouter naïvement une attente de
   clé à toute invocation du wrapper pourrait introduire un blocage circulaire.
3. Prévoir une courte attente bornée du fichier injecté dans le onstart,
   sans fabriquer de clé ni remplacer l'identité attendue.
4. Examiner une grâce d'authentification initiale strictement bornée, en
   conservant l'identité, les contrôles de clé d'hôte et le délai total.

Ces pistes doivent être testées isolément et reliées à des observations de
l'ordre réel de Vast avant de conclure à la cause ou de modifier la production.

## Reproduction, uniquement dans un conteneur jetable

Ne jamais exécuter le script directement sur une station. Il crée un fichier
`/root/.ssh/authorized_keys` synthétique dans le conteneur jetable.

Depuis une copie du dépôt sur un hôte Docker x86 :

```sh
timeout 90 docker run --rm -i --network none --cpus 1 --memory 1g \
  --pids-limit 64 --tmpfs /tmp:rw,noexec,nosuid,nodev,size=32m \
  --entrypoint /usr/bin/python3 \
  ghcr.io/cluster2600/3dprinting993-simready-workflow@sha256:79e76882a8f493012eb4cc9ab061bce0ca2d075cd505d6e33a5200e7e1e9b126 \
  - < tests/manual/simready_ssh_auth_smoke.py
```

Le listener est exclusivement `127.0.0.1:22222` dans le conteneur sans réseau ;
aucun port LAN/public n'est publié. Le processus et les clés temporaires ont
été supprimés ; l'inventaire Docker filtré sur l'image est vide après le test.
Le reçu se trouve dans
`twins/m64-cylinder-head/evidence/ssh-auth-smoke-20260907.json`.
