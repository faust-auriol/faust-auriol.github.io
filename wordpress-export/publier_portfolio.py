import argparse
import html
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import unquote, urlparse
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
EXPORT = Path(__file__).resolve().parent
GENERATED = EXPORT / "generated" / "20261029-231056"
BACKUPS = EXPORT / "backups" / "remote-publication"
TOKEN_FILE = Path.home() / ".wp_token"
API_ROOT = "https://public-api.wordpress.com/wp/v2/sites/portfolioauriol.wordpress.com"
HOME_ID = 6
HOME_SLUG = "accueil"

# These IDs are the existing page IDs used by the prior project-link workflow.
PROJECT_PAGE_IDS = {
    "sae-2-03": 21,
    "sae-2-04": 22,
    "sae-2-02": 23,
    "sae-2-05": 24,
    "sae-2-06": 25,
    "gestion-inscriptions": 26,
    "reseau-wds-pxe": 27,
    "securite-wifi-kali": 28,
}


class PublishError(RuntimeError):
    pass


def load_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise PublishError(f"Fichier introuvable : {path}") from error
    except json.JSONDecodeError as error:
        raise PublishError(f"JSON invalide dans {path} : {error}") from error


def normalize_text(value):
    value = html.unescape(re.sub(r"<[^>]+>", " ", value or ""))
    return " ".join(value.replace("\xa0", " ").split()).casefold()


def read_content_file(path, expected_title=None):
    if not path.is_file():
        raise PublishError(f"Contenu Gutenberg absent : {path}")
    content = path.read_text(encoding="utf-8")
    if "<!-- wp:" not in content:
        raise PublishError(f"Aucun commentaire de bloc Gutenberg trouvé dans {path.name}.")
    if expected_title and normalize_text(expected_title) not in normalize_text(content):
        raise PublishError(f"Le titre attendu n’apparaît pas dans {path.name} : {expected_title}")
    if path.parent.name == "projects":
        if "<!-- wp:image " not in content:
            raise PublishError(f"Bloc Image manquant dans {path.name}.")
        if not re.search(r'<img\s+[^>]*src="https://[^\"]+"[^>]*alt="[^\"]+"', content):
            raise PublishError(f"Image HTTPS avec texte alternatif manquante dans {path.name}.")
    return content


def validate_home(content):
    verification = load_json(GENERATED / "verification.json")
    if verification.get("project_count") != 8 or verification.get("destination_count") != 8:
        raise PublishError("Le manifeste ne confirme pas huit projets et huit destinations.")
    if verification.get("project_links_verified") is not True:
        raise PublishError("Le manifeste n’a pas validé les huit destinations des projets.")
    placeholders = ("[PHOTO DE PROFIL", "[CV PROVISOIRE", "{{WORDPRESS_PROJECT_URL:")
    found = [marker for marker in placeholders if marker in content]
    if found:
        raise PublishError(
            "Accueil non publiable : repères provisoires détectés ("
            + ", ".join(found)
            + "). Complète et vérifie photo, CV et liens avant --accueil."
        )


def api_request(url, token, payload=None):
    body = None
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "User-Agent": "PortfolioPagePublisher/1.0",
    }
    method = "GET"
    if payload is not None:
        method = "POST"
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json; charset=utf-8"
    request = Request(url, data=body, headers=headers, method=method)
    try:
        with urlopen(request, timeout=30) as response:
            if not 200 <= response.status < 300:
                raise PublishError(f"Réponse API inattendue : HTTP {response.status} ({url})")
            result = json.loads(response.read().decode("utf-8"))
            if not isinstance(result, dict):
                raise PublishError(f"Réponse JSON API inattendue ({url}).")
            return result
    except HTTPError as error:
        raise PublishError(f"Erreur HTTP {error.code} pour {url}.") from error
    except URLError as error:
        raise PublishError(f"Erreur réseau pour {url}: {error.reason}") from error
    except TimeoutError as error:
        raise PublishError(f"Délai dépassé pour {url}.") from error


def page_title(page):
    title = page.get("title", {})
    if isinstance(title, dict):
        return title.get("raw") or title.get("rendered") or ""
    return str(title)


def page_content_raw(page):
    content = page.get("content", {})
    return content.get("raw") if isinstance(content, dict) else None


def public_slug_from_url(url):
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.netloc != "portfolioauriol.wordpress.com":
        raise PublishError(f"URL WordPress invalide dans project-links.json : {url}")
    if parsed.query or parsed.fragment:
        raise PublishError(f"L’URL de projet doit être une URL canonique sans query/fragment : {url}")
    slug = unquote(parsed.path.rstrip("/").split("/")[-1])
    if not slug:
        raise PublishError(f"Slug public manquant dans project-links.json : {url}")
    return slug


def verify_remote_page(page, page_id, expected_title, expected_slug=None, expected_link=None):
    if page.get("id") != page_id:
        raise PublishError(f"L’API a retourné l’ID {page.get('id')} au lieu de {page_id}.")
    actual_title = page_title(page)
    if normalize_text(actual_title) != normalize_text(expected_title):
        raise PublishError(
            f"Titre inattendu pour la page {page_id}: {actual_title!r}; attendu {expected_title!r}."
        )
    if expected_slug and page.get("slug") != expected_slug:
        raise PublishError(
            f"Slug inattendu pour la page {page_id}: {page.get('slug')!r}; attendu {expected_slug!r}."
        )
    if expected_link and page.get("link") != expected_link:
        raise PublishError(
            f"URL inattendue pour la page {page_id}: {page.get('link')!r}; attendue {expected_link!r}."
        )
    if page_content_raw(page) is None:
        raise PublishError(f"Le contenu brut éditable de la page {page_id} n’a pas été retourné.")


