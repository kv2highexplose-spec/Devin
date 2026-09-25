"""Shared music-theory + MIDI-writing helpers for the MIDI Pocket generator.

Pure stdlib + mido. All generation is original: chord pools, rhythm patterns
and melody engines are parameterized per-song so no two tracks share a melody.
"""
import random

import mido

PPQ = 480

# ---------------------------------------------------------------- theory
SCALES = {
    "major":       [0, 2, 4, 5, 7, 9, 11],
    "minor":       [0, 2, 3, 5, 7, 8, 10],
    "harm_min":    [0, 2, 3, 5, 7, 8, 11],
    "dorian":      [0, 2, 3, 5, 7, 9, 10],
    "mixolydian":  [0, 2, 4, 5, 7, 9, 10],
    "phrygian":    [0, 1, 3, 5, 7, 8, 10],
    "pent_maj":    [0, 2, 4, 7, 9],
    "pent_min":    [0, 3, 5, 7, 10],
    "blues":       [0, 3, 5, 6, 7, 10],
    "lydian":      [0, 2, 4, 6, 7, 9, 11],
}

NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

# chord qualities by scale degree in major / natural minor
MAJ_QUAL = ["", "m", "m", "", "", "m", "dim"]
MIN_QUAL = ["m", "dim", "", "m", "m", "", ""]

# degree -> semitone offset within scale (7-note scales only)
def degree_pitch(root, scale, degree, octave_off=0):
    """degree is 0-based scale degree; supports degrees outside one octave."""
    steps = SCALES[scale]
    n = len(steps)
    octs, d = divmod(degree, n)
    return root + steps[d] + 12 * (octs + octave_off)


def chord_tones(root, scale, degree, n_notes=3, octave_off=0):
    """Triad/seventh on a scale degree: stack thirds."""
    q = 4 if n_notes == 4 else 3
    return [degree_pitch(root, scale, degree + 2 * i, octave_off) for i in range(q)]


def chord_quality(scale, degree):
    d = degree % 7
    if scale in ("major", "mixolydian", "lydian"):
        return MAJ_QUAL[d]
    return MIN_QUAL[d]


# ---------------------------------------------------------------- writer
class Track:
    """One logical channel/track of events in absolute ticks."""

    def __init__(self, name="", channel=0):
        self.events = []   # (tick, kind, payload)
        self.name = name
        self.channel = channel

    def program(self, tick, program, bank_msb=None, bank_lsb=None):
        if bank_msb is not None:
            self.events.append((tick, "cc", (0, bank_msb)))
        if bank_lsb is not None:
            self.events.append((tick, "cc", (32, bank_lsb)))
        self.events.append((tick, "pc", program))

    def cc(self, tick, ctrl, val):
        self.events.append((tick, "cc", (ctrl, val)))

    def note(self, tick, dur, pitch, vel):
        pitch = max(0, min(127, int(pitch)))
        vel = max(1, min(127, int(vel)))
        self.events.append((tick, "on", (pitch, vel)))
        self.events.append((tick + max(1, int(dur)), "off", (pitch, 0)))

    def chord(self, tick, dur, pitches, vel, strum=0):
        for i, p in enumerate(pitches):
            self.note(tick + i * strum, max(1, dur - i * strum), p, vel)

    def bend(self, tick, val):
        self.events.append((tick, "bend", val))

    def meta_text(self, tick, text):
        self.events.append((tick, "text", text))


class Song:
    def __init__(self, bpm, title, numerator=4, denominator=4):
        self.bpm = bpm
        self.title = title
        self.timesig = (numerator, denominator)
        self.tracks = []

    def new_track(self, name, channel):
        t = Track(name, channel)
        self.tracks.append(t)
        return t

    def build(self):
        """Serialize to a mido.MidiFile (format 1, PPQ ticks)."""
        mid = mido.MidiFile(ticks_per_beat=PPQ)
        meta = mido.MidiTrack()
        meta.append(mido.MetaMessage("set_tempo", tempo=mido.bpm2tempo(self.bpm), time=0))
        n, d = self.timesig
        meta.append(mido.MetaMessage("time_signature", numerator=n, denominator=d,
                                     clocks_per_click=24, notated_32nd_notes_per_beat=8, time=0))
        meta.append(mido.MetaMessage("track_name", name=self.title[:60], time=0))
        meta.append(mido.MetaMessage("end_of_track", time=0))
        mid.tracks.append(meta)
        for tr in self.tracks:
            mt = mido.MidiTrack()
            mt.append(mido.MetaMessage("track_name", name=tr.name[:60], time=0))
            last = 0
            for tick, kind, payload in sorted(tr.events, key=lambda e: (e[0], _order(e[1]))):
                delta = max(0, tick - last)
                last = tick
                if kind == "pc":
                    mt.append(mido.Message("program_change", channel=tr.channel,
                                           program=payload, time=delta))
                elif kind == "cc":
                    c, v = payload
                    mt.append(mido.Message("control_change", channel=tr.channel,
                                           control=c, value=v, time=delta))
                elif kind == "on":
                    p, v = payload
                    mt.append(mido.Message("note_on", channel=tr.channel,
                                           note=p, velocity=v, time=delta))
                elif kind == "off":
                    p, _ = payload
                    mt.append(mido.Message("note_off", channel=tr.channel,
                                           note=p, velocity=0, time=delta))
                elif kind == "bend":
                    mt.append(mido.Message("pitchwheel", channel=tr.channel,
                                           pitch=payload, time=delta))
                elif kind == "text":
                    mt.append(mido.MetaMessage("text", text=payload, time=delta))
            mt.append(mido.MetaMessage("end_of_track", time=0))
            mid.tracks.append(mt)
        return mid


def _order(kind):
    # bank select CCs before program change, program change before notes
    return {"cc": 0, "pc": 1, "text": 2, "on": 3, "off": 4, "bend": 5}[kind]


# ---------------------------------------------------------------- rhythm
def beats(n, den=4):
    """bar length in ticks for n beats of `den` denominator at PPQ."""
    return int(n * PPQ * 4 / den)


GM_DRUMS = {
    "kick": 36, "kick2": 35, "snare": 38, "snare2": 40, "clap": 39,
    "chat": 42, "ohat": 46, "phat": 44, "ride": 51, "crash": 49,
    "tomL": 45, "tomM": 47, "tomH": 50, "tomH2": 48,
    "cowbell": 56, "rim": 37, "shaker": 70, "tamb": 54, "congaH": 63, "congaL": 62,
    "cabasa": 69, "guiro": 74, "agogo": 67, "woodblock": 76,
}


def bars(n, beats_per_bar):
    return n * beats_per_bar
