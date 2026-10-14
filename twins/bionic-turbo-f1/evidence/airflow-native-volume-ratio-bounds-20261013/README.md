# Rapports de volumes : application aux bornes héritées

Les **13696 rapports de volumes internes** passent le seuil source 0.01 sur
l'enveloppe fermée des 153 boîtes conservées. La borne minimale est environ
**0.30145582744096006**. Les 4864 murs non couplés suivent l'initialisation
native à 1; les 384 faces MRF sont internes. Aucun ancien volume n'est
recalculé, aucun ratio géométrique ponctuel choisi, aucune admission native.

## Domaine et formule

Le domaine reste u=q_m source et v dans
`[18685771944522017155/18446744073709551616,
9345323731508729405/9223372036854775808]`.
Les 153 boîtes, leurs extrémités et les deux indécisions de déterminants sont
conservées. Quatorze manifestes, 332 entrées, sont ancrés au commit PR245
`7a1282bdbe43411ade9c0e79e831cc5c9973bb6d`.

La source officielle v2406 calcule
`min(Vown,Vnei)/(max(Vown,Vnei)+VSMALL)` dans polyMeshTools::volRatio.
checkVolRatio refuse strictement sous minRatio; l'appel applicatif fixe 0.01.
**VSMALL**, et non ROOTVSMALL, est conservé dans le dénominateur. La constante
et le seuil sont les rationnels des littéraux binary64, sous hypothèse WM_DP.
Cette hypothèse de source ne vaut pas inspection du futur binaire.

Les volumes sont les bornes exactes PR241, déjà relues indépendamment et
mathématiquement reliées au volume natif pour cette représentation. Les deux
reçus et le SHA du modèle sont vérifiés sur le même domaine. Les centres
natifs ne sont ni remplacés ni réévalués pour ce critère sans centre.

Pour des volumes dans [a,b] et [c,d], tous strictement positifs, on utilise
`[min(a,c)/(max(b,d)+s), min(b,d)/(max(a,c)+s)]`, s=VSMALL>0.
La minoration/majoration séparée du numérateur et du dénominateur démontre
l'inclusion, même si les volumes sont corrélés par v. L'encadrement peut être
conservateur; il ne suppose pas que ses extrêmes sont atteints ensemble.
Fraction conserve exactement l'additif et les quotients rationnels.

## Incidences et branches

Les faces sont ordonnées par labels triés. Le premier programme reconstruit
les familles prismes/hex; le lecteur utilise les six gabarits hex réduits et
vérifie les cycles opposés. Les 18560 faces et leurs cellules sont relues.
Les murs correspondent exactement aux faces réduites du contrat PR229.
Le dictionnaire archivé a été **lu seulement**, jamais exécuté, modifié ou
repréparé : une unique déclaration walls de type wall et ses faces sont vérifiées.

La source initialise les ratios à 1 avant les branches internes/couplées.
check_boundary_type.py relit deux en-têtes du même tar officiel :
wallPolyPatch dérive directement de polyPatch et ne surcharge pas coupled();
la méthode de base retourne false. Ce contrôle complémentaire de source lie
la déclaration wall à la branche non couplée; il n'inspecte pas un exécutable.
Les 384 faces MRF restent à incidence deux, sans invention de patch couplé.

## Lecture indépendante

verify_ratios.py n'importe pas check_ratios.py. Il reconstruit les incidences,
relit les volumes certifiés et calcule min/max par somme/différence absolue,
puis vérifie chaque quotient par produits croisés entiers. Les 13696
encadrements et 4864 initialisations concordent exactement. Il s'agit d'une
vérification indépendante de cette **nouvelle application arithmétique et des
incidences**, pas d'une nouvelle reconstruction géométrique des volumes PR241.

Six références analytiques par lecteur précèdent l'application, notamment des
volumes à l'échelle VSMALL : l'additif y change le résultat, ce qui contrôle
qu'il n'est pas omis. Ces références ne sélectionnent pas le paramètre v.
Tous les encadrements individuels sont conservés dans ratio-bounds.jsonl.gz.
Aucune indécision ni exclusion nouvelle pour ce critère sur l'enveloppe.

## Portée

Ce résultat ne modélise pas les arrondis OpenFOAM, la conversion writePrecision
16 ou les autres critères. Poids de faces et skewness exigent leurs propres
centres natifs, termes additifs, normalisations et branches. L'orthogonalité
avec son additif, la décomposition native checkFaceTets, les contacts internes
de dimension inférieure et le bilan flottant restent ouverts.

Les 113 boîtes aux prédicats nécessaires passants ne sont toujours pas admises.
Trois intervalles synthétiques et u=q_m ne qualifient pas le système entier,
les surfaces physiques 086/091, les couches ou le repos. 084 reste incomplet
et ne sera pas relancé. Aucun débit, puissance ou calibration validé.
