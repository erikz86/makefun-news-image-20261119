#!/usr/bin/env python3
"""make.fun news-image-20261119: one image that sums up Thursday 19 Nov 2026.

The program draws a newspaper front page, "THE WORLD TODAY", entirely with
the Python standard library: its own 5x7 bitmap font, its own drawing
primitives (rectangles, lines, circles, polygons) and its own PNG encoder
(zlib + struct). No network, no files read at run time, no timestamps, no
randomness -- so two runs always write the same bytes.

Run:  mkdir -p out && MAKEFUN_OUTPUT_DIR=out python3 main.py
Writes: <out>/entry.png  (1024x1024 PNG, well under 1 MiB)
"""

import hashlib
import math
import os
import struct
import sys
import zlib

W, H = 1024, 1024

# ---------------------------------------------------------------- palette ---
PAPER = (245, 239, 224)   # warm newsprint
INK = (25, 23, 19)        # near-black ink
DECK = (58, 53, 45)       # softer ink for body copy
RED = (166, 30, 30)       # section red
BLUE = (31, 58, 95)       # flag / accent blue
GOLD = (214, 164, 32)     # star gold
RULE = (138, 131, 120)    # hairline grey
WHITE = (255, 255, 255)

# ------------------------------------------------------------- 5x7 font ---
# Each glyph is 7 rows of 5 cells ('#' = ink, '.' = empty). All copy in the
# image is upper-case ASCII, so only these glyphs are needed.
FONT = {
    "A": (".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "B": ("####.", "#...#", "#...#", "####.", "#...#", "#...#", "####."),
    "C": (".####", "#....", "#....", "#....", "#....", "#....", ".####"),
    "D": ("####.", "#...#", "#...#", "#...#", "#...#", "#...#", "####."),
    "E": ("#####", "#....", "#....", "####.", "#....", "#....", "#####"),
    "F": ("#####", "#....", "#....", "####.", "#....", "#....", "#...."),
    "G": (".####", "#....", "#....", "#.###", "#...#", "#...#", ".###."),
    "H": ("#...#", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"),
    "I": ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "#####"),
    "J": ("..###", "...#.", "...#.", "...#.", "...#.", "#..#.", ".##.."),
    "K": ("#...#", "#..#.", "#.#..", "##...", "#.#..", "#..#.", "#...#"),
    "L": ("#....", "#....", "#....", "#....", "#....", "#....", "#####"),
    "M": ("#...#", "##.##", "#.#.#", "#.#.#", "#...#", "#...#", "#...#"),
    "N": ("#...#", "##..#", "##..#", "#.#.#", "#..##", "#..##", "#...#"),
    "O": (".###.", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "P": ("####.", "#...#", "#...#", "####.", "#....", "#....", "#...."),
    "Q": (".###.", "#...#", "#...#", "#...#", "#.#.#", "#..#.", ".##.#"),
    "R": ("####.", "#...#", "#...#", "####.", "#.#..", "#..#.", "#...#"),
    "S": (".####", "#....", "#....", ".###.", "....#", "....#", "####."),
    "T": ("#####", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."),
    "U": ("#...#", "#...#", "#...#", "#...#", "#...#", "#...#", ".###."),
    "V": ("#...#", "#...#", "#...#", "#...#", "#...#", ".#.#.", "..#.."),
    "W": ("#...#", "#...#", "#...#", "#.#.#", "#.#.#", "##.##", "#...#"),
    "X": ("#...#", "#...#", ".#.#.", "..#..", ".#.#.", "#...#", "#...#"),
    "Y": ("#...#", "#...#", ".#.#.", "..#..", "..#..", "..#..", "..#.."),
    "Z": ("#####", "....#", "...#.", "..#..", ".#...", "#....", "#####"),
    "0": (".###.", "#..##", "#.#.#", "##..#", "#...#", "#...#", ".###."),
    "1": ("..#..", ".##..", "..#..", "..#..", "..#..", "..#..", ".###."),
    "2": (".###.", "#...#", "....#", "...#.", "..#..", ".#...", "#####"),
    "3": ("####.", "....#", "....#", ".###.", "....#", "....#", "####."),
    "4": ("...#.", "..##.", ".#.#.", "#..#.", "#####", "...#.", "...#."),
    "5": ("#####", "#....", "####.", "....#", "....#", "#...#", ".###."),
    "6": (".###.", "#....", "#....", "####.", "#...#", "#...#", ".###."),
    "7": ("#####", "....#", "...#.", "...#.", "..#..", "..#..", "..#.."),
    "8": (".###.", "#...#", "#...#", ".###.", "#...#", "#...#", ".###."),
    "9": (".###.", "#...#", "#...#", ".####", "....#", "....#", ".###."),
    " ": (".....", ".....", ".....", ".....", ".....", ".....", "....."),
    ".": (".....", ".....", ".....", ".....", ".....", ".##..", ".##.."),
    ",": (".....", ".....", ".....", ".....", "..#..", "..#..", ".#..."),
    ":": (".....", ".##..", ".##..", ".....", ".....", ".##..", ".##.."),
    ";": (".....", ".##..", ".##..", ".....", ".....", ".##..", ".#..."),
    "!": ("..#..", "..#..", "..#..", "..#..", "..#..", ".....", "..#.."),
    "?": (".###.", "#...#", "....#", "...#.", "..#..", ".....", "..#.."),
    "'": ("..#..", "..#..", ".....", ".....", ".....", ".....", "....."),
    '"': (".#.#.", ".#.#.", ".....", ".....", ".....", ".....", "....."),
    "-": (".....", ".....", ".....", ".###.", ".....", ".....", "....."),
    "(": ("...##", "..#..", ".#...", ".#...", ".#...", "..#..", "...##"),
    ")": ("##...", "..#..", "...#.", "...#.", "...#.", "..#..", "##..."),
    "/": ("....#", "....#", "...#.", "..#..", ".#...", "#....", "#...."),
    "%": ("##..#", "##.#.", "...#.", "..#..", ".#...", "#.###", "#..##"),
    "$": ("..#..", ".####", "#.#.#", ".###.", "..#.#", "####.", "..#.."),
    "&": (".##..", "#..#.", "#..#.", ".#...", "#.#.#", "#..#.", ".##.#"),
    "+": (".....", "..#..", "..#..", ".###.", "..#..", "..#..", "....."),
    "=": (".....", ".....", ".###.", ".....", ".###.", ".....", "....."),
    "*": (".....", ".#.#.", ".###.", "#####", ".###.", ".#.#.", "....."),
    "#": (".#.#.", ".#.#.", "#####", ".#.#.", "#####", ".#.#.", ".#.#."),
    "@": (".###.", "#...#", "#.###", "#.#.#", "#.###", "#....", ".###."),
    "<": ("...#.", "..#..", ".#...", "#....", ".#...", "..#..", "...#."),
    ">": (".#...", "..#..", "...#.", "....#", "...#.", "..#..", ".#..."),
    "_": (".....", ".....", ".....", ".....", ".....", ".....", "#####"),
    "|": ("..#..", "..#..", "..#..", "..#..", "..#..", "..#..", "..#.."),
    "\u2022": (".....", ".....", ".###.", ".###.", ".###.", ".....", "....."),
}


def text_width(text, scale):
    """Pixel width of text at the given font scale."""
    if not text:
        return 0
    return len(text) * 6 * scale - scale


def wrap_text(text, scale, max_width):
    """Greedy word wrap; returns a list of lines fitting max_width px."""
    lines, cur = [], ""
    for word in text.split(" "):
        trial = word if not cur else cur + " " + word
        if text_width(trial, scale) <= max_width:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


# ---------------------------------------------------------------- canvas ---
class Canvas:
    def __init__(self, w, h, bg):
        self.w, self.h = w, h
        self.px = bytearray(w * h * 3)
        self.fill_rect(0, 0, w, h, bg)

    def set(self, x, y, color):
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i], self.px[i + 1], self.px[i + 2] = color

    def fill_rect(self, x, y, w, h, color):
        x0, y0 = max(0, x), max(0, y)
        x1, y1 = min(self.w, x + w), min(self.h, y + h)
        for yy in range(y0, y1):
            base = (yy * self.w + x0) * 3
            for xx in range(x0, x1):
                i = base + (xx - x0) * 3
                self.px[i], self.px[i + 1], self.px[i + 2] = color

    def rect(self, x, y, w, h, color, t=1):
        self.fill_rect(x, y, w, t, color)
        self.fill_rect(x, y + h - t, w, t, color)
        self.fill_rect(x, y, t, h, color)
        self.fill_rect(x + w - t, y, t, h, color)

    def hline(self, x, y, w, color, t=1):
        self.fill_rect(x, y, w, t, color)

    def vline(self, x, y, h, color, t=1):
        self.fill_rect(x, y, t, h, color)

    def line(self, x0, y0, x1, y1, color, t=1):
        """Bresenham line, thickness t (square brush)."""
        dx, dy = abs(x1 - x0), abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy
        while True:
            self.fill_rect(x0 - t // 2, y0 - t // 2, t, t, color)
            if x0 == x1 and y0 == y1:
                break
            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x0 += sx
            if e2 < dx:
                err += dx
                y0 += sy

    def circle(self, cx, cy, r, color, t=1):
        x, y, d = 0, r, 3 - 2 * r
        while x <= y:
            for px, py in ((cx + x, cy + y), (cx - x, cy + y),
                           (cx + x, cy - y), (cx - x, cy - y),
                           (cx + y, cy + x), (cx - y, cy + x),
                           (cx + y, cy - x), (cx - y, cy - x)):
                self.fill_rect(px - t // 2, py - t // 2, t, t, color)
            if d < 0:
                d += 4 * x + 6
            else:
                d += 4 * (x - y) + 10
                y -= 1
            x += 1

    def fill_circle(self, cx, cy, r, color):
        for dy in range(-r, r + 1):
            half = int(math.sqrt(max(0, r * r - dy * dy)))
            self.hline(cx - half, cy + dy, 2 * half + 1, color)

    def fill_semicircle_up(self, cx, base_y, r, color):
        """Filled upper half-disc whose flat edge sits on base_y."""
        for dy in range(0, r + 1):
            half = int(math.sqrt(max(0, r * r - dy * dy)))
            self.hline(cx - half, base_y - dy, 2 * half + 1, color)

    def fill_polygon(self, pts, color):
        """Scanline fill of a simple polygon (list of (x, y))."""
        if len(pts) < 3:
            return
        ymin = min(p[1] for p in pts)
        ymax = max(p[1] for p in pts)
        for y in range(ymin, ymax + 1):
            xs = []
            for i in range(len(pts)):
                x0, y0 = pts[i]
                x1, y1 = pts[(i + 1) % len(pts)]
                if y0 == y1:
                    continue
                if (y0 <= y < y1) or (y1 <= y < y0):
                    xs.append(x0 + (y - y0) * (x1 - x0) / (y1 - y0))
            xs.sort()
            for i in range(0, len(xs) - 1, 2):
                self.hline(int(math.ceil(xs[i])), y,
                           int(math.floor(xs[i + 1])) - int(math.ceil(xs[i])) + 1,
                           color)

    def star(self, cx, cy, r, color):
        """Five-pointed star centred on (cx, cy)."""
        pts = []
        for k in range(10):
            ang = -math.pi / 2 + k * math.pi / 5
            rad = r if k % 2 == 0 else r * 0.45
            pts.append((int(cx + rad * math.cos(ang)),
                        int(cy + rad * math.sin(ang))))
        self.fill_polygon(pts, color)

    # ------------------------------------------------------------ text ---
    def text(self, x, y, s, color, scale):
        for i, ch in enumerate(s):
            glyph = FONT.get(ch)
            if glyph is None:
                continue
            gx = x + i * 6 * scale
            for r, row in enumerate(glyph):
                for c, cell in enumerate(row):
                    if cell == "#":
                        self.fill_rect(gx + c * scale, y + r * scale,
                                       scale, scale, color)

    def text_center(self, cx, y, s, color, scale):
        self.text(cx - text_width(s, scale) // 2, y, s, color, scale)

    def text_right(self, x_right, y, s, color, scale):
        self.text(x_right - text_width(s, scale), y, s, color, scale)


# ----------------------------------------------------------------- PNG ---
def png_chunk(kind, data):
    out = struct.pack(">I", len(data)) + kind + data
    out += struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    return out


def write_png(path, cv):
    ihdr = struct.pack(">IIBBBBB", cv.w, cv.h, 8, 2, 0, 0, 0)
    raw = bytearray()
    for y in range(cv.h):
        raw.append(0)  # filter: None
        raw += cv.px[y * cv.w * 3:(y + 1) * cv.w * 3]
    blob = (b"\x89PNG\r\n\x1a\n" + png_chunk(b"IHDR", ihdr)
            + png_chunk(b"IDAT", zlib.compress(bytes(raw), 9))
            + png_chunk(b"IEND", b""))
    with open(path, "wb") as f:
        f.write(blob)
    return blob


# ------------------------------------------------------------ flags ------
def flag_usa(cv, x, y, w, h):
    """Stars and stripes: 7 stripes, blue canton with a grid of stars."""
    stripe = h // 7
    for i in range(7):
        cv.fill_rect(x, y + i * stripe, w, stripe,
                     (178, 34, 52) if i % 2 == 0 else WHITE)
    cv.fill_rect(x, y, w * 2 // 5, stripe * 4, BLUE)
    for r in range(3):
        for c in range(4):
            cv.fill_rect(x + 3 + c * 8, y + 3 + r * 7, 2, 2, WHITE)


def flag_chn(cv, x, y, w, h):
    """Red field, one large gold star and four small ones."""
    cv.fill_rect(x, y, w, h, (222, 41, 16))
    cv.star(x + 15, y + 15, 10, GOLD)
    for sx, sy in ((36, 8), (44, 15), (42, 26), (33, 32)):
        cv.star(x + sx, y + sy, 4, GOLD)


def flag_rus(cv, x, y, w, h):
    """White-blue-red horizontal tricolour."""
    cv.fill_rect(x, y, w, h // 3, WHITE)
    cv.fill_rect(x, y + h // 3, w, h // 3, (0, 57, 166))
    cv.fill_rect(x, y + 2 * h // 3, w, h - 2 * h // 3, (213, 0, 50))


# ------------------------------------------------------------ icons ------
def icon_gulf(cv, ix, iy):
    """Explosion starburst: the widening Gulf strikes."""
    cx, cy = ix + 28, iy + 28
    for k in range(12):
        ang = k * math.pi / 6
        cv.line(int(cx + 10 * math.cos(ang)), int(cy + 10 * math.sin(ang)),
                int(cx + 26 * math.cos(ang)), int(cy + 26 * math.sin(ang)),
                INK, 2)
    cv.fill_circle(cx, cy, 7, RED)


def icon_bridge(cv, ix, iy):
    """Kerch Bridge with its deck broken in the middle."""
    cv.vline(ix + 12, iy + 6, 34, INK, 2)
    cv.vline(ix + 44, iy + 6, 34, INK, 2)
    cv.hline(ix + 2, iy + 18, 20, INK, 2)
    cv.hline(ix + 34, iy + 18, 20, INK, 2)
    cv.line(ix + 22, iy + 18, ix + 34, iy + 34, INK, 2)
    cv.hline(ix + 4, iy + 46, 16, BLUE, 2)
    cv.hline(ix + 30, iy + 50, 20, BLUE, 2)


def icon_tech(cv, ix, iy):
    """Gamepad: the day GTA VI lands."""
    cv.rect(ix + 6, iy + 16, 44, 24, INK, 2)
    cv.hline(ix + 13, iy + 28, 10, INK, 2)
    cv.vline(ix + 18, iy + 23, 10, INK, 2)
    cv.fill_circle(ix + 40, iy + 24, 2, RED)
    cv.fill_circle(ix + 46, iy + 30, 2, RED)
    cv.line(ix + 8, iy + 10, ix + 48, iy + 2, BLUE, 2)
    cv.line(ix + 48, iy + 2, ix + 42, iy + 2, BLUE, 2)
    cv.line(ix + 48, iy + 2, ix + 48, iy + 8, BLUE, 2)


def icon_capitol(cv, ix, iy):
    """Capitol dome: Washington picks its next Speaker."""
    cv.fill_semicircle_up(ix + 28, iy + 30, 14, INK)
    cv.vline(ix + 28, iy + 8, 8, INK, 2)
    cv.fill_rect(ix + 28, iy + 6, 8, 5, RED)
    cv.rect(ix + 10, iy + 30, 36, 12, INK, 2)
    for cx in (18, 28, 38):
        cv.vline(ix + cx, iy + 32, 8, INK, 2)


def icon_cross(cv, ix, iy):
    """Medical cross in a ring: the Ebola outbreak."""
    cx, cy = ix + 28, iy + 28
    cv.circle(cx, cy, 20, INK, 2)
    cv.fill_rect(cx - 4, cy - 12, 8, 24, RED)
    cv.fill_rect(cx - 12, cy - 4, 24, 8, RED)


def icon_cyclone(cv, ix, iy):
    """Spiral: Cyclone Akvan curling towards India's east coast."""
    cx, cy = ix + 28, iy + 28
    for i in range(0, 260):
        t = i / 18.0
        r = 2 + i * 0.085
        px = int(cx + r * math.cos(t))
        py = int(cy + r * math.sin(t))
        cv.fill_rect(px, py, 2, 2, BLUE)


# -------------------------------------------------------------- layout ---
M = 28            # side margin
CW = 1024 - 2 * M  # content width: 968
COL = (CW - 24) // 2  # two-column width: 472

LEAD_HEAD = ["TRUMP, XI AND PUTIN", "MEET IN SHENZHEN"]
LEAD_DECK = ("FIRST-EVER TRILATERAL OF THE THREE NUCLEAR POWERS AT THE "
             "APEC SUMMIT. UKRAINE, IRAN, TRADE AND NUCLEAR ARMS ON "
             "THE TABLE.")

# (kicker, headline lines, deck, icon)
STORIES = [
    ("THE GULF WAR",
     ["IRAN HITS U.S. BASES", "IN KUWAIT, BAHRAIN"],
     "TEHRAN WIDENS ITS STRIKES AFTER THE U.S. HIT A MISSILE SITE "
     "ON QESHM ISLAND.",
     icon_gulf),
    ("UKRAINE",
     ["KERCH BRIDGE HIT", "AGAIN"],
     "TRAFFIC HALTED AFTER A NEW UKRAINIAN STRIKE. AN ARCH FELL "
     "INTO THE STRAIT A DAY EARLIER.",
     icon_bridge),
    ("THE BIGGEST DAY IN TECH",
     ["GTA VI LANDS AS", "ANTHROPIC LISTS"],
     "ROCKSTAR'S EPIC LANDS AFTER 13 YEARS, $1.65BN PRE-SOLD. "
     "ANTHROPIC LISTS ON NASDAQ AS 'ANT' IN THE BIGGEST IPO EVER.",
     icon_tech),
    ("WASHINGTON",
     ["JEFFRIES TO BE FIRST", "BLACK SPEAKER"],
     "HOUSE DEMOCRATS NOMINATE HAKEEM JEFFRIES 251-262. DEMOCRATS "
     "ALSO TAKE THE SENATE 56-44 AFTER ALASKA.",
     icon_capitol),
    ("HEALTH",
     ["EBOLA PASSES 11,000", "CASES IN CONGO"],
     "5,400 DEAD IN DR CONGO. NEARLY 3 IN 4 CHILDREN UNDER 5 "
     "DO NOT SURVIVE.",
     icon_cross),
    ("WEATHER",
     ["CYCLONE AKVAN NEARS", "INDIA'S EAST COAST"],
     "SEVERE STORM NEARS ANDHRA AND ODISHA WITH 90-110 KM/H WINDS. "
     "RED WARNING ISSUED.",
     icon_cyclone),
]

TICKER = ("MARKETS: S&P 500 -1.03%  \u2022  GOLD $3,767, A 14-MONTH LOW  "
          "\u2022  FED SIGNALS MORE HIKES  \u2022  VOYAGER 1 REACHES ONE "
          "LIGHT-DAY  \u2022  EU PLANS EUR 45BN UKRAINE LOAN  \u2022  "
          "ISRAEL GROUND OPERATION IN GAZA")

FOOTER = ("SOURCES: REUTERS \u2022 AP \u2022 AFP \u2022 LE MONDE \u2022 CNBC "
          "\u2022 PLAYSTATION \u2022 MAKE.FUN")


def story_box(cv, x, y, w, h, kicker, headline, deck, icon):
    cv.rect(x, y, w, h, RULE, 1)
    ix, iy = x + w - 16 - 56, y + 12
    icon(cv, ix, iy)
    tx = x + 16
    cv.text(tx, y + 12, kicker, RED, 2)
    hy = y + 34
    for line in headline:
        cv.text(tx, hy, line, INK, 3)
        hy += 24
    dy = hy + 8
    for line in wrap_text(deck, 2, w - 32):
        cv.text(tx, dy, line, DECK, 2)
        dy += 16


def build():
    cv = Canvas(W, H, PAPER)

    # ---- top dateline -------------------------------------------------
    cv.hline(M, 16, CW, INK, 2)
    cv.text(M, 26, "THURSDAY, 19 NOVEMBER 2026", INK, 2)
    cv.text_right(M + CW, 26, "WORLD EDITION", INK, 2)
    cv.hline(M, 46, CW, INK, 2)

    # ---- masthead ------------------------------------------------------
    cv.text_center(512, 56, "THE WORLD TODAY", INK, 9)
    cv.text_center(512, 128, "THE DAY'S NEWS IN ONE PICTURE", DECK, 2)
    cv.hline(M, 150, CW, RED, 6)
    cv.hline(M, 160, CW, INK, 2)

    # ---- lead story: the Shenzhen summit ------------------------------
    cv.rect(M, 170, CW, 190, INK, 2)
    cv.text(M + 16, 182, "THE SUMMIT: SHENZHEN, CHINA", RED, 2)
    hy = 204
    for line in LEAD_HEAD:
        cv.text(M + 16, hy, line, INK, 4)
        hy += 28
    dy = 268
    for line in wrap_text(LEAD_DECK, 2, 620):
        cv.text(M + 16, dy, line, DECK, 2)
        dy += 16
    # three flags on the right of the lead story
    fx = [700, 800, 900]
    for x0, flag, code, name in (
            (fx[0], flag_usa, "USA", "TRUMP"),
            (fx[1], flag_chn, "CHN", "XI"),
            (fx[2], flag_rus, "RUS", "PUTIN")):
        flag(cv, x0, 196, 84, 56)
        cv.rect(x0, 196, 84, 56, INK, 1)
        cv.text_center(x0 + 42, 260, code, INK, 2)
        cv.text_center(x0 + 42, 276, name, DECK, 2)
    cv.text_center(840, 302, "FIRST-EVER TRILATERAL", RED, 2)
    cv.hline(M, 372, CW, INK, 2)

    # ---- six stories in two columns ------------------------------------
    rows = [(384, 172), (568, 172), (752, 144)]
    for (ry, rh), pair in zip(rows, (STORIES[0:2], STORIES[2:4], STORIES[4:6])):
        story_box(cv, M, ry, COL, rh, *pair[0])
        story_box(cv, M + COL + 24, ry, COL, rh, *pair[1])

    # ---- bottom ticker --------------------------------------------------
    cv.fill_rect(M, 906, CW, 64, INK)
    ty = 914
    for line in wrap_text(TICKER, 2, CW - 32):
        cv.text_center(512, ty, line, WHITE, 2)
        ty += 16

    # ---- footer ---------------------------------------------------------
    cv.text_center(512, 980, FOOTER, DECK, 2)
    return cv


def main():
    outdir = os.environ.get("MAKEFUN_OUTPUT_DIR")
    if not outdir:
        outdir = "/output" if os.path.isdir("/output") else "out"
    os.makedirs(outdir, exist_ok=True)
    path = os.path.join(outdir, "entry.png")
    blob = write_png(path, build())
    print("wrote %s (%d bytes, sha256 %s)"
          % (path, len(blob), hashlib.sha256(blob).hexdigest()))


if __name__ == "__main__":
    main()
