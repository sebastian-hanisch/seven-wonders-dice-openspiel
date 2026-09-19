"""SVG rendering helpers for app.py. Presentation only -- no game logic,
no Streamlit import (kept plain-Python/testable on its own).

Every space shows its real cost and reward numbers (matching what's
printed on the physical board), not just an abstract filled/unfilled
symbol -- hovering a space also shows its exact effect text (an SVG
<title>, i.e. a native browser tooltip) via `describe_effects`.

Symbols, not just color, are used throughout -- matching the official
rulebook's own colorblind-accessibility key (rulebook p.1: "each color
used in the game has a corresponding symbol" -- Grey=diamond,
Blue=vertical bar, Red=cross, Yellow=circle, Green=triangle,
Purple=star, Black=dot, White=person). Reusing that key (plain
geometric shapes, not the game's artwork) lets a die's symbol be
matched to the board space it can fill, the way the physical dice and
boards are meant to be read. `render_legend_svg()` renders that same
key as a standalone strip.

Building layouts try to mirror the physical board's actual grid shape
(Agora and University are honest-to-goodness grids, not a strip -- see
RULES.md for photo sources) rather than a generic uniform progress bar.
"""

import math

from sevenwonders_dice.constants import BuildingKind, DieColor, EffectType
from sevenwonders_dice.describe import describe_effects
from sevenwonders_dice.player_state import (AGORA_SPACES,
                                             BARRACKS_ATTACK_SPACES,
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

# Short building names for Forum die captions (see _die_target_label) --
# distinct from describe.py's BUILDING_NAMES, which are the full names used
# in the action log/buttons and would be too wide for a 34px die tile.
_SHORT_BUILDING = {
    BuildingKind.WAREHOUSE: "Whse",
    BuildingKind.AGORA: "Agora",
    BuildingKind.BARRACKS_WEST: "Bar W",
    BuildingKind.BARRACKS_EAST: "Bar E",
    BuildingKind.MARKET: "Market",
    BuildingKind.UNIVERSITY: "Univ",
}
_LANE_ABBR = {"black": "blk", "purple": "pur", "white": "wht"}


def die_symbol(color: "DieColor", face) -> str:
  """Which shape a currently-rolled die face draws as -- usually just its
  color's shape, except Red (attack vs defense) and Black (Spy wildcard,
  shown as whatever building it currently targets)."""
  if color == DieColor.RED:
    return "cross" if face.barracks_is_attack else "square"
  if color == DieColor.BLACK:
    return BUILDING_SHAPE.get(face.wildcard_building, "dot")
  return SHAPE_OF_COLOR[color]


def _die_target_label(color: "DieColor", face) -> str:
  """A short caption of exactly what a rolled die targets right now --
  e.g. "Agora B", "W atk", "Univ pur" -- so a player can read a die's
  effect without having memorized the symbol key."""
  if color == DieColor.GREY:
    return "Whse"
  if color == DieColor.YELLOW:
    return "Market"
  if color == DieColor.WHITE:
    return "Gallery"
  if color == DieColor.BLUE:
    return f"Agora {'A' if face.agora_group == 0 else 'B'}"
  if color == DieColor.RED:
    side = "W" if face.barracks_is_west else "E"
    kind = "atk" if face.barracks_is_attack else "def"
    return f"{side} {kind}"
  if color == DieColor.GREEN:
    return f"Univ {_LANE_ABBR[face.university_lane]}"
  if color == DieColor.BLACK:
    return _SHORT_BUILDING.get(face.wildcard_building, "?")
  if color == DieColor.PURPLE:
    return _SHORT_BUILDING.get(face.guild_target, "?")
  return ""


def _xml_escape(text: str) -> str:
  return (text.replace("&", "&amp;").replace("<", "&lt;")
              .replace(">", "&gt;").replace('"', "&quot;"))


def _reward_text_from_effects(effects, printed_vp: int = 0) -> str:
  """A short (<=5 char) tag for what a space pays out, printed on the cell
  itself -- the exact text is always available via the cell's tooltip."""
  if printed_vp:
    return f"{printed_vp}VP"
  if not effects:
    return ""
  eff = effects[0]
  if eff.type == EffectType.FLAT_VP:
    return f"{eff.amount}VP"
  if eff.type == EffectType.GAIN_COINS:
    return f"+{eff.amount}c"
  if eff.type == EffectType.COIN_AND_VP_PER_SPACE:
    return f"{eff.amount}c/VP"
  if eff.type == EffectType.GALLERY_VP_PER_SPACE:
    return "VP"
  if eff.type == EffectType.UNLOCK_DIE:
    return "★"
  if eff.type == EffectType.TAKE_ANOTHER_ACTION:
    return "+A"
  if eff.type == EffectType.FREE_ACTION_A_NO_DIE_COST:
    return "free"
  if eff.type == EffectType.DIE_COST_MINUS_1:
    return "-1"
  if eff.type == EffectType.DIE_COST_ZERO:
    return "=0"
  if eff.type == EffectType.COINS_ON_DIE_CHOICE:
    return f"+{eff.amount}c/pick"
  if eff.type in (EffectType.CROSS_SPACE, EffectType.CROSS_SPACE_ONE_OF,
                  EffectType.CROSS_UP_TO_TWO):
    # Not a literal "*" -- Streamlit's markdown pass treats a lone ASCII
    # asterisk as emphasis syntax and can swallow the raw SVG tags around
    # it, so every effect tag here is built only from digits/letters/these
    # 2 unicode symbols, never bare "*"/"_"/backticks (see git history for
    # the bug this caused: whole building sections silently vanishing).
    return "→"  # -> : advances a space elsewhere on this board
  return "→"


def _tooltip_from_effects(effects, cost=None, printed_vp: int = 0) -> str:
  bits = []
  if cost is not None:
    bits.append(f"cost {cost}")
  if printed_vp:
    bits.append(f"printed VP {printed_vp} (before defense)")
  bits.append(describe_effects(effects) if effects else "no effect")
  return _xml_escape(" | ".join(bits))


def _reward_text(space) -> str:
  return _reward_text_from_effects(space.effects, space.printed_vp)


def _tooltip(space) -> str:
  return _tooltip_from_effects(space.effects, space.cost, space.printed_vp)


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
          cost=None, reward: str = "", tooltip: str = "", ring: str = None) -> str:
  """One board space: an outlined square, its symbol always visible (dim if
  not yet crossed, solid once it is), its resource cost (bottom-left) and
  reward tag (bottom-right) always printed -- matching what's printed on
  the physical board -- plus a native tooltip with the exact effect text.
  Optionally an extra colored ring (used for University's unlock steps)."""
  parts = []
  if tooltip:
    parts.append(f'<g><title>{tooltip}</title>')
  if ring:
    parts.append(f'<rect x="{x - 2:.1f}" y="{y - 2:.1f}" width="{size + 4:.1f}" '
                 f'height="{size + 4:.1f}" rx="5" fill="none" stroke="{ring}" '
                 f'stroke-width="2"/>')
  bg = color if filled else "none"
  parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{size:.1f}" height="{size:.1f}" '
               f'rx="4" fill="{bg}" stroke="{color}" stroke-width="1.4"/>')
  symbol_color = "#12151b" if filled else color
  parts.append(_symbol(x + size / 2, y + size * 0.4, size * 0.22, shape,
                       symbol_color, opacity=1.0 if filled else 0.55))
  text_color = "#12151b" if filled else "#bbb"
  font_size = max(6.0, size * 0.26)
  if cost is not None:
    parts.append(f'<text x="{x + 2:.1f}" y="{y + size - 2.5:.1f}" font-size="{font_size:.1f}" '
                 f'fill="{text_color}">{cost}</text>')
  if reward:
    parts.append(f'<text x="{x + size - 2:.1f}" y="{y + size - 2.5:.1f}" '
                 f'font-size="{font_size:.1f}" text-anchor="end" fill="{text_color}">{reward}</text>')
  if tooltip:
    parts.append("</g>")
  return "".join(parts)


