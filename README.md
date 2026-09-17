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

Requires Python 3.11+ (OpenSpiel ships prebuilt wheels for 3.11–3.13,
including native Windows).

```bash
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
tests/             unit + random-playthrough tests
examples/          random_sim.py
```

## License

MIT — see [LICENSE](LICENSE). Game design (c) Repos Production; this
repository is an independent, unofficial simulation of its rules.
