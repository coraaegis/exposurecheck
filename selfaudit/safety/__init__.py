"""Consent gate and the conditional cloud-deanonymization warning."""

from .consent import CONSENT_TEXT, require_consent
from .warnings import cloud_warning_text, needs_cloud_ack

__all__ = ["CONSENT_TEXT", "require_consent", "cloud_warning_text", "needs_cloud_ack"]
