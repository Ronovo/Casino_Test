import { add, credits, h } from '../dom.js';
import { SLIP_HINT, betBar, betSlip, late, resultPanel, slipHandlers } from '../ui.js';

const WINNER_MS = 11000;
// Real margins are a few percent of the race time; stretching them makes the finish readable on screen.
const GAP_STRETCH = 3;
const FINISH_AT = 0.92;
const GATE_PX = 46;
// Share of the distance covered at a given share of a horse's own running time: below 1 leads early, above 1 closes late.
const STYLE_CURVE = { front: 0.82, stalker: 1, closer: 1.22 };
const STYLE_NAMES = { front: 'Front-runner', stalker: 'Stalker', closer: 'Closer' };
const ORDINALS = ['1st', '2nd', '3rd', '4th', '5th', '6th', '7th', '8th', '9th', '10th', '11th', '12th'];
const KINDS = ['win', 'place', 'show'];

function formText(recent) {
  return recent.length ? recent.slice(-5).join('-') : 'first run';
}

function weightText(weight) {
  return weight ? `+${weight} lb` : 'level';
}

function swatch(runner, number) {
  return h('span', { class: 'silks', style: { background: runner.silks } }, number);
}

function conditionsText(race) {
  return `${race.distance} furlongs · ${race.going} going`;
}

function standingsEl(ctx, standings, raced) {
  return h('div', { class: 'panel leaderboard' },
    h('h3', null, `Season standings after ${raced} of ${ctx.table.layout.season_length} races`),
    h('table', { class: 'data' },
      h('thead', null, h('tr', null, ['', 'Horse', 'Runs', '1st', '2nd', '3rd', 'Points', 'Handicap', 'Last five']
        .map((title) => h('th', null, title)))),
      h('tbody', null, standings.map((row, index) => h('tr', { class: index === 0 && row.starts ? 'me' : '' },
        h('td', null, index + 1),
        h('td', null, swatch(row, ''), ' ', row.name),
        h('td', null, row.starts), h('td', null, row.firsts), h('td', null, row.seconds), h('td', null, row.thirds),
        h('td', null, h('strong', { class: 'gold' }, row.points)),
        h('td', { class: row.weight ? 'lose' : 'muted' }, weightText(row.weight)),
        h('td', { class: 'muted' }, formText(row.recent)))))));
}

function cardEl(ctx, slip) {
  const { runners } = ctx.betting;
  const priceCell = (runner, kind) => {
    const price = runner.odds[kind];
    const key = `${runner.key}|${kind}`;
    const amount = slip.get(key);
    return h('td', null, h('button', {
      class: `price ${amount ? 'on' : ''}`, disabled: !price,
      title: price ? SLIP_HINT : 'No price: too likely to be worth a bet',
      ...slipHandlers(slip, key),
    }, price || '-', amount ? h('span', { class: 'marker' }, amount) : null));
  };
  return h('table', { class: 'data race-card' },
    h('thead', null, h('tr', null, ['', 'Horse', 'Style', 'Handicap', 'Last five', 'Win', 'Place', 'Show']
      .map((title) => h('th', null, title)))),
    h('tbody', null, runners.map((runner, index) => h('tr', null,
      h('td', null, swatch(runner, index + 1)),
      h('td', null, h('strong', null, runner.name)),
      h('td', { class: 'muted' }, STYLE_NAMES[runner.style]),
      h('td', { class: runner.weight ? 'lose' : 'muted' }, weightText(runner.weight)),
      h('td', { class: 'muted' }, formText(runner.recent)),
      KINDS.map((kind) => priceCell(runner, kind))))));
}

function toBets(stakes) {
  return Object.entries(stakes).map(([key, amount]) => {
    const [horse, kind] = key.split('|');
    return { horse, kind, amount };
  });
}

function screenTimes(runners) {
  const fastest = Math.min(...runners.map((runner) => runner.time));
  return runners.map((runner) => WINNER_MS * (1 + GAP_STRETCH * (runner.time - fastest) / fastest));
}

function trackEl(ctx, round) {
  const times = screenTimes(round.runners);
  const last = Math.max(...times);
  const horses = [];
  const lanes = round.runners.map((runner, index) => {
    const badge = h('span', { class: `place-badge ${runner.position <= 3 ? 'paid' : ''}` }, ORDINALS[runner.position - 1]);
    const horse = h('div', { class: 'horse' }, h('span', { class: 'horse-icon' }, '🏇'), badge);
    horses.push(horse);
    return h('div', { class: 'lane' }, swatch(runner, index + 1), h('span', { class: 'lane-name' }, runner.name), horse);
  });
  const place = (elapsed) => {
    round.runners.forEach((runner, index) => {
      const share = Math.min(elapsed / times[index], 1.04);
      const covered = share <= 1 ? share ** STYLE_CURVE[runner.style] : share;
      horses[index].style.left = `calc(${GATE_PX}px + ${(covered * FINISH_AT).toFixed(4)} * (100% - ${GATE_PX}px))`;
      if (share >= 1) horses[index].classList.add('home');
    });
  };

  if (ctx.local.raced) {
    place(last * 1.04);
  } else {
    ctx.local.raced = true;
    place(0);
    const began = performance.now();
    const tick = (now) => {
      const elapsed = now - began;
      place(elapsed);
      if (elapsed < last * 1.04) requestAnimationFrame(tick);
    };
    requestAnimationFrame(tick);
  }
  return { el: h('div', { class: 'track' }, h('div', { class: 'finish-line', style: { left: `calc(${GATE_PX}px + ${FINISH_AT} * (100% - ${GATE_PX}px))` } }), lanes), until: last };
}

export function render(ctx, mount) {
  const { round, betting } = ctx;
  const felt = h('div', { class: 'felt turf' });
  add(mount, felt);

  if (!round) {
    ctx.local.raced = false;
    const slip = betSlip(ctx);
    // Stakes left over from the last race may point at prices the new card no longer offers.
    for (const key of Object.keys(slip.stakes)) {
      const [horse, kind] = key.split('|');
      if (!betting.runners.find((runner) => runner.key === horse)?.odds[kind]) delete slip.stakes[key];
    }
    add(felt,
      h('div', { class: 'felt-legend' }, `Season ${betting.season} · Race ${betting.race} of ${ctx.table.layout.season_length} · ${conditionsText(betting.conditions)}`),
      betting.champion && h('div', { class: 'muted' }, `🏆 Reigning champion: ${betting.champion}`),
      cardEl(ctx, slip));
    add(mount,
      betBar(ctx, slip, { label: 'Run the race', onDeal: () => ctx.start({ bets: toBets(slip.stakes) }) }),
      h('p', { class: 'hint' }, 'Pick a chip, then click any price to bet on it. Bet on as many horses as you like. Right-click takes a chip back.'),
      standingsEl(ctx, betting.standings, betting.race - 1));
    return 0;
  }

  const track = trackEl(ctx, round);
  const reveal = track.until + 500;
  add(felt,
    h('div', { class: 'felt-legend' }, `Season ${round.race.season} · Race ${round.race.number} · ${conditionsText(round.race)}`),
    track.el,
    round.season_over && late(h('div', { class: 'banner win' }, `🏆 ${round.season_over.champion} wins season ${round.season_over.season}!`), reveal));
  add(mount,
    resultPanel(ctx, round, { delay: reveal, again: 'Same bets, next race' }),
    late(standingsEl(ctx, round.standings, round.season_over ? ctx.table.layout.season_length : round.race.number), reveal));
  return reveal;
}
