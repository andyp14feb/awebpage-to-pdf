"""Unit tests for URL validation and SSRF protection."""
import pytest
from app.security.url_validator import (
    normalize_url,
    validate_url_format,
    validate_ssrf,
    is_private_ip,
    SSRFError
)


class TestURLNormalization:
    """Test URL normalization for deduplication."""
    
    def test_normalize_removes_trailing_slash(self):
        assert normalize_url("https://example.com/path/") == "https://example.com/path"
    
    def test_normalize_lowercase(self):
        assert normalize_url("HTTPS://EXAMPLE.COM/PATH") == "https://example.com/path"
    
    def test_normalize_removes_fragment(self):
        assert normalize_url("https://example.com/path#section") == "https://example.com/path"
    
    def test_normalize_preserves_query(self):
        url = normalize_url("https://example.com/path?key=value")
        assert "key=value" in url
    
    def test_normalize_root_path(self):
        assert normalize_url("https://example.com/") == "https://example.com/"


class TestURLValidation:
    """Test URL format validation."""
    
    def test_valid_http_url(self):
        validate_url_format("http://example.com")
    
    def test_valid_https_url(self):
        validate_url_format("https://example.com")
    
    def test_invalid_scheme(self):
        with pytest.raises(ValueError, match="http or https"):
            validate_url_format("ftp://example.com")
    
    def test_no_scheme(self):
        with pytest.raises(ValueError):
            validate_url_format("example.com")
    
    def test_empty_url(self):
        with pytest.raises(ValueError):
            validate_url_format("")
    
    def test_no_domain(self):
        with pytest.raises(ValueError):
            validate_url_format("https://")


class TestSSRFProtection:
    """Test SSRF protection."""
    
    def test_private_ip_detection(self):
        assert is_private_ip("127.0.0.1") is True
        assert is_private_ip("10.0.0.1") is True
        assert is_private_ip("192.168.1.1") is True
        assert is_private_ip("172.16.0.1") is True
    
    def test_public_ip_detection(self):
        assert is_private_ip("8.8.8.8") is False
        assert is_private_ip("1.1.1.1") is False
    
    def test_localhost_blocked(self):
        with pytest.raises(SSRFError, match="localhost"):
            validate_ssrf("http://localhost/")
    
    def test_private_ip_blocked(self):
        with pytest.raises(SSRFError, match="private IP"):
            validate_ssrf("http://127.0.0.1/")
    
    def test_metadata_endpoint_blocked(self):
        with pytest.raises(SSRFError, match="metadata"):
            validate_ssrf("http://169.254.169.254/")
    
    def test_public_domain_allowed(self):
        validate_ssrf("https://example.com")
