import html
import json
import re
import shutil
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
EXPORT = Path(__file__).resolve().parent
GENERATED = EXPORT / "generated"
BACKUPS = EXPORT / "backups"
HOME_URL = "https://portfolioauriol.wordpress.com/accueil/"
ANCHORS = [
    "accueil",
    "a-propos",
    "parcours",
    "competences",
    "projets",
    "interets",
    "cv",
    "contact",
]
SECTION_COLORS = {
    "accueil": ("#f7f9fc", "#071727"),
    "a-propos": ("#ffffff", "#071727"),
    "parcours": ("#f7f9fc", "#071727"),
    "competences": ("#071727", "#ffffff"),
    "projets": ("#ffffff", "#071727"),
    "interets": ("#f7f9fc", "#071727"),
    "cv": ("#39d6cf", "#071727"),
    "contact": ("#ffffff", "#071727"),
}


class Node:
    def __init__(self, tag, attrs=None):
        self.tag = tag
        self.attrs = dict(attrs or [])
        self.children = []


class DocumentParser(HTMLParser):
    VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("document")
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        node = Node(tag, attrs)
        self.stack[-1].children.append(node)
        if tag not in self.VOID_TAGS:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.stack[-1].children.append(Node(tag, attrs))

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                break

    def handle_data(self, data):
        if data:
            self.stack[-1].children.append(data)


def parse_html(text):
    parser = DocumentParser()
    parser.feed(text)
    parser.close()
    return parser.root


def attr(node, name, default=""):
    return node.attrs.get(name, default)


def classes(node):
    return set(attr(node, "class").split())


def walk(node):
    for child in getattr(node, "children", []):
        if isinstance(child, Node):
            yield child
            yield from walk(child)


def text_content(node):
    pieces = []
    for child in node.children:
        pieces.append(text_content(child) if isinstance(child, Node) else child)
    return " ".join("".join(pieces).split())


def find_all(node, predicate):
    return [candidate for candidate in walk(node) if predicate(candidate)]


def inner_html(node, accent_spans=False):
    rendered = []
    for child in node.children:
        if isinstance(child, str):
            rendered.append(html.escape(child, quote=False))
            continue
        if child.tag == "img":
            continue
        content = inner_html(child, accent_spans)
        if child.tag in {"strong", "b", "em", "i", "span", "a", "br", "code"}:
            if child.tag == "br":
                rendered.append("<br>")
            elif child.tag == "a":
                href = attr(child, "href")
                if href:
                    rendered.append(f'<a href="{html.escape(href, quote=True)}">{content}</a>')
                else:
                    rendered.append(content)
            elif child.tag == "span" and accent_spans:
                rendered.append(f'<span style="color:#089eaa">{content}</span>')
            else:
                rendered.append(f"<{child.tag}>{content}</{child.tag}>")
        else:
            rendered.append(content)
    return "".join(rendered).strip()


def paragraph_block(content, label=False):
    if label:
        settings = '{"style":{"color":{"text":"#089eaa"},"typography":{"fontSize":"0.75rem"}}}'
        styles = ' class="has-text-color" style="color:#089eaa;font-size:0.75rem"'
    else:
        settings = ""
        styles = ""
    return f"<!-- wp:paragraph {settings} -->\n<p{styles}>{content}</p>\n<!-- /wp:paragraph -->"


def heading_block(level, content, style=None):
    attributes = {"level": level}
    if style:
        attributes["style"] = style
    settings = json.dumps(attributes, ensure_ascii=False, separators=(",", ":"))
    return f'<!-- wp:heading {settings} -->\n<h{level} class="wp-block-heading">{content}</h{level}>\n<!-- /wp:heading -->'


def list_block(items):
    entries = []
    for item in items:
        entries.append(f"<!-- wp:list-item -->\n<li>{html.escape(item)}</li>\n<!-- /wp:list-item -->")
    inner = "\n".join(entries)
    return f'<!-- wp:list {{"className":"wp-block-list"}} -->\n<ul class="wp-block-list">\n{inner}\n</ul>\n<!-- /wp:list -->'


