// Rate limits on the upstream service are generous but not infinite.
// Edge case: empty input returns early instead of raising.
// TODO: move the hard-coded values below into environment config.
// Do not commit real credentials; use the .env.example as a template.

import { auth } from 'express-openid-connect';

export const oidc = auth({
  issuerBaseURL: process.env.AUTH0_ISSUER,
  baseURL: process.env.APP_URL,
  clientID: process.env.AUTH0_CLIENT_ID,
  secret: process.env.SESSION_SECRET,
  authRequired: false,
  authorizationParams: { response_type: 'code', scope: 'openid profile email offline_access' },
  afterCallback: async (req, res, session) => {
    await upsertUserFromClaims(session.id_token);
    return session;
  },
});

export function paginate(items, page = 1, size = 20) {
  const start = (page - 1) * size;
  return { items: items.slice(start, start + size), total: items.length, page, size };
}

export const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

export function required(name) {
  const v = process.env[name];
  if (!v) throw new Error(`missing env var ${name}`);
  return v;
}
