# DS1202Z-E SCPI Cheat Sheet

Sources:

- RIGOL DS1000Z-E Programming Guide (Chinese, official support mirror): https://supportcn.rigol.com/Public/Uploads/uploadfile/files/ftp/%E7%94%B5%E5%AD%90%E6%B5%8B%E9%87%8F%E4%BB%AA%E5%99%A8/%E7%A4%BA%E6%B3%A2%E5%99%A8/DS1000Z-E/%E4%B8%AD%E6%96%87%E6%89%8B%E5%86%8C/DS1000Z-E_ProgrammingGuide_CN.pdf
- RIGOL MSO1000Z/DS1000Z Programming Guide: https://www.batronix.com/files/Rigol/Oszilloskope/_DS%26MSO1000Z/MSO_DS1000Z_ProgrammingGuide_EN.pdf

## Identification and Safety

- Identity: `*IDN?`
- Clear status: `*CLS`
- Reset: `*RST`
- Error queue: `:SYSTem:ERRor?`
- Target scope USB resource uses vendor `0x1AB1`; DS1202Z-E units may appear with product `0x0517`, while some programming guide examples use `0x04CE`.
- DM3058E multimeter USB resources use product `0x09C4`; do not use those with this oscilloscope helper.

## Acquisition

- Run: `:RUN`
- Stop: `:STOP`
- Single acquisition: `:SINGle`
- Autoscale: `:AUToscale`
- Trigger status: `:TRIGger:STATus?`
- Memory depth: `:ACQuire:MDEPth?`

## Channels

- Display: `:CHANnel1:DISPlay {ON|OFF}` / `:CHANnel1:DISPlay?`
- Scale: `:CHANnel1:SCALe <volts_per_div>` / `:CHANnel1:SCALe?`
- Offset: `:CHANnel1:OFFSet <volts>` / `:CHANnel1:OFFSet?`
- Coupling: `:CHANnel1:COUPling {AC|DC|GND}` / `:CHANnel1:COUPling?`
- Probe ratio: `:CHANnel1:PROBe <ratio>` / `:CHANnel1:PROBe?`
- Bandwidth limit: `:CHANnel1:BWLimit {ON|OFF}` / `:CHANnel1:BWLimit?`

Use `CHANnel2` for channel 2. DS1202Z-E has two analog channels.

## Timebase

- Main scale: `:TIMebase:MAIN:SCALe <seconds_per_div>` / `:TIMebase:MAIN:SCALe?`
- Main offset: `:TIMebase:MAIN:OFFSet <seconds>` / `:TIMebase:MAIN:OFFSet?`
- Timebase mode: `:TIMebase:MODE?`

## Edge Trigger

- Trigger mode: `:TRIGger:MODE EDGE`
- Source: `:TRIGger:EDGE:SOURce {CHAN1|CHAN2|EXT|ACLINE}`
- Slope: `:TRIGger:EDGE:SLOPe {POSitive|NEGative|RFALl}`
- Level: `:TRIGger:EDGE:LEVel <volts>`
- Sweep: `:TRIGger:SWEep {AUTO|NORMal|SINGle}`

## Measurements

Use `:MEASure:ITEM? <item>,<source>`, for example:

```text
:MEASure:ITEM? FREQ,CHAN1
:MEASure:ITEM? VPP,CHAN1
:MEASure:ITEM? VRMS,CHAN2
```

Common items include `FREQ`, `PER`, `VMAX`, `VMIN`, `VPP`, `VTOP`, `VBASE`, `VAMP`, `VAVG`, `VRMS`, `PREShoot`, `OVERshoot`, `RIS`, `FALL`, `PWID`, `NWID`, `PDUT`, and `NDUT`.

## Waveform Readout

Screen waveform:

```text
:WAVeform:SOURce CHAN1
:WAVeform:MODE NORMal
:WAVeform:FORMat BYTE
:WAVeform:DATA?
```

Deep memory waveform:

```text
:STOP
:WAVeform:SOURce CHAN1
:WAVeform:MODE RAW
:WAVeform:FORMat BYTE
:WAVeform:STARt 1
:WAVeform:STOP <last_point>
:WAVeform:DATA?
```

For DS1000Z/DS1000Z-E RAW reads, split requests into chunks. The documented per-request limits are 250000 points for BYTE, 125000 points for WORD, and 15625 points for ASCII.

Read scaling with `:WAVeform:PREamble?`. The preamble fields are:

```text
format,type,points,count,xincrement,xorigin,xreference,yincrement,yorigin,yreference
```

For BYTE data, convert with:

```text
time_s = (sample_index - xreference) * xincrement + xorigin
voltage_v = (raw_byte - yorigin - yreference) * yincrement
```

## Screenshot

Use:

```text
:DISPlay:DATA? ON,OFF,PNG
```

The response is an IEEE 488.2 binary block; strip the block header before saving the PNG payload.
