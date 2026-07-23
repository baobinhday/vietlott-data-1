import { hasKey, t, tParamDescription, tSelectOption } from '../i18n.js';
import {
  getState,
  setGroup,
  removeGroup,
  moveGroup,
  addStepToGroup,
  removeStepFromGroup,
  reorderStepsInGroup,
  updateStep,
  updateStepParam,
} from '../state.js';
import type { GroupSpec, StrategyMetadata, StrategyParam, StrategyStep } from '../types.js';

export function renderGroupEditor(
  group: GroupSpec,
  index: number,
  strategies: StrategyMetadata[]
): HTMLElement {
  const container = document.createElement('div');
  container.className = 'group-card';
  container.dataset.index = `${index}`;
  container.dataset.category = groupCategory(group);
  container.draggable = true;

  const header = document.createElement('div');
  header.className = 'group-card-header';

  const dragHandle = document.createElement('span');
  dragHandle.className = 'drag-handle';
  dragHandle.innerHTML = '⋮⋮';
  dragHandle.title = t('builder.dragToReorder');
  dragHandle.dataset.handle = 'true';

  const nameInput = document.createElement('input');
  nameInput.className = 'group-title';
  nameInput.value = group.name;
  nameInput.placeholder = t('builder.groupNamePlaceholder');
  nameInput.addEventListener('change', () => {
    setGroup(index, { ...group, name: nameInput.value || `Nhóm ${index + 1}` });
  });

  const removeBtn = document.createElement('button');
  removeBtn.className = 'icon-btn';
  removeBtn.innerHTML = '×';
  removeBtn.title = t('builder.removeGroup');
  removeBtn.addEventListener('click', () => removeGroup(index));

  const actions = document.createElement('div');
  actions.className = 'group-actions';
  actions.appendChild(removeBtn);
  header.append(dragHandle, nameInput, actions);

  const chainTitle = document.createElement('div');
  chainTitle.className = 'form-label';
  chainTitle.style.marginBottom = '12px';
  chainTitle.textContent = t('group.steps');

  const chain = document.createElement('div');
  chain.className = 'strategy-chain';

  group.strategies.forEach((step, stepIndex) => {
    chain.appendChild(renderStepRow(group, index, step, stepIndex, strategies));
    if (stepIndex < group.strategies.length - 1) {
      const arrow = document.createElement('div');
      arrow.className = 'chain-arrow';
      arrow.textContent = '↓';
      arrow.title = t('group.stepTooltip');
      chain.appendChild(arrow);
    }
  });

  const addStepBtn = document.createElement('button');
  addStepBtn.className = 'btn btn-secondary btn-sm add-step-btn';
  addStepBtn.type = 'button';
  addStepBtn.textContent = t('group.addStep');
  addStepBtn.addEventListener('click', () => addStepToGroup(index));

  const outputSection = document.createElement('div');
  outputSection.className = 'group-output';

  const pickLabel = document.createElement('label');
  pickLabel.className = 'form-label';
  pickLabel.textContent = t('group.pickCount', { n: group.pick_count });

  const pickInput = document.createElement('input');
  pickInput.className = 'form-input';
  pickInput.type = 'number';
  pickInput.min = '1';
  pickInput.max = '20';
  pickInput.value = `${group.pick_count}`;
  pickInput.addEventListener('change', () => {
    let n = parseInt(pickInput.value, 10);
    if (Number.isNaN(n)) n = 1;
    n = Math.max(1, Math.min(20, n));
    setGroup(index, { ...group, pick_count: n });
  });

  const totalPicks = getState().pipeline.groups.reduce((sum, g) => sum + g.pick_count, 0);
  const helper = document.createElement('p');
  helper.className = 'hint';
  helper.textContent = t('group.pickCountHelper', { n: group.pick_count, total: totalPicks });

  outputSection.append(pickLabel, pickInput, helper);

  container.append(header, chainTitle, chain, addStepBtn, outputSection);

  container.addEventListener('dragstart', (e) => {
    if (e.target === dragHandle || dragHandle.contains(e.target as Node)) {
      container.classList.add('dragging');
      e.dataTransfer?.setData('text/plain', `${index}`);
      e.dataTransfer!.effectAllowed = 'move';
    } else {
      e.preventDefault();
    }
  });

  container.addEventListener('dragend', () => {
    container.classList.remove('dragging');
    document.querySelectorAll('.group-card').forEach((el) => el.classList.remove('drag-over'));
  });

  container.addEventListener('dragover', (e) => {
    e.preventDefault();
    e.dataTransfer!.dropEffect = 'move';
    container.classList.add('drag-over');
  });

  container.addEventListener('dragleave', () => container.classList.remove('drag-over'));

  container.addEventListener('drop', (e) => {
    e.preventDefault();
    const from = parseInt(e.dataTransfer?.getData('text/plain') || '-1', 10);
    if (from === -1 || from === index) return;
    moveGroup(from, index);
  });

  return container;
}

