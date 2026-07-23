import { t } from '../i18n.js';
import { setPipeline, getState, subscribe } from '../state.js';

export function renderFilterEditor(): HTMLElement {
  const container = document.createElement('div');
  container.className = 'card';

  const header = document.createElement('div');
  header.className = 'panel-header filter-header';
  header.style.cursor = 'pointer';
  const title = document.createElement('h2');
  title.className = 'card-title';
  title.textContent = t('filters.title');
  const chevron = document.createElement('span');
  chevron.className = 'filter-chevron';
  chevron.innerHTML = '›';
  header.append(title, chevron);
  container.appendChild(header);

  const body = document.createElement('div');
  body.className = 'filter-body';
  body.style.maxHeight = '0';
  body.style.overflow = 'hidden';

  const grid = document.createElement('div');
  grid.className = 'filter-grid';

  const fields: { key: keyof typeof state.pipeline.post_filters; label: string; tooltip: string }[] = [
    { key: 'min_sum', label: t('filters.min_sum'), tooltip: t('filter.minSum.tooltip') },
    { key: 'max_sum', label: t('filters.max_sum'), tooltip: t('filter.maxSum.tooltip') },
    { key: 'min_even', label: t('filters.min_even'), tooltip: t('filter.minEven.tooltip') },
    { key: 'max_even', label: t('filters.max_even'), tooltip: t('filter.maxEven.tooltip') },
    { key: 'min_odd', label: t('filters.min_odd'), tooltip: t('filter.minOdd.tooltip') },
    { key: 'max_odd', label: t('filters.max_odd'), tooltip: t('filter.maxOdd.tooltip') },
  ];

  const inputs: Map<typeof fields[number]['key'], HTMLInputElement> = new Map();

  const state = getState();
  for (const f of fields) {
    const { wrapper, input } = createNullableNumber(f.label, f.tooltip, state.pipeline.post_filters[f.key], (value) => {
      const newFilters = { ...getState().pipeline.post_filters, [f.key]: value };
      setPipeline({ post_filters: newFilters });
    });
    inputs.set(f.key, input);
    grid.appendChild(wrapper);
  }

  subscribe(() => {
    const filters = getState().pipeline.post_filters;
    for (const [key, input] of inputs) {
      const value = filters[key];
      const next = value === null ? '' : `${value}`;
      if (document.activeElement !== input && input.value !== next) {
        input.value = next;
      }
    }
  });

  body.appendChild(grid);
  container.appendChild(body);

  function toggle() {
    const isOpen = container.classList.toggle('expanded');
    body.style.maxHeight = isOpen ? '600px' : '0';
    chevron.style.transform = isOpen ? 'rotate(90deg)' : 'rotate(0deg)';
  }

  header.addEventListener('click', toggle);
  // Start collapsed.
  container.classList.remove('expanded');
  body.style.maxHeight = '0';
  chevron.style.transform = 'rotate(0deg)';

  return container;
}

function createNullableNumber(
  label: string,
  tooltip: string,
  value: number | null,
  onChange: (value: number | null) => void
): { wrapper: HTMLElement; input: HTMLInputElement } {
  const wrapper = document.createElement('div');
  wrapper.className = 'form-group';

  const labelRow = document.createElement('div');
  labelRow.className = 'param-label-row';

  const lbl = document.createElement('label');
  lbl.className = 'form-label';
  lbl.textContent = label;

  const helpBtn = document.createElement('button');
  helpBtn.className = 'param-help-btn';
  helpBtn.type = 'button';
  helpBtn.setAttribute('aria-label', `Trợ giúp cho ${label}`);
  helpBtn.innerHTML = '?';
  helpBtn.title = tooltip;

  const tip = document.createElement('div');
  tip.className = 'param-tooltip';
  tip.setAttribute('role', 'tooltip');
  const tipText = document.createElement('p');
  tipText.textContent = tooltip;
  tip.appendChild(tipText);

  labelRow.append(lbl, helpBtn, tip);

  const input = document.createElement('input');
  input.className = 'form-input';
  input.type = 'number';
  input.value = value === null ? '' : `${value}`;
  input.placeholder = t('filters.any');
  input.addEventListener('input', () => {
    const raw = input.value.trim();
    if (raw === '') {
      onChange(null);
    } else {
      const n = parseInt(raw, 10);
      onChange(Number.isNaN(n) ? null : n);
    }
  });

  wrapper.append(labelRow, input);
  return { wrapper, input };
}
