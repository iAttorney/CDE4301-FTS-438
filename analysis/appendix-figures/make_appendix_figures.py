"""Generate the explanatory SVG figures for Appendices C-E.

Figures (Appendices C-E; Appendix B is Flat Panels)
    assets/appendix-venturi.svg            Figure C1  Venturi tube (quasi-1D continuity + Bernoulli)
    assets/appendix-ground-effect-flow.svg Figure D1  Inverted wing in free air vs near the ground
    assets/appendix-ground-effect-cp.svg   Figure D2  Pressure distribution + schematic h/c trend
    assets/appendix-airfoil-anatomy.svg    Figure E1  Airfoil nomenclature and forces
    assets/appendix-airfoil-flow.svg       Figure E2  Streamlines and pressure around an airfoil

The streamlines and pressure coefficients come from a Hess-Smith panel method
(constant-strength source panels + one uniform vortex strength, Kutta condition
at the trailing edge). The ground is modelled with a mirror-image airfoil, which
is the inviscid equivalent of a moving ground. The results are inviscid, so they
show the mechanism, not the viscous force-reduction region close to the ground
(that part of Figure D2 is a labelled schematic).

Pure Python, no dependencies.
Usage:  python make_appendix_figures.py   (writes into ../../assets)
"""
import math, os

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "assets")

INK, MUTED, LINE, ACCENT = "#172333", "#66758a", "#c8d3df", "#19558a"
FONT = "system-ui,-apple-system,'Segoe UI',sans-serif"
BODY_FILL = "#dfe6ee"

# Speed bins (V/V_inf): red = slow / high pressure, blue = fast / low pressure.
BINS = [(0.6, "#b2182b"), (0.9, "#e0795e"), (1.1, "#8f9bab"),
        (1.4, "#6aa6d8"), (1.8, "#2f74b5"), (1e9, "#12396b")]
BIN_LABELS = ["< 0.6", "0.6–0.9", "0.9–1.1", "1.1–1.4", "1.4–1.8", "> 1.8"]


def speed_bin(v):
    for i, (hi, _) in enumerate(BINS):
        if v < hi:
            return i
    return len(BINS) - 1


# ---------------------------------------------------------------- SVG helpers
def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def text(x, y, s, size=14, anchor="start", color=INK, weight="normal", italic=False, raw=False, halo=False):
    style = ' font-style="italic"' if italic else ""
    if halo:
        style += ' stroke="#ffffff" stroke-width="4" stroke-linejoin="round" paint-order="stroke"'
    body = s if raw else esc(s)
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" text-anchor="{anchor}" '
            f'fill="{color}" font-weight="{weight}"{style}>{body}</text>')


def sub(base, s, size=14):
    """'C' + subscript 'L' as raw text content."""
    return f'{esc(base)}<tspan dy="{size*0.3:.1f}" font-size="{size*0.72:.1f}">{esc(s)}</tspan><tspan dy="{-size*0.3:.1f}"> </tspan>'


def poly(pts, stroke=INK, width=1.5, fill="none", dash=None, close=False, extra=""):
    d = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    tag = "polygon" if close else "polyline"
    da = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<{tag} points="{d}" fill="{fill}" stroke="{stroke}" stroke-width="{width}" '
            f'stroke-linejoin="round" stroke-linecap="round"{da}{extra}/>')


def line(x1, y1, x2, y2, stroke=INK, width=1.5, dash=None, marker=None):
    da = f' stroke-dasharray="{dash}"' if dash else ""
    mk = f' marker-end="url(#{marker})"' if marker else ""
    return (f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{stroke}" '
            f'stroke-width="{width}"{da}{mk}/>')


def arrow_defs():
    out = ["<defs>"]
    for name, col in [("arr", INK), ("arrA", ACCENT), ("arrM", MUTED), ("arrR", "#b2182b")]:
        out.append(f'<marker id="{name}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" '
                   f'markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{col}"/></marker>')
    out.append('<pattern id="hatch" width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
               f'<line x1="0" y1="0" x2="0" y2="8" stroke="{MUTED}" stroke-width="1.2"/></pattern>')
    out.append("</defs>")
    return "\n".join(out)


def svg(w, h, parts, title):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" '
            f'font-family="{FONT}">\n<title>{esc(title)}</title>\n'
            f'<rect width="{w}" height="{h}" fill="#ffffff"/>\n{arrow_defs()}\n' + "\n".join(parts) + "\n</svg>\n")


def write(name, content):
    path = os.path.join(OUT, name)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print("wrote", os.path.normpath(path))


