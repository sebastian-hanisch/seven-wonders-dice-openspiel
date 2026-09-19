"""The OpenSpiel State for 7 Wonders Dice.

No remaining rule simplifications for player-facing decisions: Agora's dual
symbol-group track, Market's per-space choice, every CROSS_SPACE_ONE_OF
building choice, and every other "cross a space of X" resolution that could
be ambiguous (Barracks attack-vs-defense, University's 3 lanes, Market via
the Spy) are all real BONUS-phase player choices -- see `_cross_options` /
`begin_cross` below. Two structural notes on the two that took real engine
changes rather than just exposing an existing hook:

  - University-unlock die swap: the rulebook says the replaced grey die is
    "chosen randomly" -- modeled as a genuine chance node (`UNLOCK_CHANCE`
    phase), deferred to right before the *next* SHAKE rather than applied
    mid-round. That also fixes a subtler issue than just "which slot":
    the physical game can only swap a die between rounds (this round's
    dice are already shaken/committed), so a same-round pick could never
    see a just-unlocked die either -- both are fixed by the same deferral.
  - Tiebreak ("most unspent coins", then shared victory): `returns()`
    already ranks players exactly right for this (VP, then a coin nudge
    that can never outweigh a real VP difference -- see `_finish_game`);
    a genuine tie is a UI/presentation concern (declaring a shared
    winner), not a utility-vector one, so it's handled in app.py's
    terminal-state screen, not here.

Everything above is a *rule* simplification. What's still uncertain is
*board data* (the 6 non-Giza cities' exact Wonder numbers) -- a source
problem (no clear photo), not a simplification; see RULES.md.
"""

import pyspiel
from sevenwonders_dice import effects as effects_lib
from sevenwonders_dice.boards import ALL_BOARDS, BoardDef, BuildingDef
from sevenwonders_dice.constants import (ActionType, BONUSES_TO_END_GAME,
                                          BuildingKind, COMPARABLE_BUILDINGS,
                                          DieColor, NUM_FORUM_DICE,
                                          NUM_QUADRANTS, PASS_COINS,
                                          QUADRANT_COSTS, SPECIAL_DICE,
                                          STARTING_DICE)
from sevenwonders_dice.describe import (BUILDING_NAMES, DIE_COLOR_NAMES,
                                         describe_effects)
from sevenwonders_dice.dice import (FACES, NUM_SHAKE_OUTCOMES_PER_DIE,
                                     decode_shake_outcome)
from sevenwonders_dice.player_state import (AGORA_SPACES,
                                             BARRACKS_ATTACK_SPACES,
                                             BARRACKS_DEFENSE_SPACES,
                                             GALLERY_SPACES,
                                             GUILD_COURT_SPACES,
                                             MARKET_SPACES, NUM_BONUS_SLOTS,
                                             UNIVERSITY_LANE_SPACES,
                                             WAREHOUSE_SPACES, WONDER_SPACES,
                                             PlayerState)

# Round-action encoding (also reused for BONUS-phase extra actions):
#   0 = PASS, 1 = WONDER, 2..8 = BUILD using Forum die at index (action - 2),
#   9..14 = build Market space (action - 9) using the (always exactly one)
#   Yellow die -- a real space choice, not the generic per-die slot, since
#   Market is fillable "in any order" (see boards.py) and which space you
#   pick matters (different costs/effects per space).
ACTION_PASS = 0
ACTION_WONDER = 1
ACTION_BUILD_BASE = 2
ACTION_MARKET_BASE = ACTION_BUILD_BASE + NUM_FORUM_DICE  # 9
NUM_ROUND_ACTIONS = ACTION_MARKET_BASE + MARKET_SPACES  # 9 + 6 = 15

_TOTAL_SPACES = {
    BuildingKind.WAREHOUSE: WAREHOUSE_SPACES,
    BuildingKind.AGORA: AGORA_SPACES,
    BuildingKind.MARKET: MARKET_SPACES,
    BuildingKind.GUILD_COURT: GUILD_COURT_SPACES,
    BuildingKind.GALLERY: GALLERY_SPACES,
    BuildingKind.UNIVERSITY: UNIVERSITY_LANE_SPACES * 3,
    BuildingKind.BARRACKS_WEST: BARRACKS_ATTACK_SPACES + BARRACKS_DEFENSE_SPACES,
    BuildingKind.BARRACKS_EAST: BARRACKS_ATTACK_SPACES + BARRACKS_DEFENSE_SPACES,
}


def _simple_building_def(board: BoardDef, kind: BuildingKind) -> BuildingDef:
  # AGORA and MARKET are deliberately absent: both have their own dedicated
  # resolution (_next_agora / _next_market) since a flat "next index in
  # board order" doesn't apply to them (Agora is 2 gated tracks, Market is
  # fillable in any order) -- see boards.py / RULES.md.
  return {
      BuildingKind.WAREHOUSE: board.warehouse,
      BuildingKind.GUILD_COURT: board.guild_court,
      BuildingKind.GALLERY: board.gallery,
  }[kind]


