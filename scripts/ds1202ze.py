#!/usr/bin/env python3
"""CLI helper for RIGOL DS1202Z-E / DS1000Z-E USBTMC/VISA control."""

from __future__ import annotations

import argparse
import csv
import ctypes
import json
import platform
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Iterable


RIGOL_VENDOR_ID = 0x1AB1
DS1000ZE_PIDS = {0x04CE, 0x0517}
DM3058E_PID = 0x09C4
USBTMC_WINDOWS_GUID = "{A9FDBB24-128A-11D5-9961-00108335E361}"
RAW_BYTE_CHUNK_LIMIT = 250_000

MEASURE_ALIASES = {
    "freq": "FREQ",
    "frequency": "FREQ",
    "period": "PER",
    "per": "PER",
    "vmax": "VMAX",
    "max": "VMAX",
    "vmin": "VMIN",
    "min": "VMIN",
    "vpp": "VPP",
    "pkpk": "VPP",
    "peak-to-peak": "VPP",
    "vtop": "VTOP",
    "top": "VTOP",
    "vbase": "VBASE",
    "base": "VBASE",
    "vamp": "VAMP",
    "amp": "VAMP",
    "vavg": "VAVG",
    "avg": "VAVG",
    "vrms": "VRMS",
    "rms": "VRMS",
    "rise": "RIS",
    "ris": "RIS",
    "fall": "FALL",
    "pwidth": "PWID",
    "pwid": "PWID",
    "nwidth": "NWID",
    "nwid": "NWID",
    "pduty": "PDUT",
    "pdut": "PDUT",
    "nduty": "NDUT",
    "ndut": "NDUT",
    "overshoot": "OVER",
    "over": "OVER",
    "preshoot": "PRES",
    "pres": "PRES",
}


def eprint(*args: object) -> None:
    print(*args, file=sys.stderr)


def import_pyvisa() -> Any:
    try:
        import pyvisa  # type: ignore
    except ImportError as exc:
        raise SystemExit(
            "pyvisa is not installed. Install it with:\n"
            "  python -m pip install --user pyvisa\n"
            "Or use --backend native on Windows when the IVI USBTMC class driver is present."
        ) from exc
    return pyvisa


def is_native_backend(backend: str | None) -> bool:
    return (backend or "").strip().lower() in {"native", "winusbtmc", "windows", "win"}


def make_rm(backend: str | None) -> Any:
    pyvisa = import_pyvisa()
    try:
        if backend:
            return pyvisa.ResourceManager(backend)
        return pyvisa.ResourceManager()
    except Exception as exc:
        raise SystemExit(
            "Unable to create a VISA ResourceManager. Install NI-VISA, Keysight IO "
            "Libraries, RIGOL UltraSigma VISA, or another full VISA backend.\n"
            f"Original error: {exc}"
        ) from exc


def list_visa_resources(backend: str | None) -> list[str]:
    rm = make_rm(backend)
    try:
        return [str(r) for r in rm.list_resources()]
    finally:
        try:
            rm.close()
        except Exception:
            pass


def windows_pnp_devices() -> list[dict[str, str]]:
    if platform.system().lower() != "windows":
        return []
    script = (
        "Get-PnpDevice | Where-Object { "
        "$_.FriendlyName -match 'USB Test|RIGOL|DS1|DS1000|DM3058|IVI|Measurement|TMC' "
        "-or $_.InstanceId -match '1AB1|04CE|09C4|USBTMC' } | "
        "Select-Object Status,Class,FriendlyName,InstanceId | ConvertTo-Json"
    )
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", script],
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            timeout=8,
            check=False,
        )
    except Exception:
        return []
    stdout = result.stdout or ""
    if not stdout.strip():
        return []
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        return []
    if isinstance(data, dict):
        data = [data]
    return [
        {k: "" if v is None else str(v) for k, v in item.items()}
        for item in data
        if isinstance(item, dict)
    ]


def _windows_guid_from_string(value: str) -> Any:
    import uuid
    from ctypes import wintypes

    class GUID(ctypes.Structure):
        _fields_ = [
            ("Data1", wintypes.DWORD),
            ("Data2", wintypes.WORD),
            ("Data3", wintypes.WORD),
            ("Data4", ctypes.c_ubyte * 8),
        ]

    return GUID.from_buffer_copy(uuid.UUID(value).bytes_le)


