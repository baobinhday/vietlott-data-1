import { t } from '../i18n.js';
import { getState, setPipeline, addGroup, subscribe } from '../state.js';
import type { GroupSpec } from '../types.js';
import { renderGroupEditor } from './group-editor.js';

function stepMetaFromCard(card: HTMLElement): string {
  const rows = Array.from(card.querySelectorAll('.strategy-step-row'));
  return rows
    .map((row) => {
      const select = row.querySelector('.step-strategy-select') as HTMLSelectElement | null;
      const input = row.querySelector('.step-pool-size input') as HTMLInputElement | null;
      const paramsInputs = Array.from(row.querySelectorAll('.step-params-panel input, .step-params-panel select')) as (HTMLInputElement | HTMLSelectElement)[];
      const paramsMeta = paramsInputs.map((i) => `${i.name || i.className}:${i.type === 'checkbox' ? (i as HTMLInputElement).checked : i.value}`).join(',');
      return `${select?.value ?? ''}:${input?.value ?? ''}:[${paramsMeta}]`;
    })
    .join('|');
}

function stepMetaFromState(group: GroupSpec): string {
  return group.strategies
    .map((s) => {
      const paramsStr = s.params ? JSON.stringify(s.params) : '';
      return `${s.strategy}:${s.pool_size ?? ''}:${paramsStr}`;
    })
    .join('|');
}

export function renderPipelineBuilder(): HTMLElement {
  const container = document.createElement('div');
  container.className = 'builder-column';

  const productCard = document.createElement('div');
  productCard.className = 'card';
  productCard.innerHTML = `<h2 class="card-title">${t('builder.product')}</h2>`;
  const productSelect = document.createElement('select');
  productSelect.className = 'form-select';
  productSelect.addEventListener('change', () => {
    setPipeline({ product: productSelect.value });
  });
  productCard.appendChild(productSelect);
  container.appendChild(productCard);

  const groupsCard = document.createElement('div');
  groupsCard.className = 'card';
  const groupsHeader = document.createElement('div');
  groupsHeader.className = 'panel-header';
  const groupsTitle = document.createElement('h2');
  groupsTitle.className = 'card-title';
  groupsTitle.textContent = t('builder.groups');
  groupsHeader.appendChild(groupsTitle);

  const addBtn = document.createElement('button');
  addBtn.className = 'btn btn-secondary btn-sm';
  addBtn.textContent = t('builder.addGroup');
  addBtn.addEventListener('click', () => addGroup());
  groupsHeader.appendChild(addBtn);
  groupsCard.appendChild(groupsHeader);

  const groupsList = document.createElement('div');
  groupsList.className = 'groups-list';
  groupsCard.appendChild(groupsList);
  container.appendChild(groupsCard);

  function render() {
    const state = getState();
    const strategies = state.strategies;
    productSelect.innerHTML = '';
    for (const p of state.products) {
      const option = document.createElement('option');
      option.value = p.name;
      option.textContent = p.display_name || p.name;
      if (p.name === state.pipeline.product) option.selected = true;
      productSelect.appendChild(option);
    }

    const currentCards = Array.from(groupsList.children) as HTMLElement[];
    const currentOrder = currentCards.map((c) => parseInt(c.dataset.index || '-1', 10));
    const desiredOrder = state.pipeline.groups.map((_, i) => i);
    const currentStepMeta = currentCards.map((c) => stepMetaFromCard(c));
    const desiredStepMeta = state.pipeline.groups.map((g) => stepMetaFromState(g));
    const needsRebuild =
      currentCards.length !== state.pipeline.groups.length ||
      !currentOrder.every((v, i) => v === desiredOrder[i]) ||
      !currentStepMeta.every((m, i) => m === desiredStepMeta[i]);

    if (needsRebuild) {
      groupsList.innerHTML = '';
      for (let i = 0; i < state.pipeline.groups.length; i++) {
        const groupEl = renderGroupEditor(state.pipeline.groups[i], i, strategies);
        groupsList.appendChild(groupEl);
      }
    }

  }

  render();
  subscribe(() => {
    const state = getState();
    const strategies = state.strategies;

    productSelect.innerHTML = '';
    for (const p of state.products) {
      const option = document.createElement('option');
      option.value = p.name;
      option.textContent = p.display_name || p.name;
      if (p.name === state.pipeline.product) option.selected = true;
      productSelect.appendChild(option);
    }

    const currentCards = Array.from(groupsList.children) as HTMLElement[];
    const currentOrder = currentCards.map((c) => parseInt(c.dataset.index || '-1', 10));
    const desiredOrder = state.pipeline.groups.map((_, i) => i);
    const currentStepMeta = currentCards.map((c) => stepMetaFromCard(c));
    const desiredStepMeta = state.pipeline.groups.map((g) => stepMetaFromState(g));
    const needsRebuild =
      currentCards.length !== state.pipeline.groups.length ||
      !currentOrder.every((v, i) => v === desiredOrder[i]) ||
      !currentStepMeta.every((m, i) => m === desiredStepMeta[i]);

    if (needsRebuild) {
      groupsList.innerHTML = '';
      for (let i = 0; i < state.pipeline.groups.length; i++) {
        const groupEl = renderGroupEditor(state.pipeline.groups[i], i, strategies);
        groupsList.appendChild(groupEl);
      }
    }
  });
  return container;
}

export function syncProductTag(tagEl: HTMLElement): void {
  const state = getState();
  const product = state.products.find((p) => p.name === state.pipeline.product);
  tagEl.className = `product-tag ${state.pipeline.product}`;
  tagEl.textContent = product?.display_name || state.pipeline.product;
}
