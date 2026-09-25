#!/usr/bin/env python3
"""Synthesize "Chip Pocket" — a tiny original chiptune-flavored GM soundfont.

All samples are generated procedurally (pulse/square/triangle/saw/noise),
so the font is 100% original — zero license risk. Writes a valid SF2 (RIFF)
readable by spessasynth / FluidSynth.

Output: site/library/soundfonts/chippocket.sf2
"""
import math
import struct
import sys
import wave
from pathlib import Path

SR = 22050  # base sample rate for one-shot drums / noise

# ---------------------------------------------------------------- waves
def square(duty, n):
    return [0.85 if (i % int(round(n / duty)) if n else 0) or True else 0 for i in range(0)]  # unused


def pulse_wave(duty, cycles=32, per_cycle=256):
    """Single-cycle-ish looped pulse train. Returns int16 list."""
    out = []
    total = cycles * per_cycle
    for i in range(total):
        ph = (i % per_cycle) / per_cycle
        out.append(int(32767 * (1.0 if ph < duty else -1.0)))
    return out


def tri_wave(cycles=32, per_cycle=256):
    out = []
    for i in range(cycles * per_cycle):
        ph = (i % per_cycle) / per_cycle
        v = 4 * abs(ph - 0.5) - 1.0
        out.append(int(32767 * (1 - 2 * v) * .9) if False else int(32767 * (ph * 4 - 1 if ph < .5 else 3 - 4 * ph)))
    return [int(x * .85) for x in out]


def saw_wave(cycles=32, per_cycle=256):
    out = []
    for i in range(cycles * per_cycle):
        ph = (i % per_cycle) / per_cycle
        out.append(int(32767 * (2 * ph - 1) * .8))
    return out


def sine_wave(cycles=32, per_cycle=256):
    return [int(32767 * .9 * math.sin(2 * math.pi * i / per_cycle))
            for i in range(cycles * per_cycle)]


def noise_hit(dur_s, decay_exp=4.0, bright=False):
    """One-shot noise burst (hats/snare/crash)."""
    import random
    rng = random.Random(7)
    n = int(SR * dur_s)
    out = []
    prev = 0.0
    for i in range(n):
        t = i / n
        amp = (1 - t) ** decay_exp
        w = rng.uniform(-1, 1)
        if not bright:
            prev = 0.5 * prev + 0.5 * w
            w = prev
        out.append(int(32767 * amp * .9 * w))
    return out


def sine_thump(dur_s=0.25, f0=150, f1=45):
    """Kick: sine with pitch drop."""
    n = int(SR * dur_s)
    out = []
    ph = 0.0
    for i in range(n):
        t = i / n
        f = f0 + (f1 - f0) * min(1.0, t * 3)
        ph += 2 * math.pi * f / SR
        amp = (1 - t) ** 3.2
        out.append(int(32767 * amp * .95 * math.sin(ph)))
    return out


def blip(f0=880, f1=110, dur_s=0.06, duty=.5):
    """Short pitched blip for toms."""
    n = int(SR * dur_s)
    out = []
    ph = 0.0
    for i in range(n):
        t = i / n
        f = f0 + (f1 - f0) * t
        ph += f / SR
        v = 1.0 if (ph % 1) < duty else -1.0
        out.append(int(32767 * (1 - t) ** 2.2 * .8 * v))
    return out


def tc(sec):
    """timecents for a duration in seconds."""
    return int(round(1200 * math.log2(max(0.0005, sec))))


# ---------------------------------------------------------------- SF2 writer
def rec_str(name, s):
    b = s.encode("ascii", "replace")
    return name.encode() + struct.pack("<I", len(b)) + b


def pad(b):
    return b + (b"\0" if len(b) % 2 else b"")


