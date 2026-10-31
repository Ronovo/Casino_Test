import { afterEach, describe, expect, it, vi } from 'vitest';
import { ApiError, api } from '../../casino/web/static/js/api.js';
import { fakeServer, reply } from './helpers.js';

afterEach(() => vi.unstubAllGlobals());

describe('api', () => {
  it('gets without a body and posts JSON', async () => {
    const server = fakeServer({
      'GET lobby': { tables: [] }, 'POST login': (body) => ({ user: body.username }), 'POST logout': {},
    });
    expect(await api.get('lobby')).toEqual({ tables: [] });
    expect(await api.post('login', { username: 'Ronovo' })).toEqual({ user: 'Ronovo' });
    await api.post('logout');
    expect(server.fetch.mock.calls[0][1]).toEqual({ method: 'GET', credentials: 'same-origin' });
    expect(server.fetch.mock.calls[1][1].headers).toEqual({ 'Content-Type': 'application/json' });
    expect(server.calls[2].body).toEqual({});
  });

  it('turns refusals into an ApiError with the server message', async () => {
    fakeServer({ 'POST start-over': reply(400, { error: 'Not broke.' }) });
    const error = await api.post('start-over').catch((caught) => caught);
    expect(error).toBeInstanceOf(ApiError);
    expect(error.status).toBe(400);
    expect(error.message).toBe('Not broke.');
  });

  it('copes with a reply that is not JSON', async () => {
    const html = async () => { throw new SyntaxError('html'); };
    vi.stubGlobal('fetch', vi.fn(async () => ({ ok: false, status: 502, json: html })));
    await expect(api.get('lobby')).rejects.toMatchObject({ status: 502, message: 'Something went wrong.' });
  });

  it('says so when the server cannot be reached', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => { throw new TypeError('offline'); }));
    await expect(api.get('lobby'))
      .rejects.toMatchObject({ status: 0, message: expect.stringContaining("Can't reach") });
  });
});
