import { add, h } from '../dom.js';
import { betBar, betSlip, handEl, late, lockedSpot, seatEl, settleRound, spotEl } from '../ui.js';

const WINNER_TEXT = { player: 'Player wins', banker: 'Banker wins', tie: 'Tie' };
// Nothing to do during the coup, so the finished table stays up longer than at the other card tables.
const HOLD_MS = 5000;

/* The bonus strip: Dragon 7 on the left, the Tie box in the middle, Panda 8 on the right. */
function stripEl(dragon, tie, panda) {
  return h('div', { class: 'spots bac-strip' },
    h('div', { class: 'bac-side' }, dragon), h('div', { class: 'bac-tie' }, tie), h('div', { class: 'bac-side' }, panda));
}

export function render(ctx, mount) {
  const { round, table } = ctx;
  const felt = h('div', { class: 'felt red cardfelt bac' });
  const bets = Object.fromEntries(table.layout.bets.map((bet) => [bet.key, bet]));
  const pays = (key) => `pays ${bets[key].pays}`;

  if (!round) {
    const slip = betSlip(ctx);
    const spot = (key) => spotEl(ctx, slip, key, bets[key].label, pays(key), { wide: true });
    add(mount, betBar(ctx, slip, { label: 'Deal', onDeal: () => ctx.start({ ...slip.stakes }) }), felt);
    add(felt,
      h('div', { class: 'hands bac-boxes' },
        seatEl('Player', null, [h('div', { class: 'hand' }), spot('player')], 'bac-player'),
        seatEl('Banker', null, [h('div', { class: 'hand' }), spot('banker')], 'bac-banker')),
      stripEl(spot('dragon7'), spot('tie'), spot('panda8')),
      h('div', { class: 'felt-legend' }, 'Closest to nine wins'),
      h('p', { class: 'hint' }, 'Dragon 7 and Panda 8 need a Player or Banker bet on the same coup.'));
    return 0;
  }

  // Dealt alternately: Player, Banker, Player, Banker, then any third cards.
  const player = handEl(ctx, 'player', round.player.cards, { start: 0, step: 800 });
  const banker = handEl(ctx, 'banker', round.banker.cards, { start: 400, step: 800 });
  const reveal = Math.max(player.until, banker.until) + 200;
  const placed = (key) => (round.stakes[key] ? lockedSpot(ctx, bets[key].label, round.stakes[key], pays(key)) : null);
  const crown = (key) => round.winner === key && late(h('div', { class: 'bac-win' }), reveal);
  const box = (name, key, side, dealt) => {
    const el = seatEl(name, null, [dealt.el, placed(key), crown(key)], `bac-${key}`);
    el.firstChild.append(late(h('span', { class: 'pill' }, `Total ${side.total}`), reveal));
    return el;
  };
  add(mount, felt);
  add(felt,
    h('div', { class: 'hands bac-boxes' }, box('Player', 'player', round.player, player), box('Banker', 'banker', round.banker, banker)),
    stripEl(placed('dragon7'), [placed('tie'), crown('tie')], placed('panda8')),
    late(h('div', { class: 'felt-legend bac-winner' }, WINNER_TEXT[round.winner]), reveal));
  settleRound(ctx, felt, round, { delay: reveal, hold: HOLD_MS });
  return reveal;
}
