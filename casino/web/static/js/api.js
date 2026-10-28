export class ApiError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
  }
}

async function request(method, path, data) {
  const options = { method, credentials: 'same-origin' };
  if (data !== undefined) {
    options.headers = { 'Content-Type': 'application/json' };
    options.body = JSON.stringify(data);
  }
  let response;
  try {
    response = await fetch(`api/${path}`, options);
  } catch {
    throw new ApiError(0, "Can't reach the casino. Is the server still running?");
  }
  let body = {};
  try {
    body = await response.json();
  } catch {
    body = {};
  }
  if (!response.ok) throw new ApiError(response.status, body.error || 'Something went wrong.');
  return body;
}

export const api = {
  get: (path) => request('GET', path),
  post: (path, data = {}) => request('POST', path, data),
};