def speed_legend(x, y, title="Local speed V/V∞"):
    parts = [text(x, y, title, 13, color=MUTED, weight="600")]
    for i, (_, col) in enumerate(BINS):
        xx = x + i * 78
        parts.append(line(xx, y + 14, xx + 26, y + 14, stroke=col, width=4))
        parts.append(text(xx + 31, y + 18.5, BIN_LABELS[i], 12, color=MUTED))
    parts.append(text(x, y + 38, "slow / high pressure  ←→  fast / low pressure", 12, color=MUTED, italic=True))
    return parts


def coloured_polyline(pts, speeds, to_px, width=1.7):
    """Split a streamline into runs of equal speed bin."""
    parts, run, cur = [], [], None
    for p, v in zip(pts, speeds):
        b = speed_bin(v)
        if cur is None:
            cur = b
        if b != cur:
            run.append(to_px(p))
            parts.append(poly(run, stroke=BINS[cur][1], width=width))
            run, cur = [to_px(p)], b
        else:
            run.append(to_px(p))
    if len(run) > 1:
        parts.append(poly(run, stroke=BINS[cur][1], width=width))
    return parts


# ------------------------------------------------------------ airfoil geometry
def naca4(m, p, t, n=70):
    """NACA 4-digit (closed TE). Returns clockwise points: TE -> lower -> LE -> upper -> TE."""
    xs = [0.5 * (1 - math.cos(math.pi * i / n)) for i in range(n + 1)]
    up, lo = [], []
    for x in xs:
        yt = 5 * t * (0.2969 * math.sqrt(x) - 0.1260 * x - 0.3516 * x**2 + 0.2843 * x**3 - 0.1036 * x**4)
        if x < p:
            yc = m / p**2 * (2 * p * x - x**2); dy = 2 * m / p**2 * (p - x)
        else:
            yc = m / (1 - p)**2 * ((1 - 2 * p) + 2 * p * x - x**2); dy = 2 * m / (1 - p)**2 * (p - x)
        th = math.atan(dy)
        up.append((x - yt * math.sin(th), yc + yt * math.cos(th)))
        lo.append((x + yt * math.sin(th), yc - yt * math.cos(th)))
    pts = lo[::-1] + up[1:]
    return pts


def camber_line(m, p, n=60):
    out = []
    for i in range(n + 1):
        x = i / n
        yc = m / p**2 * (2 * p * x - x**2) if x < p else m / (1 - p)**2 * ((1 - 2 * p) + 2 * p * x - x**2)
        out.append((x, yc))
    return out


def transform(pts, alpha_deg, invert=False, dx=0.0, dy=0.0, pivot=0.25):
    """Rotate nose-up by alpha about the pivot (fraction of chord), optionally invert, then shift."""
    a = math.radians(alpha_deg)
    out = []
    for x, y in pts:
        if invert:
            y = -y
        xr, yr = x - pivot, y
        sgn = -1 if not invert else 1  # nose up = clockwise rotation of a left-to-right chord... see below
        # Nose-up for an upright airfoil means LE rises: rotate by +alpha in the clockwise sense.
        # Nose-down (inverted wing incidence producing downforce) is the mirror of that.
        c, s = math.cos(sgn * a), math.sin(sgn * a)
        out.append((pivot + xr * c - yr * s + dx, xr * s + yr * c + dy))
    if invert:
        out = out[::-1]  # keep clockwise ordering after the reflection
    return out


