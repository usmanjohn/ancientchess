# Chess Empires — CLAUDE.md

**Read this file before writing any code.**

## Game Concept

Chess Empires is an 8x8 turn-based strategy game blending classic chess with Ancient Empires (Nokia mobile game). Chess pieces are units with HP, attack, defense, XP, and levels. The board has terrain tiles affecting movement cost and defense bonuses. Buildings (castles, houses) generate gold and heal occupying units. Two players share one browser in hotseat mode. Victory: kill the enemy King.

## Tech Stack

- Backend: Django 6.x, Python 3.12
- Frontend: Phaser.js 3 (CDN), single HTML template
- Database: SQLite (default Django)
- No DRF, no WebSockets, no Celery, no Redis until Phase 3 at earliest
- Django views return JSON where needed; all game logic lives server-side

## Folder Structure

```
ancientchess/          ← Django project root
  ancientchess/        ← project config package
    settings.py
    urls.py
  game/                ← main app
    models.py          ← GameSession, Board, Tile, Piece, Building
    views.py           ← all game logic and JSON endpoints
    urls.py            ← app URL patterns
    templates/
      game/
        game.html      ← Phaser.js frontend (single page)
  manage.py
  CLAUDE.md
```

## Phase Roadmap

- **Phase 1 (complete):** Models, views, Phaser board, move + attack + end_turn logic, hotseat play
- **Phase 2:** Unit purchasing from castles, gold economy, building capture, heal-in-building logic
- **Phase 3:** XP and leveling system, terrain visual improvements, sound effects
- **Phase 4:** Campaign/scenario maps, map editor, save/load game

## Piece Stats

| Piece  | HP | ATK | DEF | Move Points | Notes                          |
|--------|----|-----|-----|-------------|--------------------------------|
| Pawn   | 20 | 8   | 3   | 2           | Can capture buildings          |
| Knight | 25 | 12  | 4   | 3           | Ignores terrain cost (jumps)   |
| Bishop | 22 | 10  | 3   | 4           | Diagonal movement only         |
| Rook   | 30 | 14  | 5   | 4           | Straight lines only            |
| Queen  | 35 | 16  | 6   | 5           | Any direction                  |
| King   | 40 | 10  | 8   | 2           | Can capture buildings, death = game over |

## Terrain Costs and Defense Bonuses

| Terrain  | Move Cost | DEF Bonus |
|----------|-----------|-----------|
| Plains   | 1         | 0         |
| Road     | 0.5       | 0         |
| Forest   | 2         | +3        |
| Mountain | 3         | +5        |
| Water    | 4         | -2        |

Most pieces cannot enter water. Knights jump over all terrain (cost always 1 per move).

## Starting Board Layout

- Player 1 pieces: rows 0–1 (standard chess positions, mirrored)
- Player 2 pieces: rows 6–7
- Castles: (0,3) owned by Player 1, (7,4) owned by Player 2
- Houses (neutral): (3,2), (3,5), (4,2), (4,5)
- Terrain: mostly plains; scattered forest/mountain in middle rows

## Combat Formula

```
damage = max(1, attacker.attack - (defender.defense + terrain_def_bonus))
```

After combat, defender HP reduced. If HP <= 0, piece is deleted. King death ends the game.

## Key Design Decisions

- All game state is stored in the database (GameSession, Tile, Piece, Building models)
- Phaser.js is purely a renderer + input handler; it never owns authoritative state
- After every action (move, attack, end_turn), Phaser re-fetches `/game/<id>/state/`
- Movement validation uses BFS with terrain cost accumulation; Knights skip terrain costs
- `has_moved` and `has_attacked` flags are per-piece, reset on `end_turn`
- Buildings store owner (1, 2, or null); income and healing handled in `end_turn`

## Rules for Future Claude Sessions

1. Always read this file before writing any code
2. Never change model field names or structures without updating this file
3. Keep all game logic in Django views/models — Phaser only renders and POSTs actions
4. Do not introduce DRF, Celery, or Redis until Phase 3
5. SQLite is fine until Phase 3
6. Do not add features beyond the current phase without user approval
7. CSRF tokens must be included in all POST requests from Phaser
