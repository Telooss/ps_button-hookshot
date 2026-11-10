"""DualSense drawing (picture coordinates 1160x680, y down). Imported by controller.py."""
import math
from PIL import Image, ImageDraw, ImageFilter, ImageChops
from shapely.geometry import Point, LineString, Polygon, box
from shapely.ops import unary_union
from shapely import affinity

SS = 3  # supersampling
# Two-tone like the real pad (light wings, dark centre panel), in each variant's own palette.
PAL = {
    "Controller_Pro":  dict(line=(0, 0, 0), wing=(74, 74, 74), panel=(42, 42, 42), pad=(82, 82, 82), part=(100, 100, 100),
                            trig=(88, 88, 88), glyph=(184, 184, 184), dark=(31, 31, 31), led=(128, 128, 128), edge=None),
    "Controller_Pro1": dict(line=(26, 19, 10), wing=(34, 29, 22), panel=(12, 9, 8), pad=(38, 32, 24), part=(84, 73, 53),
                            trig=(66, 57, 42), glyph=(116, 98, 76), dark=(17, 7, 0), led=(98, 84, 60), edge=(44, 37, 27)),
}
C = 580  # centre line
# Proportions from a DualSense front view, scaled so the face buttons stay where the Pro has them.
FACE = {"X": (800, 166), "A": (868, 226), "B": (800, 282.2), "Y": (732, 226.1)}  # diamond callout kept
PRO_LS, PRO_RS = (348.6, 227.2), (683.4, 347.6)
LS, RS = (476.6, 309), (683.4, 309)
DPAD = (356, 222)
CREATE, OPTIONS = (418, 130), (742, 130)
GRILLE, PSBTN, MUTE = (C, 262), (C, 309), (C, 357)

def mirror(g): return affinity.scale(g, -1, 1, origin=(C, 0))
def both(g): return unary_union([g, mirror(g)])
def sym_poly(half):  # left-half outline (top centre ... bottom centre) -> full symmetric polygon
    return Polygon(half + [(2 * C - x, y) for x, y in reversed(half)]).buffer(0)
def rrect(x0, y0, x1, y1, r): return box(x0 + r, y0 + r, x1 - r, y1 - r).buffer(r, 16)

def silhouette():
    half = [(580, 56), (470, 58), (410, 62), (350, 68), (305, 78), (270, 96), (250, 124), (240, 170), (236, 226),
            (238, 290), (244, 340), (236, 400), (226, 470), (216, 535), (214, 575), (228, 606), (258, 622), (292, 620),
            (318, 600), (332, 565), (346, 515), (368, 460), (398, 420), (440, 397), (500, 386), (580, 382)]
    return sym_poly(half).buffer(20, 32).buffer(-56, 32).buffer(36, 32)

def panel(body):
    p = sym_poly([(580, 236), (452, 232), (430, 262), (410, 310), (392, 360), (366, 420), (340, 480), (322, 560), (300, 700), (580, 700)])
    return p.intersection(body.buffer(-3))

def shoulders():
    return rrect(330, 16, 432, 76, 28), rrect(276, 42, 438, 100, 26)  # L2 trigger, L1 bumper

def touchpad():
    return sym_poly([(580, 60), (452, 62), (456, 140), (462, 222), (520, 232), (580, 235)]).buffer(-8, join_style="round").buffer(8, 16)

def lightbars():
    bottom = LineString([(470, 241), (525, 248), (580, 250), (635, 248), (690, 241)]).buffer(3, 8)
    side = both(LineString([(442, 82), (446, 160), (452, 222)]).buffer(2.6, 8))
    return unary_union([bottom, side])

def dpad_buttons():
    p = Polygon([(-14, -57), (14, -57), (14, -22), (0, -10), (-14, -22)]).buffer(3.5, 8)
    return [affinity.translate(affinity.rotate(p, a, origin=(0, 0)), *DPAD) for a in (0, 90, 180, 270)]

def dpad_arrows():
    t = Polygon([(-6, -38), (6, -38), (0, -46)])
    return [affinity.translate(affinity.rotate(t, a, origin=(0, 0)), *DPAD) for a in (0, 90, 180, 270)]

def pill(c, w, h, tilt): return affinity.rotate(affinity.translate(rrect(-w / 2, -h / 2, w / 2, h / 2, w / 2 - 0.5), *c), tilt, origin=c)