def _grid(x0: float, y0: float, spaces, crossed: int, color: str, shape: str,
          cols: int, cell: float = 27, gap: float = 5,
          ring_per_cell=None) -> str:
  """A grid of `spaces` (boards.Space, in crossing order), the first
  `crossed` of them filled."""
  parts = []
  step = cell + gap
  for i, space in enumerate(spaces):
    row, col = divmod(i, cols)
    x, y = x0 + col * step, y0 + row * step
    ring = ring_per_cell(i) if ring_per_cell else None
    parts.append(_cell(x, y, cell, i < crossed, color, shape, cost=space.cost,
                       reward=_reward_text(space), tooltip=_tooltip(space), ring=ring))
  rows = math.ceil(len(spaces) / cols)
  return "".join(parts), x0 + cols * step - gap, y0 + rows * step - gap


def render_forum_svg(forum_details, width: int = 460, height: int = 260) -> str:
  """forum_details: [(DieColor, quadrant_cost, DieFace), ...] -- see
  State.forum_details(). Each die tile shows its cost (via the quadrant
  heading), its color/symbol, and a short caption of exactly what it
  currently targets (e.g. "Agora B", "W atk")."""
  by_cost = {0: [], 1: [], 2: [], 3: []}
  for idx, (color, cost, face) in enumerate(forum_details):
    by_cost[cost].append((idx, color, face))

  cell_w, cell_h = width / 2 - 8, height / 2 - 8
  origins = {0: (0, 0), 1: (width / 2 + 8, 0),
             2: (0, height / 2 + 8), 3: (width / 2 + 8, height / 2 + 8)}
  parts = [f'<svg viewBox="0 0 {width} {height}" width="{width}" height="{height}" '
           f'xmlns="http://www.w3.org/2000/svg" font-family="sans-serif">']
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
      label = _xml_escape(_die_target_label(color, face))
      parts.append(f'<g><title>Die #{die_idx}: {label} (cost {cost})</title>')
      parts.append(f'<rect x="{dx}" y="{dy}" width="34" height="34" rx="6" '
                   f'fill="{hexcolor}" stroke="#111" stroke-width="1.2"/>')
      parts.append(_symbol(dx + 17, dy + 17, 9, shape,
                           "#12151b" if color != DieColor.BLACK else "#eee"))
      parts.append(f'<text x="{dx + 17}" y="{dy + 46}" fill="#888" font-size="9" '
                   f'text-anchor="middle">#{die_idx}</text>')
      parts.append(f'<text x="{dx + 17}" y="{dy + 57}" fill="#ccc" font-size="9" '
                   f'text-anchor="middle">{label}</text>')
      parts.append("</g>")
      dx += 46
      if dx > x + cell_w - 34:
        dx = x + 10
        dy += 62
  parts.append("</svg>")
  return "".join(parts)


