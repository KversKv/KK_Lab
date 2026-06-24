import socket
import struct
import time

from PySide6.QtCore import QObject, QThread, Signal


class NtpSyncWorker(QObject):
    synced = Signal(float, float)
    failed = Signal(str)
    finished = Signal()

    _NTP_SERVERS = (
        "pool.ntp.org",
        "time.windows.com",
        "time.google.com",
        "ntp.aliyun.com",
        "cn.pool.ntp.org",
    )
    _NTP_PORT = 123
    _NTP_DELTA = 2208988800.0
    _RESYNC_INTERVAL_S = 300.0
    _SOCKET_TIMEOUT_S = 3.0
    _RETRY_SLEEP_MS = 5000

    def __init__(self):
        super().__init__()
        self._running = True

    def stop(self):
        self._running = False

    def run(self):
        while self._running:
            offset = None
            rtt = None
            last_error = ""
            for server in self._NTP_SERVERS:
                if not self._running:
                    break
                try:
                    packet = bytearray(48)
                    packet[0] = 0x1B
                    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    sock.settimeout(self._SOCKET_TIMEOUT_S)
                    try:
                        t0 = time.time()
                        sock.sendto(bytes(packet), (server, self._NTP_PORT))
                        data, _ = sock.recvfrom(48)
                        t3 = time.time()
                    finally:
                        sock.close()
                    if len(data) < 48:
                        last_error = f"{server}: short response"
                        continue
                    recv_int, recv_frac = struct.unpack("!II", data[32:40])
                    tx_int, tx_frac = struct.unpack("!II", data[40:48])
                    t1 = (recv_int + recv_frac / 2 ** 32) - self._NTP_DELTA
                    t2 = (tx_int + tx_frac / 2 ** 32) - self._NTP_DELTA
                    rtt = (t3 - t0) - (t2 - t1)
                    offset = ((t1 - t0) + (t2 - t3)) / 2.0
                    break
                except Exception as e:
                    last_error = f"{server}: {e}"
                    continue

            if not self._running:
                break

            if offset is not None:
                self.synced.emit(offset, rtt or 0.0)
                slept = 0
                while self._running and slept < self._RESYNC_INTERVAL_S * 1000:
                    QThread.msleep(200)
                    slept += 200
            else:
                self.failed.emit(last_error or "All NTP servers unreachable")
                slept = 0
                while self._running and slept < self._RETRY_SLEEP_MS:
                    QThread.msleep(200)
                    slept += 200

        self.finished.emit()
