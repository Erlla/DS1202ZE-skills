<div align="center">

[简体中文](./README.md) | English

# RIGOL DS1202Z-E Skill

**Let AI coding assistants with Skill / Agent extension support, or regular automation scripts, read and control RIGOL DS1202Z-E / DS1000Z-E oscilloscopes directly over USB.**

![Status](https://img.shields.io/badge/status-hardware%20tested-success?style=flat-square)
![Python](https://img.shields.io/badge/Python-3.x-blue?style=flat-square)
![Transport](https://img.shields.io/badge/transport-USBTMC%20%7C%20VISA-4c8eda?style=flat-square)
![Platform](https://img.shields.io/badge/platform-Windows%20native%20%7C%20VISA-lightgrey?style=flat-square)

</div>

---

## Overview

`ds1202ze` is a general-purpose instrument-control Skill for RIGOL DS1202Z-E / DS1000Z-E oscilloscopes. It packages common oscilloscope tasks into an AI-readable workflow and a Python CLI, so AI coding assistants with Skill, Agent extension, or project-rule support can discover the instrument, query identity, configure channels, set the timebase, configure triggers, capture waveforms, save screenshots, and send raw SCPI commands.

This project is not tied to a single AI tool. Its core behavior lives in `SKILL.md`, `scripts/ds1202ze.py`, and `references/scpi-cheatsheet.md`, so it can be reused by Codex, Claude Code, Cursor, TRAE, Kiro, Windsurf, or any other tool with a similar Skill/Rules/Agent instruction mechanism. If you do not need Skill invocation, `scripts/ds1202ze.py` can also be used directly as a standalone CLI.

The main design goal is reliable hardware access. On Windows, the CLI defaults to the native IVI USBTMC class-driver device path and does not require a full NI-VISA or Keysight VISA installation. If a VISA runtime is available, PyVISA backends are also supported.

The project also handles a common mixed-RIGOL bench setup: the target is the DS1202Z-E oscilloscope, while a connected DM3058/DM3058E multimeter is detected and explicitly ignored so oscilloscope SCPI commands are not sent to the wrong instrument.

Hardware-tested identities:

```text
RIGOL TECHNOLOGIES,DS1202Z-E,<scope-serial>,<firmware-version>
Rigol Technologies,DM3058E,<meter-serial>,<firmware-version>  # ignored
```

## Features

- Discover USBTMC/VISA devices and identify the DS1202Z-E / DS1000Z-E.
- Avoid selecting a connected DM3058/DM3058E multimeter.
- Query `*IDN?`, trigger state, channel state, timebase, memory depth, and SCPI error queue.
- Configure CH1/CH2 display, vertical scale, offset, coupling, probe ratio, and bandwidth limit.
- Configure main timebase scale and horizontal offset.
- Configure edge trigger source, slope, level, and sweep mode.
- Control acquisition with `run`, `stop`, `single`, `clear`, and `autoscale`.
- Capture CHAN1, CHAN2, or MATH waveforms as CSV or JSON.
- Capture oscilloscope screenshots as PNG or BMP.
- Read common measurement items such as frequency, period, Vpp, RMS, maximum, and minimum.
- Send raw SCPI `query` / `write` commands for advanced use.
- Use Windows native USBTMC through `--backend native`.
- Use PyVISA backends such as `@ivi` and `@py`.

## Directory Layout

```text
ds1202ze/
├── README.md
├── README.en.md
├── SKILL.md
├── agents/
│   └── openai.yaml
├── references/
│   └── scpi-cheatsheet.md
├── scripts/
│   └── ds1202ze.py
└── ds1202ze_ch1_100ms_1v.png
```

## Requirements

### Basic Requirements

| Item | Requirement |
|---|---|
| Instrument | RIGOL DS1202Z-E or compatible DS1000Z/DS1000Z-E oscilloscope |
| Connection | USB, shown as `USB Test and Measurement Device (IVI)` |
| Python | Python 3.x |
| OS | Windows native USBTMC is hardware-tested; other systems should use VISA/PyVISA |

### Windows Native Backend

Recommended default on Windows:

```powershell
py scripts\ds1202ze.py idn
py scripts\ds1202ze.py status --json
```

The script enumerates the IVI USBTMC class GUID:

```text
{A9FDBB24-128A-11D5-9961-00108335E361}
```

When a DS1202Z-E is found, the script communicates through the Windows device path directly. A full VISA runtime is not required.

### PyVISA Backend

If you want to use standard VISA resource strings, install PyVISA:

```powershell
py -m pip install --user pyvisa
```

Then use an installed VISA runtime:

```powershell
py scripts\ds1202ze.py --backend @ivi scan --probe
py scripts\ds1202ze.py --backend @ivi --resource "USB0::0x1AB1::0x0517::<serial>::INSTR" idn
```

If your system only has the IVI shared `visa64.dll` / `visa32.dll` router but no NI-VISA, Keysight IO Libraries, or RIGOL UltraSigma VISA backend, PyVISA may report `VI_ERROR_LIBRARY_NFOUND`. In that case, use the default Windows native backend.

## Installation

### Method 1: Install as an AI Skill

Clone the repository into the skills directory used by your AI tool. For Codex, for example:

```powershell
git clone https://github.com/Erlla/DS1202ZE-skills.git "$env:USERPROFILE\.codex\skills\ds1202ze"
```

Then ask an AI assistant with Skill support:

```text
Use $ds1202ze to capture a CH1 waveform and save a screenshot.
```

Chinese prompts work too:

```text
调用 DS1202Z-E skill，把 CH1 调到 1V/div，时基调到 100ms/div，然后抓取屏幕。
```

### Method 2: Manual Copy to a Tool-Specific Directory

Copy the whole `ds1202ze/` directory to the Skill directory used by your AI tool. Codex's default global directory example:

```text
C:\Users\<your-user-name>\.codex\skills\ds1202ze
```

Keep the `SKILL.md`, `scripts/`, and `references/` structure intact. `agents/openai.yaml` is OpenAI/Codex-specific UI metadata and can be ignored by other tools.

### Method 3: Use the CLI Only

If you do not need Skill invocation, run the script directly:

```powershell
py scripts\ds1202ze.py scan --probe
py scripts\ds1202ze.py status --json
```

## Quick Start

### 1. Scan the Instrument

```powershell
py scripts\ds1202ze.py scan --probe
```

Example output:

```text
VISA resources:
  <pyvisa unavailable: Unable to create a VISA ResourceManager...>
Windows native USBTMC paths:
  \\?\usb#vid_1ab1&pid_0517#scope-serial#{a9fdbb24-128a-11d5-9961-00108335e361}
  idn=RIGOL TECHNOLOGIES,DS1202Z-E,<scope-serial>,<firmware-version>  <target DS1202Z-E>
  \\?\usb#vid_1ab1&pid_09c4#meter-serial#{a9fdbb24-128a-11d5-9961-00108335e361}
  idn=Rigol Technologies,DM3058E,<meter-serial>,<firmware-version>  <DM3058E multimeter, ignored>
Windows PnP matches:
  OK USBTestAndMeasurementDevice USB Test and Measurement Device (IVI) USB\VID_1AB1&PID_0517\<scope-serial>
```

### 2. Query Identity

```powershell
py scripts\ds1202ze.py idn
```

Example output:

```text
RIGOL TECHNOLOGIES,DS1202Z-E,<scope-serial>,<firmware-version>
```

### 3. Show Scope Status

```powershell
py scripts\ds1202ze.py status --json
```

### 4. Configure CH1 and Timebase

```powershell
py scripts\ds1202ze.py channel 1 --scale 1 --display on
py scripts\ds1202ze.py timebase --scale 0.1
```

Here, `--scale 0.1` means 100 ms/div.

### 5. Capture Waveform and Screenshot

```powershell
py scripts\ds1202ze.py waveform CHAN1 ch1.csv
py scripts\ds1202ze.py screenshot scope.png
```

## Subcommands

| Subcommand | Purpose | Example |
|---|---|---|
| `scan` | Scan VISA and Windows native USBTMC devices | `py scripts\ds1202ze.py scan --probe` |
| `idn` | Query `*IDN?` | `py scripts\ds1202ze.py idn` |
| `status` | Print identity, trigger, timebase, channel, and error state | `py scripts\ds1202ze.py status --json` |
| `run` | Start continuous acquisition | `py scripts\ds1202ze.py run` |
| `stop` | Stop acquisition | `py scripts\ds1202ze.py stop` |
| `single` | Run single acquisition | `py scripts\ds1202ze.py single` |
| `clear` | Clear the display | `py scripts\ds1202ze.py clear` |
| `autoscale` | Autoscale the scope | `py scripts\ds1202ze.py autoscale` |
| `channel` | Query or configure CH1/CH2 | `py scripts\ds1202ze.py channel 1 --scale 1` |
| `timebase` | Query or configure main timebase | `py scripts\ds1202ze.py timebase --scale 0.001` |
| `trigger edge` | Configure edge trigger | `py scripts\ds1202ze.py trigger edge --source CHAN1 --level 1.2` |
| `measure` | Read common measurement items | `py scripts\ds1202ze.py measure freq --source CHAN1` |
| `waveform` | Capture BYTE waveform data to CSV or JSON | `py scripts\ds1202ze.py waveform CHAN1 ch1.csv` |
| `screenshot` | Capture display image to PNG or BMP | `py scripts\ds1202ze.py screenshot scope.png` |
| `query` | Send a raw SCPI query | `py scripts\ds1202ze.py query ":WAV:PRE?"` |
| `write` | Send a raw SCPI command | `py scripts\ds1202ze.py write "*CLS" --check-error` |
| `errors` | Read the SCPI error queue | `py scripts\ds1202ze.py errors` |
| `reset` | Run `*RST`; explicit confirmation required | `py scripts\ds1202ze.py reset --yes` |

## Common Examples

### Set CH1 to 1 V/div and Timebase to 100 ms/div

```powershell
py scripts\ds1202ze.py timebase --scale 0.1
py scripts\ds1202ze.py channel 1 --scale 1
py scripts\ds1202ze.py screenshot scope_100ms_1v.png
```

### Configure CH1 Probe, Coupling, and Offset

```powershell
py scripts\ds1202ze.py channel 1 --display on --scale 0.5 --offset 0 --coupling DC --probe 10
```

### Configure Edge Trigger

```powershell
py scripts\ds1202ze.py trigger edge --source CHAN1 --slope POS --level 1.2 --sweep AUTO
```

### Capture Screen Waveform to CSV

```powershell
py scripts\ds1202ze.py waveform CHAN1 ch1.csv
```

CSV output contains `time_s`, `voltage_v`, and `raw`.

### Capture Waveform to JSON

```powershell
py scripts\ds1202ze.py waveform CHAN1 ch1.json --output-format json
```

### Deep-Memory RAW Capture

```powershell
py scripts\ds1202ze.py waveform CHAN1 ch1_raw.csv --mode RAW --points 250000 --run-after
```

RAW mode stops acquisition unless `--no-stop` is supplied. Use `--run-after` to resume acquisition after capture.

### Capture a Screenshot

```powershell
py scripts\ds1202ze.py screenshot scope.png
```

### Read Measurements

```powershell
py scripts\ds1202ze.py measure freq --source CHAN1
py scripts\ds1202ze.py measure vpp --source CHAN1
py scripts\ds1202ze.py measure vrms --source CHAN2 --json
```

### Send Raw SCPI

```powershell
py scripts\ds1202ze.py query ":SYSTem:ERRor?"
py scripts\ds1202ze.py query ":WAVeform:PREamble?"
py scripts\ds1202ze.py write ":CHANnel1:DISPlay ON" --check-error
```

## Waveform Data Format

The script uses:

```text
:WAVeform:SOURce
:WAVeform:MODE
:WAVeform:FORMat BYTE
:WAVeform:PREamble?
:WAVeform:DATA?
```

It converts BYTE data using the values returned by `:WAVeform:PREamble?`:

```text
time_s = (sample_index - xreference) * xincrement + xorigin
voltage_v = (raw_byte - yorigin - yreference) * yincrement
```

In RAW deep-memory mode, the script reads data in chunks to avoid the DS1000Z/DS1000Z-E per-request `:WAVeform:DATA?` transfer limits.

## AI Usage

Once installed as a Skill, Agent extension, or project rule, the assistant reads `SKILL.md` and calls `scripts/ds1202ze.py` when relevant. Installation directories differ between AI tools, but the core usage pattern is the same.

Example prompts:

```text
调用 DS1202Z-E skill，扫描 USB 并确认示波器身份。
```

```text
Use $ds1202ze to capture a CH1 waveform as CSV and a screenshot as PNG.
```

```text
使用 DS1202Z-E skill，把 CH1 设置为 1V/div，时基设置为 100ms/div，然后抓屏。
```

## Design Notes

### Windows Native USBTMC

On Windows, the DS1202Z-E usually appears in Device Manager as:

```text
USB Test and Measurement Device (IVI)
```

The script enumerates USBTMC device interfaces with SetupAPI and sends USBTMC bulk messages through Win32 `CreateFile` / `WriteFile` / `ReadFile`. This path does not depend on PyVISA or a full NI-VISA runtime.

### PyVISA

If NI-VISA, Keysight IO Libraries Suite, or RIGOL UltraSigma VISA is installed, use:

```powershell
py scripts\ds1202ze.py --backend @ivi scan --probe
```

You can also pass an explicit resource:

```powershell
py scripts\ds1202ze.py --resource "USB0::0x1AB1::0x0517::<serial>::INSTR" idn
```

### Multi-RIGOL Instrument Guard

The script selects the target oscilloscope using USB VID/PID, device path, and `*IDN?` results. DM3058/DM3058E multimeter resources are down-ranked or rejected to avoid wrong-device selection when both the oscilloscope and multimeter are connected.

## Notes and Safety

- Do not run multiple queries against the same scope in parallel. SCPI instruments have a single output queue, so overlapping commands can interleave responses.
- Run `scan --probe` before using `--resource` to confirm the target instrument.
- Do not pass a DM3058E resource to this oscilloscope tool. The DM3058E resource usually contains `PID_09C4` or `0x09C4`.
- `reset --yes` resets oscilloscope settings. Use it only when intended.
- `channel`, `timebase`, `trigger`, and `autoscale` commands change the current front-panel state.
- RAW waveform capture may stop acquisition; use `--run-after` when you want acquisition to resume.

## Troubleshooting

### Device Not Found

Run:

```powershell
py scripts\ds1202ze.py scan --probe
```

Confirm that the output contains the target oscilloscope, for example:

```text
RIGOL TECHNOLOGIES,DS1202Z-E,<scope-serial>,<firmware-version>
```

If not, check the USB cable, oscilloscope USB Device port, Windows Device Manager, and driver installation.

### DM3058E Appears in the Scan

This is expected when the multimeter is connected. It should be marked as:

```text
<DM3058E multimeter, ignored>
```

Do not pass its resource to `--resource`.

### PyVISA Reports `VI_ERROR_LIBRARY_NFOUND`

This usually means the system has only the IVI shared VISA router but no complete vendor VISA backend. Use the default command:

```powershell
py scripts\ds1202ze.py idn
```

Or explicitly use native:

```powershell
py scripts\ds1202ze.py --backend native idn
```

### Screenshot or Waveform Capture Times Out

Try a larger timeout:

```powershell
py scripts\ds1202ze.py --timeout-ms 20000 screenshot scope.png
```

For large RAW captures, reduce `--points` or let the helper chunk the transfer with `--chunk-points`.

### `QUERY INTERRUPTED`

This usually means overlapping queries or a stale response in the output queue. Clear status and retry:

```powershell
py scripts\ds1202ze.py write "*CLS" --check-error
py scripts\ds1202ze.py errors
```

## Development and Validation

Syntax check:

```powershell
py -m py_compile scripts\ds1202ze.py
```

Skill structure validation, when the Codex / OpenAI skill-creator tool is available:

```powershell
python "$env:USERPROFILE\.codex\skills\.system\skill-creator\scripts\quick_validate.py" .
```

Hardware smoke test:

```powershell
py scripts\ds1202ze.py scan --probe
py scripts\ds1202ze.py idn
py scripts\ds1202ze.py status --json
py scripts\ds1202ze.py waveform CHAN1 ch1.csv --points 1200
py scripts\ds1202ze.py screenshot scope.png
py scripts\ds1202ze.py errors
```

## References

- [RIGOL DS1000Z-E Programming Guide, Chinese official support mirror](https://supportcn.rigol.com/Public/Uploads/uploadfile/files/ftp/%E7%94%B5%E5%AD%90%E6%B5%8B%E9%87%8F%E4%BB%AA%E5%99%A8/%E7%A4%BA%E6%B3%A2%E5%99%A8/DS1000Z-E/%E4%B8%AD%E6%96%87%E6%89%8B%E5%86%8C/DS1000Z-E_ProgrammingGuide_CN.pdf)
- [RIGOL MSO1000Z/DS1000Z Programming Guide](https://www.batronix.com/files/Rigol/Oszilloskope/_DS%26MSO1000Z/MSO_DS1000Z_ProgrammingGuide_EN.pdf)
- [IVI-6.2 USBTMC Windows interoperability specification](https://www.ivifoundation.org/downloads/Architecture%20Specifications/Ivi-6%202_USBTMC_2018-11-01.pdf)

## License

Add a `LICENSE` file before publishing the repository. MIT License is a reasonable default if there are no project-specific restrictions.
