# RIGOL DS1202Z-E USBTMC Control Toolkit

[中文说明](README.zh-CN.md) | English

This repository contains a deterministic Python CLI helper and an optional agent skill package for controlling a RIGOL DS1202Z-E / DS1000Z-E oscilloscope over USBTMC/VISA with SCPI.

The project is not limited to Codex. You can use `scripts/ds1202ze.py` directly from a terminal, integrate it into automation scripts, or install the repository as a Codex-compatible skill for agent-assisted workflows.

The helper was designed for a bench where two RIGOL USB instruments are connected at the same time:

- A RIGOL DS1202Z-E oscilloscope, the target instrument.
- A RIGOL DM3058/DM3058E multimeter, which must be ignored by this oscilloscope tool.

The CLI probes `*IDN?`, scores USB descriptors, selects the oscilloscope, and explicitly marks the DM3058E as ignored so commands are not sent to the wrong instrument.

![Captured DS1202Z-E screen](ds1202ze_ch1_100ms_1v.png)

## Features

- Discover connected USBTMC/VISA instruments with `scan --probe`.
- Automatically select the DS1202Z-E / DS1000Z-E scope and avoid the DM3058E multimeter.
- Query identity, trigger state, timebase, channel settings, memory depth, and SCPI error status.
- Configure CH1/CH2 display, volts-per-division, offset, coupling, probe ratio, and bandwidth limit.
- Configure the main timebase scale and horizontal offset.
- Configure edge trigger source, slope, level, and sweep mode.
- Control acquisition with `run`, `stop`, `single`, `clear`, and `autoscale`.
- Capture waveform data from CHAN1, CHAN2, or MATH to CSV or JSON.
- Capture display screenshots to PNG or BMP.
- Send raw SCPI queries and writes for operations not wrapped by high-level commands.
- Work on Windows without PyVISA by using the IVI USBTMC class driver directly.

## Repository Layout

```text
.
├── SKILL.md                         # Agent skill metadata and usage workflow
├── README.md                        # English README
├── README.zh-CN.md                  # Chinese README
├── agents/
│   └── openai.yaml                  # Optional Codex/OpenAI UI metadata
├── references/
│   └── scpi-cheatsheet.md           # DS1202Z-E / DS1000Z-E SCPI quick reference
├── scripts/
│   └── ds1202ze.py                  # USBTMC/VISA CLI helper
└── ds1202ze_ch1_100ms_1v.png        # Example screenshot captured from the scope
```

## Supported Instruments

| Instrument | Typical identity | USB VID:PID | Behavior |
| --- | --- | --- | --- |
| RIGOL DS1202Z-E | `RIGOL TECHNOLOGIES,DS1202Z-E,...` | `0x1AB1:0x0517` on the tested unit, `0x1AB1:0x04CE` in some DS1000Z-E examples | Selected as the target scope |
| RIGOL DS1000Z / DS1000Z-E family | `RIGOL ... DS1xxxZ...` | RIGOL USBTMC descriptors | Treated as a likely compatible scope |
| RIGOL DM3058/DM3058E | `Rigol Technologies,DM3058E,...` | `0x1AB1:0x09C4` | Explicitly ignored |

## Requirements

- Python 3.11 or newer.
- A DS1202Z-E / DS1000Z-E connected over USB and visible as a USB Test and Measurement Device.
- On Windows:
  - The IVI USBTMC class driver is enough for the default native backend.
  - PyVISA is optional.
- On non-Windows systems:
  - Install PyVISA and a working VISA backend such as NI-VISA, Keysight IO Libraries, RIGOL UltraSigma/UltraScope VISA, or another backend suitable for USBTMC.

Optional PyVISA install:

```powershell
py -m pip install --user pyvisa
```

## Installation

For direct CLI use, clone the repository anywhere you keep instrument tools:

```powershell
git clone https://github.com/<your-account>/ds1202ze.git
cd ds1202ze
py .\scripts\ds1202ze.py scan --probe
```

To install it as a Codex-compatible skill, clone the repository into the Codex skills directory.

Windows PowerShell:

```powershell
New-Item -ItemType Directory -Force "$env:USERPROFILE\.codex\skills" | Out-Null
git clone https://github.com/<your-account>/ds1202ze.git "$env:USERPROFILE\.codex\skills\ds1202ze"
```

macOS or Linux:

```bash
mkdir -p "$HOME/.codex/skills"
git clone https://github.com/<your-account>/ds1202ze.git "$HOME/.codex/skills/ds1202ze"
```

