#!/usr/bin/env python3
"""MIDI Pocket composition engine — generates original GM/GS MIDI tracks.

Every track varies: key, scale, tempo, chord progression, rhythm grid,
instrumentation, song form, melodic motif, register and dynamics.
Nothing here reproduces existing compositions; melodies are synthesized
from per-song motif parameters.

Usage:
  python3 tools/genmidi.py --out site/library/midi --index site/library/catalog.json --count 1000
"""
import argparse
import hashlib
import json
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from midilib import (PPQ, SCALES, NOTE_NAMES, Song, chord_tones, chord_quality,
                     degree_pitch, GM_DRUMS)

# ============================================================ titles
TITLE_BITS = {
    "adj":  ["Midnight", "Neon", "Crimson", "Silent", "Burning", "Frozen",
             "Electric", "Golden", "Hollow", "Endless", "Rising", "Falling",
             "Distant", "Scarlet", "Azure", "Velvet", "Lonely", "Savage",
             "Crystal", "Iron", "Solar", "Lunar", "Amber", "Quantum",
             "Wild", "Sacred", "Broken", "Hidden", "Radiant", "Drifting",
             "Stormy", "Faded", "Vivid", "Sonic", "Cobalt", "Emerald"],
    "noun": ["Highway", "Cascade", "Runner", "Signal", "Voyage", "Echo",
             "Horizon", "Circuit", "Mirage", "Pulse", "Frontier", "Orbit",
             "Ember", "Reverie", "Tempest", "Lantern", "Meridian", "Vortex",
             "Harbor", "Summit", "Current", "Aurora", "Monsoon", "Citadel",
             "Garden", "Labyrinth", "Anthem", "Requiem", "Overture", "Ballad",
             "Etude", "Nocturne", "Cascade", "Odyssey", "Pilgrim", "Rhapsody"],
    "sfx":  ["", "", "", "", "", " II", " '88", " (Reprise)", " Pt.2",
             " - Night Drive", " - Dawn Mix", " Returns", " Forever"],
}

MOODS = {
    "eurobeat": ["energetic", "driving", "euphoric"],
    "synthwave": ["nostalgic", "dreamy", "nocturnal"],
    "game": ["adventurous", "playful", "heroic", "mysterious"],
    "piano": ["tender", "melancholic", "reflective", "bright"],
    "orchestra": ["epic", "majestic", "dramatic", "serene"],
    "chiptune": ["playful", "hyper", "retro"],
    "jazz": ["smooth", "swinging", "late-night"],
    "lofi": ["mellow", "sleepy", "warm"],
    "trance": ["hypnotic", "uplifting", "euphoric"],
    "waltz": ["graceful", "romantic", "wistful"],
    "bossa": ["breezy", "romantic", "relaxed"],
    "ambient": ["floating", "meditative", "spacious"],
}

GENRE_SF = {
    "eurobeat": ["generaluser", "fluid"],
    "synthwave": ["generaluser", "fluid"],
    "game": ["generaluser", "chippocket"],
    "piano": ["generaluser", "fluid"],
    "orchestra": ["generaluser", "fluid"],
    "chiptune": ["chippocket", "generaluser"],
    "jazz": ["generaluser", "fluid"],
    "lofi": ["generaluser", "fluid"],
    "trance": ["generaluser", "fluid"],
    "waltz": ["generaluser", "fluid"],
    "bossa": ["generaluser", "fluid"],
    "ambient": ["generaluser", "fluid"],
}

# ============================================================ harmony
# degree pools per genre (0 = tonic). Sequences of scale degrees.
PROG = {
    "eurobeat":  [[0, 5, 2, 6], [0, 6, 5, 6], [0, 3, 5, 6], [5, 6, 0, 2],
                  [0, 5, 6, 2, 6], [0, 3, 6, 5]],
    "synthwave": [[0, 5, 2, 6], [0, 6, 5, 6], [0, 2, 6, 5], [5, 6, 0, 0],
                  [0, 5, 2, 5], [3, 6, 5, 5]],
    "game":      [[0, 4, 5, 3], [0, 5, 6, 4], [0, 6, 0, 6], [0, 3, 4, 4],
                  [0, 4, 3, 4], [0, 5, 3, 6], [4, 3, 0, 0], [0, 6, 5, 4]],
    "piano":     [[0, 5, 3, 4], [0, 4, 5, 3], [1, 4, 0, 3], [5, 1, 4, 0],
                  [0, 2, 3, 4], [0, 5, 1, 4], [3, 0, 4, 0]],
    "orchestra": [[0, 3, 0, 4], [0, 5, 2, 6], [0, 3, 4, 0], [0, 4, 0, 4],
                  [5, 6, 0, 3], [0, 1, 2, 3], [0, 5, 2, 4]],
    "chiptune":  [[0, 5, 6, 0], [0, 6, 5, 6], [0, 4, 5, 3], [0, 0, 5, 6],
                  [0, 3, 6, 5], [0, 5, 0, 6]],
    "jazz":      [[1, 4, 0, 5], [2, 5, 1, 4], [0, 5, 1, 4], [1, 4, 5, 0],
                  [3, 5, 0, 4], [0, 3, 1, 4]],
    "lofi":      [[1, 4, 0, 5], [0, 2, 5, 3], [1, 4, 3, 0], [0, 5, 1, 4]],
    "trance":    [[0, 5, 2, 6], [0, 6, 5, 6], [0, 3, 5, 6], [0, 2, 5, 5]],
    "waltz":     [[0, 4, 0, 4], [0, 3, 4, 0], [0, 4, 5, 4], [0, 0, 4, 4],
                  [3, 4, 0, 0], [0, 5, 4, 0]],
    "bossa":     [[1, 4, 0, 5], [0, 5, 1, 4], [0, 3, 1, 4], [3, 0, 1, 4]],
    "ambient":   [[0, 2, 5, 6], [0, 1, 0, 3], [0, 5, 0, 5], [3, 5, 0, 0]],
}

