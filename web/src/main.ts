import { apiClient, type ProductInfo } from './api.js';
import { t } from './i18n.js';
import {
  getState,
  setState,
  subscribe,
  initTheme,
  toggleTheme,
  setError,
  resetPipeline,
} from './state.js';
import { renderPipelineBuilder } from './ui/pipeline-builder.js';
import { renderFilterEditor } from './ui/filter-editor.js';
import { renderEstimator } from './ui/estimator.js';
import { renderBacktestPanel } from './ui/backtest.js';
import { renderOnboarding } from './ui/onboarding.js';
import { renderHelpModal } from './ui/help-modal.js';
import './styles.css';
import './ui/theme.css';

const DESKTOP_BREAKPOINT = 1024;

async function init(): Promise<void> {
  initTheme();

  const app = document.getElementById('app');
  if (!app) throw new Error('Missing #app root');

  const headerTabs = document.createElement('div');
  headerTabs.className = 'header-tabs';
  app.appendChild(renderHeader(headerTabs));

  const pipelineColumn = document.createElement('aside');
  pipelineColumn.className = 'pipeline-column';
  pipelineColumn.appendChild(renderOnboarding());
  pipelineColumn.appendChild(renderPipelineBuilder());
  pipelineColumn.appendChild(renderFilterEditor());

  const generateSection = renderSection('generate', t('tabs.generate'), () => renderEstimator());
  generateSection.classList.add('content-section', 'generate-section');

  const backtestSection = renderSection('backtest', t('tabs.backtest'), () => renderBacktestPanel());
  backtestSection.classList.add('content-section', 'backtest-section');

  const tabButtons: Record<string, HTMLButtonElement> = {};
  for (const tab of ['generate', 'backtest']) {
    const btn = document.createElement('button');
    btn.className = 'tab-btn';
    btn.type = 'button';
    btn.textContent = t(`tabs.${tab}`);
    btn.dataset.tab = tab;
    btn.addEventListener('click', () => switchTab(tab));
    tabButtons[tab] = btn;
    headerTabs.appendChild(btn);
  }

  const contentColumn = document.createElement('main');
  contentColumn.className = 'content-column';
  contentColumn.appendChild(generateSection);
  contentColumn.appendChild(backtestSection);

  const body = document.createElement('div');
  body.className = 'app-body';
  body.appendChild(pipelineColumn);
  body.appendChild(contentColumn);
  app.appendChild(body);

  function switchTab(tab: string) {
    const isDesktop = window.innerWidth >= DESKTOP_BREAKPOINT;

    for (const [key, btn] of Object.entries(tabButtons)) {
      btn.classList.toggle('active', key === tab);
    }

    if (isDesktop) {
      pipelineColumn.style.display = '';
      contentColumn.style.display = '';
      const targetContentTab = tab === 'pipeline' ? (generateSection.classList.contains('active') ? 'generate' : 'backtest') : tab;
      generateSection.classList.toggle('active', targetContentTab === 'generate');
      backtestSection.classList.toggle('active', targetContentTab === 'backtest');
    } else {
      if (tab === 'pipeline') {
        pipelineColumn.style.display = 'block';
        contentColumn.style.display = 'none';
      } else {
        pipelineColumn.style.display = 'none';
        contentColumn.style.display = 'block';
        generateSection.classList.toggle('active', tab === 'generate');
        backtestSection.classList.toggle('active', tab === 'backtest');
      }
    }
  }

  function handleResize() {
    const isDesktop = window.innerWidth >= DESKTOP_BREAKPOINT;
    if (isDesktop) {
      pipelineColumn.style.display = '';
      contentColumn.style.display = '';
      const activeTab = document.querySelector('.tab-btn.active')?.getAttribute('data-tab') || 'generate';
      switchTab(activeTab === 'pipeline' ? 'generate' : activeTab);
    } else {
      const activeTab = document.querySelector('.tab-btn.active')?.getAttribute('data-tab') || 'pipeline';
      switchTab(activeTab);
    }
  }

  switchTab('generate');
  handleResize();
  window.addEventListener('resize', handleResize);

  const defaultProducts: ProductInfo[] = [
    { name: 'power_655', display_name: 'Power 6/55', min: 1, max: 55, size_output: 6, has_special: false, ticket_price: 10000 },
    { name: 'power_645', display_name: 'Power 6/45', min: 1, max: 45, size_output: 6, has_special: false, ticket_price: 10000 },
    { name: 'power_535', display_name: 'Power 5/35', min: 1, max: 35, size_output: 5, has_special: false, ticket_price: 10000 },
    { name: 'keno', display_name: 'Keno', min: 1, max: 80, size_output: 20, has_special: false, ticket_price: 10000 },
    { name: '3d', display_name: '3D', min: 0, max: 9, size_output: 3, has_special: false, ticket_price: 10000 },
    { name: '3d_pro', display_name: '3D Pro', min: 0, max: 9, size_output: 3, has_special: false, ticket_price: 10000 },
    { name: 'bingo18', display_name: 'Bingo 18', min: 1, max: 18, size_output: 8, has_special: false, ticket_price: 10000 },
  ];

  try {
    const [products, strategies] = await Promise.all([
      apiClient.products(),
      apiClient.strategies(),
    ]);

    const productMap = new Map(defaultProducts.map((p) => [p.name, p]));
    const enrichedProducts = await Promise.all(
      products.map(async (name) => {
        try {
          return await apiClient.product(name);
        } catch {
          return productMap.get(name) || {
            name,
            min: 1,
            max: 55,
            size_output: 6,
            has_special: false,
            ticket_price: 10000,
          };
        }
      })
    );

    setState({ products: enrichedProducts, strategies });
  } catch (err) {
    setState({ products: defaultProducts, strategies: [] });
    setError(err instanceof Error ? err.message : t('status.loadFailed'));
  }

  subscribe(() => {
    const state = getState();
    renderError(state.error);
  });
}