def windows_usbtmc_paths() -> list[str]:
    if platform.system().lower() != "windows":
        return []

    from ctypes import wintypes

    guid = _windows_guid_from_string(USBTMC_WINDOWS_GUID)

    class SP_DEVICE_INTERFACE_DATA(ctypes.Structure):
        _fields_ = [
            ("cbSize", wintypes.DWORD),
            ("InterfaceClassGuid", type(guid)),
            ("Flags", wintypes.DWORD),
            ("Reserved", ctypes.c_size_t),
        ]

    setupapi = ctypes.WinDLL("setupapi", use_last_error=True)
    get_class_devs = setupapi.SetupDiGetClassDevsW
    get_class_devs.argtypes = [ctypes.POINTER(type(guid)), wintypes.LPCWSTR, wintypes.HWND, wintypes.DWORD]
    get_class_devs.restype = wintypes.HANDLE

    enum_interfaces = setupapi.SetupDiEnumDeviceInterfaces
    enum_interfaces.argtypes = [
        wintypes.HANDLE,
        ctypes.c_void_p,
        ctypes.POINTER(type(guid)),
        wintypes.DWORD,
        ctypes.POINTER(SP_DEVICE_INTERFACE_DATA),
    ]
    enum_interfaces.restype = wintypes.BOOL

    get_detail = setupapi.SetupDiGetDeviceInterfaceDetailW
    get_detail.argtypes = [
        wintypes.HANDLE,
        ctypes.POINTER(SP_DEVICE_INTERFACE_DATA),
        ctypes.c_void_p,
        wintypes.DWORD,
        ctypes.POINTER(wintypes.DWORD),
        ctypes.c_void_p,
    ]
    get_detail.restype = wintypes.BOOL

    destroy = setupapi.SetupDiDestroyDeviceInfoList
    destroy.argtypes = [wintypes.HANDLE]
    destroy.restype = wintypes.BOOL

    hdev = get_class_devs(ctypes.byref(guid), None, None, 0x00000002 | 0x00000010)
    if hdev == ctypes.c_void_p(-1).value:
        return []

    paths: list[str] = []
    try:
        index = 0
        while True:
            ifdata = SP_DEVICE_INTERFACE_DATA()
            ifdata.cbSize = ctypes.sizeof(SP_DEVICE_INTERFACE_DATA)
            if not enum_interfaces(hdev, None, ctypes.byref(guid), index, ctypes.byref(ifdata)):
                break
            needed = wintypes.DWORD(0)
            get_detail(hdev, ctypes.byref(ifdata), None, 0, ctypes.byref(needed), None)
            if needed.value:
                buf = ctypes.create_string_buffer(needed.value)
                detail_cb_size = 8 if ctypes.sizeof(ctypes.c_void_p) == 8 else 6
                ctypes.memmove(buf, ctypes.byref(wintypes.DWORD(detail_cb_size)), 4)
                if get_detail(hdev, ctypes.byref(ifdata), buf, needed, None, None):
                    paths.append(ctypes.wstring_at(ctypes.addressof(buf) + 4))
            index += 1
    finally:
        destroy(hdev)
    return paths


def _parse_usb_visa_resource(resource: str) -> tuple[int | None, int | None, str | None]:
    match = re.match(
        r"USB\d*::(?P<vid>0x[0-9a-fA-F]+|\d+)::(?P<pid>0x[0-9a-fA-F]+|\d+)::(?P<serial>[^:]+)",
        resource.strip(),
    )
    if not match:
        return None, None, None
    return int(match.group("vid"), 0), int(match.group("pid"), 0), match.group("serial")


def _path_matches_resource(path: str, resource: str) -> bool:
    text = path.lower()
    if resource.startswith("\\\\?\\"):
        return text == resource.lower()
    vid, pid, serial = _parse_usb_visa_resource(resource)
    if vid is not None and f"vid_{vid:04x}" not in text:
        return False
    if pid is not None and f"pid_{pid:04x}" not in text:
        return False
    if serial and serial.lower() not in text:
        return False
    if vid is not None or pid is not None or serial:
        return True
    return resource.lower() in text


