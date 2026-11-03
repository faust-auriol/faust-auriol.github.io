import json
import re
import html
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

BASE = Path.cwd()
TOKEN_FILE = Path.home() / ".wp_token"
API = "https://public-api.wordpress.com/wp/v2/sites/portfolioauriol.wordpress.com"

if not TOKEN_FILE.exists():
    raise SystemExit("Jeton introuvable : ~/.wp_token")

token = TOKEN_FILE.read_text().strip()
projets = json.loads((BASE / "data/projects.json").read_text(encoding="utf-8"))
details = json.loads((BASE / "data/project-details.json").read_text(encoding="utf-8"))

def requete(url, data=None):
    headers = {"Authorization": f"Bearer {token}"}
    if data is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(data, ensure_ascii=False).encode("utf-8")
    req = Request(url, data=data, headers=headers)
    with urlopen(req, timeout=30) as r:
        return json.load(r)

def nettoyer_texte(texte):
    texte = re.sub(r"<[^>]+>", " ", texte)
    return html.unescape(re.sub(r"\s+", " ", texte)).strip()

def contenu_html(projet):
    titre = projet["title"]
    reference = projet.get("reference") or projet.get("category", "")
    fichier = projet.get("url", "")
    identifiant = Path(fichier).stem
    info = details.get(identifiant, {})

    parties = [f"<p><strong>{html.escape(reference)}</strong></p>"]

    presentations = info.get("presentation", [])
    if presentations:
        parties.append("<h2>Présentation du projet</h2>")
        parties.extend(f"<p>{html.escape(p)}</p>" for p in presentations)
    elif identifiant == "sae-2-03":
        # Récupère le contenu principal du fichier HTML d'origine.
        chemin = BASE / fichier
        source = chemin.read_text(encoding="utf-8", errors="replace")
        match = re.search(r"<main\b[^>]*>(.*?)</main>", source, re.I | re.S)
        if match:
            extrait = match.group(1)
            extrait = re.sub(
                r"<(script|style|nav|header|footer)\b[^>]*>.*?</\1>",
                "", extrait, flags=re.I | re.S
            )
            parties.append(extrait)
        else:
            texte = nettoyer_texte(source)
            parties.append(
                "<p>Le contenu détaillé est disponible dans le projet "
                "HTML d'origine. Cette page pourra être complétée après vérification.</p>"
            )
    else:
        parties.append(
            "<p>Cette page présente le projet réalisé dans le cadre de ma formation.</p>"
        )

    travaux = info.get("work", [])
    if travaux:
        parties.append("<h2>Travaux réalisés</h2><ul>")
        parties.extend(f"<li>{html.escape(t)}</li>" for t in travaux)
        parties.append("</ul>")

    competences = info.get("skills", projet.get("technologies", []))
    if competences:
        parties.append("<h2>Compétences et technologies</h2><ul>")
        parties.extend(f"<li>{html.escape(c)}</li>" for c in competences)
        parties.append("</ul>")

    qualites = info.get("soft", [])
    if qualites:
        parties.append("<h2>Qualités mobilisées</h2><ul>")
        parties.extend(f"<li>{html.escape(q)}</li>" for q in qualites)
        parties.append("</ul>")

    autres = info.get("other", [])
    if autres:
        parties.append("<h2>Autres compétences développées</h2><ul>")
        parties.extend(f"<li>{html.escape(q)}</li>" for q in autres)
        parties.append("</ul>")

    return "\n".join(parties)

# Récupère les pages existantes pour éviter les doublons.
existantes = requete(API + "/pages?per_page=100&status=publish,draft,private")
titres_existants = {
    html.unescape(p.get("title", {}).get("rendered", "")).strip().casefold()
    for p in existantes
}

crees = 0
ignorees = 0

for projet in projets:
    titre = projet["title"].strip()

    if titre.casefold() in titres_existants:
        print(f"IGNORÉE (déjà présente) : {titre}")
        ignorees += 1
        continue

    donnees = {
        "title": titre,
        "content": contenu_html(projet),
        "status": "draft"
    }

    try:
        page = requete(API + "/pages", donnees)
        print(f"CRÉÉE — ID {page['id']} : {titre}")
        crees += 1
        titres_existants.add(titre.casefold())
    except HTTPError as e:
        print(f"ERREUR HTTP {e.code} pour {titre}")
        print(e.read().decode("utf-8", errors="replace")[:500])
        print("Arrêt du script pour éviter d'autres créations incertaines.")
        break
    except (URLError, TimeoutError) as e:
        print(f"Erreur réseau pour {titre} : {e}")
        break

print(f"\nTerminé : {crees} page(s) créée(s), {ignorees} déjà présente(s).")
print("Toutes les pages créées sont en brouillon, pas publiées.")
print("Le brouillon de test ID 20 n'a pas été supprimé.")
