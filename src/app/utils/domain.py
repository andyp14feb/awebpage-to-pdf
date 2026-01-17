"""Domain extraction using eTLD+1 (main domain)."""
from urllib.parse import urlparse
from typing import Optional
from publicsuffixlist import PublicSuffixList
import logging

logger = logging.getLogger(__name__)

# Initialize public suffix list
psl = PublicSuffixList()


def extract_main_domain(url: str) -> str:
    """
    Extract main domain (eTLD+1) from URL.
    
    Examples:
        - https://a.example.com/path -> example.com
        - https://b.example.com/path -> example.com
        - https://example.co.uk/path -> example.co.uk
    
    Args:
        url: Full URL
        
    Returns:
        Main domain (eTLD+1)
        
    Raises:
        ValueError: If domain cannot be extracted
    """
    try:
        parsed = urlparse(url)
        hostname = parsed.hostname
        
        if not hostname:
            raise ValueError(f"Cannot extract hostname from URL: {url}")
        
        # Use public suffix list to get eTLD+1
        main_domain = psl.privatesuffix(hostname)
        
        if not main_domain:
            # Fallback: use full hostname
            logger.warning(f"Could not extract eTLD+1 for {hostname}, using full hostname")
            main_domain = hostname
        
        return main_domain.lower()
        
    except Exception as e:
        logger.error(f"Error extracting main domain from {url}: {e}")
        # Fallback to hostname
        parsed = urlparse(url)
        if parsed.hostname:
            return parsed.hostname.lower()
        raise ValueError(f"Cannot extract domain from URL: {url}")
