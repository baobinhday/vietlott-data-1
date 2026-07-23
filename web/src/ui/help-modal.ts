import { t } from '../i18n.js';
import { resetPipeline } from '../state.js';

export function renderHelpModal(): HTMLElement {
  const overlay = document.createElement('div');
  overlay.className = 'help-overlay fade-in';

  const sheet = document.createElement('div');
  sheet.className = 'help-sheet';

  const header = document.createElement('div');
  header.className = 'panel-header';
  const title = document.createElement('h2');
  title.className = 'card-title';
  title.textContent = t('help.title');
  const closeBtn = document.createElement('button');
  closeBtn.className = 'icon-btn';
  closeBtn.innerHTML = '✕';
  closeBtn.addEventListener('click', close);
  header.append(title, closeBtn);
  sheet.appendChild(header);

  const body = document.createElement('div');
  body.className = 'help-body';

  const sections = [
    {
      heading: t('help.whatIsThis'),
      text: t('help.whatIsThis.text'),
    },
    {
      heading: t('help.strategies'),
      text: t('help.strategies.text'),
    },
    {
      heading: t('help.howTo'),
      text: t('help.howTo.text'),
    },
    {
      heading: t('help.docs'),
      text: 'Xem helper.md trong repository để biết ví dụ API.',
    },
  ];

  for (const section of sections) {
    const h = document.createElement('h3');
    h.className = 'help-heading';
    h.textContent = section.heading;
    const p = document.createElement('p');
    p.className = 'help-text';
    p.textContent = section.text;
    body.append(h, p);
  }

  const docLink = document.createElement('a');
  docLink.className = 'btn btn-secondary';
  docLink.href = 'https://github.com/vietvudanh/vietlott-data/blob/main/helper.md';
  docLink.target = '_blank';
  docLink.rel = 'noopener noreferrer';
  docLink.textContent = t('help.openDocs');
  body.appendChild(docLink);

  const resetBtn = document.createElement('button');
  resetBtn.className = 'btn btn-danger';
  resetBtn.style.marginTop = '12px';
  resetBtn.textContent = t('help.resetEmpty');
  resetBtn.addEventListener('click', () => {
    if (confirm(t('header.resetConfirm'))) {
      resetPipeline();
      close();
    }
  });
  body.appendChild(resetBtn);

  sheet.appendChild(body);
  overlay.appendChild(sheet);

  overlay.addEventListener('click', (e) => {
    if (e.target === overlay) close();
  });

  document.addEventListener('keydown', onKeydown);

  function close() {
    overlay.remove();
    document.removeEventListener('keydown', onKeydown);
  }

  function onKeydown(e: KeyboardEvent) {
    if (e.key === 'Escape') close();
  }

  return overlay;
}
