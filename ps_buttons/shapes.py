"""PlayStation face symbols (font units: y up, centred on 0,0, about 250 units across)."""
from shapely.geometry import Point, LineString, Polygon, box
from shapely.ops import unary_union

S = 44  # stroke of the game's own button letters, in font units (L stem = 340..384)

# ---------- shapes (font units, y up, centred on 0,0) ----------
def flat(line, w): return line.buffer(w / 2, cap_style="flat", join_style="mitre")

def face(sym, S=S):
    """S: stroke width (the game's letters use 44; PlayStation's own symbols are thinner)."""
    if sym == "circle":
        return Point(0, 0).buffer(125, 24).difference(Point(0, 0).buffer(125 - S, 24))
    if sym == "square":
        return box(-105, -105, 105, 105).difference(box(-105 + S, -105 + S, 105 - S, 105 - S))
    if sym == "triangle":
        out = Polygon([(0, 122), (138, -112), (-138, -112)])
        return out.buffer(-8, join_style="mitre").buffer(8, 6).difference(out.buffer(-S, join_style="mitre"))
    if sym == "cross":
        return unary_union([flat(LineString([(-98, -98), (98, 98)]), S), flat(LineString([(-98, 98), (98, -98)]), S)])

