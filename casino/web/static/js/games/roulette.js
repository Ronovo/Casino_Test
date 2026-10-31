import { add, credits, h } from '../dom.js';
import { chipLabel, SLIP_HINT, betBar, betSlip, resultPanel, slipHandlers } from '../ui.js';

const SPIN_MS = 5000;
const FULL_TURNS = 5;
const POCKET_COLORS = { red: '#b3242f', black: '#17181c', green: '#1f8a48' };
const OUTSIDE = [
  ['low_high:Low', '1 to 18'], ['odd_even:Even', 'Even'], ['red_black:Red', 'Red'],
  ['red_black:Black', 'Black'], ['odd_even:Odd', 'Odd'], ['low_high:High', '19 to 36'],
];

function colorOf(table, pocket) {
  if (pocket === '0' || pocket === '00') return 'green';
  return table.layout.red.includes(Number(pocket)) ? 'red' : 'black';
}

function wheelEl(ctx, pocket) {
  const { wheel } = ctx.table.layout;
  const step = 360 / wheel.length;
  const slices = wheel.map((name, index) =>
    `${POCKET_COLORS[colorOf(ctx.table, name)]} ${index * step}deg ${(index + 1) * step}deg`);
  const disc = h('div', {
    class: 'wheel',
    style: { '--pockets': String(wheel.length), background: `conic-gradient(from ${-step / 2}deg, ${slices.join(', ')})` },
  }, wheel.map((name, index) => h('span', {
    class: 'pocket-num', style: { transform: `rotate(${index * step}deg) translateY(var(--pocket-orbit))` },
  }, name)));
  const hub = h('div', { class: 'wheel-hub' });
  const ball = h('div', { class: 'wheel-ball' });
  const box = h('div', { class: 'wheel-box' },
    h('div', { class: 'wheel-bowl' }), h('div', { class: 'wheel-pointer' }), disc, hub, ball);

  if (pocket != null) {
    // Turning the disc backwards by the pocket's angle brings that pocket under the pointer at the top.
    const rest = `rotate(${-(wheel.indexOf(pocket) * step) - 360 * FULL_TURNS}deg)`;
    const settle = () => {
      hub.textContent = pocket;
      hub.classList.add(ctx.round.color);
    };
    if (ctx.local.spun) {
      disc.style.transform = rest;
      settle();
    } else {
      ctx.local.spun = true;
      // The transition only runs if the browser has painted the starting position first.
      requestAnimationFrame(() => requestAnimationFrame(() => {
        disc.classList.add('spin');
        ball.classList.add('spin');
        disc.style.transform = rest;
      }));
      setTimeout(settle, SPIN_MS);
    }
  }
  return box;
}

function boardEl(ctx, slip, winner) {
  const playing = !ctx.round;
  const cell = (key, label, extra, style) => {
    const amount = slip.get(key);
    const won = winner != null && key === `straight:${winner}`;
    const el = h('button', {
      class: `cell ${extra} ${won ? 'winner' : ''}`, style, disabled: !playing,
      title: playing ? SLIP_HINT : '',
      ...slipHandlers(slip, key),
    }, label, amount ? h('span', { class: 'marker' }, chipLabel(amount)) : null);
    if (won) el.style.animationDelay = `${SPIN_MS}ms`;
    return el;
  };

  const cells = [h('div', {
    style: { gridColumn: '1', gridRow: '1 / span 3', display: 'flex', flexDirection: 'column', gap: '2px' },
  }, ['0', '00'].map((name) => cell(`straight:${name}`, name, 'green', { flex: '1' })))];
  for (let row = 0; row < 3; row += 1) {
    for (let column = 1; column <= 12; column += 1) {
      const number = column * 3 - row;
      cells.push(cell(`straight:${number}`, String(number), colorOf(ctx.table, String(number)),
        { gridColumn: String(column + 1), gridRow: String(row + 1) }));
    }
    cells.push(cell(`column:${3 - row}`, '2 to 1', 'outside column', { gridColumn: '14', gridRow: String(row + 1) }));
  }
  ['1st 12', '2nd 12', '3rd 12'].forEach((label, index) => {
    cells.push(cell(`dozen:${index + 1}`, label, 'outside', { gridColumn: `${2 + index * 4} / span 4`, gridRow: '4' }));
  });
  OUTSIDE.forEach(([key, label], index) => {
    const tint = key.endsWith(':Red') ? 'red' : '';
    cells.push(cell(key, label, `outside ${tint}`, { gridColumn: `${2 + index * 2} / span 2`, gridRow: '5' }));
  });
  return h('div', { class: 'board' }, cells);
}

function toBets(stakes) {
  return Object.entries(stakes).map(([key, amount]) => {
    const [kind, selection] = key.split(':');
    const numbered = kind === 'dozen' || kind === 'column';
    return { kind, selection: numbered ? Number(selection) : selection, amount };
  });
}

export function render(ctx, mount) {
  const { round } = ctx;
  const felt = h('div', { class: 'felt' });
  add(mount, felt);
  const slip = betSlip(ctx);
  if (!round) ctx.local.spun = false;

  add(felt, h('div', { class: 'roulette' }, wheelEl(ctx, round ? round.pocket : null),
    boardEl(ctx, slip, round ? round.pocket : null)));
  if (!round) {
    add(mount,
      betBar(ctx, slip, { label: 'Spin', onDeal: () => ctx.start({ bets: toBets(slip.stakes) }) }),
      h('p', { class: 'hint' }, `Each bet: ${credits(ctx.table.min_bet)} minimum. Click the board to place chips; right-click takes one back.`));
    return 0;
  }
  add(mount, resultPanel(ctx, round, { delay: SPIN_MS + 300, again: 'Spin again' }));
  return SPIN_MS + 300;
}