def group_block(content, settings=None):
    settings = settings or {}
    serialized = json.dumps(settings, ensure_ascii=False, separators=(",", ":")) if settings else ""
    background = settings.get("style", {}).get("color", {}).get("background")
    color = settings.get("style", {}).get("color", {}).get("text")
    classes_attr = "wp-block-group"
    style_parts = []
    if background:
        classes_attr += " has-background"
        style_parts.append(f"background-color:{background}")
    if color:
        classes_attr += " has-text-color"
        style_parts.append(f"color:{color}")
    spacing = settings.get("style", {}).get("spacing", {}).get("padding", {})
    for side in ("top", "right", "bottom", "left"):
        if side in spacing:
            style_parts.append(f"padding-{side}:{spacing[side]}")
    style_attr = f' style="{html.escape(";".join(style_parts), quote=True)}"' if style_parts else ""
    if settings.get("align") == "full":
        classes_attr += " alignfull"
    anchor = settings.get("anchor")
    id_attr = f' id="{html.escape(anchor, quote=True)}"' if anchor else ""
    return f"<!-- wp:group {serialized} -->\n<div class=\"{classes_attr}\"{id_attr}{style_attr}>\n{content}\n</div>\n<!-- /wp:group -->"


def columns_block(items):
    cols = []
    for content in items:
        cols.append(f'<!-- wp:column -->\n<div class="wp-block-column">\n{content}\n</div>\n<!-- /wp:column -->')
    columns = "\n".join(cols)
    return f'<!-- wp:columns -->\n<div class="wp-block-columns">\n{columns}\n</div>\n<!-- /wp:columns -->'


def buttons_block(buttons):
    button_blocks = []
    for label, href in buttons:
        href_attr = f' href="{html.escape(href, quote=True)}"' if href else ""
        button_blocks.append(
            f'<!-- wp:button -->\n<div class="wp-block-button"><a class="wp-block-button__link wp-element-button"{href_attr}>{html.escape(label)}</a></div>\n<!-- /wp:button -->'
        )
    rendered_buttons = "\n".join(button_blocks)
    return f'<!-- wp:buttons -->\n<div class="wp-block-buttons">\n{rendered_buttons}\n</div>\n<!-- /wp:buttons -->'


def render_node(node):
    if node.tag in {"script", "style", "nav", "header", "footer"}:
        return ""
    if node.tag == "img":
        if "profile" in attr(node, "src").lower():
            return paragraph_block("[PHOTO DE PROFIL : importer assets/images/profile.png dans la médiathèque puis remplacer ce repère par un bloc Image circulaire.]" )
        return ""
    if node.tag == "p":
        if "hero-actions" in classes(node):
            buttons = []
            for link in (child for child in node.children if isinstance(child, Node) and child.tag == "a"):
                buttons.append((text_content(link), attr(link, "href")))
            return buttons_block(buttons)
        return paragraph_block(inner_html(node), "section-label" in classes(node) or "eyebrow" in classes(node))
    if node.tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
        level = int(node.tag[1])
        if level == 1:
            return heading_block(level, inner_html(node, accent_spans=True), {"typography": {"fontSize": "4rem", "lineHeight": "0.95"}})
        return heading_block(level, inner_html(node))
    if node.tag in {"ul", "ol"}:
        items = [text_content(child) for child in node.children if isinstance(child, Node) and child.tag == "li"]
        return list_block(items)
    if node.tag == "li":
        return ""
    if node.tag == "a":
        return paragraph_block(inner_html(node))
    if node.tag == "br":
        return ""
    if node.tag in {"section", "article", "div"}:
        if "journey-columns" in classes(node):
            columns = [render_node(child) for child in node.children if isinstance(child, Node) and child.tag == "div"]
            return columns_block([column for column in columns if column])
        children = [render_node(child) if isinstance(child, Node) else "" for child in node.children]
        children = [child for child in children if child]
        if not children:
            return ""
        return group_block("\n".join(children))
    return "".join(render_node(child) if isinstance(child, Node) else "" for child in node.children)