# ---------------------------------------------------------------- panel method
class Panels:
    def __init__(self, pts, ground=False):
        self.ground = ground
        self.pts = pts
        self.n = len(pts) - 1
        self.geo = []
        for j in range(self.n):
            ax, ay = pts[j]; bx, by = pts[j + 1]
            L = math.hypot(bx - ax, by - ay)
            c, s = (bx - ax) / L, (by - ay) / L
            self.geo.append((ax, ay, L, c, s, 0.5 * (ax + bx), 0.5 * (ay + by)))
        self.solve()

    @staticmethod
    def _unit(px, py, g, self_panel=False):
        ax, ay, L, c, s, _, _ = g
        if self_panel:
            lnr, dth = 0.0, math.pi
        else:
            dx, dy = px - ax, py - ay
            xl, yl = dx * c + dy * s, -dx * s + dy * c
            r1, r2 = xl * xl + yl * yl, (xl - L) ** 2 + yl * yl
            lnr = 0.5 * math.log(r1 / r2)
            dth = math.atan2(yl, xl - L) - math.atan2(yl, xl)
        k = 1 / (2 * math.pi)
        us, vs = lnr * k, dth * k            # unit source, local frame
        uv, vv = -dth * k, lnr * k           # unit CCW vortex, local frame
        return (us * c - vs * s, us * s + vs * c, uv * c - vv * s, uv * s + vv * c)

    def _influence(self, px, py, j, self_panel=False):
        us, vs, uv, vv = self._unit(px, py, self.geo[j], self_panel)
        if self.ground:
            ui, vi, uvi, vvi = self._unit(px, -py, self.geo[j])
            us, vs, uv, vv = us + ui, vs - vi, uv + uvi, vv - vvi
        return us, vs, uv, vv

    def solve(self):
        n = self.n
        A = [[0.0] * (n + 2) for _ in range(n + 1)]
        tang = [(g[3], g[4]) for g in self.geo]
        norm = [(-g[4], g[3]) for g in self.geo]
        rows = {}
        for i in range(n):
            _, _, _, _, _, xm, ym = self.geo[i]
            rows[i] = [self._influence(xm, ym, j, i == j) for j in range(n)]
            nx, ny = norm[i]
            for j, (us, vs, uv, vv) in enumerate(rows[i]):
                A[i][j] = nx * us + ny * vs
                A[i][n] += nx * uv + ny * vv
            A[i][n + 1] = -nx  # freestream (1, 0)
        for i in (0, n - 1):  # Kutta: Vt(0) + Vt(n-1) = 0
            tx, ty = tang[i]
            for j, (us, vs, uv, vv) in enumerate(rows[i]):
                A[n][j] += tx * us + ty * vs
                A[n][n] += tx * uv + ty * vv
            A[n][n + 1] -= tx
        sol = gauss(A)
        self.sigma, self.gamma = sol[:n], sol[n]
        self.vt, self.cp = [], []
        for i in range(n):
            tx, ty = tang[i]
            vt = tx
            for j, (us, vs, uv, vv) in enumerate(rows[i]):
                vt += self.sigma[j] * (tx * us + ty * vs) + self.gamma * (tx * uv + ty * vv)
            self.vt.append(vt); self.cp.append(1 - vt * vt)
        # Vertical force coefficient (positive up), per unit chord
        self.cl = sum(-cp * g[3] * g[2] for cp, g in zip(self.cp, self.geo))  # n_y = c

    def velocity(self, px, py):
        u, v = 1.0, 0.0
        for j in range(self.n):
            us, vs, uv, vv = self._influence(px, py, j)
            u += self.sigma[j] * us + self.gamma * uv
            v += self.sigma[j] * vs + self.gamma * vv
        return u, v

    def inside(self, x, y):
        c, pts = False, self.pts
        for i in range(len(pts) - 1):
            (x1, y1), (x2, y2) = pts[i], pts[i + 1]
            if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
                c = not c
        return c

    def streamline(self, x0, y0, box, h=0.012, nmax=900):
        pts, sp = [], []
        x, y = x0, y0
        def f(x, y):
            u, v = self.velocity(x, y); m = math.hypot(u, v) or 1e-9
            return u / m, v / m, m
        for _ in range(nmax):
            k1 = f(x, y)
            k2 = f(x + 0.5 * h * k1[0], y + 0.5 * h * k1[1])
            k3 = f(x + 0.5 * h * k2[0], y + 0.5 * h * k2[1])
            k4 = f(x + h * k3[0], y + h * k3[1])
            pts.append((x, y)); sp.append(k1[2])
            x += h / 6 * (k1[0] + 2 * k2[0] + 2 * k3[0] + k4[0])
            y += h / 6 * (k1[1] + 2 * k2[1] + 2 * k3[1] + k4[1])
            if not (box[0] <= x <= box[1] and box[2] <= y <= box[3]) or self.inside(x, y):
                break
            if self.ground and y <= 0:
                break
        return pts, sp


def gauss(A):
    n = len(A)
    for c in range(n):
        p = max(range(c, n), key=lambda r: abs(A[r][c]))
        A[c], A[p] = A[p], A[c]
        for r in range(c + 1, n):
            f = A[r][c] / A[c][c]
            if f:
                for k in range(c, n + 1):
                    A[r][k] -= f * A[c][k]
    x = [0.0] * n
    for r in range(n - 1, -1, -1):
        x[r] = (A[r][n] - sum(A[r][k] * x[k] for k in range(r + 1, n))) / A[r][r]
    return x