def create_remote_backup(pages):
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_dir = BACKUPS / timestamp
    backup_dir.mkdir(parents=True, exist_ok=False)
    for page_id, slug, page in pages:
        path = backup_dir / f"page-{page_id}-{slug}.json"
        temporary = path.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(page, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        temporary.replace(path)
    return backup_dir


def prepare_targets(args, projects, links):
    if set(PROJECT_PAGE_IDS) != {Path(project["url"]).stem for project in projects}:
        raise PublishError("Le mappage explicite des IDs ne correspond pas aux huit projets JSON.")
    if set(links) != set(PROJECT_PAGE_IDS):
        raise PublishError("project-links.json ne correspond pas exactement aux huit projets.")
    if len(set(PROJECT_PAGE_IDS.values())) != 8:
        raise PublishError("Les IDs WordPress des projets doivent être distincts.")

    targets = []
    for project in projects:
        slug = Path(project["url"]).stem
        public_slug = public_slug_from_url(links[slug])
        content_path = GENERATED / "projects" / f"{slug}.html"
        content = read_content_file(content_path, project["title"])
        targets.append({
            "id": PROJECT_PAGE_IDS[slug],
            "export_slug": slug,
            "wordpress_slug": public_slug,
            "title": project["title"],
            "url": links[slug],
            "path": content_path,
            "content": content,
        })

    if args.accueil:
        home_path = GENERATED / "accueil-gutenberg.html"
        home_content = read_content_file(home_path, "FAUST")
        validate_home(home_content)
        targets.append({
            "id": HOME_ID,
            "export_slug": HOME_SLUG,
            "wordpress_slug": HOME_SLUG,
            "title": None,
            "url": "https://portfolioauriol.wordpress.com/accueil/",
            "path": home_path,
            "content": home_content,
        })
    return targets


def dry_run(targets):
    print("SIMULATION LOCALE — aucune API appelée, aucun fichier distant modifié.\n")
    for target in targets:
        action = "Accueil (option --accueil)" if target["id"] == HOME_ID else target["title"]
        image_count = len(re.findall(r"<!-- wp:image ", target["content"]))
        print(f"Page existante ID {target['id']} | {action}")
        if target["id"] != HOME_ID:
            wordpress_slug = public_slug_from_url(target["url"])
            if wordpress_slug != target["wordpress_slug"]:
                raise PublishError(f"Slug public incohérent pour l’ID {target['id']}.")
            print(f"  Slug export/public : {target['export_slug']} -> {wordpress_slug}")
        print(f"  Fichier : {target['path'].relative_to(ROOT)}")
        print(f"  URL conservée : {target['url']}")
        print(f"  Blocs Image : {image_count}")
    print(f"\nTotal prévu : {len(targets)} page(s).")
    print("Pour écrire les fiches existantes après vérification : ajouter --publish.")


def publish(targets, links):
    if not TOKEN_FILE.is_file():
        raise PublishError(f"Jeton OAuth absent du fichier local attendu : {TOKEN_FILE}")
    token = TOKEN_FILE.read_text(encoding="utf-8").strip()
    if not token:
        raise PublishError("Le fichier local de jeton OAuth est vide.")

    remote_pages = []
    for target in targets:
        page_id = target["id"]
        page = api_request(f"{API_ROOT}/pages/{page_id}?context=edit", token)
        if target["id"] == HOME_ID:
            verify_remote_page(page, page_id, page_title(page), HOME_SLUG, target["url"])
        else:
            wordpress_slug = public_slug_from_url(target["url"])
            if wordpress_slug != target["wordpress_slug"]:
                raise PublishError(f"Slug public incohérent pour l’ID {page_id}.")
            verify_remote_page(page, page_id, target["title"], wordpress_slug, target["url"])
        remote_pages.append((page_id, target["export_slug"], page))

    # All remote contents and their identity metadata are backed up before the first update.
    backup_dir = create_remote_backup(remote_pages)
    print(f"Sauvegarde distante locale créée avant écriture : {backup_dir.relative_to(ROOT)}")

    for target, (page_id, slug, previous_page) in zip(targets, remote_pages):
        result = api_request(
            f"{API_ROOT}/pages/{page_id}",
            token,
            {"content": target["content"]},
        )
        if result.get("id") != page_id:
            raise PublishError(f"Réponse de mise à jour incohérente pour la page {page_id}.")
        if result.get("slug") and result["slug"] != previous_page.get("slug"):
            raise PublishError(f"Le slug de la page {page_id} semble avoir changé; arrêt immédiat.")
        if result.get("link") and result["link"] != previous_page.get("link"):
            raise PublishError(f"L’URL de la page {page_id} semble avoir changé; arrêt immédiat.")
        print(f"MISE À JOUR — ID {page_id} — {target['url']}")


def main():
    parser = argparse.ArgumentParser(
        description="Met à jour les contenus Gutenberg de pages WordPress existantes; aucune page n’est créée."
    )
    operation = parser.add_mutually_exclusive_group()
    operation.add_argument("--dry-run", action="store_true", help="simule localement; option sûre et sans requête API")
    operation.add_argument("--publish", action="store_true", help="autorise explicitement l’écriture des contenus après sauvegarde")
    parser.add_argument("--accueil", action="store_true", help="inclut la page d’accueil ID 6 après validation des repères")
    args = parser.parse_args()

    projects = load_json(ROOT / "data" / "projects.json")
    links = load_json(EXPORT / "project-links.json")
    targets = prepare_targets(args, projects, links)

    if not args.publish:
        dry_run(targets)
        return 0

    publish(targets, links)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except PublishError as error:
        print(f"ERREUR — {error}", file=sys.stderr)
        raise SystemExit(1)