def _label(x, y, text):
  return f'<text x="{x}" y="{y}" fill="#ccc" font-size="12" font-weight="bold">{text}</text>'


def render_legend_svg(width: int = 460) -> str:
  """The rulebook's own colorblind key (color + symbol) alongside which
  building each die feeds -- a standalone strip, reused wherever a UI
  wants to explain how to read a die/board symbol."""
  order = [DieColor.GREY, DieColor.BLUE, DieColor.RED, DieColor.YELLOW,
           DieColor.GREEN, DieColor.BLACK, DieColor.WHITE, DieColor.PURPLE]
  building_of = {
      DieColor.GREY: "Warehouse", DieColor.BLUE: "Agora",
      DieColor.RED: "Barracks", DieColor.YELLOW: "Market",
      DieColor.GREEN: "University", DieColor.BLACK: "Spy (wildcard)",
      DieColor.WHITE: "Gallery", DieColor.PURPLE: "Guild Court",
  }
  cols = 4
  col_w = width / cols
  row_h = 36
  rows = math.ceil(len(order) / cols)
  height = rows * row_h + 6
  parts = [f'<svg viewBox="0 0 {width} {height}" width="{width}" height="{height}" '
           f'xmlns="http://www.w3.org/2000/svg" font-family="sans-serif">']
  for i, color in enumerate(order):
    row, col = divmod(i, cols)
    x, y = col * col_w + 4, row * row_h + 4
    hexcolor = DIE_HEX[color]
    shape = SHAPE_OF_COLOR[color]
    parts.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="24" height="24" rx="5" '
                 f'fill="{hexcolor}" stroke="#111" stroke-width="1"/>')
    parts.append(_symbol(x + 12, y + 12, 7, shape,
                         "#eee" if color == DieColor.BLACK else "#12151b"))
    parts.append(f'<text x="{x + 30:.1f}" y="{y + 16:.1f}" font-size="10.5" '
                 f'fill="#ccc">{building_of[color]}</text>')
  parts.append("</svg>")
  return "".join(parts)


