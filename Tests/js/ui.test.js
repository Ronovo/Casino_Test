import { describe, expect, it } from 'vitest';
import {
  actionBar, betBar, betSlip, cardEl, chipEl, chipLabel, handEl, late, lockedSpot, resultPanel, seatEl, slipHandlers,
  spotEl,
} from '../../casino/web/static/js/ui.js';
import { byText, click, makeCtx, rightClick } from './helpers.js';

describe('cards', () => {
  it('draws face-up red and black cards and face-down backs', () => {
    const red = cardEl({ rank: 'A', suit: 'H' }, { animation: 'fresh', delay: 300 });
    expect(red.className).toContain('red');
    expect(red.className).toContain('fresh');
    expect(red.style.animationDelay).toBe('300ms');
    expect(red.textContent).toContain('♥');
    const black = cardEl({ rank: '10', suit: 'S' });
    expect(black.className).not.toContain('red');
    expect(black.style.animationDelay).toBe('');
    expect(cardEl(null).className).toContain('back');
  });

  it('lays out pips for number cards, one pip for aces and a medallion for faces', () => {
    const ten = cardEl({ rank: '10', suit: 'S' });
    expect(ten.className).toContain('number');
    const pips = [...ten.querySelectorAll('.pip i')];
    expect(pips).toHaveLength(10);
    expect(pips.every((pip) => pip.textContent === '♠')).toBe(true);
    expect(pips.filter((pip) => pip.className === 'flip')).toHaveLength(5);
    expect(pips[0].style.gridArea).toBe('1 / 1');
    expect(cardEl({ rank: '7', suit: 'C' }).querySelectorAll('.pip i.flip')).toHaveLength(2);
    const ace = cardEl({ rank: 'A', suit: 'D' });
    expect(ace.className).toContain('ace');
    expect(ace.querySelector('.pip').textContent).toBe('♦');
    expect(ace.querySelector('.pip').children).toHaveLength(0);
    const king = cardEl({ rank: 'K', suit: 'H' });
    expect(king.className).toContain('face');
    expect(king.querySelector('.pip b').textContent).toBe('K');
    expect(king.querySelectorAll('.corner')).toHaveLength(2);
  });

  it('animates only the cards that are new or newly turned over', () => {
    const ctx = makeCtx();
    const first = handEl(ctx, 'dealer', [{ rank: '9', suit: 'C' }, null], { start: 100, step: 200 });
    expect(first.until).toBe(500);
    expect(first.el.querySelectorAll('.fresh')).toHaveLength(2);
    expect(ctx.local.cards.dealer).toEqual(['9C', null]);

    const second = handEl(ctx, 'dealer', [{ rank: '9', suit: 'C' }, { rank: 'K', suit: 'D' }], { spread: true });
    expect(second.el.className).toContain('spread');
    expect(second.el.querySelectorAll('.turned')).toHaveLength(1);
    expect(second.until).toBe(300);

    const unchanged = handEl(ctx, 'dealer', [{ rank: '9', suit: 'C' }, { rank: 'K', suit: 'D' }], { start: 40 });
    expect(unchanged.until).toBe(40);
  });
});

describe('chips', () => {
  it('labels chips and stakes', () => {
    expect(chipLabel(25)).toBe('25');
    expect(chipLabel(1500)).toBe('1.5K');
    expect(chipEl('Green', 25).className).toBe('chip Green ');
  });
});

describe('betSlip', () => {
  it('adds the chosen chip, takes it back and clears', () => {
    const ctx = makeCtx({ chip: 25 });
    const slip = betSlip(ctx);
    slip.add('bet');
    slip.add('bet');
    expect(slip.get('bet')).toBe(50);
    expect(slip.cost()).toBe(50);
    slip.remove('bet');
    expect(slip.get('bet')).toBe(25);
    slip.remove('bet');
    expect(slip.stakes).toEqual({});
    slip.remove('never');
    expect(slip.stakes).toEqual({});
    slip.add('a');
    slip.add('b');
    slip.clear();
    expect(slip.stakes).toEqual({});
    expect(ctx.rerender).toHaveBeenCalledTimes(8);
  });

  it('stops at the table maximum', () => {
    const ctx = makeCtx({ chip: 100, table: { max_bet: 150 } });
    const slip = betSlip(ctx);
    slip.add('bet');
    slip.add('bet');
    slip.add('bet');
    expect(slip.get('bet')).toBe(150);
    expect(ctx.toast).toHaveBeenCalledWith('The most you can put there is 150 cr.', 'error');
  });

  it('refuses more than the rack holds, with or without a reserve', () => {
    const ctx = makeCtx({ chip: 25, credits: 40, table: { max_bet: null } });
    const slip = betSlip(ctx);
    slip.add('bet');
    slip.add('bet');
    expect(slip.get('bet')).toBe(25);
    slip.add('other');
    expect(slip.stakes).toEqual({ bet: 25 });
    expect(ctx.toast).toHaveBeenCalledWith("You don't have enough chips for that.", 'error');

    const poker = betSlip(makeCtx({ chip: 10, credits: 30 }), { cost: (s) => s.ante * 2, reserve: (s) => s.ante });
    poker.add('ante');
    expect(poker.get('ante')).toBe(10);
    poker.add('ante');
    expect(poker.get('ante')).toBe(10);
  });

  it('wires click and right-click to the slip', () => {
    const ctx = makeCtx({ chip: 5 });
    const slip = betSlip(ctx);
    const spot = spotEl(ctx, slip, 'tie', 'Tie', 'pays 8:1', { wide: true });
    click(spot);
    expect(slip.get('tie')).toBe(5);
    rightClick(spot);
    expect(slip.get('tie')).toBe(0);
    const handlers = slipHandlers(slip, 'tie');
    handlers.onclick();
    expect(slip.get('tie')).toBe(5);
  });
});

