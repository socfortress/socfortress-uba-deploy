"""Draws the README images (light and dark variants). Run: python3 docs/images/generate.py"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from xml.sax.saxutils import escape

OUT = Path(__file__).parent
FONT = "-apple-system, BlinkMacSystemFont, 'Segoe UI', Helvetica, Arial, sans-serif"

THEMES = {
    "light": {
        "surface": "#fcfcfb",
        "panel": "#f3f2ef",
        "border": "#d9d8d4",
        "grid": "#e6e5e1",
        "text": "#0b0b0b",
        "text2": "#52514e",
        "muted": "#6f6e69",
        "accent": "#2a78d6",
        "accent_panel": "#eaf2fc",
        "critical": "#d03b3b",
    },
    "dark": {
        "surface": "#1a1a19",
        "panel": "#242422",
        "border": "#3a3a37",
        "grid": "#2e2e2c",
        "text": "#ffffff",
        "text2": "#c3c2b7",
        "muted": "#9a998f",
        "accent": "#3987e5",
        "accent_panel": "#1d2a3b",
        "critical": "#d03b3b",
    },
}


def text(x, y, s, size=13, fill="text", weight=400, anchor="start", t=None):
    return (
        f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{weight}" fill="{t[fill]}" '
        f'text-anchor="{anchor}">{escape(s)}</text>'
    )


def svg(w, h, body, t, title):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
        f'font-family="{FONT}" role="img" aria-label="{escape(title)}">'
        f"<title>{escape(title)}</title>"
        f'<rect width="{w}" height="{h}" rx="12" fill="{t["surface"]}"/>'
        f"{''.join(body)}</svg>\n"
    )


# -- 1. How it plugs in ----------------------------------------------------------------------------


def box(x, y, w, h, title, lines, t, accent=False, note=None):
    stroke = t["accent"] if accent else t["border"]
    fill = t["accent_panel"] if accent else t["panel"]
    out = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="10" fill="{fill}" stroke="{stroke}" stroke-width="{2 if accent else 1}"/>']
    out.append(text(x + 14, y + 26, title, 15, "text", 650, t=t))
    top = y + 50
    if note:
        out.append(text(x + 14, y + 44, note, 11.5, "muted", t=t))
        top = y + 68
    bullets = any(line.startswith("- ") for line in lines)
    for i, line in enumerate(lines):
        bullet = line.startswith("- ")
        indent = 24 if bullets and not bullet else 14  # continuation lines align with the bullet's text
        out.append(text(x + indent, top + i * 19, ("• " + line[2:]) if bullet else line, 12.5, "text2", t=t))
    return out


def arrow(x1, y1, x2, y2, t, dashed=False, both=False):
    dash = ' stroke-dasharray="5 4"' if dashed else ""
    start = ' marker-start="url(#head-start)"' if both else ""
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{t["muted"]}" stroke-width="1.6"{dash}{start} marker-end="url(#head)"/>'


def how_it_works(t):
    defs = (
        "<defs>"
        f'<marker id="head" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0,0 L10,5 L0,10 z" fill="{t["muted"]}"/></marker>'
        f'<marker id="head-start" viewBox="0 0 10 10" refX="1" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M10,0 L0,5 L10,10 z" fill="{t["muted"]}"/></marker>'
        "</defs>"
    )
    b = [defs]
    b.append(text(24, 36, "How SOCFortress UBA plugs into CoPilot", 18, "text", 700, t=t))
    b += box(24, 70, 176, 78, "Endpoints", ["Windows, Linux, macOS", "(Wazuh agents)"], t)
    b += box(24, 172, 176, 78, "Microsoft 365", ["sign-ins, mail, files,", "admin changes"], t)
    b += box(262, 104, 176, 112, "Wazuh + Graylog", ["collect every customer's", "events, as today"], t)
    b += box(262, 300, 176, 70, "Wazuh indexer", ["the stored history"], t)
    b += box(
        548,
        70,
        232,
        180,
        "SOCFortress UBA",
        ["- learns what is normal for", "each person and computer", "- scores what is new or unusual", "- adds risk up, raises alerts"],
        t,
        accent=True,
        note="on its own VM",
    )
    b += box(
        850,
        70,
        186,
        180,
        "CoPilot",
        ["- incident alerts", "- risk per person", "- findings and evidence", "- verdicts tune UBA", "- one-click setup"],
        t,
    )
    # sources -> Graylog
    b.append(arrow(200, 109, 260, 140, t))
    b.append(arrow(200, 211, 260, 182, t))
    b.append(text(230, 104, "events", 11.5, "muted", anchor="middle", t=t))
    # Graylog -> UBA
    b.append(arrow(438, 160, 546, 160, t))
    b.append(text(492, 140, "copy of", 11.5, "muted", anchor="middle", t=t))
    b.append(text(492, 154, "behavior events", 11.5, "muted", anchor="middle", t=t))
    # indexer -> UBA
    b.append(arrow(438, 335, 600, 252, t, dashed=True))
    b.append(text(560, 318, "history to learn from,", 11.5, "muted", t=t))
    b.append(text(560, 333, "evidence for each finding", 11.5, "muted", t=t))
    # UBA <-> CoPilot
    b.append(arrow(780, 120, 848, 120, t))
    b.append(text(814, 110, "alerts", 11.5, "muted", anchor="middle", t=t))
    b.append(arrow(780, 200, 848, 200, t, both=True))
    b.append(text(814, 190, "API", 11.5, "muted", anchor="middle", t=t))
    b.append(
        text(
            24,
            410,
            "Setup is one click per customer in CoPilot: it creates the Graylog routing and registers the customer with UBA.",
            12.5,
            "text2",
            t=t,
        )
    )
    return svg(1060, 432, b, t, "How SOCFortress UBA plugs into CoPilot")


# -- 2. Small findings add up ----------------------------------------------------------------------

DAY = datetime(2026, 10, 1)
FINDINGS = [  # (time, points, what) - the rules' real scores
    ("08:52", 30, "Sign-in from a country this user never signed in from"),
    ("08:58", 10, "Sign-in from a device type this user never used"),
    ("09:40", 25, "First password-only (legacy) sign-in by this user"),
    ("10:20", 30, "Mail forwarding to another address configured"),
    ("11:15", 25, "File downloads far above this user's normal"),
]
THRESHOLD = 100
HALF_LIFE_H = 72


def at(hm):
    h, m = map(int, hm.split(":"))
    return DAY + timedelta(hours=h, minutes=m)


def risk_after(i):
    """Risk right after finding i: every earlier finding fades with a 3-day half-life."""
    now = at(FINDINGS[i][0])
    return sum(p * 0.5 ** ((now - at(t)).total_seconds() / 3600 / HALF_LIFE_H) for t, p, _ in FINDINGS[: i + 1])


def risk_chart(t):
    w, h = 1060, 520
    left, right, top, bottom = 70, 1030, 96, 330
    start, end = at("08:30"), at("12:00")
    y_max = 130

    def x(d):
        return left + (d - start).total_seconds() / (end - start).total_seconds() * (right - left)

    def y(v):
        return bottom - v / y_max * (bottom - top)

    b = [text(24, 36, "Small findings add up to one alert", 18, "text", 700, t=t)]
    b.append(
        text(
            24,
            60,
            "One account, one morning (illustrative). Points are the rules' real scores; each finding fades with a 3-day half-life.",
            12.5,
            "text2",
            t=t,
        )
    )
    # grid + y axis
    for v in (0, 50, 100):
        b.append(f'<line x1="{left}" y1="{y(v):.1f}" x2="{right}" y2="{y(v):.1f}" stroke="{t["grid"]}" stroke-width="1"/>')
        b.append(text(left - 10, y(v) + 4, str(v), 11.5, "muted", anchor="end", t=t))
    b.append(text(left - 10, top - 14, "risk", 11.5, "muted", anchor="end", t=t))
    for hm in ("09:00", "10:00", "11:00", "12:00"):
        b.append(text(x(at(hm)), bottom + 20, hm, 11.5, "muted", anchor="middle", t=t))
    # threshold
    b.append(
        f'<line x1="{left}" y1="{y(THRESHOLD):.1f}" x2="{right}" y2="{y(THRESHOLD):.1f}" stroke="{t["text2"]}" stroke-width="1.2" stroke-dasharray="6 5"/>'
    )
    b.append(text(left + 8, y(THRESHOLD) - 8, "alert threshold: 100 points", 12, "text2", t=t))
    # step line
    pts = [(x(start), y(0))]
    level = 0.0
    for i, (hm, _, _) in enumerate(FINDINGS):
        pts.append((x(at(hm)), y(level)))
        level = risk_after(i)
        pts.append((x(at(hm)), y(level)))
    pts.append((x(end), y(level)))
    path = " ".join(f"{'M' if i == 0 else 'L'}{px:.1f},{py:.1f}" for i, (px, py) in enumerate(pts))
    b.append(f'<path d="{path}" fill="none" stroke="{t["accent"]}" stroke-width="2" stroke-linejoin="round"/>')
    # markers with numbers
    for i, (hm, _, _) in enumerate(FINDINGS):
        cx, cy = x(at(hm)), y(risk_after(i))
        crossed = risk_after(i) >= THRESHOLD and (i == 0 or risk_after(i - 1) < THRESHOLD)
        color = t["critical"] if crossed else t["accent"]
        b.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="10" fill="{color}" stroke="{t["surface"]}" stroke-width="2"/>')
        b.append(f'<text x="{cx:.1f}" y="{cy + 4:.1f}" font-size="11" font-weight="700" fill="#ffffff" text-anchor="middle">{i + 1}</text>')
        if crossed:
            b.append(text(cx - 18, cy - 4, f"UBA alert: {round(risk_after(i))} points,", 12.5, "text", 650, anchor="end", t=t))
            b.append(text(cx - 18, cy + 12, "with all five findings as its story", 12.5, "text", 650, anchor="end", t=t))
    # numbered key
    for i, (hm, p, what) in enumerate(FINDINGS):
        ky = 372 + i * 26
        b.append(f'<circle cx="{left + 10}" cy="{ky - 4}" r="9" fill="{t["critical"] if i == len(FINDINGS) - 1 else t["accent"]}"/>')
        b.append(f'<text x="{left + 10}" y="{ky}" font-size="10.5" font-weight="700" fill="#ffffff" text-anchor="middle">{i + 1}</text>')
        b.append(text(left + 28, ky, f"{hm}", 12.5, "muted", t=t))
        b.append(text(left + 74, ky, f"+{p}", 12.5, "text", 650, t=t))
        b.append(text(left + 112, ky, what, 12.5, "text2", t=t))
    b.append(
        text(
            left + 520,
            372,
            "None of these alone is worth waking anyone up.",
            12.5,
            "text2",
            t=t,
        )
    )
    b.append(text(left + 520, 398, "Together, within one morning, they are one alert", 12.5, "text2", t=t))
    b.append(text(left + 520, 424, "an analyst can read and judge in a minute.", 12.5, "text2", t=t))
    return svg(w, h, b, t, "Small findings add up to one alert")


# -- 3. From noise to a few alerts -----------------------------------------------------------------

TILES = [
    ("~500,000", "events a day", ["Wazuh and Microsoft 365", "events UBA reads"], False),
    ("~110", "findings a day", ["unusual for that person", "or computer, with points"], False),
    ("~940", "Wazuh alerts a day", ["weighed as context,", "with capped points"], False),
    ("14", "UBA alerts in 5 days", ["each one a person or", "computer and its story"], True),
]


def noise_to_signal(t):
    w, h = 1060, 290
    b = [text(24, 36, "From noise to a few alerts worth reading", 18, "text", 700, t=t)]
    b.append(
        text(
            24,
            60,
            "SOCFortress lab, early October 2026: one Microsoft 365 tenant with about 8,500 users, plus Wazuh endpoints.",
            12.5,
            "text2",
            t=t,
        )
    )
    tile_w, gap, x0, y0 = 226, 34, 24, 88
    for i, (num, label, lines, accent) in enumerate(TILES):
        x = x0 + i * (tile_w + gap)
        stroke = t["accent"] if accent else t["border"]
        fill = t["accent_panel"] if accent else t["panel"]
        b.append(f'<rect x="{x}" y="{y0}" width="{tile_w}" height="150" rx="10" fill="{fill}" stroke="{stroke}" stroke-width="{2 if accent else 1}"/>')
        b.append(text(x + 18, y0 + 52, num, 34, "text", 700, t=t))
        b.append(text(x + 18, y0 + 80, label, 14, "text", 600, t=t))
        for j, line in enumerate(lines):
            b.append(text(x + 18, y0 + 106 + j * 18, line, 12.5, "text2", t=t))
        if i == 1:  # findings and Wazuh alerts both feed the risk: a plus, not a step
            cx, cy = x + tile_w + gap / 2, y0 + 75
            b.append(f'<path d="M{cx - 8},{cy} L{cx + 8},{cy} M{cx},{cy - 8} L{cx},{cy + 8}" stroke="{t["muted"]}" stroke-width="2" stroke-linecap="round"/>')
        elif i < len(TILES) - 1:
            ax = x + tile_w + 9
            b.append(f'<path d="M{ax},{y0 + 63} L{ax + 16},{y0 + 75} L{ax},{y0 + 87}" fill="none" stroke="{t["muted"]}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>')
    b.append(text(24, 270, "Analysts read alerts, not events: every alert links to the findings and the original records behind it.", 12.5, "text2", t=t))
    return svg(w, h, b, t, "From noise to a few alerts worth reading")


if __name__ == "__main__":
    for mode, t in THEMES.items():
        (OUT / f"how-it-works-{mode}.svg").write_text(how_it_works(t))
        (OUT / f"risk-adds-up-{mode}.svg").write_text(risk_chart(t))
        (OUT / f"noise-to-signal-{mode}.svg").write_text(noise_to_signal(t))
    print("risk after each finding:", [round(risk_after(i), 1) for i in range(len(FINDINGS))])
