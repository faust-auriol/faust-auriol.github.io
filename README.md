# Portfolio — Faust Auriol Mbingou

Structure initiale du portfolio statique compatible avec GitHub Pages.

## Visualiser le site en local

N’ouvrez pas `index.html` directement avec une adresse `file://` : les navigateurs bloquent alors le chargement des fichiers JSON utilisés par les compétences et les projets.

Depuis PowerShell, dans le dossier du portfolio, lancez :

```powershell
powershell -ExecutionPolicy Bypass -File .\start-local-server.ps1
```

Ouvrez ensuite `http://127.0.0.1:8080` dans votre navigateur. Utilisez `Ctrl+C` dans le terminal pour arrêter le serveur.

- `index.html` : structure et navigation du site.
- `css/main.css` : styles responsives.
- `js/main.js` : interactions de navigation et futurs rendus dynamiques.
- `data/` : données des compétences et projets à compléter.
- `assets/images/` : futurs médias.
- `projects/` : futures fiches de projets.
- `documents/` : futur CV PDF.
