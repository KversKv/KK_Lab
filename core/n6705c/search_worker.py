# -*- coding: utf-8 -*-
"""
N6705C VISA 搜索 Worker（仅依赖 QtCore，无 QtWidgets）。

搜索策略（见 discover_n6705c）：
- 主发现：mDNS / DNS-SD 浏览 _hislip._tcp / _vxi-11._tcp，可跨子网发现
  所有 N6705C（本机与仪器不在同一 /24 网段时 list_resources 枚举不到）；
- 兜底发现：pyvisa list_resources()（覆盖 VISA 已配置 / 同网段设备）；
- 两路候选合并后，对每个候选并行 open + IDN 探测，只保留“探测成功”的地址；
- 按序列号聚合：优先 hislip（验证通过），否则回退 inst0；
- 结果地址规范化为 IP，避免目标机无 mDNS 解析 .local 主机名失败。
"""

import re
import socket
from concurrent.futures import ThreadPoolExecutor, as_completed

import pyvisa
from PySide6.QtCore import QThread, Signal

from log_config import get_logger

logger = get_logger(__name__)

# probe timeout（毫秒）：hislip 建链略慢，给稍高值；其它给较短值
_HISLIP_PROBE_TIMEOUT_MS = 1000
_DEFAULT_PROBE_TIMEOUT_MS = 500
_MAX_PROBE_WORKERS = 8

# mDNS 浏览等待时间（秒）：给设备回应留足时间又不过长
_MDNS_BROWSE_TIMEOUT_S = 3.0
# 只发现 N6705C；服务实例名形如
# "Keysight N6705C DC Power Analyzer - MY56006098._hislip._tcp.local."
_N6705C_NAME_RE = re.compile(r"N6705C", re.IGNORECASE)

# TCPIP0::<host>::<board>::INSTR 中提取 host 段
_TCPIP_HOST_RE = re.compile(r"^(TCPIP\d*)::([^:]+)::(.*)$", re.IGNORECASE)


def _mdns_discover_n6705c() -> list[str]:
    """通过 mDNS / DNS-SD 发现 N6705C，返回 VISA 资源地址候选列表。

    - 浏览 _hislip._tcp（对应 hislip0）与 _vxi-11._tcp（对应 inst0）；
    - 仅保留服务名中含 "N6705C" 的实例；
    - 地址用设备 IP 拼成 TCPIP0::<ip>::hislip0/inst0::INSTR。
    zeroconf 不可用或网络无 mDNS 时返回空列表（由 list_resources 兜底）。
    """
    try:
        from zeroconf import Zeroconf, ServiceBrowser
    except Exception:
        logger.debug("zeroconf unavailable, skip mDNS discovery", exc_info=True)
        return []

    import time

    # service_type -> board 后缀
    type_board = {
        "_hislip._tcp.local.": "hislip0",
        "_vxi-11._tcp.local.": "inst0",
    }
    resources: set[str] = set()

    class _Listener:
        def add_service(self, zc, service_type, name):
            if not _N6705C_NAME_RE.search(name):
                return
            board = type_board.get(service_type)
            if not board:
                return
            try:
                info = zc.get_service_info(service_type, name, timeout=2000)
            except Exception:
                info = None
            if not info:
                return
            for addr in info.addresses:
                try:
                    ip = socket.inet_ntoa(addr)
                except Exception:
                    continue
                resources.add(f"TCPIP0::{ip}::{board}::INSTR")

        def update_service(self, *args):
            pass

        def remove_service(self, *args):
            pass

    zc = None
    try:
        zc = Zeroconf()
        listener = _Listener()
        for service_type in type_board:
            ServiceBrowser(zc, service_type, listener)
        time.sleep(_MDNS_BROWSE_TIMEOUT_S)
    except Exception:
        logger.debug("mDNS discovery failed", exc_info=True)
    finally:
        if zc is not None:
            try:
                zc.close()
            except Exception:
                pass

    found = sorted(resources)
    logger.debug("mDNS N6705C candidates=%s", found)
    return found


def _probe_timeout_ms(resource: str) -> int:
    return _HISLIP_PROBE_TIMEOUT_MS if "hislip" in resource.lower() else _DEFAULT_PROBE_TIMEOUT_MS


def _is_probe_candidate(resource: str) -> bool:
    """只探测 N6705C 可能出现的资源类型，跳过串口等无关资源。"""
    upper = resource.upper()
    if upper.startswith("ASRL"):
        return False
    return upper.startswith(("TCPIP", "USB", "GPIB"))


