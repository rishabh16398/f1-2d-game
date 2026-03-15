<<<<<<< HEAD
# 🏎️ F1 2D — Top-Down Racing Game

A fully featured 2D top-down F1-style racing game built with Python and Pygame. Race on 10 iconic circuits, manage your tyre strategy, battle AI drivers, and compete with a PS5 DualSense controller or keyboard.

---

## 📸 Features

### 🏁 Racing
- **10 unique circuits** — Albert Park, Monaco, Silverstone, Monza, Suzuka, Spa-Francorchamps, COTA, Interlagos, Bahrain, and Singapore
- **Choose your lap count** — 3, 5, 10, 15, or 20 laps
- **Realistic start sequence** — 5 red lights with audio pips, random lights-out delay, then GO
- **Race finish celebration** — confetti, winner announcement banner, podium results screen

### 🏎️ Car & Physics
- **Analogue driving** — throttle and brake scale progressively (especially with controller)
- **Speed-sensitive steering** — tighter at low speed, gentler at high speed for precision
- **Off-track penalty** — reduced grip and max speed on grass
- **Collision physics** — cars push apart with velocity exchange on impact

### 🛞 Tyre Strategy
- **3 compounds** with real differences:
  - **Soft 🔴** — fastest raw pace, wears 8× quicker than Hard
  - **Medium 🟡** — balanced pace and durability
  - **Hard ⚪** — slowest but lasts the entire race
- **Grip degrades** as tyre health drops — old tyres genuinely feel worse
- **Tyre warning** flashes when health drops below 25%
- **Pit stops** — drive into pit box, select new compound, 3-second stop timer

### 🤖 AI Drivers
- **3 named opponents** — Hamilton, Verstappen, Leclerc
- **3 personality types** — Aggressive, Balanced, Cautious
- **Mistake system** — AI makes genuine driving errors, width-varying errors (5–18°, lasting 25–80 frames)
- **Collision response** — AI cars get stunned when hit and coast freely instead of snapping back to racing line
- **Pit strategy** — AI decides when to pit based on tyre wear threshold
- **DRS** — AI opens DRS on straights automatically

### 📡 DRS
- **Manual mode** — press Q (keyboard) or □ (PS5) when in the DRS zone
- **Auto mode** — DRS opens automatically in the detection zone
- **Visual feedback** — rear wing on car sprite changes when DRS is open
- **HUD indicator** — dim when unavailable, amber when available, green when open

### 🎮 PS5 DualSense Controller Support
Full analogue controller support with verified button mapping:

| Button | Action |
|--------|--------|
| **R2** | Throttle (analogue) |
| **L2** | Brake (analogue) |
| **Left Stick** | Steering (analogue with expo curve) |
| **□ Square** | DRS toggle |
| **△ Triangle** | Pit stop → Soft tyres |
| **○ Circle** | Pit stop → Medium tyres |
| **✕ Cross** | Pit stop → Hard tyres / Confirm in menu |
| **D-pad ↑↓** | Navigate menu |
| **D-pad ◄►** | Change selection |
| **Options** | Quit / Restart |

### 🔊 Sound
- **Real engine sound** — loads `engine.mp3` from `assets/sounds/`, volume scales with speed and throttle
- **Procedural fallback** — synthesised engine tone if MP3 is missing (requires numpy)
- **Tyre squeal** — triggered when cornering hard at speed
- **Collision thud** — on significant impact
- **Pit stop pneumatic gun** — on entering pit box
- **Lap complete chime** — C-E-G-C arpeggio on each lap
- **Start light pips** — beep for each red light, GO burst on lights out

### 🖥️ HUD
- **Top bar** — Lap counter, current/best/last lap times, speed, gear, DRS indicator, tyre compound, position
- **Standings panel** — live P1–P4 with car colour, driver name, tyre dot and wear %
- **Bottom bar** — throttle bar, tyre wear bar, controller/keyboard indicator
- **Track name** — shown in HUD top bar
- **Tyre warning** — flashing red banner when tyres are critical
- **DRS zone banner** — centre-screen prompt when DRS is available

---

## 🗂️ Project Structure

```
f1-2d-game/
├── src/
│   ├── main.py                  # Game loop, HUD, race logic, strategy screen
│   ├── assets/
│   │   └── sounds/
│   │       └── engine.mp3       # Optional — real F1 engine sound
│   └── entities/
│       ├── __init__.py
│       ├── car.py               # Player car physics, DRS, tyre system
│       ├── ai_car.py            # AI with personality, mistakes, collision stun
│       ├── track.py             # 10 tracks, pit lane, DRS zone, S/F line
│       ├── controller.py        # PS5 DualSense support, verified button map
│       └── sound_engine.py      # MP3 loader + procedural sound fallback
├── README.md
└── requirements.txt
```

---

## ⚙️ Local Setup

### Prerequisites
- **Python 3.9+**
- **macOS, Windows, or Linux**
- A terminal / command prompt

### Step 1 — Clone or download the project

```bash
# If using git
git clone https://github.com/yourname/f1-2d-game.git
cd f1-2d-game

# Or just unzip the project folder and cd into it
cd f1-2d-game
```

