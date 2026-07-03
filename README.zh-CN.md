# RIGOL DS1202Z-E USBTMC 控制工具

中文说明 | [English README](README.md)

本仓库包含一个确定性的 Python CLI 辅助脚本，以及一个可选的 agent skill 包，用于通过 USBTMC/VISA 和 SCPI 控制 RIGOL DS1202Z-E / DS1000Z-E 示波器。

这个项目并不只给 Codex 使用。你可以直接在终端运行 `scripts/ds1202ze.py`，也可以把它集成到自己的自动化脚本里；如果需要 agent 辅助工作流，也可以把本仓库作为兼容 Codex 的 skill 安装。

这个工具特别针对一种常见台面环境设计：电脑 USB 同时连接两台 RIGOL 仪器。

- RIGOL DS1202Z-E 示波器：本工具的目标设备。
- RIGOL DM3058/DM3058E 万用表：同样是 RIGOL USBTMC 设备，但必须被本示波器工具忽略。

CLI 会探测 `*IDN?`，结合 USB 描述符打分，自动选择示波器，并明确把 DM3058E 标记为 ignored，避免把示波器命令误发给万用表。

![DS1202Z-E 抓屏示例](ds1202ze_ch1_100ms_1v.png)

## 功能特性

- 使用 `scan --probe` 发现 USBTMC/VISA 仪器。
- 自动选择 DS1202Z-E / DS1000Z-E 示波器，并避开 DM3058E 万用表。
- 查询设备身份、触发状态、时基、通道配置、存储深度和 SCPI 错误状态。
- 配置 CH1/CH2 显示、垂直档位、偏移、耦合、探头倍率和带宽限制。
- 配置主时基档位和水平偏移。
- 配置边沿触发源、斜率、电平和触发扫描模式。
- 使用 `run`、`stop`、`single`、`clear`、`autoscale` 控制采集。
- 从 CHAN1、CHAN2 或 MATH 抓取波形数据，输出 CSV 或 JSON。
- 抓取示波器屏幕，输出 PNG 或 BMP。
- 支持原始 SCPI `query` 和 `write`，方便覆盖未封装的命令。
- 在 Windows 上可直接使用 IVI USBTMC 类驱动工作，不强制依赖 PyVISA。

## 仓库结构

```text
.
├── SKILL.md                         # Agent skill 元数据和使用流程
├── README.md                        # 英文 README
├── README.zh-CN.md                  # 中文 README
├── agents/
│   └── openai.yaml                  # 可选的 Codex/OpenAI UI 元数据
├── references/
│   └── scpi-cheatsheet.md           # DS1202Z-E / DS1000Z-E SCPI 速查
├── scripts/
│   └── ds1202ze.py                  # USBTMC/VISA CLI 辅助脚本
└── ds1202ze_ch1_100ms_1v.png        # 从示波器实机抓取的示例截图
```

## 支持的仪器

| 仪器 | 典型身份信息 | USB VID:PID | 行为 |
| --- | --- | --- | --- |
| RIGOL DS1202Z-E | `RIGOL TECHNOLOGIES,DS1202Z-E,...` | 实测设备为 `0x1AB1:0x0517`，部分 DS1000Z-E 示例中为 `0x1AB1:0x04CE` | 作为目标示波器选择 |
| RIGOL DS1000Z / DS1000Z-E 系列 | `RIGOL ... DS1xxxZ...` | RIGOL USBTMC 描述符 | 视为大概率兼容示波器 |
| RIGOL DM3058/DM3058E | `Rigol Technologies,DM3058E,...` | `0x1AB1:0x09C4` | 明确忽略 |

## 环境要求

- Python 3.11 或更新版本。
- 一台通过 USB 连接、并能被系统识别为 USB Test and Measurement Device 的 DS1202Z-E / DS1000Z-E。
- Windows：
  - 默认原生后端只需要 IVI USBTMC 类驱动。
  - PyVISA 是可选项。
- 非 Windows 系统：
  - 需要安装 PyVISA 和可用的 VISA 后端，例如 NI-VISA、Keysight IO Libraries、RIGOL UltraSigma/UltraScope VISA，或其他适合 USBTMC 的后端。

可选安装 PyVISA：

```powershell
py -m pip install --user pyvisa
```

## 安装

如果只需要直接使用 CLI，可以把仓库克隆到任意仪器工具目录：

```powershell
git clone https://github.com/<your-account>/ds1202ze.git
cd ds1202ze
py .\scripts\ds1202ze.py scan --probe
```

如果希望作为兼容 Codex 的 skill 使用，可以把本仓库克隆到 Codex 的 skills 目录。

Windows PowerShell：

```powershell
New-Item -ItemType Directory -Force "$env:USERPROFILE\.codex\skills" | Out-Null
git clone https://github.com/<your-account>/ds1202ze.git "$env:USERPROFILE\.codex\skills\ds1202ze"
```

macOS 或 Linux：

