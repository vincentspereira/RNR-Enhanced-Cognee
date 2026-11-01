import socket
_original_connect=socket.socket.connect
_original_connect_ex=socket.socket.connect_ex
def _deny(self,address):
    if self.family in (socket.AF_INET,socket.AF_INET6):
        raise OSError('Audit guard: live network connections disabled during unit tests')
    return _original_connect(self,address)
def _deny_ex(self,address):
    if self.family in (socket.AF_INET,socket.AF_INET6):return 111
    return _original_connect_ex(self,address)
socket.socket.connect=_deny
socket.socket.connect_ex=_deny_ex
