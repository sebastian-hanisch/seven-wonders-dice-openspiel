"""Play 7 Wonders Dice against a bot in the browser.

    streamlit run app.py

Lets a human take one seat while RandomBot/HeuristicBot/SearchBot play the
rest. Everything else in this repo is pyspiel-facing; this file is the one
place that's Streamlit-specific -- it just drives the same public State
API (legal_actions / apply_action(s) / describe_action / player_state)
that examples/evaluate_bots.py drives, one rerun at a time.
"""

import random

import pyspiel
import streamlit as st

import sevenwonders_dice  # noqa: F401  (registers the games)
from sevenwonders_dice.bots import HeuristicBot, RandomBot, SearchBot
from sevenwonders_dice.bots.base import advance_through_chance_nodes
from sevenwonders_dice.constants import BuildingKind
from sevenwonders_dice.describe import BUILDING_NAMES, DIE_COLOR_NAMES
from sevenwonders_dice.player_state import (AGORA_SPACES, GALLERY_SPACES,
                                             GUILD_COURT_SPACES,
                                             MARKET_SPACES,
                                             UNIVERSITY_LANE_SPACES,
                                             WAREHOUSE_SPACES, WONDER_SPACES)

st.set_page_config(page_title="7 Wonders Dice", page_icon="\U0001F3DB️", layout="wide")

_PROGRESS_BUILDINGS = [
    (BuildingKind.WAREHOUSE, WAREHOUSE_SPACES),
    (BuildingKind.AGORA, AGORA_SPACES),
    (BuildingKind.MARKET, MARKET_SPACES),
    (BuildingKind.UNIVERSITY, UNIVERSITY_LANE_SPACES * 3),
    (BuildingKind.GUILD_COURT, GUILD_COURT_SPACES),
    (BuildingKind.GALLERY, GALLERY_SPACES),
]

_BOT_FACTORIES = {
    "Random": lambda rng, sims: RandomBot(rng),
    "Heuristic": lambda rng, sims: HeuristicBot(),
    "Search (MCTS)": lambda rng, sims: SearchBot(
        max_simulations=sims, seed=rng.randrange(2**31)),
}


def _log(message: str) -> None:
  st.session_state.log.append(message)
  st.session_state.log = st.session_state.log[-60:]


def _start_game(num_players: int, human_seat: int, bot_choice: str,
                 sims: int, seed: int) -> None:
  rng = random.Random(seed)
  game = pyspiel.load_game("python_seven_wonders_dice", {"players": num_players})
  state = game.new_initial_state()
  bots = {
      p: _BOT_FACTORIES[bot_choice](rng, sims)
      for p in range(num_players) if p != human_seat
  }
  st.session_state.state = state
  st.session_state.game = game
  st.session_state.rng = rng
  st.session_state.human_seat = human_seat
  st.session_state.bots = bots
  st.session_state.log = []
  _log(f"New game: {num_players} players, you are seat {human_seat}.")


def _advance_until_human_turn_or_terminal() -> None:
  """Silently resolves chance nodes and every bot's own decisions (both
  SIMULTANEOUS-round bot seats and their BONUS follow-ups), stopping only
  when the human must decide or the game ends."""
  state = st.session_state.state
  rng = st.session_state.rng
  bots = st.session_state.bots
  human = st.session_state.human_seat

  while not state.is_terminal():
    if state.is_chance_node():
      advance_through_chance_nodes(state, rng)
      continue
    if state.current_player() == pyspiel.PlayerId.SIMULTANEOUS:
      return  # need the human's pick before this round can resolve
    player = state.current_player()
    if player == human:
      return
    action = bots[player].step(state, player)
    _log(f"P{player} ({bots[player].name}): {state.describe_action(player, action)}")
    state.apply_action(action)

  if state.is_terminal():
    _log("Game over.")