```bash
mkdir -p "$HOME/.codex/skills"
git clone https://github.com/<your-account>/ds1202ze.git "$HOME/.codex/skills/ds1202ze"
```

完成可选的 Codex 安装后，可以在 Codex 中要求使用 `$ds1202ze`。不使用 Codex 时，直接从仓库目录运行 CLI 即可。

## 快速开始

在本仓库目录中运行：

```powershell
py .\scripts\ds1202ze.py scan --probe
py .\scripts\ds1202ze.py idn
py .\scripts\ds1202ze.py status --json
py .\scripts\ds1202ze.py waveform CHAN1 "$PWD\ch1.csv"
py .\scripts\ds1202ze.py screenshot "$PWD\scope.png"
```

如果安装在 Codex skills 目录中：

```powershell
py "$env:USERPROFILE\.codex\skills\ds1202ze\scripts\ds1202ze.py" scan --probe
```

## 扫描输出示例

当示波器和 DM3058E 万用表同时连接时，预期输出类似：

```text
VISA resources:
  <pyvisa unavailable: pyvisa is not installed. Install it with:>
Windows native USBTMC paths:
  \\?\usb#vid_1ab1&pid_0517#scope-serial#{...}  idn=RIGOL TECHNOLOGIES,DS1202Z-E,<scope-serial>,00.06.04  <target DS1202Z-E>
  \\?\usb#vid_1ab1&pid_09c4#meter-serial#{...}  idn=Rigol Technologies,DM3058E,<meter-serial>,01.01.00.02.03.01  <DM3058E multimeter, ignored>
```

如果同时连接多台兼容示波器，请显式传入 `--resource`。

## 常用流程

### 设置 CH1 为 1 V/div，时基为 100 ms/div

```powershell
py .\scripts\ds1202ze.py timebase --scale 0.1
py .\scripts\ds1202ze.py channel 1 --scale 1
py .\scripts\ds1202ze.py screenshot .\scope_100ms_1v.png
```

### 配置 CH1

```powershell
py .\scripts\ds1202ze.py channel 1 --display on --scale 0.5 --offset 0 --coupling DC --probe 10
```

### 配置主时基

```powershell
py .\scripts\ds1202ze.py timebase --scale 0.001 --offset 0
```

`--scale` 的单位是秒每格。例如 `0.1` 表示 100 ms/div。

### 配置边沿触发

```powershell
py .\scripts\ds1202ze.py trigger edge --source CHAN1 --slope POS --level 1.2 --sweep AUTO
```

### 抓取波形数据

屏幕波形数据：

```powershell
py .\scripts\ds1202ze.py waveform CHAN1 .\ch1.csv
```

JSON 输出：

```powershell
py .\scripts\ds1202ze.py waveform CHAN1 .\ch1.json --output-format json
```

深存储 RAW 抓取：

```powershell
py .\scripts\ds1202ze.py waveform CHAN1 .\ch1_raw.csv --mode RAW --points 250000 --run-after
```

RAW 模式默认会停止采集，除非传入 `--no-stop`。如果希望抓取后恢复采集，请使用 `--run-after`。

### 抓取屏幕截图

```powershell
py .\scripts\ds1202ze.py screenshot .\scope.png
```

### 读取测量值

```powershell
py .\scripts\ds1202ze.py measure freq --source CHAN1
py .\scripts\ds1202ze.py measure vpp --source CHAN1
py .\scripts\ds1202ze.py measure vrms --source CHAN2 --json
```

### 发送原始 SCPI

```powershell
py .\scripts\ds1202ze.py query ":WAV:PRE?"
py .\scripts\ds1202ze.py write ":CHAN1:DISP ON" --check-error
py .\scripts\ds1202ze.py errors
```

## CLI 参数参考

全局参数：

| 参数 | 用途 |
| --- | --- |
| `--resource RESOURCE` | 显式选择 VISA resource 或原生 USBTMC path。应选择 DS1202Z-E，不要选择 DM3058E。 |
| `--backend BACKEND` | 选择 PyVISA 后端，例如 `@ivi` 或 `@py`；Windows 原生 USBTMC 使用 `native`。 |
| `--timeout-ms N` | 设置 I/O 超时时间，单位毫秒。默认 `8000`。 |
| `--max-read-bytes N` | 设置最大二进制读取字节数。默认 `5000000`。 |

子命令：

| 命令 | 用途 |
| --- | --- |
| `scan --probe` | 列出 VISA resource、Windows 原生 USBTMC path、PnP 匹配项，并可查询 `*IDN?`。 |
| `idn` | 查询 `*IDN?`。 |
| `status --json` | 显示身份信息、触发状态、时基、通道状态和 SCPI 错误状态。 |
| `run`、`stop`、`single`、`clear`、`autoscale` | 控制采集和显示状态。 |
| `channel` | 查询或配置 CH1/CH2。 |
| `timebase` | 查询或配置主时基。 |
| `trigger edge` | 配置边沿触发。 |
| `measure` | 使用 `:MEASure:ITEM?` 读取常用测量值。 |
| `waveform` | 抓取 BYTE 波形数据到 CSV 或 JSON。 |
| `screenshot` | 抓取屏幕图像到 PNG 或 BMP。 |
| `query` | 发送原始 SCPI 查询。 |
| `write` | 发送原始 SCPI 命令。 |
| `errors` | 读取 SCPI 错误队列。 |
| `reset --yes` | 使用 `*RST` 复位示波器。 |

