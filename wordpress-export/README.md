# Export Gutenberg du portfolio

Ce dossier contient un exporteur hors ligne. Il lit `index.html`, les trois fichiers JSON et les huit fichiers de `projects/`. Il ne lit aucun jeton, n’effectue aucune requête réseau, ne publie rien et ne modifie aucun fichier source.

## Génération locale

Depuis la racine `portfio`, dans PowerShell :

```powershell
python .\wordpress-export\export_portfolio.py
```

Les exports apparaissent dans `wordpress-export/generated/<horodatage>/` et une copie de chaque export est créée dans `wordpress-export/backups/<horodatage>/`. Chaque exécution crée un nouveau dossier et ne remplace pas les précédents.

Les URL distantes, textes alternatifs, pages sources, auteurs et licences sont centralisés dans `project-images.json`. Les fichiers images ne sont pas téléchargés dans le dépôt. Les huit visuels sont signalés comme illustrations génériques et ne doivent pas être décrits comme des captures des réalisations.

Fichiers générés :

- `accueil-gutenberg.html` : contenu de la page d’accueil, sections et cartes générées depuis les sources.
- `navigation-entete-gutenberg.html` : navigation explicite des huit ancres, sans bloc Page List.
- `modele-page-projet.html` : squelette visuel natif Gutenberg.
- `projects/<slug>.html` : contenu Gutenberg individuel pour les huit projets.
- `verification.json` : compte des ancres, titres, contenus et destinations.

Les blocs Gutenberg Image incluent l’URL HTTPS, un texte alternatif et une légende avec attribution/licence. Si une URL devient indisponible, le navigateur conserve une zone d’image à ratio fixe et son texte alternatif. Le SVG de secours interactif est uniquement activé par le JavaScript des pages HTML statiques ; WordPress.com peut filtrer ou ne pas exécuter ce JavaScript dans du contenu de blocs.

## Liens des pages projet

Les huit pages WordPress sont déjà publiées et leurs boutons actuels fonctionnent, mais leurs URL ne figurent pas dans les sources locales. L’exporteur ne les invente pas. Sans `project-links.json`, le nouvel accueil utilise des marqueurs `{{WORDPRESS_PROJECT_URL:<slug>}}` : ne remplace pas la section Projets publiée par cet export tant que ces marqueurs ne sont pas remplacés par les URL déjà en service.

Pour produire une version prête à importer, copie `project-links.example.json` sous `project-links.json`, puis renseigne les huit URL HTTPS actuelles relevées dans une sauvegarde locale de l’accueil. L’exporteur vérifie que les huit slugs sont présents et que chaque destination est HTTPS. Cela ne nécessite pas de recréer les liens dans l’éditeur.

## Import dans WordPress.com

- Le contenu de `accueil-gutenberg.html` et des fichiers de projet est du balisage de blocs : il peut être collé dans l’éditeur de code de la page correspondante.
- `navigation-entete-gutenberg.html` concerne l’en-tête global : il doit remplacer `<!-- wp:page-list /-->` dans le modèle En-tête via l’Éditeur de site. Un contenu collé dans la page d’accueil ne peut pas remplacer l’en-tête du thème.
- Les URL des médias ne sont pas fabriquées. Les marqueurs Photo et CV doivent être remplacés par les blocs Image/Fichier après sélection des médias de la médiathèque.
- Les illustrations des projets sont des images distantes sous les licences indiquées dans les légendes. Garde les attributions et la mention « illustration générique » lors de l’import.
- `finaliser_portfolio.py` et `creer_pages_wordpress.py` ne font pas partie de cette procédure : ils appellent l’API et/ou publient des pages. Ne les exécute pas pour cet export.

La génération ne modifie aucun contenu WordPress. L’import et la publication éventuelle sont des opérations distinctes qui doivent être validées avant exécution.