class WinUsbTmcInstrument:
    """Small Windows USBTMC transport using the IVI USBTMC class driver."""

    write_termination = "\n"
    read_termination = "\n"

    def __init__(self, path: str, timeout_ms: int = 8000) -> None:
        if platform.system().lower() != "windows":
            raise RuntimeError("native USBTMC backend is only available on Windows")
        self.path = path
        self.timeout = timeout_ms
        self._tag = 1
        self._load_win32()
        self.handle = self._create_file(path)

    def _load_win32(self) -> None:
        from ctypes import wintypes

        self.wintypes = wintypes
        self.kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

        class OVERLAPPED(ctypes.Structure):
            _fields_ = [
                ("Internal", ctypes.c_size_t),
                ("InternalHigh", ctypes.c_size_t),
                ("Offset", wintypes.DWORD),
                ("OffsetHigh", wintypes.DWORD),
                ("hEvent", wintypes.HANDLE),
            ]

        self.OVERLAPPED = OVERLAPPED

        self.CreateFile = self.kernel32.CreateFileW
        self.CreateFile.argtypes = [
            wintypes.LPCWSTR,
            wintypes.DWORD,
            wintypes.DWORD,
            ctypes.c_void_p,
            wintypes.DWORD,
            wintypes.DWORD,
            wintypes.HANDLE,
        ]
        self.CreateFile.restype = wintypes.HANDLE

        self.WriteFile = self.kernel32.WriteFile
        self.WriteFile.argtypes = [
            wintypes.HANDLE,
            ctypes.c_void_p,
            wintypes.DWORD,
            ctypes.POINTER(wintypes.DWORD),
            ctypes.POINTER(OVERLAPPED),
        ]
        self.WriteFile.restype = wintypes.BOOL

        self.ReadFile = self.kernel32.ReadFile
        self.ReadFile.argtypes = [
            wintypes.HANDLE,
            ctypes.c_void_p,
            wintypes.DWORD,
            ctypes.POINTER(wintypes.DWORD),
            ctypes.POINTER(OVERLAPPED),
        ]
        self.ReadFile.restype = wintypes.BOOL

        self.CreateEvent = self.kernel32.CreateEventW
        self.CreateEvent.argtypes = [ctypes.c_void_p, wintypes.BOOL, wintypes.BOOL, wintypes.LPCWSTR]
        self.CreateEvent.restype = wintypes.HANDLE

        self.WaitForSingleObject = self.kernel32.WaitForSingleObject
        self.WaitForSingleObject.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        self.WaitForSingleObject.restype = wintypes.DWORD

        self.GetOverlappedResult = self.kernel32.GetOverlappedResult
        self.GetOverlappedResult.argtypes = [
            wintypes.HANDLE,
            ctypes.POINTER(OVERLAPPED),
            ctypes.POINTER(wintypes.DWORD),
            wintypes.BOOL,
        ]
        self.GetOverlappedResult.restype = wintypes.BOOL

        self.CancelIoEx = self.kernel32.CancelIoEx
        self.CancelIoEx.argtypes = [wintypes.HANDLE, ctypes.POINTER(OVERLAPPED)]
        self.CancelIoEx.restype = wintypes.BOOL

        self.CloseHandle = self.kernel32.CloseHandle
        self.CloseHandle.argtypes = [wintypes.HANDLE]
        self.CloseHandle.restype = wintypes.BOOL

    def _create_file(self, path: str) -> Any:
        handle = self.CreateFile(
            path,
            0x80000000 | 0x40000000,
            0x00000001 | 0x00000002,
            None,
            3,
            0x80 | 0x40000000,
            None,
        )
        if handle == ctypes.c_void_p(-1).value:
            raise ctypes.WinError(ctypes.get_last_error())
        return handle

    def _next_tag(self) -> int:
        tag = self._tag
        self._tag = 1 if self._tag >= 255 else self._tag + 1
        return tag

    def _overlapped_io(self, op: str, buffer: Any, length: int) -> int:
        event = self.CreateEvent(None, True, False, None)
        if not event:
            raise ctypes.WinError(ctypes.get_last_error())
        overlapped = self.OVERLAPPED()
        overlapped.hEvent = event
        transferred = self.wintypes.DWORD(0)
        try:
            if op == "write":
                ok = self.WriteFile(self.handle, buffer, length, ctypes.byref(transferred), ctypes.byref(overlapped))
            else:
                ok = self.ReadFile(self.handle, buffer, length, ctypes.byref(transferred), ctypes.byref(overlapped))
            err = ctypes.get_last_error()
            if not ok and err != 997:
                raise ctypes.WinError(err)
            wait = self.WaitForSingleObject(event, int(self.timeout))
            if wait == 258:
                self.CancelIoEx(self.handle, ctypes.byref(overlapped))
                raise TimeoutError(f"native USBTMC {op} timed out after {self.timeout} ms")
            if wait != 0:
                raise ctypes.WinError(ctypes.get_last_error())
            if not self.GetOverlappedResult(self.handle, ctypes.byref(overlapped), ctypes.byref(transferred), False):
                raise ctypes.WinError(ctypes.get_last_error())
            return int(transferred.value)
        finally:
            self.CloseHandle(event)

    def _write_bytes(self, data: bytes) -> int:
        buf = ctypes.create_string_buffer(data)
        return self._overlapped_io("write", buf, len(data))

    def _read_bytes(self, size: int) -> bytes:
        buf = ctypes.create_string_buffer(size)
        count = self._overlapped_io("read", buf, size)
        return buf.raw[:count]

    def _dev_dep_msg_out(self, data: bytes) -> None:
        tag = self._next_tag()
        header = bytes([1, tag, 0xFF - tag, 0]) + int(len(data)).to_bytes(4, "little") + bytes([1, 0, 0, 0])
        packet = header + data
        packet += b"\0" * ((4 - (len(packet) % 4)) % 4)
        self._write_bytes(packet)

    def _request_dev_dep_msg_in(self, max_size: int = 1_048_576) -> bytes:
        chunks: list[bytes] = []
        remaining = max_size
        while remaining > 0:
            request_size = min(remaining, 1_048_576)
            tag = self._next_tag()
            request = bytes([2, tag, 0xFF - tag, 0]) + int(request_size).to_bytes(4, "little") + bytes([0, 0, 0, 0])
            request += b"\0" * ((4 - (len(request) % 4)) % 4)
            self._write_bytes(request)
            response = self._read_bytes(request_size + 12)
            if len(response) < 12:
                raise IOError(f"short USBTMC response: {response!r}")
            transfer_size = int.from_bytes(response[4:8], "little")
            attrs = response[8]
            chunks.append(response[12 : 12 + transfer_size])
            remaining -= transfer_size
            if attrs & 1 or transfer_size == 0:
                break
        return b"".join(chunks)

    def write(self, command: str | bytes) -> None:
        data = command.encode("ascii") if isinstance(command, str) else command
        termination = self.write_termination.encode("ascii") if self.write_termination else b""
        if termination and not data.endswith(termination):
            data += termination
        self._dev_dep_msg_out(data)

    def read_raw(self, max_size: int = 1_048_576) -> bytes:
        return self._request_dev_dep_msg_in(max_size)

    def query(self, command: str) -> str:
        self.write(command)
        return self.read_raw().decode("ascii", errors="replace").strip()

    def close(self) -> None:
        if getattr(self, "handle", None):
            self.CloseHandle(self.handle)
            self.handle = None


def configure_instrument(inst: Any, timeout_ms: int, max_read_bytes: int = 5_000_000) -> None:
    try:
        inst.timeout = timeout_ms
    except Exception:
        pass
    try:
        inst.chunk_size = max(inst.chunk_size, max_read_bytes)
    except Exception:
        pass
    for attr, value in (("write_termination", "\n"), ("read_termination", "\n")):
        try:
            setattr(inst, attr, value)
        except Exception:
            pass


def resource_score(resource: str, idn: str | None = None) -> int:
    text = f"{resource} {idn or ''}".upper()
    score = 0
    if "DM3058" in text or "09C4" in text or "PID_09C4" in text:
        score -= 100
    if "USB" in text or "USBTMC" in text:
        score += 5
    if "1AB1" in text or "VID_1AB1" in text:
        score += 10
    if "04CE" in text or "0517" in text or "PID_04CE" in text or "PID_0517" in text:
        score += 30
    if "RIGOL" in text:
        score += 10
    if "DS1202Z-E" in text or "DS1202ZE" in text:
        score += 70
    elif "DS1000Z-E" in text or "DS1000Z" in text:
        score += 50
    elif re.search(r"\b(MSO|DS)1\d{3}Z", text):
        score += 45
    elif "OSCILLOSCOPE" in text:
        score += 25
    return score