def section_settings(section_id):
    background, color = SECTION_COLORS[section_id]
    return {
        "align": "full",
        "anchor": section_id,
        "style": {
            "color": {"background": background, "text": color},
            "spacing": {"padding": {"top": "4rem", "right": "2rem", "bottom": "4rem", "left": "2rem"}},
        },
    }


def nav_content():
    names = (("Accueil", "accueil"), ("À propos", "a-propos"), ("Parcours", "parcours"), ("Compétences", "competences"), ("Projets", "projets"), ("Centres d’intérêt", "interets"), ("CV", "cv"), ("Contact", "contact"))
    links = []
    for label, anchor in names:
        settings = {"label": label, "type": "custom", "url": f"{HOME_URL}#{anchor}", "kind": "custom"}
        links.append(f"<!-- wp:navigation-link {json.dumps(settings, ensure_ascii=False, separators=(',', ':'))} /-->")
    nav = '<!-- wp:navigation {"overlayMenu":"mobile","layout":{"type":"flex","justifyContent":"right"}} -->\n' + "\n".join(links) + "\n<!-- /wp:navigation -->"
    brand = paragraph_block('<strong>FAM</strong> &nbsp; Faust Auriol Mbingou')
    return group_block(
        columns_block([brand, nav]),
        {"align": "full", "style": {"color": {"background": "#071727", "text": "#ffffff"}, "spacing": {"padding": {"top": "0.75rem", "bottom": "0.75rem", "left": "1.25rem", "right": "1.25rem"}}}},
    )


def project_card(project, destination):
    title = html.escape(project["title"])
    category = html.escape(project.get("category", ""))
    details = []
    if project.get("reference"):
        details.append(html.escape(project["reference"]))
    if project.get("technologies"):
        details.append(" · ".join(html.escape(item) for item in project["technologies"]))
    body = [paragraph_block(f'<span style="color:#089eaa">{category}</span>')]
    body.append(heading_block(3, title))
    if details:
        body.append(paragraph_block("<br>".join(details)))
    body.append(buttons_block([("Voir le projet", destination)]))
    return group_block("\n".join(body), {"style": {"color": {"background": "#f7f9fc", "text": "#071727"}, "spacing": {"padding": {"top": "1.25rem", "right": "1.25rem", "bottom": "1.25rem", "left": "1.25rem"}}}})


def find_project_source(project):
    path = ROOT / project["url"]
    if not path.is_file():
        raise ValueError(f"Fichier projet introuvable : {path}")
    document = parse_html(path.read_text(encoding="utf-8"))
    title_nodes = find_all(document, lambda node: node.tag == "title")
    body_nodes = find_all(document, lambda node: node.tag == "body")
    source_title = text_content(title_nodes[0]) if title_nodes else ""
    expected_title = project["title"].casefold()
    if expected_title not in source_title.casefold():
        raise ValueError(f"Titre de projet incohérent dans {path.name} : {source_title}")
    project_id = attr(body_nodes[0], "data-project") if body_nodes else ""
    if project_id and project_id != Path(project["url"]).stem:
        raise ValueError(f"Identifiant data-project incohérent dans {path.name}")
    return document


def extract_sae_203(document):
    def by_class(name):
        matches = find_all(document, lambda node: name in classes(node))
        return matches[0] if matches else None

    overview = by_class("project-overview")
    work = by_class("project-checklist")
    skills = by_class("project-skill-tags")
    qualities = by_class("project-qualities")
    paragraphs = [text_content(node) for node in find_all(overview, lambda node: node.tag == "p" and "section-label" not in classes(node))] if overview else []
    work_items = [text_content(node) for node in find_all(work, lambda node: node.tag == "li")] if work else []
    skill_items = [text_content(node) for node in find_all(skills, lambda node: node.tag == "li")] if skills else []
    soft, other = [], []
    if qualities:
        columns = [node for node in qualities.children if isinstance(node, Node) and node.tag == "div"]
        for index, column in enumerate(columns):
            items = [text_content(node) for node in find_all(column, lambda node: node.tag == "li")]
            if index == 0:
                soft = items
            else:
                other = items
    return {"presentation": paragraphs, "work": work_items, "skills": skill_items, "soft": soft, "other": other}


