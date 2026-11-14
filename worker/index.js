import { gate } from "./gate.js";

// Cloudflare Workers entry point. run_worker_first (wrangler.jsonc) makes every
// request pass through here before any static file is served.
//
// html_handling is "none" so files are served at exactly the URL requested
// (e.g. /section-6-2.html stays /section-6-2.html, as on GitHub Pages); the
// only mapping done here is "/" -> "/index.html".
export default {
  async fetch(request, env) {
    return gate(request, env, () => {
      const url = new URL(request.url);
      if (url.pathname === "/") {
        url.pathname = "/index.html";
        return env.ASSETS.fetch(new Request(url, request));
      }
      return env.ASSETS.fetch(request);
    });
  },
};
