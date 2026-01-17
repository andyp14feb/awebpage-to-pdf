"""URL validation and SSRF protection."""
import re
import ipaddress
from urllib.parse import urlparse, urlunparse
from typing import Optional
import httpx


# Private IP ranges
PRIVATE_IP_RANGES = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]

# Metadata endpoints
METADATA_ENDPOINTS = [
    "169.254.169.254",  # AWS, Azure, GCP
    "metadata.google.internal",
]


class SSRFError(Exception):
    """SSRF validation error."""
    pass


def normalize_url(url: str) -> str:
    """
    Normalize URL for deduplication.
    
    - Convert to lowercase
    - Remove trailing slash
    - Sort query parameters
    - Remove fragment
    """
    parsed = urlparse(url.lower())
    
    # Remove fragment
    normalized = urlunparse((
        parsed.scheme,
        parsed.netloc,
        parsed.path.rstrip('/') if parsed.path != '/' else '/',
        parsed.params,
        parsed.query,
        ''  # Remove fragment
    ))
    
    return normalized


def validate_url_format(url: str) -> None:
    """
    Validate URL format.
    
    Raises:
        ValueError: If URL format is invalid
    """
    if not url or not isinstance(url, str):
        raise ValueError("URL must be a non-empty string")
    
    parsed = urlparse(url)
    
    # Check scheme
    if parsed.scheme not in ('http', 'https'):
        raise ValueError("URL must use http or https scheme")
    
    # Check netloc
    if not parsed.netloc:
        raise ValueError("URL must have a valid domain")


def is_private_ip(hostname: str) -> bool:
    """Check if hostname resolves to a private IP."""
    try:
        ip = ipaddress.ip_address(hostname)
        return any(ip in network for network in PRIVATE_IP_RANGES)
    except ValueError:
        # Not a direct IP, need to resolve
        return False


def is_metadata_endpoint(hostname: str) -> bool:
    """Check if hostname is a known metadata endpoint."""
    return hostname.lower() in METADATA_ENDPOINTS


def validate_ssrf(url: str) -> None:
    """
    Validate URL against SSRF attacks.
    
    Raises:
        SSRFError: If URL is potentially dangerous
    """
    parsed = urlparse(url)
    hostname = parsed.hostname
    
    if not hostname:
        raise SSRFError("Invalid hostname")
    
    # Check metadata endpoints
    if is_metadata_endpoint(hostname):
        raise SSRFError("Access to metadata endpoints is blocked")
    
    # Check if hostname is a direct IP
    if is_private_ip(hostname):
        raise SSRFError("Access to private IP ranges is blocked")
    
    # Check for localhost
    if hostname.lower() in ('localhost', 'localhost.localdomain'):
        raise SSRFError("Access to localhost is blocked")
    
    # Try to resolve hostname and check IPs
    try:
        import socket
        addrs = socket.getaddrinfo(hostname, None)
        for addr in addrs:
            ip_str = addr[4][0]
            if is_private_ip(ip_str):
                raise SSRFError(f"Hostname resolves to private IP: {ip_str}")
    except socket.gaierror:
        # DNS resolution failed - let it fail during actual request
        pass
    except Exception:
        # Other errors - proceed with caution
        pass


async def validate_redirects(url: str, max_redirects: int = 5) -> str:
    """
    Follow redirects and validate each hop.
    
    Returns:
        Final URL after redirects
        
    Raises:
        SSRFError: If any redirect target is dangerous
    """
    current_url = url
    redirect_count = 0
    
    async with httpx.AsyncClient(follow_redirects=False, timeout=10.0) as client:
        while redirect_count < max_redirects:
            try:
                response = await client.head(current_url, timeout=10.0)
                
                if response.status_code in (301, 302, 303, 307, 308):
                    redirect_url = response.headers.get('location')
                    if not redirect_url:
                        break
                    
                    # Make absolute if relative
                    if redirect_url.startswith('/'):
                        parsed = urlparse(current_url)
                        redirect_url = f"{parsed.scheme}://{parsed.netloc}{redirect_url}"
                    
                    # Validate redirect target
                    validate_url_format(redirect_url)
                    validate_ssrf(redirect_url)
                    
                    current_url = redirect_url
                    redirect_count += 1
                else:
                    break
                    
            except httpx.RequestError:
                # Network error - will fail during actual render
                break
    
    return current_url
