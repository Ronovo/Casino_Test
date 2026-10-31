import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { CHIP_VALUES, byText, card, click, fakeServer, player, reply } from './helpers.js';

const PAGE = '<header id="topbar" hidden></header><main id="screen"></main>'
  + '<div id="toasts" aria-live="polite"></div><div id="modal" hidden></div>';
const CHARACTER = { id: 1, name: 'Lucky', difficulty: 'Medium', credits: 1000 };
const SEATED = { user: 'Ronovo', character: 1, characters: [CHARACTER] };
const TABLES = [
  { key: 'blackjack', game: 'blackjack', title: 'Blackjack', description: 'Classic', min_bet: 1, max_bet: 100,
    min_buy_in: 1, in_progress: true },
  { key: 'high_roller', game: 'poker', title: 'High Roller', description: 'Big', min_bet: 500, max_bet: null,
    min_buy_in: 1500, in_progress: false },
  { key: 'mystery', game: 'craps', title: 'Mystery', description: 'Unknown', min_bet: 1, max_bet: 10, min_buy_in: 1,
    in_progress: false },
];
const BLACKJACK = { key: 'blackjack', game: 'blackjack', title: 'Blackjack', description: '', min_bet: 1,
  max_bet: 100, min_buy_in: 1, rules: [['Get closer to 21 than the dealer.']], layout: { natural: '3:2' },
  paytable: [{ title: null, rows: [['Win', '1:1']] }, { title: 'Bonuses', rows: [['Any other 21', '2:1']] }] };
const HAND = { name: 'Hand', cards: [card('10S'), card('6H')], bet: 1, status: '', active: true, label: '16',
  state: '' };
const IN_PLAY = { finished: false, actions: [{ id: 'stand', label: 'Stand' }], hands: [HAND],
  dealer: { cards: [card('9C'), null], label: 'Showing 9', state: '' } };
const DONE = { finished: true, actions: [], hands: [{ ...HAND, active: false }],
  dealer: { cards: [card('9C'), card('8D')], label: '17', state: '' },
  result: { net: 1, notes: ['Dealer stands on 17.'], settlements: [] } };
// Time for the dealer's hole card to turn (500ms), the pause after it and the hold on the finished table before
// the result takes the felt's place. A fresh deal lands four cards first, so it takes longer.
const HOLD = 2500;
const REVEAL = 800 + HOLD;
const REDEAL = 1100 + HOLD;

const listeners = [];
let server;

beforeEach(() => {
  const listen = window.addEventListener;
  vi.spyOn(window, 'addEventListener').mockImplementation(function track(type, listener, options) {
    listeners.push([type, listener, options]);
    return listen.call(this, type, listener, options);
  });
});

