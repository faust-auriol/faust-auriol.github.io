# Modifications du modèle Assembler

Ces changements touchent le modèle global du thème, pas le contenu des pages. Ils ne sont pas appliqués par l’exporteur.

## En-tête et menu

Dans l’Éditeur de site, ouvrir la partie En-tête et remplacer le bloc Navigation dont le contenu est `<!-- wp:page-list /-->` par le bloc Navigation de `generated/<horodatage>/navigation-entete-gutenberg.html`. Cela conserve un seul menu et limite ses entrées aux huit ancres demandées. Vérifier le rendu desktop et mobile avant d’enregistrer le modèle.

Ne coller pas ce fragment dans le contenu de la page : il créerait un deuxième menu au lieu de remplacer celui du thème.

## « Lire la suite » vertical

Ce libellé n’est pas dans les fichiers HTML du portfolio. Il provient donc du modèle/bloc WordPress. Dans l’Éditeur de site, inspecter le modèle qui affiche le lien, sélectionner son parent et vérifier que le bloc est dans une colonne assez large et dans une disposition normale (pas une colonne étroite ou un groupe vertical). Pour les fiches projet individuelles, retirer le bloc « Lire la suite » s’il provient d’une boucle/extrait qui n’a pas lieu d’être sur ce modèle.

`assembler-read-more-fix.css` est un correctif CSS de repli, pas un bloc Gutenberg. Il n’est utile que si l’interface de l’offre active expose un champ CSS additionnel. Si ce champ n’est pas disponible, ne chercher pas à importer ce fichier dans le contenu : corriger la largeur et la disposition avec les réglages natifs du modèle.

## Limites de l’import

Les fichiers HTML exportés peuvent définir le contenu Gutenberg d’une page. Ils ne remplacent pas le modèle Assembler, ne fournissent pas de PHP et ne chargent pas `main.css` ou le JavaScript du site. La navigation d’en-tête et le bloc « Lire la suite » nécessitent donc un ajustement distinct dans l’Éditeur de site. Aucune API n’est appelée par les fichiers de ce dossier.

Les blocs Image générés embarquent les URL distantes et leurs attributs alt. Les styles responsives d’image essentiels (largeur maximale, ratio 16:9 et object-fit) sont intégrés dans le bloc. Le fichier `css/responsive-overrides.css` améliore les pages HTML statiques et n’est pas chargé automatiquement par WordPress.com. Le repli SVG par JavaScript des pages statiques ne s’applique pas nécessairement aux blocs hébergés ; en cas d’indisponibilité, le fond bleu nuit, la dimension réservée et le texte alternatif gardent une présentation lisible.