# Rules, sources, and confidence

This document says exactly where every rule and every number in this
implementation came from, and how confident we are in it. Nothing here
reproduces the game's artwork; only structural/numeric data needed to run
the simulation was transcribed.

## Primary sources (mechanics — high confidence)

The core rules were read in full from the **official rulebook and player
aid**, downloaded directly from the publisher:

- Rulebook (EN): `cdn.svc.asmodee.net/production-rprod/storage/games/7-wonders-dice/rulebooks/7dice-en01-rules-mkt-1757940319zGYvH.pdf`
- Player Aid / effect glossary (EN): `cdn.svc.asmodee.net/production-rprod/storage/games/7-wonders-dice/player_aids/7dice-en01-player-aid-mkt-1757938830cy5Au.pdf`
- Both linked from `rprod.com/en/games/7-wonders-dice` (Repos Production's
  own site).

These confirm, verbatim: setup, the Forum's 4-quadrant shake mechanic,
the 3 turn actions (build / construct Wonder / pass), the "dice are never
removed, multiple players may pick the same one" rule, how each building
type works (Wonder, Barracks attack/defense formula, Agora, Market,
University's 3-special-die unlocks, Guild Court's neighbor-comparison
gate, the Spy and Gallery of Leaders), the bonus-slot mechanic, the
end-game trigger (3rd bonus + 1 final round), scoring, and the full
generic effect vocabulary (`EffectType` in `constants.py` maps 1:1 to the
Player Aid's icons).

## Board layout sources (numbers — see confidence per board below)

The rulebook doesn't print per-board numbers as text (they're only on the
physical boards). We found and used real photographs instead:

| Photo | Source | What it shows |
|---|---|---|
| `7-Wonders-Dice.webp` | meepleandthemoose.com (credit: Oriol Farre via BGG) | Full top-down Giza board, Forum, dice |
| `setup-4.jpg`, `gameplay-2-4.jpg`, `gameplay-3-4.jpg`, `gameplay-4-3.jpg`, `gameplay-7.jpg` | whatsericplaying.com (Feb 2026 review) | Giza board (2nd angle), a University macro (exact space costs), 2 more distinct boards, Forum macro |
| `7wonders-dice-1.jpg` … `-9.jpg` | nerdly.co.uk (Nov 2025 review) | **Photo #1 shows 6 of the 7 boards side by side**; #4/#6/#7/#8 are sharp macros of Barracks and Agora |

## Confidence by board

| City | Wonder | Confidence | Notes |
|---|---|---|---|
| Giza | The Great Pyramid | **High** | Photographed clearly from 2 independent sources/angles, including the rulebook's own worked scoring example (page 8: total 86 VP) |
| Rhodes | The Colossus of Rhodes | Medium | Board visible in the nerdly.co.uk group photo; Wonder numbers are a reasonable reconstruction |
| Alexandria | The Lighthouse of Alexandria | Medium | Same as above |
| Babylon | The Hanging Gardens of Babylon | Medium | Same as above |
| Olympia | The Statue of Zeus | Low-Medium | Inferred as the 7th roster city; not clearly distinguished in the available photos |
| Ephesus | The Temple of Artemis | Low-Medium | Same as above |
| Halicarnassus | The Mausoleum at Halicarnassus | Low-Medium | Same as above |

**What's shared vs. board-specific**: cross-checking the photos, the
**Warehouse costs, Barracks attack/defense track shape, University's
3-lane structure, and the 3 bonus-slot effects read identically on every
photographed board** — implemented as a standard template
(`boards.py: _standard_*`) used by all 7. The asymmetry between cities is
concentrated in the **Wonder** (unique 3-step track + effects per city)
and, to a lesser extent, in exactly which effect sits on which space —
which is where the Medium/Low-Medium confidence above applies.

**If you own a physical copy**: the numbers to double-check first are the
6 non-Giza Wonders (`boards.py`, search each city's `wonder=(...)` block)
and the Agora/Market/Guild Court exact costs. Everything is plain data —
correcting a number doesn't require touching the engine.

## Deliberate simplifications (for a tractable action space)

- **Agora**: the rulebook's "each space takes either of 2 symbols on the
  blue die" is read as *every* blue-die face working on *any* Agora
  space (a single ordered sequence), not two independently-gated tracks.
- **Market** ("any order"): the engine auto-picks the cheapest still-open
  space rather than exposing which-space-to-fill as a separate decision.
- **Spy (black die) wildcard** and any generic `CROSS_SPACE`/
  `CROSS_SPACE_ONE_OF` effect: when the target is Barracks, always
  advances the *attack* track (defense is only reachable via the Red
  die's actual defense faces); when the target is University, advances
  the first not-yet-complete lane in a fixed order.
- **University-unlock die swap**: the rulebook has the replaced grey die
  "chosen randomly"; the engine picks the first grey slot deterministically
  instead of spending a chance node on a cosmetic detail.
- **Tiebreak**: the real tiebreak ("most unspent coins", then shared
  victory) is folded into the returned utility as a small nudge
  (`VP + coins * 1e-3`) so it influences ranking without ever being able
  to outweigh a real VP difference.

## Effect vocabulary

`EffectType` in `constants.py` is the complete, board-independent set of
effects from the Player Aid: `CROSS_SPACE`, `CROSS_SPACE_ONE_OF`,
`CROSS_UP_TO_TWO`, `GAIN_COINS`, `FREE_ACTION_A_NO_DIE_COST`,
`TAKE_ANOTHER_ACTION`, `COIN_AND_VP_PER_SPACE`, `DIE_COST_MINUS_1`,
`DIE_COST_ZERO`, `COINS_ON_DIE_CHOICE`, `UNLOCK_DIE`, `FLAT_VP`,
`GALLERY_VP_PER_SPACE`. Every bonus-slot and building-space effect in
`boards.py` is built from this vocabulary.

## Not implemented

- BoardGameArena was **not** used as a source for anything — its Terms of
  Service forbid automated/programmatic access, so it was out of scope
  from the start.
- The exclusive "Diceopolis" bonus Wonder (mentioned on the publisher's
  page as a bonus-content variant) is not included.