### Step 2 — Create a virtual environment

```bash
python3 -m venv venv
```

Activate it:

```bash
# macOS / Linux
source venv/bin/activate

# Windows
venv\Scripts\activate
```

You should see `(venv)` at the start of your terminal prompt.

### Step 3 — Install dependencies

```bash
pip install pygame numpy
```

> **Note:** `numpy` is only required if you don't have an `engine.mp3` file (used for the procedural sound fallback). If you have the MP3, `numpy` is optional but harmless to install.

### Step 4 — (Optional) Add engine sound

If you have an F1 engine sound recording:

1. Create the folder `src/assets/sounds/`
2. Name your file `engine.mp3`
3. Place it at `src/assets/sounds/engine.mp3`

Good free sources for F1 engine sounds:
- [freesound.org](https://freesound.org) — search "F1 engine" or "formula car engine loop"
- [zapsplat.com](https://zapsplat.com) — search "racing car engine"
- [pixabay.com/sound-effects](https://pixabay.com/sound-effects/) — search "race car engine"

If the file is missing the game will use a synthesised fallback automatically.

### Step 5 — Run the game

```bash
python src/main.py
```

---

## 🎮 Controls

### Keyboard

| Key | Action |
|-----|--------|
| **W / ↑** | Throttle |
| **S / ↓** | Brake |
| **A / ←** | Steer left |
| **D / →** | Steer right |
| **Q** | DRS (hold to open, manual mode) |
| **1** | Pit stop → Soft tyres |
| **2** | Pit stop → Medium tyres |
| **3** | Pit stop → Hard tyres |
| **R** | Restart race |
| **ESC** | Quit |

### Strategy Screen (Keyboard)

| Key | Action |
|-----|--------|
| **↑ / ↓** | Navigate rows |
| **← / →** | Change value (laps / tyre) |
| **1 / 2 / 3** | Select Soft / Medium / Hard tyre |
| **D** | Toggle DRS Auto/Manual |
| **ENTER** | Start race |
| **ESC** | Quit |

### PS5 DualSense Controller

Connect via **USB-C** or **Bluetooth** before launching. On macOS:
1. Hold **PS + Create** buttons together for ~3 seconds to enter pairing mode
2. Open **System Settings → Bluetooth**
3. Select **DualSense Wireless Controller** and click **Connect**

The game auto-detects the controller on startup. The HUD shows a green **PS5** badge when connected.

---

## 🏟️ Circuits

| # | Track | Country | Character |
|---|-------|---------|-----------|
| 0 | Albert Park | 🇦🇺 Australia | Flowing loop, chicane on straight |
| 1 | Monaco | 🇲🇨 Monaco | Tightest circuit, 8 slow corners |
| 2 | Silverstone | 🇬🇧 Great Britain | Wide sweeping Maggotts S-curves |
| 3 | Monza | 🇮🇹 Italy | Huge straights, minimal cornering |
| 4 | Suzuka | 🇯🇵 Japan | S-curves left side, Spoon + 130R |
| 5 | Spa-Francorchamps | 🇧🇪 Belgium | Longest track, Eau Rouge section |
| 6 | COTA | 🇺🇸 USA | Big blind T1, esses complex |
| 7 | Interlagos | 🇧🇷 Brazil | Senna S chicane, Ferradura horseshoe |
| 8 | Bahrain | 🇧🇭 Bahrain | Desert sand, two chicane sections |
| 9 | Singapore | 🇸🇬 Singapore | Night circuit (dark grass), tightest streets |

---

## 🔧 Troubleshooting

**Game won't start**
```bash
# Make sure you're in the right directory and venv is active
source venv/bin/activate
python src/main.py
```

**`ModuleNotFoundError: No module named 'pygame'`**
```bash
pip install pygame
```

**`ModuleNotFoundError: No module named 'numpy'`**
```bash
pip install numpy
```

**Controller not detected**
- Make sure the controller is connected **before** launching the game
- Try USB-C cable instead of Bluetooth if Bluetooth isn't working
- Run the test script to verify detection:
```bash
python src/test_controller.py
```

**No sound / sound errors**
- The game will run silently if audio init fails — this is expected on some headless setups
- Make sure your system audio is not muted
- If using the MP3 engine sound, confirm the file is at `src/assets/sounds/engine.mp3`

**Track looks wrong / cars driving off screen**
- The game is designed for **1512×982** resolution (MacBook Pro Retina)
- It scales to other resolutions but very small screens may look cramped

---

## 📦 Requirements

```
pygame>=2.0.0
numpy>=1.20.0
```

Save this as `requirements.txt` in the project root and install with:

```bash
pip install -r requirements.txt
```

---

## 🛠️ Built With

- **Python 3.11**
- **Pygame 2.6** — rendering, input, audio
- **NumPy** — procedural sound synthesis (fallback only)

---

## 📄 License

This project is for personal and educational use. F1 track names and driver names are used for reference only and are not affiliated with Formula 1, FOM, or any official F1 entity.
