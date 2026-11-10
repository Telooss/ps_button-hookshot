"""Builds the PS Buttons mod from the player's own copy of the game.

Three romfs files are rewritten, in the game's own style:
  Font2/Scalable/External...bfotf.zs   button glyphs of prompts and texts (A B X Y, L R ZL ZR, + -)
  UI/Layout2Archive/Common...bntx.zs    text button icons, ocarina notes, "Commandes" controller screen
  System/Resource/ResourceSizeTable...  the font's size entry (the redrawn font is a bit larger)"""
from __future__ import annotations

import io
import math
import shutil
import struct
import zlib
from collections.abc import Callable
from pathlib import Path

import astc_encoder as ae
import numpy as np
import zstandard
from fontTools.pens.recordingPen import RecordingPen
from fontTools.pens.t2CharStringPen import T2CharStringPen
from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw
from shapely import affinity
from shapely.geometry import LineString, box
from shapely.geometry.polygon import orient
from shapely.ops import unary_union

from . import controller
from .bntx import textures
from .shapes import S, face, flat
from .tex import decode, swizzle

MOD_NAME = "PS_Buttons"
FONT = "Font2/Scalable/External.Nin_Ounce_NVN2.bfotf"
BNTX = "UI/Layout2Archive/Common.Product.100.Nin_Ounce_NVN2.bntx"
RSTB = "System/Resource/ResourceSizeTable.Product.111.Nin_Ounce_NVN2.rsizetable"


def symbols(xbox: bool) -> dict[str, str]:
    """Which PlayStation symbol each Switch letter shows. Default: Hookshot's "Nintendo" layout preset
    (A = right button = Circle); xbox=True for the "Xbox / PC" or "Swap Face" presets (A = bottom = Cross)."""
    return {"A": "cross" if xbox else "circle", "B": "circle" if xbox else "cross", "X": "triangle", "Y": "square"}


# ---------- shapes (font units, y up) ----------
def digit(d, x0, bot, top):
    if d == "1":
        stem = box(x0 + 62, bot, x0 + 62 + S, top)
        flag = flat(LineString([(x0 + 4, top - 78), (x0 + 84, top - 18)]), S)
        return unary_union([stem, flag]).intersection(box(x0, bot, x0 + 62 + S, top))
    if d == "2":  # geometric 2: arc, diagonal, foot (like the game's L)
        w, r = 150, 75 - S / 2
        cx, cy = x0 + 75, top - 75
        arc = [(cx + r * math.cos(math.radians(a)), cy + r * math.sin(math.radians(a))) for a in range(165, -41, -15)]
        line = LineString(arc + [(x0 + S / 2, bot + S)])
        g = unary_union([flat(line, S), box(x0, bot, x0 + w, bot + 40)])
        return g.intersection(box(x0, bot, x0 + w, top))


def bars():  # Options: three horizontal bars
    return unary_union([LineString([(-100, y), (100, y)]).buffer(20, 6) for y in (-80, 0, 80)])


def create():  # Create: three rays fanning upward
    rays = []
    for a in (-50, 0, 50):
        dx, dy = math.sin(math.radians(a)), math.cos(math.radians(a))
        rays.append(LineString([(dx * 95, -185 + dy * 95), (dx * 225, -185 + dy * 225)]).buffer(20, 6))
    return unary_union(rays)


def polys(g):
    return list(g.geoms) if hasattr(g, "geoms") else [g]


# ---------- font ----------
def contours(glyph):
    p = RecordingPen(); glyph.draw(p)
    out, cur = [], []
    for op, a in p.value:
        cur.append((op, a))
        if op in ("closePath", "endPath"):
            out.append(cur); cur = []
    return out


def bounds(c):
    pts = [pt for _, a in c for pt in a]
    return min(x for x, _ in pts), min(y for _, y in pts), max(x for x, _ in pts), max(y for _, y in pts)


def area(c):
    pts = [a[-1] for _, a in c if a]
    return sum(pts[i][0] * pts[(i + 1) % len(pts)][1] - pts[(i + 1) % len(pts)][0] * pts[i][1] for i in range(len(pts))) / 2


def replay(pen, c, dx=0):
    for op, a in c:
        getattr(pen, op)(*[(x + dx, y) for x, y in a])


