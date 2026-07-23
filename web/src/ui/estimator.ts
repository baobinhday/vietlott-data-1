import { apiClient, formatCurrency } from '../api.js';
import { t } from '../i18n.js';
import type { ProductInfo } from '../types.js';
import { getState, setState, setPipeline, setLoading, subscribe } from '../state.js';
import { syncProductTag } from './pipeline-builder.js';
import { strategyCategory } from './group-editor.js';

let debounceTimer: ReturnType<typeof setTimeout> | null = null;

export function renderEstimator(): HTMLElement {
  const container = document.createElement('div');
  container.className = 'estimator-column';

  const card = document.createElement('div');
  card.className = 'card';
  container.appendChild(card);

  const header = document.createElement('div');
  header.className = 'panel-header';
  const title = document.createElement('h2');
  title.className = 'card-title';
  title.textContent = t('estimator.title');
  const productTag = document.createElement('span');
  productTag.className = 'product-tag';
  header.append(title, productTag);
  card.appendChild(header);

  const costSummary = document.createElement('div');
  costSummary.className = 'cost-summary';
  const costAmount = document.createElement('span');
  costAmount.className = 'amount';
  const costLabel = document.createElement('span');
  costLabel.className = 'label';
  costSummary.append(costAmount, costLabel);
  card.appendChild(costSummary);

  const ticketCountGroup = document.createElement('div');
  ticketCountGroup.className = 'form-group';
  const ticketCountLabel = document.createElement('label');
  ticketCountLabel.className = 'form-label';
  ticketCountLabel.textContent = t('estimator.ticketsToGenerate');
  const ticketCountInput = document.createElement('input');
  ticketCountInput.className = 'form-input';
  ticketCountInput.type = 'number';
  ticketCountInput.min = '1';
  ticketCountInput.max = '50';
  ticketCountInput.value = `${getState().pipeline.ticket_count}`;
  ticketCountInput.addEventListener('input', () => {
    const n = parseInt(ticketCountInput.value, 10);
    setPipeline({ ticket_count: Number.isNaN(n) ? 1 : Math.max(1, Math.min(50, n)) });
  });
  ticketCountGroup.append(ticketCountLabel, ticketCountInput);
  card.appendChild(ticketCountGroup);

  const detail = document.createElement('p');
  detail.className = 'hint';
  card.appendChild(detail);

  const generateBtn = document.createElement('button');
  generateBtn.className = 'btn btn-primary btn-block';
  generateBtn.style.marginTop = '16px';
  generateBtn.innerHTML = t('estimator.generate');
  card.appendChild(generateBtn);

  const resultSection = document.createElement('div');
  resultSection.className = 'generate-result fade-in';
  resultSection.style.marginTop = '20px';
  card.appendChild(resultSection);

  generateBtn.addEventListener('click', handleGenerate);

  function updateEstimate() {
    const state = getState();
    const product = state.products.find((p) => p.name === state.pipeline.product) as ProductInfo | undefined;
    const price = product?.ticket_price || 0;
    const totalCost = price * state.pipeline.ticket_count;
    const totalPicks = state.pipeline.groups.reduce((sum, g) => sum + g.pick_count, 0);

    costAmount.textContent = formatCurrency(totalCost);
    costLabel.textContent = t('estimator.costLabel', { count: state.pipeline.ticket_count, price: formatCurrency(price) });
    detail.textContent = t('estimator.detail', { groups: state.pipeline.groups.length, picks: totalPicks });

    syncProductTag(productTag);

    if (ticketCountInput.value !== `${state.pipeline.ticket_count}`) {
      ticketCountInput.value = `${state.pipeline.ticket_count}`;
    }
  }

  function update() {
    const state = getState();

    if (debounceTimer) clearTimeout(debounceTimer);
    debounceTimer = setTimeout(() => {
      if (!container.isConnected) return;
      updateEstimate();
    }, 200);

    if (state.loading.generate) {
      generateBtn.disabled = true;
      generateBtn.innerHTML = t('estimator.generating');
    } else {
      generateBtn.disabled = false;
      generateBtn.innerHTML = t('estimator.generate');
    }

    if (state.generateResult) {
      renderGenerateResult(resultSection, state.generateResult);
    } else {
      resultSection.innerHTML = '';
    }
  }

  updateEstimate();
  update();
  subscribe(() => {
    if (!container.isConnected) return;
    update();
  });
  return container;
}