After optional Codex installation, ask Codex to use `$ds1202ze`. Without Codex, run the CLI directly from the cloned repository.

## Quick Start

From a cloned repository:

```powershell
py .\scripts\ds1202ze.py scan --probe
py .\scripts\ds1202ze.py idn
py .\scripts\ds1202ze.py status --json
py .\scripts\ds1202ze.py waveform CHAN1 "$PWD\ch1.csv"
py .\scripts\ds1202ze.py screenshot "$PWD\scope.png"
```

If installed under Codex skills:

```powershell
py "$env:USERPROFILE\.codex\skills\ds1202ze\scripts\ds1202ze.py" scan --probe
```

## Example Scan Output

This is the expected behavior when both the oscilloscope and the DM3058E multimeter are connected:

```text
VISA resources:
  <pyvisa unavailable: pyvisa is not installed. Install it with:>
Windows native USBTMC paths:
  \\?\usb#vid_1ab1&pid_0517#scope-serial#{...}  idn=RIGOL TECHNOLOGIES,DS1202Z-E,<scope-serial>,00.06.04  <target DS1202Z-E>
  \\?\usb#vid_1ab1&pid_09c4#meter-serial#{...}  idn=Rigol Technologies,DM3058E,<meter-serial>,01.01.00.02.03.01  <DM3058E multimeter, ignored>
```

If more than one compatible oscilloscope is connected, pass `--resource` explicitly.

## Common Workflows

### Set CH1 to 1 V/div and timebase to 100 ms/div

```powershell
py .\scripts\ds1202ze.py timebase --scale 0.1
py .\scripts\ds1202ze.py channel 1 --scale 1
py .\scripts\ds1202ze.py screenshot .\scope_100ms_1v.png
```

### Configure CH1

```powershell
py .\scripts\ds1202ze.py channel 1 --display on --scale 0.5 --offset 0 --coupling DC --probe 10
```

### Configure the main timebase

```powershell
py .\scripts\ds1202ze.py timebase --scale 0.001 --offset 0
```

`--scale` is seconds per division. For example, `0.1` means 100 ms/div.

### Configure edge trigger

```powershell
py .\scripts\ds1202ze.py trigger edge --source CHAN1 --slope POS --level 1.2 --sweep AUTO
```

### Capture waveform data

Screen waveform data:

```powershell
py .\scripts\ds1202ze.py waveform CHAN1 .\ch1.csv
```

JSON output:

```powershell
py .\scripts\ds1202ze.py waveform CHAN1 .\ch1.json --output-format json
```

Deep memory RAW capture:

```powershell
py .\scripts\ds1202ze.py waveform CHAN1 .\ch1_raw.csv --mode RAW --points 250000 --run-after
```

RAW mode stops acquisition unless `--no-stop` is supplied. Use `--run-after` to resume acquisition after capture.

### Capture a screenshot

```powershell
py .\scripts\ds1202ze.py screenshot .\scope.png
```

### Read measurements

```powershell
py .\scripts\ds1202ze.py measure freq --source CHAN1
py .\scripts\ds1202ze.py measure vpp --source CHAN1
py .\scripts\ds1202ze.py measure vrms --source CHAN2 --json
```

### Send raw SCPI

```powershell
py .\scripts\ds1202ze.py query ":WAV:PRE?"
py .\scripts\ds1202ze.py write ":CHAN1:DISP ON" --check-error
py .\scripts\ds1202ze.py errors
```

## CLI Reference

Global options:

| Option | Purpose |
| --- | --- |
| `--resource RESOURCE` | Select a VISA resource or native USBTMC path explicitly. Use the DS1202Z-E resource, not the DM3058E resource. |
| `--backend BACKEND` | Select a PyVISA backend such as `@ivi` or `@py`; use `native` for Windows USBTMC. |
| `--timeout-ms N` | Set I/O timeout in milliseconds. Default is `8000`. |
| `--max-read-bytes N` | Set maximum binary read size. Default is `5000000`. |

Subcommands:

| Command | Purpose |
| --- | --- |
| `scan --probe` | List VISA resources, Windows native USBTMC paths, PnP matches, and optional `*IDN?` results. |
| `idn` | Query `*IDN?`. |
| `status --json` | Show identity, trigger state, timebase, channel state, and SCPI error status. |
| `run`, `stop`, `single`, `clear`, `autoscale` | Control acquisition and display state. |
| `channel` | Query or configure CH1/CH2. |
| `timebase` | Query or configure main timebase. |
| `trigger edge` | Configure edge trigger. |
| `measure` | Run `:MEASure:ITEM?` for common measurements. |
| `waveform` | Capture BYTE waveform data to CSV or JSON. |
| `screenshot` | Capture display image to PNG or BMP. |
| `query` | Send a raw SCPI query. |
| `write` | Send a raw SCPI command. |
| `errors` | Read the SCPI error queue. |
| `reset --yes` | Reset the scope with `*RST`. |

## Waveform Output Format

CSV output contains:

| Column | Meaning |
| --- | --- |
| `time_s` | Sample time in seconds. |
| `voltage_v` | Converted voltage in volts. |
| `raw` | Raw BYTE sample from the oscilloscope. |

The helper reads `:WAVeform:PREamble?` and converts BYTE data with:

```text
time_s = (sample_index - xreference) * xincrement + xorigin
voltage_v = (raw_byte - yorigin - yreference) * yincrement
```

## Safety Notes

- Do not run multiple commands against the same oscilloscope in parallel. SCPI instruments have a single output queue.
- Always verify `scan --probe` output before using `--resource`.
- Do not pass a DM3058E resource to this oscilloscope tool. The DM3058E resource usually contains `PID_09C4` or `0x09C4`.
- `reset` requires `--yes` intentionally because `*RST` changes front-panel state.
- RAW waveform capture may stop acquisition. Use `--run-after` when you want the scope to resume.

## Tested Configuration

Tested on 2026-07-03 with:

- Oscilloscope: `RIGOL TECHNOLOGIES,DS1202Z-E,<scope-serial>,00.06.04`
- Multimeter on the other USB port: `Rigol Technologies,DM3058E,<meter-serial>,01.01.00.02.03.01`
- Python: 3.11.15 and 3.14 available on Windows
- Transport: Windows native USBTMC through `USB Test and Measurement Device (IVI)`
- Verified operations:
  - `scan --probe`
  - `idn`
  - `status --json`
  - CH1 scale configuration
  - main timebase configuration
  - 1200-point CH1 waveform capture
  - PNG screenshot capture

## Troubleshooting

### `pyvisa is not installed`

On Windows, this is fine if native USBTMC is available. The helper will use native USBTMC automatically. To use a VISA backend explicitly, install PyVISA:

```powershell
py -m pip install --user pyvisa
```

### The DM3058E appears in the scan

That is expected when the multimeter is connected. The scan should mark it as:

```text
<DM3058E multimeter, ignored>
```

Do not pass its resource to `--resource`.

### No USBTMC device appears

Check that:

- The oscilloscope USB device port is connected to the PC.
- Windows Device Manager shows `USB Test and Measurement Device (IVI)`.
- The oscilloscope is powered on and not held by another control program.
- The USB cable is data-capable.

### Screenshot or waveform capture times out

Try a larger timeout:

```powershell
py .\scripts\ds1202ze.py --timeout-ms 20000 screenshot .\scope.png
```

For large RAW captures, reduce `--points` or let the helper chunk the transfer with `--chunk-points`.

## Publishing Checklist

Before publishing to GitHub:

- Confirm the repository contains `SKILL.md`, `scripts/ds1202ze.py`, `references/scpi-cheatsheet.md`, `agents/openai.yaml`, and this README.
- Avoid committing `__pycache__`, local logs, or private measurement data.
- Add a license file if the repository will be public.
- Run `python -m py_compile scripts/ds1202ze.py`.
- Run `python scripts/ds1202ze.py scan --probe` on a machine with the scope attached.

## References

- [RIGOL DS1000Z-E Programming Guide, Chinese official support mirror](https://supportcn.rigol.com/Public/Uploads/uploadfile/files/ftp/%E7%94%B5%E5%AD%90%E6%B5%8B%E9%87%8F%E4%BB%AA%E5%99%A8/%E7%A4%BA%E6%B3%A2%E5%99%A8/DS1000Z-E/%E4%B8%AD%E6%96%87%E6%89%8B%E5%86%8C/DS1000Z-E_ProgrammingGuide_CN.pdf)
- [RIGOL MSO1000Z/DS1000Z Programming Guide mirror](https://www.batronix.com/files/Rigol/Oszilloskope/_DS%26MSO1000Z/MSO_DS1000Z_ProgrammingGuide_EN.pdf)

## License

Add a license before publishing this repository publicly. MIT is a common choice for small helper scripts, but choose the license that matches your intended use.
