import { apiClient, formatCurrency, formatNumber, formatPercent } from '../api.js';
import { t } from '../i18n.js';
import { getState, setBacktestTicketCount, setLoading, setState, subscribe } from '../state.js';
import { barChart, lineChart } from '../chart.js';
import type { PerDraw } from '../types.js';

export function renderBacktestPanel(): HTMLElement {
  const container = document.createElement('div');
  container.className = 'backtest-column';

  const card = document.createElement('div');
  card.className = 'card';
  container.appendChild(card);

  const header = document.createElement('div');
  header.className = 'panel-header';
  const title = document.createElement('h2');
  title.className = 'card-title';
  title.textContent = t('backtest.title');
  header.appendChild(title);
  card.appendChild(header);

  const fromWrapper = createDateInput(t('backtest.dateFrom'));
  const toWrapper = createDateInput(t('backtest.dateTo'));

  const ticketCountWrapper = document.createElement('div');
  ticketCountWrapper.className = 'form-group';
  const ticketCountLabel = document.createElement('label');
  ticketCountLabel.className = 'form-label';
  ticketCountLabel.textContent = t('backtest.ticketsPerDraw');
  const ticketCountInput = document.createElement('input');
  ticketCountInput.className = 'form-input';
  ticketCountInput.type = 'number';
  ticketCountInput.min = '1';
  ticketCountInput.max = '50';
  ticketCountInput.value = `${getState().backtestTicketCount}`;
  ticketCountInput.addEventListener('input', () => {
    const raw = parseInt(ticketCountInput.value, 10);
    const n = Number.isNaN(raw) ? 1 : Math.max(1, Math.min(50, raw));
    setBacktestTicketCount(n);
  });
  ticketCountWrapper.append(ticketCountLabel, ticketCountInput);

  const ticketHelp = document.createElement('p');
  ticketHelp.className = 'hint';
  ticketHelp.textContent = t('backtest.ticketsPerDrawHelp');

  const quickDates = document.createElement('div');
  quickDates.className = 'quick-date-bar';
  const quickOptions = [
    { label: t('backtest.last7'), days: 7 },
    { label: t('backtest.last30'), days: 30 },
    { label: t('backtest.last90'), days: 90 },
    { label: t('backtest.last365'), days: 365 },
    { label: t('backtest.ytd'), mode: 'ytd' as const },
  ];
  const quickButtons: HTMLButtonElement[] = [];

  function applyQuickRange(days: number | 'ytd') {
    const today = new Date();
    let from: Date;
    if (days === 'ytd') {
      from = new Date(today.getFullYear(), 0, 1);
    } else {
      from = new Date(today);
      from.setDate(today.getDate() - days);
    }
    const fromInput = fromWrapper.querySelector('input') as HTMLInputElement;
    const toInput = toWrapper.querySelector('input') as HTMLInputElement;
    fromInput.value = formatDateInput(from);
    toInput.value = formatDateInput(today);

    quickButtons.forEach((btn) => btn.classList.remove('active'));
  }

  for (const opt of quickOptions) {
    const btn = document.createElement('button');
    btn.className = 'btn btn-sm btn-secondary quick-date-btn';
    btn.type = 'button';
    btn.textContent = opt.label;
    btn.addEventListener('click', () => {
      applyQuickRange(opt.mode || opt.days!);
      quickButtons.forEach((b) => b.classList.remove('active'));
      btn.classList.add('active');
    });
    quickButtons.push(btn);
    quickDates.appendChild(btn);
  }

  const controls = document.createElement('div');
  controls.className = 'form-row backtest-controls';
  controls.append(fromWrapper, toWrapper, ticketCountWrapper);
  card.appendChild(controls);

  card.appendChild(quickDates);
  card.appendChild(ticketHelp);

  const runBtn = document.createElement('button');
  runBtn.className = 'btn btn-primary btn-block';
  runBtn.style.marginTop = '16px';
  runBtn.textContent = t('backtest.run');
  card.appendChild(runBtn);

  // Default to last 365 days once the component is mounted.
  const last365Label = t('backtest.last365');
  requestAnimationFrame(() => {
    applyQuickRange(365);
    const defaultBtn = quickButtons.find((b) => b.textContent === last365Label);
    defaultBtn?.classList.add('active');
  });

  const resultsContainer = document.createElement('div');
  resultsContainer.className = 'backtest-result';
  card.appendChild(resultsContainer);

  runBtn.addEventListener('click', async () => {
    const state = getState();
    const dateFrom = fromWrapper.querySelector('input')!.value;
    const dateTo = toWrapper.querySelector('input')!.value;
    const ticketCount = state.backtestTicketCount;
    if (!dateFrom || !dateTo) {
      setState({ error: t('backtest.selectRange') });
      return;
    }
    setLoading('backtest', true);
    setState({ error: null });
    try {
      const result = await apiClient.backtest(state.pipeline, dateFrom, dateTo, ticketCount);
      setState({ backtestResult: result });
    } catch (err) {
      setState({ error: err instanceof Error ? err.message : t('backtest.failed') });
    } finally {
      setLoading('backtest', false);
    }
  });

  function render() {
    const state = getState();
    if (state.loading.backtest) {
      resultsContainer.innerHTML = '';
      const mask = document.createElement('div');
      mask.className = 'loading-mask';
      mask.innerHTML = t('backtest.running');
      resultsContainer.appendChild(mask);
      return;
    }
    if (state.backtestResult) {
      renderBacktestResults(resultsContainer, state.backtestResult);
    } else {
      resultsContainer.innerHTML = `<div class="empty-state"><div class="empty-state-icon">📈</div><p>${t('backtest.empty')}</p></div>`;
    }
  }

  render();
  subscribe(() => {
    if (!container.isConnected) return;
    if (document.activeElement !== ticketCountInput) {
      ticketCountInput.value = `${getState().backtestTicketCount}`;
    }
    render();
  });
  return container;
}


