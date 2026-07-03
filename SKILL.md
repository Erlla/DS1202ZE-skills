---
name: ds1202ze
description: Control and read RIGOL DS1202Z-E / DS1000Z-E oscilloscopes over USBTMC/VISA using SCPI. Use when an agent or user needs to discover a connected DS1202ZE, distinguish it from a RIGOL DM3058/DM3058E multimeter on another USB port, query *IDN?, capture waveform CSV/JSON data, capture screenshots, configure channels/timebase/trigger, run/stop/single/autoscale acquisition, or send raw oscilloscope SCPI commands.
---

# RIGOL DS1202Z-E

Use this package for RIGOL DS1202Z-E oscilloscope work over USB. The bundled CLI prefers the DS1202Z-E/DS1000Z-E by `*IDN?` and USB PID, and explicitly down-ranks or rejects DM3058/DM3058E multimeters so a second RIGOL USB instrument is not selected by accident.

On Windows, the CLI can use the IVI USBTMC class driver directly with `--backend native`; a full VISA runtime is optional. PyVISA is supported when NI-VISA, Keysight VISA, RIGOL UltraSigma, or another backend is installed.

## Quick Start

Run the bundled script from this package:

```powershell
py "$env:USERPROFILE\.codex\skills\ds1202ze\scripts\ds1202ze.py" scan --probe
py "$env:USERPROFILE\.codex\skills\ds1202ze\scripts\ds1202ze.py" idn
py "$env:USERPROFILE\.codex\skills\ds1202ze\scripts\ds1202ze.py" status --json
py "$env:USERPROFILE\.codex\skills\ds1202ze\scripts\ds1202ze.py" waveform CHAN1 "$PWD\ch1.csv"
py "$env:USERPROFILE\.codex\skills\ds1202ze\scripts\ds1202ze.py" screenshot "$PWD\scope.png"
```

If `pyvisa` is missing and native USBTMC is not available, install it with:

```powershell
py -m pip install --user pyvisa
```

Use `--resource "<VISA resource>"` when multiple scopes are connected. Prefer DS1000Z-E resources like `USB0::0x1AB1::0x0517::<serial>::INSTR` or `USB0::0x1AB1::0x04CE::<serial>::INSTR`, depending on firmware/USB descriptor. DM3058E resources such as `USB0::0x1AB1::0x09C4::<serial>::INSTR` are the multimeter and should not be used with this oscilloscope helper.

## Workflow

1. Discover instruments with `scan --probe`. Confirm the selected identity includes `RIGOL` and `DS1202Z-E` or another DS1000Z-E/DS1000Z oscilloscope model. If the scan also shows `DM3058`, control that instrument with a DM3058E-specific tool instead.
2. Query identity and state with `idn` and `status --json`.
3. For display waveform data, use `waveform CHAN1 out.csv`. This reads normal screen waveform data and does not stop acquisition.
4. For deep memory, use `waveform CHAN1 out.csv --mode raw --points N --run-after`. RAW mode stops acquisition unless `--no-stop` is supplied.
5. For front-panel-equivalent control, use `run`, `stop`, `single`, `autoscale`, `channel`, `timebase`, `trigger edge`, and `measure`.
6. For unsupported operations, use `query "<SCPI?>"` and `write "<SCPI>"`, then check `errors`.

## Common Commands

```powershell
py "$env:USERPROFILE\.codex\skills\ds1202ze\scripts\ds1202ze.py" channel 1 --display on --scale 0.5 --offset 0 --coupling DC --probe 10
py "$env:USERPROFILE\.codex\skills\ds1202ze\scripts\ds1202ze.py" timebase --scale 0.001 --offset 0
py "$env:USERPROFILE\.codex\skills\ds1202ze\scripts\ds1202ze.py" trigger edge --source CHAN1 --slope POS --level 1.2 --sweep AUTO
py "$env:USERPROFILE\.codex\skills\ds1202ze\scripts\ds1202ze.py" measure freq --source CHAN1
py "$env:USERPROFILE\.codex\skills\ds1202ze\scripts\ds1202ze.py" query ":WAV:PRE?"
py "$env:USERPROFILE\.codex\skills\ds1202ze\scripts\ds1202ze.py" errors
```

Use `reset --yes` only when the user clearly wants to reset the oscilloscope.

## Notes

- Do not run multiple commands against the same oscilloscope in parallel. SCPI instruments have one output queue, and overlapping queries can corrupt responses.
- `waveform` uses `:WAV:SOUR`, `:WAV:MODE`, `:WAV:FORM BYTE`, `:WAV:PRE?`, and `:WAV:DATA?`, then converts BYTE samples to volts using the waveform preamble.
- DS1202Z-E has two analog channels. The helper accepts `CHAN1`, `CH1`, `1`, `CHAN2`, `CH2`, `2`, and `MATH`.
- RAW waveform mode reads internal memory in chunks because DS1000Z-E BYTE waveform transfers are limited per `:WAV:DATA?` request.
- For detailed SCPI reminders, read `references/scpi-cheatsheet.md`.