def marker_for(resource: str, idn: str | None) -> str:
    text = f"{resource} {idn or ''}".upper()
    if "DM3058" in text or "09C4" in text or "PID_09C4" in text:
        return "  <DM3058E multimeter, ignored>"
    score = resource_score(resource, idn)
    if "DS1202Z-E" in text or "DS1202ZE" in text:
        return "  <target DS1202Z-E>"
    if score >= 45:
        return "  <likely DS1000Z/DS1000Z-E oscilloscope>"
    if score >= 25:
        return "  <possible oscilloscope>"
    return ""


def query_idn(resource: str, backend: str | None, timeout_ms: int) -> str | None:
    pyvisa = import_pyvisa()
    rm = make_rm(backend)
    try:
        inst = rm.open_resource(resource)
        try:
            configure_instrument(inst, timeout_ms)
            return str(inst.query("*IDN?")).strip()
        except pyvisa.errors.VisaIOError:
            return None
        finally:
            inst.close()
    except Exception:
        return None
    finally:
        try:
            rm.close()
        except Exception:
            pass


def probe_native_idn(path: str, timeout_ms: int) -> str | None:
    inst = WinUsbTmcInstrument(path, timeout_ms)
    try:
        return inst.query("*IDN?")
    except Exception:
        return None
    finally:
        inst.close()


def choose_resource(resources: Iterable[str], backend: str | None, timeout_ms: int) -> str:
    candidates: list[tuple[int, str, str | None]] = []
    for resource in resources:
        idn: str | None = None
        if any(token in resource.upper() for token in ("USB", "TCPIP", "GPIB", "ASRL")):
            try:
                idn = query_idn(resource, backend, timeout_ms)
            except SystemExit:
                raise
            except Exception:
                idn = None
        score = resource_score(resource, idn)
        if score >= 25:
            candidates.append((score, resource, idn))
    if not candidates:
        raise SystemExit(
            "No likely DS1202Z-E/DS1000Z-E VISA resource found. Run 'scan --probe', "
            "then pass --resource explicitly. Do not pass the DM3058E resource."
        )
    candidates.sort(reverse=True, key=lambda item: item[0])
    top = candidates[0]
    if len(candidates) > 1 and candidates[1][0] == top[0]:
        lines = "\n".join(f"  {r}  idn={i or '<no response>'}" for _, r, i in candidates)
        raise SystemExit(f"Multiple equally likely scope resources found:\n{lines}\nPass --resource.")
    return top[1]


def choose_native_path(resource: str | None, timeout_ms: int) -> str:
    paths = windows_usbtmc_paths()
    if resource:
        matches = [path for path in paths if _path_matches_resource(path, resource)]
        if not matches and resource.startswith("\\\\?\\"):
            matches = [resource]
    else:
        matches = paths
    if not matches:
        raise SystemExit("No Windows native USBTMC device path found.")

    candidates: list[tuple[int, str, str | None]] = []
    for path in matches:
        idn = probe_native_idn(path, timeout_ms)
        score = resource_score(path, idn)
        if score >= 25:
            candidates.append((score, path, idn))
    if not candidates:
        pid_matches = [
            path
            for path in matches
            if "vid_1ab1&pid_04ce" in path.lower() or "vid_1ab1&pid_0517" in path.lower()
        ]
        if len(pid_matches) == 1:
            return pid_matches[0]
        if pid_matches:
            joined = "\n".join(f"  {path}" for path in pid_matches)
            raise SystemExit(f"Multiple DS1000Z-E native USBTMC paths found:\n{joined}\nPass --resource.")
        raise SystemExit("No likely DS1202Z-E native USBTMC path found. Run 'scan --probe'.")
    candidates.sort(reverse=True, key=lambda item: item[0])
    top = candidates[0]
    if len(candidates) > 1 and candidates[1][0] == top[0]:
        lines = "\n".join(f"  {path}  idn={idn or '<no response>'}" for _, path, idn in candidates)
        raise SystemExit(f"Multiple equally likely native USBTMC scopes found:\n{lines}\nPass --resource.")
    return top[1]


def ensure_scope_idn(idn: str | None, resource: str) -> None:
    if not idn:
        return
    if resource_score(resource, idn) < 25:
        raise SystemExit(f"Selected resource does not look like a DS1202Z-E scope: {resource} idn={idn}")
    if "DM3058" in idn.upper():
        raise SystemExit(f"Selected resource is the DM3058E multimeter, not the oscilloscope: {resource} idn={idn}")


def should_use_native(args: argparse.Namespace) -> bool:
    if is_native_backend(args.backend):
        return True
    if args.backend is not None or platform.system().lower() != "windows":
        return False
    if args.resource and not (args.resource.upper().startswith("USB") or args.resource.startswith("\\\\?\\")):
        return False
    return bool(windows_usbtmc_paths())


def open_native_scope(args: argparse.Namespace, ensure_scope: bool = True) -> Any:
    path = choose_native_path(args.resource, args.timeout_ms)
    inst = WinUsbTmcInstrument(path, args.timeout_ms)
    inst._ds1202ze_resource = f"native:{path}"
    if ensure_scope:
        ensure_scope_idn(inst.query("*IDN?"), path)
    return inst


def open_pyvisa_scope(args: argparse.Namespace, ensure_scope: bool = True) -> Any:
    rm = make_rm(args.backend)
    resources = list(rm.list_resources())
    resource = args.resource or choose_resource(resources, args.backend, args.timeout_ms)
    try:
        inst = rm.open_resource(resource)
        configure_instrument(inst, args.timeout_ms, args.max_read_bytes)
        inst._ds1202ze_rm = rm
        inst._ds1202ze_resource = resource
        if ensure_scope:
            ensure_scope_idn(str(inst.query("*IDN?")).strip(), resource)
        return inst
    except Exception:
        try:
            rm.close()
        except Exception:
            pass
        raise


