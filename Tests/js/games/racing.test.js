import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { render } from '../../../casino/web/static/js/games/racing.js';
import { byText, click, makeCtx, mount } from '../helpers.js';

const table = { layout: { season_length: 40 } };
const conditions = { distance: 8, going: 'Good' };
const runners = [
  { key: 'alpha', name: 'Alpha', silks: '#111', style: 'front', weight: 0, recent: [],
    odds: { win: '3:1', place: '1:1', show: null } },
  { key: 'bravo', name: 'Bravo', silks: '#222', style: 'closer', weight: 6, recent: [1, 2, 3, 4, 5, 6],
    odds: { win: '9:1', place: '4:1', show: '2:1' } },
];
const standings = [
  { key: 'alpha', name: 'Alpha', silks: '#111', starts: 2, firsts: 1, seconds: 0, thirds: 1, points: 13, weight: 0,
    recent: [1, 3] },
  { key: 'bravo', name: 'Bravo', silks: '#222', starts: 2, firsts: 0, seconds: 1, thirds: 0, points: 5, weight: 6,
    recent: [2, 4] },
];
const RESULT = { net: 30, notes: ['Alpha wins by 1.2 lengths.'], settlements: [] };

let frames;

beforeEach(() => {
  frames = [];
  vi.stubGlobal('requestAnimationFrame', (fn) => frames.push(fn));
  vi.spyOn(performance, 'now').mockReturnValue(0);
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

function race(overrides = {}) {
  return { finished: true, actions: [], result: RESULT, standings, season_over: null,
    race: { season: 1, number: 3, ...conditions },
    runners: [
      { key: 'alpha', name: 'Alpha', silks: '#111', style: 'front', weight: 0, position: 1, time: 97.6, lengths: 0 },
      { key: 'bravo', name: 'Bravo', silks: '#222', style: 'closer', weight: 6, position: 4, time: 98, lengths: 2 },
      { key: 'charlie', name: 'Charlie', silks: '#333', style: 'stalker', weight: 0, position: 11, time: 99,
        lengths: 8 },
    ], ...overrides };
}

describe('horse racing', () => {
  it('lists the card, drops stakes the new card does not price, and sends bets', () => {
    const betting = { season: 1, race: 3, champion: null, conditions, runners, standings };
    const ctx = makeCtx({ table, betting, local: { stakes: { 'alpha|show': 5, 'gone|win': 5, 'alpha|win': 5 } } });
    ctx.rerender = () => {
      el.replaceChildren();
      render(ctx, el);
    };
    const el = mount();
    expect(render(ctx, el)).toBe(0);
    expect(ctx.local.stakes).toEqual({ 'alpha|win': 5 });
    expect(el.textContent).toContain('Season 1 · Race 3 of 40 · 8 furlongs · Good going');
    expect(el.textContent).not.toContain('Reigning champion');

    const show = byText(el, '.tote tr', 'Alpha').querySelectorAll('.price')[2];
    expect(show.disabled).toBe(true);
    expect(show.textContent).toBe('-');
    const bravo = byText(el, 'tbody tr', 'Bravo');
    expect(bravo.textContent).toContain('+6 lb');
    expect(bravo.textContent).toContain('2-3-4-5-6');
    click(bravo.querySelectorAll('.price')[1]);
    expect(byText(el, 'tbody tr', 'Bravo').querySelector('.price.on .marker').textContent).toBe('5');

    const leaderboard = el.querySelector('.leaderboard');
    expect(leaderboard.textContent).toContain('after 2 of 40 races');
    expect(leaderboard.querySelector('tbody tr').className).toBe('me');
    click(byText(el, 'button', 'Run the race'));
    expect(ctx.start).toHaveBeenCalledWith({ bets: [{ horse: 'alpha', kind: 'win', amount: 5 },
      { horse: 'bravo', kind: 'place', amount: 5 }] });
  });

  it('names the reigning champion and the first race of a season', () => {
    const fresh = standings.map((row) => ({ ...row, starts: 0 }));
    const betting = { season: 2, race: 1, champion: 'Alpha', conditions, runners, standings: fresh };
    const el = mount();
    render(makeCtx({ table, betting }), el);
    expect(el.querySelector('.champion').textContent).toContain('Reigning champion: Alpha');
    expect(el.querySelector('.leaderboard tbody tr').className).toBe('');
  });

  it('runs the race to the line, then shows the places', () => {
    const el = mount();
    const reveal = render(makeCtx({ table, round: race() }), el);
    const horses = el.querySelectorAll('.horse');
    expect([...horses].map((h) => h.textContent)).toEqual(['🏇1st', '🏇4th', '🏇11th']);
    expect(horses[0].className).toBe('horse');

    frames.shift()(1000);
    expect(frames).toHaveLength(1);
    frames.shift()(reveal * 2);
    expect(frames).toHaveLength(0);
    expect([...horses].every((h) => h.className.includes('home'))).toBe(true);
    expect(el.querySelector('.place-badge.paid').textContent).toBe('1st');
    expect(el.querySelector('.leaderboard').textContent).toContain('after 3 of 40 races');
  });

  it('shows a finished race at the line and crowns the season champion', () => {
    const el = mount();
    const round = race({ season_over: { season: 1, champion: 'Alpha' },
      race: { season: 1, number: 40, ...conditions } });
    render(makeCtx({ table, round, local: { raced: true } }), el);
    expect(frames).toHaveLength(0);
    expect([...el.querySelectorAll('.horse')].every((h) => h.className.includes('home'))).toBe(true);
    expect(el.querySelector('.banner').textContent).toBe('🏆 Alpha wins season 1!');
    expect(el.querySelector('.leaderboard').textContent).toContain('after 40 of 40 races');
  });
});
