"""SVG rendering helpers for app.py. Presentation only -- no game logic,
no Streamlit import (kept plain-Python/testable on its own).
"""

from sevenwonders_dice.constants import BuildingKind, DieColor
from sevenwonders_dice.player_state import (AGORA_SPACES,
                                             BARRACKS_ATTACK_SPACES,
                                             BARRACKS_DEFENSE_SPACES,
                                             GALLERY_SPACES,
                                             GUILD_COURT_SPACES,
                                             MARKET_SPACES,
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
_DEFENSE_HEX = "#e0a5a0"


def render_forum_svg(forum_summary, width: int = 420, height: int = 220) -> str:
  """forum_summary: [(DieColor, quadrant_cost), ...] -- see State.forum_summary()."""
  by_cost = {0: [], 1: [], 2: [], 3: []}
  for idx, (color, cost) in enumerate(forum_summary):
    by_cost[cost].append((idx, color))

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
    dx, dy = x + 8, y + 30
    for die_idx, color in by_cost[cost]:
      fill = DIE_HEX[color]
      text_color = "#111" if color in (DieColor.WHITE, DieColor.YELLOW) else "#fff"
      parts.append(f'<rect x="{dx}" y="{dy}" width="30" height="30" rx="5" '
                   f'fill="{fill}" stroke="#111" stroke-width="1.2"/>')
      parts.append(f'<text x="{dx + 15}" y="{dy + 20}" fill="{text_color}" '
                   f'font-size="12" text-anchor="middle" font-weight="bold">'
                   f'{die_idx}</text>')
      dx += 36
      if dx > x + cell_w - 30:
        dx = x + 8
        dy += 36
  parts.append("</svg>")
  return "".join(parts)


def render_board_svg(ps, width: int = 380) -> str:
  """A compact roll-and-write-style progress tracker for one player's board:
  one row per building, crossed spaces filled, remaining spaces outlined."""
  rows = [
      ("Warehouse", ps.warehouse_crossed, WAREHOUSE_SPACES,
       BUILDING_HEX[BuildingKind.WAREHOUSE]),
      ("Agora", ps.agora_crossed, AGORA_SPACES, BUILDING_HEX[BuildingKind.AGORA]),
      ("Market", bin(ps.market_crossed_mask).count("1"), MARKET_SPACES,
       BUILDING_HEX[BuildingKind.MARKET]),
      ("University", sum(ps.univ_lane_progress.values()), UNIVERSITY_LANE_SPACES * 3,
       BUILDING_HEX[BuildingKind.UNIVERSITY]),
      ("Guild Court", ps.guild_crossed, GUILD_COURT_SPACES,
       BUILDING_HEX[BuildingKind.GUILD_COURT]),
      ("Gallery", ps.gallery_crossed, GALLERY_SPACES,
       BUILDING_HEX[BuildingKind.GALLERY]),
      ("W.Barracks atk", ps.barracks_w_attack, BARRACKS_ATTACK_SPACES,
       BUILDING_HEX[BuildingKind.BARRACKS_WEST]),
      ("W.Barracks def", ps.barracks_w_defense, BARRACKS_DEFENSE_SPACES, _DEFENSE_HEX),
      ("E.Barracks atk", ps.barracks_e_attack, BARRACKS_ATTACK_SPACES,
       BUILDING_HEX[BuildingKind.BARRACKS_EAST]),
      ("E.Barracks def", ps.barracks_e_defense, BARRACKS_DEFENSE_SPACES, _DEFENSE_HEX),
      ("Wonder", ps.wonder_crossed, WONDER_SPACES, BUILDING_HEX[BuildingKind.WONDER]),
  ]
  row_h, label_w, sq, gap = 26, 110, 18, 4
  height = len(rows) * row_h + 8
  parts = [f'<svg viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" '
           f'font-family="sans-serif">']
  for i, (label, crossed, total, color) in enumerate(rows):
    y = i * row_h + 4
    parts.append(f'<text x="0" y="{y + 14}" fill="#ccc" font-size="11">{label}</text>')
    for s in range(total):
      x = label_w + s * (sq + gap)
      filled = s < crossed
      fill = color if filled else "none"
      opacity = "1" if filled else "0.5"
      parts.append(f'<rect x="{x}" y="{y}" width="{sq}" height="{sq}" rx="3" '
                   f'fill="{fill}" stroke="{color}" stroke-width="1.3" '
                   f'opacity="{opacity}"/>')
  parts.append("</svg>")
  return "".join(parts)
