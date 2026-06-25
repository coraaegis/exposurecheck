from selfaudit.backends import HeuristicBackend, build_backend
from selfaudit.backends.transports import CloudTransport, LocalTransport
from selfaudit.safety import needs_cloud_ack, require_consent


def test_consent_flag_passes():
    assert require_consent(True) is True


def test_consent_interactive_accept_and_decline():
    out = []
    assert require_consent(False, input_fn=lambda _p: "I own this data", output_fn=out.append)
    assert require_consent(False, input_fn=lambda _p: "yes", output_fn=out.append)
    assert not require_consent(False, input_fn=lambda _p: "no", output_fn=out.append)


def test_backend_egress_flags():
    assert HeuristicBackend().sends_data_offsite is False
    local = build_backend("local", base_url="http://localhost:11434")
    assert local.sends_data_offsite is False and local.is_local is True
    cloud = build_backend("cloud", api_key="sk-test")
    assert cloud.sends_data_offsite is True and cloud.is_local is False


def test_cloud_ack_only_for_anonymous_account():
    cloud = build_backend("cloud", api_key="sk-test")
    local = build_backend("local")
    assert needs_cloud_ack(cloud, anon_account=True) is True
    assert needs_cloud_ack(cloud, anon_account=False) is False   # real-name acct: cloud is fine
    assert needs_cloud_ack(local, anon_account=True) is False    # local never egresses


def test_cloud_backend_requires_key():
    import pytest
    from selfaudit.backends import TransportError
    with pytest.raises(TransportError):
        build_backend("cloud", api_key="")
