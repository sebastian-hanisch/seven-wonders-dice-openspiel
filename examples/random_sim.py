"""Runs random self-play games and prints score statistics.

Usage:
    python examples/random_sim.py --games 200 --players 4
"""

import argparse
import random
import statistics

import pyspiel
import sevenwonders_dice  # noqa: F401  (registers the game)


def play_one(game, rng):
  state = game.new_initial_state()
  while not state.is_terminal():
    if state.is_chance_node():
      outcomes, probs = zip(*state.chance_outcomes())
      state.apply_action(rng.choices(outcomes, weights=probs, k=1)[0])
    elif state.current_player() == pyspiel.PlayerId.SIMULTANEOUS:
      actions = [rng.choice(state.legal_actions(p))
                 for p in range(game.num_players())]
      state.apply_actions(actions)
    else:
      player = state.current_player()
      state.apply_action(rng.choice(state.legal_actions(player)))
  return state


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument("--games", type=int, default=200)
  parser.add_argument("--players", type=int, default=4)
  parser.add_argument("--seed", type=int, default=0)
  args = parser.parse_args()

  rng = random.Random(args.seed)
  game = pyspiel.load_game("python_seven_wonders_dice", {"players": args.players})

  all_scores = []
  for i in range(args.games):
    state = play_one(game, rng)
    all_scores.extend(state.returns())
    if (i + 1) % max(1, args.games // 10) == 0:
      print(f"...{i + 1}/{args.games} games played")

  print(f"\n{args.games} games, {args.players} players each, "
        f"{len(all_scores)} final scores:")
  print(f"  mean={statistics.mean(all_scores):.1f} "
        f"stdev={statistics.stdev(all_scores):.1f} "
        f"min={min(all_scores):.1f} max={max(all_scores):.1f}")


if __name__ == "__main__":
  main()
