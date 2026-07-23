import { t } from '../i18n.js';
import { getState, subscribe, applyPreset, addGroup, PIPELINE_PRESETS } from '../state.js';

export function renderOnboarding(): HTMLElement {
  const container = document.createElement('div');
  container.className = 'onboarding card';

  const heading = document.createElement('h2');
  heading.className = 'onboarding-title';
  heading.textContent = t('onboarding.title');
  container.appendChild(heading);

  const intro = document.createElement('p');
  intro.className = 'onboarding-intro';
  intro.textContent = t('onboarding.intro');
  container.appendChild(intro);

  const help = renderHelpAccordion();
  container.appendChild(help);

  const presetKeys = [
    { name: 'preset.steinerTopNumbers', desc: 'preset.steinerTopNumbers.desc' },
    { name: 'preset.hybridPool', desc: 'preset.hybridPool.desc' },
    { name: 'preset.frequencyMarkov', desc: 'preset.frequencyMarkov.desc' },
    { name: 'preset.longAbsence', desc: 'preset.longAbsence.desc' },
  ];

  const presets = document.createElement('div');
  presets.className = 'preset-grid';
  for (let i = 0; i < PIPELINE_PRESETS.length; i++) {
    const keys = presetKeys[i];
    const btn = document.createElement('button');
    btn.className = 'preset-card';
    btn.type = 'button';

    const title = document.createElement('span');
    title.className = 'preset-card-title';
    title.textContent = t(keys.name);

    const desc = document.createElement('span');
    desc.className = 'preset-card-desc';
    desc.textContent = t(keys.desc);

    btn.append(title, desc);
    btn.addEventListener('click', () => applyPreset(i));
    presets.appendChild(btn);
  }
  container.appendChild(presets);

  const or = document.createElement('div');
  or.className = 'onboarding-divider';
  or.textContent = t('onboarding.or');
  container.appendChild(or);

  const manualBtn = document.createElement('button');
  manualBtn.className = 'btn btn-secondary btn-block';
  manualBtn.textContent = t('onboarding.addManual');
  manualBtn.addEventListener('click', () => addGroup());
  container.appendChild(manualBtn);

  function update() {
    if (!container.isConnected) return;
    const hasGroups = getState().pipeline.groups.length > 0;
    container.style.display = hasGroups ? 'none' : '';
  }

  update();
  subscribe(update);
  return container;
}

function renderHelpAccordion(): HTMLElement {
  const details = document.createElement('details');
  details.className = 'help-accordion';

  const summary = document.createElement('summary');
  summary.className = 'help-accordion-summary';
  summary.textContent = t('onboarding.whatIsPipeline');
  details.appendChild(summary);

  const body = document.createElement('div');
  body.className = 'help-accordion-body';

  const bullets = [
    t('onboarding.bullet1'),
    t('onboarding.bullet2'),
    t('onboarding.bullet3'),
    t('onboarding.bullet4'),
  ];

  const ul = document.createElement('ul');
  for (const text of bullets) {
    const li = document.createElement('li');
    li.textContent = text;
    ul.appendChild(li);
  }
  body.appendChild(ul);
  details.appendChild(body);

  return details;
}