function renderStepRow(
  group: GroupSpec,
  groupIndex: number,
  step: StrategyStep,
  stepIndex: number,
  strategies: StrategyMetadata[]
): HTMLElement {
  const row = document.createElement('div');
  row.className = 'strategy-step-row';
  row.dataset.stepIndex = `${stepIndex}`;
  row.draggable = true;

  const stepDrag = document.createElement('span');
  stepDrag.className = 'step-drag-handle';
  stepDrag.innerHTML = '⋮⋮';
  stepDrag.title = t('builder.dragToReorder');

  const badge = document.createElement('span');
  badge.className = 'step-badge';
  badge.textContent = `${stepIndex + 1}`;

  const strategy = strategies.find((s) => s.key === step.strategy) || strategies[0];

  const select = document.createElement('select');
  select.className = 'form-select step-strategy-select';
  for (const s of strategies) {
    const option = document.createElement('option');
    option.value = s.key;
    option.textContent = s.label;
    if (s.key === step.strategy) option.selected = true;
    select.appendChild(option);
  }
  select.addEventListener('change', () => {
    const newStrategy = strategies.find((s) => s.key === select.value)!;
    const params: Record<string, unknown> = {};
    for (const p of newStrategy.params) {
      params[p.name] = p.default ?? null;
    }
    updateStep(groupIndex, stepIndex, { strategy: newStrategy.key, params });
  });

  const paramsToggle = document.createElement('button');
  paramsToggle.className = 'icon-btn params-toggle';
  paramsToggle.type = 'button';
  paramsToggle.title = t('group.expandParams');
  paramsToggle.textContent = '⚙';

  const poolSizeWrapper = document.createElement('div');
  poolSizeWrapper.className = 'step-pool-size';

  const poolInput = document.createElement('input');
  poolInput.className = 'form-input';
  poolInput.type = 'number';
  poolInput.min = '1';
  poolInput.max = '55';
  poolInput.value = step.pool_size === null || step.pool_size === undefined ? '' : `${step.pool_size}`;
  poolInput.placeholder = t('group.poolSizeAuto');
  poolInput.title = t('group.poolSizeTooltip');
  poolInput.addEventListener('change', () => {
    const n = parseInt(poolInput.value, 10);
    updateStep(groupIndex, stepIndex, { pool_size: Number.isNaN(n) ? null : n });
  });

  const poolHelpBtn = document.createElement('button');
  poolHelpBtn.className = 'param-help-btn';
  poolHelpBtn.type = 'button';
  poolHelpBtn.setAttribute('aria-label', 'Trợ giúp pool size');
  poolHelpBtn.innerHTML = '?';
  poolHelpBtn.title = t('group.poolSizeTooltip');

  const poolTooltip = document.createElement('div');
  poolTooltip.className = 'param-tooltip';
  poolTooltip.setAttribute('role', 'tooltip');
  const poolTooltipDesc = document.createElement('p');
  poolTooltipDesc.textContent = t('group.poolSizeTooltip');
  poolTooltip.appendChild(poolTooltipDesc);

  poolSizeWrapper.append(poolInput, poolHelpBtn, poolTooltip);

  const removeStepBtn = document.createElement('button');
  removeStepBtn.className = 'icon-btn';
  removeStepBtn.type = 'button';
  removeStepBtn.innerHTML = '×';
  removeStepBtn.title = t('group.removeStep');
  removeStepBtn.disabled = group.strategies.length <= 1;
  removeStepBtn.addEventListener('click', () => removeStepFromGroup(groupIndex, stepIndex));

  const topRow = document.createElement('div');
  topRow.className = 'step-top-row';
  topRow.append(stepDrag, badge, select, paramsToggle, poolSizeWrapper, removeStepBtn);
  row.appendChild(topRow);

  const paramsPanel = document.createElement('div');
  paramsPanel.className = 'step-params-panel';
  paramsPanel.style.display = 'none';
  if (strategy) {
    for (const param of strategy.params) {
      const control = createParamControl(param, step.params[param.name], (value) => {
        updateStepParam(groupIndex, stepIndex, param.name, value);
      });
      paramsPanel.appendChild(control);
    }
  }
  row.appendChild(paramsPanel);

  paramsToggle.addEventListener('click', () => {
    const isOpen = paramsPanel.style.display !== 'none';
    paramsPanel.style.display = isOpen ? 'none' : 'block';
    paramsToggle.title = isOpen ? t('group.expandParams') : t('group.collapseParams');
    paramsToggle.classList.toggle('active', !isOpen);
  });

  row.addEventListener('dragstart', (e) => {
    if (e.target === stepDrag || stepDrag.contains(e.target as Node)) {
      row.classList.add('dragging');
      e.dataTransfer?.setData('text/plain', `${stepIndex}`);
      e.dataTransfer!.effectAllowed = 'move';
      e.stopPropagation();
    } else {
      e.preventDefault();
    }
  });

  row.addEventListener('dragend', () => {
    row.classList.remove('dragging');
    document.querySelectorAll('.strategy-step-row').forEach((el) => el.classList.remove('drag-over'));
  });

  row.addEventListener('dragover', (e) => {
    e.preventDefault();
    e.dataTransfer!.dropEffect = 'move';
    row.classList.add('drag-over');
    e.stopPropagation();
  });

  row.addEventListener('dragleave', () => row.classList.remove('drag-over'));

  row.addEventListener('drop', (e) => {
    e.preventDefault();
    e.stopPropagation();
    const from = parseInt(e.dataTransfer?.getData('text/plain') || '-1', 10);
    if (from === -1 || from === stepIndex) return;
    reorderStepsInGroup(groupIndex, from, stepIndex);
  });

  return row;
}

