"""DualSense-style picture for the "Commandes" screen, drawn in the style of the game's Pro controller art.
Positions are in the 1160x680 picture. Buttons that sit where the Pro has them (face buttons, right stick,
shoulders) keep their callout lines; the others (d-pad, left stick, Create, Options) get their lines moved."""
import math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageChops
from shapely.geometry import Point, LineString, Polygon, box
from shapely.ops import unary_union
from shapely import affinity

from .controller_draw import *  # noqa: F401,F403  (drawing, positions, palette)

def shadow(orig_sh, orig_pic, body):
    """Rebuild the blurred left-half shadow with the new silhouette, using the original's placement."""
    sh = np.array(orig_sh.getchannel("R")).astype(float)
    a = np.array(orig_pic.getchannel("A")) > 128
    ys, xs = np.nonzero(a[:, :580]); px0, py0, py1 = xs.min(), ys.min(), ys.max()
    ys, xs = np.nonzero(sh > sh.max() / 2); sx0, sy0, sy1 = xs.min(), ys.min(), ys.max()
    k = (sy1 - sy0) / (py1 - py0)
    m = Image.new("L", orig_sh.size, 0); d = ImageDraw.Draw(m)
    l2, l1 = shoulders()
    for g in (body, l2, l1):
        d.polygon([(sx0 + (x - px0) * k, sy0 + (y - py0) * k) for x, y in g.exterior.coords], fill=255)
    out = np.array(m.filter(ImageFilter.GaussianBlur(13))).astype(float) * (sh.max() / 255)
    return Image.fromarray(out.clip(0, 255).astype(np.uint8))

# ---------- callout lines (1555x1511 masks) ----------
SX, SY = 0.9024, 0.879
def g(p): return (520 + (p[0] - PRO_LS[0]) / SX, 715 + (p[1] - PRO_LS[1]) / SY)

def blob(d, c, r):
    """Slightly irregular dot like the hand-drawn anchors. c, r in supersampled pixels."""
    j = [0.06, -0.04, 0.08, 0.0, -0.06, 0.05, -0.02, 0.07, -0.05, 0.03]
    d.polygon([(c[0] + r * (1 + j[i]) * math.cos(i * math.pi / 5), c[1] + r * (1 + j[i]) * math.sin(i * math.pi / 5)) for i in range(10)], fill=255)

def lines(mask, erase, polylines, dots):
    """Erase boxes, then draw 5.5 px lines and anchor dots, anti-aliased."""
    a = np.array(mask)
    for x0, y0, x1, y1 in erase: a[y0:y1, x0:x1] = 0
    W, H = mask.size
    hi = Image.new("L", (W * SS, H * SS), 0); d = ImageDraw.Draw(hi)
    for pl in polylines:
        d.line([(x * SS, y * SS) for x, y in pl], fill=255, width=round(5.5 * SS), joint="curve")
        for x, y in pl: d.ellipse(((x - 2.7) * SS, (y - 2.7) * SS, (x + 2.7) * SS, (y + 2.7) * SS), fill=255)
    for c in dots: blob(d, (c[0] * SS, c[1] * SS), 10.5 * SS)
    lo = np.array(hi.resize((W, H), Image.LANCZOS))
    return Image.fromarray(np.maximum(a, lo))

def move_block(mask, src_box, dx, dy):
    a = np.array(mask); x0, y0, x1, y1 = src_box
    blk = a[y0:y1, x0:x1].copy(); a[y0:y1, x0:x1] = 0
    a[y0 + dy:y1 + dy, x0 + dx:x1 + dx] = np.maximum(a[y0 + dy:y1 + dy, x0 + dx:x1 + dx], blk)
    return Image.fromarray(a)

def guides(m):
    """m: dict page -> L mask of ControllerGuide_Pro_0N. Returns the edited ones."""
    out = {}
    # page 0 - left stick: around the left of the d-pad, then under it to the stick
    ls = g(LS); x1 = g((268, 0))[0]
    a0 = lines(m[0], [(150, 660, 546, 745)], [[(146, 669.5), (x1, 669.5), (x1, ls[1]), (ls[0], ls[1])]], [ls])
    # page 0 - right stick moved up: re-anchor the top of its vertical line
    rs = g(RS)
    a0 = lines(a0, [(872, 826, 912, 878)], [[(891.5, rs[1]), (891.5, 884)]], [(891.5, rs[1])])
    # page 0 - "+" -> Options (top of the pill)
    op = g((OPTIONS[0], OPTIONS[1] - 19))
    out[0] = lines(a0, [(868, 552, round(op[0]) - 3, 640)], [[(op[0], 561.5), (op[0], op[1])]], [op])
    # page 1 - "-" -> Create
    cr = g((CREATE[0], CREATE[1] - 19))
    out[1] = lines(m[1], [(round(cr[0]) + 3, 552, 700, 640)], [[(cr[0], 563.5), (cr[0], cr[1])]], [cr])
    # page 3 - d-pad frame moved with the d-pad; stem redrawn down to the bottom line, which is trimmed
    d0 = g((455.8, 347.1)); d1 = g(DPAD); dx, dy = round(d1[0] - d0[0]), round(d1[1] - d0[1])
    a3 = np.array(m[3]); col = a3[:, 636:642].max(1) > 128
    yb = 1016
    while col[yb - 1]: yb -= 1   # top of the stem = bottom vertex of the frame
    stem_top = yb
    e = move_block(m[3], (540, 750, 738, stem_top + 14), dx, dy)  # frame incl. its rounded bottom
    sx = 638.5 + dx
    a = np.array(e); a[stem_top + 14:1016, 630:648] = 0; a[1012:1026, round(sx) + 3:648] = 0
    out[3] = lines(Image.fromarray(a), [], [[(sx, stem_top + 10 + dy), (sx, 1018.5)]], [])
    return out
