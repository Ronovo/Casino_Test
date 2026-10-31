import { describe, expect, it, vi } from 'vitest';
import { add, clear, credits, h, limits, netClass, signedCredits } from '../../casino/web/static/js/dom.js';

describe('h', () => {
  it('sets classes, styles, listeners, properties and attributes', () => {
    const onclick = vi.fn();
    const el = h('input', {
      class: 'big', style: { color: 'red', '--size': '3px' }, onclick, value: 'hi', 'data-x': 7, 'aria-hidden': true,
      skipped: null, off: false,
    });
    el.click();
    expect(el.className).toBe('big');
    expect(el.style.color).toBe('red');
    expect(el.style.getPropertyValue('--size')).toBe('3px');
    expect(onclick).toHaveBeenCalledOnce();
    expect(el.value).toBe('hi');
    expect(el.getAttribute('data-x')).toBe('7');
    expect(el.getAttribute('aria-hidden')).toBe('');
    expect(el.hasAttribute('skipped')).toBe(false);
    expect(el.hasAttribute('off')).toBe(false);
  });

  it('adds children as text, never as markup', () => {
    const el = h('div', null, '<b>bold</b>', 3, [h('span', null, 'nested'), [null, false]], null);
    expect(el.querySelector('b')).toBeNull();
    expect(el.textContent).toBe('<b>bold</b>3nested');
  });
});

describe('helpers', () => {
  it('adds to and clears an element', () => {
    const el = add(h('div'), 'a', ['b']);
    expect(el.textContent).toBe('ab');
    expect(clear(el).childNodes.length).toBe(0);
  });

  it('formats credits and limits', () => {
    expect(credits(1234)).toBe('1,234 cr');
    expect(signedCredits(5)).toBe('+5 cr');
    expect(signedCredits(-5)).toBe('-5 cr');
    expect(signedCredits(0)).toBe('0 cr');
    expect(limits({ min_bet: 5, max_bet: 500 })).toBe('5 cr to 500 cr');
    expect(limits({ min_bet: 1, max_bet: null })).toBe('1 cr to no limit');
  });

  it('names the result of a net amount', () => {
    expect(netClass(10)).toBe('win');
    expect(netClass(-10)).toBe('lose');
    expect(netClass(0)).toBe('push');
    expect(netClass(0, '')).toBe('');
  });
});
