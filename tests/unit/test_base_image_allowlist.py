"""
Unit tests for base image allowlist validation (SEC-172).

Verifies that only approved Docker base images can be used for agent creation.
Prevents arbitrary image pull attacks that could expose internal network services.

Module: src/backend/services/agent_service/helpers.py
Issue: https://github.com/abilityai/trinity/issues/172
"""

import fnmatch
import json
import pytest
from unittest.mock import MagicMock

# ---- Inline reimplementation of the validation logic for unit testing ----
# This avoids importing the full backend dependency chain while testing
# the exact same algorithm used in helpers.py.

DEFAULT_BASE_IMAGE_ALLOWLIST = [
    "trinity-agent-base:*",
]


class ImageNotAllowedError(Exception):
    """Raised when image is not on the allowlist."""
    def __init__(self, detail: str, status_code: int = 403):
        self.detail = detail
        self.status_code = status_code


def validate_base_image(image: str, settings_service=None) -> None:
    """Mirror of helpers.validate_base_image for unit testing."""
    allowlist_json = settings_service.get_setting("base_image_allowlist") if settings_service else None
    if allowlist_json:
        try:
            allowlist = json.loads(allowlist_json)
            if not isinstance(allowlist, list):
                allowlist = DEFAULT_BASE_IMAGE_ALLOWLIST
        except json.JSONDecodeError:
            allowlist = DEFAULT_BASE_IMAGE_ALLOWLIST
    else:
        allowlist = DEFAULT_BASE_IMAGE_ALLOWLIST

    for pattern in allowlist:
        if fnmatch.fnmatch(image, pattern):
            return

    raise ImageNotAllowedError(
        detail=f"Base image '{image}' is not in the allowed image list. "
        f"Allowed patterns: {allowlist}"
    )


@pytest.fixture
def mock_settings():
    """Mock settings service — default returns None (use default allowlist)."""
    svc = MagicMock()
    svc.get_setting.return_value = None
    return svc


# =========================================================================
# Default allowlist tests
# =========================================================================

class TestDefaultAllowlist:
    """Tests with default allowlist (no custom setting)."""

    def test_default_trinity_image_allowed(self, mock_settings):
        validate_base_image("trinity-agent-base:latest", mock_settings)

    def test_versioned_trinity_image_allowed(self, mock_settings):
        validate_base_image("trinity-agent-base:1.0.0", mock_settings)
        validate_base_image("trinity-agent-base:v2.3.1", mock_settings)

    def test_arbitrary_image_blocked(self, mock_settings):
        with pytest.raises(ImageNotAllowedError) as exc_info:
            validate_base_image("alpine:latest", mock_settings)
        assert exc_info.value.status_code == 403
        assert "not in the allowed image list" in exc_info.value.detail

    def test_malicious_registry_blocked(self, mock_settings):
        with pytest.raises(ImageNotAllowedError):
            validate_base_image("evil.registry.io/backdoor:latest", mock_settings)

    def test_ubuntu_blocked(self, mock_settings):
        with pytest.raises(ImageNotAllowedError):
            validate_base_image("ubuntu:22.04", mock_settings)

    def test_empty_string_blocked(self, mock_settings):
        with pytest.raises(ImageNotAllowedError):
            validate_base_image("", mock_settings)

    def test_partial_name_match_blocked(self, mock_settings):
        """Prefixing allowed name shouldn't bypass the check."""
        with pytest.raises(ImageNotAllowedError):
            validate_base_image("not-trinity-agent-base:latest", mock_settings)

    def test_no_tag_blocked(self, mock_settings):
        """Image without a tag doesn't match 'name:*' pattern."""
        with pytest.raises(ImageNotAllowedError):
            validate_base_image("trinity-agent-base", mock_settings)


# =========================================================================
# Custom allowlist tests
# =========================================================================

class TestCustomAllowlist:
    """Tests with admin-configured custom allowlist."""

    def test_custom_allowlist_extends_images(self, mock_settings):
        mock_settings.get_setting.return_value = json.dumps([
            "trinity-agent-base:*",
            "my-custom-image:*",
        ])
        validate_base_image("my-custom-image:v1", mock_settings)

    def test_custom_allowlist_replaces_default(self, mock_settings):
        """Custom allowlist fully replaces default."""
        mock_settings.get_setting.return_value = json.dumps([
            "only-this-image:*",
        ])
        with pytest.raises(ImageNotAllowedError):
            validate_base_image("trinity-agent-base:latest", mock_settings)

    def test_custom_allowlist_with_registry_prefix(self, mock_settings):
        mock_settings.get_setting.return_value = json.dumps([
            "trinity-agent-base:*",
            "ghcr.io/myorg/*",
        ])
        validate_base_image("ghcr.io/myorg/agent:v1", mock_settings)

    def test_empty_allowlist_blocks_everything(self, mock_settings):
        """Empty list means nothing is allowed."""
        mock_settings.get_setting.return_value = json.dumps([])
        with pytest.raises(ImageNotAllowedError):
            validate_base_image("trinity-agent-base:latest", mock_settings)


# =========================================================================
# Malformed settings fallback tests
# =========================================================================

class TestMalformedSettings:
    """Tests that malformed settings fall back to default safely."""

    def test_invalid_json_falls_back(self, mock_settings):
        mock_settings.get_setting.return_value = "not-json"
        validate_base_image("trinity-agent-base:latest", mock_settings)

    def test_non_list_json_falls_back(self, mock_settings):
        mock_settings.get_setting.return_value = json.dumps("string-value")
        validate_base_image("trinity-agent-base:latest", mock_settings)

    def test_non_list_dict_falls_back(self, mock_settings):
        mock_settings.get_setting.return_value = json.dumps({"key": "value"})
        validate_base_image("trinity-agent-base:latest", mock_settings)

    def test_null_setting_uses_default(self, mock_settings):
        mock_settings.get_setting.return_value = None
        validate_base_image("trinity-agent-base:latest", mock_settings)

    def test_no_settings_service_uses_default(self):
        """When settings_service is None, default allowlist is used."""
        validate_base_image("trinity-agent-base:latest", None)


# =========================================================================
# Error message tests
# =========================================================================

class TestErrorMessages:
    """Tests that error messages are informative."""

    def test_error_includes_image_name(self, mock_settings):
        with pytest.raises(ImageNotAllowedError) as exc_info:
            validate_base_image("evil:latest", mock_settings)
        assert "evil:latest" in exc_info.value.detail

    def test_error_includes_allowlist(self, mock_settings):
        with pytest.raises(ImageNotAllowedError) as exc_info:
            validate_base_image("evil:latest", mock_settings)
        assert "trinity-agent-base:*" in exc_info.value.detail