def open_scope(args: argparse.Namespace, ensure_scope: bool = True) -> Any:
    if should_use_native(args):
        return open_native_scope(args, ensure_scope)
    try:
        return open_pyvisa_scope(args, ensure_scope)
    except SystemExit as exc:
        if args.backend is None and platform.system().lower() == "windows" and windows_usbtmc_paths():
            eprint(f"PyVISA backend unavailable; falling back to native USBTMC. Detail: {exc}")
            return open_native_scope(args, ensure_scope)
        raise


def close_scope(inst: Any) -> None:
    rm = getattr(inst, "_ds1202ze_rm", None)
    try:
        inst.close()
    finally:
        if rm is not None:
            try:
                rm.close()
            except Exception:
                pass


def ask(inst: Any, command: str) -> str:
    return str(inst.query(command)).strip()


def tell(inst: Any, command: str) -> None:
    inst.write(command)


def read_raw(inst: Any, max_size: int) -> bytes:
    if isinstance(inst, WinUsbTmcInstrument):
        return inst.read_raw(max_size)
    try:
        return bytes(inst.read_raw(max_size))
    except TypeError:
        return bytes(inst.read_raw())


def query_binary(inst: Any, command: str, max_size: int) -> bytes:
    tell(inst, command)
    return read_raw(inst, max_size)


def parse_ieee_block(raw: bytes) -> bytes:
    start = raw.find(b"#")
    if start < 0:
        raise ValueError(f"binary block header not found; first bytes={raw[:32]!r}")
    raw = raw[start:]
    if len(raw) < 2:
        raise ValueError("incomplete binary block header")
    digits = int(chr(raw[1]))
    if digits == 0:
        return raw[2:].rstrip(b"\n")
    header_len = 2 + digits
    if len(raw) < header_len:
        raise ValueError("incomplete binary block length")
    payload_len = int(raw[2:header_len].decode("ascii"))
    end = header_len + payload_len
    if len(raw) < end:
        raise ValueError(f"incomplete binary block: got {len(raw) - header_len}, expected {payload_len}")
    return raw[header_len:end]


def normalize_on_off(value: str) -> str:
    key = value.strip().lower()
    if key in {"on", "1", "true", "yes", "enable", "enabled"}:
        return "ON"
    if key in {"off", "0", "false", "no", "disable", "disabled"}:
        return "OFF"
    raise SystemExit(f"Expected on/off, got {value!r}")


def normalize_source(value: str) -> str:
    key = value.strip().upper().replace(" ", "")
    mapping = {
        "1": "CHAN1",
        "CH1": "CHAN1",
        "CHANNEL1": "CHAN1",
        "CHAN1": "CHAN1",
        "2": "CHAN2",
        "CH2": "CHAN2",
        "CHANNEL2": "CHAN2",
        "CHAN2": "CHAN2",
        "MATH": "MATH",
    }
    if key in mapping:
        return mapping[key]
    if key in {"CH3", "CHAN3", "CHANNEL3", "3", "CH4", "CHAN4", "CHANNEL4", "4"}:
        raise SystemExit("DS1202Z-E has only CHAN1 and CHAN2 analog inputs.")
    raise SystemExit(f"Unknown source {value!r}; use CHAN1, CHAN2, or MATH.")


def normalize_channel(value: str) -> int:
    source = normalize_source(value)
    if source == "MATH":
        raise SystemExit("Channel configuration only supports CHAN1 or CHAN2.")
    return int(source[-1])


def normalize_measure_item(value: str) -> str:
    key = value.strip().lower()
    return MEASURE_ALIASES.get(key, value.strip().upper())


def safe_query(inst: Any, command: str) -> str | None:
    try:
        return ask(inst, command)
    except Exception:
        return None


def parse_preamble(text: str) -> dict[str, Any]:
    values = [item.strip() for item in text.split(",")]
    keys = [
        "format",
        "type",
        "points",
        "count",
        "xincrement",
        "xorigin",
        "xreference",
        "yincrement",
        "yorigin",
        "yreference",
    ]
    preamble: dict[str, Any] = {"raw": text}
    for key, raw in zip(keys, values):
        try:
            if key in {"format", "type", "points", "count"}:
                preamble[key] = int(float(raw))
            else:
                preamble[key] = float(raw)
        except ValueError:
            preamble[key] = raw
    return preamble


def query_wave_points(inst: Any, fallback: int) -> int:
    for command in (":WAV:POIN?", ":ACQ:MDEP?"):
        text = safe_query(inst, command)
        if not text:
            continue
        clean = text.strip().upper()
        if clean == "AUTO":
            continue
        try:
            return int(float(clean))
        except ValueError:
            continue
    return fallback


def waveform_row(raw_value: int, index: int, preamble: dict[str, Any]) -> dict[str, float | int]:
    xinc = float(preamble.get("xincrement", 1.0))
    xorigin = float(preamble.get("xorigin", 0.0))
    xref = float(preamble.get("xreference", 0.0))
    yinc = float(preamble.get("yincrement", 1.0))
    yorigin = float(preamble.get("yorigin", 0.0))
    yref = float(preamble.get("yreference", 0.0))
    return {
        "time_s": (index - xref) * xinc + xorigin,
        "voltage_v": (raw_value - yorigin - yref) * yinc,
        "raw": raw_value,
    }


def write_waveform_output(path: Path, raw_data: bytes, preamble: dict[str, Any], start_point: int, output_format: str) -> None:
    if output_format == "json":
        samples = [
            waveform_row(raw_value, start_point - 1 + offset, preamble)
            for offset, raw_value in enumerate(raw_data)
        ]
        path.write_text(json.dumps({"preamble": preamble, "samples": samples}, indent=2), encoding="utf-8")
        return

    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=["time_s", "voltage_v", "raw"])
        writer.writeheader()
        for offset, raw_value in enumerate(raw_data):
            writer.writerow(waveform_row(raw_value, start_point - 1 + offset, preamble))


