# 7 Wonders Dice — OpenSpiel

An unofficial [OpenSpiel](https://github.com/google-deepmind/open_spiel)
implementation of **7 Wonders Dice** (Antoine Bauza / Repos Production,
2025), a "shake & write" spin-off of the 7 Wonders board game, for AI
research, bot development, and simulation.

This is a fan project, not affiliated with or endorsed by Repos Production
or Asmodee. It implements the game's rules and structure; it does not
include or redistribute any of the game's artwork, and reproduces no
rulebook text beyond short factual mechanic descriptions. See
[RULES.md](RULES.md) for exactly which numbers come from the official
rulebook, which were transcribed from photos of physical boards, and which
are best-effort reconstructions.

## Install

Requires Python 3.11+. OpenSpiel ships prebuilt wheels for 3.11–3.14 on
Windows, Linux and macOS, so a plain `pip install` works natively —
verified here in a fresh venv on the latest Python (3.14) with current
dependency versions, no build toolchain needed.

```bash
python -m venv .venv
.venv\Scripts\activate   # or: source .venv/bin/activate on Linux/macOS
pip install -e ".[dev]"
```

## Quickstart

```python
import pyspiel
import sevenwonders_dice  # registers "python_seven_wonders_dice"

game = pyspiel.load_game("python_seven_wonders_dice", {"players": 4})
state = game.new_initial_state()
print(game, state)
```

Run a batch of random self-play games and print score statistics:

```bash
python examples/random_sim.py --games 200 --players 4
```

Run the test suite:

```bash
pytest -q
```

## How the game maps to OpenSpiel

- **Dynamics**: `SIMULTANEOUS` — every round, all players privately choose
  Construct a Building / Construct Wonder / Pass at once, matching the
  physical game (dice are never removed from the Forum, so there's no
  contested-pick conflict to resolve).
- **Chance nodes**: dealing each player a random city board at the start,
  and "shaking" the Forum each round (random face + quadrant per die).
- **Information**: perfect information + stochastic — like backgammon,
  everything is public except future die outcomes.
- Player counts 2–7 are supported via the `players` game parameter
  (default 4). A second registered game, `python_seven_wonders_dice_solo`,
  is the same engine as a `SEQUENTIAL`, 1-player variant — see "Bots"
  below for why.

See [`src/sevenwonders_dice/state.py`](src/sevenwonders_dice/state.py) for
the full state machine and a list of the (documented) simplifications made
to keep the action space tractable — e.g. a few minor sub-choices (which
open Market space to fill, which building a wildcard Spy die advances) are
auto-resolved with a fixed deterministic rule rather than exposed as
separate decisions.

## Bots

Three bots live in `src/sevenwonders_dice/bots/`, in increasing strength
(and cost) order:

| Bot | Idea | Cost |
|---|---|---|
| `RandomBot` | uniform random legal action | trivial |
| `HeuristicBot` | greedy: clone + apply each legal action, score the result (VP + coins + resources + building progress), greedily resolve short BONUS-effect chains the same way | cheap |
| `SearchBot` | OpenSpiel's own `mcts.MCTSBot`, run on a per-decision snapshot (see below) | ~2-5s per decision at the default 100 simulations; tune `max_simulations` for strength vs. speed |

They're plain Python classes (`step(state, player) -> action`), not
`pyspiel.Bot` subclasses (`SearchBot` wraps a real `pyspiel.Bot` internally,
but its own interface matches the other two) — see `bots/base.py` for why.
Try them:

```bash
python examples/evaluate_bots.py --games 50 --seats random,heuristic,search,heuristic
```

**Using OpenSpiel's own MCTS on a `SIMULTANEOUS` game.** `mcts.MCTSBot`
hard-requires `GameType.dynamics == SEQUENTIAL` and refuses this game
outright — but the game barely needs `SIMULTANEOUS` in the first place: a
player's own progress, coins and VP this round never depend on what anyone
else simultaneously picks (dice are never removed from the Forum), only on
the shake and their own choice. The only thing opponents contribute to a
decision is their *current standing*, for Guild Court/Barracks comparisons.
That makes one player's decision problem close to a solitaire MDP, not a
genuinely multi-agent one — so `game.py` registers a second, SEQUENTIAL,
1-player variant of the *same* game (`python_seven_wonders_dice_solo`,
same `State` class — a 1-player `SIMULTANEOUS` round already collapses to
a plain sequential decision), `SevenWondersDiceState.make_solo_snapshot()`
freezes a live position into it, and OpenSpiel's real `MCTSBot` solves
that snapshot directly. The one thing this can't see is opponents' future
moves (e.g. a race to end the game by hitting 3 bonuses first) — a small
approximation given how little the rulebook actually couples players
within a round.

A hand-rolled decoupled-UCB1 bandit (the "naive" way to search a
`SIMULTANEOUS` game — treat it as a 1-ply bandit over your own actions,
backed by rollouts) was the first version of `SearchBot`. It worked, after
fixing two real bugs found by actually measuring it — a uniform-random
rollout policy lost most games to plain `HeuristicBot` (a bad model of a
competent opponent), and UCB1's exploration constant needed rescaling from
the textbook `[0, 1]` assumption to this game's VP-sized returns — but it
was still a from-scratch reimplementation of something the framework
already does well. See `bots/search_bot.py`'s docstring for the full
story of both versions, kept there since the failure modes are the useful
part.

Also worth knowing: an early version of `HeuristicBot` passed ~70% of the
time instead of building, because its scoring weighted the guaranteed +3
coins from passing over building progress. Fixed by adding an explicit
progress term — see
`tests/test_bots.py::test_heuristic_bot_builds_more_than_it_passes`, kept
as a regression test.

## Project layout

```
src/sevenwonders_dice/
  constants.py     enums: die colors, buildings, actions, effect types
  effects.py       the effect vocabulary + interpreter
  boards.py        the 7 city boards (see RULES.md for data provenance)
  dice.py          die faces + the Forum shake mechanic
  player_state.py  per-player economy/progress tracking
  state.py         the OpenSpiel State (game loop, legality, scoring,
                   plus make_solo_snapshot() -- see "Bots" above)
  game.py          both registered Games: the SIMULTANEOUS multiplayer
                   game and its SEQUENTIAL 1-player "solo" variant
  observer.py      human-readable state observations
  bots/            RandomBot, HeuristicBot, SearchBot (see "Bots" above)
tests/             unit + random-playthrough + bot tests
examples/          random_sim.py, evaluate_bots.py
```

## License

MIT — see [LICENSE](LICENSE). Game design (c) Repos Production; this
repository is an independent, unofficial simulation of its rules.