def flow_panel(P, ox, oy, S, box, seeds, label, ground_y=None):
    """Draw streamlines + airfoil for one panel. Returns svg parts."""
    to_px = lambda p: (ox + p[0] * S, oy - p[1] * S)
    parts = []
    X0, Y0 = to_px((box[0], box[3])); X1, Y1 = to_px((box[1], box[2]))
    clip_id = f"clip{abs(hash(label)) % 10**6}"
    parts.append(f'<clipPath id="{clip_id}"><rect x="{X0:.1f}" y="{Y0:.1f}" width="{X1-X0:.1f}" height="{Y1-Y0:.1f}"/></clipPath>')
    parts.append(f'<g clip-path="url(#{clip_id})">')
    for y0 in seeds:
        pts, sp = P.streamline(box[0], y0, box)
        parts += coloured_polyline(pts, sp, to_px)
    parts.append("</g>")
    parts.append(poly([to_px(p) for p in P.pts], stroke=INK, width=1.6, fill=BODY_FILL, close=True))
    if ground_y is not None:
        gx0, gy = to_px((box[0], 0)); gx1, _ = to_px((box[1], 0))
        parts.append(f'<rect x="{gx0:.1f}" y="{gy:.1f}" width="{gx1-gx0:.1f}" height="14" fill="url(#hatch)"/>')
        parts.append(line(gx0, gy, gx1, gy, stroke=INK, width=2))
    parts.append(f'<rect x="{X0:.1f}" y="{Y0:.1f}" width="{X1-X0:.1f}" height="{Y1-Y0 + (14 if ground_y is not None else 0):.1f}" fill="none" stroke="{LINE}"/>')
    parts.append(text(X0 + 10, Y0 + 22, label, 14, weight="700", halo=True))
    return parts


def cp_axes(x0, y0, w, h, ymin, ymax, ystep, title):
    """-Cp (up) against x/c. Returns parts and a mapping function."""
    parts = []
    m = lambda xc, cp: (x0 + xc * w, y0 + h - (-cp - ymin) / (ymax - ymin) * h)
    v = ymin
    while v <= ymax + 1e-9:
        _, yy = m(0, -v)
        parts.append(line(x0, yy, x0 + w, yy, stroke="#eef2f6" if abs(v) > 1e-9 else LINE, width=1))
        parts.append(text(x0 - 8, yy + 4, f"{v:g}", 12, "end", MUTED))
        v += ystep
    for xc in (0, 0.25, 0.5, 0.75, 1.0):
        xx, _ = m(xc, 0)
        parts.append(text(xx, y0 + h + 18, f"{xc:g}", 12, "middle", MUTED))
    parts.append(line(x0, y0 + h, x0 + w, y0 + h, stroke=MUTED, width=1))
    parts.append(line(x0, y0, x0, y0 + h, stroke=MUTED, width=1))
    parts.append(text(x0 + w / 2, y0 + h + 38, "Position along chord, x/c", 13, "middle", MUTED))
    parts.append(f'<text x="{x0-44:.1f}" y="{y0+h/2:.1f}" font-size="13" fill="{MUTED}" text-anchor="middle" '
                 f'transform="rotate(-90 {x0-44:.1f} {y0+h/2:.1f})">{sub("−C", "p", 13)}</text>')
    parts.append(text(x0, y0 - 12, title, 14, weight="700"))
    return parts, m


def cp_curve(P, chord_x0, m, color, width=2.0, dash=None):
    """Only used with axes ranges that contain the whole curve."""
    pts = []
    for g, cp in zip(P.geo, P.cp):
        xc = g[5] - chord_x0
        pts.append(m(xc, cp))
    return poly(pts, stroke=color, width=width, dash=dash)


