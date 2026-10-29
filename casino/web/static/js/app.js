import { ApiError, api } from './api.js';
import { add, clear, credits, h, limits, signedCredits } from './dom.js';
import { chipEl } from './ui.js';
import * as baccarat from './games/baccarat.js';
import * as blackjack from './games/blackjack.js';
import * as gtn from './games/gtn.js';
import * as poker from './games/poker.js';
import * as racing from './games/racing.js';
import * as roulette from './games/roulette.js';

const GAMES = { blackjack, poker, baccarat, gtn, roulette, racing };
const ICONS = { blackjack: '🃏', poker: '♠️', baccarat: '🎴', gtn: '🔢', roulette: '🎡', racing: '🏇' };

const screen = document.getElementById('screen');
const topbar = document.getElementById('topbar');
const toasts = document.getElementById('toasts');
const modal = document.getElementById('modal');

const state = { session: null, player: null };
// Bumped on every navigation so a slow response can't draw over a newer screen.
let visit = 0;

// ------------------------------------------------------------------ feedback
function toast(message, kind = '', title = '') {
  const el = h('div', { class: `toast ${kind}` }, title && h('div', { class: 'title' }, title), message);
  toasts.append(el);
  setTimeout(() => el.remove(), kind === 'achievement-toast' ? 7000 : 4500);
}

function fail(error) {
  if (error instanceof ApiError && error.status === 401) {
    state.session = { ...state.session, user: null, character: null, characters: [] };
    route();
  }
  toast(error instanceof ApiError ? error.message : 'Something went wrong.', 'error');
  if (!(error instanceof ApiError)) console.error(error);
}

/* Take the player snapshot, unlocks and notices that come back with every floor reply.
   `delay` holds back anything that would give away a result before its animation has finished. */
function absorb(body, delay = 0) {
  if (!body.player) return;
  state.player = body.player;
  setTimeout(() => {
    drawTopbar();
    for (const unlocked of body.achievements || []) {
      toast(unlocked.description, 'achievement-toast', `★ ${unlocked.display_name}`);
    }
  }, delay);
  for (const notice of body.notices || []) toast(notice);
}

function showModal(...children) {
  add(clear(modal), h('div', { class: 'panel' }, children,
    h('div', { class: 'row', style: { marginTop: '18px' } },
      h('span', { class: 'spacer' }), h('button', { class: 'primary', onclick: closeModal }, 'Close'))));
  modal.hidden = false;
}

function closeModal() {
  modal.hidden = true;
}

modal.addEventListener('click', (event) => {
  if (event.target === modal) closeModal();
});

// ------------------------------------------------------------------ navigation
function go(hash) {
  if (location.hash === hash) route();
  else location.hash = hash;
}

function drawTopbar() {
  const { session, player } = state;
  topbar.hidden = !session.user;
  if (!session.user) return;
  add(clear(topbar), h('span', { class: 'brand', onclick: () => go('#/lobby') }, `♠ ${session.app}`));
  const seated = session.character != null && player;
  if (seated) {
    add(topbar, [
      h('span', { class: 'who' }, `${player.name} · ${player.difficulty}`),
      h('span', { class: 'spacer' }),
      h('span', { class: 'purse', title: 'Your chips' }, credits(player.credits)),
      h('button', { class: 'link', onclick: () => go('#/lobby') }, 'Tables'),
      h('button', { class: 'link', onclick: () => go('#/profile') }, 'Profile'),
      h('button', { class: 'link', onclick: () => go('#/cashier') }, 'Cashier'),
      h('button', { class: 'link', onclick: switchCharacter }, 'Switch character'),
    ]);
  } else {
    add(topbar, [h('span', { class: 'who' }, `Signed in as ${session.user}`), h('span', { class: 'spacer' })]);
  }
  add(topbar, h('button', { class: 'link', onclick: logout }, 'Log out'));
}

async function switchCharacter() {
  try {
    state.session = await api.post('characters/select', { id: null });
    state.player = null;
    go('#/characters');
  } catch (error) {
    fail(error);
  }
}