function createDateInput(label: string): HTMLElement {
  const wrapper = document.createElement('div');
  wrapper.className = 'form-group';
  const lbl = document.createElement('label');
  lbl.className = 'form-label';
  lbl.textContent = label;
  const input = document.createElement('input');
  input.className = 'form-input';
  input.type = 'date';
  wrapper.append(lbl, input);
  return wrapper;
}

function formatDateInput(d: Date): string {
  const year = d.getFullYear();
  const month = `${d.getMonth() + 1}`.padStart(2, '0');
  const day = `${d.getDate()}`.padStart(2, '0');
  return `${year}-${month}-${day}`;
}

function renderBacktestResults(container: HTMLElement, result: Awaited<ReturnType<typeof apiClient.backtest>>): void {
  container.innerHTML = '';

  const summary = document.createElement('div');
  summary.className = 'backtest-summary';

  const metrics = [
    { label: t('backtest.draws'), value: result.draws.toLocaleString('en-US') },
    { label: t('backtest.totalCost'), value: formatCurrency(result.total_cost_vnd) },
    { label: t('backtest.totalRevenue'), value: formatCurrency(result.total_revenue_vnd) },
    { label: t('backtest.netProfit'), value: formatCurrency(result.net_profit_vnd), highlight: result.net_profit_vnd >= 0 ? 'positive' : 'negative' },
  ];
  for (const m of metrics) {
    const card = document.createElement('div');
    card.className = `backtest-summary-card ${m.highlight || ''}`;
    card.innerHTML = `<div class="backtest-summary-label">${m.label}</div><div class="backtest-summary-value">${m.value}</div>`;
    summary.appendChild(card);
  }

  const roiCard = document.createElement('div');
  roiCard.className = `backtest-roi ${result.roi >= 0 ? 'positive' : 'negative'}`;
  roiCard.innerHTML = `<div class="backtest-roi-label">${t('backtest.roi')}</div><div class="backtest-roi-value">${formatPercent(result.roi)}</div>`;
  summary.appendChild(roiCard);
  container.appendChild(summary);

  const charts = document.createElement('div');
  charts.className = 'backtest-charts';

  const matchesChart = document.createElement('div');
  matchesChart.className = 'chart-card';
  const matchesTitle = document.createElement('div');
  matchesTitle.className = 'chart-title';
  matchesTitle.textContent = t('backtest.matchesDistribution');
  const matchesSvg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  const matchesContainer = document.createElement('div');
  matchesContainer.className = 'chart-container backtest-chart-sm';
  matchesContainer.appendChild(matchesSvg);
  matchesChart.append(matchesTitle, matchesContainer);

  const profitChart = document.createElement('div');
  profitChart.className = 'chart-card';
  const profitTitle = document.createElement('div');
  profitTitle.className = 'chart-title';
  profitTitle.textContent = t('backtest.cumulativeProfit');
  const profitSvg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  const profitContainer = document.createElement('div');
  profitContainer.className = 'chart-container backtest-chart-lg';
  profitContainer.appendChild(profitSvg);
  profitChart.append(profitTitle, profitContainer);

  charts.append(matchesChart, profitChart);
  container.appendChild(charts);

  const matchData = Object.entries(result.matches_distribution)
    .map(([k, v]) => ({ label: t('backtest.matchLabel', { count: k }), value: v }))
    .sort((a, b) => parseInt(a.label) - parseInt(b.label));
  const profitPoints = result.per_draw.map((d, i) => ({ x: i, y: d.cumulative_profit_vnd }));

  requestAnimationFrame(() => {
    barChart(matchesSvg, matchData);
    lineChart(profitSvg, profitPoints, {
      yBaseline: 0,
      fill: true,
      color: result.net_profit_vnd >= 0 ? 'var(--success)' : 'var(--danger)',
    });
  });

  const tableCard = document.createElement('div');
  tableCard.className = 'card backtest-table-card';
  const tableHeader = document.createElement('div');
  tableHeader.className = 'panel-header';
  const tableTitle = document.createElement('h2');
  tableTitle.className = 'card-title';
  tableTitle.textContent = t('backtest.perDrawTitle');
  tableHeader.appendChild(tableTitle);
  tableCard.appendChild(tableHeader);

  const width = window.innerWidth;
  const rowsPerPage = width >= 1920 ? result.per_draw.length : width >= 1440 ? 50 : 30;
  const totalRows = result.per_draw.length;
  const totalPages = Math.max(1, Math.ceil(totalRows / rowsPerPage));
  let currentPage = 1;

  const table = document.createElement('table');
  table.className = 'table backtest-table';

  const thead = document.createElement('thead');
  const headerRow = document.createElement('tr');
  const columns: { key: keyof PerDraw; label: string; sortable: boolean }[] = [
    { key: 'date', label: t('backtest.date'), sortable: true },
    { key: 'ticket', label: t('backtest.ticket'), sortable: false },
    { key: 'actual', label: t('backtest.actual'), sortable: false },
    { key: 'matches', label: t('backtest.matches'), sortable: true },
    { key: 'prize_vnd', label: t('backtest.prize'), sortable: true },
    { key: 'cumulative_profit_vnd', label: t('backtest.cumProfit'), sortable: true },
  ];

  let sortColumn: keyof PerDraw = 'date';
  let sortDirection: 'asc' | 'desc' = 'desc';
  const headerCells: { key: keyof PerDraw; arrow: HTMLElement; th: HTMLElement }[] = [];

  for (const col of columns) {
    const th = document.createElement('th');
    th.textContent = col.label;
    if (col.sortable) {
      th.classList.add('sortable');
      const arrow = document.createElement('span');
      arrow.className = 'sort-arrow';
      arrow.textContent = '';
      th.appendChild(arrow);
      headerCells.push({ key: col.key, arrow, th });
      th.addEventListener('click', () => {
        if (sortColumn === col.key) {
          sortDirection = sortDirection === 'desc' ? 'asc' : 'desc';
        } else {
          sortColumn = col.key;
          sortDirection = 'desc';
        }
        updateSortUI();
        renderPage(1);
      });
    }
    headerRow.appendChild(th);
  }
  thead.appendChild(headerRow);
  table.appendChild(thead);

  const tbody = document.createElement('tbody');
  table.appendChild(tbody);

  function updateSortUI() {
    for (const { key, arrow, th } of headerCells) {
      th.classList.toggle('sorted-asc', key === sortColumn && sortDirection === 'asc');
      th.classList.toggle('sorted-desc', key === sortColumn && sortDirection === 'desc');
      arrow.textContent = key === sortColumn ? (sortDirection === 'asc' ? '▲' : '▼') : '';
    }
  }

  function sortRows(rows: PerDraw[], column: keyof PerDraw, direction: 'asc' | 'desc'): PerDraw[] {
    return [...rows].sort((a, b) => {
      let cmp = 0;
      if (column === 'date') {
        cmp = a.date.localeCompare(b.date);
      } else {
        cmp = (a[column] as number) - (b[column] as number);
      }
      return direction === 'asc' ? cmp : -cmp;
    });
  }

  function formatTicketNumbers(ticket: number[], actual: number[]): string {
    const actualSet = new Set(actual);
    const numsHtml = ticket
      .map((num) => (actualSet.has(num) ? `<span class="matched-num">${num}</span>` : `${num}`))
      .join(', ');
    return `[${numsHtml}]`;
  }

  function renderTicketsCell(d: PerDraw): string {
    const tickets = d.tickets?.length ? d.tickets : [d.ticket];
    const actual = d.actual || [];
    const first = tickets[0];
    let html = `<code class="ticket-cell">${formatTicketNumbers(first, actual)}</code>`;
    if (tickets.length > 1) {
      const more = tickets.slice(1);
      html += `<div class="ticket-more">${t('backtest.moreTickets', { n: more.length })}</div>`;
      html += `<div class="ticket-list-inline">${more.map((t) => `<code class="ticket-cell">${formatTicketNumbers(t, actual)}</code>`).join('')}</div>`;
    }
    return html;
  }

  function renderPage(page: number) {
    currentPage = Math.max(1, Math.min(page, totalPages));
    tbody.innerHTML = '';
    const sortedRows = sortRows(result.per_draw, sortColumn, sortDirection);
    const start = (currentPage - 1) * rowsPerPage;
    const pageRows = sortedRows.slice(start, start + rowsPerPage);
    for (const d of pageRows) {
      const tr = document.createElement('tr');
      const prizeClass = d.prize_vnd > 0 ? 'positive' : 'muted';
      tr.innerHTML = `
        <td>${d.date}</td>
        <td class="ticket-col">${renderTicketsCell(d)}</td>
        <td class="actual-col">${d.actual.join(', ')}</td>
        <td class="highlight">${d.matches}</td>
        <td class="${prizeClass}">${formatCurrency(d.prize_vnd)}</td>
        <td class="${d.cumulative_profit_vnd >= 0 ? 'positive' : 'negative'}">${formatCurrency(d.cumulative_profit_vnd)}</td>
      `;
      tbody.appendChild(tr);
    }
    if (totalPages > 1) {
      pageInfo.textContent = t('backtest.pageInfo', { page: currentPage, total: totalPages });
      prevBtn.disabled = currentPage === 1;
      nextBtn.disabled = currentPage === totalPages;
      pagination.style.display = 'flex';
    } else {
      pagination.style.display = 'none';
    }
  }

  updateSortUI();

  const pagination = document.createElement('div');
  pagination.className = 'backtest-pagination';
  const prevBtn = document.createElement('button');
  prevBtn.className = 'btn btn-sm btn-secondary';
  prevBtn.textContent = t('backtest.prevPage');
  prevBtn.addEventListener('click', () => renderPage(currentPage - 1));
  const nextBtn = document.createElement('button');
  nextBtn.className = 'btn btn-sm btn-secondary';
  nextBtn.textContent = t('backtest.nextPage');
  nextBtn.addEventListener('click', () => renderPage(currentPage + 1));
  const pageInfo = document.createElement('span');
  pageInfo.className = 'backtest-page-info';
  pagination.append(prevBtn, pageInfo, nextBtn);

  const tableWrap = document.createElement('div');
  tableWrap.className = 'backtest-table-wrap';
  tableWrap.appendChild(table);
  tableCard.append(tableWrap, pagination);
  container.appendChild(tableCard);

  renderPage(1);
}
