import { add, credits, h } from '../dom.js';
import { betBar, betSlip, late, settleRound } from '../ui.js';

const DIGIT_STEP = 350;

function sealedEl(digits, number) {
  const text = number == null ? '?'.repeat(digits) : String(number).padStart(digits, '0');
  return h('div', { class: 'sealed' }, [...text].map((digit, index) => {
    const el = h('div', { class: `digit ${number == null ? '' : 'shown'}` }, digit);
    if (number != null) el.style.animationDelay = `${index * DIGIT_STEP}ms`;
    return el;
  }));
}

function numberInput(picks, field, index, low, high, placeholder) {
  return h('input', {
    type: 'number', min: low, max: high, placeholder, value: index == null ? picks[field] : picks[field][index],
    oninput: (event) => {
      if (index == null) picks[field] = event.target.value;
      else picks[field][index] = event.target.value;
    },
  });
}

function toggles(ctx, picks, field, options) {
  return options.map(([value, label]) => h('button', {
    class: `toggle ${picks[field] === value ? 'on' : ''}`,
    onclick: () => {
      picks[field] = value;
      ctx.rerender();
    },
  }, label));
}

function stakeBox(slip, key) {
  return h('div', { class: 'stake-box' },
    h('button', { onclick: () => slip.remove(key), disabled: !slip.get(key), title: 'Take a chip back' }, '−'),
    h('strong', { class: 'gold' }, credits(slip.get(key))),
    h('button', { onclick: () => slip.add(key), title: 'Add the selected chip' }, '+'));
}

function freshChoices(difficulty) {
  return { difficulty, picks: { pick: '', range: '', lucky: ['', ''], high_low: null, even_odd: null } };
}

function collect(slip, picks, difficulty) {
  const whole = (text) => (/^\d+$/.test(String(text).trim()) ? Number(text) : null);
  const selections = {
    pick: whole(picks.pick), range: whole(picks.range), high_low: picks.high_low, even_odd: picks.even_odd,
    lucky: [whole(picks.lucky[0]), whole(picks.lucky[1])],
  };
  const bets = {};
  for (const [kind, amount] of Object.entries(slip.stakes)) {
    const selection = selections[kind];
    if (selection == null || (kind === 'lucky' && selection.includes(null))) {
      return { problem: 'Choose what you are betting on for every bet with chips on it.' };
    }
    bets[kind] = { selection, amount };
  }
  return { bets: { difficulty: difficulty.name, bets } };
}

export function render(ctx, mount) {
  const { round, table } = ctx;
  const { difficulties } = table.layout;
  const local = ctx.local;
  local.gtn ||= freshChoices(difficulties[0].name);
  const difficulty = difficulties.find((d) => d.name === (round ? round.difficulty : local.gtn.difficulty));
  const { picks } = local.gtn;
  const felt = h('div', { class: 'felt purple' });

  if (round) {
    const reveal = difficulty.digits * DIGIT_STEP + 300;
    add(mount, felt);
    add(felt,
      h('div', { class: 'felt-legend' }, `${difficulty.name}: 1 to ${difficulty.max_number.toLocaleString('en-US')}`),
      sealedEl(difficulty.digits, round.number),
      late(h('div', { class: 'felt-legend reveal' }, `The number is ${round.number.toLocaleString('en-US')}`), reveal));
    settleRound(ctx, felt, round, { delay: reveal, again: 'Same bets, new number' });
    return reveal;
  }

  const slip = betSlip(ctx);
  const top = difficulty.max_number;
  const pays = difficulty.ratios;
  const row = (key, name, payText, controls) => h('div', { class: 'bet-row' },
    h('div', null, h('strong', null, name), h('div', { class: 'pays' }, payText)),
    h('div', { class: 'picks' }, controls),
    stakeBox(slip, key));

  add(mount,
    betBar(ctx, slip, {
      label: 'Reveal the number',
      onDeal: () => {
        const { bets, problem } = collect(slip, picks, difficulty);
        if (problem) ctx.toast(problem, 'error');
        else ctx.start(bets);
      },
    }),
    felt,
    h('p', { class: 'hint' }, 'Pick a chip above, then use + and − on each bet you want to make.'));
  add(felt,
    sealedEl(difficulty.digits, null),
    h('div', { class: 'bet-rows' },
      row('pick', 'Pick a Number', `exact ${pays.exact} · within ${difficulty.scale.toLocaleString('en-US')} pays ${pays.close}`,
        numberInput(picks, 'pick', null, 1, top, `1 to ${top}`)),
      row('high_low', 'High / Low', `pays ${pays.high_low}`, toggles(ctx, picks, 'high_low', [
        ['Low', `Low (1 to ${difficulty.half.toLocaleString('en-US')})`],
        ['High', `High (${(difficulty.half + 1).toLocaleString('en-US')} and up)`]])),
      row('even_odd', 'Even / Odd', `pays ${pays.even_odd}`, toggles(ctx, picks, 'even_odd', [['Even', 'Even'], ['Odd', 'Odd']])),
      row('range', 'Range', `${difficulty.range_size.toLocaleString('en-US')} numbers in a row · pays ${pays.range}`,
        numberInput(picks, 'range', null, 1, top - difficulty.range_size + 1, 'first number')),
      row('lucky', 'Lucky Combo', `#1 pays ${pays.lucky_1} · #2 pays ${pays.lucky_2}`, [
        numberInput(picks, 'lucky', 0, 1, top, 'lucky #1'), numberInput(picks, 'lucky', 1, 1, top, 'lucky #2')])),
    h('div', { class: 'row center difficulty' }, difficulties.map((d) => h('button', {
      class: `toggle ${d.name === difficulty.name ? 'on' : ''}`,
      onclick: () => {
        local.gtn = freshChoices(d.name);
        slip.clear();
      },
    }, `${d.name}: 1 to ${d.max_number.toLocaleString('en-US')}`))));
  return 0;
}
