"""SVG rendering helpers for app.py. Presentation only -- no game logic,
no Streamlit import (kept plain-Python/testable on its own).

Symbols, not just color, are used throughout -- matching the official
rulebook's own colorblind-accessibility key (rulebook p.1: "each color
used in the game has a corresponding symbol" -- Grey=diamond,
Blue=vertical bar, Red=cross, Yellow=circle, Green=triangle,
Purple=star, Black=dot, White=person). Reusing that key (plain
geometric shapes, not the game's artwork) lets a die's symbol be
matched to the board space it can fill, the way the physical dice and
boards are meant to be read.

Building layouts try to mirror the physical board's actual grid shape
(Agora and University are honest-to-goodness grids, not a strip -- see
RULES.md for photo sources) rather than a generic uniform progress bar.
"""

import math

from sevenwonders_dice.constants import BuildingKind, DieColor
from sevenwonders_dice.player_state import (BARRACKS_ATTACK_SPACES,
                                             BARRACKS_DEFENSE_SPACES,
                                             GALLERY_SPACES,
                                             GUILD_COURT_SPACES,
                                             UNIVERSITY_LANE_SPACES,
                                             WAREHOUSE_SPACES, WONDER_SPACES)

DIE_HEX = {
    DieColor.GREY: "#9e9e9e",
    DieColor.BLUE: "#3b6fa8",
    DieColor.RED: "#c0392b",
    DieColor.YELLOW: "#d4a72c",
    DieColor.GREEN: "#4a8f4a",
    DieColor.BLACK: "#2b2b2b",
    DieColor.WHITE: "#eceae4",
    DieColor.PURPLE: "#7d5ba6",
}

# The rulebook's own colorblind symbol key, reused for die <-> board matching.
SHAPE_OF_COLOR = {
    DieColor.GREY: "diamond",
    DieColor.BLUE: "bar",
    DieColor.RED: "cross",       # Barracks defense spaces use "square" instead
    DieColor.YELLOW: "circle",
    DieColor.GREEN: "triangle",
    DieColor.BLACK: "dot",
    DieColor.WHITE: "person",
    DieColor.PURPLE: "star",
}

BUILDING_HEX = {
    BuildingKind.WAREHOUSE: DIE_HEX[DieColor.GREY],
    BuildingKind.AGORA: DIE_HEX[DieColor.BLUE],
    BuildingKind.BARRACKS_WEST: DIE_HEX[DieColor.RED],
    BuildingKind.BARRACKS_EAST: DIE_HEX[DieColor.RED],
    BuildingKind.MARKET: DIE_HEX[DieColor.YELLOW],
    BuildingKind.UNIVERSITY: DIE_HEX[DieColor.GREEN],
    BuildingKind.GUILD_COURT: DIE_HEX[DieColor.PURPLE],
    BuildingKind.GALLERY: "#c7c4ba",
    BuildingKind.WONDER: "#c9a227",
}
BUILDING_SHAPE = {
    BuildingKind.WAREHOUSE: "diamond",
    BuildingKind.AGORA: "bar",
    BuildingKind.MARKET: "circle",
    BuildingKind.UNIVERSITY: "triangle",
    BuildingKind.GUILD_COURT: "star",
    BuildingKind.GALLERY: "person",
    BuildingKind.BARRACKS_WEST: "cross",
    BuildingKind.BARRACKS_EAST: "cross",
    BuildingKind.WONDER: "diamond",
}
_LANE_UNLOCK_HEX = {"black": DIE_HEX[DieColor.BLACK],
                     "purple": DIE_HEX[DieColor.PURPLE],
                     "white": DIE_HEX[DieColor.WHITE]}


def die_symbol(color: "DieColor", face) -> str:
  """Which shape a currently-rolled die face draws as -- usually just its
  color's shape, except Red (attack vs defense) and Black (Spy wildcard,
  shown as whatever building it currently targets)."""
  if color == DieColor.RED:
    return "cross" if face.barracks_is_attack else "square"
  if color == DieColor.BLACK:
    return BUILDING_SHAPE.get(face.wildcard_building, "dot")
  return SHAPE_OF_COLOR[color]