# =================================================================== Figure B1
def fig_venturi():
    W, H = 900, 565
    cy, x_in, x_out = 330, 60, 840
    h1, h2 = 78, 36
    def half(x):
        if x < 230: return h1
        if x < 390: return h2 + (h1 - h2) * 0.5 * (1 + math.cos(math.pi * (x - 230) / 160))
        if x < 470: return h2
        if x < 720: return h1 - (h1 - h2) * 0.5 * (1 + math.cos(math.pi * (x - 470) / 250))
        return h1
    xs = list(range(x_in, x_out + 1, 4))
    P = []
    # duct walls
    top = [(x, cy - half(x)) for x in xs]; bot = [(x, cy + half(x)) for x in xs]
    P.append(poly(top + [(x_out, cy - h1 - 14), (x_in, cy - h1 - 14)], stroke="none", fill="#eef2f6", close=True))
    P.append(poly(bot + [(x_out, cy + h1 + 14), (x_in, cy + h1 + 14)], stroke="none", fill="#eef2f6", close=True))
    # streamlines, coloured by V/V1 = h1/h (continuity)
    for k in [-0.85, -0.6, -0.35, -0.1, 0.1, 0.35, 0.6, 0.85]:
        pts = [(x, cy + k * half(x)) for x in xs]
        P += coloured_polyline(pts, [h1 / half(x) for x in xs], lambda p: p, width=2)
    P.append(poly(top, width=2.2)); P.append(poly(bot, width=2.2))
    # manometer tubes: liquid level drops by k*(v^2 - v1^2)
    datum, kp = 92, 22.0
    stations = [(140, "1"), (430, "2"), (790, "3")]
    for x, lab in stations:
        v = h1 / half(x)
        wall = cy - half(x)
        level = datum + kp * (v * v - 1)
        P.append(f'<rect x="{x-9}" y="{datum-28}" width="18" height="{wall-datum+28:.1f}" fill="#ffffff" stroke="{INK}" stroke-width="1.5"/>')
        P.append(f'<rect x="{x-7.5}" y="{level:.1f}" width="15" height="{wall-level:.1f}" fill="#9cc3e6"/>')
        P.append(line(x, cy - half(x) + 4, x, cy + half(x) - 4, stroke=MUTED, width=1, dash="3 4"))
        P.append(text(x, cy + h1 + 40, lab, 15, "middle", weight="700"))
    P.append(line(120, datum, 820, datum, stroke=MUTED, width=1, dash="5 5"))
    lvl2 = datum + kp * ((h1 / h2) ** 2 - 1)
    P.append(line(470, datum + 2, 470, lvl2 - 2, stroke="#b2182b", width=1.6, marker="arrR"))
    P.append(text(480, (datum + lvl2) / 2 + 2, "Δh ∝ p₁ − p₂", 13, color="#b2182b"))
    P.append(text(140, cy + h1 + 60, "A₁, v₁, p₁", 13, "middle", MUTED))
    P.append(text(430, cy + h1 + 60, "A₂ < A₁  →  v₂ > v₁,  p₂ < p₁", 13, "middle", MUTED))
    P.append(text(790, cy + h1 + 60, "A₃ = A₁  →  v₃ = v₁,  p₃ = p₁", 13, "middle", MUTED))
    P.append(text(x_in - 4, cy - h1 - 22, "Flow →", 13, color=MUTED, weight="600"))
    P.append(text(170, 60, "Manometer level = local static pressure", 12, color=MUTED, italic=True))
    P += speed_legend(220, 500, "Speed v/v₁")
    return svg(W, H, P, "Venturi tube: streamlines bunch together and speed up in the throat, where the static pressure drops")


