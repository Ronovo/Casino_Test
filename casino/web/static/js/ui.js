import { add, credits, h, netClass, signedCredits } from './dom.js';

const SUITS = { S: '♠', H: '♥', D: '♦', C: '♣' };

/* Classic pip positions for 2-10 as [column, row] on a 3 by 13 grid; pips below the middle row hang upside down. */
const sides = (rows) => rows.flatMap((row) => [[1, row], [3, row]]);
const PIPS = {
  2: [[2, 1], [2, 13]], 3: [[2, 1], [2, 7], [2, 13]],
  4: sides([1, 13]), 5: [...sides([1, 13]), [2, 7]],
  6: sides([1, 7, 13]), 7: [...sides([1, 7, 13]), [2, 4]], 8: [...sides([1, 7, 13]), [2, 4], [2, 10]],
  9: [...sides([1, 5, 9, 13]), [2, 7]], 10: [...sides([1, 5, 9, 13]), [2, 3], [2, 11]],
};

// ------------------------------------------------------------------ cards
export function cardEl(card, { animation = '', delay = 0 } = {}) {
  const red = card && (card.suit === 'H' || card.suit === 'D');
  const el = h('div', { class: `card ${card ? '' : 'back'} ${red ? 'red' : ''} ${animation}` });
  if (delay) el.style.animationDelay = `${delay}ms`;
  if (card) {
    const suit = SUITS[card.suit];
    const spots = PIPS[card.rank];
    const kind = spots ? 'number' : card.rank === 'A' ? 'ace' : 'face';
    const pip = { number: () => spots.map(([col, row]) => h('i', { class: row > 7 ? 'flip' : '', style: { gridArea: `${row} / ${col}` } }, suit)),
      ace: () => suit, face: () => h('b', null, card.rank) }[kind]();
    el.classList.add(kind);
    add(el, [h('span', { class: 'corner' }, card.rank, h('br'), suit), h('span', { class: 'pip' }, pip),
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
/* A chip or stake in thousands from 1,000 up, to one decimal: 1500 is 1.5K. */
export function chipLabel(value) {
  return value >= 1000 ? `${Math.floor(value / 100) / 10}K` : String(value);
}

export function chipEl(color, value, extra = '') {
  return h('div', { class: `chip ${color} ${extra}` }, chipLabel(value));
}

/* Up to `limit` chips showing an amount the way a dealer would stack it, biggest chips at the bottom. */
function stackEl(ctx, amount, limit = 5) {
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

function chipTray(ctx) {
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

export const SLIP_HINT = 'Click to add a chip, right-click to take one back';

/* Click adds the chosen chip to this spot on the slip, right-click takes one back. */
export function slipHandlers(slip, key) {
  return {
    onclick: () => slip.add(key),
    oncontextmenu: (event) => {
      event.preventDefault();
      slip.remove(key);
    },
  };
}

function spotContents(ctx, name, amount, pays) {
  return [h('span', { class: 'spot-name' }, name), pays && h('span', { class: 'spot-pays' }, pays),
    amount ? [stackEl(ctx, amount), h('span', { class: 'spot-amount' }, credits(amount))] : null];
}

export function spotEl(ctx, slip, key, name, pays, { wide = false } = {}) {
  return h('button', {
    class: `spot ${wide ? 'wide' : ''}`,
    title: SLIP_HINT,
    ...slipHandlers(slip, key),
  }, spotContents(ctx, name, slip.get(key), pays));
}

export function lockedSpot(ctx, name, amount, pays) {
  return h('div', { class: 'spot locked' }, spotContents(ctx, name, amount, pays));
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

export function resultPanel(ctx, round, { again = 'Same bets again' } = {}) {
  const { net, notes, settlements } = round.result;
  const outcome = netClass(net);
  const banner = { win: `★ YOU WIN ${signedCredits(net)} ★`, lose: `THE HOUSE WINS ${signedCredits(net)}`,
    push: 'PUSH: your stake comes back' }[outcome];
  const rows = settlements.map((s) => h('tr', null,
    h('td', null, s.label),
    h('td', null, credits(s.amount)),
    h('td', { class: RESULT_CLASS[s.result] }, RESULT_TEXT[s.result] + (s.ratio ? ` ${s.ratio}` : '')),
    h('td', { class: netClass(s.net) }, signedCredits(s.net))));
  return h('div', { class: 'result' },
    h('div', { class: `banner ${outcome}` }, banner),
    h('div', { class: 'notes' }, notes.map((note) => h('p', null, note))),
    h('table', { class: 'data' },
      h('thead', null, h('tr', null, ['Bet', 'Stake', 'Result', 'Net'].map((name) => h('th', null, name)))),
      h('tbody', null, rows)),
    h('div', { class: 'actions' },
      h('button', { class: 'primary', disabled: !ctx.local.lastBets, onclick: () => ctx.repeat() }, again),
      h('button', { onclick: () => ctx.newRound() }, 'Change bets')));
}

/* Once the reveal delay has passed, `el` takes the felt's place, or lies over it when `over` is set. */
export function afterReveal(felt, el, delay, { over = false } = {}) {
  late(el, 0);
  const show = () => (over ? felt.append(el) : felt.replaceWith(el));
  if (delay) setTimeout(show, delay);
  else show();
}

/* `hold` keeps the finished table up for a while after the reveal before the result takes its place. */
export function settleRound(ctx, felt, round, { delay = 0, hold = 0, again } = {}) {
  afterReveal(felt, resultPanel(ctx, round, { again }), delay + hold);
}

/* Keep an element hidden until `delay` ms from now, so it can't give away a result mid-animation. */
export function late(el, delay) {
  el.classList.add('late');
  el.style.animationDelay = `${delay}ms`;
  return el;
}

export function tabsEl(options, selected, pick) {
  return h('div', { class: 'tabs' }, Object.entries(options).map(([key, label]) =>
    h('button', { type: 'button', class: key === selected ? 'on' : '', onclick: () => pick(key) }, label)));
}

export function seatEl(label, pill, body, extra = '') {
  return h('div', { class: `seat ${extra}` },
    h('div', { class: 'seat-label' }, label, pill && h('span', { class: `pill ${pill.state || ''}` }, pill.label)),
    body);
}