async function logout() {
  try {
    state.session = await api.post('logout');
    state.player = null;
    go('#/');
  } catch (error) {
    fail(error);
  }
}

const SCREENS = { lobby: lobbyScreen, table: tableScreen, profile: profileScreen, cashier: cashierScreen };

// Set by the table screen: tells the server the player got up, however they left the table.
let leaveTable = null;

async function route() {
  if (leaveTable) {
    const leaving = leaveTable;
    leaveTable = null;
    leaving();
  }
  visit += 1;
  closeModal();
  drawTopbar();
  if (!state.session.user) return state.session.portfolio_pending ? accountLinkScreen() : authScreen();
  if (state.session.character == null) return charactersScreen();
  const [name, argument] = location.hash.replace(/^#\/?/, '').split('/');
  try {
    await (SCREENS[name] || lobbyScreen)(decodeURIComponent(argument || ''), visit);
  } catch (error) {
    fail(error);
    if (error instanceof ApiError && error.status === 404) go('#/lobby');
  }
}

// ------------------------------------------------------------------ accounts
function securityFields() {
  const question = h('select', null, h('option', { value: '' }, 'Pick a question'),
    state.session.questions.map((q) => h('option', { value: q }, q)));
  const answer = h('input', { maxLength: 100, autocomplete: 'off' });
  const fields = [
    h('div', { class: 'field' }, h('label', null, 'Security question'), question),
    h('div', { class: 'field' }, h('label', null, 'Answer'), answer),
    h('p', { class: 'muted', style: { fontSize: '12px', marginBottom: '12px' } },
      'You need this answer to reset your password.'),
  ];
  return { question, answer, fields };
}

function authScreen(mode = 'login', notice = '') {
  const username = h('input', { autocomplete: 'username', maxLength: 20 });
  const password = h('input', { type: 'password', autocomplete: mode === 'login' ? 'current-password' : 'new-password' });
  const security = securityFields();
  const error = h('div', { class: 'error-text' });
  const submit = async (event) => {
    event.preventDefault();
    try {
      state.session = await api.post(mode, {
        username: username.value.trim(), password: password.value,
        question: security.question.value, answer: security.answer.value,
      });
      go('#/lobby');
    } catch (problem) {
      error.textContent = problem.message;
    }
  };
  add(clear(screen), h('div', { class: 'narrow' },
    h('div', { class: 'hero' },
      h('div', { class: 'suits' }, '♠', h('span', { class: 'red' }, '♥'), '♣', h('span', { class: 'red' }, '♦')),
      h('h1', null, state.session.app),
      h('p', { class: 'muted' }, 'Blackjack · Hold\'em · Baccarat · Roulette · Racing')),
    notice && h('p', { class: 'muted', style: { textAlign: 'center' } }, notice),
    state.session.portfolio && portfolioButton(),
    h('form', { class: 'panel', onsubmit: submit },
      h('div', { class: 'tabs' },
        h('button', { type: 'button', class: mode === 'login' ? 'on' : '', onclick: () => authScreen('login') }, 'Log in'),
        h('button', { type: 'button', class: mode === 'register' ? 'on' : '', onclick: () => authScreen('register') },
          'Create account')),
      h('div', { class: 'field' }, h('label', null, 'Username'), username),
      h('div', { class: 'field' }, h('label', null, 'Password'), password),
      mode === 'register' && h('p', { class: 'muted', style: { fontSize: '12px', marginBottom: '12px' } },
        '3 to 20 letters, digits, dashes or underscores. Passwords need at least 6 characters.'),
      mode === 'register' && security.fields,
      h('button', { class: state.session.portfolio ? '' : 'primary', type: 'submit', style: { width: '100%' } },
        mode === 'login' ? 'Log in' : 'Create account'),
      mode === 'login' && h('button', { type: 'button', class: 'link', style: { marginTop: '8px' }, onclick: resetScreen },
        'Forgot password?'),
      error)));
  username.focus();
}

let portfolioNameRequest = null;

// The portfolio account this browser is logged in to, or null when there is none or the portfolio can't be reached.
function portfolioName() {
  portfolioNameRequest ??= fetch(`${state.session.portfolio_url}/sso/me`,
    { credentials: 'include', signal: AbortSignal.timeout(5000) })
    .then((response) => (response.ok ? response.json() : {}))
    .then((data) => data.username || null)
    .catch(() => null);
  return portfolioNameRequest;
}

function portfolioButton() {
  const button = h('button', {
    class: 'primary', type: 'button', style: { width: '100%', marginBottom: '12px' },
    onclick: () => { location.href = '/sso/login'; },
  }, 'Log in with portfolio account');
  portfolioName().then((name) => {
    if (name) button.textContent = `Log in as ${name}`;
  });
  return button;
}

// The first portfolio login here: link a casino account the player already has, or make a new one.
function accountLinkScreen() {
  const name = state.session.portfolio_pending;
  const username = h('input', { autocomplete: 'username', maxLength: 20, value: name });
  const password = h('input', { type: 'password', autocomplete: 'current-password' });
  const error = h('div', { class: 'error-text' });
  const choose = async (path, data) => {
    error.textContent = '';
    try {
      state.session = await api.post(path, data);
      go('#/lobby');
    } catch (problem) {
      error.textContent = problem.message;
    }
  };
  const link = (event) => {
    event.preventDefault();
    choose('portfolio/link', { username: username.value.trim(), password: password.value });
  };
  add(clear(screen), h('div', { class: 'narrow' },
    h('form', { class: 'panel', onsubmit: link },
      h('h2', null, 'Link your account'),
      h('p', { class: 'muted' }, `This is the first time ${name} has logged in here. If you already have a casino `
        + 'account, log in to it once to link it. After that, your portfolio account opens it on any device.'),
      h('div', { class: 'field' }, h('label', null, 'Username'), username),
      h('div', { class: 'field' }, h('label', null, 'Password'), password),
      h('button', { class: 'primary', type: 'submit', style: { width: '100%' } }, 'Link this account'),
      h('button', { type: 'button', style: { width: '100%', marginTop: '8px' }, onclick: () => choose('portfolio/new') },
        'Make a new account'),
      h('button', { type: 'button', class: 'link', style: { marginTop: '8px' }, onclick: logout }, 'Cancel'),
      error)));
  password.focus();
}

// Two steps: the username brings up its security question, then the answer and a new password change it.
function resetScreen() {
  const username = h('input', { autocomplete: 'username', maxLength: 20 });
  const answer = h('input', { maxLength: 100, autocomplete: 'off' });
  const password = h('input', { type: 'password', autocomplete: 'new-password' });
  const question = h('p', null);
  const second = h('div', { hidden: true },
    question,
    h('div', { class: 'field' }, h('label', null, 'Answer'), answer),
    h('div', { class: 'field' }, h('label', null, 'New password'), password));
  const button = h('button', { class: 'primary', type: 'submit', style: { width: '100%' } }, 'Next');
  const error = h('div', { class: 'error-text' });
  const submit = async (event) => {
    event.preventDefault();
    error.textContent = '';
    try {
      if (second.hidden) {
        question.textContent = (await api.post('reset-question', { username: username.value.trim() })).question;
        username.readOnly = true;
        second.hidden = false;
        button.textContent = 'Reset password';
        answer.focus();
        return;
      }
      await api.post('reset-password', { username: username.value.trim(), answer: answer.value, password: password.value });
      authScreen('login', 'Password changed. Log in with your new password.');
    } catch (problem) {
      error.textContent = problem.message;
    }
  };
  add(clear(screen), h('div', { class: 'narrow' },
    h('form', { class: 'panel', onsubmit: submit },
      h('h2', null, 'Reset password'),
      h('div', { class: 'field' }, h('label', null, 'Username'), username),
      second,
      button,
      h('button', { type: 'button', class: 'link', style: { marginTop: '8px' }, onclick: () => authScreen('login') }, 'Back'),
      error)));
  username.focus();
}

function charactersScreen() {
  const { session } = state;
  const name = h('input', { maxLength: 30, placeholder: 'Who is going to be betting?' });
  const difficulty = h('select', null, session.difficulties.map((d) => h('option', { value: d.key }, d.label)));
  difficulty.value = 'Medium';
  const error = h('div', { class: 'error-text' });
  const sit = async (request) => {
    try {
      state.session = await request;
      go('#/lobby');
    } catch (problem) {
      error.textContent = problem.message;
    }
  };
  add(clear(screen),
    h('h2', null, 'Who\'s playing?'),
    h('p', { class: 'muted', style: { margin: '4px 0 18px' } },
      'Each character has its own chips, record and achievements.'),
    h('div', { class: 'grid' }, session.characters.map((character) => h('button', {
      class: 'tile', onclick: () => sit(api.post('characters/select', { id: character.id })),
    }, h('span', { class: 'icon' }, '🎩'), h('h3', null, character.name),
       h('span', { class: 'muted' }, character.difficulty),
       h('span', { class: 'limits gold' }, credits(character.credits))))),
    h('div', { class: 'section-title' }, h('h2', null, 'New character')),
    h('form', {
      class: 'panel', style: { maxWidth: '460px' },
      onsubmit: (event) => {
        event.preventDefault();
        sit(api.post('characters', { name: name.value, difficulty: difficulty.value }));
      },
    },
      h('div', { class: 'field' }, h('label', null, 'Name'), name),
      h('div', { class: 'field' }, h('label', null, 'Difficulty (starting chips)'), difficulty),
      h('button', { class: 'primary', type: 'submit' }, 'Sit down'), error));
}

// ------------------------------------------------------------------ lobby
async function lobbyScreen(_, mine) {
  const body = await api.get('lobby');
  if (mine !== visit) return;
  absorb(body);
  const { player } = body;
  const tiles = body.tables.map((table) => {
    const short = !table.in_progress && player.credits < table.min_buy_in;
    return h('button', {
      class: 'tile', disabled: short, onclick: () => go(`#/table/${encodeURIComponent(table.key)}`),
      title: short ? `You need at least ${credits(table.min_buy_in)} to sit here` : '',
    },
      table.in_progress && h('span', { class: 'badge' }, 'Round in progress'),
      h('span', { class: 'icon' }, ICONS[table.game] || '🎲'),
      h('h3', null, table.title),
      h('span', { class: 'muted' }, table.description),
      h('span', { class: 'limits' }, `Limits ${limits(table)}`));
  });
  add(clear(screen),
    player.broke && h('div', { class: 'notice' },
      'You can\'t afford any table. You can start over with fresh starting chips.',
      h('button', { class: 'primary', onclick: startOver }, 'Start over')),
    h('div', { class: 'section-title' }, h('h2', null, 'Casino Floor'),
      h('span', { class: 'muted' }, `Welcome, ${player.name}. You have ${credits(player.credits)} in chips.`)),
    h('div', { class: 'grid' }, tiles));
}

async function startOver() {
  try {
    absorb(await api.post('start-over'));
    route();
  } catch (error) {
    fail(error);
  }
}

// ------------------------------------------------------------------ profile
async function profileScreen(_, mine) {
  const body = await api.get('profile');
  if (mine !== visit) return;
  absorb(body);
  const { player } = body;
  const stats = body.stats.length
    ? h('table', { class: 'data' },
      h('thead', null, h('tr', null, ['Game', 'Won', 'Lost', 'Push', 'Net', 'Best win'].map((t) => h('th', null, t)))),
      h('tbody', null, body.stats.map((row) => h('tr', null,
        h('td', null, row.game), h('td', null, row.wins), h('td', null, row.losses), h('td', null, row.pushes),
        h('td', { class: row.net_credits > 0 ? 'win' : row.net_credits < 0 ? 'lose' : '' }, signedCredits(row.net_credits)),
        h('td', null, credits(row.biggest_win))))))
    : h('p', { class: 'muted' }, 'No games played yet.');
  const categories = body.categories.map((category) => {
    const unlocked = category.items.filter((item) => item.unlocked).length;
    return [
      h('div', { class: 'section-title' }, h('h3', null, category.category),
        h('span', { class: 'muted' }, `${unlocked}/${category.items.length}`)),
      h('div', { class: 'achievements' }, category.items.map((item) => (item.unlocked
        ? h('div', { class: 'achievement' }, h('div', { class: 'name' }, `★ ${item.display_name}`),
          h('div', null, item.description), h('div', { class: 'when' }, item.date_unlocked))
        : h('div', { class: 'achievement locked' }, h('div', { class: 'name' }, '☆ Hidden achievement'),
          h('div', null, 'Keep playing to find out.'))))),
    ];
  });
  add(clear(screen),
    h('div', { class: 'section-title' }, h('h2', null, player.name),
      h('span', { class: 'muted' }, `${player.difficulty} · net worth ${credits(player.credits)}`)),
    player.broke && h('div', { class: 'notice' }, 'You can\'t afford any table.',
      h('button', { class: 'primary', onclick: startOver }, 'Start over with fresh chips')),
    h('div', { class: 'panel' }, h('h3', null, 'Record'), stats),
    h('div', { class: 'section-title' }, h('h2', null, 'Achievements')),
    categories);
}

// ------------------------------------------------------------------ cashier
async function cashierScreen(_, mine) {
  const body = await api.get('cashier');
  if (mine !== visit) return;
  absorb(body);
  drawCashier();
}

function drawCashier() {
  const { chips } = state.player;
  const values = state.session.chip_values;
  const colors = Object.keys(values);
  const smallerTotal = (color) => colors.filter((c) => values[c] < values[color])
    .reduce((sum, c) => sum + chips[c] * values[c], 0);
  const exchange = async (data) => {
    try {
      absorb(await api.post('cashier', data));
      drawCashier();
    } catch (error) {
      fail(error);
    }
  };

  const breakable = colors.filter((color) => values[color] > values[colors[0]] && chips[color] > 0);
  const breakColor = h('select', null, breakable.map((c) => h('option', { value: c }, `${c} (${values[c]}) ×${chips[c]}`)));
  const breakInto = h('select');
  const fillInto = () => add(clear(breakInto), colors.filter((c) => values[c] < values[breakColor.value])
    .map((c) => h('option', { value: c }, `${c} (${values[c]})`)));
  breakColor.addEventListener('change', fillInto);
  if (breakable.length) fillInto();
  const breakCount = h('input', { type: 'number', min: 1, value: 1 });

  const upTargets = colors.filter((color) => smallerTotal(color) >= values[color]);
  const upInto = h('select', null, upTargets.map((c) => h('option', { value: c },
    `${c} (${values[c]}), up to ${Math.floor(smallerTotal(c) / values[c])}`)));
  const upCount = h('input', { type: 'number', min: 1, value: 1 });

  add(clear(screen),
    h('div', { class: 'section-title' }, h('h2', null, 'Chip Exchange'),
      h('span', { class: 'muted' }, 'Trade chips for other colors. Your total never changes.')),
    h('div', { class: 'panel row', style: { gap: '26px', justifyContent: 'center' } }, colors.map((color) =>
      h('div', { class: 'seat' }, chipEl(color, values[color]), h('strong', null, `×${chips[color]}`),
        h('span', { class: 'muted' }, color)))),
    h('div', { class: 'grid', style: { marginTop: '18px' } },
      h('form', {
        class: 'panel',
        onsubmit: (event) => {
          event.preventDefault();
          exchange({ action: 'break', color: breakColor.value, into: breakInto.value, count: Number(breakCount.value) });
        },
      }, h('h3', null, 'Break chips'),
        breakable.length ? [
          h('div', { class: 'field' }, h('label', null, 'Break'), breakColor),
          h('div', { class: 'field' }, h('label', null, 'How many'), breakCount),
          h('div', { class: 'field' }, h('label', null, 'Into'), breakInto),
          h('button', { class: 'primary', type: 'submit' }, 'Break'),
        ] : h('p', { class: 'muted' }, 'You have no chips bigger than White to break.')),
      h('form', {
        class: 'panel',
        onsubmit: (event) => {
          event.preventDefault();
          exchange({ action: 'color_up', into: upInto.value, count: Number(upCount.value) });
        },
      }, h('h3', null, 'Color up'),
        upTargets.length ? [
          h('div', { class: 'field' }, h('label', null, 'Into'), upInto),
          h('div', { class: 'field' }, h('label', null, 'How many'), upCount),
          h('button', { class: 'primary', type: 'submit' }, 'Color up'),
        ] : h('p', { class: 'muted' }, 'You don\'t have enough small chips to color up.'))));
}

// ------------------------------------------------------------------ tables
function showRules(table) {
  showModal(
    h('h2', null, table.title),
    h('p', { class: 'muted' }, `Table limits ${limits(table)}`),
    table.rules.map((page) => h('div', { class: 'rules-page' }, page.map((line) => h('p', null, line)))),
    h('h3', { style: { marginTop: '18px' } }, 'Payouts'),
    h('div', { class: 'paytable' }, table.paytable.map((section) => h('div', null,
      section.title && h('strong', null, section.title),
      section.rows.map((row) => h('div', { class: 'pay-row' }, h('span', null, row[0]), h('span', null, row[1])))))));
}

async function tableScreen(key, mine) {
  const body = await api.get(`tables/${encodeURIComponent(key)}`);
  if (mine !== visit) return;
  absorb(body);
  const game = GAMES[body.table.game];
  const mount = h('div');
  const smallest = Object.values(state.session.chip_values).find((value) => value >= body.table.min_bet) || 1;

  const ctx = {
    table: body.table,
    betting: body.betting,
    round: body.round,
    player: state.player,
    chipValues: state.session.chip_values,
    // UI state that outlives a render: stakes being built, the selected chip, cards already on the felt.
    local: { stakes: {}, chip: smallest, cards: {}, lastBets: null },
    busy: false,
    toast,
    rerender() {
      ctx.player = state.player;
      return game.render(ctx, clear(mount)) || 0;
    },
    start: (bets) => send('start', { bets }, () => {
      ctx.local.lastBets = bets;
      ctx.local.cards = {};
    }),
    act: (action) => send('act', { action }),
    repeat: () => ctx.start(ctx.local.lastBets),
    newRound() {
      ctx.round = null;
      ctx.local.cards = {};
      ctx.rerender();
    },
  };

  async function send(verb, data, before) {
    if (ctx.busy) return;
    ctx.busy = true;
    try {
      const reply = await api.post(`tables/${encodeURIComponent(key)}/${verb}`, data);
      if (mine !== visit) return;
      if (before) before();
      ctx.round = reply.round;
      ctx.betting = reply.betting;
      state.player = reply.player;
      ctx.busy = false;
      absorb(reply, ctx.rerender());
    } catch (error) {
      fail(error);
    } finally {
      ctx.busy = false;
    }
  }

  leaveTable = () => {
    if (!ctx.round || ctx.round.finished) {
      api.post(`tables/${encodeURIComponent(key)}/leave`).then((reply) => absorb(reply), fail);
    }
  };
  const leave = () => go('#/lobby');

  add(clear(screen),
    h('div', { class: 'table-head' },
      h('button', { onclick: leave }, '← Tables'),
      h('h2', null, body.table.title),
      h('span', { class: 'muted' }, `Limits ${limits(body.table)}`),
      h('span', { class: 'spacer' }),
      h('button', { onclick: () => showRules(body.table) }, 'Rules & payouts')),
    mount);
  ctx.rerender();
}

// ------------------------------------------------------------------ boot
window.addEventListener('hashchange', route);
api.get('session').then((session) => {
  state.session = session;
  document.title = session.app;
  route();
}).catch(() => {
  add(clear(screen), h('div', { class: 'narrow panel' }, 'The casino is closed. Start the server and reload.'));
});
