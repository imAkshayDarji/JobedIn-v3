import pytest

from app.services.url_validator import validate_apply_url


class TestValidateApplyUrl:
    def test_valid_https_url(self):
        is_valid, error = validate_apply_url("https://boards.greenhouse.io/company/jobs/123")
        assert is_valid is True
        assert error is None

    def test_valid_http_url(self):
        is_valid, error = validate_apply_url("http://example.com/jobs/123")
        assert is_valid is True
        assert error is None

    def test_blocks_private_ip_10(self):
        is_valid, error = validate_apply_url("https://10.0.0.1/jobs")
        assert is_valid is False
        assert "private" in error.lower()

    def test_blocks_private_ip_172(self):
        is_valid, error = validate_apply_url("https://172.16.0.1/jobs")
        assert is_valid is False
        assert "private" in error.lower()

    def test_blocks_private_ip_192_168(self):
        is_valid, error = validate_apply_url("https://192.168.1.1/jobs")
        assert is_valid is False
        assert "private" in error.lower()

    def test_blocks_loopback_127(self):
        is_valid, error = validate_apply_url("https://127.0.0.1/jobs")
        assert is_valid is False
        assert "127.0.0.1" in error

    def test_blocks_link_local_169_254(self):
        is_valid, error = validate_apply_url("https://169.254.1.1/jobs")
        assert is_valid is False
        assert "169.254.1.1" in error

    def test_blocks_localhost(self):
        is_valid, error = validate_apply_url("https://localhost/jobs")
        assert is_valid is False
        assert "blocked" in error.lower()

    def test_blocks_ipv6_loopback(self):
        is_valid, error = validate_apply_url("https://[::1]/jobs")
        assert is_valid is False

    def test_blocks_ftp_scheme(self):
        is_valid, error = validate_apply_url("ftp://example.com/jobs")
        assert is_valid is False
        assert "scheme" in error.lower()

    def test_blocks_no_scheme(self):
        is_valid, error = validate_apply_url("example.com/jobs")
        assert is_valid is False

    def test_blocks_empty_url(self):
        is_valid, error = validate_apply_url("")
        assert is_valid is False

    def test_blocks_whitespace_url(self):
        is_valid, error = validate_apply_url("   ")
        assert is_valid is False