def cmd_scan(args: argparse.Namespace) -> int:
    pyvisa_available = True
    pyvisa_error: str | None = None
    resources: list[str] = []
    if not is_native_backend(args.backend):
        try:
            resources = list_visa_resources(args.backend)
        except SystemExit as exc:
            pyvisa_available = False
            pyvisa_error = str(exc).splitlines()[0]

    print("VISA resources:")
    if resources:
        for resource in resources:
            idn = query_idn(resource, args.backend, args.timeout_ms) if args.probe else None
            suffix = f"  idn={idn}" if idn else ""
            print(f"  {resource}{suffix}{marker_for(resource, idn)}")
    else:
        if pyvisa_available:
            print("  <none>")
        else:
            print(f"  <pyvisa unavailable: {pyvisa_error or 'backend error'}>")

    native_paths = windows_usbtmc_paths()
    if native_paths:
        print("Windows native USBTMC paths:")
        for path in native_paths:
            idn = None
            if args.probe:
                try:
                    idn = probe_native_idn(path, args.timeout_ms)
                except Exception as exc:
                    idn = f"<probe failed: {exc}>"
            suffix = f"  idn={idn}" if idn else ""
            print(f"  {path}{suffix}{marker_for(path, idn)}")

    pnp = windows_pnp_devices()
    if pnp:
        print("Windows PnP matches:")
        for item in pnp:
            status = item.get("Status", "")
            klass = item.get("Class", "")
            name = item.get("FriendlyName", "")
            instance = item.get("InstanceId", "")
            print(f"  {status} {klass} {name} {instance}{marker_for(instance, name)}")
    return 0


def cmd_idn(args: argparse.Namespace) -> int:
    inst = open_scope(args)
    try:
        print(ask(inst, "*IDN?"))
        return 0
    finally:
        close_scope(inst)


def cmd_status(args: argparse.Namespace) -> int:
    inst = open_scope(args)
    try:
        status = {
            "resource": getattr(inst, "_ds1202ze_resource", args.resource),
            "idn": ask(inst, "*IDN?"),
            "trigger_status": safe_query(inst, ":TRIG:STAT?"),
            "acquire_memory_depth": safe_query(inst, ":ACQ:MDEP?"),
            "timebase_scale_s_per_div": safe_query(inst, ":TIM:MAIN:SCAL?"),
            "timebase_offset_s": safe_query(inst, ":TIM:MAIN:OFFS?"),
            "channels": {},
            "error": safe_query(inst, ":SYST:ERR?"),
        }
        for ch in (1, 2):
            status["channels"][f"CHAN{ch}"] = {
                "display": safe_query(inst, f":CHAN{ch}:DISP?"),
                "scale_v_per_div": safe_query(inst, f":CHAN{ch}:SCAL?"),
                "offset_v": safe_query(inst, f":CHAN{ch}:OFFS?"),
                "coupling": safe_query(inst, f":CHAN{ch}:COUP?"),
                "probe": safe_query(inst, f":CHAN{ch}:PROB?"),
            }
        if args.json:
            print(json.dumps(status, indent=2))
        else:
            print(f"resource: {status['resource']}")
            print(f"idn: {status['idn']}")
            print(f"trigger_status: {status['trigger_status']}")
            print(f"timebase_scale_s_per_div: {status['timebase_scale_s_per_div']}")
            print(f"error: {status['error']}")
        return 0
    finally:
        close_scope(inst)


def cmd_acquire(args: argparse.Namespace) -> int:
    commands = {
        "run": ":RUN",
        "stop": ":STOP",
        "single": ":SING",
        "autoscale": ":AUT",
        "clear": ":CLE",
    }
    inst = open_scope(args)
    try:
        tell(inst, commands[args.command_name])
        if args.command_name == "autoscale":
            time.sleep(args.wait)
        return 0
    finally:
        close_scope(inst)


def cmd_channel(args: argparse.Namespace) -> int:
    ch = normalize_channel(args.channel)
    prefix = f":CHAN{ch}"
    inst = open_scope(args)
    try:
        if args.display is not None:
            tell(inst, f"{prefix}:DISP {normalize_on_off(args.display)}")
        if args.scale is not None:
            tell(inst, f"{prefix}:SCAL {args.scale}")
        if args.offset is not None:
            tell(inst, f"{prefix}:OFFS {args.offset}")
        if args.coupling is not None:
            tell(inst, f"{prefix}:COUP {args.coupling.upper()}")
        if args.probe is not None:
            tell(inst, f"{prefix}:PROB {args.probe}")
        if args.bwlimit is not None:
            tell(inst, f"{prefix}:BWL {normalize_on_off(args.bwlimit)}")
        result = {
            "channel": f"CHAN{ch}",
            "display": safe_query(inst, f"{prefix}:DISP?"),
            "scale_v_per_div": safe_query(inst, f"{prefix}:SCAL?"),
            "offset_v": safe_query(inst, f"{prefix}:OFFS?"),
            "coupling": safe_query(inst, f"{prefix}:COUP?"),
            "probe": safe_query(inst, f"{prefix}:PROB?"),
            "bwlimit": safe_query(inst, f"{prefix}:BWL?"),
        }
        print(json.dumps(result, indent=2))
        return 0
    finally:
        close_scope(inst)


