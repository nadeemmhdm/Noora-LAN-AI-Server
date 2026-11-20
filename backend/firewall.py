import subprocess
import sys
from typing import Dict, Any

RULE_NAME = "Noora LAN AI Server"

def check_firewall_rule(port: int = 8080) -> Dict[str, Any]:
    """Checks whether the Windows Firewall inbound rule for Noora AI Server exists."""
    if sys.platform != "win32":
        return {"supported": False, "exists": True, "message": "Non-Windows OS"}

    try:
        cmd = ["netsh", "advfirewall", "firewall", "show", "rule", f"name={RULE_NAME}"]
        res = subprocess.run(cmd, capture_output=True, text=True)
        exists = "No rules match" not in res.stdout and res.returncode == 0
        return {
            "supported": True,
            "exists": exists,
            "rule_name": RULE_NAME,
            "port": port,
            "details": res.stdout if exists else "No active rule found."
        }
    except Exception as e:
        return {
            "supported": True,
            "exists": False,
            "rule_name": RULE_NAME,
            "port": port,
            "error": str(e)
        }

def add_firewall_rule(port: int = 8080) -> Dict[str, Any]:
    """Adds an inbound rule for TCP traffic on the server port."""
    if sys.platform != "win32":
        return {"success": False, "message": "Firewall commands are only supported on Windows."}

    cmd = [
        "netsh", "advfirewall", "firewall", "add", "rule",
        f"name={RULE_NAME}",
        "dir=in",
        "action=allow",
        "protocol=TCP",
        f"localport={port}",
        "profile=private,domain"
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0 and "Ok." in res.stdout:
            return {"success": True, "message": f"Firewall rule '{RULE_NAME}' created for port {port}."}
        else:
            return {
                "success": False, 
                "message": f"Administrator privileges may be required to modify Windows Firewall: {res.stderr or res.stdout}"
            }
    except Exception as e:
        return {"success": False, "message": str(e)}

def remove_firewall_rule() -> Dict[str, Any]:
    """Removes the inbound rule for Noora AI Server."""
    if sys.platform != "win32":
        return {"success": False, "message": "Firewall commands are only supported on Windows."}

    cmd = ["netsh", "advfirewall", "firewall", "delete", "rule", f"name={RULE_NAME}"]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0:
            return {"success": True, "message": f"Firewall rule '{RULE_NAME}' removed."}
        else:
            return {"success": False, "message": res.stderr or res.stdout}
    except Exception as e:
        return {"success": False, "message": str(e)}
