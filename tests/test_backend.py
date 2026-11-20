import time
import os
import sys
from pathlib import Path

# Add project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.config import APP_NAME, DEVELOPER, MODELS_DIR
from backend.database import (
    init_db, generate_api_key, verify_api_key, log_api_request, 
    get_db_connection, is_ip_blocked, set_ip_blocked_status
)
from backend.network_utils import is_private_lan_ip, get_primary_lan_ip
from backend.firewall import check_firewall_rule
from backend.inference import engine

def test_database_and_keys():
    init_db()
    raw_key, record = generate_api_key("Unit Test Key", rate_limit_rpm=30)
    assert raw_key.startswith("sk-local-")
    assert record["name"] == "Unit Test Key"
    
    # Verify raw key succeeds
    verified = verify_api_key(raw_key)
    assert verified is not None
    assert verified["name"] == "Unit Test Key"

    # Verify invalid key fails
    assert verify_api_key("sk-local-invalidkey1234567890") is None

def test_private_lan_ip_detection():
    # RFC 1918 Private and loopback
    assert is_private_lan_ip("127.0.0.1") is True
    assert is_private_lan_ip("192.168.1.15") is True
    assert is_private_lan_ip("10.0.0.5") is True
    assert is_private_lan_ip("172.16.5.10") is True
    
    # Public IPs should fail LAN check
    assert is_private_lan_ip("8.8.8.8") is False
    assert is_private_lan_ip("1.1.1.1") is False

def test_ip_blocking():
    test_ip = "192.168.1.250"
    set_ip_blocked_status(test_ip, True, reason="Testing Block")
    assert is_ip_blocked(test_ip) is True
    
    set_ip_blocked_status(test_ip, False)
    assert is_ip_blocked(test_ip) is False

def test_engine_lifecycle_offline():
    stats = engine.get_stats()
    assert "status" in stats
    assert stats["status"] in ["OFFLINE", "ONLINE", "STARTING", "ERROR"]

def test_firewall_status_check():
    fw = check_firewall_rule(port=8080)
    assert "supported" in fw
    assert "exists" in fw

if __name__ == "__main__":
    test_database_and_keys()
    print("Database & Keys test PASSED")
    test_private_lan_ip_detection()
    print("LAN IP detection test PASSED")
    test_ip_blocking()
    print("IP Blocking test PASSED")
    test_engine_lifecycle_offline()
    print("Engine lifecycle test PASSED")
    test_firewall_status_check()
    print("Firewall status test PASSED")
    print("\nALL BACKEND UNIT TESTS PASSED!")
