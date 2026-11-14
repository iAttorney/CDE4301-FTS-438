# Basic template for iDP report

## Tools used
- Grid.js for generating table
- Shoelace for custom web-components

## Password protection (Cloudflare Pages)

The whole site is gated by `functions/_middleware.js`, a Cloudflare Pages Function that
shows a login page until the visitor enters the password. The password is **not** stored
in this repository; it is read from a Cloudflare secret.

Setup (one time):
1. Cloudflare dashboard > Workers & Pages > Create > Pages > Connect to Git, and select this repository.
2. Build settings: framework preset `None`, build command empty, build output directory `/`.
3. Project > Settings > Variables and Secrets > add a **secret** named `SITE_PASSWORD` for both Production and Preview.
4. Redeploy. Visiting the `*.pages.dev` URL should now show the sign-in page.
5. Disable GitHub Pages for this repository (Settings > Pages), otherwise the unprotected copy stays online.

To change the password, edit the secret and redeploy; all existing sign-ins are invalidated.
To test locally: put `SITE_PASSWORD=choose-a-test-password` in a `.dev.vars` file (do not commit it) and run `npx wrangler pages dev .`.

Note: this repository is public, so its source files are readable on GitHub regardless of the site password.
