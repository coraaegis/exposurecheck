import socket

import pytest

from exposurecheck.safety.offline import NetworkEgressBlocked, enforce_no_egress


def test_offline_blocks_offmachine_and_allows_loopback():
    orig_c, orig_cx = socket.socket.connect, socket.socket.connect_ex
    try:
        enforce_no_egress()
        # an off-machine target is refused BEFORE any bytes leave the machine
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        with pytest.raises(NetworkEgressBlocked):
            s.connect(("1.2.3.4", 80))
        s.close()
        # loopback (on-machine, e.g. local Ollama) must NOT be blocked; a refused /
        # in-progress OSError on a closed port is fine — the guard let it through.
        s2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s2.setblocking(False)
        try:
            s2.connect(("127.0.0.1", 9))
        except NetworkEgressBlocked:
            pytest.fail("loopback must not be blocked under --offline")
        except OSError:
            pass
        finally:
            s2.close()
    finally:
        socket.socket.connect, socket.socket.connect_ex = orig_c, orig_cx
