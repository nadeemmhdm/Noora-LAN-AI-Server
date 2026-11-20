import socket
import psutil
import ipaddress
from typing import List, Dict, Optional, Tuple

_hostname_cache: Dict[str, str] = {}

def get_network_interfaces() -> List[Dict[str, str]]:
    """Returns a list of all active network interfaces and their IPv4 addresses."""
    interfaces = []
    addrs = psutil.net_if_addrs()
    stats = psutil.net_if_stats()

    for iface_name, addr_list in addrs.items():
        is_up = stats[iface_name].isup if iface_name in stats else True
        if not is_up:
            continue
        for addr in addr_list:
            if addr.family == socket.AF_INET:
                ip = addr.address
                # Skip virtual loopback if other interfaces exist, but list them
                interfaces.append({
                    "name": iface_name,
                    "ip": ip,
                    "netmask": addr.netmask or "255.255.255.0",
                    "is_loopback": ip.startswith("127.")
                })
    return interfaces

def get_primary_lan_ip() -> str:
    """Detects the active outgoing LAN IPv4 address (e.g. 192.168.1.100)."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Does not actually transmit packets, just resolves the routing interface
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip

def is_private_lan_ip(ip_str: str) -> bool:
    """Verifies if an IP address belongs to RFC 1918 private LAN ranges or loopback."""
    if not ip_str:
        return False
    # Handle IPv6-mapped IPv4 e.g. ::ffff:192.168.1.5
    if ip_str.startswith("::ffff:"):
        ip_str = ip_str.replace("::ffff:", "")
    try:
        ip_obj = ipaddress.ip_address(ip_str)
        return ip_obj.is_private or ip_obj.is_loopback
    except ValueError:
        return False

def resolve_hostname(ip_str: str) -> str:
    """Resolves IP to hostname with in-memory caching."""
    if ip_str in _hostname_cache:
        return _hostname_cache[ip_str]
    try:
        hostname, _, _ = socket.gethostbyaddr(ip_str)
        _hostname_cache[ip_str] = hostname
        return hostname
    except Exception:
        _hostname_cache[ip_str] = ip_str
        return ip_str
