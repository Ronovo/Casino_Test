import { vi } from 'vitest';

export const CHIP_VALUES = { White: 1, Red: 5, Green: 25, Black: 100, Purple: 500, Orange: 1000 };

export function player(overrides = {}) {
  return {
    name: 'Lucky', difficulty: 'Medium', credits: 1000, broke: false,
    chips: { White: 25, Red: 10, Green: 5, Black: 3, Purple: 1, Orange: 0 }, ...overrides,
  };
}

/* A table screen's ctx, as app.js builds it, with spies in place of the server calls. */
export function makeCtx({ table = {}, betting = null, round = null, credits = 1000, chip = 5, local = {} } = {}) {
  const ctx = {
    table: { title: 'Test Table', min_bet: 1, max_bet: 100, layout: {}, ...table },
    betting,
    round,
    player: player({ credits }),
    chipValues: CHIP_VALUES,
    local: { stakes: {}, chip, cards: {}, shown: false, lastBets: null, ...local },
    busy: false,
    toast: vi.fn(),
    rerender: vi.fn(),
    start: vi.fn(),
    act: vi.fn(),
    repeat: vi.fn(),
    newRound: vi.fn(),
  };
  return ctx;
}

export function card(text) {
  return { rank: text.slice(0, -1), suit: text.slice(-1) };
}

export function mount() {
  const el = document.createElement('div');
  document.body.append(el);
  return el;
}

export function click(el) {
  el.dispatchEvent(new MouseEvent('click', { bubbles: true }));
}

export function rightClick(el) {
  el.dispatchEvent(new MouseEvent('contextmenu', { bubbles: true, cancelable: true }));
}

export function byText(root, selector, text) {
  return [...root.querySelectorAll(selector)].find((el) => el.textContent.includes(text));
}

/* Requests the page makes with fetch are answered from `routes`, keyed by "METHOD path". */
export function fakeServer(routes = {}) {
  const calls = [];
  const fetch = vi.fn(async (url, options = {}) => {
    const method = options.method || 'GET';
    const path = String(url).replace(/^api\//, '');
    const body = options.body === undefined ? undefined : JSON.parse(options.body);
    calls.push({ method, path, body });
    const handler = routes[`${method} ${path}`];
    if (!handler) return reply(404, { error: 'Not found.' });
    const result = typeof handler === 'function' ? await handler(body) : handler;
    return typeof result?.json === 'function' ? result : reply(200, result);
  });
  vi.stubGlobal('fetch', fetch);
  return { fetch, calls, routes };
}

export function reply(status, body) {
  return { ok: status >= 200 && status < 300, status, json: async () => body };
}
