"""The conditional cloud-deanonymization warning.

local is NOT forced (that would shrink the audience to near-zero). Instead the
risk is stated precisely and conditionally: it bites only when an *anonymous*
account is audited through a *real-name* AI account. For a real-name / public
account, cloud is fine and the warning is informational.
"""

from __future__ import annotations

from ..backends.base import Backend


def cloud_warning_text() -> str:
    return (
        "CLOUD BACKEND SELECTED -- read before continuing:\n"
        "You are about to send your post history to a cloud AI provider.\n"
        "\n"
        "IF the account you are auditing is a pseudonymous one you keep separate from\n"
        "your real identity, AND your AI/cloud account is registered under your real\n"
        "name or paid with a real-name method, THEN the provider can link\n"
        "  real identity  <->  anonymous account\n"
        "on their side (exposed later via subpoena, breach or insider). That is exactly\n"
        "the deanonymization this tool exists to help you prevent -- you'd be doing it\n"
        "to yourself.\n"
        "\n"
        "  - Strictly-anonymous audit?  Use  --backend local  (no data leaves your\n"
        "    machine), or a cloud account opened and paid for anonymously.\n"
        "  - Auditing your real-name / public account?  Cloud is fine; this does not\n"
        "    apply to you."
    )


def needs_cloud_ack(backend: Backend, anon_account: bool) -> bool:
    """True when we must require an explicit acknowledgement before proceeding:
    a cloud backend AND the user flagged the audited account as anonymous."""
    return backend.sends_data_offsite and anon_account