function createParamControl(
  param: StrategyParam,
  value: unknown,
  onChange: (value: unknown) => void
): HTMLElement {
  const wrapper = document.createElement('div');
  wrapper.className = 'form-group';

  const labelRow = document.createElement('div');
  labelRow.className = 'param-label-row';

  const label = document.createElement('label');
  label.className = 'form-label';
  const paramLabelKey = `param.${param.name}`;
  label.textContent = hasKey(paramLabelKey) ? t(paramLabelKey) : param.name.replace(/_/g, ' ');

  const helpBtn = document.createElement('button');
  helpBtn.className = 'param-help-btn';
  helpBtn.type = 'button';
  helpBtn.setAttribute('aria-label', `Trợ giúp cho ${param.name}`);
  helpBtn.innerHTML = '?';
  helpBtn.title = tParamDescription(param.description || '');

  const tooltip = renderTooltip(param);
  labelRow.append(label, helpBtn, tooltip);

  if (param.type === 'select' && param.options) {
    const select = document.createElement('select');
    select.className = 'form-select';
    for (const opt of param.options) {
      const option = document.createElement('option');
      option.value = opt;
      option.textContent = tSelectOption(opt);
      if (opt === value) option.selected = true;
      select.appendChild(option);
    }
    select.addEventListener('change', () => onChange(select.value));
    wrapper.append(labelRow, select);
  } else if (param.type === 'boolean') {
    const checkbox = document.createElement('input');
    checkbox.type = 'checkbox';
    checkbox.checked = Boolean(value);
    checkbox.addEventListener('change', () => onChange(checkbox.checked));
    const row = document.createElement('label');
    row.style.display = 'flex';
    row.style.alignItems = 'center';
    row.style.gap = '8px';
    row.style.cursor = 'pointer';
    row.append(checkbox, document.createTextNode(tParamDescription(param.description || param.name)));
    wrapper.append(labelRow, row);
  } else {
    const input = document.createElement('input');
    input.className = 'form-input';
    if (param.type === 'date') {
      input.type = 'date';
    } else if (param.type === 'integer' || param.type === 'number') {
      input.type = 'number';
      if (param.min !== undefined) input.min = `${param.min}`;
      if (param.max !== undefined) input.max = `${param.max}`;
    } else {
      input.type = 'text';
    }
    input.value = value === null || value === undefined ? '' : `${value}`;
    input.addEventListener('change', () => {
      if (param.type === 'integer' || param.type === 'number') {
        const n = input.value === '' ? null : parseFloat(input.value);
        onChange(n);
      } else {
        onChange(input.value);
      }
    });
    wrapper.append(labelRow, input);
  }

  if (param.description && param.type !== 'boolean') {
    const hint = document.createElement('p');
    hint.className = 'hint';
    hint.textContent = tParamDescription(param.description);
    wrapper.appendChild(hint);
  }

  return wrapper;
}

function renderTooltip(param: StrategyParam): HTMLElement {
  const tooltip = document.createElement('div');
  tooltip.className = 'param-tooltip';
  tooltip.setAttribute('role', 'tooltip');

  const desc = document.createElement('p');
  desc.textContent = tParamDescription(param.description || t('param.noDescription'));
  tooltip.appendChild(desc);

  if (param.min !== undefined || param.max !== undefined) {
    const bounds = document.createElement('p');
    bounds.className = 'param-tooltip-bounds';
    bounds.textContent = t('param.bounds', {
      min: param.min ?? '-∞',
      max: param.max ?? '+∞',
    });
    tooltip.appendChild(bounds);
  }

  return tooltip;
}

function groupCategory(group: GroupSpec): string {
  const firstStep = group.strategies[0];
  return firstStep ? strategyCategory(firstStep.strategy) : 'random';
}

export function strategyCategory(strategyKey: string): string {
  const key = strategyKey.toLowerCase();
  if (key.includes('frequency')) return 'frequency';
  if (key.includes('markov')) return 'markov';
  if (key.includes('steiner')) return 'steiner';
  if (key.includes('hybrid')) return 'hybrid';
  if (key.includes('long') || key.includes('absence')) return 'long_absence';
  return 'random';
}