class SF2:
    def __init__(self, name):
        self.name = name
        self.samples = []          # (name, int16 list, looped, rate, origKey)
        self.inst = []             # (name, [(keyLo,keyHi,velLo,velHi,sampleIdx,att,dec,sus,rel,pan,rootKey,mode)])
        self.presets = []          # (bank, preset, name, inst_idx)

    def add_sample(self, name, pcm, looped, rate=SR, key=60):
        self.samples.append((name, pcm, looped, rate, key))
        return len(self.samples) - 1

    def add_inst(self, name, zones):
        self.inst.append((name, zones))
        return len(self.inst) - 1

    def add_preset(self, bank, preset, name, inst_idx):
        self.presets.append((bank, preset, name, inst_idx))

    # ------------------------------------------------------------ build
    def build(self):
        # ---------- sdta
        smpl = bytearray()
        offs = []
        for name, pcm, looped, rate, key in self.samples:
            offs.append(len(smpl) // 2)
            for v in pcm:
                smpl += struct.pack("<h", v)
            # 46 zero samples terminator per spec between samples (pad 32 + 46)
            smpl += b"\0" * 92
        sdta = rec_str("smpl", "")  # placeholder; actual: chunk 'smpl'
        smpl_chunk = b"smpl" + struct.pack("<I", len(smpl)) + bytes(smpl)
        sdta_body = b"sdta" + smpl_chunk
        sdta = b"LIST" + struct.pack("<I", len(sdta_body)) + sdta_body

        # ---------- pdta records
        # instrument global zones: zone0 = global (no sampleID), then keyed zones
        inst_names = [n for n, _ in self.inst]
        inst_recs = b""
        ibag_recs = b""
        imod_recs = b""
        igen_recs = b""
        shdr_recs = b""
        ibag_count = 0
        igen_count = 0
        imod_count = 0

        sample_chunks = []  # offsets already computed via offs
        # recompute sample offsets (each followed by 46 zero shorts)
        offs = []
        pos = 0
        for name, pcm, looped, rate, key in self.samples:
            offs.append(pos)
            pos += len(pcm) + 46

        imod_recs += b"\0" * 10  # shared terminal record
        for iname, zones in self.inst:
            inst_recs += iname.encode()[:20].ljust(20, b"\0") + struct.pack("<H", ibag_count)
            # zones: first may be global (sample_idx None)
            for (klo, khi, vlo, vhi, sidx, att, dec, sus, rel, pan, rootkey, modes, scaletune) in zones:
                g = ibag_count
                ibag_recs += struct.pack("<HH", igen_count, imod_count)
                ibag_count += 1
                # generators
                def gen(op, val):
                    nonlocal igen_count, igen_recs
                    igen_recs += struct.pack("<Hh", op, val)
                    igen_count += 1
                # gen ops: keyRange=43 velRange=44 att=48? (see below — SF2 spec ids)
                # delayVolEnv=33 attackVolEnv=34 holdVolEnv=35 decayVolEnv=36
                # sustainVolEnv=37 releaseVolEnv=38 keyRange=43 velRange=44
                # instrument=41(pbag only) pan=17 coarse=51 fine=52 scaleTuning=56
                # overridingRootKey=58 sampleModes=54 sampleID=53
                gen(43, (khi << 8) | klo)         # keyRange
                if vhi:
                    gen(44, (vhi << 8) | vlo)
                if att is not None:
                    gen(34, att)
                if dec is not None:
                    gen(36, dec)
                if sus is not None:
                    gen(37, sus)
                if rel is not None:
                    gen(38, rel)
                if pan is not None:
                    gen(17, pan)
                if scaletune is not None:
                    gen(56, scaletune)
                if rootkey is not None:
                    gen(58, rootkey)
                if modes:
                    gen(54, modes)                # sampleModes: 1=loop, 3=loop till release
                if sidx is not None:
                    gen(53, sidx)                 # sampleID LAST per spec
            # terminal ibag
            ibag_recs += struct.pack("<HH", igen_count, imod_count)
            ibag_count += 1
        # EOI sentinel references the final ibag record, which must exist
        inst_recs += b"EOI".ljust(20, b"\0") + struct.pack("<H", ibag_count)
        ibag_recs += struct.pack("<HH", igen_count, imod_count)
        ibag_count += 1

        for i, (name, pcm, looped, rate, key) in enumerate(self.samples):
            start = offs[i]
            end = offs[i] + len(pcm) - 1
            if looped:
                sl, el = start, end
            else:
                sl = el = start
            shdr_recs += name.encode()[:20].ljust(20, b"\0") + struct.pack(
                "<IIIIIBbHH", start, end, sl, el, rate, key, 0, 0, 1 if not looped else 1)
        shdr_recs += b"EOS".ljust(20, b"\0") + struct.pack("<IIIIIBbHH", 0, 0, 0, 0, 0, 0, 0, 0, 0)

        # preset records: pbag/pgen reference instruments
        phdr_recs = b""
        pbag_recs = b""
        pmod_recs = b""
        pgen_recs = b""
        pbag_count = 0
        pgen_count = 0
        for (bank, preset, pname, inst_idx) in self.presets:
            phdr_recs += pname.encode()[:20].ljust(20, b"\0") + struct.pack(
                "<HHHIII", preset, bank, pbag_count, 0, 0, 0)
            pbag_recs += struct.pack("<HH", pgen_count, 0)
            pbag_count += 1
            pgen_recs += struct.pack("<Hh", 41, inst_idx)  # 'instrument' gen
            pgen_count += 1
        pmod_recs += b"\0" * 10  # terminal modulator record
        # EOP sentinel references the final pbag record, which must exist
        phdr_recs += b"EOP".ljust(20, b"\0") + struct.pack("<HHHIII", 0, 0, pbag_count, 0, 0, 0)
        pbag_recs += struct.pack("<HH", pgen_count, 0)
        pbag_count += 1

        def chunk(name, data):
            b = name.encode() + struct.pack("<I", len(data)) + data
            return b + (b"\0" if len(data) % 2 else b"")

        pdta_body = (b"pdta" + chunk("phdr", phdr_recs) + chunk("pbag", pbag_recs)
                     + chunk("pmod", pmod_recs) + chunk("pgen", pgen_recs)
                     + chunk("inst", inst_recs) + chunk("ibag", ibag_recs)
                     + chunk("imod", imod_recs) + chunk("igen", igen_recs)
                     + chunk("shdr", shdr_recs))
        pdta = b"LIST" + struct.pack("<I", len(pdta_body)) + pdta_body

        info_body = (b"INFO" + chunk("ifil", struct.pack("<HH", 2, 1))
                     + chunk("isng", b"EMU8000\0")
                     + chunk("INAM", self.name.encode() + b"\0"))
        info = b"LIST" + struct.pack("<I", len(info_body)) + info_body

        body = b"sfbk" + pad(info) + pad(sdta) + pad(pdta)
        return b"RIFF" + struct.pack("<I", len(body)) + body


# ---------------------------------------------------------------- build the font
def build_chip():
    sf = SF2("Chip Pocket")

    # looped waves — rate chosen so one looped cycle plays concert pitch at key 60:
    # rate = per_cycle_cycles_len... we use 32 cycles * 256 = 8192 samples; want C4=261.63Hz:
    #   freq = rate/8192 for key60 when looped across whole sample
    LEN = 32 * 256
    RATE_LOOP = int(round(261.625565 * LEN))  # ~2.1MHz — synth resamples fine
    w_sq50 = sf.add_sample("sq50", pulse_wave(.50), True, RATE_LOOP, 60)
    w_sq25 = sf.add_sample("sq25", pulse_wave(.25), True, RATE_LOOP, 60)
    w_sq12 = sf.add_sample("sq125", pulse_wave(.125), True, RATE_LOOP, 60)
    w_tri = sf.add_sample("tri", tri_wave(), True, RATE_LOOP, 60)
    w_saw = sf.add_sample("saw", saw_wave(), True, RATE_LOOP, 60)
    w_sin = sf.add_sample("sine", sine_wave(), True, RATE_LOOP, 60)
    w_noise = sf.add_sample("noise_loop", noise_hit(1.0, .01, bright=True), True, SR, 60)

    # drums
    d_kick = sf.add_sample("kick", sine_thump(.3, 170, 42), False)
    d_snare = sf.add_sample("snare", noise_hit(.22, 5.0, True), False)
    d_chat = sf.add_sample("chat", noise_hit(.05, 6.0, True), False)
    d_ohat = sf.add_sample("ohat", noise_hit(.3, 3.5, True), False)
    d_tomh = sf.add_sample("tomh", blip(660, 220, .09), False)
    d_tomm = sf.add_sample("tomm", blip(440, 160, .12), False)
    d_toml = sf.add_sample("toml", blip(300, 90, .18), False)
    d_crash = sf.add_sample("crash", noise_hit(1.4, 1.6, True), False)
    d_clap = sf.add_sample("clap", noise_hit(.15, 5.0, True), False)
    d_ride = sf.add_sample("ride", noise_hit(.7, 2.5, True), False)

    # helper: zone tuple
    def Z(sidx, klo=0, khi=127, att=None, dec=None, sus=None, rel=None,
          pan=None, rootkey=None, modes=1, scaletune=100, vlo=0, vhi=0):
        return (klo, khi, vlo, vhi, sidx, att, dec, sus, rel, pan, rootkey,
                modes, scaletune)

    ATT = tc(.001)
    REL_FAST = tc(.25)
    REL_MED = tc(.5)
    REL_SLOW = tc(1.2)
    DEC_MED = tc(.4)
    SUS_MED = 350   # sustainVolEnv in 0.1% units: 350 = ~ -10dB-ish plateau? (centibels of attenuation at sustain)

    # GM program families -> (waveform, env character)
    FAM = {
        "piano":   (w_sq25, ATT, tc(.9), 300, REL_MED),
        "chrom":   (w_sq50, ATT, tc(.5), 400, REL_FAST),
        "organ":   (w_sq50, ATT, tc(8.0), 0, REL_FAST),
        "guitar":  (w_sq25, ATT, tc(.7), 350, REL_FAST),
        "bass":    (w_tri, ATT, tc(1.5), 200, REL_MED),
        "strings": (w_sq12, tc(.08), tc(4.0), 100, REL_SLOW),
        "ens":     (w_sq50, tc(.05), tc(5.0), 80, REL_SLOW),
        "brass":   (w_saw, ATT, tc(2.5), 150, REL_MED),
        "reed":    (w_sq25, ATT, tc(3.0), 120, REL_MED),
        "pipe":    (w_tri, ATT, tc(4.0), 60, REL_MED),
        "lead":    (w_saw, ATT, tc(6.0), 0, REL_FAST),
        "pad":     (w_sin, tc(.3), tc(8.0), 40, REL_SLOW),
        "fx":      (w_noise, ATT, tc(4.0), 150, REL_MED),
        "ethnic":  (w_sq25, ATT, tc(1.2), 200, REL_MED),
        "perc":    (w_sq50, ATT, tc(.35), 450, REL_FAST),
        "sfx":     (w_noise, ATT, tc(6.0), 0, REL_MED),
    }
    GM_MAP = {  # program ranges -> family
        range(0, 8): "piano", range(8, 16): "chrom", range(16, 24): "organ",
        range(24, 32): "guitar", range(32, 40): "bass", range(40, 48): "strings",
        range(48, 56): "ens", range(56, 64): "brass", range(64, 72): "reed",
        range(72, 80): "pipe", range(80, 88): "lead", range(88, 96): "pad",
        range(96, 104): "fx", range(104, 112): "ethnic",
        range(112, 120): "perc", range(120, 128): "sfx",
    }
    GM_NAMES = [
        "Piano","BritePno","EPiano","HnkyTnk","EP1","EP2","Harpsi","Clav",
        "Celesta","Glocken","MusicBox","Vibes","Marimba","Xylo","TubBells","Dulcimer",
        "Drawbar","PercOrgn","RockOrgn","ChurchOr","ReedOrgn","Accordion","Harmonica","Tango",
        "NylonGtr","SteelGtr","JazzGtr","CleanGtr","MuteGtr","OvrdrvGtr","DistGtr","GtrHarm",
        "AcstcBass","FngrBass","PickBass","Fretless","Slap1","Slap2","SynBass1","SynBass2",
        "Violin","Viola","Cello","Contra","TremStr","PizzStr","Harp","Timpani",
        "StrEns1","StrEns2","SynStr1","SynStr2","ChoirAah","ChoirOoh","SynVoice","OrchHit",
        "Trumpet","Trombone","Tuba","MuteTpt","FrHorn","BrassSec","SynBrass1","SynBrass2",
        "SopSax","AltoSax","TenorSax","BariSax","Oboe","EngHorn","Bassoon","Clarinet",
        "Piccolo","Flute","Recorder","PanFlute","BlownBtl","Shakuhachi","Whistle","Ocarina",
        "SqLead","SawLead","Caliope","Chiff","Charang","VoiceLd","Fifths","BassLead",
        "NewAgePad","WarmPad","PolyPad","ChoirPad","BowedPad","MetalPad","HaloPad","SweepPad",
        "Rain","Soundtrk","Crystal","Atmosphr","Bright","Goblins","Echoes","SciFi",
        "Sitar","Banjo","Shamisen","Koto","Kalimba","Bagpipe","Fiddle","Shanai",
        "Tinkle","Agogo","SteelDrm","Woodblk","Taiko","MeloTom","SynDrum","RevCym",
        "GtrFret","Breath","Seashore","Bird","Phone","Helicptr","Applause","Gunshot",
    ]

    for prog in range(128):
        fam = next(GM_MAP[r] for r in GM_MAP if prog in r)
        wave, att, dec, sus, rel = FAM[fam]
        inst = sf.add_inst(GM_NAMES[prog], [Z(wave, att=att, dec=dec, sus=sus, rel=rel)])
        sf.add_preset(0, prog, GM_NAMES[prog], inst)

    # ---- drum kit (bank 128, preset 0 = standard kit)
    drum_zones = []
    KEY_MAP = {}
    def kit(klo, khi, sidx):
        KEY_MAP[(klo, khi)] = sidx
    kit(35, 36, d_kick); kit(37, 37, d_clap); kit(38, 40, d_snare)
    kit(41, 43, d_toml); kit(44, 44, d_chat); kit(45, 45, d_toml)
    kit(46, 46, d_ohat); kit(47, 48, d_tomm); kit(49, 49, d_crash)
    kit(50, 50, d_tomh); kit(51, 51, d_ride); kit(52, 52, d_crash)
    kit(53, 57, d_ride); kit(58, 69, d_chat); kit(70, 81, d_snare)
    for (klo, khi), sidx in sorted(KEY_MAP.items()):
        drum_zones.append(Z(sidx, klo=klo, khi=khi, att=ATT, dec=tc(2.5), sus=0,
                            rel=tc(.3), modes=0, scaletune=0, rootkey=60))
    inst = sf.add_inst("ChipKit", drum_zones)
    sf.add_preset(128, 0, "Standard Kit", inst)

    return sf.build()


def main():
    out = Path(sys.argv[1] if len(sys.argv) > 1 else
               "site/library/soundfonts/chippocket.sf2")
    data = build_chip()
    out.write_bytes(data)
    print(f"wrote {out} ({len(data)/1e6:.1f} MB)")


if __name__ == "__main__":
    main()