# =================================================================== Figure D1
def fig_anatomy():
    W, H = 900, 470
    S, ox, oy = 560, 190, 250
    alpha = 8
    foil = transform(naca4(0.04, 0.4, 0.12), alpha)
    camb = transform(camber_line(0.04, 0.4), alpha)
    to_px = lambda p: (ox + p[0] * S, oy - p[1] * S)
    on_chord = lambda f: (le[0] + f * (te[0] - le[0]), le[1] + f * (te[1] - le[1]))
    surf = lambda upper, xc: to_px(min((p for i, p in enumerate(foil) if (i > len(foil) // 2) == upper),
                                        key=lambda p: abs(p[0] - transform([(xc, 0)], alpha)[0][0])))
    P = []
    le, te = to_px(camb[0]), to_px(camb[-1])
    P.append(poly([to_px(p) for p in foil], fill=BODY_FILL, width=1.8, close=True))
    P.append(line(le[0], le[1], te[0], te[1], stroke=ACCENT, width=1.4, dash="7 5"))
    P.append(poly([to_px(p) for p in camb], stroke="#b2182b", width=1.4, dash="2 4"))
    # freestream and angle of attack
    P.append(line(le[0] - 170, le[1], le[0] - 20, le[1], width=2, marker="arr"))
    P.append(text(le[0] - 170, le[1] - 12, sub("V", "∞", 15) + " (freestream)", 15, raw=True))
    P.append(line(le[0], le[1], te[0] + 20, le[1], stroke=MUTED, width=1, dash="3 4"))
    r, a = 470, math.radians(alpha)
    P.append(f'<path d="M{le[0]+r:.1f},{le[1]:.1f} A{r},{r} 0 0 1 {le[0]+r*math.cos(a):.1f},{le[1]+r*math.sin(a):.1f}" '
             f'fill="none" stroke="{INK}" stroke-width="1.3"/>')
    P.append(text(le[0] + r + 8, le[1] + 0.5 * r * math.sin(a) + 5, "α", 16, weight="700"))
    P.append(text(le[0] + r + 24, le[1] + 0.5 * r * math.sin(a) + 5, "angle of attack", 13, color=MUTED))
    # edge labels
    P.append(text(le[0] - 14, le[1] + 36, "Leading edge", 13, "end", MUTED))
    P.append(line(le[0] - 12, le[1] + 26, le[0] - 3, le[1] + 5, stroke=MUTED, width=1))
    P.append(text(te[0] + 10, te[1] + 5, "Trailing edge", 13, color=MUTED))
    # surfaces
    u = surf(True, 0.62)
    P.append(text(u[0] + 30, u[1] - 46, "Upper surface (suction side)", 13, color=MUTED))
    P.append(line(u[0] + 40, u[1] - 40, u[0] + 2, u[1] - 3, stroke=MUTED, width=1))
    l = surf(False, 0.3)
    P.append(text(l[0] - 150, l[1] + 62, "Lower surface (pressure side)", 13, color=MUTED))
    P.append(line(l[0] - 40, l[1] + 48, l[0] - 2, l[1] + 4, stroke=MUTED, width=1))
    # chord and camber line
    ch = on_chord(0.62)
    P.append(text(ch[0] - 40, ch[1] + 78, "Chord line, length c", 13, color=ACCENT))
    P.append(line(ch[0] - 10, ch[1] + 64, ch[0], ch[1] + 3, stroke=ACCENT, width=1))
    cm = to_px(camb[48])
    P.append(text(cm[0] + 70, cm[1] + 66, "Mean camber line", 13, color="#b2182b"))
    P.append(line(cm[0] + 80, cm[1] + 52, cm[0] + 2, cm[1] + 2, stroke="#b2182b", width=1))
    # forces at quarter chord
    qc = to_px(transform([(0.25, 0.0)], alpha)[0])
    Lf, D = 175, 45
    P.append(line(qc[0], qc[1], qc[0], qc[1] - Lf, stroke=ACCENT, width=2.6, marker="arrA"))
    P.append(line(qc[0], qc[1], qc[0] + D, qc[1], stroke=ACCENT, width=2.6, marker="arrA"))
    P.append(line(qc[0], qc[1], qc[0] + D, qc[1] - Lf, stroke=INK, width=1.6, dash="6 4", marker="arr"))
    P.append(text(qc[0] - 10, qc[1] - Lf + 10, "Lift L (⊥ to V∞)", 14, "end", ACCENT, "700"))
    P.append(text(qc[0] + D + 8, qc[1] + 5, "Drag D (∥ to V∞)", 14, color=ACCENT, weight="700", halo=True))
    P.append(text(qc[0] + D + 10, qc[1] - Lf + 10, "Resultant R", 13, color=INK))
    P.append(text(30, H - 20, "On a race car the wing is mounted upside down, so the same force acts towards the ground (downforce).", 13, color=MUTED, italic=True))
    return svg(W, H, P, "Airfoil nomenclature: leading and trailing edge, chord line, mean camber line, angle of attack, lift and drag")


# =================================================================== Figure D2
def fig_airfoil_flow():
    W = 900
    alpha = 6
    foil = transform(naca4(0.04, 0.4, 0.12, 60), alpha)
    P0 = Panels(foil)
    print(f"  NACA 4412, alpha={alpha}: inviscid C_L = {P0.cl:.3f}")
    box = (-0.55, 1.75, -0.5, 0.62)
    S, ox, oy = 370, 30 + 0.55 * 370, 20 + 0.62 * 370
    seeds = [-0.46 + 0.07 * i for i in range(16)] + [0.012, 0.03]
    parts = []
    parts += flow_panel(P0, ox, oy, S, box, sorted(seeds), "(a) Streamlines coloured by local speed")
    ybot = oy - box[2] * S
    parts += speed_legend(330, ybot + 28)
    cy0 = ybot + 110
    ax, m = cp_axes(110, cy0, 740, 250, -1.0, 2.5, 0.5, "(b) Surface pressure coefficient")
    parts += ax
    parts.append(cp_curve(P0, 0.0, m, ACCENT, 2.2))
    tx, ty = m(0.3, -1.95)
    parts.append(text(tx, ty, "Upper (suction) surface: Cₚ < 0, suction peak near the leading edge", 13, color=ACCENT))
    tx, ty = m(0.3, 0.05)
    parts.append(text(tx, ty, "Lower (pressure) surface: Cₚ > 0", 13, color=ACCENT))
    tx, ty = m(0.12, -0.75)
    parts.append(text(tx, ty, "Area enclosed between the curves = lift coefficient", 13, color=MUTED, italic=True))
    H = int(cy0 + 300)
    return svg(W, H, parts, "Streamlines and surface pressure coefficient around a NACA 4412 airfoil at 6 degrees angle of attack")


# ============================================================ Figures C1 and C2
def fig_ground_effect():
    alpha, hc = 4, 0.3
    base = naca4(0.04, 0.4, 0.12, 60)
    free = transform(base, alpha, invert=True, dy=0.35)
    lowest = min(y for _, y in transform(base, alpha, invert=True))
    near = transform(base, alpha, invert=True, dy=hc - lowest)
    Pf, Pg = Panels(free), Panels(near, ground=True)
    df_f, df_g = -Pf.cl, -Pg.cl
    print(f"  inverted NACA 4412, alpha={alpha}: free-air downforce C_L = {df_f:.3f}; h/c={hc}: {df_g:.3f} (+{(df_g/df_f-1)*100:.0f}%)")

    # ----- C1: streamlines
    W = 900
    S = 360
    boxf = (-0.55, 1.75, -0.2, 0.75)
    boxg = (-0.55, 1.75, 0.0, 0.75)
    ox = 30 + 0.55 * S
    parts = []
    oy1 = 20 + 0.75 * S
    seeds_f = [-0.17 + 0.065 * i for i in range(15)]
    parts += flow_panel(Pf, ox, oy1, S, boxf, seeds_f, "(a) Free air: no ground nearby")
    parts.append(text(ox + 1.25 * S, oy1 - 0.53 * S, sub("Downforce C", "L", 13) + f" = {df_f:.2f}", 13, raw=True, color=INK, halo=True))
    oy2 = oy1 - boxf[2] * S + 40 + 0.75 * S
    seeds_g = [0.025, 0.07, 0.115, 0.16, 0.205, 0.25] + [0.3 + 0.065 * i for i in range(7)]
    parts += flow_panel(Pg, ox, oy2, S, boxg, seeds_g, f"(b) Near the ground: h/c = {hc} (moving ground)", ground_y=0)
    parts.append(text(ox + 1.25 * S, oy2 - 0.53 * S, sub("Downforce C", "L", 13) + f" = {df_g:.2f}  (+{(df_g/df_f-1)*100:.0f}%)", 13, raw=True, color=INK, halo=True))
    # ground motion arrow
    gy = oy2 + 30
    parts.append(line(ox + 0.55 * S, gy, ox + 0.85 * S, gy, stroke=MUTED, width=1.5, marker="arrM"))
    parts.append(text(ox + 0.88 * S, gy + 4, "ground moves at V∞ relative to the wing", 12, color=MUTED))
    # ride height dimension
    lx = near[0][0] if False else None
    xlow = min(near, key=lambda p: p[1])
    xp, yp = ox + xlow[0] * S, oy2 - xlow[1] * S
    parts.append(line(xp, yp + 3, xp, oy2 - 3, stroke="#b2182b", width=1.3, marker="arrR"))
    parts.append(text(xp + 6, (yp + oy2) / 2 + 4, "h", 13, color="#b2182b", weight="700", italic=True))
    parts += speed_legend(220, oy2 + 58)
    H1 = int(oy2 + 120)
    c1 = svg(W, H1, parts, "Streamlines around an inverted wing in free air and close to a moving ground")

    # ----- C2: Cp comparison + schematic trend
    parts = []
    x_le_f = min(x for x, _ in free); x_le_g = min(x for x, _ in near)
    ax, m = cp_axes(90, 50, 340, 260, -1.0, 2.5, 0.5, "(a) Surface Cₚ (panel method)")
    parts += ax
    parts.append(cp_curve(Pf, x_le_f, m, "#8f9bab", 2.0, dash="6 4"))
    parts.append(cp_curve(Pg, x_le_g, m, ACCENT, 2.2))
    parts.append(line(300, 66, 330, 66, stroke="#8f9bab", width=2, dash="6 4"))
    parts.append(text(336, 70, "Free air", 12, color=MUTED))
    parts.append(line(300, 86, 330, 86, stroke=ACCENT, width=2.2))
    parts.append(text(336, 90, f"h/c = {hc}", 12, color=ACCENT))
    tx, ty = m(0.42, -1.55)
    parts.append(text(tx, ty, "lower (suction) surface", 12, color=MUTED, italic=True, halo=True))
    tx, ty = m(0.42, 0.55)
    parts.append(text(tx, ty, "upper (pressure) surface", 12, color=MUTED, italic=True, halo=True))

    # schematic downforce vs h/c
    gx, gy0, gw, gh = 540, 50, 320, 260
    parts.append(text(gx, gy0 - 12, "(b) Schematic trend (after [11], [12])", 14, weight="700"))
    def trend(h):
        enh = 1 + 1.0 / (1 + (h / 0.12) ** 1.4)
        red = 1 - 0.8 * math.exp(-(h / 0.075) ** 1.8)
        return enh * red
    hs = [0.005 + i * 0.003 for i in range(200)]
    vals = [trend(h) for h in hs]
    vmax = max(vals); hpk = hs[vals.index(vmax)]
    mx = lambda h: gx + h / 0.6 * gw
    my = lambda v: gy0 + gh - (v - 0.3) / (vmax + 0.15 - 0.3) * gh
    parts.append(f'<rect x="{mx(0):.1f}" y="{gy0}" width="{mx(hpk)-mx(0):.1f}" height="{gh}" fill="#fbecea"/>')
    parts.append(f'<rect x="{mx(hpk):.1f}" y="{gy0}" width="{mx(0.6)-mx(hpk):.1f}" height="{gh}" fill="#eaf2fa"/>')
    parts.append(line(gx, gy0 + gh, gx + gw, gy0 + gh, stroke=MUTED, width=1, marker="arrM"))
    parts.append(line(gx, gy0 + gh, gx, gy0 - 2, stroke=MUTED, width=1, marker="arrM"))
    parts.append(line(mx(0), my(1), mx(0.6), my(1), stroke="#8f9bab", width=1.3, dash="5 4"))
    parts.append(text(mx(0.59), my(1) + 16, "free-air value", 12, "end", MUTED))
    parts.append(poly([(mx(h), my(v)) for h, v in zip(hs, vals)], stroke=ACCENT, width=2.4))
    parts.append(f'<circle cx="{mx(hpk):.1f}" cy="{my(vmax):.1f}" r="4" fill="{ACCENT}"/>')
    parts.append(text(mx(hpk) + 8, my(vmax) - 8, "maximum downforce", 12, color=ACCENT, weight="600"))
    rx, ry = (mx(0) + mx(hpk)) / 2 + 4, gy0 + gh - 10
    parts.append(f'<text x="{rx:.1f}" y="{ry:.1f}" font-size="12" fill="#b2182b" transform="rotate(-90 {rx:.1f} {ry:.1f})">force reduction</text>')
    parts.append(text((mx(hpk) + mx(0.6)) / 2, gy0 + gh - 14, "force enhancement", 12, "middle", ACCENT))
    parts.append(line(mx(hpk), gy0 + gh, mx(hpk), gy0 + gh + 5, stroke=MUTED, width=1))
    parts.append(text(mx(hpk), gy0 + gh + 18, "≈ 0.1", 12, "middle", MUTED))
    parts.append(text(gx + gw / 2, gy0 + gh + 38, "Ride height h/c →", 13, "middle", MUTED))
    parts.append(f'<text x="{gx-14:.1f}" y="{gy0+gh/2:.1f}" font-size="13" fill="{MUTED}" text-anchor="middle" '
                 f'transform="rotate(-90 {gx-14:.1f} {gy0+gh/2:.1f})">Downforce (qualitative)</text>')
    parts.append(text(gx, gy0 + gh + 60, "Not to scale. Below h/c ≈ 0.1, trailing-edge", 12, color=MUTED, italic=True))
    parts.append(text(gx, gy0 + gh + 76, "separation on the suction surface reduces downforce.", 12, color=MUTED, italic=True))
    c2 = svg(W, 400, parts, "Surface pressure on an inverted wing in free air and near the ground, and the schematic downforce trend with ride height")
    return c1, c2


if __name__ == "__main__":
    write("appendix-venturi.svg", fig_venturi())
    write("appendix-airfoil-anatomy.svg", fig_anatomy())
    print("solving panel methods ...")
    write("appendix-airfoil-flow.svg", fig_airfoil_flow())
    c1, c2 = fig_ground_effect()
    write("appendix-ground-effect-flow.svg", c1)
    write("appendix-ground-effect-cp.svg", c2)
