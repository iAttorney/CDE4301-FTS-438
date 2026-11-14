// Password gate for the whole site. Shared by the Cloudflare Workers entry point
// (worker/index.js) and the Cloudflare Pages entry point (functions/_middleware.js).
//
// gate(request, env, next): `next()` must return the real (unprotected) response.
// Runs before every request, so HTML, images, CSS and JS are all protected.
// The password is NOT stored in this repository: set it as a secret named
// SITE_PASSWORD in the Worker (see README.md). If the secret
// is missing, the site refuses to serve anything rather than falling open.
//
// Flow: no valid cookie -> login page. Correct password -> signed HttpOnly
// cookie (valid 7 days) -> redirected back to the page that was requested.
// Changing SITE_PASSWORD invalidates every existing cookie.

const COOKIE_NAME = "fsae_auth";
const COOKIE_MAX_AGE = 60 * 60 * 24 * 7; // 7 days
const LOGIN_PATH = "/__login";
const encoder = new TextEncoder();

async function hmacHex(secret, message) {
  const key = await crypto.subtle.importKey(
    "raw",
    encoder.encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );
  const sig = await crypto.subtle.sign("HMAC", key, encoder.encode(message));
  return [...new Uint8Array(sig)]
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

// Constant-time comparison of two equal-length hex strings.
function safeEqual(a, b) {
  if (a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return diff === 0;
}

// Compare passwords via HMAC digests so length never leaks and compare is constant-time.
async function passwordMatches(attempt, actual) {
  const [a, b] = await Promise.all([
    hmacHex("password-check", attempt),
    hmacHex("password-check", actual),
  ]);
  return safeEqual(a, b);
}

function sessionToken(password) {
  return hmacHex(password, "fsae-report-session-v1");
}

function getCookie(request, name) {
  const header = request.headers.get("Cookie") || "";
  for (const part of header.split(";")) {
    const [k, ...v] = part.trim().split("=");
    if (k === name) return v.join("=");
  }
  return "";
}

// Only allow same-site relative redirects (blocks open-redirect via ?next=).
function safeNext(value) {
  if (typeof value !== "string" || !value.startsWith("/")) return "/";
  if (value.startsWith("//") || value.startsWith("/\\")) return "/";
  if (value.startsWith(LOGIN_PATH)) return "/";
  return value;
}

function escapeHtml(s) {
  return s.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
}

function loginPage(next, errorMessage) {
  const body = `<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width,initial-scale=1" />
    <meta name="robots" content="noindex,nofollow" />
    <title>Sign in | CDE4301 Interim Report</title>
    <script>
      // If the session expired while a chapter was open in the report's iframe,
      // show the login page full-window instead of inside the frame.
      if (window.top !== window.self) window.top.location.href = location.href;
    </script>
    <style>
      :root { --ink: #172333; --muted: #66758a; --line: #e4e9ef; --accent: #19558a; }
      * { box-sizing: border-box; }
      body {
        margin: 0; min-height: 100vh; display: grid; place-items: center; padding: 24px;
        color: var(--ink); background: #f7f9fc;
        font: 17px/1.6 system-ui, -apple-system, "Segoe UI", sans-serif;
      }
      main {
        width: min(100%, 400px); padding: 32px 28px; background: #fff;
        border: 1px solid var(--line); border-radius: 12px; box-shadow: 0 8px 30px #17233314;
      }
      .eyebrow { margin: 0 0 6px; font-size: .8rem; font-weight: 700; letter-spacing: .14em; text-transform: uppercase; color: var(--muted); }
      h1 { margin: 0 0 8px; font-size: 1.45rem; line-height: 1.3; }
      p { margin: 0 0 20px; color: var(--muted); font-size: .95rem; }
      label { display: block; margin-bottom: 6px; font-size: .9rem; font-weight: 600; }
      input[type=password] {
        width: 100%; padding: 10px 12px; font: inherit; color: var(--ink);
        border: 1px solid #ccd5df; border-radius: 8px;
      }
      input[type=password]:focus-visible { outline: 3px solid var(--accent); outline-offset: 1px; }
      button {
        margin-top: 16px; width: 100%; padding: 11px 14px; font: inherit; font-weight: 600;
        color: #fff; background: var(--accent); border: 0; border-radius: 8px; cursor: pointer;
      }
      button:hover { background: #134770; }
      .error { margin: 0 0 16px; padding: 10px 12px; color: #8a1c1c; background: #fdeeee; border-left: 3px solid #b2182b; border-radius: 4px; font-size: .9rem; }
    </style>
  </head>
  <body>
    <main>
      <p class="eyebrow">CDE4301 &middot; Interim Report</p>
      <h1>This report is password protected</h1>
      <p>Enter the password to continue.</p>
      ${errorMessage ? `<div class="error" role="alert">${escapeHtml(errorMessage)}</div>` : ""}
      <form method="post" action="${LOGIN_PATH}">
        <input type="hidden" name="next" value="${escapeHtml(next)}" />
        <label for="password">Password</label>
        <input id="password" name="password" type="password" autocomplete="current-password" required autofocus />
        <button type="submit">Sign in</button>
      </form>
    </main>
  </body>
</html>
`;
  return new Response(body, {
    status: errorMessage ? 401 : 200,
    headers: {
      "Content-Type": "text/html; charset=UTF-8",
      "Cache-Control": "no-store",
      "X-Robots-Tag": "noindex, nofollow",
    },
  });
}

export async function gate(request, env, next) {
  const password = env.SITE_PASSWORD;

  if (!password) {
    // Names only, never values: lets whoever deployed see what the running Worker actually has.
    const names = Object.keys(env || {});
    const present = names.includes("SITE_PASSWORD");
    return new Response(
      "Password protection is not configured.\n" +
        "\n" +
        (present
          ? "SITE_PASSWORD exists on the running Worker but its value is empty. Re-enter the secret value.\n"
          : "The running Worker has no binding named exactly SITE_PASSWORD.\n" +
            "Add it as a Secret under the Worker's Settings > Variables and Secrets (not under Build), then deploy.\n") +
        "\nBindings visible to this Worker: " + JSON.stringify(names) + "\n",
      { status: 500, headers: { "Content-Type": "text/plain; charset=UTF-8", "Cache-Control": "no-store" } },
    );
  }

  const url = new URL(request.url);
  const token = await sessionToken(password);

  // Login form submission.
  if (url.pathname === LOGIN_PATH) {
    if (request.method !== "POST") return Response.redirect(url.origin + "/", 303);
    const form = await request.formData();
    const attempt = String(form.get("password") || "");
    const target = safeNext(String(form.get("next") || "/"));
    if (!(await passwordMatches(attempt, password))) {
      return loginPage(target, "Incorrect password. Please try again.");
    }
    return new Response(null, {
      status: 303,
      headers: {
        Location: target,
        "Cache-Control": "no-store",
        "Set-Cookie": `${COOKIE_NAME}=${token}; Path=/; Max-Age=${COOKIE_MAX_AGE}; HttpOnly; Secure; SameSite=Lax`,
      },
    });
  }

  // Already signed in: serve the requested file.
  if (safeEqual(getCookie(request, COOKIE_NAME), token)) {
    const response = await next();
    const headers = new Headers(response.headers);
    headers.set("X-Robots-Tag", "noindex, nofollow");
    return new Response(response.body, {
      status: response.status,
      statusText: response.statusText,
      headers,
    });
  }

  // Not signed in: show the login page for page loads, 401 for everything else.
  const wantsHtml = (request.headers.get("Accept") || "").includes("text/html");
  if (request.method === "GET" && wantsHtml) {
    return loginPage(safeNext(url.pathname + url.search), "");
  }
  return new Response("Unauthorized", { status: 401, headers: { "Cache-Control": "no-store" } });
}