def cmd_timebase(args: argparse.Namespace) -> int:
    inst = open_scope(args)
    try:
        if args.scale is not None:
            tell(inst, f":TIM:MAIN:SCAL {args.scale}")
        if args.offset is not None:
            tell(inst, f":TIM:MAIN:OFFS {args.offset}")
        result = {
            "scale_s_per_div": safe_query(inst, ":TIM:MAIN:SCAL?"),
            "offset_s": safe_query(inst, ":TIM:MAIN:OFFS?"),
            "mode": safe_query(inst, ":TIM:MODE?"),
        }
        print(json.dumps(result, indent=2))
        return 0
    finally:
        close_scope(inst)


def cmd_trigger_edge(args: argparse.Namespace) -> int:
    inst = open_scope(args)
    try:
        tell(inst, ":TRIG:MODE EDGE")
        if args.source is not None:
            tell(inst, f":TRIG:EDGE:SOUR {normalize_source(args.source)}")
        if args.slope is not None:
            tell(inst, f":TRIG:EDGE:SLOP {args.slope.upper()}")
        if args.level is not None:
            tell(inst, f":TRIG:EDGE:LEV {args.level}")
        if args.sweep is not None:
            tell(inst, f":TRIG:SWE {args.sweep.upper()}")
        result = {
            "mode": safe_query(inst, ":TRIG:MODE?"),
            "source": safe_query(inst, ":TRIG:EDGE:SOUR?"),
            "slope": safe_query(inst, ":TRIG:EDGE:SLOP?"),
            "level_v": safe_query(inst, ":TRIG:EDGE:LEV?"),
            "sweep": safe_query(inst, ":TRIG:SWE?"),
            "status": safe_query(inst, ":TRIG:STAT?"),
        }
        print(json.dumps(result, indent=2))
        return 0
    finally:
        close_scope(inst)


def cmd_measure(args: argparse.Namespace) -> int:
    source = normalize_source(args.source)
    item = normalize_measure_item(args.item)
    inst = open_scope(args)
    try:
        value = ask(inst, f":MEAS:ITEM? {item},{source}")
        result = {"item": item, "source": source, "value": value}
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(value)
        return 0
    finally:
        close_scope(inst)


def cmd_waveform(args: argparse.Namespace) -> int:
    source = normalize_source(args.source)
    mode = args.mode.upper()
    output = Path(args.output)
    output_format = args.output_format
    if output_format == "auto":
        output_format = "json" if output.suffix.lower() == ".json" else "csv"
    inst = open_scope(args)
    try:
        if mode == "RAW" and not args.no_stop:
            tell(inst, ":STOP")
            time.sleep(0.05)
        tell(inst, f":WAV:SOUR {source}")
        tell(inst, f":WAV:MODE {mode}")
        tell(inst, ":WAV:FORM BYTE")
        preamble = parse_preamble(ask(inst, ":WAV:PRE?"))
        fallback_points = int(preamble.get("points", 1200) or 1200)
        start_point = max(1, args.start)
        if args.stop is not None:
            stop_point = max(start_point, args.stop)
        else:
            points = args.points or query_wave_points(inst, fallback_points)
            stop_point = start_point + max(1, points) - 1
        chunk_points = max(1, min(args.chunk_points, RAW_BYTE_CHUNK_LIMIT))

        raw_data = bytearray()
        current = start_point
        while current <= stop_point:
            chunk_stop = min(stop_point, current + chunk_points - 1)
            expected = chunk_stop - current + 1
            tell(inst, f":WAV:STAR {current}")
            tell(inst, f":WAV:STOP {chunk_stop}")
            block = parse_ieee_block(query_binary(inst, ":WAV:DATA?", expected + 128))
            raw_data.extend(block[:expected])
            current = chunk_stop + 1

        output.parent.mkdir(parents=True, exist_ok=True)
        write_waveform_output(output, bytes(raw_data), preamble, start_point, output_format)
        if args.run_after:
            tell(inst, ":RUN")
        summary = {
            "output": str(output),
            "format": output_format,
            "source": source,
            "mode": mode,
            "points": len(raw_data),
            "start": start_point,
            "stop": start_point + len(raw_data) - 1,
        }
        print(json.dumps(summary, indent=2))
        return 0
    finally:
        close_scope(inst)


def cmd_screenshot(args: argparse.Namespace) -> int:
    output = Path(args.output)
    fmt = args.format.upper()
    inst = open_scope(args)
    try:
        raw = query_binary(inst, f":DISP:DATA? ON,OFF,{fmt}", args.max_read_bytes)
        payload = parse_ieee_block(raw)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(payload)
        print(json.dumps({"output": str(output), "bytes": len(payload), "format": fmt}, indent=2))
        return 0
    finally:
        close_scope(inst)


def cmd_query(args: argparse.Namespace) -> int:
    inst = open_scope(args)
    try:
        print(ask(inst, args.command))
        return 0
    finally:
        close_scope(inst)


def cmd_write(args: argparse.Namespace) -> int:
    inst = open_scope(args)
    try:
        tell(inst, args.command)
        if args.check_error:
            print(ask(inst, ":SYST:ERR?"))
        return 0
    finally:
        close_scope(inst)


def cmd_errors(args: argparse.Namespace) -> int:
    inst = open_scope(args)
    try:
        for _ in range(args.count):
            error = ask(inst, ":SYST:ERR?")
            print(error)
            if error.startswith("0"):
                break
        return 0
    finally:
        close_scope(inst)


def cmd_reset(args: argparse.Namespace) -> int:
    if not args.yes:
        raise SystemExit("Refusing to reset without --yes")
    inst = open_scope(args)
    try:
        tell(inst, "*RST")
        return 0
    finally:
        close_scope(inst)