def render_board_svg(ps, width: int = 460) -> str:
  """A grid-accurate progress tracker for one player's board: Agora and
  University are real grids (matching the physical board), Barracks is
  two side-by-side attack/defense columns, everything else a row -- each
  space showing the symbol of the die that can fill it plus its real cost
  (bottom-left) and reward (bottom-right); hover a space for its exact
  effect text."""
  C, G = 27, 5
  y = 10
  parts = []

  def section(label, svg_and_extent, ytop):
    svg, x_end, y_end = svg_and_extent
    parts.append(_label(0, ytop + 15, label))
    parts.append(svg)
    return y_end + 22

  # Warehouse: row of 6.
  g = _grid(120, y, ps.board.warehouse.spaces, ps.warehouse_crossed,
            BUILDING_HEX[BuildingKind.WAREHOUSE], "diamond", cols=WAREHOUSE_SPACES,
            cell=C, gap=G)
  y = section("Warehouse", g, y)

  # Agora: 3x3 grid: 8 real spaces (2 independently-gated symbol-group
  # tracks -- see RULES.md) + the top-right "+N first-to-finish" cell.
  parts.append(_label(0, y + 15, "Agora"))
  agora_color = BUILDING_HEX[BuildingKind.AGORA]
  order = [0, 1, None, 2, 3, 4, 5, 6, 7]  # None = the completion-bonus cell
  step = C + G
  for i, space_idx in enumerate(order):
    row, col = divmod(i, 3)
    x, cy = 120 + col * step, y + row * step
    if space_idx is None:
      filled = ps.building_progress(BuildingKind.AGORA) >= AGORA_SPACES
      bonus = ps.board.agora_completion_bonus_vp
      tooltip = _xml_escape(f"First player to complete all {AGORA_SPACES} "
                            f"Agora spaces gets +{bonus} VP")
      parts.append(_cell(x, cy, C, filled, agora_color, "star",
                         reward=f"+{bonus}", tooltip=tooltip))
    else:
      space = ps.board.agora.spaces[space_idx]
      group = space.agora_symbol_group
      parts.append(_cell(x, cy, C, ps.agora_space_crossed(space_idx), agora_color,
                         "bar", cost=space.cost, reward=_reward_text(space),
                         tooltip=_tooltip(space) + f" (group {chr(65 + group)})"))
  y += 3 * step + 18

  # Market: fillable in any order -> a real 3x2 grid of its 6 actual
  # spaces (not a generic progress count), since which specific space was
  # picked now matters (see RULES.md: real per-space choice).
  parts.append(_label(0, y + 15, "Market"))
  market_color = BUILDING_HEX[BuildingKind.MARKET]
  for i, space in enumerate(ps.board.market.spaces):
    row, col = divmod(i, 3)
    x, cy = 120 + col * step, y + row * step
    filled = bool((ps.market_crossed_mask >> i) & 1)
    parts.append(_cell(x, cy, C, filled, market_color, "circle", cost=space.cost,
                       reward=_reward_text(space), tooltip=_tooltip(space)))
  y += 2 * step + 18

  # University: 3 lanes x 3 steps; each lane's last step rings in the
  # special die color it unlocks (black / purple / white).
  parts.append(_label(0, y + 15, "University"))
  lane_spaces = {"black": ps.board.university.lane_black,
                 "purple": ps.board.university.lane_purple,
                 "white": ps.board.university.lane_white}
  for row, lane in enumerate(("black", "purple", "white")):
    progress = ps.univ_lane_progress[lane]
    for col in range(UNIVERSITY_LANE_SPACES):
      x, cy = 120 + col * step, y + row * step
      ring = _LANE_UNLOCK_HEX[lane] if col == UNIVERSITY_LANE_SPACES - 1 else None
      space = lane_spaces[lane][col]
      parts.append(_cell(x, cy, C, col < progress, BUILDING_HEX[BuildingKind.UNIVERSITY],
                         "triangle", cost=space.cost, reward=_reward_text(space),
                         tooltip=_tooltip(space), ring=ring))
  y += 3 * step + 18

  # Guild Court / Gallery: short rows.
  g = _grid(120, y, ps.board.guild_court.spaces, ps.guild_crossed,
            BUILDING_HEX[BuildingKind.GUILD_COURT], "star", cols=GUILD_COURT_SPACES,
            cell=C, gap=G)
  y = section("Guild Court", g, y)

  g = _grid(120, y, ps.board.gallery.spaces, ps.gallery_crossed,
            BUILDING_HEX[BuildingKind.GALLERY], "person", cols=GALLERY_SPACES,
            cell=C, gap=G)
  y = section("Gallery", g, y)

  # Barracks: attack (5) + defense (2) as two side-by-side columns, west
  # and east barracks as two such pairs -- matching the physical board's
  # vertical Barracks columns.
  defense_tooltip = _xml_escape(
      "cost varies | reduces this side's incoming attack VP by 1 per "
      "crossed defense space")

  def barracks_block(label, bdef, attack_progress, defense_progress, color):
    nonlocal y
    parts.append(_label(0, y + 15, label))
    for i, space in enumerate(bdef.attack):
      cy = y + i * step
      parts.append(_cell(120, cy, C, i < attack_progress, color, "cross",
                         cost=space.cost, reward=_reward_text(space), tooltip=_tooltip(space)))
    for i, space in enumerate(bdef.defense):
      cy = y + i * step
      parts.append(_cell(120 + step, cy, C, i < defense_progress, color, "square",
                         cost=space.cost, tooltip=defense_tooltip))
    y += BARRACKS_ATTACK_SPACES * step + 18

  barracks_block("West Barracks (atk | def)", ps.board.barracks_west,
                  ps.barracks_w_attack, ps.barracks_w_defense,
                  BUILDING_HEX[BuildingKind.BARRACKS_WEST])
  barracks_block("East Barracks (atk | def)", ps.board.barracks_east,
                  ps.barracks_e_attack, ps.barracks_e_defense,
                  BUILDING_HEX[BuildingKind.BARRACKS_EAST])

  # Wonder: 3 unique steps.
  g = _grid(120, y, ps.board.wonder, ps.wonder_crossed,
            BUILDING_HEX[BuildingKind.WONDER], "diamond", cols=WONDER_SPACES,
            cell=C, gap=G)
  y = section("Wonder", g, y)

  # Bonus slots: 3 fixed effects (no resource cost -- triggered by
  # completing any building), one of which gets picked per completion.
  parts.append(_label(0, y + 15, "Bonus slots"))
  for i, effect in enumerate(ps.board.bonus_slots):
    x = 120 + i * step
    used = bool((ps.bonus_used_mask >> i) & 1)
    reward = _reward_text_from_effects((effect,))
    tooltip = _tooltip_from_effects((effect,))
    parts.append(_cell(x, y, C, used, "#c9a227", "star", reward=reward, tooltip=tooltip))
  y += step + 8

  height = y + 5
  header = (f'<svg viewBox="0 0 {width} {height}" width="{width}" height="{height}" '
            f'xmlns="http://www.w3.org/2000/svg" font-family="sans-serif">')
  return header + "".join(parts) + "</svg>"
