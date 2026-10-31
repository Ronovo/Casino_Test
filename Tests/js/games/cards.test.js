import { describe, expect, it } from 'vitest';
import * as baccarat from '../../../casino/web/static/js/games/baccarat.js';
import * as blackjack from '../../../casino/web/static/js/games/blackjack.js';
import * as poker from '../../../casino/web/static/js/games/poker.js';
import { byText, card, click, makeCtx, mount } from '../helpers.js';

const RESULT = { net: 10, notes: ['Done.'], settlements: [] };

function redraw(game, ctx, el) {
  el.replaceChildren();
  return game.render(ctx, el);
}

describe('baccarat', () => {
  const table = { layout: { bets: [{ key: 'player', label: 'Player', pays: '1:1' },
    { key: 'banker', label: 'Banker', pays: '1:1' }, { key: 'tie', label: 'Tie', pays: '8:1' },
    { key: 'dragon7', label: 'Dragon 7 bonus', pays: '40:1' }, { key: 'panda8', label: 'Panda 8 bonus', pays: '25:1' }] } };

  it('takes bets and deals', () => {
    const ctx = makeCtx({ table });
    const el = mount();
    expect(baccarat.render(ctx, el)).toBe(0);
    expect(el.querySelector('.bac-player .spot').textContent).toContain('Player');
    expect([...el.querySelectorAll('.bac-strip .spot .spot-name')].map((s) => s.textContent)).toEqual(['Dragon 7 bonus', 'Tie', 'Panda 8 bonus']);
    click(byText(el, '.spot', 'Player'));
    redraw(baccarat, ctx, el);
    click(byText(el, 'button', 'Deal'));
    expect(ctx.start).toHaveBeenCalledWith({ player: 5 });
  });

  it('deals Player and Banker alternately and names the winner once the cards are down', () => {
    const round = {
      player: { cards: [card('9S'), card('KH')], total: 9 },
      banker: { cards: [card('2H'), card('3D'), card('4C')], total: 9 },
      winner: 'tie', stakes: { player: 0, banker: 10, tie: 5 }, finished: true, actions: [], result: RESULT,
    };
    const el = mount();
    expect(baccarat.render(makeCtx({ table, round }), el)).toBe(3000);
    expect(el.querySelector('.bac-winner').textContent).toBe('Tie');
    expect([...el.querySelectorAll('.spot.locked .spot-name')].map((s) => s.textContent)).toEqual(['Banker', 'Tie']);
    expect(el.querySelector('.bac-tie .bac-win').style.animationDelay).toBe('3000ms');
    expect(el.querySelector('.bac-boxes .bac-win')).toBeNull();
  });

  it('outlines the winning box once the cards are down', () => {
    const round = {
      player: { cards: [card('9S'), card('KH')], total: 9 },
      banker: { cards: [card('2H'), card('3D'), card('4C')], total: 9 },
      winner: 'banker', stakes: { player: 10 }, finished: true, actions: [], result: RESULT,
    };
    const el = mount();
    baccarat.render(makeCtx({ table, round }), el);
    expect(el.querySelector('.bac-banker .bac-win.late')).toBeTruthy();
    expect(el.querySelector('.bac-player .bac-win')).toBeNull();
    expect(el.querySelector('.bac-tie .bac-win')).toBeNull();
    expect(el.querySelectorAll('.spot.locked')).toHaveLength(1);
  });
});

