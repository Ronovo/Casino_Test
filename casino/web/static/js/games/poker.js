import { add, h } from '../dom.js';
import { actionBar, betBar, betSlip, handEl, lockedSpot, resultPanel, seatEl, spotEl } from '../ui.js';

const BET_NAMES = { ante: 'Ante', blind: 'Blind', play: 'Play', trips: 'Trips', pairs: 'Pairs Bonus' };

/* A spot printed on the felt with nothing on it yet. */
function ghostSpot(name) {
  return h('div', { class: 'spot ghost' }, h('span', { class: 'spot-name' }, name));
}

/* The printed UTH layout: Trips on the left, Ante, Blind and Play in the middle, Pairs Bonus on the right. */
function spotsEl(trips, core, pairs) {
  return h('div', { class: 'spots uth-spots' },
    h('div', { class: 'uth-side' }, trips), h('div', { class: 'uth-core' }, core), h('div', { class: 'uth-side' }, pairs));
}

function boardEl(body) {
  return h('div', { class: 'uth-board' }, body,
    h('div', { class: 'uth-strip' }, h('span', { class: 'flop' }, 'Flop'), h('span', null, 'Turn'), h('span', null, 'River')));
}

export function render(ctx, mount) {
  const { round } = ctx;
  const felt = h('div', { class: 'felt blue cardfelt uth' });
  add(mount, felt);

  if (!round) {
    const slip = betSlip(ctx, {
      cost: (s) => (s.ante || 0) * 2 + (s.trips || 0) + (s.pairs || 0),
      reserve: (s) => s.ante || 0,
    });
    add(felt,
      h('div', { class: 'felt-legend' }, 'Dealer qualifies with a pair or better'),
      boardEl(h('div', { class: 'hand spread uth-slots' }, Array.from({ length: 5 }, () => h('div', { class: 'uth-slot' })))),
      spotsEl(
        spotEl(ctx, slip, 'trips', 'Trips', 'side bet'),
        [spotEl(ctx, slip, 'ante', 'Ante', 'pays 1:1'), lockedSpot(ctx, 'Blind', slip.get('ante'), 'matches Ante'), ghostSpot('Play')],
        spotEl(ctx, slip, 'pairs', 'Pairs Bonus', 'side bet')),
      h('div', { class: 'felt-legend' }, 'Raise early for a bigger Play bet: 4x · 3x · 2x · 1x'));
    add(mount,
      betBar(ctx, slip, {
        label: 'Deal',
        ready: slip.get('ante') > 0,
        onDeal: () => ctx.start({ ante: slip.get('ante'), trips: slip.get('trips'), pairs: slip.get('pairs') }),
      }),
      h('p', { class: 'hint' }, 'The Ante places a matching Blind, and you need one more Ante in your rack for a Play bet. Trips and Pairs Bonus are optional.'));
    return 0;
  }

  const opening = !ctx.local.cards.player;
  const player = handEl(ctx, 'player', round.player, { step: 300 });
  const board = handEl(ctx, 'board', round.board, { start: opening ? 750 : 0, step: opening ? 110 : 260, spread: true });
  const dealer = handEl(ctx, 'dealer', round.dealer, { start: opening ? 150 : board.until, step: opening ? 300 : 350 });
  const reveal = round.finished ? dealer.until + 300 : 0;
  const placed = (key) => (round.bets[key] ? lockedSpot(ctx, BET_NAMES[key], round.bets[key]) : ghostSpot(BET_NAMES[key]));

  add(felt,
    seatEl('Dealer', round.dealer_hand && { label: round.dealer_hand }, dealer.el, 'dealer'),
    boardEl(seatEl(round.street, null, board.el)),
    seatEl('You', { label: round.player_hand }, player.el),
    spotsEl(placed('trips'), ['ante', 'blind', 'play'].map(placed), placed('pairs')));
  if (round.finished) add(mount, resultPanel(ctx, round, { delay: reveal }));
  else add(mount, actionBar(ctx, round));
  return reveal;
}
