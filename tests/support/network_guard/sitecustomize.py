"""Unit-test guard: refuse live TCP connections without breaking local IPC."""
import socket

_connect = socket.socket.connect
_connect_ex = socket.socket.connect_ex


def _deny_network(self, address):
    if self.family in (socket.AF_INET, socket.AF_INET6):
        raise OSError("Unit-test guard: live network connections are disabled")
    return _connect(self, address)


def _deny_network_ex(self, address):
    if self.family in (socket.AF_INET, socket.AF_INET6):
        return 111
    return _connect_ex(self, address)


socket.socket.connect = _deny_network
socket.socket.connect_ex = _deny_network_ex