def _star_points(cx, cy, r_outer, r_inner):
  pts = []
  for i in range(10):
    angle = -math.pi / 2 + i * math.pi / 5
    r = r_outer if i % 2 == 0 else r_inner
    pts.append(f"{cx + r * math.cos(angle):.1f},{cy + r * math.sin(angle):.1f}")
  return " ".join(pts)


def _symbol(cx: float, cy: float, r: float, shape: str, color: str,
            opacity: float = 1.0) -> str:
  o = f' opacity="{opacity}"' if opacity != 1.0 else ""
  if shape == "diamond":
    pts = f"{cx},{cy - r} {cx + r},{cy} {cx},{cy + r} {cx - r},{cy}"
    return f'<polygon points="{pts}" fill="{color}"{o}/>'
  if shape == "bar":
    return (f'<rect x="{cx - r * 0.4:.1f}" y="{cy - r:.1f}" '
            f'width="{r * 0.8:.1f}" height="{r * 2:.1f}" rx="2" fill="{color}"{o}/>')
  if shape == "circle":
    return f'<circle cx="{cx}" cy="{cy}" r="{r:.1f}" fill="{color}"{o}/>'
  if shape == "triangle":
    pts = f"{cx},{cy - r} {cx + r},{cy + r * 0.8} {cx - r},{cy + r * 0.8}"
    return f'<polygon points="{pts}" fill="{color}"{o}/>'
  if shape == "square":
    return (f'<rect x="{cx - r * 0.8:.1f}" y="{cy - r * 0.8:.1f}" '
            f'width="{r * 1.6:.1f}" height="{r * 1.6:.1f}" rx="2" fill="{color}"{o}/>')
  if shape == "cross":
    w = r * 0.32
    return (f'<g{o}>'
            f'<line x1="{cx - r:.1f}" y1="{cy - r:.1f}" x2="{cx + r:.1f}" y2="{cy + r:.1f}" '
            f'stroke="{color}" stroke-width="{w:.1f}" stroke-linecap="round"/>'
            f'<line x1="{cx - r:.1f}" y1="{cy + r:.1f}" x2="{cx + r:.1f}" y2="{cy - r:.1f}" '
            f'stroke="{color}" stroke-width="{w:.1f}" stroke-linecap="round"/></g>')
  if shape == "star":
    return f'<polygon points="{_star_points(cx, cy, r, r * 0.45)}" fill="{color}"{o}/>'
  if shape == "dot":
    return (f'<g{o}><circle cx="{cx}" cy="{cy}" r="{r:.1f}" fill="none" '
            f'stroke="{color}" stroke-width="{r * 0.3:.1f}"/>'
            f'<circle cx="{cx}" cy="{cy}" r="{r * 0.35:.1f}" fill="{color}"/></g>')
  if shape == "person":
    return (f'<g{o}><circle cx="{cx}" cy="{cy - r * 0.5:.1f}" r="{r * 0.42:.1f}" fill="{color}"/>'
            f'<polygon points="{cx - r * 0.65:.1f},{cy + r:.1f} {cx + r * 0.65:.1f},{cy + r:.1f} '
            f'{cx},{cy - r * 0.05:.1f}" fill="{color}"/></g>')
  raise ValueError(shape)


def _cell(x: float, y: float, size: float, filled: bool, color: str, shape: str,
          ring: str = None) -> str:
  """One board space: an outlined square, its symbol always visible (dim if
  not yet crossed, solid once it is), optionally with an extra colored
  ring (used for University's unlock steps)."""
  parts = []
  if ring:
    parts.append(f'<rect x="{x - 2:.1f}" y="{y - 2:.1f}" width="{size + 4:.1f}" '
                 f'height="{size + 4:.1f}" rx="5" fill="none" stroke="{ring}" '
                 f'stroke-width="2"/>')
  bg = color if filled else "none"
  parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{size:.1f}" height="{size:.1f}" '
               f'rx="4" fill="{bg}" stroke="{color}" stroke-width="1.4"/>')
  symbol_color = "#12151b" if filled else color
  parts.append(_symbol(x + size / 2, y + size / 2, size * 0.27, shape,
                       symbol_color, opacity=1.0 if filled else 0.55))
  return "".join(parts)