describe('spots', () => {
  it('shows a stake on an open or locked spot', () => {
    const ctx = makeCtx();
    const slip = betSlip(ctx);
    ctx.local.stakes.bet = 1234;
    const open = spotEl(ctx, slip, 'bet', 'Your bet');
    expect(open.className).toBe('spot ');
    expect(open.querySelector('.spot-amount').textContent).toBe('1,234 cr');
    expect(open.querySelectorAll('.stack .chip')).toHaveLength(5);
    expect(open.querySelector('.spot-pays')).toBeNull();

    const locked = lockedSpot(ctx, 'Blind', 0, 'matches Ante');
    expect(locked.querySelector('.spot-pays').textContent).toBe('matches Ante');
    expect(locked.querySelector('.spot-amount')).toBeNull();
  });
});

describe('bars', () => {
  it('offers chips, clearing and dealing', () => {
    const ctx = makeCtx({ chip: 5, credits: 30 });
    const slip = betSlip(ctx);
    const dealt = [];
    const empty = betBar(ctx, slip, { onDeal: () => dealt.push(true) });
    expect(byText(empty, 'button', 'Deal').disabled).toBe(true);
    expect(byText(empty, 'button', 'Clear').disabled).toBe(true);
    expect(empty.querySelector('.chip.Red').className).toContain('on');
    expect(empty.querySelector('.chip.Black').disabled).toBe(true);

    click(empty.querySelector('.chip.Green'));
    expect(ctx.local.chip).toBe(25);
    slip.add('bet');
    const bar = betBar(ctx, slip, { label: 'Spin', onDeal: () => dealt.push(true), extra: ['extra bit'] });
    expect(bar.textContent).toContain('extra bit');
    click(byText(bar, 'button', 'Spin'));
    expect(dealt).toHaveLength(1);
    click(byText(bar, 'button', 'Clear'));
    expect(slip.stakes).toEqual({});
    ctx.busy = true;
    expect(byText(betBar(ctx, slip, { onDeal() {}, ready: false }), 'button', 'Deal').disabled).toBe(true);
  });

  it('lists the moves on offer', () => {
    const ctx = makeCtx();
    const bar = actionBar(ctx, { actions: [{ id: 'hit', label: 'Hit' }, { id: 'stand', label: 'Stand' }] });
    const [hit, stand] = bar.querySelectorAll('button');
    expect(hit.className).toBe('primary');
    expect(stand.className).toBe('');
    click(stand);
    expect(ctx.act).toHaveBeenCalledWith('stand');
  });
});

describe('resultPanel', () => {
  const settlement = (result, net, ratio = null) => ({ label: 'Hand', amount: 10, result, ratio, net });

  it('shows a win, every kind of settlement and the buttons for the next round', () => {
    const ctx = makeCtx({ local: { lastBets: { bet: 10 } } });
    const round = { result: { net: 15, notes: ['Dealer busts!'], settlements: [
      settlement('win', 20, '2:1'), settlement('lose', -10), settlement('push', 0), settlement('surrender', -5),
    ] } };
    const panel = resultPanel(ctx, round, { delay: 900, again: 'Deal again' });
    expect(panel.querySelector('.banner').className).toBe('banner win');
    expect(panel.querySelector('.banner').textContent).toBe('★ YOU WIN +15 cr ★');
    expect(panel.style.animationDelay).toBe('900ms');
    expect([...panel.querySelectorAll('tbody td:nth-child(3)')].map((td) => td.textContent))
      .toEqual(['WIN 2:1', 'LOSE', 'PUSH', 'SURRENDER']);
    expect([...panel.querySelectorAll('tbody td:nth-child(4)')].map((td) => td.className))
      .toEqual(['win', 'lose', 'push', 'lose']);
    click(byText(panel, 'button', 'Deal again'));
    click(byText(panel, 'button', 'Change bets'));
    expect(ctx.repeat).toHaveBeenCalledOnce();
    expect(ctx.newRound).toHaveBeenCalledOnce();
  });

  it('shows a loss and a push, and can only repeat bets it has', () => {
    const ctx = makeCtx();
    const lost = resultPanel(ctx, { result: { net: -10, notes: [], settlements: [] } });
    expect(lost.querySelector('.banner').textContent).toBe('THE HOUSE WINS -10 cr');
    expect(lost.style.animationDelay).toBe('0ms');
    expect(byText(lost, 'button', 'Same bets again').disabled).toBe(true);
    const pushed = resultPanel(ctx, { result: { net: 0, notes: [], settlements: [] } });
    expect(pushed.querySelector('.banner').className).toBe('banner push');
  });
});

describe('layout helpers', () => {
  it('delays an element and labels a seat', () => {
    expect(late(document.createElement('div'), 250).className).toBe('late');
    const plain = seatEl('Dealer', null, 'cards');
    expect(plain.className).toBe('seat ');
    expect(plain.querySelector('.pill')).toBeNull();
    const busted = seatEl('You', { label: '22 BUST', state: 'bust' }, 'cards', 'active');
    expect(busted.className).toBe('seat active');
    expect(busted.querySelector('.pill').className).toBe('pill bust');
    expect(seatEl('You', { label: '20' }, 'cards').querySelector('.pill').className).toBe('pill ');
  });
});
