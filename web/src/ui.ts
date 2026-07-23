export type ElementAttrs = Record<string, string | number | boolean | undefined>;

export function el<K extends keyof HTMLElementTagNameMap>(
  tag: K,
  attrs?: ElementAttrs,
  children?: (Node | string | null | undefined)[]
): HTMLElementTagNameMap[K] {
  const element = document.createElement(tag);
  if (attrs) {
    for (const [key, value] of Object.entries(attrs)) {
      if (value === undefined || value === null || value === false) continue;
      if (key === 'className' || key === 'class') {
        element.setAttribute('class', String(value));
      } else if (key.startsWith('data-')) {
        element.setAttribute(key, String(value));
      } else if (key === 'textContent') {
        element.textContent = String(value);
      } else if (key === 'innerHTML') {
        element.innerHTML = String(value);
      } else if (key in element && !(key === 'value' && typeof value === 'boolean')) {
        try {
          (element as Record<string, unknown>)[key] = value;
        } catch {
          element.setAttribute(key, String(value));
        }
      } else {
        element.setAttribute(key, String(value));
      }
    }
  }
  if (children) {
    for (const child of children) {
      if (child === null || child === undefined) continue;
      element.append(child);
    }
  }
  return element;
}

export function clear(node: Node): void {
  while (node.firstChild) {
    node.removeChild(node.firstChild);
  }
}

export function on<K extends keyof HTMLElementEventMap>(
  node: EventTarget,
  event: K,
  fn: (event: HTMLElementEventMap[K]) => void
): () => void {
  node.addEventListener(event, fn as EventListener);
  return () => node.removeEventListener(event, fn as EventListener);
}

