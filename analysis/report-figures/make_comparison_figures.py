"""Regenerate the rear-wing and full-car comparison bar charts (Figures 8, 11, 14).

All numbers are read from the tables in section-6-2.html, so the charts always
match the report:
    Table 2 -> Figure 8   assets/report-figure-rear-wing-straight.png
    Table 3 -> Figure 11  assets/report-figure-rear-wing-cornering.png
    Table 4 -> Figure 14  assets/report-figure-full-car-comparison.png

Percentage changes in C_L/C_D are computed from the downforce and drag columns
(not from the rounded C_L/C_D column), so they agree with the text.

Each chart is drawn as SVG (pure Python) and rasterised to PNG at 2x with
headless Microsoft Edge / Chrome.

Usage:  python make_comparison_figures.py [--svg-only]
"""
import html, math, os, re, shutil, subprocess, sys, tempfile

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
ASSETS = os.path.join(ROOT, "assets")

INK, AXIS_LABEL, GRID = "#1f2a37", "#5a6b80", "#e3e6ea"
GREY, SELECTED = "#9ca6b2", "#1f5687"
FONT = "Inter,'Segoe UI',system-ui,sans-serif"
MINUS = "\u2212"


# ------------------------------------------------------------------ table data
def read_tables():
    src = open(os.path.join(ROOT, "section-6-2.html"), encoding="utf-8").read()
    tables = []
    for t in re.findall(r"<table.*?</table>", src, re.S):
        rows = []
        for r in re.findall(r"<tr([^>]*)>(.*?)</tr>", t, re.S):
            cells = [html.unescape(re.sub(r"<[^>]+>", "", c)).replace("\xa0", " ")
                     for c in re.findall(r"<t[hd][^>]*>(.*?)</t[hd]>", r[1], re.S)]
            cells = [" ".join(c.split()) for c in cells]
            rows.append(("selected-row" in r[0], cells))
        tables.append(rows)
    return tables


def num(s):
    return float(s.replace(MINUS, "-").replace("\u2212", "-"))


# ------------------------------------------------------------------- formatting
def signed(v, nd=1, unit=""):
    s = f"{abs(v):.{nd}f}"
    return ("+" if v >= 0 else MINUS) + s + unit


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def nice_step(span, target=4):
    raw = span / target
    mag = 10 ** math.floor(math.log10(raw))
    for m in (1, 2, 2.5, 5, 10):
        if raw <= m * mag:
            return m * mag
    return 10 * mag


def tick_fmt(v, step):
    if abs(v) < 1e-9:
        v = 0.0
    nd = 0 if float(step).is_integer() else 1
    s = f"{abs(v):.{nd}f}"
    return (MINUS if v < 0 else "") + s


# -------------------------------------------------------------------- drawing
def text(x, y, s, size=14, anchor="start", color=INK, weight=400, raw=False):
    body = s if raw else esc(s)
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" text-anchor="{anchor}" '
            f'fill="{color}" font-weight="{weight}">{body}</text>')


def clcd(size):
    sub = size * 0.68
    return (f'C<tspan dy="{size*0.25:.1f}" font-size="{sub:.1f}">L</tspan>'
            f'<tspan dy="{-size*0.25:.1f}">/C</tspan>'
            f'<tspan dy="{size*0.25:.1f}" font-size="{sub:.1f}">D</tspan>')