def add_holes(pen, g, dx=0, dy=0):
    """Cut g out of a filled shape: exterior clockwise, interiors counter-clockwise."""
    for p in polys(affinity.translate(g, dx, dy)):
        p = orient(p, -1.0)
        for ring in [p.exterior, *p.interiors]:
            pts = list(ring.coords)[:-1]
            pen.moveTo(pts[0])
            for q in pts[1:]:
                pen.lineTo(q)
            pen.closePath()


FONT_KEY = bytes.fromhex("a6018502")  # .bfotf: 8-byte header, then OpenType XORed with this key


def xor(b: bytes) -> bytes:
    return bytes(x ^ FONT_KEY[i % 4] for i, x in enumerate(b))


def build_font(enc: bytes, sym: dict[str, str]) -> bytes:
    f = TTFont(io.BytesIO(xor(enc[8:])), recalcTimestamp=False)  # keep the game's date: reproducible builds
    gs, cm = f.getGlyphSet(), f.getBestCmap()
    top = f["CFF "].cff.topDictIndex[0]
    cs = top.CharStrings
    new = {}

    def put(cp, draw):
        name = cm[cp]
        pen = T2CharStringPen(gs[name].width, None)
        draw(pen, contours(gs[name]))
        new[name] = pen.getCharString(private=cs[name].private, globalSubrs=top.GlobalSubrs)

    # A/B/X/Y: keep the disc (largest contour), drop the letter, cut the symbol
    for cp, n in zip(range(0xE040, 0xE044), "ABXY"):
        def d(pen, cs_, n=n):
            disc = max(cs_, key=area); replay(pen, disc)
            x0, y0, x1, y1 = bounds(disc)
            k = 1.22 if sym[n] == "triangle" else 1.1  # match the letters' visual size
            add_holes(pen, affinity.scale(face(sym[n]), k, k, origin=(0, 0)), (x0 + x1) / 2, (y0 + y1) / 2)
        put(cp, d)
    # L R ZL ZR -> L1 R1 L2 R2: keep the tag and the L/R letter, add the digit
    for cp, dg in ((0xE044, "1"), (0xE045, "1"), (0xE046, "2"), (0xE047, "2")):
        def d(pen, cs_, dg=dg):
            tag = max(cs_, key=area)
            rest = sorted((c for c in cs_ if c is not tag), key=lambda c: bounds(c)[0])
            # ZL/ZR: drop the Z (leftmost hole); the letter is what remains
            letter = rest[1:] if len(rest) > 1 and area(rest[0]) < 0 and bounds(rest[0])[2] < bounds(rest[1])[0] else rest
            lx0 = min(bounds(c)[0] for c in letter); lx1 = max(bounds(c)[2] for c in letter)
            bot = min(bounds(c)[1] for c in letter); topy = max(bounds(c)[3] for c in letter)
            dw = 106 if dg == "1" else 150
            tx0, _, tx1, _ = bounds(tag)
            start = (tx0 + tx1) / 2 - (lx1 - lx0 + 30 + dw) / 2
            replay(pen, tag)
            for c in letter:
                replay(pen, c, start - lx0)
            add_holes(pen, digit(dg, start + (lx1 - lx0) + 30, bot, topy))
        put(cp, d)
    # + / - -> Options / Create
    for cp, g in ((0xE04B, bars()), (0xE04C, create())):
        def d(pen, cs_, g=g):
            disc = max(cs_, key=area); replay(pen, disc)
            x0, y0, x1, y1 = bounds(disc)
            add_holes(pen, g, (x0 + x1) / 2, (y0 + y1) / 2)
        put(cp, d)
    for name, c in new.items():
        if cs.charStringsAreIndexed:
            cs.charStringsIndex[cs.charStrings[name]] = c
        else:
            cs.charStrings[name] = c
    if "DSIG" in f:
        del f["DSIG"]
    buf = io.BytesIO(); f.save(buf); p = buf.getvalue()
    return enc[:4] + xor(struct.pack(">I", len(p))) + xor(p)