MINOR_GENRES = {"eurobeat", "synthwave", "trance", "chiptune", "ambient", "game"}
MAJOR_GENRES = {"piano", "waltz", "bossa", "lofi"}

SEVENTH_PROB = {"jazz": .9, "bossa": .8, "lofi": .7, "piano": .3,
                "orchestra": .2, "synthwave": .2, "ambient": .35}
SUS_PROB = {"synthwave": .15, "ambient": .2, "trance": .1}

# ============================================================ form
FORMS = {
    "pop":    ["intro", "verse", "chorus", "verse", "chorus", "bridge", "chorus", "outro"],
    "loop":   ["intro", "a", "a", "b", "a", "b", "a", "outro"],
    "thru":   ["intro", "a", "b", "a2", "c", "b2", "outro"],
    "dance":  ["intro", "build", "drop", "break", "build", "drop", "outro"],
    "class":  ["intro", "expo", "dev", "expo2", "coda"],
    "jam":    ["intro", "a", "a", "bridge", "a", "bridge", "a", "outro"],
}
GENRE_FORMS = {
    "eurobeat": ["pop", "dance"], "synthwave": ["pop", "thru"],
    "game": ["loop", "pop", "thru"], "piano": ["thru", "class"],
    "orchestra": ["class", "thru"], "chiptune": ["loop", "pop"],
    "jazz": ["jam", "thru"], "lofi": ["loop", "jam"],
    "trance": ["dance", "pop"], "waltz": ["class", "thru"],
    "bossa": ["jam", "loop"], "ambient": ["thru", "class"],
}

SECTION_LEN = {"intro": (2, 4), "outro": (2, 4), "verse": (4, 8), "chorus": (8, 8),
               "bridge": (4, 8), "a": (4, 8), "b": (4, 8), "a2": (4, 8),
               "b2": (4, 8), "c": (4, 8), "build": (4, 8), "drop": (8, 8),
               "break": (4, 8), "expo": (8, 12), "dev": (8, 12), "expo2": (8, 12),
               "coda": (4, 8)}

ENERGY = {"intro": .35, "outro": .3, "verse": .6, "chorus": .9, "bridge": .5,
          "a": .55, "b": .75, "a2": .65, "b2": .85, "c": .5, "build": .7,
          "drop": 1.0, "break": .4, "expo": .6, "dev": .75, "expo2": .85, "coda": .5}

STRONG = {"verse", "chorus", "a", "b", "a2", "b2", "drop", "expo", "expo2"}


# ============================================================ helpers
def pick(rng, xs):
    return xs[rng.randrange(len(xs))]


def chance(rng, p):
    return rng.random() < p


def clamp(v, lo=1, hi=127):
    return max(lo, min(hi, int(v)))


def snap_to_scale(pitch, root, scale):
    steps = SCALES[scale]
    pc = (pitch - root) % 12
    if pc in steps:
        return pitch
    # nearest scale tone within 1 semitone
    for off in (1, -1):
        if (pc + off) % 12 in steps:
            return pitch + off
    return pitch + 1


def snap_to_chord(pitch, tones):
    if pitch in tones:
        return pitch
    best, bd = pitch, 99
    for t in tones:
        d = abs(t - pitch)
        if d < bd:
            best, bd = t, d
    return best


def scale_7(scale):
    """Whether the scale has 7 degrees (needed for triad stacking)."""
    return len(SCALES[scale]) == 7


