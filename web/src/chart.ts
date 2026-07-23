export interface BarDatum {
  label: string;
  value: number;
}

export interface LinePoint {
  x: number;
  y: number;
}

export interface LineChartOptions {
  yBaseline?: number;
  color?: string;
  fill?: boolean;
}

function createSvgEl<K extends keyof SVGElementTagNameMap>(tag: K): SVGElementTagNameMap[K] {
  return document.createElementNS('http://www.w3.org/2000/svg', tag);
}

function getTextColor(): string {
  return getComputedStyle(document.body).getPropertyValue('--text-secondary').trim() || '#94a3b8';
}

function getAccentColor(): string {
  return getComputedStyle(document.body).getPropertyValue('--accent').trim() || '#6366f1';
}

function getDangerColor(): string {
  return getComputedStyle(document.body).getPropertyValue('--danger').trim() || '#ef4444';
}

function getSuccessColor(): string {
  return getComputedStyle(document.body).getPropertyValue('--success').trim() || '#22c55e';
}

export function barChart(svg: SVGSVGElement, data: BarDatum[]): void {
  svg.innerHTML = '';
  const width = svg.clientWidth || 320;
  const height = svg.clientHeight || 240;
  const padding = { top: 24, right: 24, bottom: 40, left: 48 };
  const chartWidth = width - padding.left - padding.right;
  const chartHeight = height - padding.top - padding.bottom;

  const maxValue = Math.max(1, ...data.map((d) => d.value));
  const textColor = getTextColor();

  const barWidth = Math.max(12, chartWidth / data.length - 12);
  const barSpacing = (chartWidth - barWidth * data.length) / Math.max(1, data.length - 1);

  for (let i = 0; i <= 4; i++) {
    const y = padding.top + chartHeight - (chartHeight / 4) * i;
    const line = createSvgEl('line');
    line.setAttribute('x1', `${padding.left}`);
    line.setAttribute('x2', `${width - padding.right}`);
    line.setAttribute('y1', `${y}`);
    line.setAttribute('y2', `${y}`);
    line.setAttribute('stroke', 'currentColor');
    line.setAttribute('stroke-opacity', '0.15');
    svg.appendChild(line);

    const label = createSvgEl('text');
    label.setAttribute('x', `${padding.left - 8}`);
    label.setAttribute('y', `${y + 4}`);
    label.setAttribute('text-anchor', 'end');
    label.setAttribute('fill', textColor);
    label.setAttribute('font-size', '10');
    label.textContent = `${Math.round((maxValue / 4) * i)}`;
    svg.appendChild(label);
  }

  data.forEach((d, i) => {
    const barHeight = (d.value / maxValue) * chartHeight;
    const x = padding.left + i * (barWidth + barSpacing);
    const y = padding.top + chartHeight - barHeight;

    const rect = createSvgEl('rect');
    rect.setAttribute('x', `${x}`);
    rect.setAttribute('y', `${y}`);
    rect.setAttribute('width', `${barWidth}`);
    rect.setAttribute('height', `${barHeight}`);
    rect.setAttribute('rx', '4');
    rect.setAttribute('fill', getAccentColor());
    rect.setAttribute('opacity', '0.85');
    svg.appendChild(rect);

    const label = createSvgEl('text');
    label.setAttribute('x', `${x + barWidth / 2}`);
    label.setAttribute('y', `${padding.top + chartHeight + 18}`);
    label.setAttribute('text-anchor', 'middle');
    label.setAttribute('fill', textColor);
    label.setAttribute('font-size', '10');
    label.setAttribute('font-weight', '600');
    label.textContent = d.label;
    svg.appendChild(label);

    if (d.value > 0) {
      const value = createSvgEl('text');
      value.setAttribute('x', `${x + barWidth / 2}`);
      value.setAttribute('y', `${y - 6}`);
      value.setAttribute('text-anchor', 'middle');
      value.setAttribute('fill', textColor);
      value.setAttribute('font-size', '10');
      value.setAttribute('font-weight', '600');
      value.textContent = `${d.value}`;
      svg.appendChild(value);
    }
  });
}

