# F40 Vast — publication OCI verifiee

Cette preuve ferme uniquement les gates de publication de l'image de transport
F40. Le workflow GitHub a construit un index OCI `linux/amd64`, publie un SBOM
et une provenance, execute les smokes hors ligne, puis reussi un pull anonyme du
digest exact. Un second pull anonyme et le smoke de separation de privileges ont
ete reproduits localement le 2 septembre 2026.

La preuve canonique est `publication.json`. Le `lock.json` inclus dans l'image
reste volontairement un verrou de recette prepublication : y inscrire le digest
de l'image modifierait l'image elle-meme et rendrait ce digest autoreferentiel.
Les faits post-publication sont donc portes par ce dossier d'evidence externe au
contexte OCI.

Cette etape ne prouve pas l'injection de la cle SSH par Vast, une execution F40
sur Vast, la correlation physique, la puissance de 1 600 ch, le demarrage ou la
fabricabilite du moteur. Ces gates restent fermees.

