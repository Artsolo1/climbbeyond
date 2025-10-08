<<<<<<< HEAD
<<<<<<< HEAD
# Climb Beyond

A tiny  platformer written in **Python + pygame**.

## Controls

- **Move**: A/D OR arrows left/right
- **Jump**: J OR C (fixed height, with coyote time)
- **Dash**: K OR X (4 directions using W/A/S/D; 1 dash until touching ground)
- **Grab/Hang**: L OR Z (manual hold; drains stamina; climb with W/S; instant refill on ground)
- **Interact (NPC)**: E
- **Restart Level**: Esc


## Run from Terminal

- **cd** into the folder with game file
```bash
python -m venv .venv
# OR
py -3 -m venv .venv
# Windows:
.venv\Scripts\python -m pip install -U pip && .venv\Scripts\pip install -r requirements.txt
.venv\Scripts\python -m game
# macOS/Linux:
source .venv/bin/activate
python -m pip install -U pip && pip install -r requirements.txt
python -m game
```

## Project structure

celestish_homework/
├─ game/
│  ├─ __init__.py
│  ├─ __main__.py      # enables: python -m game
│  └─ main.py          # all game logic + menus
├─ levels/             # ASCII tile maps (# walls, ^ spikes, S spawn, E exit, N NPC)
├─ requirements.txt
└─ README.md


## Level format

- `#` wall (solid). Place them on **left/right edges** to create visible boundaries.
- `^` spike (hazard).
- `S` spawn (one per level).
- `E` exit.
- `N` NPC (optional; press **E** near it to read tips).

## Notes

- Game length target: **5–10 minutes** across 3 levels provided.
- After each level you see **Time** and **Deaths** and your **Best** gets saved to `stats.json`.
- Parallax background included. Sprites are placeholders (rectangles) — swap in pixel art later.
