# Basic template for iDP report

## Tools used
- Grid.js for generating table
- Shoelace for custom web-components

## Password protection (Cloudflare Workers)

The whole site is gated by a Cloudflare Worker (`worker/index.js` + `worker/gate.js`,
configured in `wrangler.jsonc`). Every request, including images, scripts and styles, passes
through the Worker first, which shows a login page until the visitor enters the password.
The password is **not** stored in this repository; it is read from a Cloudflare secret.

Setup (one time):
1. Cloudflare dashboard > Workers & Pages > Create application > Import a repository, and select this repository.
   Project name `cde4301-fts-438` (must match `name` in `wrangler.jsonc`); leave the build command empty;
   the default deploy command (`npx wrangler deploy`) is correct.
2. Worker > Settings > **Variables and Secrets** (the top-level one, NOT the one under *Build*, which the running Worker
   cannot see) > add a variable named exactly `SITE_PASSWORD`, type **Secret**, then save and deploy.
3. Redeploy. The `*.workers.dev` URL should now show the sign-in page.
4. Disable GitHub Pages for this repository (Settings > Pages), otherwise the unprotected copy stays online.

To change the password, edit the secret and redeploy; all existing sign-ins are invalidated.
If the secret is missing the site serves nothing (it never falls open).

To test locally: create a `.dev.vars` file containing `SITE_PASSWORD=choose-a-test-password`
(it is git-ignored) and run `npx wrangler dev`.

Notes:
- `.assetsignore` keeps repo-only files (`worker/`, `analysis/`, `README.md`, ...) out of the deployed site.
- Do not add a `functions/` folder: Wrangler treats it as a Cloudflare *Pages* project and refuses to deploy.
- This repository is public, so its source files are readable on GitHub regardless of the site password.