def project_page(project, detail, destination):
    sections = []
    back = buttons_block([("← Retour aux projets", f"{HOME_URL}#projets")])
    lead = [
        paragraph_block(f'<span style="color:#089eaa">{html.escape(detail.get("category", project.get("category", "")))}</span>'),
        heading_block(1, html.escape(project["title"])),
        back,
    ]
    sections.append(group_block("\n".join(lead), {"align": "full", "style": {"color": {"background": "#f7f9fc", "text": "#071727"}, "spacing": {"padding": {"top": "4rem", "right": "2rem", "bottom": "4rem", "left": "2rem"}}}}))
    presentation = detail.get("presentation", [])
    sections.append(group_block("\n".join([heading_block(2, "Présentation du projet.")] + [paragraph_block(html.escape(item)) for item in presentation]), {"align": "full", "style": {"color": {"background": "#ffffff", "text": "#071727"}, "spacing": {"padding": {"top": "3rem", "right": "2rem", "bottom": "3rem", "left": "2rem"}}}}))
    if detail.get("work"):
        sections.append(group_block("\n".join([heading_block(2, "Objectifs &amp; travail réalisé.") , list_block(detail["work"])]), {"align": "full", "style": {"color": {"background": "#f7f9fc", "text": "#071727"}, "spacing": {"padding": {"top": "3rem", "right": "2rem", "bottom": "3rem", "left": "2rem"}}}}))
    skills = detail.get("skills", project.get("technologies", []))
    if skills:
        sections.append(group_block("\n".join([heading_block(2, "Compétences mobilisées."), list_block(skills)]), {"align": "full", "style": {"color": {"background": "#071727", "text": "#ffffff"}, "spacing": {"padding": {"top": "3rem", "right": "2rem", "bottom": "3rem", "left": "2rem"}}}}))
    for label, title, key in (("Savoir-être", "Approche personnelle.", "soft"), ("Autres savoir-faire", "Pratiques complémentaires.", "other")):
        if detail.get(key):
            sections.append(group_block("\n".join([paragraph_block(label, True), heading_block(2, title), list_block(detail[key])]), {"align": "full", "style": {"color": {"background": "#ffffff", "text": "#071727"}, "spacing": {"padding": {"top": "2rem", "right": "2rem", "bottom": "2rem", "left": "2rem"}}}}))
    sections.append(group_block(back, {"align": "full", "style": {"color": {"background": "#f7f9fc", "text": "#071727"}, "spacing": {"padding": {"top": "2rem", "right": "2rem", "bottom": "2rem", "left": "2rem"}}}}))
    return "\n\n".join(sections) + "\n"


def load_links(slugs):
    path = EXPORT / "project-links.json"
    if not path.exists():
        return {slug: f"{{{{WORDPRESS_PROJECT_URL:{slug}}}}}" for slug in slugs}, False
    links = json.loads(path.read_text(encoding="utf-8"))
    if set(links) != set(slugs):
        raise ValueError("project-links.json doit contenir exactement les huit slugs projet.")
    for slug, url in links.items():
        parsed = urlparse(url)
        if parsed.scheme != "https" or not parsed.netloc:
            raise ValueError(f"Destination HTTPS manquante ou invalide pour {slug}.")
    return links, True


