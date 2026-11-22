"""
Desktop pet - settings in one place.
Developed by Tunes
"""

APP_NAME = "Blip"
CREDIT = "Developed by Tunes"
VERSION = "1.1.0"

# --- Looks (change these in the Settings window, they get saved) ---
CHARACTER = "Blob"        # Blob, Cat, Bunny, Ghost
THEME = "Nexus"           # Nexus, Ember, Mint, Frost, Sakura
HAT = "None"              # None, Santa hat, Crown, Headphones, Bow
EYES_FOLLOW_CURSOR = True

# Size of the see-through window that holds the pet (pixels).
PET_SIZE = 120

# Walking speed in pixels per second.
WALK_SPEED = 55

# Frames per second for each state. Lower = less CPU.
FPS_WALK = 24
FPS_IDLE = 8
FPS_SLEEP = 2
FPS_PHYSICS = 60          # only while being dragged / flying through the air
FPS_HIDDEN = 1            # while hidden behind a fullscreen game
FPS_DANCE = 20            # while dancing to music

# How long the pet stands still before choosing something new (seconds).
IDLE_TIME = (2.0, 6.0)

# After idling, chance it takes a short nap instead of walking (0.0 - 1.0).
NAP_CHANCE = 0.025      # was 0.12 (Blip napped far too often)
NAP_TIME = (10.0, 25.0)
NAP_MIN_AWAKE = 20 * 60  # only nap after being awake this long (seconds)

# Fall asleep when you haven't touched mouse/keyboard for this long (seconds).
USER_IDLE_SLEEP_SECONDS = 600   # 10 min

# Time between blinks (seconds).
BLINK_EVERY = (2.5, 6.0)

# --- Physics (stage 2) ---
GRAVITY = 2400            # pixels per second squared (pull downwards)
BOUNCE = 0.55             # 0 = no bounce, 1 = bounces forever
GROUND_FRICTION = 0.75    # sideways speed kept on each bounce
AIR_DRAG = 0.4            # how fast sideways speed fades in the air (per second)
MAX_THROW_SPEED = 3000    # cap on how hard you can throw it
JUMP_SPEED = 950          # upward speed of a double-click jump

# --- Games / fullscreen ---
# Hide + pause the pet while a fullscreen app is on the SAME screen as the pet.
HIDE_IN_FULLSCREEN = True

# --- Pokes ---
POKES_TO_GET_GRUMPY = 5   # this many clicks within 2 seconds = grumpy
GRUMPY_SECONDS = 4

# --- Reactions (stage 4) ---
# Sit on top of your open windows (and fall off when you move them).
SIT_ON_WINDOWS = True
CLIMB_CHANCE = 0.18       # after idling, chance it jumps up onto a window
HOP_DOWN_CHANCE = 0.25    # while on a window, chance it hops back down

# Sweat when your PC is working hard.
SWEAT_WHEN_BUSY = True
CPU_SWEAT_AT = 90         # % CPU (averaged over a few seconds)
RAM_SWEAT_AT = 92         # % RAM in use

# Get sleepy late at night: droopy eyes, yawns, more naps.
SLEEPY_AT_NIGHT = True
NIGHT_START_HOUR = 23     # 11 pm
NIGHT_END_HOUR = 6        # 6 am
YAWN_EVERY = (25.0, 70.0) # seconds between yawns at night

# --- Music (stage 4) ---
# Headphones on + dance to the beat while a music app plays (Spotify, VLC, ...),
# and a "now playing" bubble when the song changes.
LISTEN_TO_MUSIC = True

# --- PC helper ---
# When your PC is struggling (same check as sweating), Blip offers to help: poke it
# to see what's using RAM/CPU. Never closes anything unless you tick it.
PC_HELPER = True
PC_HELPER_COOLDOWN = 30 * 60   # seconds between offers
GPU_HOT_AT = 83               # Â°C: ask "want me to help cool it down?"

# --- Chat buddy ---
ASK_QUESTIONS = True     # Blip asks you a question now and then (max 3 a day, 9:00-23:00)
GAME_BUDDY = True        # after a game: "How did the match go?" + win/loss stats

# --- Mini radio ---
RADIO_STATION = ""       # last station you played
RADIO_VOLUME = 60        # 0-100

# --- Random antics (trip, football, NFL throw, sneeze...) ---
ANTICS = "Normal"        # Off, Rare (8-15 min), Normal (3-8 min), Lots (1-3 min)

# --- Dancing (separate from "show what's playing") ---
DANCE = True             # dance moves + headphones while music plays
FPS_PAUSED = 0.2         # screen locked / display off: one quiet check every 5 s


def music_active():
    """Any music feature on? If not, Blip doesn't even check for sound."""
    return DANCE or LISTEN_TO_MUSIC

# --- Extras ---
DND_UNTIL = 0.0          # Do Not Disturb until this time (0 = off)
SEASONAL = True          # seasonal outfits (Santa hat in December, pumpkin at Halloween...)
HAPPY = 70.0             # happiness 0-100 (see extras.py)
HAPPY_AT = 0.0           # when HAPPY was last updated
SOUNDS = "Off"           # Off, Low, Normal

# --- Levels & prestige (see progress.py) ---
# XP needed for level L -> L+1 = XP_BASE + XP_GROWTH * L.  Level 1 -> 55 = about 34,800 XP,
# which is roughly 5 weeks at ~1,000 XP a day of normal use.
XP_BASE = 300
XP_GROWTH = 12.5
# source: (XP each time, max times per day)
XP_SOURCES = {
    "daily": (150, 1),       # first time Blip sees you today (+ streak bonus)
    "active": (40, 10),      # every 10 active minutes together (max 100 min a day)
    "feed": (25, 5),
    "pet": (15, 5),
    "poke": (2, 10),
    "chat": (10, 10),
    "task": (20, 5),         # reminders done, to-do items ticked off
    "game": (40, 5),         # game-buddy reports
    "focus": (80, 4),        # finished focus sessions
    "trick": (10, 5),        # antics you start from the Play menu
    "seek": (60, 3),         # winning hide and seek
    "music": (50, 6),        # every 15 min of music/radio with Blip
    "launch": (15, 5),       # opening an app through Blip
    "catch": (30, 5),        # catching Blip in mid-air
    "throw": (20, 5),        # throwing Blip far (bigger throws give more)
    "jump": (3, 10),         # double-click jumps
    "happy": (100, 1),       # keeping Blip's happiness above 70
    "first_chat": (50, 1),   # first chat of the day
}
XP_STREAK_BONUS = 20         # extra XP per day of streak...
XP_STREAK_MAX = 200          # ...up to this much

# --- Updates (see updater.py) ---
UPDATE_REPO = "TunesDev/Blip"   # GitHub repo that hosts Blip's releases
AUTO_UPDATE = True              # check at start + every 6 h, install updates automatically
UPDATE_LAST = ""                # time of the last check
LAST_VERSION = "1.1.0"               # to say "Updated to vX!" after an update
FIRST_RUN_DONE = False          # the welcome window has been shown