def _normalize_host_to_ip(resource: str) -> str:
    """把 TCPIP 资源中的 .local mDNS 主机名解析为 IP，其它资源原样返回。"""
    match = _TCPIP_HOST_RE.match(resource)
    if not match:
        return resource
    prefix, host, tail = match.group(1), match.group(2), match.group(3)
    # 已是 IP 则无需解析
    if re.match(r"^\d{1,3}(\.\d{1,3}){3}$", host):
        return resource
    try:
        import socket
        ip = socket.gethostbyname(host)
        return f"{prefix}::{ip}::{tail}"
    except Exception:
        # 解析失败保留原地址（本机可能仍能靠 mDNS 连上）
        return resource


# --- 跨网段（跨 VLAN）主动扫描 ---------------------------------------------
# mDNS 是链路本地协议，广播到不了被路由器/VLAN 隔开的网段。对这些网段只能
# 主动扫描：对网段内每个 IP 探测 hislip 端口 4880，端口开的再交给 IDN 确认。
_HISLIP_PORT = 4880
_PORT_PROBE_TIMEOUT_S = 0.3
_MAX_SCAN_WORKERS = 64
_LAST_SCAN_HAD_EXTRA = False  # 记录本次是否配置了额外网段（供 UI 提示判断）


def _discovery_config_path() -> str:
    from ui.resource_path import get_user_data_dir
    import os
    return os.path.join(get_user_data_dir("n6705c"), "discovery.json")


def _load_extra_subnets() -> list[str]:
    """读取用户配置的额外扫描网段（CIDR，如 "10.31.40.0/24"）。

    配置文件：user_data/n6705c/discovery.json（打包后 %APPDATA%/KK_Lab/n6705c/）
    结构：{"extra_subnets": ["10.31.40.0/24", ...]}
    文件不存在时创建一个带注释字段的空模板，返回空列表。
    """
    import json
    import os

    path = _discovery_config_path()
    if not os.path.isfile(path):
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "_comment": "extra_subnets 里填要主动扫描的跨网段(CIDR)，"
                                    "例如 10.31.40.0/24；mDNS 只能发现本广播域内仪器。",
                        "extra_subnets": [],
                    },
                    f, indent=2, ensure_ascii=False,
                )
        except OSError:
            logger.debug("create discovery.json failed", exc_info=True)
        return []

    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f) or {}
        subnets = raw.get("extra_subnets", [])
        if not isinstance(subnets, list):
            return []
        return [str(s).strip() for s in subnets if str(s).strip()]
    except (OSError, json.JSONDecodeError):
        logger.debug("read discovery.json failed", exc_info=True)
        return []


def _tcp_port_open(ip: str, port: int, timeout: float) -> bool:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout)
    try:
        return sock.connect_ex((ip, port)) == 0
    except OSError:
        return False
    finally:
        try:
            sock.close()
        except OSError:
            pass


def _scan_subnets_for_n6705c() -> list[str]:
    """主动扫描用户配置的额外网段，返回开着 hislip 端口的 IP 拼成的资源地址。

    只做端口存活筛选（快），真正的型号确认仍由 _probe_one(*IDN?) 完成。
    """
    global _LAST_SCAN_HAD_EXTRA
    import ipaddress

    subnets = _load_extra_subnets()
    _LAST_SCAN_HAD_EXTRA = bool(subnets)
    if not subnets:
        return []

    hosts: list[str] = []
    for cidr in subnets:
        try:
            net = ipaddress.ip_network(cidr, strict=False)
        except ValueError:
            logger.debug("invalid subnet in discovery.json: %s", cidr)
            continue
        hosts.extend(str(h) for h in net.hosts())

    if not hosts:
        return []

    resources: list[str] = []
    try:
        with ThreadPoolExecutor(max_workers=min(_MAX_SCAN_WORKERS, len(hosts))) as pool:
            futures = {
                pool.submit(_tcp_port_open, ip, _HISLIP_PORT, _PORT_PROBE_TIMEOUT_S): ip
                for ip in hosts
            }
            for fut in as_completed(futures):
                ip = futures[fut]
                try:
                    if fut.result():
                        resources.append(f"TCPIP0::{ip}::hislip0::INSTR")
                except Exception:
                    continue
    except Exception:
        logger.debug("subnet scan failed", exc_info=True)

    found = sorted(resources)
    logger.debug("subnet scan hislip-open candidates=%s", found)
    return found


def _probe_one(resource: str):
    """对单个资源做 open + IDN 探测。返回 (serial, resource, idn) 或 None。

    每次探测使用独立的 ResourceManager：IVI-VISA 的 RM/session 非线程安全，
    多线程共享同一个 rm 会导致 viFindNext / viOpen 状态互相踩踏（枚举被打断）。
    """
    rm = None
    instr = None
    try:
        try:
            rm = pyvisa.ResourceManager()
        except Exception:
            rm = pyvisa.ResourceManager("@ni")
        instr = rm.open_resource(resource, timeout=_probe_timeout_ms(resource))
        idn = instr.query("*IDN?").strip()
        logger.debug("Probe %s -> IDN=%r", resource, idn)
        if "N6705" not in idn.upper():
            return None
        parts = idn.split(",")
        serial = parts[2].strip() if len(parts) > 2 else resource
        return serial, resource, idn
    except Exception:
        logger.debug("Probe %s failed", resource, exc_info=True)
        return None
    finally:
        if instr is not None:
            try:
                instr.close()
            except Exception:
                pass
        if rm is not None:
            try:
                rm.close()
            except Exception:
                pass