def _grid(x0: float, y0: float, crossed: int, total: int, color: str, shape: str,
          cols: int, cell: float = 24, gap: float = 4,
          ring_per_cell=None) -> str:
  parts = []
  step = cell + gap
  for i in range(total):
    row, col = divmod(i, cols)
    x, y = x0 + col * step, y0 + row * step
    ring = ring_per_cell(i) if ring_per_cell else None
    parts.append(_cell(x, y, cell, i < crossed, color, shape, ring))
  rows = math.ceil(total / cols)
  return "".join(parts), x0 + cols * step - gap, y0 + rows * step - gap


def render_forum_svg(forum_details, width: int = 440, height: int = 230) -> str:
  """forum_details: [(DieColor, quadrant_cost, DieFace), ...] -- see
  State.forum_details()."""
  by_cost = {0: [], 1: [], 2: [], 3: []}
  for idx, (color, cost, face) in enumerate(forum_details):
    by_cost[cost].append((idx, color, face))

  cell_w, cell_h = width / 2 - 8, height / 2 - 8
  origins = {0: (0, 0), 1: (width / 2 + 8, 0),
             2: (0, height / 2 + 8), 3: (width / 2 + 8, height / 2 + 8)}
  parts = [f'<svg viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" '
           f'font-family="sans-serif">']
  for cost, (x, y) in origins.items():
    parts.append(f'<rect x="{x}" y="{y}" width="{cell_w}" height="{cell_h}" rx="8" '
                 f'fill="#1c2029" stroke="#444" stroke-width="1.5"/>')
    unit = "coin" if cost == 1 else "coins"
    parts.append(f'<text x="{x + 8}" y="{y + 18}" fill="#e8b84b" font-size="13" '
                 f'font-weight="bold">{cost} {unit}</text>')
    dx, dy = x + 10, y + 32
    for die_idx, color, face in by_cost[cost]:
      hexcolor = DIE_HEX[color]
      shape = die_symbol(color, face)
      parts.append(f'<rect x="{dx}" y="{dy}" width="34" height="34" rx="6" '
                   f'fill="{hexcolor}" stroke="#111" stroke-width="1.2"/>')
      parts.append(_symbol(dx + 17, dy + 17, 9, shape,
                           "#12151b" if color != DieColor.BLACK else "#eee"))
      parts.append(f'<text x="{dx + 17}" y="{dy + 46}" fill="#888" font-size="9" '
                   f'text-anchor="middle">#{die_idx}</text>')
      dx += 42
      if dx > x + cell_w - 34:
        dx = x + 10
        dy += 48
  parts.append("</svg>")
  return "".join(parts)


def _label(x, y, text):
  return f'<text x="{x}" y="{y}" fill="#ccc" font-size="12" font-weight="bold">{text}</text>'