## 波形输出格式

CSV 输出包含：

| 列名 | 含义 |
| --- | --- |
| `time_s` | 采样时间，单位秒。 |
| `voltage_v` | 换算后的电压，单位伏。 |
| `raw` | 示波器返回的原始 BYTE 采样值。 |

脚本会读取 `:WAVeform:PREamble?`，并按以下公式换算 BYTE 数据：

```text
time_s = (sample_index - xreference) * xincrement + xorigin
voltage_v = (raw_byte - yorigin - yreference) * yincrement
```

## 安全注意事项

- 不要对同一台示波器并行运行多个命令。SCPI 仪器只有一个输出队列，并发查询可能打乱响应。
- 使用 `--resource` 前，先通过 `scan --probe` 确认目标设备。
- 不要把 DM3058E 的 resource 传给本示波器工具。DM3058E resource 通常包含 `PID_09C4` 或 `0x09C4`。
- `reset` 必须显式传入 `--yes`，因为 `*RST` 会改变前面板状态。
- RAW 波形抓取可能会停止采集。如果希望抓取后恢复运行，请使用 `--run-after`。

## 实测配置

测试日期：2026-07-03。

- 示波器：`RIGOL TECHNOLOGIES,DS1202Z-E,<scope-serial>,00.06.04`
- 另一路 USB 万用表：`Rigol Technologies,DM3058E,<meter-serial>,01.01.00.02.03.01`
- Python：Windows 上可用 3.11.15 和 3.14
- 通信方式：Windows 原生 USBTMC，设备显示为 `USB Test and Measurement Device (IVI)`
- 已验证操作：
  - `scan --probe`
  - `idn`
  - `status --json`
  - CH1 垂直档位配置
  - 主时基配置
  - CH1 1200 点波形抓取
  - PNG 屏幕抓图

## 故障排查

### 提示 `pyvisa is not installed`

在 Windows 上，如果原生 USBTMC 可用，这是正常情况。脚本会自动使用原生 USBTMC。若希望显式使用 VISA 后端，可以安装 PyVISA：

```powershell
py -m pip install --user pyvisa
```

### 扫描结果里出现 DM3058E

这是预期行为，只要万用表连接在 USB 上就会出现。它应该被标记为：

```text
<DM3058E multimeter, ignored>
```

不要把它的 resource 传给 `--resource`。

### 没有出现 USBTMC 设备

请检查：

- 示波器 USB Device 口已连接电脑。
- Windows 设备管理器中能看到 `USB Test and Measurement Device (IVI)`。
- 示波器已开机，并且没有被其他控制软件占用。
- USB 线支持数据传输。

### 截图或波形抓取超时

可以增大超时时间：

```powershell
py .\scripts\ds1202ze.py --timeout-ms 20000 screenshot .\scope.png
```

对于较大的 RAW 抓取，可以减少 `--points`，或让脚本通过 `--chunk-points` 分块传输。

## 发布到 GitHub 前的检查清单

- 确认仓库包含 `SKILL.md`、`scripts/ds1202ze.py`、`references/scpi-cheatsheet.md`、`agents/openai.yaml` 和 README。
- 不要提交 `__pycache__`、本地日志或私有测量数据。
- 如果仓库公开发布，请添加 license 文件。
- 运行 `python -m py_compile scripts/ds1202ze.py`。
- 在连接示波器的机器上运行 `python scripts/ds1202ze.py scan --probe`。

## 参考资料

- [RIGOL DS1000Z-E Programming Guide，中文官方支持镜像](https://supportcn.rigol.com/Public/Uploads/uploadfile/files/ftp/%E7%94%B5%E5%AD%90%E6%B5%8B%E9%87%8F%E4%BB%AA%E5%99%A8/%E7%A4%BA%E6%B3%A2%E5%99%A8/DS1000Z-E/%E4%B8%AD%E6%96%87%E6%89%8B%E5%86%8C/DS1000Z-E_ProgrammingGuide_CN.pdf)
- [RIGOL MSO1000Z/DS1000Z Programming Guide 镜像](https://www.batronix.com/files/Rigol/Oszilloskope/_DS%26MSO1000Z/MSO_DS1000Z_ProgrammingGuide_EN.pdf)

## 许可证

公开发布前建议添加 license 文件。对于小型辅助脚本，MIT 是常见选择；也可以按你的实际用途选择其他许可证。