def _apply_human_action(action: int) -> None:
  state = st.session_state.state
  human = st.session_state.human_seat
  bots = st.session_state.bots
  _log(f"You: {state.describe_action(human, action)}")

  if state.current_player() == pyspiel.PlayerId.SIMULTANEOUS:
    actions = [None] * state.num_players()
    actions[human] = action
    for p, bot in bots.items():
      actions[p] = bot.step(state, p)
      _log(f"P{p} ({bot.name}): {state.describe_action(p, actions[p])}")
    state.apply_actions(actions)
  else:
    state.apply_action(action)

  _advance_until_human_turn_or_terminal()


def _render_setup() -> None:
  st.title("\U0001F3DB️ 7 Wonders Dice")
  st.caption("Unofficial fan simulation -- play against a bot. "
             "See the repo's RULES.md for rule sources and simplifications.")
  with st.form("setup"):
    num_players = st.slider("Number of players", 2, 7, 3)
    human_seat = st.selectbox("Your seat", list(range(num_players)))
    bot_choice = st.selectbox("Opponent bot", list(_BOT_FACTORIES.keys()), index=1)
    sims = st.slider("Search (MCTS) simulations per decision", 20, 300, 80,
                      help="Only used if 'Search (MCTS)' is selected. Higher "
                           "= stronger but slower (a few seconds/decision).")
    seed = st.number_input("Random seed", value=0, step=1)
    submitted = st.form_submit_button("Start game", type="primary")
  if submitted:
    _start_game(num_players, human_seat, bot_choice, sims, seed)
    _advance_until_human_turn_or_terminal()
    st.rerun()


def _render_forum() -> None:
  state = st.session_state.state
  st.subheader("Forum")
  forum = state.forum_summary()
  cols = st.columns(len(forum))
  for i, (col, (color, cost)) in enumerate(zip(cols, forum)):
    col.metric(f"Die #{i}", DIE_COLOR_NAMES[color], f"{cost} coins")


def _render_player_panel(state, player: int, label: str) -> None:
  ps = state.player_state(player)
  with st.expander(f"{label} -- {ps.board.city} ({ps.board.wonder_name})",
                    expanded=(player == st.session_state.human_seat)):
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Coins", ps.coins)
    c2.metric("Resources", ps.resources)
    c3.metric("Wonder", f"{ps.wonder_crossed}/{WONDER_SPACES}")
    c4.metric("Bonuses", f"{ps.bonus_crossed}/3")
    st.progress(min(1.0, ps.total_end_game_vp() / 60.0),
                text=f"~{ps.total_end_game_vp()} VP so far")
    for kind, total in _PROGRESS_BUILDINGS:
      st.caption(f"{BUILDING_NAMES[kind]}: {ps.building_progress(kind)}/{total}")
    st.caption(f"Western Barracks: {ps.barracks_w_attack}/5 atk, "
               f"{ps.barracks_w_defense}/2 def  |  "
               f"Eastern Barracks: {ps.barracks_e_attack}/5 atk, "
               f"{ps.barracks_e_defense}/2 def")


def _render_game() -> None:
  state = st.session_state.state
  human = st.session_state.human_seat

  top = st.columns([3, 1])
  with top[1]:
    if st.button("New game"):
      for key in ("state", "game", "rng", "human_seat", "bots", "log"):
        st.session_state.pop(key, None)
      st.rerun()

  _render_forum()

  st.subheader("Players")
  cols = st.columns(state.num_players())
  for p in range(state.num_players()):
    with cols[p]:
      _render_player_panel(state, p, "You" if p == human else f"Player {p}")

  st.subheader("Log")
  st.text("\n".join(st.session_state.log[-12:]) or "(nothing yet)")

  if state.is_terminal():
    returns = state.returns()
    winner = max(range(state.num_players()), key=lambda p: returns[p])
    st.header("\U0001F3C1 Game over")
    if winner == human:
      st.success(f"You win! Final scores: {[round(r) for r in returns]}")
    else:
      st.error(f"Player {winner} wins. Final scores: {[round(r) for r in returns]}")
    return

  st.subheader("Your move")
  for action, description in state.legal_action_descriptions(human):
    if st.button(description, key=f"action_{action}_{len(st.session_state.log)}"):
      _apply_human_action(action)
      st.rerun()


def main() -> None:
  if "state" not in st.session_state:
    _render_setup()
  else:
    _render_game()


if __name__ == "__main__":
  main()