function renderHeader(tabsContainer?: HTMLElement): HTMLElement {
  const header = document.createElement('header');
  header.className = 'app-header';

  const brand = document.createElement('div');
  brand.className = 'header-brand';
  brand.innerHTML = `<span class="brand-dot"></span><h1>${t('app.title')}</h1>`;

  const actions = document.createElement('div');
  actions.className = 'header-actions';

  const helpBtn = document.createElement('button');
  helpBtn.className = 'icon-btn';
  helpBtn.title = t('header.help');
  helpBtn.innerHTML = '?';
  helpBtn.addEventListener('click', () => {
    if (!document.querySelector('.help-overlay')) {
      document.body.appendChild(renderHelpModal());
    }
  });

  const resetBtn = document.createElement('button');
  resetBtn.className = 'icon-btn';
  resetBtn.title = t('header.reset');
  resetBtn.innerHTML = '↺';
  resetBtn.addEventListener('click', () => {
    if (confirm(t('header.resetConfirm'))) {
      resetPipeline();
    }
  });

  const themeBtn = document.createElement('button');
  themeBtn.className = 'theme-toggle';
  themeBtn.innerHTML = getState().theme === 'dark' ? '🌙' : '☀️';
  themeBtn.title = t('header.theme');
  themeBtn.addEventListener('click', () => {
    toggleTheme();
    themeBtn.innerHTML = getState().theme === 'dark' ? '🌙' : '☀️';
  });

  actions.append(helpBtn, resetBtn, themeBtn);
  header.append(brand);
  if (tabsContainer) header.appendChild(tabsContainer);
  header.append(actions);
  return header;
}

function renderSection(name: string, title: string, renderBody: () => HTMLElement): HTMLElement {
  const section = document.createElement('section');
  section.className = 'section';
  section.dataset.section = name;

  const header = document.createElement('div');
  header.className = 'section-header';
  const titleEl = document.createElement('h2');
  titleEl.className = 'section-title';
  titleEl.textContent = title;
  const chevron = document.createElement('span');
  chevron.className = 'section-chevron';
  chevron.innerHTML = '›';
  header.append(titleEl, chevron);
  section.appendChild(header);

  const body = document.createElement('div');
  body.className = 'section-body';
  body.appendChild(renderBody());
  section.appendChild(body);

  return section;
}

let errorToast: HTMLElement | null = null;

function renderError(message: string | null): void {
  if (!message) {
    errorToast?.remove();
    errorToast = null;
    return;
  }
  if (!errorToast) {
    errorToast = document.createElement('div');
    errorToast.className = 'error-toast fade-in';
    const close = document.createElement('button');
    close.textContent = '✕';
    close.addEventListener('click', () => setError(null));
    errorToast.appendChild(close);
    document.body.appendChild(errorToast);
  }
  const closeBtn = errorToast.querySelector('button');
  errorToast.innerHTML = '';
  if (closeBtn) errorToast.appendChild(closeBtn);
  errorToast.appendChild(document.createTextNode(message));
}

init().catch((err) => {
  console.error('Bootstrap failed', err);
  const app = document.getElementById('app');
  if (app) {
    app.innerHTML = `<div class="empty-state"><h2>${t('error.startFailed')}</h2><p>${err.message}</p></div>`;
  }
});