class Canvas:
    def __init__(self, w, h, base=None):
        self.im = base.resize((w * SS, h * SS), Image.NEAREST) if base else Image.new("RGBA", (w * SS, h * SS), (255, 255, 255, 0))
        self.d = ImageDraw.Draw(self.im)
    def poly(self, g, fill):
        for p in (g.geoms if hasattr(g, "geoms") else [g]):
            if p.is_empty or not hasattr(p, "exterior"): continue
            self.d.polygon([(x * SS, y * SS) for x, y in p.exterior.coords], fill=fill + (255,))
            for r in p.interiors: self.d.polygon([(x * SS, y * SS) for x, y in r.coords], fill=(255, 255, 255, 0))
    def outlined(self, g, fill, line, w):
        self.poly(g, line); self.poly(g.buffer(-w, join_style="round"), fill)
    def done(self, w, h): return self.im.resize((w, h), Image.LANCZOS)

def disc_mask(size, c, r):
    m = Image.new("L", size, 0); ImageDraw.Draw(m).ellipse((c[0] - r, c[1] - r, c[0] + r, c[1] + r), fill=255); return m

def draw(variant, orig, face_symbol):
    """orig: decoded original picture of this variant. face_symbol(sym, S) -> shapely geometry (~250 units across)."""
    P = PAL[variant]; W, H = orig.size
    cv = Canvas(W, H)
    l2, l1 = shoulders()
    cv.outlined(both(l2), P["trig"], P["line"], 3)
    cv.outlined(both(l1), P["wing"], P["line"], 3)
    body = silhouette()
    cv.outlined(body, P["wing"], P["line"], 3)
    pn = panel(body)
    cv.poly(pn.buffer(2.2), P["line"]); cv.poly(pn, P["panel"])
    im = cv.done(W, H)
    if P["edge"]:  # Pro1 has a soft lighter rim inside the body
        m = Image.new("L", (W, H), 0); ImageDraw.Draw(m).polygon(list(body.buffer(-3).exterior.coords), fill=255)
        rim = ImageChops.subtract(m, m.filter(ImageFilter.GaussianBlur(12)))
        im.paste(Image.new("RGBA", (W, H), P["edge"] + (255,)), (0, 0), rim.point(lambda v: min(255, int(v * 1.6))))
    cv = Canvas(W, H, im)
    cv.outlined(touchpad(), P["pad"], P["line"], 2.5)
    cv.poly(lightbars(), P["led"])
    for b in dpad_buttons(): cv.outlined(b, P["part"], P["line"], 2.2)
    for t in dpad_arrows(): cv.poly(t, P["dark"])
    cv.outlined(pill(CREATE, 13, 36, -14), P["part"], P["line"], 2)
    cv.outlined(pill(OPTIONS, 13, 36, 14), P["part"], P["line"], 2)
    for i in range(6): cv.poly(Point(GRILLE[0] - 22.5 + 9 * i, GRILLE[1]).buffer(2.6, 8), P["led"])
    cv.outlined(Point(*PSBTN).buffer(13, 24), P["part"], P["line"], 2)
    cv.outlined(pill(MUTE, 8, 34, 90), P["part"], P["line"], 1.8)
    im = cv.done(W, H)
    # sticks and face buttons: lifted from the original art (sticks a touch smaller, like the DualSense)
    k = 0.88; n = round(140 * k)
    crop = orig.crop((round(PRO_RS[0]) - 70, round(PRO_RS[1]) - 70, round(PRO_RS[0]) + 70, round(PRO_RS[1]) + 70)).resize((n, n), Image.LANCZOS)
    for dst in (LS, RS):
        im.paste(crop, (round(dst[0] - n / 2), round(dst[1] - n / 2)), disc_mask(crop.size, (n / 2, n / 2), 66 * k))
    sym = {"A": "circle", "B": "cross", "X": "triangle", "Y": "square"}  # physical positions
    for key, (x, y) in FACE.items():
        c = orig.crop((x - 36, y - 36, x + 36, y + 36))
        im.paste(c, (round(x) - 36, round(y) - 36), disc_mask(c.size, (36, 36), 34))
        ImageDraw.Draw(im).ellipse((x - 25, y - 25, x + 25, y + 25), fill=P["part"] + (255,))
        cv = Canvas(W, H); gm = affinity.translate(affinity.scale(face_symbol(sym[key], 24), 0.125, -0.125, origin=(0, 0)), x, y)
        cv.poly(gm, P["glyph"]); im.alpha_composite(cv.done(W, H))
    return im, body
