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
  (default 4).

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
| `SearchBot` | flat Monte Carlo / decoupled-UCB1 bandit over its own root actions, backed by short `HeuristicBot`-driven rollouts | ~2-5s per decision by default; a full multi-round game can take several minutes. Lower `num_rollouts`/`horizon_decisions` trade strength for speed. |

They're plain Python classes (`step(state, player) -> action`), not
`pyspiel.Bot` subclasses — see `bots/base.py` for why. Try them:

```bash
python examples/evaluate_bots.py --games 50 --seats random,heuristic,search,heuristic
```

**Why `SIMULTANEOUS` needed a custom search bot**: OpenSpiel's built-in
`mcts.py` assumes one actor per tree node, so it doesn't apply here
directly. `SearchBot` instead runs UCB1 as a bandit over *its own* legal
actions only (no combinatorial blow-up from also branching on what
opponents might do), evaluating each by simulation. Two things that
mattered once actually measured, not just designed on paper (see
`bots/search_bot.py`'s docstring for the full story):

- **Rollout policy quality beats rollout depth.** A first version with
  uniform-random rollouts to a true terminal state *lost most games to
  the plain heuristic bot* — simulating "everyone plays randomly from
  here" is a bad model of an actual opponent. Swapping in a cheap
  `HeuristicBot` variant for rollouts (and cutting them short instead of
  always running to terminal) fixed it.
- **UCB1's exploration constant has to match the reward scale.** The
  textbook `c = sqrt(2)` assumes rewards in [0, 1]; this game's returns
  are raw VP totals (~20-100), so the exploration term needs to be
  normalized or it's negligible next to the mean and the bandit barely
  explores.
- Also worth knowing before you tune it: an early version of
  `HeuristicBot` itself passed ~70% of the time instead of building,
  because its scoring weighted the guaranteed +3 coins from passing over
  building progress. Fixed by adding an explicit progress term — see
  `tests/test_bots.py::test_heuristic_bot_builds_more_than_it_passes`,
  kept as a regression test.

## Project layout

```
src/sevenwonders_dice/
  constants.py     enums: die colors, buildings, actions, effect types
  effects.py       the effect vocabulary + interpreter
  boards.py        the 7 city boards (see RULES.md for data provenance)
  dice.py          die faces + the Forum shake mechanic
  player_state.py  per-player economy/progress tracking
  state.py         the OpenSpiel State (game loop, legality, scoring)
  game.py          the OpenSpiel Game (registration, GameType/GameInfo)
  observer.py      human-readable state observations
  bots/            RandomBot, HeuristicBot, SearchBot (see "Bots" above)
tests/             unit + random-playthrough + bot tests
examples/          random_sim.py, evaluate_bots.py
```

## License

MIT — see [LICENSE](LICENSE). Game design (c) Repos Production; this
repository is an independent, unofficial simulation of its rules.