export function lineChart(
  svg: SVGSVGElement,
  points: LinePoint[],
  options: LineChartOptions = {}
): void {
  svg.innerHTML = '';
  const width = svg.clientWidth || 320;
  const height = svg.clientHeight || 240;
  const padding = { top: 24, right: 24, bottom: 32, left: 48 };
  const chartWidth = width - padding.left - padding.right;
  const chartHeight = height - padding.top - padding.bottom;

  if (points.length < 2) {
    const text = createSvgEl('text');
    text.setAttribute('x', `${width / 2}`);
    text.setAttribute('y', `${height / 2}`);
    text.setAttribute('text-anchor', 'middle');
    text.setAttribute('fill', getTextColor());
    text.setAttribute('font-size', '12');
    text.textContent = 'Not enough data';
    svg.appendChild(text);
    return;
  }

  const values = points.map((p) => p.y);
  const minY = Math.min(...values, options.yBaseline ?? 0);
  const maxY = Math.max(...values, options.yBaseline ?? 0);
  const range = Math.max(1, maxY - minY);

  const textColor = getTextColor();
  const strokeColor = options.color ?? (values[values.length - 1] >= 0 ? getSuccessColor() : getDangerColor());

  const xAt = (i: number) => padding.left + (i / (points.length - 1)) * chartWidth;
  const yAt = (v: number) => padding.top + chartHeight - ((v - minY) / range) * chartHeight;

  for (let i = 0; i <= 4; i++) {
    const y = padding.top + chartHeight - (chartHeight / 4) * i;
    const line = createSvgEl('line');
    line.setAttribute('x1', `${padding.left}`);
    line.setAttribute('x2', `${width - padding.right}`);
    line.setAttribute('y1', `${y}`);
    line.setAttribute('y2', `${y}`);
    line.setAttribute('stroke', 'currentColor');
    line.setAttribute('stroke-opacity', '0.15');
    svg.appendChild(line);

    const label = createSvgEl('text');
    label.setAttribute('x', `${padding.left - 8}`);
    label.setAttribute('y', `${y + 4}`);
    label.setAttribute('text-anchor', 'end');
    label.setAttribute('fill', textColor);
    label.setAttribute('font-size', '10');
    label.textContent = `${Math.round(minY + (range / 4) * i).toLocaleString('en-US')}`;
    svg.appendChild(label);
  }

  if (options.yBaseline !== undefined && options.yBaseline >= minY && options.yBaseline <= maxY) {
    const baselineY = yAt(options.yBaseline);
    const baseline = createSvgEl('line');
    baseline.setAttribute('x1', `${padding.left}`);
    baseline.setAttribute('x2', `${width - padding.right}`);
    baseline.setAttribute('y1', `${baselineY}`);
    baseline.setAttribute('y2', `${baselineY}`);
    baseline.setAttribute('stroke', textColor);
    baseline.setAttribute('stroke-opacity', '0.35');
    baseline.setAttribute('stroke-dasharray', '4 4');
    svg.appendChild(baseline);
  }

  const pathD = points
    .map((p, i) => `${i === 0 ? 'M' : 'L'} ${xAt(i)} ${yAt(p.y)}`)
    .join(' ');

  if (options.fill) {
    const baselineY = yAt(Math.max(minY, options.yBaseline ?? minY));
    const areaD = `${pathD} L ${xAt(points.length - 1)} ${baselineY} L ${xAt(0)} ${baselineY} Z`;
    const areaId = `line-fill-${Math.random().toString(36).slice(2, 9)}`;
    const defs = createSvgEl('defs');
    const gradient = createSvgEl('linearGradient');
    gradient.setAttribute('id', areaId);
    gradient.setAttribute('x1', '0');
    gradient.setAttribute('y1', '0');
    gradient.setAttribute('x2', '0');
    gradient.setAttribute('y2', '1');
    const stop1 = createSvgEl('stop');
    stop1.setAttribute('offset', '0%');
    stop1.setAttribute('stop-color', strokeColor);
    stop1.setAttribute('stop-opacity', '0.35');
    const stop2 = createSvgEl('stop');
    stop2.setAttribute('offset', '100%');
    stop2.setAttribute('stop-color', strokeColor);
    stop2.setAttribute('stop-opacity', '0.02');
    gradient.append(stop1, stop2);
    defs.appendChild(gradient);
    svg.appendChild(defs);

    const area = createSvgEl('path');
    area.setAttribute('d', areaD);
    area.setAttribute('fill', `url(#${areaId})`);
    area.setAttribute('stroke', 'none');
    svg.appendChild(area);
  }

  const path = createSvgEl('path');
  path.setAttribute('d', pathD);
  path.setAttribute('fill', 'none');
  path.setAttribute('stroke', strokeColor);
  path.setAttribute('stroke-width', '2.5');
  path.setAttribute('stroke-linecap', 'round');
  path.setAttribute('stroke-linejoin', 'round');
  svg.appendChild(path);

  points.forEach((p, i) => {
    const cx = xAt(i);
    const cy = yAt(p.y);
    const circle = createSvgEl('circle');
    circle.setAttribute('cx', `${cx}`);
    circle.setAttribute('cy', `${cy}`);
    circle.setAttribute('r', '3');
    circle.setAttribute('fill', strokeColor);
    circle.setAttribute('stroke', 'var(--bg-elevated)');
    circle.setAttribute('stroke-width', '2');
    svg.appendChild(circle);
  });
}
