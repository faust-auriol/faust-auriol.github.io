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

async function renderProjectDetail() {
  const projectId = document.body.dataset.project;
  const main = document.querySelector('#project-content');
  if (!projectId || !main) return;

  try {
    const response = await fetch('../data/project-details.json');
    if (!response.ok) throw new Error('Données indisponibles');
    const projects = await response.json();
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