def add_common(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--resource", help="VISA resource or native USBTMC path. Use the DS1202Z-E, not DM3058E.")
    parser.add_argument("--backend", help="PyVISA backend such as @ivi or @py; use 'native' for Windows USBTMC")
    parser.add_argument("--timeout-ms", type=int, default=8000, help="I/O timeout in milliseconds")
    parser.add_argument("--max-read-bytes", type=int, default=5_000_000, help="Maximum binary read size")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="RIGOL DS1202Z-E / DS1000Z-E USBTMC/VISA helper")
    add_common(parser)
    sub = parser.add_subparsers(dest="command_name", required=True)

    scan = sub.add_parser("scan", help="List VISA resources, native USBTMC paths, and Windows PnP matches")
    scan.add_argument("--probe", action="store_true", help="Query *IDN? for candidate instruments")
    scan.set_defaults(func=cmd_scan)

    idn = sub.add_parser("idn", help="Query *IDN? from the selected scope")
    idn.set_defaults(func=cmd_idn)

    status = sub.add_parser("status", help="Show identity, channel, timebase, trigger, and error state")
    status.add_argument("--json", action="store_true")
    status.set_defaults(func=cmd_status)

    for name in ("run", "stop", "single", "clear"):
        action = sub.add_parser(name, help=f"Send :{name.upper()} acquisition command")
        action.set_defaults(func=cmd_acquire)
    autoscale = sub.add_parser("autoscale", help="Autoscale the oscilloscope")
    autoscale.add_argument("--wait", type=float, default=8.0, help="Seconds to wait after autoscale")
    autoscale.set_defaults(func=cmd_acquire)

    channel = sub.add_parser("channel", help="Query or configure CHAN1/CHAN2")
    channel.add_argument("channel", help="1, 2, CHAN1, or CHAN2")
    channel.add_argument("--display", help="on/off")
    channel.add_argument("--scale", type=float, help="Volts per division")
    channel.add_argument("--offset", type=float, help="Vertical offset in volts")
    channel.add_argument("--coupling", choices=["AC", "DC", "GND", "ac", "dc", "gnd"])
    channel.add_argument("--probe", type=float, help="Probe ratio, e.g. 1, 10, 100")
    channel.add_argument("--bwlimit", help="on/off")
    channel.set_defaults(func=cmd_channel)

    timebase = sub.add_parser("timebase", help="Query or configure main timebase")
    timebase.add_argument("--scale", type=float, help="Seconds per division")
    timebase.add_argument("--offset", type=float, help="Horizontal offset in seconds")
    timebase.set_defaults(func=cmd_timebase)

    trigger = sub.add_parser("trigger", help="Configure trigger subsystem")
    trigger_sub = trigger.add_subparsers(dest="trigger_command", required=True)
    edge = trigger_sub.add_parser("edge", help="Configure edge trigger")
    edge.add_argument("--source", help="CHAN1 or CHAN2")
    edge.add_argument("--slope", choices=["POS", "NEG", "RFAL", "pos", "neg", "rfal"], help="Edge slope")
    edge.add_argument("--level", type=float, help="Trigger level in volts")
    edge.add_argument("--sweep", choices=["AUTO", "NORM", "SING", "auto", "norm", "sing"], help="Trigger sweep")
    edge.set_defaults(func=cmd_trigger_edge)

    measure = sub.add_parser("measure", help="Run :MEAS:ITEM? for a source")
    measure.add_argument("item", help="freq, period, vpp, vrms, vmax, etc.")
    measure.add_argument("--source", default="CHAN1", help="CHAN1 or CHAN2")
    measure.add_argument("--json", action="store_true")
    measure.set_defaults(func=cmd_measure)

    waveform = sub.add_parser("waveform", help="Capture waveform data to CSV or JSON")
    waveform.add_argument("source", help="CHAN1, CHAN2, or MATH")
    waveform.add_argument("output", help="Output .csv or .json")
    waveform.add_argument("--mode", default="NORM", choices=["NORM", "RAW", "MAX", "norm", "raw", "max"])
    waveform.add_argument("--start", type=int, default=1, help="First waveform point")
    waveform.add_argument("--stop", type=int, help="Last waveform point")
    waveform.add_argument("--points", type=int, help="Number of points to request when --stop is omitted")
    waveform.add_argument("--chunk-points", type=int, default=RAW_BYTE_CHUNK_LIMIT)
    waveform.add_argument("--output-format", choices=["auto", "csv", "json"], default="auto")
    waveform.add_argument("--no-stop", action="store_true", help="Do not send :STOP before RAW reads")
    waveform.add_argument("--run-after", action="store_true", help="Send :RUN after capture")
    waveform.set_defaults(func=cmd_waveform)

    screenshot = sub.add_parser("screenshot", help="Capture the display image to PNG or BMP")
    screenshot.add_argument("output", help="Output image path")
    screenshot.add_argument("--format", choices=["PNG", "BMP", "png", "bmp"], default="PNG")
    screenshot.set_defaults(func=cmd_screenshot)

    query = sub.add_parser("query", help="Send a raw SCPI query")
    query.add_argument("command", help="SCPI query ending in ?")
    query.set_defaults(func=cmd_query)

    write = sub.add_parser("write", help="Send a raw SCPI command")
    write.add_argument("command", help="SCPI command")
    write.add_argument("--check-error", action="store_true", help="Print :SYST:ERR? after write")
    write.set_defaults(func=cmd_write)

    errors = sub.add_parser("errors", help="Read the SCPI error queue")
    errors.add_argument("--count", type=int, default=8)
    errors.set_defaults(func=cmd_errors)

    reset = sub.add_parser("reset", help="Reset the oscilloscope with *RST")
    reset.add_argument("--yes", action="store_true", help="Confirm reset")
    reset.set_defaults(func=cmd_reset)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args) or 0)
    except KeyboardInterrupt:
        eprint("Interrupted")
        return 130
    except SystemExit:
        raise
    except Exception as exc:
        eprint(f"ERROR: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