describe('blackjack', () => {
  const table = { layout: { natural: '3:2' } };
  const hand = (overrides) => ({ name: 'Hand', cards: [card('10S'), card('6H')], bet: 10, status: '', active: true,
    label: '16', state: '', ...overrides });

  it('takes a bet and deals', () => {
    const ctx = makeCtx({ table });
    const el = mount();
    expect(blackjack.render(ctx, el)).toBe(0);
    expect(el.querySelector('.bj-arc').textContent).toBe('Blackjack pays 3 to 2');
    expect(el.querySelector('.bj-arc').style.getPropertyValue('--mid')).toBe('10');
    expect(el.querySelectorAll('.bj-arc span')[4].style.getPropertyValue('--i')).toBe('4');
    click(el.querySelector('.spot'));
    redraw(blackjack, ctx, el);
    click(byText(el, 'button', 'Deal'));
    expect(ctx.start).toHaveBeenCalledWith({ bet: 5 });
  });

  it('shows one hand waiting for a move', () => {
    const round = { finished: false, actions: [{ id: 'hit', label: 'Hit' }],
      dealer: { cards: [card('9C'), null], label: 'Showing 9', state: '' }, hands: [hand()] };
    const el = mount();
    expect(blackjack.render(makeCtx({ table, round }), el)).toBe(0);
    expect(el.querySelector('.seat.active .seat-label').textContent).toContain('You');
    expect(byText(el, 'button', 'Hit')).toBeTruthy();
  });

  it('shows the insurance stake under the dealer once it is taken', () => {
    const round = { finished: false, actions: [{ id: 'hit', label: 'Hit' }], insurance: 5,
      dealer: { cards: [card('AC'), null], label: 'Showing 11', state: '' }, hands: [hand()] };
    const el = mount();
    blackjack.render(makeCtx({ table, round }), el);
    expect([...el.querySelectorAll('.spot.locked .spot-name')].map((s) => s.textContent)).toEqual(['Insurance', 'Bet']);
    expect(byText(el, '.spot.locked', 'Insurance').textContent).toContain('5 cr');
  });

  it('shows split hands, the one in play and the one waiting', () => {
    const round = { finished: false, actions: [{ id: 'stand', label: 'Stand' }],
      dealer: { cards: [card('9C'), null], label: 'Showing 9', state: '' },
      hands: [hand({ name: 'Hand 1' }), hand({ name: 'Hand 2', active: false })] };
    const el = mount();
    blackjack.render(makeCtx({ table, round, local: { cards: { dealer: ['9C', null] } } }), el);
    expect(el.querySelector('.seat.active').textContent).toContain('Hand 1');
    expect(el.querySelector('.seat.waiting').textContent).toContain('Hand 2');
    expect([...el.querySelectorAll('.hands .seat')].map((s) => s.style.getPropertyValue('--fan'))).toEqual(['-0.5', '0.5']);
  });

  it('reveals the dealer and the result after the last card', () => {
    const round = { finished: true, actions: [], result: RESULT,
      dealer: { cards: [card('9C'), card('8D')], label: '17', state: '' },
      hands: [hand({ name: 'Hand 1', status: 'Doubled', active: false }), hand({ name: 'Hand 2', active: false })] };
    const ctx = makeCtx({ table, round, local: { lastBets: { bet: 10 }, cards: { dealer: ['9C', null] } } });
    const el = mount();
    const reveal = blackjack.render(ctx, el);
    expect(reveal).toBeGreaterThan(0);
    expect(el.querySelector('.seat.waiting')).toBeNull();
    expect(el.textContent).toContain('Doubled');
    expect(byText(el, 'button', 'Deal again').textContent).toBe('Deal again (10 cr)');
    ctx.local.lastBets = null;
    redraw(blackjack, ctx, el);
    expect(byText(el, 'button', 'Deal again').textContent).toBe('Deal again (0 cr)');
  });
});

describe('poker', () => {
  it('needs an Ante, places the Blind and takes optional side bets', () => {
    const ctx = makeCtx();
    const el = mount();
    expect(poker.render(ctx, el)).toBe(0);
    expect(byText(el, 'button', 'Deal').disabled).toBe(true);
    for (const name of ['Trips', 'Ante', 'Pairs Bonus']) {
      redraw(poker, ctx, el);
      click(byText(el, '.spot', name));
    }
    redraw(poker, ctx, el);
    expect(byText(el, '.spot', 'Blind').textContent).toContain('5 cr');
    expect(el.querySelector('.uth-core .spot.ghost').textContent).toBe('Play');
    expect(el.querySelectorAll('.uth-slot')).toHaveLength(5);
    expect(el.querySelector('.bet-total').textContent).toBe('Bet 20 cr');
    click(byText(el, 'button', 'Deal'));
    expect(ctx.start).toHaveBeenCalledWith({ ante: 5, trips: 5, pairs: 5 });
  });

  it('keeps the dealer and the rest of the board face down mid-hand', () => {
    const round = { finished: false, actions: [{ id: 'check', label: 'Check' }], street: 'Pre-Flop',
      player: [card('AS'), card('AD')], player_hand: 'Pair of Aces', board: [null, null, null, null, null],
      dealer: [null, null], dealer_hand: null, bets: { ante: 10, blind: 10 } };
    const el = mount();
    expect(poker.render(makeCtx({ round }), el)).toBe(0);
    expect(el.querySelectorAll('.card.back')).toHaveLength(7);
    expect([...el.querySelectorAll('.spot.ghost .spot-name')].map((s) => s.textContent)).toEqual(['Trips', 'Play', 'Pairs Bonus']);
    expect([...el.querySelectorAll('.uth-core .spot .spot-name')].map((s) => s.textContent)).toEqual(['Ante', 'Blind', 'Play']);
    expect(byText(el, 'button', 'Check')).toBeTruthy();
  });

  it('shows the showdown once the cards are out', () => {
    const board = [card('2C'), card('7S'), card('KD'), card('9D'), card('5C')];
    const round = { finished: true, actions: [], street: 'Showdown', result: RESULT,
      player: [card('AS'), card('AD')], player_hand: 'Pair of Aces', board, dealer: [card('3H'), card('4H')],
      dealer_hand: 'High Card, King', bets: { ante: 10, blind: 10, play: 40, trips: 5, pairs: 5 } };
    const el = mount();
    const ctx = makeCtx({ round, local: { cards: { player: ['AS', 'AD'], board: ['2C', '7S', 'KD', null, null],
      dealer: [null, null] } } });
    expect(poker.render(ctx, el)).toBeGreaterThan(0);
    expect(el.textContent).toContain('High Card, King');
    expect(el.querySelectorAll('.spot.locked')).toHaveLength(5);
    expect(el.querySelector('.spot.ghost')).toBeNull();
  });
});