def _select_preferred(resources: list[str]) -> str:
    """同一序列号的多个可连地址中择优：hislip 优先，否则 inst0，否则任意。"""
    hislip = [r for r in resources if "hislip" in r.lower()]
    if hislip:
        return hislip[0]
    inst = [r for r in resources if "inst" in r.lower()]
    if inst:
        return inst[0]
    return resources[0]


def discover_n6705c_details() -> list[dict]:
    """发现所有可连的 N6705C，返回结构化信息列表。

    每项：{"resource": <规范化地址>, "serial": <序列号>, "idn": <IDN 原文>}
    - resource 已规范化（IP、优先 hislip）。
    """
    # 主发现：mDNS（本广播域内跨 /24 子网自动发现）。
    mdns_candidates = _mdns_discover_n6705c()

    # 跨 VLAN 发现：主动扫描用户配置的额外网段（mDNS 广播到不了的网段）。
    scan_candidates = _scan_subnets_for_n6705c()

    # 兜底发现：pyvisa list_resources（同网段 / VISA 已配置设备）。
    # 用一个临时 rm 取完列表后立即关闭，避免与探测线程各自的 rm/session 并发冲突。
    rm = None
    resources = []
    try:
        try:
            rm = pyvisa.ResourceManager()
        except Exception:
            rm = pyvisa.ResourceManager("@ni")
        resources = list(rm.list_resources()) or []
    except Exception:
        logger.debug("N6705C list_resources failed", exc_info=True)
    finally:
        if rm is not None:
            try:
                rm.close()
            except Exception:
                pass

    visa_candidates = [r for r in resources if _is_probe_candidate(r)]
    # 合并三路候选并去重（保序：mDNS > 主动扫描 > VISA）
    candidates = list(dict.fromkeys(mdns_candidates + scan_candidates + visa_candidates))
    logger.debug(
        "N6705C mdns=%s scan=%s visa=%s candidates=%s",
        mdns_candidates, scan_candidates, visa_candidates, candidates,
    )
    if not candidates:
        return []

    # 并行探测（每线程独立 rm），只收集验证通过的地址，按序列号聚合
    verified: dict[str, list[tuple[str, str]]] = {}
    try:
        with ThreadPoolExecutor(max_workers=min(_MAX_PROBE_WORKERS, len(candidates))) as pool:
            futures = {pool.submit(_probe_one, res): res for res in candidates}
            for fut in as_completed(futures):
                result = fut.result()
                if result is None:
                    continue
                serial, resource, idn = result
                verified.setdefault(serial, []).append((resource, idn))
    except Exception:
        logger.debug("N6705C probe failed", exc_info=True)
        return []

    details = []
    for serial, entries in verified.items():
        preferred = _select_preferred([r for r, _ in entries])
        idn = next((i for r, i in entries if r == preferred), "")
        details.append({
            "resource": _normalize_host_to_ip(preferred),
            "serial": serial,
            "idn": idn,
        })
    return details


def discover_n6705c() -> list[str]:
    """发现所有可连的 N6705C，返回规范化（IP、优先 hislip）后的地址列表。"""
    return [d["resource"] for d in discover_n6705c_details()]


def discovery_scope_hint() -> str | None:
    """搜索完成后给 UI 用的作用域提示（未配置跨网段时返回引导语，否则 None）。

    mDNS 只能发现本广播域内的仪器；被路由器/VLAN 隔开的其它网段（如
    10.31.40.x）需在 discovery.json 的 extra_subnets 里配置后才会被主动扫描。
    """
    if _LAST_SCAN_HAD_EXTRA:
        return None
    return (
        "当前仅能自动搜索本网段（同一广播域）的仪器。\n"
        "其它网段（被路由器/VLAN 隔开，如 10.31.40.x）的 N6705C 无法自动发现，\n"
        "如需搜索请在下列配置文件的 extra_subnets 中填写网段（CIDR）后重试：\n"
        f"{_discovery_config_path()}"
    )


class SearchThread(QThread):
    search_result = Signal(str, list)

    def __init__(self, label, parent=None):
        super().__init__(parent)
        self._label = label

    def run(self):
        found = discover_n6705c()
        self.search_result.emit(self._label, found)
