import { add, credits, h, signedCredits } from './dom.js';

const SUITS = { S: '♠', H: '♥', D: '♦', C: '♣' };

// ------------------------------------------------------------------ cards
export function cardEl(card, { animation = '', delay = 0 } = {}) {
  const red = card && (card.suit === 'H' || card.suit === 'D');
  const el = h('div', { class: `card ${card ? '' : 'back'} ${red ? 'red' : ''} ${animation}` });
  if (delay) el.style.animationDelay = `${delay}ms`;
  if (card) {
    const suit = SUITS[card.suit];
    add(el, [h('span', { class: 'corner' }, card.rank, h('br'), suit), h('span', { class: 'pip' }, suit),
             h('span', { class: 'corner flip' }, card.rank, h('br'), suit)]);
  }
  return el;
}

/* A hand that animates only what changed since the previous render of the same `key`:
   new cards are dealt in, face-down cards that are now face up are turned over.
   Returns the element and the time in ms until its last animation has started. */
export function handEl(ctx, key, cards, { start = 0, step = 300, spread = false } = {}) {
  const before = ctx.local.cards[key] || [];
  const el = h('div', { class: `hand ${spread ? 'spread' : ''}` });
  let delay = start;
  let changed = 0;
  cards.forEach((card, index) => {
    const dealt = index >= before.length;
    const turned = !dealt && before[index] === null && card !== null;
    const animation = dealt ? 'fresh' : turned ? 'turned' : '';
    el.append(cardEl(card, { animation, delay: animation ? delay : 0 }));
    if (animation) {
      delay += step;
      changed += 1;
    }
  });
  ctx.local.cards[key] = cards.map((card) => (card ? card.rank + card.suit : null));
  return { el, until: changed ? delay : start };
}

// ------------------------------------------------------------------ chips
function chipLabel(value) {
  return value >= 1000 ? `${value / 1000}K` : String(value);
}

export function chipEl(color, value, extra = '') {
  return h('div', { class: `chip ${color} ${extra}` }, chipLabel(value));
}

/* Up to `limit` chips showing an amount the way a dealer would stack it, biggest chips at the bottom. */
export function stackEl(ctx, amount, limit = 5) {
  const el = h('div', { class: 'stack' });
  const colors = Object.keys(ctx.chipValues).reverse();
  let left = amount;
  let shown = 0;
  for (const color of colors) {
    const value = ctx.chipValues[color];
    while (left >= value && shown < limit) {
      el.append(chipEl(color, value, 'small'));
      left -= value;
      shown += 1;
    }
  }
  return el;
}

/* Stakes being built for the next round. `cost` turns the stakes into the credits they take from the wallet
   (a poker Ante also buys a Blind); `reserve` is extra the table wants left in the rack on top of that. */
export function betSlip(ctx, { cost = (stakes) => Object.values(stakes).reduce((a, b) => a + b, 0), reserve = () => 0 } = {}) {
  const stakes = ctx.local.stakes;
  const limit = ctx.table.max_bet || Infinity;
  return {
    stakes,
    get: (key) => stakes[key] || 0,
    cost: () => cost(stakes),
    add(key) {
      const current = stakes[key] || 0;
      const next = Math.min(current + ctx.local.chip, limit);
      if (next === current) return ctx.toast(`The most you can put there is ${credits(limit)}.`, 'error');
      stakes[key] = next;
      if (cost(stakes) + reserve(stakes) > ctx.player.credits) {
        stakes[key] = current;
        if (!current) delete stakes[key];
        return ctx.toast("You don't have enough chips for that.", 'error');
      }
      ctx.rerender();
    },
    remove(key) {
      const next = (stakes[key] || 0) - ctx.local.chip;
      if (next > 0) stakes[key] = next;
      else delete stakes[key];
      ctx.rerender();
    },
    clear() {
      for (const key of Object.keys(stakes)) delete stakes[key];
      ctx.rerender();
    },
  };
}

export function chipTray(ctx) {
  const tray = h('div', { class: 'tray' });
  for (const [color, value] of Object.entries(ctx.chipValues)) {
    const button = h('button', {
      class: `chip ${color} ${ctx.local.chip === value ? 'on' : ''}`,
      title: `Bet with ${credits(value)} chips`,
      disabled: value > ctx.player.credits,
      onclick: () => {
        ctx.local.chip = value;
        ctx.rerender();
      },
    }, chipLabel(value));
    tray.append(button);
  }
  return tray;
}

