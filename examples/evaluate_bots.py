"""Tournament runner: seats a mix of bots, plays N games, reports results.

Usage:
    python examples/evaluate_bots.py --games 100 --seats random,heuristic,search,heuristic
    python examples/evaluate_bots.py --games 30 --seats heuristic,search --rollouts 128
"""

import argparse
import random
import statistics
import time

import pyspiel
import sevenwonders_dice  # noqa: F401  (registers the game)
from sevenwonders_dice.bots import HeuristicBot, RandomBot, SearchBot, play_full_game

BOT_FACTORIES = {
    "random": lambda rng, rollouts: RandomBot(rng),
    "heuristic": lambda rng, rollouts: HeuristicBot(),
    "search": lambda rng, rollouts: SearchBot(num_rollouts=rollouts, rng=rng),
}


def build_bots(seat_names, rng, rollouts):
  return [BOT_FACTORIES[name](rng, rollouts) for name in seat_names]


def main():
  parser = argparse.ArgumentParser()
  parser.add_argument("--games", type=int, default=50)
  parser.add_argument("--seats", type=str, default="random,heuristic,search,heuristic",
                       help="comma-separated bot names (random|heuristic|search), "
                            "one per seat -- also sets the number of players")
  parser.add_argument("--rollouts", type=int, default=64,
                       help="SearchBot rollout budget per decision")
  parser.add_argument("--seed", type=int, default=0)
  args = parser.parse_args()

  seat_names = args.seats.split(",")
  num_players = len(seat_names)
  rng = random.Random(args.seed)
  game = pyspiel.load_game("python_seven_wonders_dice", {"players": num_players})

  wins = [0] * num_players
  score_totals = [0.0] * num_players
  start = time.time()

  for game_idx in range(args.games):
    bots = build_bots(seat_names, rng, args.rollouts)
    state = play_full_game(game, bots, rng)
    returns = state.returns()
    for p, r in enumerate(returns):
      score_totals[p] += r
    winner = max(range(num_players), key=lambda p: returns[p])
    wins[winner] += 1
    if (game_idx + 1) % max(1, args.games // 10) == 0:
      print(f"...{game_idx + 1}/{args.games} games")

  elapsed = time.time() - start
  print(f"\n{args.games} games, {elapsed:.1f}s total "
        f"({elapsed / args.games:.2f}s/game)\n")
  print(f"{'Seat':<6} {'Bot':<10} {'Win %':>8} {'Avg score':>10}")
  for p, name in enumerate(seat_names):
    win_pct = 100.0 * wins[p] / args.games
    avg_score = score_totals[p] / args.games
    print(f"P{p:<5} {name:<10} {win_pct:>7.1f}% {avg_score:>10.1f}")


if __name__ == "__main__":
  main()