class SevenWondersDiceState(pyspiel.State):
  """See module docstring."""

  def __init__(self, game, num_players: int):
    super().__init__(game)
    self._num_players = num_players
    self._game_over = False
    self._returns = [0.0] * num_players

    self._phase = "DEAL"
    self._deal_index = 0
    self._remaining_boards = list(range(len(ALL_BOARDS)))
    self._players = [None] * num_players  # type: list

    self._forum_colors = list(STARTING_DICE)
    self._forum_faces = [FACES[c][0] for c in self._forum_colors]
    self._forum_quadrant = [0] * NUM_FORUM_DICE
    self._shake_die_index = 0
    self._pending_unlocks = []  # DieColor values awaiting a chance-node swap

    self._pending_round_actions = {}
    self._bonus_queue = []  # list of player indices with pending decisions
    self._agora_first_completer = None

    self._end_game_triggered = False
    self._final_round_player = None  # whoever triggered it (finishes the round they're in, then 1 more)
    self._rounds_after_trigger = 0

  # -- OpenSpiel required overrides --------------------------------------

  def current_player(self):
    if self._game_over:
      return pyspiel.PlayerId.TERMINAL
    if self._phase in ("DEAL", "SHAKE", "UNLOCK_CHANCE"):
      return pyspiel.PlayerId.CHANCE
    if self._phase == "ACTION":
      # With exactly one player, a SIMULTANEOUS round with one actor is the
      # same thing as a sequential decision -- returning the concrete
      # player id here (instead of SIMULTANEOUS) is what lets the solo
      # game variant (see game.py) declare itself SEQUENTIAL and be solved
      # directly by OpenSpiel's own MCTSBot. See bots/mcts_bot.py.
      if self._num_players == 1:
        return 0
      return pyspiel.PlayerId.SIMULTANEOUS
    if self._phase == "BONUS":
      return self._bonus_queue[0]
    raise ValueError(self._phase)

  def _legal_actions(self, player):
    if self._phase == "BONUS":
      return self._legal_bonus_actions(player)
    if self._phase == "ACTION":
      return self._legal_round_actions(player)
    if self._phase in ("DEAL", "SHAKE", "UNLOCK_CHANCE"):
      return [a for a, _p in self.chance_outcomes()]
    raise ValueError(f"_legal_actions called in phase {self._phase}")

  def chance_outcomes(self):
    if self._phase == "DEAL":
      n = len(self._remaining_boards)
      p = 1.0 / n
      return [(i, p) for i in range(n)]
    if self._phase == "SHAKE":
      p = 1.0 / NUM_SHAKE_OUTCOMES_PER_DIE
      return [(i, p) for i in range(NUM_SHAKE_OUTCOMES_PER_DIE)]
    if self._phase == "UNLOCK_CHANCE":
      n = len(self._grey_positions())
      p = 1.0 / n
      return [(i, p) for i in range(n)]
    raise ValueError(self._phase)

  def _apply_action(self, action):
    if self._phase == "DEAL":
      self._apply_deal(action)
    elif self._phase == "SHAKE":
      self._apply_shake(action)
    elif self._phase == "UNLOCK_CHANCE":
      self._apply_unlock_chance(action)
    elif self._phase == "BONUS":
      player = self._bonus_queue[0]
      self._apply_bonus_action(player, action)
      if not self._players[player].pending_bonus_actions:
        self._bonus_queue.pop(0)
      if not self._bonus_queue:
        self._advance_round_or_end()
    elif self._phase == "ACTION" and self._num_players == 1:
      self._pending_round_actions = {0: action}
      self._resolve_round()
    else:
      raise ValueError(self._phase)

  def _apply_actions(self, actions):
    assert self._phase == "ACTION"
    for p, a in enumerate(actions):
      self._pending_round_actions[p] = a
    self._resolve_round()

  def is_terminal(self):
    return self._game_over

  def returns(self):
    return list(self._returns)

  def __str__(self):
    return (f"phase={self._phase} shake_idx={self._shake_die_index} "
            f"bonus_queue={self._bonus_queue} "
            f"pending_unlocks={self._pending_unlocks} game_over={self._game_over}")

  def player_state(self, player: int) -> PlayerState:
    """Read-only access to a player's board/economy, for observers and bots.
    `None` until that player's board has been dealt."""
    return self._players[player]

  def forum_summary(self):
    """[(DieColor, quadrant_cost), ...] for the 7 Forum dice, in slot
    order, for observers/UIs. Empty during the DEAL phase (before the
    first shake)."""
    return [(c, QUADRANT_COSTS[q])
            for c, q in zip(self._forum_colors, self._forum_quadrant)]

  def forum_details(self):
    """[(DieColor, quadrant_cost, DieFace), ...] for the 7 Forum dice --
    like forum_summary() but also exposes each die's currently-rolled
    DieFace (dice.py), for UIs that want to show *which* building/lane/
    attack-or-defense a die targets right now, not just its color."""
    return [(c, QUADRANT_COSTS[q], f) for c, q, f in
            zip(self._forum_colors, self._forum_quadrant, self._forum_faces)]

  def make_solo_snapshot(self, player: int, solo_game) -> "SevenWondersDiceState":
    """Builds a 1-player solo-mode state (see game.py's SEQUENTIAL solo
    game variant) seeded with `player`'s current progress and the live
    Forum, at the same decision point `player` is actually facing right
    now (same dice, same costs) -- ready to hand to OpenSpiel's own
    MCTSBot. See bots/mcts_bot.py for why this is sound: a player's own
    outcome this round never depends on what others simultaneously pick
    (RULES.md), so freezing everyone else's current standing (for Guild
    Court/Barracks) and letting `player` search on alone is not an
    approximation of the round in progress, only of future rounds (where
    it ignores that opponents keep playing too). Works from either an
    ACTION (simultaneous round) or BONUS (this player's own follow-up
    decision) decision point -- whichever `player` is actually facing.
    """
    assert self._phase in ("ACTION", "BONUS")
    if self._phase == "BONUS":
      assert self._bonus_queue and self._bonus_queue[0] == player
    solo = SevenWondersDiceState(solo_game, 1)
    solo._phase = self._phase
    solo._bonus_queue = [0] if self._phase == "BONUS" else []
    solo._players = [self._players[player].clone()]
    solo._forum_colors = list(self._forum_colors)
    solo._forum_faces = list(self._forum_faces)
    solo._forum_quadrant = list(self._forum_quadrant)
    solo._pending_unlocks = list(self._pending_unlocks)
    return solo

  # -- human-readable descriptions (for the Streamlit app / debugging) ----

  def legal_action_descriptions(self, player: int):
    """[(action, description), ...] for every currently legal action of
    `player`, in the same order as legal_actions(player)."""
    return [(a, self.describe_action(player, a))
            for a in self.legal_actions(player)]

  def describe_action(self, player: int, action: int) -> str:
    ps = self._players[player]
    if self._phase == "BONUS":
      kind, arg = ps.pending_bonus_actions[0]
      if kind == "CHOOSE_BONUS":
        effect = ps.board.bonus_slots[action]
        return f"Choose bonus {action + 1}/3: {describe_effects((effect,))}"
      if kind == "FREE_A":
        return "(free action, no die cost) " + self._describe_build_or_pass(ps, action, free=True)
      if kind == "ANY":
        return "(bonus action) " + self._describe_build_or_pass(ps, action)
      if kind == "CROSS_ONE_OF":
        buildings = arg
        if action < len(buildings):
          return f"Cross a space of {BUILDING_NAMES[buildings[action]]}"
        return "(no valid target to cross)"
      if kind == "CROSS_SPACE":
        building, times = arg
        options = self._cross_options(ps, building)
        if action < len(options):
          space, ctx = options[action]
          label = self._describe_cross_target(building, ctx)
          extra = f" -> {describe_effects(space.effects)}" if space.effects else ""
          more = f" (then {times - 1} more)" if times > 1 else ""
          return f"Cross {label} (space cost {space.cost} resources){extra}{more}"
        return "(no valid target to cross)"
      raise ValueError(kind)
    return self._describe_build_or_pass(ps, action)

  def _describe_cross_target(self, building: BuildingKind, ctx) -> str:
    name = BUILDING_NAMES[building]
    if building == BuildingKind.AGORA:
      return f"{name} space (symbol group {'A' if ctx == 0 else 'B'})"
    if building in (BuildingKind.BARRACKS_WEST, BuildingKind.BARRACKS_EAST):
      return f"{name} space ({ctx})"
    if building == BuildingKind.UNIVERSITY:
      return f"{name} space ({ctx} lane)"
    if building == BuildingKind.MARKET:
      return f"{name} space #{ctx + 1}"
    return f"{name} space"

  def _describe_build_or_pass(self, ps: PlayerState, action: int, free: bool = False) -> str:
    if action == ACTION_PASS:
      return f"Pass (+{PASS_COINS} coins)"
    if action == ACTION_WONDER:
      space = ps.board.wonder[ps.wonder_crossed]
      step = ps.wonder_crossed + 1
      return (f"Build Wonder step {step}/{WONDER_SPACES} "
              f"(cost {space.cost} resources) -> {describe_effects(space.effects)}")
    if action >= ACTION_MARKET_BASE:
      space_idx = action - ACTION_MARKET_BASE
      space = ps.board.market.spaces[space_idx]
      yellow_idx = self._forum_colors.index(DieColor.YELLOW)
      quadrant_cost = QUADRANT_COSTS[self._forum_quadrant[yellow_idx]]
      die_cost_str = "free" if free else f"{ps.effective_die_cost(DieColor.YELLOW, quadrant_cost)} coins"
      extra = f" -> {describe_effects(space.effects)}" if space.effects else ""
      return (f"Use Yellow die (die cost {die_cost_str}) -> Market space "
              f"#{space_idx + 1} (space cost {space.cost} resources){extra}")
    die_idx = action - ACTION_BUILD_BASE
    color = self._forum_colors[die_idx]
    face = self._forum_faces[die_idx]
    quadrant_cost = QUADRANT_COSTS[self._forum_quadrant[die_idx]]
    die_cost_str = "free" if free else f"{ps.effective_die_cost(color, quadrant_cost)} coins"
    if color == DieColor.BLACK:
      building = face.wildcard_building
      name = BUILDING_NAMES.get(building, "no valid target")
      options = self._cross_options(ps, building) if building is not None else []
      suffix = " -- choose which space" if len(options) > 1 else ""
      return (f"Use die #{die_idx} (Black (Spy), die cost {die_cost_str}) "
              f"-> {name}{suffix}")
    kind, space, _ctx = self._resolve_die_target(ps, color, face)
    building = BUILDING_NAMES[kind]
    extra = f" -> {describe_effects(space.effects)}" if space.effects else ""
    vp_str = f", VP {space.printed_vp}" if space.printed_vp else ""
    return (f"Use die #{die_idx} ({DIE_COLOR_NAMES[color]}, die cost {die_cost_str}) "
            f"-> {building} (space cost {space.cost} resources{vp_str}){extra}")

  # -- DEAL phase ----------------------------------------------------------

  def _apply_deal(self, action):
    board_idx = self._remaining_boards.pop(action)
    self._players[self._deal_index] = PlayerState(ALL_BOARDS[board_idx], board_idx)
    self._deal_index += 1
    if self._deal_index == self._num_players:
      self._phase = "SHAKE"
      self._shake_die_index = 0

  # -- SHAKE phase -----------------------------------------------------------

  def _apply_shake(self, action):
    face_idx, quadrant = decode_shake_outcome(action)
    color = self._forum_colors[self._shake_die_index]
    self._forum_faces[self._shake_die_index] = FACES[color][face_idx]
    self._forum_quadrant[self._shake_die_index] = quadrant
    self._shake_die_index += 1
    if self._shake_die_index == NUM_FORUM_DICE:
      self._phase = "ACTION"
      self._pending_round_actions = {}

  # -- UNLOCK_CHANCE phase --------------------------------------------------
  #
  # A University unlock (EffectType.UNLOCK_DIE) only queues the color in
  # `_pending_unlocks`; the Forum doesn't actually gain that die until this
  # phase runs, inserted by _advance_round_or_end() right before the next
  # SHAKE -- matching the physical game (dice can only be swapped between
  # rounds) and giving the "which grey die" pick a real, fair chance node
  # instead of a deterministic placeholder.

  def _grey_positions(self):
    return [i for i, c in enumerate(self._forum_colors) if c == DieColor.GREY]

  def _apply_unlock_chance(self, action):
    color = self._pending_unlocks.pop(0)
    pos = self._grey_positions()[action]
    self._forum_colors[pos] = color
    self._forum_faces[pos] = FACES[color][0]
    if self._pending_unlocks:
      return  # another color is waiting: stay in UNLOCK_CHANCE for it
    self._phase = "SHAKE"
    self._shake_die_index = 0

  # -- ACTION (simultaneous) phase -----------------------------------------

  def _legal_round_actions(self, player):
    ps = self._players[player]
    actions = [ACTION_PASS]
    if ps.wonder_crossed < WONDER_SPACES:
      space = ps.board.wonder[ps.wonder_crossed]
      if ps.can_pay(space.cost):
        actions.append(ACTION_WONDER)
    for die_idx in range(NUM_FORUM_DICE):
      if self._forum_colors[die_idx] == DieColor.YELLOW:
        continue  # see _legal_market_actions -- a separate, explicit choice
      if self._can_build_with_die(ps, die_idx):
        actions.append(ACTION_BUILD_BASE + die_idx)
    actions.extend(self._legal_market_actions(ps))
    return actions

  def _can_build_with_die(self, ps: PlayerState, die_idx: int) -> bool:
    color = self._forum_colors[die_idx]
    if color in SPECIAL_DICE and color not in ps.unlocked_by_me:
      return False
    quadrant_cost = QUADRANT_COSTS[self._forum_quadrant[die_idx]]
    die_cost = ps.effective_die_cost(color, quadrant_cost)
    if ps.coins < die_cost:
      return False
    face = self._forum_faces[die_idx]
    if color == DieColor.BLACK:
      building = face.wildcard_building
      if building is None:
        return False
      return bool(self._cross_options(ps, building, available_coins=ps.coins - die_cost))
    kind, space, _ctx = self._resolve_die_target(ps, color, face)
    if kind is None or space is None:
      return False
    return ps.coins - die_cost >= max(0, space.cost - ps.resources)

  def _resolve_die_target(self, ps: PlayerState, color: DieColor, face):
    """Returns (BuildingKind, Space, context) for what picking this die
    would build next, or (None, None, None) if nothing is available. Not
    valid for BLACK (the Spy): its target can be ambiguous (more than one
    legal sub-target), so it's resolved via _cross_options instead --
    see _can_build_with_die / _apply_die_pick."""
    if color == DieColor.GREY:
      return self._next_simple(ps, BuildingKind.WAREHOUSE)
    if color == DieColor.YELLOW:
      return self._next_market(ps)
    if color == DieColor.BLUE:
      return self._next_agora(ps, face.agora_group)
    if color == DieColor.WHITE:
      return self._next_simple(ps, BuildingKind.GALLERY)
    if color == DieColor.PURPLE:
      return self._next_guild_court(ps, face.guild_target)
    if color == DieColor.GREEN:
      return self._next_university(ps, face.university_lane)
    if color == DieColor.RED:
      return self._next_barracks(ps, face.barracks_is_west, face.barracks_is_attack)
    raise ValueError(color)

  def _next_simple(self, ps, kind):
    bdef = _simple_building_def(ps.board, kind)
    idx = ps.building_progress(kind)
    if idx >= len(bdef.spaces):
      return None, None, None
    return kind, bdef.spaces[idx], None

  def _next_agora(self, ps, group):
    """The next not-yet-crossed Agora space in symbol `group`'s (0 or 1)
    own track -- Agora is two independently-gated tracks, one per blue-die
    symbol group (rulebook: "each space takes either of 2 symbols"), not a
    single sequence."""
    if group is None:
      return None, None, None
    group_spaces = [s for s in ps.board.agora.spaces if s.agora_symbol_group == group]
    idx = ps.agora_group_progress[group]
    if idx >= len(group_spaces):
      return None, None, None
    return BuildingKind.AGORA, group_spaces[idx], group

  def _next_market(self, ps):
    bdef = ps.board.market
    open_idxs = [i for i in range(len(bdef.spaces))
                 if not (ps.market_crossed_mask >> i) & 1]
    if not open_idxs:
      return None, None, None
    best = min(open_idxs, key=lambda i: bdef.spaces[i].cost)
    return BuildingKind.MARKET, bdef.spaces[best], best

  def _legal_market_actions(self, ps, waive_die_cost=False):
    """Legal ACTION_MARKET_BASE+i actions: building Market via the Yellow
    die is a real choice of *which* open space to fill (not auto-picked),
    since Market is fillable in any order and spaces differ in cost/effect."""
    if waive_die_cost:
      die_cost = 0
    else:
      yellow_idx = self._forum_colors.index(DieColor.YELLOW)
      quadrant_cost = QUADRANT_COSTS[self._forum_quadrant[yellow_idx]]
      die_cost = ps.effective_die_cost(DieColor.YELLOW, quadrant_cost)
      if ps.coins < die_cost:
        return []
    bdef = ps.board.market
    return [ACTION_MARKET_BASE + i for i, space in enumerate(bdef.spaces)
            if not (ps.market_crossed_mask >> i) & 1
            and ps.coins - die_cost >= max(0, space.cost - ps.resources)]

  def _next_guild_court(self, ps, target_building):
    idx = ps.guild_crossed
    if idx >= GUILD_COURT_SPACES or target_building is None:
      return None, None, None
    if not self._guild_court_condition_met(ps, target_building):
      return None, None, None
    return BuildingKind.GUILD_COURT, ps.board.guild_court.spaces[idx], target_building

  def _guild_court_condition_met(self, ps, target_building):
    me = self._players.index(ps)
    my_count = ps.building_progress(target_building)
    if self._num_players == 2:
      other = self._players[1 - me]
      return my_count > other.building_progress(target_building)
    # num_players == 1 (solo mode, see game.py) falls through here too:
    # both "neighbors" resolve to the player themselves, so the condition
    # degenerates to my_count >= my_count -- always true, i.e. no
    # opponents means no Guild Court gating friction. That's a deliberate
    # consequence of the general formula, not a special case.
    left = self._players[(me - 1) % self._num_players]
    right = self._players[(me + 1) % self._num_players]
    return (my_count >= left.building_progress(target_building) and
            my_count >= right.building_progress(target_building))

  def _next_university(self, ps, lane):
    if lane is None:
      return None, None, None
    idx = ps.univ_lane_progress[lane]
    if idx >= UNIVERSITY_LANE_SPACES:
      return None, None, None
    lane_spaces = {"black": ps.board.university.lane_black,
                   "purple": ps.board.university.lane_purple,
                   "white": ps.board.university.lane_white}[lane]
    return BuildingKind.UNIVERSITY, lane_spaces[idx], lane

  def _next_barracks(self, ps, is_west, is_attack):
    if is_west is None or is_attack is None:
      return None, None, None
    kind = BuildingKind.BARRACKS_WEST if is_west else BuildingKind.BARRACKS_EAST
    bdef = ps.board.barracks_west if is_west else ps.board.barracks_east
    if is_attack:
      idx = ps.barracks_w_attack if is_west else ps.barracks_e_attack
      if idx >= BARRACKS_ATTACK_SPACES:
        return None, None, None
      return kind, bdef.attack[idx], "attack"
    idx = ps.barracks_w_defense if is_west else ps.barracks_e_defense
    if idx >= BARRACKS_DEFENSE_SPACES:
      return None, None, None
    return kind, bdef.defense[idx], "defense"

  # -- "cross a space of X" resolution, for both die picks (the Spy) and
  # effects (CROSS_SPACE / CROSS_SPACE_ONE_OF / CROSS_UP_TO_TWO) ----------

  def _cross_options(self, ps: PlayerState, building: BuildingKind,
                      available_coins=None):
    """All distinct, currently-affordable sub-targets for "cross a space of
    `building`". Only ever more than one when `building` has independently
    gated sub-tracks: Agora's 2 symbol groups, Barracks' attack/defense,
    University's 3 lanes, or Market's any-order spaces -- exactly the
    buildings that already require a real choice when reached via their
    own die (Blue/Red/Green/Yellow), so a Spy pick or a generic effect that
    reduces to one of them is resolved the same way: for real, not by a
    silent fixed preference. Returns [(Space, ctx), ...]."""
    if available_coins is None:
      available_coins = ps.coins

    def ok(space):
      return ps.can_pay_with(space.cost, available_coins)

    if building == BuildingKind.AGORA:
      out = []
      for group in (0, 1):
        _, space, ctx = self._next_agora(ps, group)
        if space is not None and ok(space):
          out.append((space, ctx))
      return out
    if building == BuildingKind.MARKET:
      bdef = ps.board.market
      return [(space, i) for i, space in enumerate(bdef.spaces)
              if not (ps.market_crossed_mask >> i) & 1 and ok(space)]
    if building == BuildingKind.UNIVERSITY:
      out = []
      for lane in ("black", "purple", "white"):
        _, space, ctx = self._next_university(ps, lane)
        if space is not None and ok(space):
          out.append((space, ctx))
      return out
    if building in (BuildingKind.BARRACKS_WEST, BuildingKind.BARRACKS_EAST):
      is_west = building == BuildingKind.BARRACKS_WEST
      out = []
      for is_attack in (True, False):
        _, space, ctx = self._next_barracks(ps, is_west, is_attack)
        if space is not None and ok(space):
          out.append((space, ctx))
      return out
    if building in (BuildingKind.WAREHOUSE, BuildingKind.GALLERY):
      _, space, ctx = self._next_simple(ps, building)
      return [(space, ctx)] if space is not None and ok(space) else []
    return []  # GUILD_COURT: gated by a die-face comparison target, not this

  def begin_cross(self, ps: PlayerState, building: BuildingKind, times: int = 1) -> None:
    """Cross a space of `building`, `times` times (times=2 for
    CROSS_UP_TO_TWO). Resolves immediately whenever there's only one legal
    sub-target; queues a real BONUS-phase choice (see _legal_bonus_actions
    / _apply_bonus_action's "CROSS_SPACE" case) whenever there's more than
    one -- this is the callback effects.py's CROSS_SPACE/CROSS_UP_TO_TWO
    use, and CROSS_ONE_OF's own resolution funnels into it too once a
    building has been picked."""
    if times <= 0:
      return
    options = self._cross_options(ps, building)
    if not options:
      return
    if len(options) == 1:
      space, ctx = options[0]
      self._cross_specific(ps, building, space, ctx)
      self.begin_cross(ps, building, times - 1)
      return
    ps.pending_bonus_actions.append(("CROSS_SPACE", (building, times)))

  def _cross_specific(self, ps: PlayerState, kind: BuildingKind, space, ctx) -> None:
    player = self._players.index(ps)
    ps.pay(space.cost)
    self._advance_building(player, kind, ctx)
    if kind in (BuildingKind.BARRACKS_WEST, BuildingKind.BARRACKS_EAST) and ctx == "attack":
      self._score_barracks_attack(player, kind, space)
    self._apply_space_effects(player, space)
    self._maybe_trigger_bonus(player, kind)

  def queue_cross_one_of(self, ps: PlayerState, buildings) -> None:
    """CROSS_SPACE_ONE_OF is a real player choice (which building to
    advance), resolved as a BONUS-phase decision -- see _legal_bonus_actions
    / _apply_bonus_action's "CROSS_ONE_OF" case. Whichever building is
    picked then goes through begin_cross() too, so a building with its own
    sub-track ambiguity (e.g. Agora) gets a second, follow-up choice."""
    ps.pending_bonus_actions.append(("CROSS_ONE_OF", tuple(buildings)))

  def _resolve_round(self):
    for player in range(self._num_players):
      action = self._pending_round_actions[player]
      self._apply_round_action(player, action)
    self._pending_round_actions = {}
    self._start_bonus_phase_or_next_round()

  def _apply_round_action(self, player, action):
    ps = self._players[player]
    if action == ACTION_PASS:
      ps.coins += PASS_COINS
      return
    if action == ACTION_WONDER:
      space = ps.board.wonder[ps.wonder_crossed]
      if not ps.can_pay(space.cost):
        return  # became illegal due to simultaneous resolution order; no-op
      ps.pay(space.cost)
      ps.wonder_crossed += 1
      self._apply_space_effects(player, space)
      return
    self._apply_die_pick(player, action, waive_die_cost=False)

  def _pay_die_cost(self, ps: PlayerState, color: DieColor, die_cost: int) -> None:
    ps.coins -= die_cost
    ps.coins += ps.coins_on_die_choice.get(color, 0)

  def _apply_die_pick(self, player: int, action: int, waive_die_cost: bool) -> None:
    """Resolves picking a die (or a Market-space action, see
    ACTION_MARKET_BASE) -- the single path used by a normal round action,
    a FREE_A bonus (die cost waived), and an ANY bonus's die-pick branch."""
    ps = self._players[player]
    if action >= ACTION_MARKET_BASE:
      space_idx = action - ACTION_MARKET_BASE
      bdef = ps.board.market
      if space_idx >= len(bdef.spaces) or (ps.market_crossed_mask >> space_idx) & 1:
        return  # became illegal (e.g. contested); no-op
      space = bdef.spaces[space_idx]
      if waive_die_cost:
        die_cost = 0
      else:
        yellow_idx = self._forum_colors.index(DieColor.YELLOW)
        quadrant_cost = QUADRANT_COSTS[self._forum_quadrant[yellow_idx]]
        die_cost = ps.effective_die_cost(DieColor.YELLOW, quadrant_cost)
      if ps.coins < die_cost or not ps.can_pay(space.cost, coin_cost=die_cost):
        return
      self._pay_die_cost(ps, DieColor.YELLOW, die_cost)
      self._cross_specific(ps, BuildingKind.MARKET, space, space_idx)
      return

    die_idx = action - ACTION_BUILD_BASE
    color = self._forum_colors[die_idx]
    face = self._forum_faces[die_idx]
    if waive_die_cost:
      die_cost = 0
    else:
      quadrant_cost = QUADRANT_COSTS[self._forum_quadrant[die_idx]]
      die_cost = ps.effective_die_cost(color, quadrant_cost)
    if ps.coins < die_cost:
      return

    if color == DieColor.BLACK:
      building = face.wildcard_building
      if building is None:
        return
      options = self._cross_options(ps, building, available_coins=ps.coins - die_cost)
      if not options:
        return
      self._pay_die_cost(ps, color, die_cost)
      if len(options) == 1:
        space, ctx = options[0]
        self._cross_specific(ps, building, space, ctx)
      else:
        ps.pending_bonus_actions.append(("CROSS_SPACE", (building, 1)))
      return

    kind, space, ctx = self._resolve_die_target(ps, color, face)
    if kind is None or not ps.can_pay(space.cost, coin_cost=die_cost):
      return
    self._pay_die_cost(ps, color, die_cost)
    self._cross_specific(ps, kind, space, ctx)

  def _advance_building(self, player, kind, ctx):
    ps = self._players[player]
    if kind == BuildingKind.WAREHOUSE:
      ps.warehouse_crossed += 1
      ps.resources += 1
    elif kind == BuildingKind.AGORA:
      ps.agora_group_progress[ctx] += 1
      if (ps.building_progress(BuildingKind.AGORA) == AGORA_SPACES
          and self._agora_first_completer is None):
        self._agora_first_completer = player
        ps.banked_end_game_vp += ps.board.agora_completion_bonus_vp
    elif kind == BuildingKind.MARKET:
      ps.market_crossed_mask |= (1 << ctx)
    elif kind == BuildingKind.GUILD_COURT:
      ps.guild_crossed += 1
    elif kind == BuildingKind.GALLERY:
      ps.gallery_crossed += 1
    elif kind == BuildingKind.UNIVERSITY:
      ps.univ_lane_progress[ctx] += 1
    elif kind in (BuildingKind.BARRACKS_WEST, BuildingKind.BARRACKS_EAST):
      is_west = kind == BuildingKind.BARRACKS_WEST
      if ctx == "attack":
        if is_west:
          ps.barracks_w_attack += 1
        else:
          ps.barracks_e_attack += 1
      else:
        if is_west:
          ps.barracks_w_defense += 1
        else:
          ps.barracks_e_defense += 1
    else:
      raise ValueError(kind)

  def _score_barracks_attack(self, player, kind, space):
    ps = self._players[player]
    if self._num_players == 1:
      # No neighbor to attack in solo mode (see game.py's solo variant) --
      # treat it the same as attacking an undefended city (rulebook: "if
      # the city has no defense, gain the indicated Victory Points").
      ps.barracks_vp_total += space.printed_vp
      return
    is_west = kind == BuildingKind.BARRACKS_WEST
    target = self._players[(player - 1) % self._num_players] if is_west \
        else self._players[(player + 1) % self._num_players]
    # From the target's perspective the attacker is on their opposite side.
    defense = target.barracks_e_defense if is_west else target.barracks_w_defense
    vp = max(0, space.printed_vp - defense)
    ps.barracks_vp_total += vp

  def _apply_space_effects(self, player, space):
    ps = self._players[player]
    for eff in space.effects:
      effects_lib.apply_immediate(eff, ps, self)

  def _maybe_trigger_bonus(self, player, kind):
    if kind == BuildingKind.WONDER:
      return
    ps = self._players[player]
    total = _TOTAL_SPACES[kind]
    if ps.building_progress(kind) == total:
      ps.pending_bonus_actions.append(("CHOOSE_BONUS", None))

  # -- effect-interpreter callbacks (see effects.apply_immediate) ---------

  def building_progress(self, ps: PlayerState, kind: BuildingKind) -> int:
    return ps.building_progress(kind)

  def unlock_special_die(self, ps: PlayerState, color: DieColor) -> None:
    """Only marks `color` as usable by `ps` and queues it to actually enter
    the Forum -- the swap itself is deferred to a genuine chance node right
    before the next SHAKE (see the UNLOCK_CHANCE phase below), both for
    *which* grey slot becomes the new color (rulebook: "chosen randomly")
    and for *when*: the physical game can only swap a die between rounds
    (this round's dice are already shaken/committed), so immediately
    swapping mid-round was never right either -- deferring fixes both."""
    ps.unlocked_by_me.add(color)
    if color not in self._forum_colors and color not in self._pending_unlocks:
      self._pending_unlocks.append(color)

  # -- BONUS phase (sequential per-player follow-ups) ----------------------

  def _start_bonus_phase_or_next_round(self):
    self._bonus_queue = [p for p in range(self._num_players)
                          if self._players[p].pending_bonus_actions]
    if self._bonus_queue:
      self._phase = "BONUS"
    else:
      self._advance_round_or_end()

  def _legal_bonus_actions(self, player):
    ps = self._players[player]
    kind, arg = ps.pending_bonus_actions[0]
    if kind == "CHOOSE_BONUS":
      return [i for i in range(NUM_BONUS_SLOTS)
              if not (ps.bonus_used_mask >> i) & 1] or [0]
    if kind == "FREE_A":
      actions = []
      for die_idx in range(NUM_FORUM_DICE):
        color = self._forum_colors[die_idx]
        if color == DieColor.YELLOW:
          continue  # see _legal_market_actions -- a separate, explicit choice
        if color in SPECIAL_DICE and color not in ps.unlocked_by_me:
          continue
        face = self._forum_faces[die_idx]
        if color == DieColor.BLACK:
          building = face.wildcard_building
          if building is not None and self._cross_options(ps, building):
            actions.append(ACTION_BUILD_BASE + die_idx)
          continue
        k, space, _ctx = self._resolve_die_target(ps, color, face)
        if k is not None and ps.can_pay(space.cost):
          actions.append(ACTION_BUILD_BASE + die_idx)
      actions.extend(self._legal_market_actions(ps, waive_die_cost=True))
      return actions or [ACTION_PASS]
    if kind == "ANY":
      return self._legal_round_actions(player)
    if kind == "CROSS_ONE_OF":
      buildings = arg
      choices = [i for i, b in enumerate(buildings) if self._cross_options(ps, b)]
      return choices or [0]
    if kind == "CROSS_SPACE":
      building, _times = arg
      options = self._cross_options(ps, building)
      return list(range(len(options))) or [0]
    raise ValueError(kind)

  def _apply_bonus_action(self, player, action):
    ps = self._players[player]
    kind, arg = ps.pending_bonus_actions.pop(0)
    if kind == "CHOOSE_BONUS":
      if not ((ps.bonus_used_mask >> action) & 1) and action < NUM_BONUS_SLOTS:
        ps.bonus_used_mask |= (1 << action)
        ps.bonus_crossed += 1
        effects_lib.apply_immediate(ps.board.bonus_slots[action], ps, self)
        if ps.bonus_crossed == BONUSES_TO_END_GAME and not self._end_game_triggered:
          self._end_game_triggered = True
          self._final_round_player = player
      return
    if kind == "FREE_A":
      if action != ACTION_PASS:
        self._apply_die_pick(player, action, waive_die_cost=True)
      return
    if kind == "ANY":
      self._apply_round_action(player, action)
      return
    if kind == "CROSS_ONE_OF":
      buildings = arg
      if 0 <= action < len(buildings):
        self.begin_cross(ps, buildings[action], times=1)
      return
    if kind == "CROSS_SPACE":
      building, times = arg
      options = self._cross_options(ps, building)
      if 0 <= action < len(options):
        space, ctx = options[action]
        self._cross_specific(ps, building, space, ctx)
        self.begin_cross(ps, building, times - 1)
      return
    raise ValueError(kind)

  def _advance_round_or_end(self):
    if self._end_game_triggered:
      self._rounds_after_trigger += 1
      if self._rounds_after_trigger >= 2:  # the triggering round + 1 final round
        self._finish_game()
        return
    if self._pending_unlocks:
      self._phase = "UNLOCK_CHANCE"
    else:
      self._phase = "SHAKE"
      self._shake_die_index = 0

  def _finish_game(self):
    self._game_over = True
    # Tiebreak is "most unspent coins" (then shared victory). A tiny coin
    # nudge on the returned utility reflects that without ever letting it
    # override a real Victory Point difference -- exactly right for
    # ranking (what returns() is for); declaring an actual shared winner
    # is a presentation concern, handled in app.py's terminal screen.
    self._final_scores = [ps.total_end_game_vp() for ps in self._players]
    for i, ps in enumerate(self._players):
      self._returns[i] = self._final_scores[i] + ps.coins * 1e-3