export function spotEl(ctx, slip, key, name, pays, { wide = false } = {}) {
  const amount = slip.get(key);
  return h('button', {
    class: `spot ${wide ? 'wide' : ''}`,
    title: 'Click to add a chip, right-click to take one back',
    onclick: () => slip.add(key),
    oncontextmenu: (event) => {
      event.preventDefault();
      slip.remove(key);
    },
  }, h('span', { class: 'spot-name' }, name), pays && h('span', { class: 'spot-pays' }, pays),
     amount ? [stackEl(ctx, amount), h('span', { class: 'spot-amount' }, credits(amount))] : null);
}

export function lockedSpot(ctx, name, amount, pays) {
  return h('div', { class: `spot locked` }, h('span', { class: 'spot-name' }, name),
           pays && h('span', { class: 'spot-pays' }, pays),
           amount ? [stackEl(ctx, amount), h('span', { class: 'spot-amount' }, credits(amount))] : null);
}

export function betBar(ctx, slip, { label = 'Deal', ready = true, onDeal, extra = [] }) {
  const total = slip.cost();
  return h('div', { class: 'bet-bar' },
    chipTray(ctx),
    h('div', { class: 'bet-total' }, `Bet ${credits(total)}`),
    extra,
    h('button', { onclick: () => slip.clear(), disabled: !total }, 'Clear'),
    h('button', { class: 'primary', disabled: !ready || !total || ctx.busy, onclick: onDeal }, label));
}

export function actionBar(ctx, round) {
  return h('div', { class: 'actions' }, round.actions.map((action, index) => h('button', {
    class: index === 0 ? 'primary' : '',
    disabled: ctx.busy,
    onclick: () => ctx.act(action.id),
  }, action.label)));
}

// ------------------------------------------------------------------ results
const RESULT_TEXT = { win: 'WIN', lose: 'LOSE', push: 'PUSH', surrender: 'SURRENDER' };
const RESULT_CLASS = { win: 'win', lose: 'lose', push: 'push', surrender: 'push' };

export function resultPanel(ctx, round, { delay = 0, again = 'Same bets again' } = {}) {
  const { net, notes, settlements } = round.result;
  const banner = net > 0 ? ['win', `★ YOU WIN ${signedCredits(net)} ★`]
    : net < 0 ? ['lose', `THE HOUSE WINS ${signedCredits(net)}`]
    : ['push', 'PUSH: your stake comes back'];
  const rows = settlements.map((s) => h('tr', null,
    h('td', null, s.label),
    h('td', null, credits(s.amount)),
    h('td', { class: RESULT_CLASS[s.result] }, RESULT_TEXT[s.result] + (s.ratio ? ` ${s.ratio}` : '')),
    h('td', { class: s.net > 0 ? 'win' : s.net < 0 ? 'lose' : 'push' }, signedCredits(s.net))));
  const panel = h('div', { class: 'result' },
    h('div', { class: `banner ${banner[0]}` }, banner[1]),
    h('div', { class: 'notes' }, notes.map((note) => h('p', null, note))),
    h('table', { class: 'data' },
      h('thead', null, h('tr', null, ['Bet', 'Stake', 'Result', 'Net'].map((name) => h('th', null, name)))),
      h('tbody', null, rows)),
    h('div', { class: 'actions' },
      h('button', { class: 'primary', disabled: !ctx.local.lastBets, onclick: () => ctx.repeat() }, again),
      h('button', { onclick: () => ctx.newRound() }, 'Change bets')));
  return late(panel, delay);
}

/* Keep an element hidden until `delay` ms from now, so it can't give away a result mid-animation. */
export function late(el, delay) {
  el.classList.add('late');
  el.style.animationDelay = `${delay}ms`;
  return el;
}

export function seatEl(label, pill, body, extra = '') {
  return h('div', { class: `seat ${extra}` },
    h('div', { class: 'seat-label' }, label, pill && h('span', { class: `pill ${pill.state || ''}` }, pill.label)),
    body);
}
