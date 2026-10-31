import { describe, expect, it } from 'vitest';
import { render } from '../../../casino/web/static/js/games/gtn.js';
import { byText, click, makeCtx, mount } from '../helpers.js';

const RATIOS = { exact: '5:1', close: '1:1', high_low: '1:1', even_odd: '1:1', range: '2:1', lucky_1: '3:1',
  lucky_2: '1:1' };
const table = { layout: { difficulties: [
  { name: 'Easy', max_number: 10, scale: 1, half: 5, range_size: 2, digits: 2, ratios: RATIOS },
  { name: 'Medium', max_number: 100, scale: 10, half: 50, range_size: 20, digits: 3, ratios: RATIOS },
] } };

function redraw(ctx, el) {
  el.replaceChildren();
  return render(ctx, el);
}

function type(input, value) {
  input.value = value;
  input.dispatchEvent(new Event('input'));
}

function row(el, name) {
  return byText(el, '.bet-row', name);
}

function addChip(el, name) {
  click(byText(row(el, name), 'button', '+'));
}

describe('guess the number', () => {
  it('builds every kind of bet and sends them', () => {
    const ctx = makeCtx({ table });
    ctx.rerender = () => redraw(ctx, el);
    const el = mount();
    expect(render(ctx, el)).toBe(0);
    expect(el.querySelector('.sealed').textContent).toBe('??');
    expect(el.querySelector('.difficulty .toggle.on').textContent).toBe('Easy: 1 to 10');

    type(row(el, 'Pick a Number').querySelector('input'), '07');
    type(row(el, 'Range').querySelector('input'), '3');
    const [first, second] = row(el, 'Lucky Combo').querySelectorAll('input');
    type(first, '2');
    type(second, '9');
    click(byText(row(el, 'High / Low'), 'button', 'High'));
    click(byText(row(el, 'Even / Odd'), 'button', 'Odd'));
    for (const name of ['Pick a Number', 'Range', 'Lucky Combo', 'High / Low', 'Even / Odd']) addChip(el, name);
    addChip(el, 'Range');
    click(byText(row(el, 'Range'), 'button', '−'));

    expect(row(el, 'High / Low').querySelector('.toggle.on').textContent).toContain('High');
    click(byText(el, 'button', 'Reveal the number'));
    expect(ctx.start).toHaveBeenCalledWith({ difficulty: 'Easy', bets: {
      pick: { selection: 7, amount: 5 }, range: { selection: 3, amount: 5 }, lucky: { selection: [2, 9], amount: 5 },
      high_low: { selection: 'High', amount: 5 }, even_odd: { selection: 'Odd', amount: 5 },
    } });
  });

  it('asks for a choice on every bet with chips on it', () => {
    const ctx = makeCtx({ table });
    ctx.rerender = () => redraw(ctx, el);
    const el = mount();
    render(ctx, el);
    addChip(el, 'Pick a Number');
    type(row(el, 'Pick a Number').querySelector('input'), 'seven');
    click(byText(el, 'button', 'Reveal the number'));
    ctx.local.stakes = {};
    redraw(ctx, el);
    addChip(el, 'Lucky Combo');
    type(row(el, 'Lucky Combo').querySelector('input'), '4');
    click(byText(el, 'button', 'Reveal the number'));
    expect(ctx.toast).toHaveBeenCalledTimes(2);
    expect(ctx.toast).toHaveBeenCalledWith('Choose what you are betting on for every bet with chips on it.', 'error');
    expect(ctx.start).not.toHaveBeenCalled();
  });

  it('starts over with fresh choices on another difficulty', () => {
    const ctx = makeCtx({ table });
    ctx.rerender = () => redraw(ctx, el);
    const el = mount();
    render(ctx, el);
    addChip(el, 'Pick a Number');
    click(byText(el, 'button', 'Medium: 1 to 100'));
    expect(ctx.local.stakes).toEqual({});
    expect(el.querySelector('.sealed').textContent).toBe('???');
    expect(row(el, 'Range').textContent).toContain('20 numbers in a row');
  });

  it('reveals the number one digit at a time', () => {
    const ctx = makeCtx({ table, round: { difficulty: 'Medium', number: 7, finished: true, actions: [],
      result: { net: 0, notes: [], settlements: [] } } });
    const el = mount();
    expect(render(ctx, el)).toBe(3 * 350 + 300);
    const digits = el.querySelectorAll('.digit.shown');
    expect([...digits].map((d) => d.textContent).join('')).toBe('007');
    expect(digits[2].style.animationDelay).toBe('700ms');
    expect(el.querySelector('.felt-legend.reveal').textContent).toBe('The number is 7');
  });
});
