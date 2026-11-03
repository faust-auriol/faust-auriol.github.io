const menuToggle = document.querySelector('.menu-toggle');
const menu = document.querySelector('#menu');

menuToggle?.addEventListener('click', () => {
  const isOpen = menu.classList.toggle('is-open');
  menuToggle.setAttribute('aria-expanded', String(isOpen));
});

menu?.querySelectorAll('a').forEach((link) => link.addEventListener('click', () => {
  menu.classList.remove('is-open');
  menuToggle?.setAttribute('aria-expanded', 'false');
}));

document.querySelector('#current-year').textContent = new Date().getFullYear();

function createTagList(items, className) {
  const list = document.createElement('ul');
  list.className = className;
  items.forEach((item) => {
    const tag = document.createElement('li');
    tag.textContent = item;
    list.append(tag);
  });
  return list;
}

function createProjectIllustration(projectId, imageData) {
  if (!imageData?.src) return null;

  const figure = document.createElement('figure');
  figure.className = 'project-illustration project-card-illustration';
  const image = document.createElement('img');
  image.src = imageData.src;
  image.alt = imageData.alt;
  image.width = 960;
  image.height = 540;
  image.loading = 'lazy';
  image.addEventListener('error', () => {
    const svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 540"><rect width="960" height="540" fill="#071727"/><path d="M260 360h440M340 270h280M410 180h140" stroke="#39d6cf" stroke-width="18" stroke-linecap="round"/><circle cx="300" cy="360" r="24" fill="#39d6cf"/><circle cx="480" cy="270" r="24" fill="#39d6cf"/><circle cx="660" cy="360" r="24" fill="#39d6cf"/></svg>';
    if (!image.dataset.fallbackApplied) {
      image.dataset.fallbackApplied = 'true';
      image.alt = 'Illustration de remplacement ; image source indisponible.';
      image.src = `data:image/svg+xml,${encodeURIComponent(svg)}`;
    }
  }, { once: true });
  figure.append(image);

  const caption = document.createElement('figcaption');
  caption.append('Illustration générique · ');
  const source = document.createElement('a');
  source.href = imageData.source;
  source.target = '_blank';
  source.rel = 'noreferrer';
  source.textContent = `${imageData.artist}, ${imageData.license}`;
  caption.append(source);
  figure.append(caption);
  figure.dataset.project = projectId;
  return figure;
}

async function renderPortfolioData() {
  const skillsList = document.querySelector('#skills-list');
  const projectsList = document.querySelector('#projects-list');
  if (!skillsList || !projectsList) return;

  try {
    const [skillsResponse, projectsResponse, imagesResponse] = await Promise.all([
      fetch('data/skills.json'),
      fetch('data/projects.json'),
      fetch('wordpress-export/project-images.json'),
    ]);
    if (!skillsResponse.ok || !projectsResponse.ok || !imagesResponse.ok) throw new Error('Données indisponibles');

    const skills = await skillsResponse.json();
    const projects = await projectsResponse.json();
    const images = await imagesResponse.json();
    skills.forEach(({ category, items }) => {
      const card = document.createElement('article');
      card.className = 'skill-category';
      const title = document.createElement('h3');
      title.textContent = category;
      card.append(title, createTagList(items, 'skill-list'));
      skillsList.append(card);
    });

    projects.forEach(({ title, technologies, category, url, reference }, index) => {
      const card = document.createElement('article');
      card.className = 'project-card';
      const projectId = url.split('/').pop().replace(/\.html$/, '');
      const illustration = createProjectIllustration(projectId, images[projectId]);
      if (illustration) card.append(illustration);
      const number = document.createElement('span');
      number.className = 'project-number';
      number.textContent = category || String(index + 1).padStart(2, '0');
      const heading = document.createElement('h3');
      heading.textContent = title;
      card.append(number, heading);
      // Afficher la référence du projet si disponible
      if (reference) {
        const ref = document.createElement('p');
        ref.className = 'project-ref';
        ref.textContent = reference;
        card.append(ref);
      }
      if (technologies?.length) card.append(createTagList(technologies, 'project-tags'));
      const button = document.createElement(url ? 'a' : 'span');
      button.className = url ? 'button' : 'button button-disabled';
      if (url) {
        button.href = url;
      } else {
        button.setAttribute('aria-disabled', 'true');
      }
      button.textContent = 'Voir le projet';
      card.append(button);
      projectsList.append(card);
    });
  } catch (error) {
    console.error('Impossible de charger les données du portfolio.', error);
    const message = document.createElement('p');
    message.className = 'data-load-notice';
    message.textContent = 'Les données du portfolio ne sont pas disponibles pour le moment.';
    document.querySelector('#skills-list')?.append(message.cloneNode(true));
    document.querySelector('#projects-list')?.append(message);
  }
}

renderPortfolioData();

// Vérifie si le CV PDF est présent et active le bouton de téléchargement
async function checkAndActivateCV() {
  const container = document.querySelector('#cv');
  if (!container) return;
  const disabledBtn = container.querySelector('.button-disabled');
  try {
    const resp = await fetch('documents/cv.pdf', { method: 'HEAD' });
    if (resp.ok && disabledBtn) {
      const link = document.createElement('a');
      link.className = 'button';
      link.href = 'documents/cv.pdf';
      link.setAttribute('download', '');
      link.innerHTML = 'Télécharger mon CV <span aria-hidden="true">↓</span>';
      disabledBtn.replaceWith(link);
    }
  } catch (e) {
    // En local sans serveur ou en cas d'erreur, laisser le bouton désactivé
  }
}

checkAndActivateCV();