def home_content(source, skills, projects, links):
    main = next(iter(find_all(source, lambda node: node.tag == "main")), None)
    if main is None:
        raise ValueError("main introuvable dans index.html")
    source_sections = {attr(node, "id"): node for node in find_all(main, lambda node: node.tag == "section" and attr(node, "id"))}
    missing = [anchor for anchor in ANCHORS if anchor not in source_sections]
    if missing:
        raise ValueError(f"Ancres absentes de index.html : {', '.join(missing)}")

    output = []
    for anchor in ANCHORS:
        section = source_sections[anchor]
        if anchor == "competences":
            items = []
            for category in skills:
                category_content = heading_block(3, html.escape(category["category"])) + "\n" + list_block(category["items"])
                items.append(group_block(category_content, {"style": {"color": {"background": "#0c2237", "text": "#ffffff"}, "spacing": {"padding": {"top": "1rem", "right": "1rem", "bottom": "1rem", "left": "1rem"}}}}))
            content = heading_block(2, "Compétences techniques.") + "\n" + columns_block(items)
        elif anchor == "projets":
            cards = [project_card(project, links[Path(project["url"]).stem]) for project in projects]
            content = heading_block(2, "Mes projets.") + "\n" + paragraph_block("Une sélection de projets réalisés au cours de mon parcours en informatique.") + "\n" + columns_block(cards[:4]) + "\n" + columns_block(cards[4:])
        else:
            if anchor == "accueil":
                hero_copy = next((child for child in section.children if isinstance(child, Node) and "hero-copy" in classes(child)), None)
                hero_visual = next((child for child in section.children if isinstance(child, Node) and "hero-visual" in classes(child)), None)
                if hero_copy is None or hero_visual is None:
                    raise ValueError("Colonnes du bandeau d’accueil introuvables dans index.html")
                content = columns_block([render_node(hero_copy), render_node(hero_visual)])
            else:
                content = "\n".join(render_node(child) for child in section.children if isinstance(child, Node))
            if anchor == "cv":
                content += "\n" + buttons_block([("Télécharger mon CV", "")])
                content += "\n" + paragraph_block("[CV PROVISOIRE : importer documents/cv.pdf dans la médiathèque et remplacer le bouton provisoire par son lien.]" )
        output.append(group_block(content, section_settings(anchor)))
    return "\n\n".join(output) + "\n"


def navigation_content():
    return nav_content() + "\n"