# ============================================================ melody engine
def gen_motif_rhythm(rng, density, beats_per_bar, note_val):
    """One-bar onset pattern in ticks."""
    bar = beats_per_bar * PPQ
    step = PPQ // note_val
    slots = bar // step
    grid = [0.0] * slots
    grid[0] = 1.0
    for i in range(1, slots):
        w = density * (1.6 if i % (slots // beats_per_bar) == 0 else 0.75)
        grid[i] = w
    onsets = [i * step for i, w in enumerate(grid) if rng.random() < w]
    if len(onsets) < 2:
        onsets = [0, bar // 2]
    return sorted(onsets)


def motif_to_phrase(rng, onsets, chords_tick, root, scale, par):
    """Emit (tick, dur, degree) melody notes for one bar.

    par: {range_lo, range_hi, leap, rest, syncop, legato}
    chords_tick: list of (tick_in_bar, degree) so strong beats align with harmony.
    """
    notes = []
    bar = max(onsets) + PPQ
    prev_deg = rng.choice([4, 7, 9])
    for i, tick in enumerate(onsets):
        if i and chance(rng, par["rest"]):
            continue
        nxt = onsets[i + 1] if i + 1 < len(onsets) else bar
        dur = int((nxt - tick) * par["legato"])
        dur = max(PPQ // 8, dur)
        # strong beat -> chord tone; weak -> scale tone
        deg_now = chord_at(chords_tick, tick)
        tones7 = chord_tones(root, scale, deg_now) if scale_7(scale) else []
        strong = tick % PPQ == 0
        if strong and tones7 and chance(rng, .75):
            tone = pick(rng, tones7)
            deg = nearest_degree(tone, root, scale, prev_deg, par)
        else:
            step_dir = rng.choice([-1, 1])
            leap = chance(rng, par["leap"])
            deg = prev_deg + step_dir * (rng.randint(2, 4) if leap else 1)
        prev_deg = deg
        notes.append((tick, dur, deg))
    return notes


def nearest_degree(tone, root, scale, around_deg, par):
    """Return degree whose pitch is `tone`, nearest octave to `around_deg`."""
    n = len(SCALES[scale])
    best, bd = around_deg, 999
    for d in range(around_deg - n * 2, around_deg + n * 2 + 1):
        p = degree_pitch(root, scale, d)
        dd = abs(p - tone)
        if dd < bd:
            best, bd = d, dd
    return best


def chord_at(chords_tick, tick):
    """chords_tick: sorted [(tick, degree)] section-relative; get active degree."""
    deg = chords_tick[0][1]
    for t, d in chords_tick:
        if t <= tick:
            deg = d
        else:
            break
    return deg


def render_melody(rng, song, trk, section_plans, root, scale, par,
                  base_oct, vel_scale=1.0, chord_off=0):
    """Render melody over all sections; motif rhythm varies slightly per section."""
    for sec_i, (tick0, n_bars, chords, energy, prog_degrees) in enumerate(section_plans):
        if energy < .3 or not par["play"].get(sec_i, True):
            continue
        onsets = gen_motif_rhythm(rng, par["density"] * (0.7 + 0.5 * energy),
                                  par["beats_bar"], par["note_val"])
        # phrase: repeat motif with variation; end phrase on tonic occasionally
        local_root = root + prog_degrees.get("key_shift", 0)
        for b in range(n_bars):
            t0 = tick0 + b * par["bar_len"]
            bar_rel = b * par["bar_len"]
            ch = [(t - bar_rel, d) for t, d in chords
                  if bar_rel <= t < bar_rel + par["bar_len"]]
            if not ch:
                ch = [(0, chords[0][1])]
            vary = (b % par["phrase_len"]) == par["phrase_len"] - 1
            onsets_b = onsets
            if vary and chance(rng, .6):  # cadence: thin the bar out
                onsets_b = [o for o in onsets if o % PPQ == 0] or [0]
            notes = motif_to_phrase(rng, onsets_b, ch, local_root, scale, par)
            for tick, dur, deg in notes:
                # hold final phrase note
                if vary:
                    dur = max(dur, PPQ)
                p = degree_pitch(local_root, scale, deg, base_oct + chord_off)
                p = snap_to_scale(p, local_root, scale)
                if p < par["range_lo"] or p > par["range_hi"]:
                    p = p - 12 if p > par["range_hi"] else p + 12
                v = clamp(par["vel"] * energy * vel_scale * (1 + .15 * (tick % PPQ == 0)))
                trk.note(t0 + tick, dur, clamp(p, 0, 127), v)


# ============================================================ drums
def drum_bar(rng, trk, t0, bar, pattern, vel_base, energy, swing=0.0):
    """pattern: {drum: [step probs len 16]}, fills at bar end."""
    D = GM_DRUMS
    for name, grid in pattern.items():
        note = D[name]
        for i, w in enumerate(grid):
            if w <= 0 or rng.random() > w * energy:
                continue
            t = t0 + i * bar // 16
            if swing and (i % 4 == 2):  # swing 16ths
                t += int(bar // 16 * swing)
            trk.note(t, max(1, bar // 32), note,
                     clamp(vel_base * (1.15 if i % 4 == 0 else .9)))
    return t0


def drum_fill(rng, trk, t0, bar, energy=1.0):
    D = GM_DRUMS
    start = t0 + bar - bar // 4
    toms = [D["tomH2"], D["tomH"], D["tomM"], D["tomL"]]
    for i in range(8):
        trk.note(start + i * bar // 32, bar // 32, pick(rng, toms + [D["snare"]]),
                 clamp(95 * energy))


def crash(trk, tick):
    trk.note(tick, PPQ, GM_DRUMS["crash"], 100)


PAT = {
    "eurobeat": {"kick": [1,0,0,0]*4, "ohat": [0,0,1,0]*4,
                 "chat": [1,0,1,0,1,0,1,0]*2, "snare": [0,0,0,0,1,0,0,0]*2,
                 "clap": [0,0,0,0,1,0,0,.3]*2, "ride": [.5]*16},
    "synthwave": {"kick": [1,0,0,0,0,0,0,.6,1,0,0,0,0,0,0,0],
                  "snare": [0,0,0,0,1,0,0,0]*2, "chat": [1,.3]*8,
                  "ohat": [0,0,0,0,0,0,1,0]*2, "ride": [.4]*16},
    "trance": {"kick": [1,0,0,0]*4, "ohat": [0,0,1,0]*4,
               "chat": [.8]*16, "clap": [0,0,0,0,1,0,0,.2]*2,
               "crash": [1]+[0]*15},
    "chiptune": {"kick": [1,0,0,.5,0,0,1,0,0,0,0,.5,0,0,0,0],
                 "snare": [0,0,0,0,1,0,0,0]*2, "chat": [.9]*16,
                 "ohat": [0,0,0,0,0,0,1,0]*2},
    "game": {"kick": [1,0,0,0,0,0,1,0]*2, "snare": [0,0,0,0,1,0,0,0]*2,
             "chat": [1,0,1,0,1,0,1,0]*2, "ohat": [0,0,0,0,0,0,1,0]*2,
             "tomL": [0]*14+[0,.3]},
    "jazz": {"ride": [1,0,0,.8,0,0,1,0,0,.8,0,0]*1+[1,0,0,.7],
             "chat": [0,0,0,0,1,0,0,0,0,0,0,0,1,0,0,0],
             "kick": [1,0,0,0,0,0,0,0,0,0,.5,0,0,0,0,0]},
    "lofi": {"kick": [1,0,0,0,0,0,0,.5,0,0,1,0,0,0,0,0],
             "snare": [0,0,0,0,1,0,0,0]*2, "chat": [.7,.2,.7,.2]*4,
             "rim": [0,0,0,0,0,0,.4,0]*2},
    "waltz": {"kick": [1,0,0,0]*4, "snare": [0,0,0,0,1,0,0,0,1,0,0,0,0,0,0,0],
              "chat": [.8,0,0,0]*4, "ohat": [0,0,0,0,.6,0,0,0,.6,0,0,0,0,0,0,0]},
    "bossa": {"kick": [1,0,0,0,0,0,1,0,0,0]*2,
              "rim": [1,0,0,.7,0,0,1,0,0,0,1,0,0,.7,0,0],
              "chat": [.8]*16, "shaker": [.5]*16},
    "ambient": {"kick": [1,0,0,0,0,0,0,0]*2, "shaker": [.3]*16,
                "ohat": [0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0]},
    "orchestra": {"kick": [1,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0],
                  "tomL": [0]*12+[.6,0,0,0], "crash": [1]+[0]*15,
                  "shaker": [.4]*16},
    "piano": {},
}

# ============================================================ genre composers
def plan_sections(rng, genre, beats_bar):
    """Return list of (name, n_bars)."""
    form = pick(rng, GENRE_FORMS[genre])
    plan = []
    for s in FORMS[form]:
        lo, hi = SECTION_LEN[s]
        n = rng.randint(lo // 4, hi // 4) * 4 or 4
        plan.append((s, n))
    return plan


def prog_for_section(rng, genre, name, verse_prog, chorus_prog):
    if name in ("chorus", "drop", "b", "b2", "expo", "expo2"):
        return chorus_prog
    return verse_prog


def chords_for(prog, n_bars, bar_len, len_per_chord_bars=None):
    """[(tick, degree)] — cycle progression to fill n_bars."""
    lp = len_per_chord_bars or 1
    out = []
    total = n_bars * bar_len
    t = 0
    i = 0
    while t < total:
        out.append((t, prog[i % len(prog)]))
        t += lp * bar_len
        i += 1
    return out


def bass_line(rng, trk, chords_sec, tick0, n_bars, bar_len, style, root, scale, energy):
    oct_off = -2
    for b in range(n_bars):
        t0 = tick0 + b * bar_len
        deg = chord_at(chords_sec, b * bar_len)
        cp = [degree_pitch(root, scale, deg + 2 * i, oct_off) for i in range(3)]
        r = cp[0]
        if style == "drive8":        # eurobeat/trance pumping 8ths
            for i in range(bar_len // (PPQ // 2)):
                trk.note(t0 + i * PPQ // 2, PPQ // 2 - 20, r + (12 if i % 2 else 0), clamp(105 * energy))
        elif style == "offbeat16":   # trance offbeat
            for i in range(bar_len // (PPQ // 4)):
                if i % 4 == 2:
                    trk.note(t0 + i * PPQ // 4, PPQ // 4 - 20, r + 12, clamp(100 * energy))
        elif style == "walk":        # jazz walking quarters
            tones = chord_tones(root, scale, deg, 4)
            prev = r
            for i in range(bar_len // PPQ):
                if i == 3 and chance(rng, .7):
                    p = prev + rng.choice([-1, -2, 1, 2])  # chromatic approach
                else:
                    p = pick(rng, tones)
                p = max(28, min(55, snap_to_scale(p, root, scale)))
                trk.note(t0 + i * PPQ, int(PPQ * .9), p - 12 if p > 55 else p, clamp(95 * energy))
                prev = p
        elif style == "waltz":
            trk.note(t0, int(PPQ * .8), r, clamp(100 * energy))
            for i in (1, 2):
                if i * PPQ < bar_len:
                    trk.note(t0 + i * PPQ, int(PPQ * .5), cp[1] if len(cp) > 1 else r + 7, clamp(75 * energy))
        elif style == "bossa":
            trk.note(t0, int(PPQ * .9), r, clamp(100 * energy))
            trk.note(t0 + int(bar_len * .625), int(PPQ * .7), r + 7, clamp(85 * energy))
            trk.note(t0 + bar_len - PPQ // 2, PPQ // 2 - 30, r + 12, clamp(80 * energy))
        elif style == "long":
            trk.note(t0, bar_len, r, clamp(88 * energy))
            if len(cp) > 1 and n_bars > 2 and b % 4 == 3:
                trk.note(t0 + bar_len - PPQ, PPQ - 20, cp[-1], clamp(80 * energy))
        elif style == "sparse":
            trk.note(t0, int(PPQ * 1.5), r, clamp(90 * energy))
            if chance(rng, .4):
                trk.note(t0 + int(bar_len * .75), PPQ // 2, r + 7, clamp(70 * energy))
        else:  # "root8"
            for i in range(bar_len // (PPQ // 2)):
                trk.note(t0 + i * PPQ // 2, PPQ // 2 - 40, r, clamp(98 * energy))


def pad_chords(rng, trk, chords_sec, tick0, n_bars, bar_len, style, root, scale,
               energy, n_notes=3, oct_off=0):
    for b in range(n_bars):
        t0 = tick0 + b * bar_len
        deg = chord_at(chords_sec, b * bar_len)
        tones = chord_tones(root, scale, deg, n_notes, oct_off)
        v = clamp(78 * energy)
        if style == "sustain":
            trk.chord(t0, bar_len, tones, v)
        elif style == "stab8":       # rhythmic stabs 8ths
            for i in range(bar_len // (PPQ // 2)):
                if chance(rng, .8):
                    trk.chord(t0 + i * PPQ // 2, PPQ // 2 - 60, tones, v)
        elif style == "stab16":      # offbeat 16th stabs
            for i in range(bar_len // (PPQ // 4)):
                if i % 4 in (2, 3) and chance(rng, .7):
                    trk.chord(t0 + i * PPQ // 4, PPQ // 4 - 40, tones, v)
        elif style == "arpeggio":
            # per-section pattern variety: direction, octave span, grid, gaps
            up2 = tones + [t + 12 for t in tones]
            pat = pick(rng, ["ping", "ping", "up", "down", "up2", "bounce", "walk", "broken"])
            if pat == "ping":
                seq = tones + tones[::-1][1:-1]
            elif pat == "up":
                seq = tones[:]
            elif pat == "down":
                seq = tones[::-1]
            elif pat == "up2":
                seq = up2
            elif pat == "bounce":   # alternating octaves, chiptune feel
                seq = [x for t in tones for x in (t, t + 12)]
            elif pat == "walk":
                seq = [tones[0]]
                for _ in range(7):
                    seq.append(pick(rng, tones + up2))
            else:                   # broken: fixed index pattern
                idx = [0, 2, 1, 2, 0, 1, 2, 1]
                seq = [tones[i % len(tones)] for i in idx]
            step = pick(rng, [PPQ // 4, PPQ // 4, PPQ // 2, PPQ // 3])
            octv = pick(rng, [12, 12, 24])
            for i in range(bar_len // step):
                if chance(rng, .92):
                    trk.note(t0 + i * step, step - 30,
                             seq[i % len(seq)] + octv, clamp(70 * energy))
        elif style == "waltz":
            for i in (1, 2):
                if i * PPQ < bar_len:
                    trk.chord(t0 + i * PPQ, int(PPQ * .55), tones, v)
        elif style == "strum":       # piano/bossa syncopated strums
            grid = [0, .5, .75, 1.5, 2.5, 3.0]
            for g in grid:
                if g * PPQ < bar_len and chance(rng, .75):
                    trk.chord(t0 + int(g * PPQ), int(PPQ * .6), tones, v, strum=8)
        elif style == "whole":
            if b % 2 == 0:
                trk.chord(t0, bar_len * 2, tones, clamp(60 * energy))


def apply_prog_bank(trk, program, bank=None):
    if bank:
        trk.program(0, program, bank_msb=bank)
    else:
        trk.program(0, program)
    trk.cc(0, 7, 100)   # volume
    trk.cc(0, 10, 64)   # pan center


def compose(song, rng, genre, spec):
    """Generic composer driven by per-genre spec dict."""
    root = spec["root"]
    scale = spec["scale"]
    beats_bar = spec["beats_bar"]
    bar_len = beats_bar * PPQ
    verse_prog = pick(rng, PROG[genre])
    chorus_prog = pick(rng, [p for p in PROG[genre] if p != verse_prog] or [verse_prog])
    plan = plan_sections(rng, genre, beats_bar)

    # section layout: absolute ticks + per-section chords
    tick = 0
    sections = []
    for name, nb in plan:
        prog = prog_for_section(rng, genre, name, verse_prog, chorus_prog)
        ch = chords_for(prog, nb, bar_len, spec.get("chord_bars", 1))
        key_shift = 0
        if name in ("bridge", "c", "dev") and chance(rng, spec.get("modulate", .4)):
            key_shift = pick(rng, [2, 3, -2, -3, 5])
        sections.append({"name": name, "tick": tick, "bars": nb,
                         "chords": ch, "energy": ENERGY.get(name, .6),
                         "key_shift": key_shift})
        tick += nb * bar_len

    # instruments
    chans = {"drums": 9, "bass": 0, "chord": 1, "lead": 2, "pad": 3, "arp": 4, "extra": 5}
    t_dr = song.new_track("drums", chans["drums"])
    t_bass = song.new_track("bass", chans["bass"])
    t_ch = song.new_track("chords", chans["chord"])
    t_lead = song.new_track("lead", chans["lead"])
    t_pad = song.new_track("pad", chans["pad"])

    apply_prog_bank(t_bass, spec["bass_prog"], spec.get("bass_bank"))
    apply_prog_bank(t_ch, spec["chord_prog"], spec.get("chord_bank"))
    apply_prog_bank(t_lead, spec["lead_prog"], spec.get("lead_bank"))
    if spec["pad_prog"] is not None:
        apply_prog_bank(t_pad, spec["pad_prog"], spec.get("pad_bank"))

    par = dict(density=spec["density"], beats_bar=beats_bar, bar_len=bar_len,
               note_val=spec["note_val"], leap=spec["leap"], rest=spec["rest"],
               syncop=spec.get("syncop", .2), legato=spec.get("legato", .95),
               range_lo=spec["range_lo"], range_hi=spec["range_hi"],
               phrase_len=pick(rng, [2, 4]), vel=spec["vel"], play={})

    drum_pat = PAT[spec["drum_pat"]]
    for i, sec in enumerate(sections):
        t0, nb, en = sec["tick"], sec["bars"], sec["energy"]
        ch_sec = [(c[0], c[1]) for c in sec["chords"]]
        local_root = root + sec["key_shift"]
        # relative chords re-anchored per section already use global tick — keep as is
        # drums
        if drum_pat and en > .35 and spec["drums_in"].get(sec["name"], True):
            for b in range(nb):
                drum_bar(rng, t_dr, t0 + b * bar_len, bar_len, drum_pat,
                         92, en, swing=spec.get("swing", 0))
                if (b + 1) % 4 == 0 and b + 1 < nb and chance(rng, .8):
                    drum_fill(rng, t_dr, t0 + b * bar_len, bar_len, en)
            crash(t_dr, t0)
        # bass
        bass_line(rng, t_bass, ch_sec, t0, nb, bar_len,
                  spec["bass_style"], local_root, scale, en)
        # chords
        pad_chords(rng, t_ch, ch_sec, t0, nb, bar_len,
                   spec["chord_style"], local_root, scale, en,
                   n_notes=4 if chance(rng, SEVENTH_PROB.get(genre, .15)) else 3,
                   oct_off=spec.get("chord_oct", 0))
        # pad
        if spec.get("pad_prog") is not None and en >= .3:
            pad_chords(rng, t_pad, ch_sec, t0, nb, bar_len, "sustain",
                       local_root, scale, en * .8, n_notes=3, oct_off=1)

    # melody
    mel_sections = []
    for i, sec in enumerate(sections):
        name = sec["name"]
        mel_sections.append((sec["tick"], sec["bars"],
                             sec["chords"], sec["energy"],
                             {"key_shift": sec["key_shift"]}))
        par["play"][i] = name in STRONG or chance(rng, .35)
    render_melody(rng, song, t_lead, mel_sections, root, scale, par,
                  spec["mel_oct"])


# ============================================================ specs
def spec_for(rng, genre):
    minorish = genre in MINOR_GENRES or (genre == "orchestra" and chance(rng, .5))
    scale = "minor" if minorish else "major"
    if genre == "game" and chance(rng, .3):
        scale = pick(rng, ["dorian", "mixolydian", "pent_maj"])
    if genre == "jazz":
        scale = pick(rng, ["major", "dorian", "mixolydian"])
    if genre == "ambient":
        scale = pick(rng, ["minor", "lydian", "dorian", "pent_maj"])
    if genre == "chiptune":
        scale = pick(rng, ["minor", "pent_min", "dorian"])
    if genre == "waltz":
        scale = pick(rng, ["major", "minor", "harm_min"])
    if genre == "bossa":
        scale = "major"
    if genre == "lofi":
        scale = pick(rng, ["major", "dorian"])
    if genre == "piano":
        scale = pick(rng, ["major", "major", "minor"])
    if scale in ("pent_maj", "pent_min", "blues") and not scale_7(scale):
        scale = "major" if scale == "pent_maj" else "minor"

    s = {
        "eurobeat": dict(
            bpm=(148, 172), beats_bar=4, drum_pat="eurobeat",
            bass_prog=39, chord_prog=2, lead_prog=81, pad_prog=91,
            bass_style="drive8", chord_style="stab8", mel_oct=1,
            density=.62, note_val=4, leap=.3, rest=.12, vel=104,
            range_lo=57, range_hi=84, modulate=.5),
        "synthwave": dict(
            bpm=(84, 112), beats_bar=4, drum_pat="synthwave",
            bass_prog=39, chord_prog=91, lead_prog=81, pad_prog=90,
            bass_style="drive8", chord_style="stab16", mel_oct=1,
            density=.4, note_val=4, leap=.32, rest=.22, vel=96,
            range_lo=57, range_hi=81, modulate=.35, swing=0),
        "game": dict(
            bpm=(100, 150), beats_bar=4, drum_pat="game",
            bass_prog=33, chord_prog=4, lead_prog=pick(rng, [80, 81, 74, 76]),
            pad_prog=49, bass_style="root8", chord_style="stab8", mel_oct=1,
            density=.55, note_val=4, leap=.35, rest=.15, vel=102,
            range_lo=60, range_hi=86, modulate=.5),
        "piano": dict(
            bpm=(72, 120), beats_bar=4, drum_pat="piano",
            bass_prog=33, chord_prog=0, lead_prog=0, pad_prog=49,
            bass_style="sparse", chord_style="strum", mel_oct=0,
            density=.45, note_val=4, leap=.3, rest=.3, vel=88,
            range_lo=55, range_hi=84, modulate=.4, legato=1.0),
        "orchestra": dict(
            bpm=(80, 140), beats_bar=4, drum_pat="orchestra",
            bass_prog=44, chord_prog=49, lead_prog=pick(rng, [41, 74, 69, 72]),
            pad_prog=49, bass_style="sparse", chord_style="sustain", mel_oct=1,
            density=.42, note_val=4, leap=.38, rest=.25, vel=96,
            range_lo=57, range_hi=88, modulate=.55),
        "chiptune": dict(
            bpm=(120, 170), beats_bar=4, drum_pat="chiptune",
            bass_prog=80, chord_prog=80, lead_prog=pick(rng, [80, 81]),
            pad_prog=None, bass_style="drive8", chord_style="stab16", mel_oct=1,
            density=.6, note_val=4, leap=.3, rest=.15, vel=100,
            range_lo=60, range_hi=90, modulate=.4, legato=.7),
        "jazz": dict(
            bpm=(90, 150), beats_bar=4, drum_pat="jazz",
            bass_prog=33, chord_prog=2, lead_prog=pick(rng, [57, 66, 71]),
            pad_prog=None, bass_style="walk", chord_style="strum", mel_oct=1,
            density=.5, note_val=4, leap=.35, rest=.28, vel=92,
            range_lo=58, range_hi=84, modulate=.4, swing=.55, legato=.9),
        "lofi": dict(
            bpm=(65, 90), beats_bar=4, drum_pat="lofi",
            bass_prog=34, chord_prog=5, lead_prog=pick(rng, [5, 74, 11]),
            pad_prog=90, bass_style="sparse", chord_style="strum", mel_oct=0,
            density=.32, note_val=4, leap=.25, rest=.4, vel=80,
            range_lo=57, range_hi=79, modulate=.25, swing=.3, legato=1.0),
        "trance": dict(
            bpm=(130, 145), beats_bar=4, drum_pat="trance",
            bass_prog=39, chord_prog=91, lead_prog=81, pad_prog=90,
            bass_style="offbeat16", chord_style="stab16", mel_oct=1,
            density=.5, note_val=4, leap=.28, rest=.2, vel=102,
            range_lo=60, range_hi=86, modulate=.4),
        "waltz": dict(
            bpm=(90, 140), beats_bar=3, drum_pat="waltz",
            bass_prog=33, chord_prog=49, lead_prog=pick(rng, [0, 41, 74]),
            pad_prog=49, bass_style="waltz", chord_style="waltz", mel_oct=0,
            density=.4, note_val=4, leap=.33, rest=.3, vel=90,
            range_lo=55, range_hi=84, modulate=.4),
        "bossa": dict(
            bpm=(120, 150), beats_bar=4, drum_pat="bossa",
            bass_prog=33, chord_prog=25, lead_prog=pick(rng, [74, 25, 11]),
            pad_prog=None, bass_style="bossa", chord_style="strum", mel_oct=0,
            density=.38, note_val=4, leap=.3, rest=.3, vel=85,
            range_lo=57, range_hi=81, modulate=.35, swing=.15),
        "ambient": dict(
            bpm=(60, 95), beats_bar=4, drum_pat="ambient",
            bass_prog=90, chord_prog=91, lead_prog=pick(rng, [95, 74, 92]),
            pad_prog=89, bass_style="long", chord_style="whole", mel_oct=0,
            density=.22, note_val=2, leap=.4, rest=.5, vel=74,
            range_lo=55, range_hi=79, modulate=.5, legato=1.1, chord_bars=2),
    }[genre]
    s["root"] = rng.randrange(0, 12)
    s["scale"] = scale
    s["bpm"] = rng.randint(*s["bpm"])
    s["drums_in"] = {}
    return s


def make_title(rng, used):
    for _ in range(50):
        t = f"{pick(rng, TITLE_BITS['adj'])} {pick(rng, TITLE_BITS['noun'])}{pick(rng, TITLE_BITS['sfx'])}"
        if t not in used:
            used.add(t)
            return t
    return f"{pick(rng, TITLE_BITS['adj'])} {pick(rng, TITLE_BITS['noun'])} {rng.randint(100,999)}"


def generate_one(rng, genre, idx, used_titles):
    title = make_title(rng, used_titles)
    spec = spec_for(rng, genre)
    den = 8 if spec["beats_bar"] == 3 and chance(rng, .5) else 4
    song = Song(spec["bpm"], title, spec["beats_bar"], den)
    # register tempo & key text event on a meta-like track (in drums track)
    compose(song, rng, genre, spec)
    mid = song.build()
    key = NOTE_NAMES[spec["root"]] + " " + spec["scale"]
    tags = [genre, key.split()[0], spec["scale"],
            "minor" if spec["scale"] in ("minor", "harm_min", "dorian", "phrygian", "pent_min") else "major"]
    if spec["beats_bar"] == 3:
        tags.append("3/4")
    if spec["bpm"] >= 150:
        tags.append("fast")
    elif spec["bpm"] <= 85:
        tags.append("slow")
    mood = pick(rng, MOODS[genre])
    track_id = f"{genre}-{idx:03d}-{hashlib.sha1(title.encode()).hexdigest()[:6]}"
    fname = f"{track_id}.mid"
    rec = {
        "id": track_id, "title": title, "file": f"midi/{fname}",
        "genre": genre, "mood": mood, "bpm": spec["bpm"],
        "key": key, "tags": sorted(set(tags)),
        "recommendedSoundfonts": GENRE_SF[genre],
    }
    return mid, rec


def measure_duration_sec(mid):
    ticks = mid.ticks_per_beat
    total_ticks = 0
    for trk in mid.tracks:
        t = sum(m.time for m in trk)
        total_ticks = max(total_ticks, t)
    # assume single tempo
    tempo = 500000
    for m in mid.tracks[0]:
        if m.type == "set_tempo":
            tempo = m.tempo
            break
    return round(total_ticks / ticks * tempo / 1e6, 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="site/library/midi")
    ap.add_argument("--index", default="site/library/catalog.json")
    ap.add_argument("--parts-dir", default="site/library/catalog")
    ap.add_argument("--count", type=int, default=1000)
    ap.add_argument("--per-genre", type=int, default=0,
                    help="override: tracks per genre")
    ap.add_argument("--seed", type=int, default=20260925)
    ap.add_argument("--part-size", type=int, default=100)
    args = ap.parse_args()

    genres = list(MOODS)
    per = args.per_genre or max(1, args.count // len(genres))
    rng = random.Random(args.seed)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    used_titles = set()
    records = []
    for genre in genres:
        for i in range(per):
            trng = random.Random(rng.random())
            mid, rec = generate_one(trng, genre, i, used_titles)
            path = out / rec["file"].split("/")[1]
            mid.save(str(path))
            rec["durationSec"] = measure_duration_sec(mid)
            rec["sizeBytes"] = path.stat().st_size
            records.append(rec)
        print(f"{genre}: {per} tracks", file=sys.stderr)

    # split catalog into parts
    parts_dir = Path(args.parts_dir)
    parts_dir.mkdir(parents=True, exist_ok=True)
    rng.shuffle(records)
    parts = []
    genres_map = {}
    for i in range(0, len(records), args.part_size):
        chunk = records[i:i + args.part_size]
        name = f"catalog/part-{i // args.part_size:03d}.json"
        (parts_dir / f"part-{i // args.part_size:03d}.json").write_text(
            json.dumps(chunk, ensure_ascii=False))
        parts.append({"file": name, "count": len(chunk)})
    for r in records:
        genres_map.setdefault(r["genre"], {"count": 0})
        genres_map[r["genre"]]["count"] += 1
    catalog = {
        "version": 2, "count": len(records), "seed": args.seed,
        "genres": genres_map, "parts": parts,
    }
    Path(args.index).write_text(json.dumps(catalog, ensure_ascii=False, indent=1))
    print(f"total {len(records)} tracks -> {args.index}", file=sys.stderr)


if __name__ == "__main__":
    main()
