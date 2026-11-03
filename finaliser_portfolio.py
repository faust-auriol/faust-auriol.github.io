import json
import re
import html
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError

TOKEN = (Path.home() / ".wp_token").read_text().strip()
API = "https://public-api.wordpress.com/wp/v2/sites/portfolioauriol.wordpress.com"
IDS = list(range(21, 29))

def api(url, data=None):
    body = None
    headers = {"Authorization": f"Bearer {TOKEN}"}
    if data is not None:
        body = json.dumps(data, ensure_ascii=False).encode()
        headers["Content-Type"] = "application/json"
    req = Request(url, data=body, headers=headers, method="POST" if data is not None else "GET")
    with urlopen(req, timeout=30) as r:
        return json.load(r)

def titre(page):
    return html.unescape(page["title"]["rendered"]).replace("\xa0", " ").strip()

try:
    # Récupérer l'accueil en mode édition
    accueil = api(API + "/pages/6?context=edit")
    contenu = accueil.get("content", {}).get("raw")
    if not contenu:
        raise RuntimeError("WordPress n'a pas fourni le contenu brut de l'accueil.")

    # Sauvegarde locale avant modification
    sauvegarde = Path("accueil_avant_liens.html")
    sauvegarde.write_text(contenu, encoding="utf-8")
    print(f"Sauvegarde créée : {sauvegarde.resolve()}")

    pages = []
    for identifiant in IDS:
        page = api(f"{API}/pages/{identifiant}?context=edit")
        pages.append(page)

    # Préparer les URL des projets
    liens = []
    for page in pages:
        url = page.get("link")
        if not url:
            url = f"https://portfolioauriol.wordpress.com/?page_id={page['id']}"
        liens.append((page["id"], titre(page), url))

    # Vérifier qu'il y a exactement 8 boutons non liés
    motif = '<a class="wp-block-button__link wp-element-button">Détails à venir</a>'
    nombre = contenu.count(motif)
    if nombre != 8:
        raise RuntimeError(
            f"{nombre} boutons exacts trouvés au lieu de 8. "
            "Aucune page n'a été publiée et l'accueil n'a pas été modifié."
        )

    # Publier les pages de projet
    for identifiant, nom, url in liens:
        page = api(f"{API}/pages/{identifiant}", {"status": "publish"})
        print(f"PUBLIÉE — {titre(page)} — {page.get('link', url)}")

    # Remplacer les boutons dans l'ordre des projets
    for identifiant, nom, url in liens:
        bouton = (
            '<a class="wp-block-button__link wp-element-button" '
            f'href="{html.escape(url, quote=True)}">Voir le projet</a>'
        )
        contenu = contenu.replace(motif, bouton, 1)

    # Mettre à jour l'accueil en conservant les autres blocs
    page_accueil = api(API + "/pages/6", {"content": contenu})
    print("\nACCUEIL MIS À JOUR :", page_accueil.get("link"))
    print("Les 8 boutons ont été reliés aux pages de projets.")

except HTTPError as e:
    print(f"\nERREUR HTTP {e.code}")
    print(e.read().decode("utf-8", errors="replace")[:1500])
    print("Vérifie les pages publiées avant de relancer le script.")
except Exception as e:
    print("\nARRÊT :", e)
    print("La sauvegarde locale de l'accueil, si créée, est conservée.")
