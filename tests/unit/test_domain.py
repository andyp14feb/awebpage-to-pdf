"""Unit tests for domain extraction."""
import pytest
from app.utils.domain import extract_main_domain


class TestDomainExtraction:
    """Test eTLD+1 domain extraction."""
    
    def test_simple_domain(self):
        assert extract_main_domain("https://example.com/path") == "example.com"
    
    def test_subdomain(self):
        assert extract_main_domain("https://www.example.com/path") == "example.com"
    
    def test_multiple_subdomains(self):
        assert extract_main_domain("https://a.b.example.com/path") == "example.com"
    
    def test_co_uk_domain(self):
        assert extract_main_domain("https://example.co.uk/path") == "example.co.uk"
    
    def test_subdomain_co_uk(self):
        assert extract_main_domain("https://www.example.co.uk/path") == "example.co.uk"
    
    def test_case_insensitive(self):
        assert extract_main_domain("HTTPS://EXAMPLE.COM/PATH") == "example.com"
