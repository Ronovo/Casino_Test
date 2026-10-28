import { add, h } from '../dom.js';
import { betBar, betSlip, handEl, late, lockedSpot, resultPanel, seatEl, spotEl } from '../ui.js';

const WINNER_TEXT = { player: 'Player wins', banker: 'Banker wins', tie: 'Tie' };

export function render(ctx, mount) {
  const { round, table } = ctx;
  const felt = h('div', { class: 'felt red' });
  add(mount, felt);
  const pays = Object.fromEntries(table.layout.bets.map((bet, index) => [bet.key, table.paytable[0].rows[index][1]]));

  if (!round) {
    const slip = betSlip(ctx);
    add(felt,
      h('div', { class: 'hands' }, seatEl('Player', null, h('div', { class: 'hand' })),
        seatEl('Banker', null, h('div', { class: 'hand' }))),
      h('div', { class: 'felt-legend' }, 'Closest to nine wins'),
      h('div', { class: 'spots' }, table.layout.bets.map((bet) =>
        spotEl(ctx, slip, bet.key, bet.label, `pays ${pays[bet.key]}`, { wide: true }))));
    add(mount,
      betBar(ctx, slip, { label: 'Deal', onDeal: () => ctx.start({ ...slip.stakes }) }),
      h('p', { class: 'hint' }, 'Dragon 7 and Panda 8 need a Player or Banker bet on the same coup.'));
    return 0;
  }

  // Dealt alternately: Player, Banker, Player, Banker, then any third cards.
  const player = handEl(ctx, 'player', round.player.cards, { start: 0, step: 800 });
  const banker = handEl(ctx, 'banker', round.banker.cards, { start: 400, step: 800 });
  const reveal = Math.max(player.until, banker.until) + 200;
  const seat = (name, side, dealt) => {
    const el = seatEl(name, null, dealt.el);
    el.firstChild.append(late(h('span', { class: 'pill' }, `Total ${side.total}`), reveal));
    return el;
  };
  add(felt,
    h('div', { class: 'hands' }, seat('Player', round.player, player), seat('Banker', round.banker, banker)),
    late(h('div', { class: 'felt-legend' }, WINNER_TEXT[round.winner]), reveal),
    h('div', { class: 'spots' }, table.layout.bets.filter((bet) => round.stakes[bet.key]).map((bet) =>
      lockedSpot(ctx, bet.label, round.stakes[bet.key], `pays ${pays[bet.key]}`))));
  add(mount, resultPanel(ctx, round, { delay: reveal }));
  return reveal;
}
