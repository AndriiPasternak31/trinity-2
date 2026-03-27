"""
Tests for SSRF prevention in skills library URL validation (SEC-179).

Validates that:
- Only github.com URLs are accepted
- Internal/private addresses are rejected
- Various bypass attempts are blocked
- Shorthand formats work correctly

Related: GitHub Issue #179 (pentest finding 3.2.2)
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src', 'backend'))

from utils.url_validation import validate_skills_library_url


class TestValidateSkillsLibraryUrl:
    """Test suite for skills library URL SSRF prevention."""

    # =========================================================================
    # Valid URLs — should be accepted
    # =========================================================================

    def test_valid_github_https_url(self):
        """Standard HTTPS github.com URL passes."""
        result = validate_skills_library_url("https://github.com/abilityai/skills-library")
        assert result == "https://github.com/abilityai/skills-library"

    def test_valid_github_www_url(self):
        """www.github.com is also accepted."""
        result = validate_skills_library_url("https://www.github.com/org/repo")
        assert result == "https://www.github.com/org/repo"

    def test_valid_shorthand_github_com(self):
        """Shorthand 'github.com/owner/repo' is accepted and prefixed."""
        result = validate_skills_library_url("github.com/abilityai/skills-library")
        assert "github.com" in result

    def test_valid_shorthand_owner_repo(self):
        """Shorthand 'owner/repo' format is accepted."""
        result = validate_skills_library_url("abilityai/skills-library")
        assert result == "abilityai/skills-library"

    def test_valid_github_url_with_trailing_slash(self):
        """Trailing slash doesn't affect validation."""
        result = validate_skills_library_url("https://github.com/org/repo/")
        assert result == "https://github.com/org/repo/"

    def test_valid_github_url_with_git_suffix(self):
        """URL with .git suffix is accepted."""
        result = validate_skills_library_url("https://github.com/org/repo.git")
        assert result == "https://github.com/org/repo.git"

    # =========================================================================
    # SSRF Attack Vectors — must be rejected
    # =========================================================================

    def test_reject_localhost(self):
        """Reject localhost URL — pentest reproduction."""
        with pytest.raises(ValueError, match="github.com"):
            validate_skills_library_url("https://127.0.0.1:8000")

    def test_reject_localhost_hostname(self):
        """Reject 'localhost' hostname."""
        with pytest.raises(ValueError, match="github.com"):
            validate_skills_library_url("https://localhost:8000")

    def test_reject_internal_ip_10(self):
        """Reject RFC 1918 private range 10.0.0.0/8."""
        with pytest.raises(ValueError, match="github.com"):
            validate_skills_library_url("https://10.0.0.1/repo")

    def test_reject_internal_ip_172(self):
        """Reject RFC 1918 private range 172.16.0.0/12."""
        with pytest.raises(ValueError, match="github.com"):
            validate_skills_library_url("https://172.28.0.1/repo")

    def test_reject_internal_ip_192(self):
        """Reject RFC 1918 private range 192.168.0.0/16."""
        with pytest.raises(ValueError, match="github.com"):
            validate_skills_library_url("https://192.168.1.1/repo")

    def test_reject_metadata_service(self):
        """Reject cloud metadata service IP."""
        with pytest.raises(ValueError, match="github.com"):
            validate_skills_library_url("https://169.254.169.254/latest/meta-data/")

    def test_reject_http_scheme(self):
        """Reject non-HTTPS scheme."""
        with pytest.raises(ValueError, match="HTTPS"):
            validate_skills_library_url("http://github.com/org/repo")

    def test_reject_ftp_scheme(self):
        """Reject FTP scheme."""
        with pytest.raises(ValueError, match="HTTPS"):
            validate_skills_library_url("ftp://github.com/org/repo")

    def test_reject_file_scheme(self):
        """Reject file:// scheme."""
        with pytest.raises(ValueError, match="HTTPS"):
            validate_skills_library_url("file:///etc/passwd")

    def test_reject_non_github_host(self):
        """Reject non-github.com hosts."""
        with pytest.raises(ValueError, match="github.com"):
            validate_skills_library_url("https://evil.com/org/repo")

    def test_reject_github_subdomain_bypass(self):
        """Reject github.com as a subdomain of another domain."""
        with pytest.raises(ValueError, match="github.com"):
            validate_skills_library_url("https://github.com.evil.com/org/repo")

    def test_reject_github_lookalike(self):
        """Reject domains that look like github.com but aren't."""
        with pytest.raises(ValueError, match="github.com"):
            validate_skills_library_url("https://githubxcom/org/repo")

    def test_reject_at_sign_bypass(self):
        """Reject URL with @ to try to redirect to different host."""
        with pytest.raises(ValueError, match="github.com"):
            validate_skills_library_url("https://github.com@evil.com/org/repo")

    def test_reject_empty_url(self):
        """Reject empty string."""
        with pytest.raises(ValueError, match="empty"):
            validate_skills_library_url("")

    def test_reject_whitespace_url(self):
        """Reject whitespace-only string."""
        with pytest.raises(ValueError, match="empty"):
            validate_skills_library_url("   ")

    def test_reject_ipv6_loopback(self):
        """Reject IPv6 loopback."""
        with pytest.raises(ValueError, match="github.com"):
            validate_skills_library_url("https://[::1]:8000/repo")

    def test_reject_localhost_shorthand(self):
        """Reject 'localhost/something' shorthand."""
        with pytest.raises(ValueError, match="github.com"):
            validate_skills_library_url("localhost/something")

    def test_reject_dot_prefix_shorthand(self):
        """Reject './path' shorthand (local filesystem)."""
        with pytest.raises(ValueError, match="github.com"):
            validate_skills_library_url("./local-path")

    def test_reject_zero_ip(self):
        """Reject 0.0.0.0 (binds to all interfaces)."""
        with pytest.raises(ValueError, match="github.com"):
            validate_skills_library_url("https://0.0.0.0:8000/repo")

    # =========================================================================
    # Edge Cases
    # =========================================================================

    def test_strips_whitespace(self):
        """Leading/trailing whitespace is stripped."""
        result = validate_skills_library_url("  https://github.com/org/repo  ")
        assert result == "https://github.com/org/repo"

    def test_case_insensitive_hostname(self):
        """Hostname check is case-insensitive."""
        result = validate_skills_library_url("https://GITHUB.COM/org/repo")
        assert result == "https://GITHUB.COM/org/repo"

    def test_github_with_port(self):
        """github.com with explicit port 443 is accepted."""
        result = validate_skills_library_url("https://github.com:443/org/repo")
        assert result == "https://github.com:443/org/repo"
