import { add, credits, h } from '../dom.js';
import { actionBar, betBar, betSlip, handEl, late, lockedSpot, seatEl, settleRound, spotEl } from '../ui.js';

/* One span per character so the CSS can rotate each onto an arc. */
function arcText(text) {
  const chars = [...text];
  return h('div', { class: 'bj-arc', style: { '--mid': String((chars.length - 1) / 2) } },
    chars.map((ch, index) => h('span', { style: { '--i': String(index) } }, ch)));
}

const HOLD_MS = 2500;

function legend(table) {
  return h('div', { class: 'bj-legend' },
    arcText(`Blackjack pays ${table.layout.natural.replace(':', ' to ')}`),
    h('div', { class: 'felt-legend bj-rule' }, 'Dealer must hit soft 17 · Insurance pays 2 to 1'));
}

export function render(ctx, mount) {
  const { round, table } = ctx;
  const felt = h('div', { class: 'felt cardfelt bj' });

  if (!round) {
    const slip = betSlip(ctx);
    add(mount,
      betBar(ctx, slip, { label: 'Deal', onDeal: () => ctx.start({ bet: slip.get('bet') }) }),
      felt,
      h('p', { class: 'hint' }, 'Pick a chip, then click the betting circle. Right-click takes a chip back.'));
    add(felt, h('div', { class: 'spots bj-curve' }, spotEl(ctx, slip, 'bet', 'Your bet')),
      seatEl('Dealer', null, h('div', { class: 'hand' }), 'dealer'), legend(table));
    return 0;
  }

  // Player cards land first; the dealer's are offset so the four opening cards alternate.
  let playerUntil = 0;
  const mid = (round.hands.length - 1) / 2;
  const hands = round.hands.map((hand, index) => {
    const dealt = handEl(ctx, `hand${index}`, hand.cards, { step: 300 });
    playerUntil = Math.max(playerUntil, dealt.until);
    const label = round.hands.length > 1 ? hand.name : 'You';
    const state = hand.active ? 'active' : round.hands.length > 1 && !round.finished ? 'waiting' : '';
    const seat = seatEl(label, hand, dealt.el, state);
    seat.style.setProperty('--fan', String(index - mid));
    seat.append(lockedSpot(ctx, hand.status || 'Bet', hand.bet));
    return seat;
  });
  const opening = !ctx.local.cards.dealer;
  const dealer = handEl(ctx, 'dealer', round.dealer.cards, { start: opening ? 150 : playerUntil, step: opening ? 300 : 500 });
  const reveal = round.finished ? dealer.until + 250 : 0;
  const dealerSeat = seatEl('Dealer', null, dealer.el, 'dealer');
  dealerSeat.firstChild.append(late(h('span', { class: `pill ${round.dealer.state}` }, round.dealer.label), reveal));
  if (round.insurance) dealerSeat.append(h('div', { class: 'bj-insurance' }, lockedSpot(ctx, 'Insurance', round.insurance)));

  if (!round.finished) add(mount, actionBar(ctx, round));
  add(mount, felt);
  add(felt, h('div', { class: 'hands bj-curve' }, hands), dealerSeat, legend(table));
  if (round.finished) {
    settleRound(ctx, felt, round, { delay: reveal, hold: HOLD_MS, again: `Deal again (${credits(ctx.local.lastBets?.bet || 0)})` });
  }
  return reveal;
}
