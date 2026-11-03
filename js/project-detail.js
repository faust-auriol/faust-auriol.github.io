function createList(items, className) {
  const list = document.createElement('ul');
  list.className = className;
  items.forEach((item) => {
    const entry = document.createElement('li');
    entry.textContent = item;
    list.append(entry);
  });
  return list;
}

function createHeading(label, title) {
  const heading = document.createElement('div');
  heading.className = 'project-section-heading';
  const labelElement = document.createElement('p');
  labelElement.className = 'section-label';
  labelElement.textContent = label;
  const titleElement = document.createElement('h2');
  const [first, ...rest] = title.split(' ');
  titleElement.append(`${first} `);
  const emphasis = document.createElement('em');
  emphasis.textContent = rest.join(' ');
  titleElement.append(emphasis);
  heading.append(labelElement, titleElement);
  return heading;
}

function createContentSection(className, label, title, content) {
  const section = document.createElement('section');
  section.className = `project-section ${className}`;
  section.append(createHeading(label, title), content);
  return section;
}

function createProjectIllustration(projectId, imageData) {
  if (!imageData || !imageData.src) return null;

  const figure = document.createElement('figure');
  figure.className = 'project-illustration';
  figure.style.backgroundColor = '#071727';
  const image = document.createElement('img');
  image.src = imageData.src;
  image.alt = imageData.alt;
  image.loading = 'lazy';
  image.style.aspectRatio = '16 / 9';
  image.style.objectFit = 'cover';
  image.width = 960;
  image.height = 540;
  image.addEventListener('error', () => {
    if (image.dataset.fallbackApplied) {
      const placeholder = document.createElement('p');
      placeholder.className = 'project-image-fallback';
      placeholder.textContent = 'Illustration indisponible. Le contenu du projet reste accessible.';
      figure.replaceChildren(placeholder);
      figure.classList.add('is-fallback');
      return;
    }

    image.dataset.fallbackApplied = 'true';
    image.alt = 'Illustration de remplacement ; image source indisponible.';
    const svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 540"><rect width="960" height="540" fill="#071727"/><path d="M260 360h440M340 270h280M410 180h140" stroke="#39d6cf" stroke-width="18" stroke-linecap="round"/><circle cx="300" cy="360" r="24" fill="#39d6cf"/><circle cx="480" cy="270" r="24" fill="#39d6cf"/><circle cx="660" cy="360" r="24" fill="#39d6cf"/></svg>';
    image.src = `data:image/svg+xml,${encodeURIComponent(svg)}`;
  }, { once: false });
  figure.append(image);

  const caption = document.createElement('figcaption');
  caption.append('Illustration générique, ne représentant pas une capture de cette réalisation. ');
  const sourceLink = document.createElement('a');
  sourceLink.href = imageData.source;
  sourceLink.target = '_blank';
  sourceLink.rel = 'noreferrer';
  sourceLink.textContent = `Source : ${imageData.artist} — ${imageData.license}`;
  caption.append(sourceLink);
  figure.append(caption);
  figure.dataset.project = projectId;
  return figure;
}

async function renderProjectDetail() {
  const projectId = document.body.dataset.project;
  const main = document.querySelector('#project-content');
  if (!projectId || !main) return;

  try {
    const [response, imageResponse] = await Promise.all([
      fetch('../data/project-details.json'),
      fetch('../wordpress-export/project-images.json').catch(() => null),
    ]);
    if (!response.ok) throw new Error('Données indisponibles');
    const projects = await response.json();
    const imageManifest = imageResponse?.ok ? await imageResponse.json() : {};
    const project = projects[projectId];
    if (!project) throw new Error('Projet introuvable');

    const hero = document.createElement('section');
    hero.className = 'project-hero';
    const backLink = document.createElement('a');
    backLink.className = 'project-back-link';
    backLink.href = '../index.html#projets';
    backLink.textContent = '← Retour aux projets';
    const category = document.createElement('p');
    category.className = 'eyebrow';
    category.textContent = project.category;
    const heading = document.createElement('h1');
    heading.textContent = project.title;
    hero.append(backLink, category, heading);
    main.append(hero);

    const illustration = createProjectIllustration(projectId, imageManifest[projectId]);
    if (illustration) main.append(illustration);

    const presentation = document.createElement('div');
    project.presentation.forEach((paragraph, index) => {
      const text = document.createElement('p');
      text.textContent = paragraph;
      if (index === 0) text.className = 'project-lead';
      presentation.append(text);
    });
    main.append(createContentSection('project-overview', '01 — Contexte', 'Présentation du projet.', presentation));

    if (project.work?.length) main.append(createContentSection('project-work-section', '02 — Réalisation', 'Objectifs & travail réalisé.', createList(project.work, 'project-checklist')));

    main.append(createContentSection('project-skills-section', '03 — Compétences', 'Compétences mobilisées.', createList(project.skills, 'project-skill-tags')));

    if (project.soft?.length || project.other?.length) {
      const human = document.createElement('div');
      human.className = 'project-qualities';
      if (project.soft?.length) {
        const soft = document.createElement('div');
        soft.append(createHeading('04 — Savoir-être', 'Approche personnelle.'), createList(project.soft, 'project-plain-list'));
        human.append(soft);
      }
      if (project.other?.length) {
        const other = document.createElement('div');
        other.append(createHeading('05 — Autres savoir-faire', 'Pratiques complémentaires.'), createList(project.other, 'project-plain-list'));
        human.append(other);
      }
      const section = document.createElement('section');
      section.className = 'project-section project-human-section';
      section.append(human);
      main.append(section);
    }

    const returnSection = document.createElement('section');
    returnSection.className = 'project-return-section';
    const returnButton = document.createElement('a');
    returnButton.className = 'button';
    returnButton.href = '../index.html#projets';
    returnButton.textContent = '← Retour aux projets';
    returnSection.append(returnButton);
    main.append(returnSection);
  } catch (error) {
    console.error('Impossible de charger la fiche projet.', error);
  }
}

renderProjectDetail();
