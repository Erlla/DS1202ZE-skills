<div align="center">

简体中文 | [English](./README.en.md)

# RIGOL DS1202Z-E Skill

**让支持 Skill / Agent 扩展的 AI 编码助手或自动化脚本通过 USB 直接读取和控制 RIGOL DS1202Z-E / DS1000Z-E 示波器。**

![Status](https://img.shields.io/badge/status-hardware%20tested-success?style=flat-square)
![Python](https://img.shields.io/badge/Python-3.x-blue?style=flat-square)
![Transport](https://img.shields.io/badge/transport-USBTMC%20%7C%20VISA-4c8eda?style=flat-square)
![Platform](https://img.shields.io/badge/platform-Windows%20native%20%7C%20VISA-lightgrey?style=flat-square)

</div>

---

## 项目简介

`ds1202ze` 是一个面向 RIGOL DS1202Z-E / DS1000Z-E 示波器的通用仪器控制 Skill。它把常见的示波器控制流程封装成 AI 可读的工作流和 Python CLI 工具，使支持 Skill、Agent 扩展或项目规则的 AI 编码助手可以完成设备发现、身份查询、通道配置、时基配置、触发设置、波形抓取、屏幕截图和原始 SCPI 命令发送。

这个项目并不绑定某一个 AI 工具。核心能力由 `SKILL.md`、`scripts/ds1202ze.py` 和 `references/scpi-cheatsheet.md` 组成，可被 Codex、Claude Code、Cursor、TRAE、Kiro、Windsurf 或其他支持类似 Skill/Rules/Agent 指令机制的工具复用；如果不需要 AI Skill 触发，也可以直接把 `scripts/ds1202ze.py` 当作独立 CLI 使用。

这个项目的重点是可靠地连接真实硬件。Windows 下脚本默认优先使用 IVI USBTMC class driver 暴露的原生设备路径，不要求安装完整 NI-VISA 或 Keysight VISA；如果系统已有 VISA runtime，也可以显式使用 PyVISA 后端。

本项目还特别处理了同一台电脑同时连接两台 RIGOL USB 仪器的场景：目标设备是 DS1202Z-E 示波器，另一台 DM3058/DM3058E 万用表会被识别并明确忽略，避免把示波器 SCPI 命令误发给万用表。

实机验证设备：

```text
RIGOL TECHNOLOGIES,DS1202Z-E,<scope-serial>,<firmware-version>
Rigol Technologies,DM3058E,<meter-serial>,<firmware-version>  # ignored
```

## 主要能力

- 扫描 USBTMC/VISA 设备并识别 DS1202Z-E / DS1000Z-E。
- 在连接 DM3058/DM3058E 万用表时自动避开万用表资源。
- 查询 `*IDN?`、触发状态、通道状态、时基、存储深度和错误队列。
- 配置 CH1/CH2 显示、垂直档位、偏移、耦合、探头倍率和带宽限制。
- 配置主时基档位和水平偏移。
- 配置边沿触发源、斜率、电平和触发扫描模式。
- 控制采集：`run`、`stop`、`single`、`clear` 和 `autoscale`。
- 从 CHAN1、CHAN2 或 MATH 抓取波形，输出 CSV 或 JSON。
- 抓取示波器屏幕，输出 PNG 或 BMP。
- 读取常用测量项，例如频率、周期、峰峰值、RMS、最大值和最小值。
- 发送任意原始 SCPI `query` / `write` 命令，便于扩展。
- 在 Windows 上通过 `--backend native` 直接使用 IVI USBTMC 驱动。
- 支持 PyVISA `@ivi`、`@py` 等后端。

## 目录结构

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

## 环境要求

### 基础要求

| 项目 | 要求 |
|---|---|
| 仪器 | RIGOL DS1202Z-E 或兼容的 DS1000Z/DS1000Z-E 系列示波器 |
| 连接 | USB，设备应显示为 `USB Test and Measurement Device (IVI)` |
| Python | Python 3.x |
| 系统 | Windows 原生 USBTMC 已实测；其他系统建议使用 VISA/PyVISA |

### Windows native 后端

Windows 下推荐默认后端：

```powershell
py scripts\ds1202ze.py idn
py scripts\ds1202ze.py status --json
```

脚本会自动枚举 IVI USBTMC class GUID：

```text
{A9FDBB24-128A-11D5-9961-00108335E361}
```

如果发现 DS1202Z-E，会直接通过 Windows 设备路径通信，不需要完整 VISA runtime。

### PyVISA 后端

如果你希望使用标准 VISA 资源字符串，安装 PyVISA：

```powershell
py -m pip install --user pyvisa
```

然后使用系统中的 VISA runtime：

```powershell
py scripts\ds1202ze.py --backend @ivi scan --probe
py scripts\ds1202ze.py --backend @ivi --resource "USB0::0x1AB1::0x0517::<serial>::INSTR" idn
```

如果只安装了 IVI shared `visa64.dll` / `visa32.dll` router，但没有 NI-VISA、Keysight IO Libraries 或 RIGOL UltraSigma VISA 后端，PyVISA 可能会报 `VI_ERROR_LIBRARY_NFOUND`。这种情况下直接使用默认 Windows native 后端即可。

## 安装

### 方法一：作为 AI Skill 安装

将仓库 clone 到你的 AI 工具所使用的 skills 目录。以 Codex 为例：

```powershell
git clone https://github.com/Erlla/DS1202ZE-skills.git "$env:USERPROFILE\.codex\skills\ds1202ze"
```

然后在支持 Skill 的 AI 工具中使用：

```text
Use $ds1202ze to capture a CH1 waveform and save a screenshot.
```

中文也可以直接说：

```text
调用 DS1202Z-E skill，把 CH1 调到 1V/div，时基调到 100ms/div，然后抓取屏幕。
```

### 方法二：手动复制到指定工具目录

将整个 `ds1202ze/` 目录复制到你的 AI 工具的 Skill 目录。Codex 的默认全局目录示例：

```text
C:\Users\<你的用户名>\.codex\skills\ds1202ze
```

保留 `SKILL.md`、`scripts/` 和 `references/` 目录结构。`agents/openai.yaml` 是 OpenAI/Codex 相关的界面元数据，其他工具可以忽略。

### 方法三：仅使用 CLI 脚本

如果不需要 Skill 触发，只想直接控制示波器：

```powershell
py scripts\ds1202ze.py scan --probe
py scripts\ds1202ze.py status --json
```

## 快速开始

### 1. 扫描设备

```powershell
py scripts\ds1202ze.py scan --probe
```

示例输出：

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

### 2. 查询身份

```powershell
py scripts\ds1202ze.py idn
```

示例输出：

```text
RIGOL TECHNOLOGIES,DS1202Z-E,<scope-serial>,<firmware-version>
```

### 3. 查看示波器状态

```powershell
py scripts\ds1202ze.py status --json
```

### 4. 设置 CH1 和时基

```powershell
py scripts\ds1202ze.py channel 1 --scale 1 --display on
py scripts\ds1202ze.py timebase --scale 0.1
```

其中 `--scale 0.1` 表示 100 ms/div。

### 5. 抓取波形和屏幕

```powershell
py scripts\ds1202ze.py waveform CHAN1 ch1.csv
py scripts\ds1202ze.py screenshot scope.png
```

## 子命令

| 子命令 | 用途 | 示例 |
|---|---|---|
| `scan` | 扫描 VISA 和 Windows native USBTMC 设备 | `py scripts\ds1202ze.py scan --probe` |
| `idn` | 查询 `*IDN?` | `py scripts\ds1202ze.py idn` |
| `status` | 输出身份、触发状态、时基、通道和错误状态 | `py scripts\ds1202ze.py status --json` |
| `run` | 开始连续采集 | `py scripts\ds1202ze.py run` |
| `stop` | 停止采集 | `py scripts\ds1202ze.py stop` |
| `single` | 执行单次采集 | `py scripts\ds1202ze.py single` |
| `clear` | 清屏 | `py scripts\ds1202ze.py clear` |
| `autoscale` | 自动设置显示 | `py scripts\ds1202ze.py autoscale` |
| `channel` | 查询或配置 CH1/CH2 | `py scripts\ds1202ze.py channel 1 --scale 1` |
| `timebase` | 查询或配置主时基 | `py scripts\ds1202ze.py timebase --scale 0.001` |
| `trigger edge` | 配置边沿触发 | `py scripts\ds1202ze.py trigger edge --source CHAN1 --level 1.2` |
| `measure` | 读取常用测量项 | `py scripts\ds1202ze.py measure freq --source CHAN1` |
| `waveform` | 抓取 BYTE 波形到 CSV 或 JSON | `py scripts\ds1202ze.py waveform CHAN1 ch1.csv` |
| `screenshot` | 抓取屏幕到 PNG 或 BMP | `py scripts\ds1202ze.py screenshot scope.png` |
| `query` | 发送原始 SCPI 查询 | `py scripts\ds1202ze.py query ":WAV:PRE?"` |
| `write` | 发送原始 SCPI 命令 | `py scripts\ds1202ze.py write "*CLS" --check-error` |
| `errors` | 读取 SCPI 错误队列 | `py scripts\ds1202ze.py errors` |
| `reset` | 执行 `*RST`，需要显式确认 | `py scripts\ds1202ze.py reset --yes` |

## 常用示例

### 设置 CH1 为 1 V/div，时基为 100 ms/div

```powershell
py scripts\ds1202ze.py timebase --scale 0.1
py scripts\ds1202ze.py channel 1 --scale 1
py scripts\ds1202ze.py screenshot scope_100ms_1v.png
```

### 配置 CH1 探头、耦合和偏移

```powershell
py scripts\ds1202ze.py channel 1 --display on --scale 0.5 --offset 0 --coupling DC --probe 10
```

### 配置边沿触发

```powershell
py scripts\ds1202ze.py trigger edge --source CHAN1 --slope POS --level 1.2 --sweep AUTO
```

### 抓取屏幕波形到 CSV

```powershell
py scripts\ds1202ze.py waveform CHAN1 ch1.csv
```

CSV 输出包含 `time_s`、`voltage_v` 和 `raw` 三列。

### 抓取波形到 JSON

```powershell
py scripts\ds1202ze.py waveform CHAN1 ch1.json --output-format json
```

### 深存储 RAW 抓取

```powershell
py scripts\ds1202ze.py waveform CHAN1 ch1_raw.csv --mode RAW --points 250000 --run-after
```

RAW 模式默认会停止采集，除非传入 `--no-stop`。如果希望抓取后恢复采集，请使用 `--run-after`。

### 抓取屏幕截图

```powershell
py scripts\ds1202ze.py screenshot scope.png
```

### 读取测量项

```powershell
py scripts\ds1202ze.py measure freq --source CHAN1
py scripts\ds1202ze.py measure vpp --source CHAN1
py scripts\ds1202ze.py measure vrms --source CHAN2 --json
```

### 发送原始 SCPI

```powershell
py scripts\ds1202ze.py query ":SYSTem:ERRor?"
py scripts\ds1202ze.py query ":WAVeform:PREamble?"
py scripts\ds1202ze.py write ":CHANnel1:DISPlay ON" --check-error
```

## 波形数据格式

脚本会使用：

```text
:WAVeform:SOURce
:WAVeform:MODE
:WAVeform:FORMat BYTE
:WAVeform:PREamble?
:WAVeform:DATA?
```

并根据 `:WAVeform:PREamble?` 返回的参数换算 BYTE 数据：

```text
time_s = (sample_index - xreference) * xincrement + xorigin
voltage_v = (raw_byte - yorigin - yreference) * yincrement
```

RAW 深存储模式下，脚本会分块读取数据，避免超过 DS1000Z/DS1000Z-E 单次 `:WAVeform:DATA?` 传输限制。

## AI 使用方式

安装为 Skill、Agent 扩展或项目规则后，AI 会在相关请求中读取 `SKILL.md` 并调用 `scripts/ds1202ze.py`。不同 AI 工具的安装目录不同，但核心使用方式一致。

可以这样提问：

```text
调用 DS1202Z-E skill，扫描 USB 并确认示波器身份。
```

```text
Use $ds1202ze to capture a CH1 waveform as CSV and a screenshot as PNG.
```

```text
使用 DS1202Z-E skill，把 CH1 设置为 1V/div，时基设置为 100ms/div，然后抓屏。
```

## 设计说明

### Windows native USBTMC

DS1202Z-E 在 Windows 设备管理器中通常显示为：

```text
USB Test and Measurement Device (IVI)
```

脚本会通过 SetupAPI 枚举 USBTMC 设备接口，并用 Win32 `CreateFile` / `WriteFile` / `ReadFile` 发送 USBTMC bulk 消息。这条路径不依赖 PyVISA，也不需要完整 NI-VISA runtime。

### PyVISA

如果系统已经安装 NI-VISA、Keysight IO Libraries Suite 或 RIGOL UltraSigma VISA，可以使用：

```powershell
py scripts\ds1202ze.py --backend @ivi scan --probe
```

也可以显式指定资源：

```powershell
py scripts\ds1202ze.py --resource "USB0::0x1AB1::0x0517::<serial>::INSTR" idn
```

### 多 RIGOL 仪器保护

脚本会结合 USB VID/PID、设备路径和 `*IDN?` 结果选择目标示波器。DM3058/DM3058E 万用表资源会被降权或拒绝，避免在同时连接示波器和万用表时误选设备。

## 注意事项

- 不要并行向同一台示波器发送多个查询。SCPI 仪器只有一个输出队列，并行查询会导致响应串线。
- 使用 `--resource` 前，先运行 `scan --probe` 确认目标设备。
- 不要把 DM3058E 的 resource 传给本示波器工具。DM3058E resource 通常包含 `PID_09C4` 或 `0x09C4`。
- `reset --yes` 会重置示波器设置，只在明确需要时使用。
- `channel`、`timebase`、`trigger`、`autoscale` 等命令会改变示波器当前前面板状态。
- RAW 波形抓取可能会停止采集；需要恢复采集时使用 `--run-after`。

## 故障排查

### 找不到设备

运行：

```powershell
py scripts\ds1202ze.py scan --probe
```

确认输出中有目标示波器，例如：

```text
RIGOL TECHNOLOGIES,DS1202Z-E,<scope-serial>,<firmware-version>
```

如果没有，请检查 USB 线、示波器 USB Device 口、Windows 设备管理器和驱动安装状态。

### 扫描到了 DM3058E

这是预期行为，只要万用表连接在 USB 上就会出现。它应该被标记为：

```text
<DM3058E multimeter, ignored>
```

不要把它的 resource 传给 `--resource`。

### PyVISA 报 `VI_ERROR_LIBRARY_NFOUND`

这表示系统中可能只有 IVI shared VISA router，没有完整 vendor VISA backend。直接使用默认命令即可：

```powershell
py scripts\ds1202ze.py idn
```

或显式使用 native：

```powershell
py scripts\ds1202ze.py --backend native idn
```

### 截图或波形抓取超时

可以增大超时时间：

```powershell
py scripts\ds1202ze.py --timeout-ms 20000 screenshot scope.png
```

对于较大的 RAW 抓取，可以减少 `--points`，或让脚本通过 `--chunk-points` 分块传输。

### 出现 `QUERY INTERRUPTED`

通常是多个查询重叠或上一次响应未读取完。清空状态后重试：

```powershell
py scripts\ds1202ze.py write "*CLS" --check-error
py scripts\ds1202ze.py errors
```

## 开发与验证

语法检查：

```powershell
py -m py_compile scripts\ds1202ze.py
```

Skill 结构校验（Codex / OpenAI skill-creator 工具可用时）：

```powershell
python "$env:USERPROFILE\.codex\skills\.system\skill-creator\scripts\quick_validate.py" .
```

硬件 smoke test：

```powershell
py scripts\ds1202ze.py scan --probe
py scripts\ds1202ze.py idn
py scripts\ds1202ze.py status --json
py scripts\ds1202ze.py waveform CHAN1 ch1.csv --points 1200
py scripts\ds1202ze.py screenshot scope.png
py scripts\ds1202ze.py errors
```

## 参考资料

- [RIGOL DS1000Z-E Programming Guide，中文官方支持镜像](https://supportcn.rigol.com/Public/Uploads/uploadfile/files/ftp/%E7%94%B5%E5%AD%90%E6%B5%8B%E9%87%8F%E4%BB%AA%E5%99%A8/%E7%A4%BA%E6%B3%A2%E5%99%A8/DS1000Z-E/%E4%B8%AD%E6%96%87%E6%89%8B%E5%86%8C/DS1000Z-E_ProgrammingGuide_CN.pdf)
- [RIGOL MSO1000Z/DS1000Z Programming Guide](https://www.batronix.com/files/Rigol/Oszilloskope/_DS%26MSO1000Z/MSO_DS1000Z_ProgrammingGuide_EN.pdf)
- [IVI-6.2 USBTMC Windows interoperability specification](https://www.ivifoundation.org/downloads/Architecture%20Specifications/Ivi-6%202_USBTMC_2018-11-01.pdf)

## 许可

建议在上传 GitHub 时为仓库添加 `LICENSE` 文件。若无特殊限制，可以使用 MIT License。