def panel(x0, x1, top, bottom, values, selected, labels, title, xlabel, n_rows,
          fixed=None, label_bold_selected=False):
    """Horizontal bars. values/labels top-to-bottom. Returns svg parts."""
    out = []
    lo, hi = min(0, min(values)), max(0, max(values))
    if fixed:                       # (axis min, axis max, tick step)
        vmin, vmax, step = fixed
    else:                           # leave ~30% of the span for the value labels
        span = (hi - lo) or 1
        vmax = hi + 0.32 * span if hi > 0 else 0.05 * span
        vmin = lo - 0.45 * span if lo < 0 else -0.06 * span  # labels sit left of negative bars
        step = nice_step(vmax - vmin, 5)
    lo_t = math.ceil(vmin / step - 1e-9) * step
    hi_t = math.floor(vmax / step + 1e-9) * step
    X = lambda v: x0 + (v - vmin) / (vmax - vmin) * (x1 - x0)

    # grid + ticks
    t = lo_t
    while t <= hi_t + 1e-9:
        if abs(t) > 1e-9:
            out.append(f'<line x1="{X(t):.1f}" y1="{top:.1f}" x2="{X(t):.1f}" y2="{bottom:.1f}" stroke="{GRID}" stroke-width="1"/>')
        out.append(f'<line x1="{X(t):.1f}" y1="{bottom:.1f}" x2="{X(t):.1f}" y2="{bottom+4:.1f}" stroke="{INK}" stroke-width="1"/>')
        out.append(text(X(t), bottom + 23, tick_fmt(t, step), 13.5, "middle"))
        t += step
    # bars
    pitch = (bottom - top) / n_rows
    bh = pitch * 0.6
    for i, (v, lab) in enumerate(zip(values, labels)):
        yc = top + pitch * (i + 0.5)
        col = SELECTED if selected[i] else GREY
        xa, xb = sorted((X(0), X(v)))
        out.append(f'<rect x="{xa:.1f}" y="{yc-bh/2:.1f}" width="{xb-xa:.1f}" height="{bh:.1f}" fill="{col}"/>')
        weight = 600 if (label_bold_selected and selected[i]) else 400
        if v >= 0:
            out.append(text(X(v) + 10, yc + 5, lab, 13.5, "start", weight=weight))
        else:
            out.append(text(X(v) - 10, yc + 5, lab, 13.5, "end", weight=weight))
    # zero line and spines
    out.append(f'<line x1="{X(0):.1f}" y1="{top:.1f}" x2="{X(0):.1f}" y2="{bottom:.1f}" stroke="{INK}" stroke-width="1.2"/>')
    out.append(f'<line x1="{x0:.1f}" y1="{top:.1f}" x2="{x0:.1f}" y2="{bottom:.1f}" stroke="{INK}" stroke-width="1"/>')
    out.append(f'<line x1="{x0:.1f}" y1="{bottom:.1f}" x2="{x1:.1f}" y2="{bottom:.1f}" stroke="{INK}" stroke-width="1"/>')
    out.append(text(x0, top - 17, title, 16, raw=True))
    out.append(text((x0 + x1) / 2, bottom + 48, xlabel, 14, "middle", AXIS_LABEL, raw=True))
    return out


def category_labels(x, top, bottom, lines_list):
    out = []
    pitch = (bottom - top) / len(lines_list)
    for i, lines in enumerate(lines_list):
        yc = top + pitch * (i + 0.5)
        lh = 23.5
        y = yc - lh * (len(lines) - 1) / 2 + 5
        for j, l in enumerate(lines):
            out.append(text(x, y + j * lh, l, 13.5, "end"))
    return out


def svg(w, h, parts, title):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}" '
            f'font-family="{FONT}"><title>{esc(title)}</title>'
            f'<rect width="{w}" height="{h}" fill="#ffffff"/>\n' + "\n".join(parts) + "\n</svg>\n")


# ------------------------------------------------------------- figure builders
def delta_figure(rows, label_split, H, title, rw_col_name):
    head = rows[0][1]
    ci = {name: i for i, name in enumerate(head)}
    df, dr, rw = ci["Full-car downforce (N)"], ci["Full-car drag (N)"], ci[rw_col_name]
    data = rows[1:]
    base = data[0][1]
    assert "baseline" in base[0].lower(), base[0]
    configs = [r for r in data[1:] if not r[0]] + [r for r in data[1:] if r[0]]  # selected last
    b_ratio = num(base[df]) / num(base[dr])
    rw_d = [num(c[rw]) - num(base[rw]) for _, c in configs]
    df_d = [num(c[df]) - num(base[df]) for _, c in configs]
    pct = [(num(c[df]) / num(c[dr]) / b_ratio - 1) * 100 for _, c in configs]
    sel = [s for s, _ in configs]
    names = [label_split(c[0].replace(" (selected)", "")) for _, c in configs]

    W = 1010
    top, bottom = 42, H - 68
    xs = [(137, 412), (429, 703), (720, 995)]
    P = category_labels(132, top, bottom, names)
    P += panel(*xs[0], top, bottom, rw_d, sel, [signed(v, 1, " N") for v in rw_d],
               "(a) Rear-wing downforce", "Change vs R26 baseline (N)", len(configs))
    P += panel(*xs[1], top, bottom, df_d, sel, [signed(v, 1, " N") for v in df_d],
               "(b) Full-car downforce", "Change vs R26 baseline (N)", len(configs))
    P += panel(*xs[2], top, bottom, pct, sel, [signed(v, 1, "%") for v in pct],
               "(c) Full-car " + clcd(16), "Change vs R26 baseline (%)", len(configs))
    print(f"  {title}:")
    for n, a, b, c in zip(names, rw_d, df_d, pct):
        print(f"    {' '.join(n):48s} RW {a:+6.1f} N   FC {b:+6.1f} N   CL/CD {c:+5.2f}%")
    return svg(W, H, P, title)