def render_board_svg(ps, width: int = 400) -> str:
  """A grid-accurate progress tracker for one player's board: Agora and
  University are real grids (matching the physical board), Barracks is
  two side-by-side attack/defense columns, everything else a row --
  each space showing the symbol of the die that can fill it."""
  C, G = 22, 4
  y = 10
  parts = []

  def section(label, svg_and_extent, ytop):
    svg, x_end, y_end = svg_and_extent
    parts.append(_label(0, ytop + 15, label))
    parts.append(svg)
    return y_end + 22

  # Warehouse: row of 6.
  g = _grid(110, y, ps.warehouse_crossed, WAREHOUSE_SPACES,
            BUILDING_HEX[BuildingKind.WAREHOUSE], "diamond", cols=6, cell=C, gap=G)
  y = section("Warehouse", g, y)

  # Agora: 3x3 grid: 8 real spaces + the top-right "+3 first-to-finish" cell.
  parts.append(_label(0, y + 15, "Agora"))
  agora_color = BUILDING_HEX[BuildingKind.AGORA]
  order = [0, 1, None, 2, 3, 4, 5, 6, 7]  # None = the completion-bonus cell
  for i, space_idx in enumerate(order):
    row, col = divmod(i, 3)
    x, cy = 110 + col * (C + G), y + row * (C + G)
    if space_idx is None:
      filled = ps.agora_crossed >= 8
      parts.append(_cell(x, cy, C, filled, agora_color, "star"))
    else:
      parts.append(_cell(x, cy, C, space_idx < ps.agora_crossed, agora_color, "bar"))
  y += 3 * (C + G) + 18

  # Market: any order -> a loose 3x2 grid rather than an ordered strip.
  market_crossed = bin(ps.market_crossed_mask).count("1")
  g = _grid(110, y, market_crossed, 6, BUILDING_HEX[BuildingKind.MARKET],
            "circle", cols=3, cell=C, gap=G)
  y = section("Market", g, y)

  # University: 3 lanes x 3 steps; each lane's last step rings in the
  # special die color it unlocks (black / purple / white).
  parts.append(_label(0, y + 15, "University"))
  for row, lane in enumerate(("black", "purple", "white")):
    progress = ps.univ_lane_progress[lane]
    for col in range(UNIVERSITY_LANE_SPACES):
      x, cy = 110 + col * (C + G), y + row * (C + G)
      ring = _LANE_UNLOCK_HEX[lane] if col == UNIVERSITY_LANE_SPACES - 1 else None
      parts.append(_cell(x, cy, C, col < progress,
                         BUILDING_HEX[BuildingKind.UNIVERSITY], "triangle", ring))
  y += 3 * (C + G) + 18

  # Guild Court / Gallery: short rows.
  g = _grid(110, y, ps.guild_crossed, GUILD_COURT_SPACES,
            BUILDING_HEX[BuildingKind.GUILD_COURT], "star", cols=GUILD_COURT_SPACES,
            cell=C, gap=G)
  y = section("Guild Court", g, y)

  g = _grid(110, y, ps.gallery_crossed, GALLERY_SPACES,
            BUILDING_HEX[BuildingKind.GALLERY], "person", cols=GALLERY_SPACES,
            cell=C, gap=G)
  y = section("Gallery", g, y)

  # Barracks: attack (5) + defense (2) as two side-by-side columns, west
  # and east barracks as two such pairs -- matching the physical board's
  # vertical Barracks columns.
  parts.append(_label(0, y + 15, "West Barracks (atk | def)"))
  for i in range(BARRACKS_ATTACK_SPACES):
    cy = y + i * (C + G)
    parts.append(_cell(110, cy, C, i < ps.barracks_w_attack, BUILDING_HEX[BuildingKind.BARRACKS_WEST], "cross"))
  for i in range(BARRACKS_DEFENSE_SPACES):
    cy = y + i * (C + G)
    parts.append(_cell(110 + (C + G), cy, C, i < ps.barracks_w_defense, BUILDING_HEX[BuildingKind.BARRACKS_WEST], "square"))
  y += BARRACKS_ATTACK_SPACES * (C + G) + 18

  parts.append(_label(0, y + 15, "East Barracks (atk | def)"))
  for i in range(BARRACKS_ATTACK_SPACES):
    cy = y + i * (C + G)
    parts.append(_cell(110, cy, C, i < ps.barracks_e_attack, BUILDING_HEX[BuildingKind.BARRACKS_EAST], "cross"))
  for i in range(BARRACKS_DEFENSE_SPACES):
    cy = y + i * (C + G)
    parts.append(_cell(110 + (C + G), cy, C, i < ps.barracks_e_defense, BUILDING_HEX[BuildingKind.BARRACKS_EAST], "square"))
  y += BARRACKS_ATTACK_SPACES * (C + G) + 18

  # Wonder: 3 steps.
  g = _grid(110, y, ps.wonder_crossed, WONDER_SPACES,
            BUILDING_HEX[BuildingKind.WONDER], "diamond", cols=WONDER_SPACES,
            cell=C, gap=G)
  y = section("Wonder", g, y)

  height = y + 5
  header = (f'<svg viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" '
            f'font-family="sans-serif">')
  return header + "".join(parts) + "</svg>"