def write_generated(projects, project_details, skills, links):
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    generated = GENERATED / timestamp
    project_output = generated / "projects"
    project_output.mkdir(parents=True)

    source = parse_html((ROOT / "index.html").read_text(encoding="utf-8"))
    home = home_content(source, skills, projects, links)
    (generated / "accueil-gutenberg.html").write_text(home, encoding="utf-8")
    (generated / "navigation-entete-gutenberg.html").write_text(navigation_content(), encoding="utf-8")

    project_html = []
    slugs = []
    for project in projects:
        slug = Path(project["url"]).stem
        slugs.append(slug)
        source_doc = find_project_source(project)
        detail = project_details.get(slug)
        if slug == "sae-2-03":
            detail = {"category": project.get("reference", project.get("category", "")), **extract_sae_203(source_doc)}
        if not detail:
            raise ValueError(f"Données détaillées introuvables pour {slug}")
        result = project_page(project, detail, links[slug])
        target = project_output / f"{slug}.html"
        target.write_text(result, encoding="utf-8")
        project_html.append(target)

    template = """<!-- Modèle de contenu à personnaliser dans Gutenberg. Les vrais contenus des huit projets sont dans projects/*.html. -->
<!-- wp:group {\"align\":\"full\",\"style\":{\"color\":{\"background\":\"#f7f9fc\",\"text\":\"#071727\"},\"spacing\":{\"padding\":{\"top\":\"4rem\",\"bottom\":\"4rem\",\"left\":\"2rem\",\"right\":\"2rem\"}}}} -->
<div class=\"wp-block-group alignfull has-background has-text-color\" style=\"background-color:#f7f9fc;color:#071727;padding:4rem 2rem\">
<!-- wp:paragraph {\"style\":{\"color\":{\"text\":\"#089eaa\"}}} --><p class=\"has-text-color\" style=\"color:#089eaa\">[Catégorie du projet]</p><!-- /wp:paragraph -->
<!-- wp:heading {\"level\":1} --><h1 class=\"wp-block-heading\">[Titre du projet]</h1><!-- /wp:heading -->
<!-- wp:buttons --><div class=\"wp-block-buttons\"><!-- wp:button --><div class=\"wp-block-button\"><a class=\"wp-block-button__link wp-element-button\" href=\"https://portfolioauriol.wordpress.com/accueil/#projets\">← Retour aux projets</a></div><!-- /wp:button --></div><!-- /wp:buttons -->
</div>
<!-- /wp:group -->
<!-- Ajouter ensuite Présentation, Travail réalisé, Compétences, Savoir-être et autres savoir-faire uniquement si leurs données existent. -->
"""
    (generated / "modele-page-projet.html").write_text(template, encoding="utf-8")

    home_text = (generated / "accueil-gutenberg.html").read_text(encoding="utf-8")
    nav_text = (generated / "navigation-entete-gutenberg.html").read_text(encoding="utf-8")
    if "<!-- wp:page-list /-->" in nav_text or "wp:page-list" in nav_text:
        raise ValueError("La navigation exportée contient encore un bloc Page List.")
    if len(re.findall(r"<!-- wp:navigation-link ", nav_text)) != 8:
        raise ValueError("La navigation doit contenir exactement huit liens.")
    for anchor in ANCHORS:
        if f'"anchor":"{anchor}"' not in home_text:
            raise ValueError(f"Ancre Gutenberg absente : {anchor}")
    titles = [project["title"] for project in projects]
    if any(home_text.count(html.escape(title)) < 1 for title in titles):
        raise ValueError("Un ou plusieurs titres de projet manquent dans l’accueil exporté.")
    if len(re.findall(r"Voir le projet", home_text)) != 8:
        raise ValueError("L’accueil exporté ne contient pas huit boutons projet.")
    destinations = re.findall(
        r'<a class="wp-block-button__link wp-element-button" href="(\{\{WORDPRESS_PROJECT_URL:[^\"]+\}\}|https://[^\"]+)">Voir le projet</a>',
        home_text,
    )
    if len(destinations) != 8:
        raise ValueError("Les huit destinations projet ne sont pas présentes dans l’accueil exporté.")
    if len(project_html) != 8:
        raise ValueError("Huit contenus projet doivent être générés.")

    manifest = {
        "network_requests": False,
        "published": False,
        "project_count": len(projects),
        "project_links_verified": not any("{{WORDPRESS_PROJECT_URL:" in item for item in destinations),
        "project_slugs": slugs,
        "anchors": ANCHORS,
        "destination_count": len(destinations),
        "generated_project_pages": [f"projects/{path.name}" for path in project_html],
    }
    (generated / "verification.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    backup = BACKUPS / timestamp
    shutil.copytree(generated, backup)
    return manifest, backup, generated


def main():
    projects = json.loads((ROOT / "data/projects.json").read_text(encoding="utf-8"))
    project_details = json.loads((ROOT / "data/project-details.json").read_text(encoding="utf-8"))
    skills = json.loads((ROOT / "data/skills.json").read_text(encoding="utf-8"))
    if len(projects) != 8:
        raise ValueError(f"Huit projets attendus dans projects.json, trouvé : {len(projects)}")
    if not (ROOT / "index.html").is_file():
        raise ValueError("index.html introuvable")
    slugs = [Path(project["url"]).stem for project in projects]
    links, configured = load_links(slugs)
    manifest, backup, generated = write_generated(projects, project_details, skills, links)
    print(f"Export Gutenberg créé dans : {generated}")
    print(f"Sauvegarde locale horodatée : {backup}")
    print(f"Sections vérifiées : {len(manifest['anchors'])}")
    print(f"Projets et destinations repérés : {manifest['project_count']} / {manifest['destination_count']}")
    print(f"URL WordPress des projets vérifiées : {'oui' if configured else 'non — marqueurs à remplacer par les URL déjà publiées'}")
    print("Aucune requête réseau effectuée ; aucune publication ou modification distante.")


if __name__ == "__main__":
    main()