function renderGenerateResult(container: HTMLElement, result: Awaited<ReturnType<typeof apiClient.generate>>): void {
  container.innerHTML = '';

  const header = document.createElement('div');
  header.className = 'ticket-list-header';
  const title = document.createElement('h3');
  title.textContent = t('estimator.generatedTickets', { count: result.tickets.length });
  const meta = document.createElement('span');
  meta.className = 'small';
  meta.textContent = result.target_date;
  meta.style.color = 'var(--text-secondary)';
  header.append(title, meta);
  container.appendChild(header);

  const groups = getState().pipeline.groups;
  const list = document.createElement('div');
  list.className = 'ticket-list';
  for (const ticket of result.tickets) {
    list.appendChild(renderTicketPill(ticket, groups));
  }
  container.appendChild(list);

  const legend = renderTicketLegend(groups);
  if (legend) {
    container.appendChild(legend);
  }

  const cost = document.createElement('p');
  cost.className = 'hint';
  cost.style.marginTop = '12px';
  cost.textContent = t('estimator.totalCost', { cost: formatCurrency(result.total_cost_vnd) });
  container.appendChild(cost);
}

export function renderTicketPill(ticket: number[], groups?: { strategies: { strategy: string }[]; name: string; pick_count: number }[], actual?: number[]): HTMLElement {
  const pill = document.createElement('div');
  pill.className = 'ticket-pill';

  const segmentMap = buildSegmentMap(ticket.length, groups);

  for (let i = 0; i < ticket.length; i++) {
    const n = ticket[i];
    const span = document.createElement('span');
    span.className = 'ticket-number';
    span.textContent = `${n}`;
    if (actual?.includes(n)) {
      span.classList.add('special');
    } else if (segmentMap[i]) {
      span.dataset.category = segmentMap[i];
    }
    pill.appendChild(span);
  }
  return pill;
}

function buildSegmentMap(
  ticketLength: number,
  groups?: { strategies: { strategy: string }[]; name: string; pick_count: number }[]
): string[] {
  const map: string[] = new Array(ticketLength).fill('');
  if (!groups || groups.length === 0) return map;

  const totalPick = groups.reduce((sum, g) => sum + g.pick_count, 0);
  if (totalPick !== ticketLength) return map;

  let offset = 0;
  for (const g of groups) {
    const category = strategyCategory(g.strategies[0]?.strategy || 'random');
    for (let i = 0; i < g.pick_count; i++) {
      if (offset + i < ticketLength) {
        map[offset + i] = category;
      }
    }
    offset += g.pick_count;
  }
  return map;
}

function renderTicketLegend(groups?: { strategies: { strategy: string }[]; name: string }[]): HTMLElement | null {
  if (!groups || groups.length === 0) return null;
  const legend = document.createElement('div');
  legend.className = 'ticket-legend';
  for (const g of groups) {
    const item = document.createElement('span');
    item.className = 'ticket-legend-item';
    const dot = document.createElement('span');
    dot.className = 'ticket-legend-dot';
    dot.dataset.category = strategyCategory(g.strategies[0]?.strategy || 'random');
    item.append(dot, document.createTextNode(g.name));
    legend.appendChild(item);
  }
  return legend;
}


async function handleGenerate() {
  const state = getState();
  setLoading('generate', true);
  setState({ error: null });
  try {
    const result = await apiClient.generate(state.pipeline);
    setState({ generateResult: result });
  } catch (err) {
    setState({ error: err instanceof Error ? err.message : t('estimator.generateFailed') });
  } finally {
    setLoading('generate', false);
  }
}