def full_car_figure(rows):
    head = rows[0][1]
    ci = {name: i for i, name in enumerate(head)}
    df, dr = ci["Full-car downforce (N)"], ci["Full-car drag (N)"]
    base, new = rows[1][1], rows[2][1]
    assert rows[2][0], "second row should be the selected R27e row"
    vals_df = [num(base[df]), num(new[df])]
    vals_dr = [num(base[dr]), num(new[dr])]
    ratio = [d / r for d, r in zip(vals_df, vals_dr)]
    ch = lambda a: (a[1] / a[0] - 1) * 100
    sel = [False, True]
    W, H = 1010, 260
    top, bottom = 42, 192
    P = category_labels(107, top, bottom, [[base[0]], [new[0]]])
    P += panel(112, 352, top, bottom, vals_df, sel,
               [f"{vals_df[0]:.1f} N", f"{vals_df[1]:.1f} N ({signed(ch(vals_df), 1, '%')})"],
               "(a) Full-car downforce", "Downforce (N)", 2, fixed=(0, 500, 100), label_bold_selected=True)
    P += panel(422, 662, top, bottom, vals_dr, sel,
               [f"{vals_dr[0]:.1f} N", f"{vals_dr[1]:.1f} N ({signed(ch(vals_dr), 1, '%')})"],
               "(b) Full-car drag", "Drag (N)", 2, fixed=(0, 220, 50), label_bold_selected=True)
    P += panel(731, 966, top, bottom, ratio, sel,
               [f"{ratio[0]:.2f}", f"{ratio[1]:.2f} ({signed(ch(ratio), 1, '%')})"],
               "(c) Full-car " + clcd(16), clcd(14), 2, fixed=(0, 3.5, 1), label_bold_selected=True)
    print(f"  Figure 14: CL/CD {ratio[0]:.3f} -> {ratio[1]:.3f} ({ch(ratio):+.2f}%), "
          f"downforce {ch(vals_df):+.2f}%, drag {ch(vals_dr):+.2f}%")
    return svg(W, H, P, "Full-car comparison of the baseline R26e and the R27e")


def split_straight(name):            # "3rd 70°, slot 20.5 mm" -> two lines
    a, b = name.split(", slot")
    return [a + ",", "slot" + b]


def split_cornering(name):           # "250 mm, 39° / 115 mm, 67° / 21 mm" -> three lines
    a, b, c = [p.strip() for p in name.split("/")]
    return ["2nd " + a, "3rd " + b, "slot " + c]


# ----------------------------------------------------------------- rasterising
def find_browser():
    for p in [r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
              r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
              r"C:\Program Files\Google\Chrome\Application\chrome.exe",
              shutil.which("msedge") or "", shutil.which("google-chrome") or "", shutil.which("chromium") or ""]:
        if p and os.path.exists(p):
            return p
    return None


def rasterise(svg_text, w, h, out_png, browser, tmp):
    src = os.path.join(tmp, os.path.basename(out_png).replace(".png", ".svg"))
    open(src, "w", encoding="utf-8").write(svg_text)
    profile = os.path.join(tmp, "profile")
    cmd = [browser, "--headless=new", "--disable-gpu", "--hide-scrollbars",
           f"--user-data-dir={profile}", "--force-device-scale-factor=2",
           f"--window-size={w},{h}", f"--screenshot={out_png}", "file:///" + src.replace("\\", "/")]
    subprocess.run(cmd, timeout=60, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print("  wrote", out_png)


def main():
    t = read_tables()
    straight, corner, full = t[0], t[1], t[2]
    figs = [
        ("report-figure-rear-wing-straight.png", 1010, 460,
         delta_figure(straight, split_straight, 460, "Figure 8", "Rear-wing downforce (N)")),
        ("report-figure-rear-wing-cornering.png", 1010, 540,
         delta_figure(corner, split_cornering, 540, "Figure 11", "Rear-wing downforce (N)")),
        ("report-figure-full-car-comparison.png", 1010, 260, full_car_figure(full)),
    ]
    tmp = tempfile.mkdtemp(prefix="report-figs-")
    if "--svg-only" in sys.argv:
        for name, w, h, s in figs:
            p = os.path.join(tmp, name.replace(".png", ".svg"))
            open(p, "w", encoding="utf-8").write(s)
            print("  wrote", p)
        return
    browser = find_browser()
    if not browser:
        sys.exit("No Edge/Chrome found; run with --svg-only and convert the SVGs manually.")
    for name, w, h, s in figs:
        rasterise(s, w, h, os.path.join(ASSETS, name), browser, tmp)
    shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
