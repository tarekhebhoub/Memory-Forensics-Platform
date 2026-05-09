"""Heuristic + IOC-based detection over Volatility plugin output.

This module ships two layers:

* **Per-plugin detectors** — each `detect_<plugin>` function consumes the parsed
  rows for one plugin and returns a list of `Detection` objects.
* **Cross-plugin correlators** — `correlate(job_results)` runs after every
  plugin finishes and produces composite findings (e.g. "PID 1234 has injected
  code AND a public-IP connection AND was spawned by Word").

Each `Detection` carries a MITRE ATT&CK technique mapping so the UI / report
can present analyst-grade context.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Iterable

# ════════════════════════════════════════════════════════════════════
#  Catalogues
# ════════════════════════════════════════════════════════════════════

SUSPICIOUS_TOOLS = {
    "mimikatz", "procdump", "psexec", "wce.exe", "pwdump",
    "powersploit", "cobaltstrike", "meterpreter", "empire", "rubeus",
    "kerberoast", "bloodhound", "sharphound", "lazagne", "secretsdump",
    "impacket", "winpeas", "seatbelt", "sharpup", "sharpchrome",
    "nanodump", "ngrok", "frp", "chisel", "rclone.exe",
    "anydesk", "tightvnc",
}

KNOWN_MALWARE_MUTEXES = {
    "Global\\$BotMutex$", "Global\\$DBWinMutex", "Global\\PowerLockerMutex",
    "TrickBot", "EmotetMutex", "ZeroAccessMutex", "RYUKMUTEX",
    "Global\\552FFA80-3393-423d-8671-7BA046BB5906",  # Conti
    "DCEXEC", "WICI", "Global\\KOMODOMUTEXSPECIAL",
}

LOLBINS = {
    "powershell.exe", "cmd.exe", "wmic.exe", "mshta.exe", "rundll32.exe",
    "regsvr32.exe", "certutil.exe", "bitsadmin.exe", "schtasks.exe",
    "wscript.exe", "cscript.exe", "msbuild.exe", "installutil.exe",
    "regasm.exe", "regsvcs.exe", "csc.exe", "msxsl.exe", "forfiles.exe",
    "extexport.exe", "odbcconf.exe", "control.exe", "ie4uinit.exe",
    "fodhelper.exe", "cmstp.exe", "scriptrunner.exe",
}

SUSPICIOUS_CMD_TOKENS = (
    " -enc", " -encodedcommand", " -nop ", " -windowstyle hidden",
    " iex(", " invoke-expression", " downloadstring", " downloadfile",
    " frombase64string", " net.webclient", " bitstransfer",
    " add-mppreference", " set-mppreference",
    " hidden -ep bypass", " -exec bypass", " -ep bypass",
    " certutil -urlcache", " certutil -decode",
    " mshta vbscript:", " javascript:execute",
)

EXPECTED_PARENTS = {
    "lsass.exe":     {"wininit.exe"},
    "services.exe":  {"wininit.exe"},
    "winlogon.exe":  {"smss.exe", ""},
    "smss.exe":      {"system", ""},
    "csrss.exe":     {"smss.exe", ""},
    "wininit.exe":   {"smss.exe", ""},
    "explorer.exe":  {"userinit.exe", "explorer.exe", ""},
    "spoolsv.exe":   {"services.exe"},
    "svchost.exe":   {"services.exe"},
    "lsm.exe":       {"wininit.exe"},
    "taskhost.exe":  {"services.exe"},
    "taskhostw.exe": {"services.exe"},
    "dwm.exe":       {"winlogon.exe", "services.exe"},
}

SHELL_SPAWNING_PARENTS_BAD = {
    "winword.exe", "excel.exe", "powerpnt.exe", "outlook.exe", "onenote.exe",
    "msaccess.exe", "visio.exe", "acrord32.exe", "acrobat.exe",
    "chrome.exe", "msedge.exe", "firefox.exe",
}
SHELLS = {"powershell.exe", "cmd.exe", "wscript.exe", "cscript.exe",
          "mshta.exe", "regsvr32.exe", "rundll32.exe"}

SUSPICIOUS_PORTS = {
    1080, 1090, 4444, 4445, 5555, 6666, 6667, 7000, 8000, 8080,
    8443, 9001, 9050, 9999, 10000, 12345, 31337, 50050,
}

REG_PERSISTENCE_KEYS = (
    r"\software\microsoft\windows\currentversion\run",
    r"\software\microsoft\windows\currentversion\runonce",
    r"\software\microsoft\windows nt\currentversion\winlogon",
    r"\system\currentcontrolset\services",
    r"\software\microsoft\windows\currentversion\image file execution options",
    r"\software\classes\exefile\shell\open\command",
    r"appinit_dlls",
)

PRIVATE_NET_RE = re.compile(
    r"^(10\.|192\.168\.|172\.(1[6-9]|2\d|3[01])\.|127\.|169\.254\.|::1|fe80:|0\.0\.0\.0)"
)

SIGNED_DRIVER_DIRS = (r"\windows\system32\drivers\\", r"\windows\system32\\",
                      r"\systemroot\system32\\")
SIGNED_MODULE_DIRS = (r"\windows\system32\\", r"\windows\syswow64\\",
                      r"\program files\\", r"\program files (x86)\\")
SUSPICIOUS_DIRS = (r"\users\\", r"\appdata\\", r"\temp\\", r"\downloads\\",
                   r"\public\\", r"\programdata\\", r"\$recycle.bin\\",
                   r"\windows\temp\\", r"\perflogs\\")


@dataclass
class Detection:
    plugin: str
    severity: str
    score: int
    title: str
    message: str
    evidence: dict
    mitre: list[str] = field(default_factory=list)
    pid: str = ""


SEVERITY_WEIGHT = {"info": 1, "low": 5, "medium": 15, "high": 30, "critical": 50}


def _val(row, *keys: str, default: str = "") -> str:
    if not isinstance(row, dict):
        return default
    for k in keys:
        if k in row and row[k] is not None:
            return str(row[k])
        for variant in (k.lower(), k.upper(), k.capitalize()):
            if variant in row and row[variant] is not None:
                return str(row[variant])
    return default


def _path_under(value: str, dirs) -> bool:
    v = (value or "").lower().replace("/", "\\")
    return any(seg in v for seg in dirs)


# ════════════════════════════════════════════════════════════════════
#  Per-plugin detectors  (standard set)
# ════════════════════════════════════════════════════════════════════

def detect_malfind(rows):
    out = []
    for r in rows:
        proc = _val(r, "Process", "ImageFileName")
        pid = _val(r, "PID", "Pid")
        prot = _val(r, "Protection")
        notes = _val(r, "Notes")
        is_exec = "EXECUTE" in prot.upper()
        sev = "high" if is_exec else "medium"
        out.append(Detection(
            plugin="windows.malfind", severity=sev, score=SEVERITY_WEIGHT[sev],
            title="Possible code injection / hollowing",
            message=f"malfind reported suspicious memory in {proc} (PID {pid}). Protection={prot} {notes}".strip(),
            evidence={"pid": pid, "process": proc, "protection": prot, "notes": notes},
            mitre=["T1055", "T1055.012"], pid=pid,
        ))
    return out


def detect_pslist(rows):
    out = []
    by_pid = {_val(r, "PID", "Pid"): r for r in rows}
    for r in rows:
        name = _val(r, "ImageFileName", "Name", "Process").lower()
        pid = _val(r, "PID", "Pid")
        ppid = _val(r, "PPID", "Ppid")
        cmdline = _val(r, "Cmdline", "CommandLine", "cmd")

        if any(t in name for t in SUSPICIOUS_TOOLS) or \
           any(t in cmdline.lower() for t in SUSPICIOUS_TOOLS):
            out.append(Detection(
                plugin="windows.pslist", severity="critical",
                score=SEVERITY_WEIGHT["critical"],
                title="Known offensive tool present",
                message=f"Process '{name}' (PID {pid}) matches a known offensive toolname.",
                evidence={"pid": pid, "name": name, "cmdline": cmdline},
                mitre=["T1059", "T1003"], pid=pid,
            ))

        parent_name = _val(by_pid.get(ppid), "ImageFileName", "Name").lower()
        expected = EXPECTED_PARENTS.get(name)
        if expected is not None and parent_name not in expected:
            out.append(Detection(
                plugin="windows.pslist", severity="high",
                score=SEVERITY_WEIGHT["high"],
                title="Unexpected process parent",
                message=f"{name} (PID {pid}) was spawned by '{parent_name or 'unknown'}', "
                        f"expected one of {sorted(expected)}.",
                evidence={"pid": pid, "name": name, "ppid": ppid, "parent": parent_name},
                mitre=["T1036", "T1055"], pid=pid,
            ))

        if parent_name in SHELL_SPAWNING_PARENTS_BAD and name in SHELLS:
            out.append(Detection(
                plugin="windows.pslist", severity="critical",
                score=SEVERITY_WEIGHT["critical"],
                title="Office / browser spawned a shell",
                message=f"'{parent_name}' (PPID {ppid}) spawned '{name}' (PID {pid}) — "
                        f"classic phishing-payload behaviour.",
                evidence={"parent": parent_name, "child": name, "pid": pid, "ppid": ppid,
                          "cmdline": cmdline},
                mitre=["T1566.001", "T1059.001"], pid=pid,
            ))

        if name in LOLBINS and cmdline:
            cl = cmdline.lower()
            if any(s in cl for s in SUSPICIOUS_CMD_TOKENS):
                out.append(Detection(
                    plugin="windows.pslist", severity="high",
                    score=SEVERITY_WEIGHT["high"],
                    title="LOLBIN abuse / obfuscated command line",
                    message=f"{name} executed with suspicious flags: {cmdline[:200]}",
                    evidence={"pid": pid, "name": name, "cmdline": cmdline},
                    mitre=["T1059.001", "T1027"], pid=pid,
                ))

        path = _val(r, "Path", "FullPath", "ImageFilePath")
        if path and _path_under(path, SUSPICIOUS_DIRS):
            out.append(Detection(
                plugin="windows.pslist", severity="medium",
                score=SEVERITY_WEIGHT["medium"],
                title="Process running from user-writable path",
                message=f"{name} (PID {pid}) executes from '{path}'.",
                evidence={"pid": pid, "name": name, "path": path},
                mitre=["T1036.005"], pid=pid,
            ))
    return out


def detect_cmdline(rows):
    out = []
    for r in rows:
        cmd = _val(r, "Args", "Cmdline", "CommandLine")
        proc = _val(r, "Process", "ImageFileName")
        pid = _val(r, "PID", "Pid")
        cl = cmd.lower()
        if any(t in cl for t in SUSPICIOUS_CMD_TOKENS):
            out.append(Detection(
                plugin="windows.cmdline", severity="high",
                score=SEVERITY_WEIGHT["high"],
                title="Suspicious / obfuscated command line",
                message=f"{proc} (PID {pid}): {cmd[:200]}",
                evidence={"pid": pid, "process": proc, "cmdline": cmd},
                mitre=["T1027", "T1059"], pid=pid,
            ))
    return out


def detect_netscan(rows):
    out = []
    for r in rows:
        foreign = _val(r, "ForeignAddr", "ForeignAddress", "foreign_addr")
        fport = _val(r, "ForeignPort", "foreign_port") or "0"
        proc = _val(r, "Owner", "Process", "owner")
        pid = _val(r, "PID", "Pid")
        state = _val(r, "State", "state")
        try:
            port_n = int(fport)
        except ValueError:
            port_n = 0

        if port_n in SUSPICIOUS_PORTS:
            out.append(Detection(
                plugin="windows.netscan", severity="high",
                score=SEVERITY_WEIGHT["high"],
                title="Connection on suspicious / C2 port",
                message=f"{proc} → {foreign}:{port_n} ({state})",
                evidence={"process": proc, "foreign": foreign, "port": port_n,
                          "state": state, "pid": pid},
                mitre=["T1571", "T1095"], pid=pid,
            ))

        if foreign and not PRIVATE_NET_RE.match(foreign) and \
                foreign not in {"*", "::"} and port_n > 1024 and \
                state.upper() in {"ESTABLISHED", "SYN_SENT"}:
            out.append(Detection(
                plugin="windows.netscan", severity="medium",
                score=SEVERITY_WEIGHT["medium"],
                title="Outbound connection to public IP",
                message=f"{proc} connected to public IP {foreign}:{port_n} ({state})",
                evidence={"process": proc, "foreign": foreign, "port": port_n,
                          "state": state, "pid": pid},
                mitre=["T1071"], pid=pid,
            ))
    return out


def detect_svcscan(rows):
    out = []
    for r in rows:
        binary = _val(r, "Binary", "BinaryPath").lower()
        name = _val(r, "Name", "ServiceName")
        state = _val(r, "State")
        if binary and _path_under(binary, SUSPICIOUS_DIRS):
            out.append(Detection(
                plugin="windows.svcscan", severity="high",
                score=SEVERITY_WEIGHT["high"],
                title="Service binary in unusual location",
                message=f"Service '{name}' ({state}) points at '{binary}'.",
                evidence={"name": name, "binary": binary, "state": state},
                mitre=["T1543.003"],
            ))
    return out


# ════════════════════════════════════════════════════════════════════
#  Per-plugin detectors  (deep set)
# ════════════════════════════════════════════════════════════════════

def detect_ldrmodules(rows):
    """Process hollowing: a DLL present in only some of the three loader lists."""
    out = []
    for r in rows:
        in_load = str(_val(r, "InLoad", "InLoadOrderModuleList")).lower() == "true"
        in_init = str(_val(r, "InInit", "InInitOrderModuleList")).lower() == "true"
        in_mem = str(_val(r, "InMem", "InMemoryOrderModuleList")).lower() == "true"
        if not (in_load and in_init and in_mem):
            pid = _val(r, "Pid", "PID")
            proc = _val(r, "Process", "ImageFileName")
            mp = _val(r, "MappedPath", "Path")
            if not mp:
                continue
            out.append(Detection(
                plugin="windows.ldrmodules", severity="high",
                score=SEVERITY_WEIGHT["high"],
                title="DLL missing from a loader list (process hollowing)",
                message=f"PID {pid} ({proc}) loaded '{mp}' "
                        f"with InLoad={in_load} InInit={in_init} InMem={in_mem}.",
                evidence={"pid": pid, "process": proc, "path": mp,
                          "InLoad": in_load, "InInit": in_init, "InMem": in_mem},
                mitre=["T1055.012"], pid=pid,
            ))
    return out


def detect_dlllist(rows):
    out = []
    for r in rows:
        path = _val(r, "Path", "DllPath", "FullDllName")
        proc = _val(r, "Process", "ImageFileName")
        pid = _val(r, "PID", "Pid")
        if path and _path_under(path, (r"\users\\", r"\appdata\\", r"\temp\\",
                                       r"\public\\", r"\downloads\\",
                                       r"\$recycle.bin\\")):
            out.append(Detection(
                plugin="windows.dlllist", severity="medium",
                score=SEVERITY_WEIGHT["medium"],
                title="DLL loaded from user-writable path",
                message=f"{proc} (PID {pid}) loaded '{path}'.",
                evidence={"pid": pid, "process": proc, "dll": path},
                mitre=["T1574.002"], pid=pid,
            ))
    return out


def detect_callbacks(rows):
    out = []
    safe = ("ntoskrnl", "ntkrnlmp", "win32k", "fltmgr", "tcpip", "ndis",
            "wdf01000", "ksecdd", "msrpc", "fastfat", "ntfs", "fileinfo",
            "ci.dll", "wcifs", "luafv", "mountmgr", "afd.sys", "netio",
            "cng.sys", "fwpkclnt", "rdyboost", "wof.sys", "volsnap",
            "fvevol", "iorate", "storport")
    for r in rows:
        module = _val(r, "Module", "Owner").lower()
        ctype = _val(r, "Type", "Callback")
        detail = _val(r, "Detail", "Symbol")
        if module and not any(m in module for m in safe):
            out.append(Detection(
                plugin="windows.callbacks", severity="high",
                score=SEVERITY_WEIGHT["high"],
                title="Non-Microsoft kernel callback",
                message=f"Callback type {ctype} owned by '{module}' ({detail}).",
                evidence={"type": ctype, "module": module, "detail": detail},
                mitre=["T1547.013"],
            ))
    return out


def detect_ssdt(rows):
    out = []
    for r in rows:
        module = _val(r, "Module", "Owner").lower()
        if module and "ntoskrnl" not in module and "win32k" not in module:
            out.append(Detection(
                plugin="windows.ssdt", severity="critical",
                score=SEVERITY_WEIGHT["critical"],
                title="SSDT hook detected",
                message=f"SSDT entry owned by '{module}' — likely rootkit hook.",
                evidence=r, mitre=["T1014"],
            ))
    return out


def detect_driverscan(rows):
    out = []
    for r in rows:
        path = _val(r, "Path", "DriverName", "Name").lower()
        if not path:
            continue
        if not _path_under(path, SIGNED_DRIVER_DIRS) and any(
                s in path for s in (r"\users\\", r"\temp\\", r"\appdata\\",
                                    r"\programdata\\")):
            out.append(Detection(
                plugin="windows.driverscan", severity="critical",
                score=SEVERITY_WEIGHT["critical"],
                title="Driver loaded from non-standard path",
                message=f"Driver '{path}' is outside system32\\drivers — possible rootkit.",
                evidence=r, mitre=["T1014", "T1543.003"],
            ))
    return out


def detect_modules(rows):
    out = []
    for r in rows:
        path = _val(r, "Path", "FullName").lower()
        name = _val(r, "Name")
        if path and not _path_under(path, SIGNED_MODULE_DIRS) \
                and _path_under(path, SUSPICIOUS_DIRS):
            out.append(Detection(
                plugin="windows.modules", severity="high",
                score=SEVERITY_WEIGHT["high"],
                title="Kernel module from user-writable path",
                message=f"Module '{name}' loaded from '{path}'.",
                evidence=r, mitre=["T1543"],
            ))
    return out


def detect_mutantscan(rows):
    out = []
    for r in rows:
        name = _val(r, "Name")
        if not name:
            continue
        for known in KNOWN_MALWARE_MUTEXES:
            if known.lower() in name.lower():
                out.append(Detection(
                    plugin="windows.mutantscan", severity="critical",
                    score=SEVERITY_WEIGHT["critical"],
                    title="Known malware mutex present",
                    message=f"Mutex '{name}' matches a known malware family fingerprint.",
                    evidence=r, mitre=["T1027"],
                ))
                break
    return out


def detect_envars(rows):
    out = []
    for r in rows:
        var = _val(r, "Variable", "Name").lower()
        val = _val(r, "Value")
        if var in ("psmodulepath", "path") and _path_under(val, SUSPICIOUS_DIRS):
            out.append(Detection(
                plugin="windows.envars", severity="medium",
                score=SEVERITY_WEIGHT["medium"],
                title="Environment variable hijack",
                message=f"{var.upper()} contains user-writable path: {val[:200]}",
                evidence=r, mitre=["T1574.007"],
            ))
    return out


def detect_privileges(rows):
    out = []
    sensitive = {"sedebugprivilege", "seimpersonateprivilege",
                 "setcbprivilege", "seloaddriverprivilege",
                 "setakeownershipprivilege"}
    system_procs = {"lsass.exe", "services.exe", "system", "wininit.exe",
                    "winlogon.exe", "csrss.exe", "smss.exe", ""}
    for r in rows:
        proc = _val(r, "Process", "ImageFileName").lower()
        pid = _val(r, "PID", "Pid")
        priv = _val(r, "Privilege").lower()
        enabled = str(_val(r, "Enabled")).lower() == "true"
        if priv in sensitive and enabled and proc and proc not in system_procs:
            out.append(Detection(
                plugin="windows.privileges", severity="medium",
                score=SEVERITY_WEIGHT["medium"],
                title="Sensitive privilege held by non-system process",
                message=f"{proc} (PID {pid}) has {priv} enabled.",
                evidence=r, mitre=["T1134"], pid=pid,
            ))
    return out


def detect_handles(rows):
    out = []
    for r in rows:
        htype = _val(r, "Type").lower()
        name = _val(r, "Name").lower()
        proc = _val(r, "Process")
        pid = _val(r, "PID", "Pid")
        if htype == "process" and "lsass.exe" in name:
            if proc and "lsass.exe" not in proc.lower() and proc.lower() not in (
                    "system", "wininit.exe", "services.exe"):
                out.append(Detection(
                    plugin="windows.handles", severity="critical",
                    score=SEVERITY_WEIGHT["critical"],
                    title="Handle to LSASS from non-system process",
                    message=f"{proc} (PID {pid}) holds a handle to LSASS — credential dump?",
                    evidence=r, mitre=["T1003.001"], pid=pid,
                ))
    return out


def detect_filescan(rows):
    out = []
    seen = 0
    for r in rows:
        name = _val(r, "Name", "Path").lower()
        if any(name.endswith(ext) for ext in (".exe", ".dll", ".ps1", ".vbs",
                                              ".js", ".bat", ".cmd", ".scr",
                                              ".hta", ".jse", ".vbe", ".lnk")):
            if _path_under(name, (r"\$recycle.bin\\", r"\windows\temp\\",
                                  r"\users\public\\", r"\perflogs\\")):
                seen += 1
                if seen > 100:  # cap noise
                    continue
                out.append(Detection(
                    plugin="windows.filescan", severity="medium",
                    score=SEVERITY_WEIGHT["medium"],
                    title="Executable in unusual location",
                    message=f"File '{name}' present in unusual path.",
                    evidence=r, mitre=["T1036.005"],
                ))
    return out


def detect_registry(rows):
    out = []
    for r in rows:
        key = _val(r, "Key").lower()
        value = _val(r, "Data", "Value")
        name = _val(r, "Name")
        if any(p in key for p in REG_PERSISTENCE_KEYS) and value:
            if _path_under(value, SUSPICIOUS_DIRS):
                out.append(Detection(
                    plugin="windows.registry.printkey", severity="high",
                    score=SEVERITY_WEIGHT["high"],
                    title="Persistence registry value points to suspicious path",
                    message=f"{key}\\{name} = {value[:200]}",
                    evidence=r, mitre=["T1547.001"],
                ))
            elif any(s in value.lower() for s in
                     ("powershell", "cmd /c", "mshta ", "rundll32 ")):
                out.append(Detection(
                    plugin="windows.registry.printkey", severity="medium",
                    score=SEVERITY_WEIGHT["medium"],
                    title="Persistence key invokes a shell / LOLBIN",
                    message=f"{key}\\{name} = {value[:200]}",
                    evidence=r, mitre=["T1547.001", "T1059"],
                ))
    return out


def _noop(rows):
    return []


# ════════════════════════════════════════════════════════════════════
#  Cross-plugin correlation
# ════════════════════════════════════════════════════════════════════

def correlate(results: dict) -> list[Detection]:
    out: list[Detection] = []

    # 1. Hidden processes (psscan ∖ pslist)
    pslist_pids = {_val(r, "PID", "Pid")
                   for r in results.get("windows.pslist", [])}
    for r in results.get("windows.psscan", []):
        pid = _val(r, "PID", "Pid")
        name = _val(r, "ImageFileName", "Name")
        if pid and pid not in pslist_pids and pid != "0":
            out.append(Detection(
                plugin="xview.process", severity="critical",
                score=SEVERITY_WEIGHT["critical"],
                title="Hidden process (cross-view discrepancy)",
                message=f"PID {pid} ({name}) found by psscan but not pslist — likely rootkit / DKOM.",
                evidence={"pid": pid, "name": name},
                mitre=["T1014", "T1055"], pid=pid,
            ))

    # 2. Hidden kernel modules (modscan ∖ modules)
    mods = {_val(r, "Name").lower() for r in results.get("windows.modules", [])}
    for r in results.get("windows.modscan", []):
        name = _val(r, "Name").lower()
        if name and mods and name not in mods:
            out.append(Detection(
                plugin="xview.module", severity="critical",
                score=SEVERITY_WEIGHT["critical"],
                title="Hidden kernel module",
                message=f"Module '{name}' visible to modscan but missing from modules list.",
                evidence=r, mitre=["T1014"],
            ))

    # 3. Injected process beaconing combo
    malfind_pids = {_val(r, "PID", "Pid")
                    for r in results.get("windows.malfind", [])}
    for r in results.get("windows.netscan", []):
        pid = _val(r, "PID", "Pid")
        foreign = _val(r, "ForeignAddr", "ForeignAddress")
        if pid and pid in malfind_pids and foreign and not PRIVATE_NET_RE.match(foreign):
            out.append(Detection(
                plugin="xview.implant", severity="critical",
                score=SEVERITY_WEIGHT["critical"],
                title="Injected process beaconing to public IP",
                message=f"PID {pid} has injected memory AND an outbound connection to {foreign}.",
                evidence={"pid": pid, "foreign": foreign},
                mitre=["T1055", "T1071"], pid=pid,
            ))

    return out


# ════════════════════════════════════════════════════════════════════
#  Registry
# ════════════════════════════════════════════════════════════════════

DETECTORS = {
    # Standard
    "windows.malfind":           detect_malfind,
    "windows.pslist":            detect_pslist,
    "windows.cmdline":           detect_cmdline,
    "windows.netscan":           detect_netscan,
    "windows.svcscan":           detect_svcscan,
    # Deep
    "windows.ldrmodules":        detect_ldrmodules,
    "windows.dlllist":           detect_dlllist,
    "windows.callbacks":         detect_callbacks,
    "windows.ssdt":              detect_ssdt,
    "windows.driverscan":        detect_driverscan,
    "windows.modules":           detect_modules,
    "windows.modscan":           _noop,
    "windows.mutantscan":        detect_mutantscan,
    "windows.envars":            detect_envars,
    "windows.privileges":        detect_privileges,
    "windows.handles":           detect_handles,
    "windows.filescan":          detect_filescan,
    "windows.registry.printkey": detect_registry,
    "windows.registry.userassist": _noop,
    "windows.psscan":            _noop,
    "windows.pstree":            _noop,
}


def aggregate(detections: Iterable[Detection]) -> int:
    detections = list(detections)
    if not detections:
        return 0
    total = sum(d.score for d in detections)
    score = int(100 * (1 - math.exp(-total / 200)))
    return min(100, max(0, score))