afterEach(async () => {
  vi.useRealTimers();
  await settle();
  for (const [type, listener, options] of listeners.splice(0)) window.removeEventListener(type, listener, options);
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

function session(overrides = {}) {
  return { app: "Ronovo's Casino", user: null, characters: [], character: null, portfolio: false,
    portfolio_url: null, portfolio_pending: null, questions: ['Pet?', 'City?'], chip_values: CHIP_VALUES,
    difficulties: [{ key: 'Easy', label: 'Easy - 10,000 credits' }, { key: 'Medium', label: 'Medium - 1,000 credits' }],
    ...overrides };
}

function floor(extra = {}, playerOverrides = {}) {
  return { player: player(playerOverrides), achievements: [], notices: [], ...extra };
}

function table(round = null, info = BLACKJACK) {
  return floor({ table: info, betting: {}, round });
}

function deferred() {
  let resolve;
  const promise = new Promise((done) => { resolve = done; });
  return { promise, resolve };
}

async function settle() {
  for (let i = 0; i < 8; i += 1) await new Promise((resolve) => setTimeout(resolve, 0));
}

async function boot({ hash = '', routes = {}, ...overrides } = {}) {
  document.body.innerHTML = PAGE;
  history.replaceState(null, '', `/${hash}`);
  server = fakeServer({ 'GET session': session(overrides), 'GET lobby': floor({ tables: TABLES }), ...routes });
  vi.resetModules();
  await import('../../casino/web/static/js/app.js');
  await settle();
}

async function visit(hash) {
  location.hash = hash;
  await settle();
}

function $(selector) {
  return document.querySelector(selector);
}

function button(text, root = document) {
  return byText(root, 'button', text);
}

function fill(label, value) {
  const field = byText(document, '.field', label);
  const input = field.querySelector('input, select');
  input.value = value;
  input.dispatchEvent(new Event('change'));
}

async function submit(form = $('#screen form')) {
  form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
  await settle();
}

function posted(path) {
  return server.calls.filter((call) => call.method === 'POST' && call.path === path);
}

function toasts() {
  return [...document.querySelectorAll('.toast')].map((toast) => toast.textContent);
}

describe('starting up', () => {
  it('says the casino is closed when the server cannot be reached', async () => {
    await boot({ routes: { 'GET session': () => { throw new TypeError('offline'); } } });
    expect($('#screen').textContent).toBe('The casino is closed. Start the server and reload.');
  });

  it('opens on the login screen', async () => {
    await boot();
    expect(document.title).toBe("Ronovo's Casino");
    expect($('#topbar').hidden).toBe(true);
    expect($('.hero').textContent).toContain('Guess the Number');
    expect(button('Log in', $('form .tabs')).className).toBe('on');
    expect($('form > button.full').className).toBe('full primary');
  });
});

describe('accounts', () => {
  it('logs in and opens the lobby', async () => {
    await boot({ routes: { 'POST login': session(SEATED) } });
    fill('Username', '  Ronovo ');
    fill('Password', 'hunter22');
    await submit();
    expect(posted('login')[0].body).toEqual({ username: 'Ronovo', password: 'hunter22', question: '', answer: '' });
    expect(location.hash).toBe('#/lobby');
    expect($('#screen').textContent).toContain('Welcome, Lucky. You have 1,000 cr in chips.');
    expect($('#topbar').hidden).toBe(false);
    expect($('#topbar .who').textContent).toBe('Lucky · Medium');
  });

  it('shows why a login failed', async () => {
    await boot({ routes: { 'POST login': reply(400, { error: 'Wrong username or password.' }) } });
    await submit();
    expect($('.error-text').textContent).toBe('Wrong username or password.');
  });

  it('registers with a security question', async () => {
    await boot({ routes: { 'POST register': session({ user: 'Ronovo' }) } });
    click(button('Create account', $('.tabs')));
    expect($('.field-hint').textContent).toContain('3 to 20 letters');
    fill('Username', 'Ronovo');
    fill('Password', 'hunter22');
    fill('Security question', 'City?');
    fill('Answer', 'Paris');
    await submit();
    expect(posted('register')[0].body).toEqual({ username: 'Ronovo', password: 'hunter22', question: 'City?',
      answer: 'Paris' });
    expect($('#topbar .who').textContent).toBe('Signed in as Ronovo');
  });

  it('resets a forgotten password in two steps', async () => {
    await boot({ routes: { 'POST reset-question': { question: 'Pet?' }, 'POST reset-password': { reset: true } } });
    click(button('Forgot password?'));
    fill('Username', 'Ronovo');
    await submit();
    expect($('form p').textContent).toBe('Pet?');
    expect(byText(document, '.field', 'Username').querySelector('input').readOnly).toBe(true);
    fill('Answer', 'Rex');
    fill('New password', 'newpass1');
    click(button('Reset password'));
    await submit();
    expect(posted('reset-password')[0].body).toEqual({ username: 'Ronovo', answer: 'Rex', password: 'newpass1' });
    expect($('#screen').textContent).toContain('Password changed. Log in with your new password.');
  });

  it('says when a reset cannot start, and goes back', async () => {
    await boot({ routes: { 'POST reset-question': reply(400, { error: 'There is no account with that username.' }) } });
    click(button('Forgot password?'));
    await submit();
    expect($('.error-text').textContent).toBe('There is no account with that username.');
    click(button('Back'));
    expect(button('Forgot password?')).toBeTruthy();
  });

  it('offers the portfolio login under the name the portfolio knows', async () => {
    await boot({ portfolio: true, portfolio_url: 'http://portfolio.test',
      routes: { 'GET http://portfolio.test/sso/me': { username: 'Gambler' } } });
    expect(button('Log in as Gambler')).toBeTruthy();
    expect($('form > button.full').className).toBe('full ');
    click(button('Create account', $('.tabs')));
    click(button('Log in', $('.tabs')));
    await settle();
    expect(server.calls.filter((call) => call.path.endsWith('/sso/me'))).toHaveLength(1);
    const browser = { href: '' };
    vi.stubGlobal('location', browser);
    click(button('Log in as Gambler'));
    vi.unstubAllGlobals();
    expect(browser.href).toBe('/sso/login');
  });

  it.each([
    ['logged out of the portfolio', reply(401, {})],
    ['without a name', {}],
    ['unreachable', () => { throw new TypeError('offline'); }],
  ])('keeps the plain portfolio button when the portfolio is %s', async (_, answer) => {
    await boot({ portfolio: true, portfolio_url: 'http://portfolio.test',
      routes: { 'GET http://portfolio.test/sso/me': answer } });
    expect(button('Log in with portfolio account')).toBeTruthy();
  });

  it('links a first portfolio login to an existing account', async () => {
    let tries = 0;
    await boot({ portfolio_pending: 'Gambler', routes: { 'POST portfolio/link': () => {
      tries += 1;
      return tries === 1 ? reply(400, { error: 'Wrong username or password.' }) : session(SEATED);
    } } });
    expect($('h2').textContent).toBe('Link your account');
    expect(byText(document, '.field', 'Username').querySelector('input').value).toBe('Gambler');
    fill('Password', 'wrong');
    await submit();
    expect($('.error-text').textContent).toBe('Wrong username or password.');
    fill('Password', 'hunter22');
    await submit();
    expect(posted('portfolio/link')[1].body).toEqual({ username: 'Gambler', password: 'hunter22' });
    expect(location.hash).toBe('#/lobby');
  });

  it('makes a new account for a first portfolio login, or cancels it', async () => {
    await boot({ portfolio_pending: 'Gambler', routes: { 'POST portfolio/new': session({ user: 'Gambler' }) } });
    click(button('Make a new account'));
    await settle();
    expect($('#topbar .who').textContent).toBe('Signed in as Gambler');

    await boot({ portfolio_pending: 'Gambler', routes: { 'POST logout': session() } });
    click(button('Cancel'));
    await settle();
    expect(button('Forgot password?')).toBeTruthy();
  });
});

describe('characters', () => {
  it('sits down as an existing character', async () => {
    await boot({ user: 'Ronovo', characters: [CHARACTER], routes: { 'POST characters/select': session(SEATED) } });
    const tile = byText(document, '.tile', 'Lucky');
    expect(tile.textContent).toContain('1,000 cr');
    click(tile);
    await settle();
    expect(posted('characters/select')[0].body).toEqual({ id: 1 });
    expect($('#screen').textContent).toContain('Casino Floor');
  });

  it('makes a new character, and says why one was refused', async () => {
    let tries = 0;
    await boot({ user: 'Ronovo', routes: { 'POST characters': () => {
      tries += 1;
      return tries === 1 ? reply(400, { error: "'Lucky' is already taken." }) : session(SEATED);
    } } });
    fill('Name', 'Lucky');
    await submit();
    expect($('.error-text').textContent).toBe("'Lucky' is already taken.");
    fill('Difficulty', 'Easy');
    await submit();
    expect(posted('characters')[1].body).toEqual({ name: 'Lucky', difficulty: 'Easy' });
  });
});

describe('navigation', () => {
  it('moves between screens from the topbar', async () => {
    await boot({ ...SEATED, hash: '#/lobby', routes: {
      'GET profile': floor({ stats: [], categories: [] }), 'GET cashier': floor(),
      'POST characters/select': session({ user: 'Ronovo', characters: [CHARACTER] }), 'POST logout': session(),
    } });
    click(button('Profile', $('#topbar')));
    await settle();
    expect($('#screen').textContent).toContain('No games played yet.');
    click(button('Cashier', $('#topbar')));
    await settle();
    expect($('#screen h2').textContent).toBe('Chip Exchange');
    click($('#topbar .brand'));
    await settle();
    expect($('#screen').textContent).toContain('Casino Floor');
    click(button('Tables', $('#topbar')));
    await settle();
    expect(server.calls.filter((call) => call.path === 'lobby')).toHaveLength(3);
    click(button('Switch character', $('#topbar')));
    await settle();
    expect($('#screen h2').textContent).toBe("Who's playing?");
    click(button('Log out', $('#topbar')));
    await settle();
    expect($('#topbar').hidden).toBe(true);
  });

  it('reports a topbar action that fails', async () => {
    await boot({ ...SEATED, routes: { 'POST characters/select': reply(500, {}), 'POST logout': reply(500, {}) } });
    click(button('Switch character', $('#topbar')));
    click(button('Log out', $('#topbar')));
    await settle();
    expect(toasts()).toEqual(['Something went wrong.', 'Something went wrong.']);
  });

  it('returns to the login screen when the login has run out', async () => {
    await boot({ ...SEATED, routes: { 'GET lobby': reply(401, { error: 'Log in to play.' }) } });
    expect(button('Forgot password?')).toBeTruthy();
    expect(toasts()).toEqual(['Log in to play.']);
  });

  it('shows the lobby for an unknown screen and after a missing table', async () => {
    await boot({ ...SEATED, hash: '#/nowhere' });
    expect($('#screen').textContent).toContain('Casino Floor');
    await boot({ ...SEATED, hash: '#/table/gone',
      routes: { 'GET tables/gone': reply(404, { error: 'There is no such table.' }) } });
    expect(location.hash).toBe('#/lobby');
    expect(toasts()).toEqual(['There is no such table.']);
    expect($('#screen').textContent).toContain('Casino Floor');
  });

  it('reports a screen that breaks', async () => {
    const logged = vi.spyOn(console, 'error').mockImplementation(() => {});
    await boot({ ...SEATED, hash: '#/table/mystery',
      routes: { 'GET tables/mystery': table(null, { ...BLACKJACK, key: 'mystery', game: 'craps' }) } });
    expect(toasts()).toEqual(['Something went wrong.']);
    expect(logged).toHaveBeenCalledOnce();
    expect(location.hash).toBe('#/table/mystery');
  });

  it.each([
    ['#/lobby', 'GET lobby', floor({ tables: TABLES }), '#/profile', 'No games played yet.'],
    ['#/profile', 'GET profile', floor({ stats: [], categories: [] }), '#/cashier', 'Chip Exchange'],
    ['#/cashier', 'GET cashier', floor(), '#/profile', 'No games played yet.'],
    ['#/table/blackjack', 'GET tables/blackjack', table(), '#/profile', 'No games played yet.'],
  ])('does not draw %s once the player has moved on', async (hash, route, body, destination, shown) => {
    const slow = deferred();
    await boot({ ...SEATED, hash, routes: { 'GET profile': floor({ stats: [], categories: [] }), 'GET cashier': floor(),
      [route]: () => slow.promise } });
    await visit(destination);
    slow.resolve(body);
    await settle();
    expect($('#screen').textContent).toContain(shown);
  });
});

describe('lobby', () => {
  it('lists the tables and marks the ones the player can not afford', async () => {
    await boot({ ...SEATED });
    const [blackjack, highRoller, mystery] = document.querySelectorAll('.tile');
    expect(blackjack.querySelector('.badge').textContent).toBe('Round in progress');
    expect(blackjack.textContent).toContain('Limits 1 cr to 100 cr');
    expect(highRoller.disabled).toBe(true);
    expect(highRoller.title).toBe('You need at least 1,500 cr to sit here');
    expect(highRoller.textContent).toContain('500 cr to no limit');
    expect(mystery.querySelector('.icon').textContent).toBe('🎲');
    expect(mystery.title).toBe('');
    click(blackjack);
    expect(location.hash).toBe('#/table/blackjack');
  });

  it('shows notices and achievements', async () => {
    const achievements = [{ display_name: '21!', description: 'Get a Blackjack' }];
    const lobby = floor({ tables: [], achievements, notices: ['Stake returned.'] });
    await boot({ ...SEATED, routes: { 'GET lobby': lobby } });
    expect(toasts()).toEqual(['Stake returned.', '21!Get a Blackjack']);
  });

  it('lets a broke player start over', async () => {
    let starts = 0;
    await boot({ ...SEATED, routes: {
      'GET lobby': floor({ tables: TABLES }, { credits: 0, broke: true }),
      'POST start-over': () => {
        starts += 1;
        return starts === 1 ? floor() : reply(400, { error: 'Starting over is only for players who are broke.' });
      },
    } });
    click(button('Start over'));
    await settle();
    expect(server.calls.filter((call) => call.path === 'lobby')).toHaveLength(2);
    click(button('Start over'));
    await settle();
    expect(toasts()).toEqual(['Starting over is only for players who are broke.']);
  });
});

describe('profile', () => {
  it('shows the record and the achievements, hiding the locked ones', async () => {
    const stats = [{ game: 'Blackjack', wins: 2, losses: 1, pushes: 0, net_credits: 15, biggest_win: 20 },
      { game: 'Roulette', wins: 0, losses: 2, pushes: 0, net_credits: -10, biggest_win: 0 },
      { game: 'Baccarat', wins: 1, losses: 1, pushes: 1, net_credits: 0, biggest_win: 5 }];
    const categories = [{ category: 'Blackjack', items: [
      { unlocked: true, display_name: '21!', description: 'Get a Blackjack', date_unlocked: '2026-10-30' },
      { unlocked: false }] }];
    await boot({ ...SEATED, hash: '#/profile',
      routes: { 'GET profile': floor({ stats, categories }, { credits: 0, broke: true }) } });
    expect([...document.querySelectorAll('tbody td:nth-child(5)')].map((td) => td.className))
      .toEqual(['win', 'lose', '']);
    expect($('.section-title h3').parentElement.textContent).toContain('1/2');
    expect($('.achievement').textContent).toContain('2026-10-30');
    expect($('.achievement.locked').textContent).toContain('Hidden achievement');
    expect(button('Start over with fresh chips')).toBeTruthy();
  });
});

describe('cashier', () => {
  it('breaks chips into a smaller color and colors up', async () => {
    await boot({ ...SEATED, hash: '#/cashier', routes: { 'GET cashier': floor(),
      'POST cashier': floor({}, { chips: { White: 0, Red: 0, Green: 0, Black: 0, Purple: 0, Orange: 1 } }) } });
    fill('Break', 'Purple');
    expect([...byText(document, '.field', 'Into').querySelectorAll('option')].map((o) => o.value))
      .toEqual(['White', 'Red', 'Green', 'Black']);
    fill('Into', 'Black');
    await submit(document.querySelector('#screen form'));
    expect(posted('cashier')[0].body).toEqual({ action: 'break', color: 'Purple', into: 'Black', count: 1 });

    await boot({ ...SEATED, hash: '#/cashier',
      routes: { 'GET cashier': floor(), 'POST cashier': { player: player() } } });
    expect(byText(document, 'option', 'Black (100), up to 2')).toBeTruthy();
    await submit(document.querySelectorAll('#screen form')[1]);
    expect(posted('cashier')[0].body).toEqual({ action: 'color_up', into: 'Red', count: 1 });
  });

  it('says when there is nothing to exchange, and reports a refused exchange', async () => {
    const chips = { White: 3, Red: 0, Green: 0, Black: 0, Purple: 0, Orange: 0 };
    await boot({ ...SEATED, hash: '#/cashier', routes: { 'GET cashier': floor({}, { chips }),
      'POST cashier': reply(400, { error: "That exchange isn't possible." }) } });
    expect($('#screen').textContent).toContain('You have no chips bigger than White to break.');
    expect($('#screen').textContent).toContain("You don't have enough small chips to color up.");
    await submit(document.querySelector('#screen form'));
    expect(toasts()).toEqual(["That exchange isn't possible."]);
  });
});

describe('tables', () => {
  async function sit(routes = {}, round = null, info = BLACKJACK) {
    await boot({ ...SEATED, hash: `#/table/${info.key}`, routes: { [`GET tables/${info.key}`]: table(round, info),
      ...routes } });
  }

  it('plays a round, deals again and changes bets', async () => {
    let deals = 0;
    await sit({
      'POST tables/blackjack/start': () => floor({ round: (deals += 1) === 1 ? IN_PLAY : DONE }),
      'POST tables/blackjack/act': floor({ round: DONE,
        achievements: [{ display_name: 'Win', description: 'Won' }] }),
    });
    expect($('#screen h2').textContent).toBe('Blackjack');
    click($('.spot'));
    click(button('Deal'));
    await settle();
    expect(posted('tables/blackjack/start')[0].body).toEqual({ bets: { bet: 1 } });
    vi.useFakeTimers();
    click(button('Stand'));
    await vi.advanceTimersByTimeAsync(0);
    expect($('.banner')).toBeNull();
    await vi.advanceTimersByTimeAsync(REVEAL);
    expect($('.felt')).toBeNull();
    expect($('.banner').textContent).toContain('YOU WIN');
    click(button('Deal again'));
    await vi.advanceTimersByTimeAsync(REDEAL);
    expect(posted('tables/blackjack/start')[1].body).toEqual({ bets: { bet: 1 } });
    click(button('Change bets'));
    expect(button('Deal')).toBeTruthy();
  });

  it('sends one move at a time and reports a refused bet', async () => {
    const slow = deferred();
    await sit({ 'POST tables/blackjack/act': () => slow.promise,
      'POST tables/blackjack/start': reply(400, { error: 'The maximum stake is 100 cr.' }) }, IN_PLAY);
    const stand = button('Stand');
    click(stand);
    click(stand);
    vi.useFakeTimers();
    slow.resolve(floor({ round: DONE }));
    await vi.advanceTimersByTimeAsync(REVEAL);
    expect(posted('tables/blackjack/act')).toHaveLength(1);
    click(button('Change bets'));
    click($('.spot'));
    click(button('Deal'));
    await vi.advanceTimersByTimeAsync(0);
    expect(toasts()).toEqual(['The maximum stake is 100 cr.']);
  });

  it('tells the server when the player gets up, unless a round is in play', async () => {
    await sit({ 'POST tables/blackjack/leave': floor({ notices: ['Walked away.'] }) });
    click(button('← Tables'));
    await settle();
    expect(posted('tables/blackjack/leave')).toHaveLength(1);
    expect(toasts()).toEqual(['Walked away.']);

    await sit({ 'POST tables/blackjack/leave': {} }, DONE);
    await visit('#/lobby');
    expect(posted('tables/blackjack/leave')).toHaveLength(1);

    await sit({ 'POST tables/blackjack/leave': reply(500, {}) });
    await visit('#/profile');
    expect(toasts()).toContain('Something went wrong.');

    await sit({}, IN_PLAY);
    await visit('#/lobby');
    expect(posted('tables/blackjack/leave')).toHaveLength(0);
  });

  it('does not draw a move that comes back after the player left', async () => {
    const slow = deferred();
    await sit({ 'POST tables/blackjack/act': () => slow.promise }, IN_PLAY);
    click(button('Stand'));
    await visit('#/lobby');
    slow.resolve(floor({ round: DONE }));
    await settle();
    expect($('.banner')).toBeNull();
    expect($('#screen').textContent).toContain('Casino Floor');
  });

  it('starts the chip tray at the smallest chip the table takes', async () => {
    await sit({}, null, { ...BLACKJACK, key: 'whale', min_bet: 5000 });
    expect($('.chip.on').textContent).toBe('1');
    await sit({}, null, { ...BLACKJACK, key: 'tens', min_bet: 10 });
    expect($('.chip.on').textContent).toBe('25');
  });

  it('plays the spin again when the same bets go down for another round', async () => {
    const roulette = { ...BLACKJACK, key: 'roulette', game: 'roulette', title: 'Roulette',
      layout: { wheel: ['0', '00', '1', '2'], red: [1] } };
    const spun = { finished: true, actions: [], pocket: '2', color: 'black',
      result: { net: -1, notes: [], settlements: [] } };
    await sit({ 'POST tables/roulette/start': floor({ round: spun }) }, null, roulette);
    vi.useFakeTimers();
    click($('.cell'));
    click(button('Spin'));
    await vi.advanceTimersByTimeAsync(5000);
    expect($('.wheel-hub').textContent).toBe('2');
    await vi.advanceTimersByTimeAsync(300);
    click(button('Spin again'));
    await vi.advanceTimersByTimeAsync(0);
    expect($('.wheel-hub').textContent).toBe('');
    await vi.advanceTimersByTimeAsync(5000);
    expect($('.wheel-hub').textContent).toBe('2');
  });

  it('shows the rules and payouts in a dialog', async () => {
    await sit();
    click(button('Rules & payouts'));
    const modal = $('#modal');
    expect(modal.hidden).toBe(false);
    expect(modal.textContent).toContain('Get closer to 21 than the dealer.');
    expect([...modal.querySelectorAll('.paytable strong')].map((s) => s.textContent)).toEqual(['Bonuses']);
    click(modal.querySelector('.panel'));
    expect(modal.hidden).toBe(false);
    click(modal);
    expect(modal.hidden).toBe(true);
    click(button('Rules & payouts'));
    click(button('Close', modal));
    expect(modal.hidden).toBe(true);
  });
});

describe('toasts', () => {
  it('fade after a few seconds, achievements a little later', async () => {
    await boot({ ...SEATED, routes: {
      'GET lobby': floor({ tables: [] }, { broke: true }),
      'POST start-over': floor({ achievements: [{ display_name: 'Again', description: 'Start over' }] }),
      'POST logout': reply(500, {}),
    } });
    vi.useFakeTimers();
    click(button('Log out', $('#topbar')));
    click(button('Start over'));
    await vi.advanceTimersByTimeAsync(0);
    expect(toasts()).toEqual(['Something went wrong.', 'AgainStart over']);
    await vi.advanceTimersByTimeAsync(4500);
    expect(toasts()).toEqual(['AgainStart over']);
    await vi.advanceTimersByTimeAsync(2500);
    expect(toasts()).toEqual([]);
  });
});