# ---------- textures ----------
def raster(g, size, scale, cx, cy, ss=8):
    """Rasterise shapely geometry (font units around 0,0) to an L mask, y flipped."""
    im = Image.new("L", (size * ss, size * ss), 0); d = ImageDraw.Draw(im)
    T = lambda pts: [((cx + x * scale) * ss, (cy - y * scale) * ss) for x, y in pts]
    for p in polys(g):
        d.polygon(T(p.exterior.coords), fill=255)
        for r in p.interiors:
            d.polygon(T(r.coords), fill=0)
    return im.resize((size, size), Image.LANCZOS)


def bc4_encode(a):
    H, W = a.shape; out = bytearray()
    for by in range(0, H, 4):
        for bx in range(0, W, 4):
            blk = a[by:by + 4, bx:bx + 4].astype(np.int32).ravel()
            hi, lo = int(blk.max()), int(blk.min())
            if hi == lo:
                out += bytes([hi, lo]) + bytes(6); continue
            pal = np.array([hi, lo] + [((7 - i) * hi + i * lo) // 7 for i in range(1, 7)])
            idx = np.abs(blk[:, None] - pal[None, :]).argmin(1)
            out += bytes([hi, lo]) + sum(int(i) << (3 * n) for n, i in enumerate(idx)).to_bytes(6, "little")
    return bytes(out)


def build_bntx(orig: bytes, sym: dict[str, str]) -> bytes:
    b = bytearray(orig); tx = textures(orig)

    def put(t, raw):
        assert len(raw) == t["size"]; b[t["data"]:t["data"] + t["size"]] = raw
    for n, s in sym.items():  # 64x64 BC4 masks; letters are ~29 px for 250 units
        t = tx[f"KeyTexFont{n}_00"]; assert t["fmt"] == 0x1d01 and t["w"] == t["h"] == 64
        put(t, swizzle(bc4_encode(np.array(raster(face(s), 64, 0.116, 31.5, 31.5))), 16, 16, 8, t["bhl"], True, t["size"]))
    ctx = ae.ASTCContext(ae.ASTCConfig(ae.ASTCProfile.LDR_SRGB, 4, 4, 1, 100, 0))
    for n, s in sym.items():  # 93x93 ASTC: white disc (67 px = 564 units), black symbol
        t = tx[f"OcarinaButton{n}_00"]; assert t["fmt"] == 0x2d06 and t["w"] == t["h"] == 93
        im = decode(orig, t, True).convert("RGBA")
        ImageDraw.Draw(im).ellipse((46.5 - 30, 46.5 - 30, 46.5 + 30, 46.5 + 30), fill=(255, 255, 255, 255))
        im.paste(Image.new("RGBA", im.size, (0, 0, 0, 255)), (0, 0), raster(face(s), 93, 67 / 564, 46.5, 46.5))
        pad = Image.new("RGBA", (96, 96), (255, 255, 255, 0)); pad.paste(im, (0, 0))
        comp = ctx.compress(ae.ASTCImage(ae.ASTCType.U8, 96, 96, 1, pad.tobytes()), ae.ASTCSwizzle.from_str("RGBA"))
        put(t, swizzle(comp, 24, 24, 16, t["bhl"], True, t["size"]))

    # "Commandes" screen: DualSense-style picture, its shadow, and the callout lines that had to move
    def put_bc4(t, im):
        assert t["fmt"] == 0x1d01
        bw, bh = math.ceil(t["w"] / 4), math.ceil(t["h"] / 4)
        pad = Image.new("L", (bw * 4, bh * 4), 0); pad.paste(im, (0, 0))
        put(t, swizzle(bc4_encode(np.array(pad)), bw, bh, 8, t["bhl"], True, t["size"]))

    def put_astc(t, im):
        assert t["fmt"] == 0x2d06 and t["w"] % 4 == 0 and t["h"] % 4 == 0
        comp = ctx.compress(ae.ASTCImage(ae.ASTCType.U8, t["w"], t["h"], 1, im.tobytes()), ae.ASTCSwizzle.from_str("RGBA"))
        put(t, swizzle(comp, t["w"] // 4, t["h"] // 4, 16, t["bhl"], True, t["size"]))
    dec = lambda name: decode(orig, tx[name], True)
    body = None
    for v in ("Controller_Pro", "Controller_Pro1"):
        im, body = controller.draw(v, dec(v).convert("RGBA"), face)  # symbols by physical position
        put_astc(tx[v], im)
    put_bc4(tx["ControllerSh_Pro1"], controller.shadow(dec("ControllerSh_Pro1"), dec("Controller_Pro1"), body))
    for i, im in controller.guides({i: dec(f"ControllerGuide_Pro_0{i}").getchannel("R") for i in (0, 1, 3)}).items():
        put_bc4(tx[f"ControllerGuide_Pro_0{i}"], im)
    out = bytes(b)
    assert len(out) == len(orig)
    return out


# ---------- romfs io ----------
def _sarc(buf):
    data_off = struct.unpack_from("<I", buf, 0xC)[0]; sfat = struct.unpack_from("<H", buf, 4)[0]
    n = struct.unpack_from("<H", buf, sfat + 6)[0]; names = sfat + 12 + n * 16 + 8; out = {}
    for i in range(n):
        _, attr, s, e = struct.unpack_from("<IIII", buf, sfat + 12 + i * 16)
        o = names + (attr & 0xFFFF) * 4
        out[buf[o:buf.index(b"\0", o)].decode()] = buf[data_off + s:data_off + e]
    return out


class _Romfs:
    def __init__(self, romfs: Path):
        self.root = romfs
        pack = zstandard.ZstdDecompressor().decompress((romfs / "Pack/ZsDic.pack.zs").read_bytes())
        self.dic = zstandard.ZstdCompressionDict(_sarc(pack)["zs.zsdic"])

    def read(self, rel: str) -> bytes:
        return zstandard.ZstdDecompressor(dict_data=self.dic).decompress((self.root / f"{rel}.zs").read_bytes(),
                                                                         max_output_size=1 << 31)

    def compress_like(self, rel: str, data: bytes) -> bytes:
        """Same dictionary use as the original: files read before the dictionaries load (RESTBL) have none,
        and compressing those with a dictionary makes the game crash at start-up."""
        d = self.dic if zstandard.get_frame_parameters((self.root / f"{rel}.zs").read_bytes()).dict_id else None
        comp = zstandard.ZstdCompressor(level=19, dict_data=d).compress(data)
        assert zstandard.ZstdDecompressor(dict_data=d).decompress(comp, max_output_size=1 << 31) == data
        return comp


def grow_size_entry(table: bytes, rel: str, grow_by: int) -> bytes | None:
    """The resource size table reserves memory per file (CRC32 of the path -> size); None if no change is needed."""
    if grow_by <= 0:
        return None
    rs = bytearray(table)
    count, h = struct.unpack_from("<I", rs, 14)[0], zlib.crc32(rel.encode())
    for i in range(count):
        crc, size = struct.unpack_from("<II", rs, 22 + 8 * i)
        if crc == h:
            struct.pack_into("<I", rs, 22 + 8 * i + 4, size + grow_by)
            return bytes(rs)
    return None


def build_mod(game: Path, mods: Path, xbox: bool = False, log: Callable[[str], None] = print) -> Path:
    """Writes <mods>/PS_Buttons/romfs/...; an existing install is only replaced once the new one is complete."""
    game, mods = Path(game), Path(mods)
    final, tmp, old = mods / MOD_NAME, mods / f"{MOD_NAME}.tmp", mods / f"{MOD_NAME}.old"
    shutil.rmtree(tmp, ignore_errors=True)
    try:
        romfs = _Romfs(game / "romfs")
        sym = symbols(xbox)

        def write(rel, data):
            dst = tmp / "romfs" / (rel + ".zs")
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(romfs.compress_like(rel, data))

        log("Police des boutons…")
        font_old = romfs.read(FONT)
        font_new = build_font(font_old, sym)
        write(FONT, font_new)
        log("Icônes, ocarina et écran Commandes (environ une minute)…")
        write(BNTX, build_bntx(romfs.read(BNTX), sym))
        log("Table des tailles…")
        table = grow_size_entry(romfs.read(RSTB), FONT, len(font_new) - len(font_old))
        if table is not None:
            write(RSTB, table)
        shutil.rmtree(old, ignore_errors=True)
        if final.exists():
            final.rename(old)
        tmp.rename(final)
        shutil.rmtree(old, ignore_errors=True)
        return final
    except BaseException:
        shutil.rmtree(tmp, ignore_errors=True)
        raise
