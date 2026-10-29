import { add, credits, h } from '../dom.js';
import { actionBar, betBar, betSlip, handEl, late, lockedSpot, resultPanel, seatEl, spotEl } from '../ui.js';

export function render(ctx, mount) {
  const { round, table } = ctx;
  const felt = h('div', { class: 'felt' });
  add(mount, felt);
  const legend = h('div', { class: 'felt-legend' }, `Blackjack pays ${table.layout.natural.replace(':', ' to ')}`);

  if (!round) {
    const slip = betSlip(ctx);
    add(felt, seatEl('Dealer', null, h('div', { class: 'hand' })), legend,
      h('div', { class: 'spots' }, spotEl(ctx, slip, 'bet', 'Your bet')));
    add(mount,
      betBar(ctx, slip, { label: 'Deal', onDeal: () => ctx.start({ bet: slip.get('bet') }) }),
      h('p', { class: 'hint' }, 'Pick a chip, then click the betting circle. Right-click takes a chip back.'));
    return 0;
  }

  // Player cards land first; the dealer's are offset so the four opening cards alternate.
  let playerUntil = 0;
  const hands = round.hands.map((hand, index) => {
    const dealt = handEl(ctx, `hand${index}`, hand.cards, { step: 300 });
    playerUntil = Math.max(playerUntil, dealt.until);
    const label = round.hands.length > 1 ? hand.name : 'You';
    const state = hand.active ? 'active' : round.hands.length > 1 && !round.finished ? 'waiting' : '';
    const seat = seatEl(label, hand, dealt.el, state);
    seat.append(lockedSpot(ctx, hand.status || 'Bet', hand.bet));
    return seat;
  });
  const opening = !ctx.local.cards.dealer;
  const dealer = handEl(ctx, 'dealer', round.dealer.cards, { start: opening ? 150 : playerUntil, step: opening ? 300 : 500 });
  const reveal = round.finished ? dealer.until + 250 : 0;
  const dealerSeat = seatEl('Dealer', null, dealer.el);
  dealerSeat.firstChild.append(late(h('span', { class: `pill ${round.dealer.state}` }, round.dealer.label), reveal));

  add(felt, dealerSeat, legend, h('div', { class: 'hands' }, hands));
  if (round.finished) add(mount, resultPanel(ctx, round, { delay: reveal, again: `Deal again (${credits(ctx.local.lastBets?.bet || 0)})` }));
  else add(mount, actionBar(ctx, round));
  return reveal;
}
