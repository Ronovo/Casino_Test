import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { render } from '../../../casino/web/static/js/games/roulette.js';
import { byText, click, makeCtx, mount, rightClick } from '../helpers.js';

const NUMBERS = Array.from({ length: 36 }, (_, i) => String(i + 1));
const RED = [1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36];
const TABLE = { layout: { wheel: ['00', '0', ...NUMBERS], red: RED } };
const RESULT = { net: -5, notes: [], settlements: [] };

let frames;

beforeEach(() => {
  frames = [];
  vi.useFakeTimers();
  vi.stubGlobal('requestAnimationFrame', (fn) => frames.push(fn));
});

afterEach(() => {
  vi.useRealTimers();
  vi.unstubAllGlobals();
});

function cell(el, label) {
  return [...el.querySelectorAll('.cell')].find((c) => c.firstChild.textContent === label);
}

describe('roulette', () => {
  it('colors the board and sends every kind of bet', () => {
    const ctx = makeCtx({ table: TABLE });
    ctx.rerender = () => {
      el.replaceChildren();
      render(ctx, el);
    };
    const el = mount();
    expect(render(ctx, el)).toBe(0);
    expect([...el.querySelectorAll('.cell.green')].map((c) => c.textContent)).toEqual(['0', '00']);
    expect(cell(el, '1').className).toContain('red');
    expect(cell(el, '2').className).toContain('black');
    expect(el.querySelectorAll('.cell.column')).toHaveLength(3);
    expect(el.querySelector('.wheel').style.getPropertyValue('--pockets')).toBe('38');
    expect(cell(el, 'Red').className).toContain('outside red');

    for (const label of ['17', '17', '2nd 12', 'Red']) click(cell(el, label));
    click(cell(el, '2 to 1'));
    rightClick(cell(el, '2 to 1'));
    expect(cell(el, '17').querySelector('.marker').textContent).toBe('10');
    click(byText(el, 'button', 'Spin'));
    expect(ctx.start).toHaveBeenCalledWith({ bets: [
      { kind: 'straight', selection: '17', amount: 10 }, { kind: 'dozen', selection: 2, amount: 5 },
      { kind: 'red_black', selection: 'Red', amount: 5 },
    ] });
  });

  it('spins the wheel, then shows the pocket and the winning number', () => {
    const ctx = makeCtx({ table: TABLE, round: { pocket: '17', color: 'black', finished: true, actions: [],
      result: RESULT } });
    const el = mount();
    expect(render(ctx, el)).toBe(5300);
    const disc = el.querySelector('.wheel');
    expect(disc.querySelectorAll('.pocket-num')).toHaveLength(38);
    expect(cell(el, '17').className).toContain('winner');
    expect(cell(el, '17').style.animationDelay).toBe('5000ms');
    expect(cell(el, '18').disabled).toBe(true);

    frames.shift()();
    frames.shift()();
    expect(disc.className).toContain('spin');
    expect(el.querySelector('.wheel-ball').className).toBe('wheel-ball spin');
    expect(disc.style.transform).toBe(`rotate(${-18 * (360 / 38) - 5 * 360}deg)`);
    expect(el.querySelector('.wheel-hub').textContent).toBe('');
    vi.advanceTimersByTime(5000);
    expect(el.querySelector('.wheel-hub').className).toBe('wheel-hub black');
    expect(el.querySelector('.wheel-hub').textContent).toBe('17');
  });

  it('shows a wheel that has already spun at rest', () => {
    const ctx = makeCtx({ table: TABLE, round: { pocket: '0', color: 'green', finished: true, actions: [],
      result: RESULT }, local: { spun: true } });
    const el = mount();
    render(ctx, el);
    expect(frames).toHaveLength(0);
    expect(el.querySelector('.wheel-ball').className).toBe('wheel-ball');
    expect(el.querySelector('.wheel-hub').textContent).toBe('0');
  });
});
