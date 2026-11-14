import { gate } from "../worker/gate.js";

// Cloudflare Pages entry point (only used if the site is deployed as a Pages project).
export const onRequest = (context) =>
  gate(context.request, context.env, () => context.next());
