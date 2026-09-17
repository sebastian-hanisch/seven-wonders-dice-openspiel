"""Play 7 Wonders Dice against a bot in the browser.

    streamlit run app.py

Lets a human take one seat while RandomBot/HeuristicBot/SearchBot play the
rest. Everything else in this repo is pyspiel-facing; this file is the one
place that's Streamlit-specific -- it just drives the same public State
API (legal_actions / apply_action(s) / describe_action / player_state)
that examples/evaluate_bots.py drives, one rerun at a time.
"""

import random

import plotly.graph_objects as go
import pyspiel
import streamlit as st

import sevenwonders_dice  # noqa: F401  (registers the games)
from app_graphics import render_board_svg, render_forum_svg
from sevenwonders_dice.bots import HeuristicBot, RandomBot, SearchBot
from sevenwonders_dice.bots.base import advance_through_chance_nodes
from sevenwonders_dice.player_state import WONDER_SPACES

st.set_page_config(page_title="7 Wonders Dice", page_icon="\U0001F3DB️", layout="wide")

_PLAYER_LINE_COLORS = ["#3b6fa8", "#c0392b", "#4a8f4a", "#d4a72c",
                        "#7d5ba6", "#e07b39", "#2ba3a3"]

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
  st.session_state.vp_history = []
  _log(f"New game: {num_players} players, you are seat {human_seat}.")


def _record_vp_snapshot() -> None:
  state = st.session_state.state
  snapshot = {p: state.player_state(p).total_end_game_vp()
              for p in range(state.num_players())
              if state.player_state(p) is not None}
  st.session_state.vp_history.append(snapshot)


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
  _record_vp_snapshot()


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
    _record_vp_snapshot()
    st.rerun()


def _render_forum() -> None:
  state = st.session_state.state
  st.subheader("Forum")
  st.markdown(render_forum_svg(state.forum_summary()), unsafe_allow_html=True)


def _render_player_panel(state, player: int, label: str) -> None:
  ps = state.player_state(player)
  with st.expander(f"{label} -- {ps.board.city} ({ps.board.wonder_name})",
                    expanded=(player == st.session_state.human_seat)):
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Coins", ps.coins)
    c2.metric("Res.", ps.resources)
    c3.metric("Wonder", f"{ps.wonder_crossed}/{WONDER_SPACES}")
    c4.metric("Bonus", f"{ps.bonus_crossed}/3")
    st.progress(min(1.0, ps.total_end_game_vp() / 60.0),
                text=f"~{ps.total_end_game_vp()} VP so far")
    st.markdown(render_board_svg(ps), unsafe_allow_html=True)


def _render_vp_chart() -> None:
  history = st.session_state.vp_history
  if len(history) < 2:
    return
  state = st.session_state.state
  human = st.session_state.human_seat
  fig = go.Figure()
  for p in range(state.num_players()):
    ys = [snap.get(p) for snap in history]
    name = "You" if p == human else f"Player {p}"
    color = _PLAYER_LINE_COLORS[p % len(_PLAYER_LINE_COLORS)]
    fig.add_trace(go.Scatter(
        x=list(range(len(ys))), y=ys, mode="lines+markers", name=name,
        line=dict(color=color, width=3 if p == human else 2)))
  fig.update_layout(
      height=280, margin=dict(l=10, r=10, t=30, b=10),
      xaxis_title="round", yaxis_title="VP so far",
      legend=dict(orientation="h", yanchor="bottom", y=1.02),
      template="plotly_dark")
  st.plotly_chart(fig, use_container_width=True)


def _render_game() -> None:
  state = st.session_state.state
  human = st.session_state.human_seat

  top = st.columns([3, 1])
  with top[1]:
    if st.button("New game"):
      for key in ("state", "game", "rng", "human_seat", "bots", "log", "vp_history"):
        st.session_state.pop(key, None)
      st.rerun()

  _render_forum()

  st.subheader("Players")
  cols = st.columns(state.num_players())
  for p in range(state.num_players()):
    with cols[p]:
      _render_player_panel(state, p, "You" if p == human else f"Player {p}")

  _render_vp_chart()

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
