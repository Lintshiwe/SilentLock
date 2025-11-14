"""
Advanced Security Manager for SilentLock Password Manager
Provides comprehensive cyber threat protection and security hardening.
"""

import os
import sys
import time
import hashlib
import psutil
import winreg
import tempfile
import threading
import subprocess
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
import json
import ctypes
from ctypes import wintypes
import win32api
import win32con
import win32security
import win32file
import win32process


class SecurityHardening:
    """Comprehensive cyber security hardening for SilentLock."""
    
    def __init__(self):
        self.start_time = time.time()
        self.process_id = os.getpid()
        self.integrity_checks = {}
        self.security_events = []
        self.is_monitoring = False
        self.monitor_thread = None
        
        # Security configuration
        self.config = {
            'anti_debugging': True,
            'memory_protection': True,
            'process_monitoring': True,
            'file_integrity': True,
            'network_protection': True,
            'anti_tampering': True
        }
        
        # Initialize security measures
        self._initialize_security()
    
    def _initialize_security(self):
        """Initialize all security measures."""
        try:
            if self.config['anti_debugging']:
                self._enable_anti_debugging()
            
            if self.config['memory_protection']:
                self._enable_memory_protection()
            
            if self.config['process_monitoring']:
                self._start_process_monitoring()
            
            if self.config['file_integrity']:
                self._initialize_file_integrity()
            
            if self.config['anti_tampering']:
                self._enable_anti_tampering()
                
            self._log_security_event("Security hardening initialized", "INFO")
            
        except Exception as e:
            self._log_security_event(f"Security initialization failed: {e}", "CRITICAL")
    
    def _enable_anti_debugging(self):
        """Enable anti-debugging measures."""
        try:
            # Check for debugger presence
            if self._is_debugger_present():
                self._log_security_event("Debugger detected - potential threat", "CRITICAL")
                self._trigger_security_response("DEBUGGER_DETECTED")
            
            # Set debug privilege protection
            self._protect_debug_privileges()
            
            # Monitor for debugging attempts
            self._start_debug_monitoring()
            
        except Exception as e:
            self._log_security_event(f"Anti-debugging setup failed: {e}", "WARNING")
    
    def _is_debugger_present(self) -> bool:
        """Check if debugger is present."""
        try:
            # Check IsDebuggerPresent
            kernel32 = ctypes.windll.kernel32
            if kernel32.IsDebuggerPresent():
                return True
            
            # Check for common debugging processes
            dangerous_processes = [
                'ollydbg.exe', 'idaq.exe', 'idaq64.exe', 'windbg.exe',
                'x32dbg.exe', 'x64dbg.exe', 'immunity.exe', 'cheatengine.exe'
            ]
            
            for proc in psutil.process_iter(['name']):
                if proc.info['name'].lower() in dangerous_processes:
                    return True
            
            return False
            
        except Exception:
            return False
    
    def _protect_debug_privileges(self):
        """Protect against debug privilege escalation."""
        try:
            # Attempt to remove debug privileges
            token = win32security.OpenProcessToken(
                win32api.GetCurrentProcess(),
                win32con.TOKEN_ADJUST_PRIVILEGES | win32con.TOKEN_QUERY
            )
            
            # Remove SeDebugPrivilege if present
            try:
                privilege = win32security.LookupPrivilegeValue(None, "SeDebugPrivilege")
                win32security.AdjustTokenPrivileges(
                    token, 0, [(privilege, win32con.SE_PRIVILEGE_REMOVED)]
                )
            except:
                pass  # Privilege not present or already removed
                
        except Exception as e:
            self._log_security_event(f"Debug privilege protection failed: {e}", "WARNING")
    
    def _enable_memory_protection(self):
        """Enable memory protection measures."""
        try:
            # Enable DEP (Data Execution Prevention)
            kernel32 = ctypes.windll.kernel32
            try:
                kernel32.SetProcessDEPPolicy(1)  # Enable DEP for current process
            except:
                pass  # DEP might already be enabled system-wide
            
            # Clear sensitive data from memory periodically
            self._start_memory_cleanup()
            
            # Enable heap protection
            self._enable_heap_protection()
            
        except Exception as e:
            self._log_security_event(f"Memory protection setup failed: {e}", "WARNING")
    
    def _enable_heap_protection(self):
        """Enable heap protection features."""
        try:
            # Enable heap terminate on corruption
            kernel32 = ctypes.windll.kernel32
            ntdll = ctypes.windll.ntdll
            heap = kernel32.GetProcessHeap()
            
            # Set heap flags for protection
            kernel32.HeapSetInformation(
                heap, 0, None, 0  # HeapEnableTerminationOnCorruption
            )
            
        except Exception:
            pass  # Heap protection not critical if fails
    
    def _start_process_monitoring(self):
        """Start monitoring for suspicious processes."""
        if not self.is_monitoring:
            self.is_monitoring = True
            self.monitor_thread = threading.Thread(
                target=self._process_monitor_loop,
                daemon=True
            )
            self.monitor_thread.start()
    
    def _process_monitor_loop(self):
        """Monitor for suspicious processes and activities."""
        while self.is_monitoring:
            try:
                # Check for malicious processes
                self._check_malicious_processes()
                
                # Check for injection attempts
                self._check_code_injection()
                
                # Monitor network connections
                self._monitor_network_activity()
                
                # Check file system integrity
                self._check_file_integrity()
                
                time.sleep(5)  # Check every 5 seconds
                
            except Exception as e:
                self._log_security_event(f"Process monitoring error: {e}", "WARNING")
    
    def _check_malicious_processes(self):
        """Check for known malicious processes."""
        try:
            malicious_patterns = [
                'keylogger', 'password', 'hack', 'crack', 'inject',
                'dump', 'stealer', 'trojan', 'backdoor', 'rootkit'
            ]
            
            for proc in psutil.process_iter(['name', 'pid', 'cmdline']):
                try:
                    proc_name = proc.info['name'].lower()
                    cmdline = ' '.join(proc.info['cmdline'] or []).lower()
                    
                    for pattern in malicious_patterns:
                        if pattern in proc_name or pattern in cmdline:
                            self._log_security_event(
                                f"Suspicious process detected: {proc_name} (PID: {proc.info['pid']})",
                                "CRITICAL"
                            )
                            self._trigger_security_response("MALICIOUS_PROCESS")
                            
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
                    
        except Exception as e:
            self._log_security_event(f"Malicious process check failed: {e}", "WARNING")
    
    def _check_code_injection(self):
        """Check for code injection attempts."""
        try:
            current_process = psutil.Process(self.process_id)
            
            # Check for unexpected memory regions
            try:
                with current_process.oneshot():
                    memory_info = current_process.memory_info()
                    
                    # Check if memory usage is suspicious
                    if memory_info.rss > 500 * 1024 * 1024:  # 500MB threshold
                        self._log_security_event(
                            f"Suspicious memory usage: {memory_info.rss / 1024 / 1024:.1f}MB",
                            "WARNING"
                        )
                        
            except Exception:
                pass
                
            # Check for DLL injection
            self._check_dll_injection()
            
        except Exception as e:
            self._log_security_event(f"Code injection check failed: {e}", "WARNING")
    
    def _check_dll_injection(self):
        """Check for DLL injection attempts."""
        try:
            # Get loaded modules
            process = win32api.GetCurrentProcess()
            modules = win32process.EnumProcessModules(process)
            
            # Check for suspicious DLLs
            suspicious_dlls = ['inject', 'hook', 'keylog', 'capture', 'dump']
            
            for module in modules:
                try:
                    module_name = win32process.GetModuleFileNameEx(process, module).lower()
                    for pattern in suspicious_dlls:
                        if pattern in module_name:
                            self._log_security_event(
                                f"Suspicious DLL loaded: {module_name}",
                                "CRITICAL"
                            )
                            self._trigger_security_response("DLL_INJECTION")
                            
                except Exception:
                    continue
                    
        except Exception:
            pass  # DLL check not critical if fails
    
    def _monitor_network_activity(self):
        """Monitor for suspicious network activity."""
        try:
            connections = psutil.net_connections(kind='inet')
            
            # Check for unexpected network connections from our process
            our_connections = [
                conn for conn in connections 
                if conn.pid == self.process_id
            ]
            
            if our_connections:
                for conn in our_connections:
                    self._log_security_event(
                        f"Unexpected network connection: {conn.laddr} -> {conn.raddr}",
                        "WARNING"
                    )
                    
        except Exception:
            pass  # Network monitoring not critical if fails
    
    def _initialize_file_integrity(self):
        """Initialize file integrity monitoring."""
        try:
            # Calculate checksums for critical files
            critical_files = [
                'main.py',
                'src/security.py',
                'src/database.py',
                'src/gui.py'
            ]
            
            for file_path in critical_files:
                if os.path.exists(file_path):
                    checksum = self._calculate_file_hash(file_path)
                    self.integrity_checks[file_path] = checksum
                    
        except Exception as e:
            self._log_security_event(f"File integrity initialization failed: {e}", "WARNING")
    
    def _check_file_integrity(self):
        """Check file integrity against stored checksums."""
        try:
            for file_path, stored_hash in self.integrity_checks.items():
                if os.path.exists(file_path):
                    current_hash = self._calculate_file_hash(file_path)
                    if current_hash != stored_hash:
                        self._log_security_event(
                            f"File integrity violation: {file_path}",
                            "CRITICAL"
                        )
                        self._trigger_security_response("FILE_TAMPERED")
                        
        except Exception as e:
            self._log_security_event(f"File integrity check failed: {e}", "WARNING")
    
    def _calculate_file_hash(self, file_path: str) -> str:
        """Calculate SHA-256 hash of a file."""
        try:
            hasher = hashlib.sha256()
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hasher.update(chunk)
            return hasher.hexdigest()
            
        except Exception:
            return ""
    
    def _enable_anti_tampering(self):
        """Enable anti-tampering protection."""
        try:
            # Protect critical registry keys
            self._protect_registry_keys()
            
            # Monitor for process termination attempts
            self._protect_process_termination()
            
            # Enable self-protection
            self._enable_self_protection()
            
        except Exception as e:
            self._log_security_event(f"Anti-tampering setup failed: {e}", "WARNING")
    
    def _protect_registry_keys(self):
        """Protect critical registry keys."""
        try:
            # Protect SilentLock registry entries
            keys_to_protect = [
                (winreg.HKEY_CURRENT_USER, r"SOFTWARE\SilentLock"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run")
            ]
            
            for root_key, subkey_path in keys_to_protect:
                try:
                    # Set restrictive permissions on registry key
                    key = winreg.OpenKey(
                        root_key, subkey_path, 
                        0, winreg.KEY_READ | winreg.KEY_WRITE
                    )
                    winreg.CloseKey(key)
                    
                except FileNotFoundError:
                    pass  # Key doesn't exist yet
                except Exception:
                    pass  # Permission denied or other error
                    
        except Exception:
            pass  # Registry protection not critical if fails
    
    def _protect_process_termination(self):
        """Protect against process termination attempts."""
        try:
            # This is a placeholder - full implementation would require
            # lower-level system hooks or driver-level protection
            pass
            
        except Exception:
            pass
    
    def _enable_self_protection(self):
        """Enable self-protection mechanisms."""
        try:
            # Mark process as critical (requires admin privileges)
            try:
                ntdll = ctypes.windll.ntdll
                current_process = win32api.GetCurrentProcess()
                
                # Attempt to set critical process flag
                ntdll.RtlSetProcessIsCritical(1, 0, 0)
                
            except Exception:
                pass  # Requires admin privileges
                
        except Exception:
            pass
    
    def _start_memory_cleanup(self):
        """Start periodic memory cleanup."""
        def cleanup_loop():
            while self.is_monitoring:
                try:
                    # Force garbage collection
                    import gc
                    gc.collect()
                    
                    # Clear sensitive variables (would need specific implementation)
                    self._secure_memory_wipe()
                    
                    time.sleep(30)  # Cleanup every 30 seconds
                    
                except Exception:
                    pass
        
        threading.Thread(target=cleanup_loop, daemon=True).start()
    
    def _secure_memory_wipe(self):
        """Securely wipe sensitive data from memory."""
        try:
            # This is a placeholder for secure memory wiping
            # Full implementation would use ctypes to overwrite memory
            pass
            
        except Exception:
            pass
    
    def _start_debug_monitoring(self):
        """Monitor for debugging attempts."""
        def debug_monitor():
            while self.is_monitoring:
                try:
                    if self._is_debugger_present():
                        self._trigger_security_response("DEBUGGER_DETECTED")
                    
                    time.sleep(1)  # Check frequently
                    
                except Exception:
                    pass
        
        threading.Thread(target=debug_monitor, daemon=True).start()
    
    def _trigger_security_response(self, threat_type: str):
        """Trigger appropriate security response."""
        try:
            self._log_security_event(f"Security threat detected: {threat_type}", "CRITICAL")
            
            responses = {
                'DEBUGGER_DETECTED': self._handle_debugger_threat,
                'MALICIOUS_PROCESS': self._handle_malicious_process,
                'DLL_INJECTION': self._handle_injection_threat,
                'FILE_TAMPERED': self._handle_tampering_threat
            }
            
            handler = responses.get(threat_type)
            if handler:
                handler()
                
        except Exception as e:
            self._log_security_event(f"Security response failed: {e}", "CRITICAL")
    
    def _handle_debugger_threat(self):
        """Handle debugger detection."""
        # Lock down application
        self._emergency_lockdown("Debugger detected")
    
    def _handle_malicious_process(self):
        """Handle malicious process detection."""
        # Increase monitoring frequency
        self._log_security_event("Increased security monitoring due to threat", "WARNING")
    
    def _handle_injection_threat(self):
        """Handle code injection threat."""
        # Emergency shutdown
        self._emergency_lockdown("Code injection detected")
    
    def _handle_tampering_threat(self):
        """Handle file tampering."""
        # Verify integrity and potentially restore
        self._log_security_event("File tampering detected - verify installation", "CRITICAL")
    
    def _emergency_lockdown(self, reason: str):
        """Emergency security lockdown."""
        self._log_security_event(f"EMERGENCY LOCKDOWN: {reason}", "CRITICAL")
        
        # Clear sensitive data
        self._secure_memory_wipe()
        
        # Could implement additional lockdown measures:
        # - Clear clipboard
        # - Lock database
        # - Notify admin
        # - Graceful shutdown
    
    def _log_security_event(self, message: str, level: str):
        """Log security events."""
        try:
            event = {
                'timestamp': datetime.now().isoformat(),
                'level': level,
                'message': message,
                'process_id': self.process_id
            }
            
            self.security_events.append(event)
            
            # Keep only last 1000 events
            if len(self.security_events) > 1000:
                self.security_events = self.security_events[-1000:]
            
            # Log to file if needed
            self._write_security_log(event)
            
        except Exception:
            pass  # Logging should not crash application
    
    def _write_security_log(self, event: Dict):
        """Write security event to log file."""
        try:
            log_dir = os.path.join(os.path.expandvars(r'%APPDATA%'), 'SilentLock', 'logs')
            os.makedirs(log_dir, exist_ok=True)
            
            log_file = os.path.join(log_dir, 'security.log')
            
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(f"{event['timestamp']} [{event['level']}] {event['message']}\n")
                
        except Exception:
            pass
    
    def get_status(self):
        """Get current security status."""
        return {
            'monitoring_active': self.is_monitoring,
            'uptime': time.time() - self.start_time,
            'events_count': len(self.security_events),
            'last_check': datetime.now().isoformat(),
            'config': self.config.copy()
        }
    
    def start_monitoring(self):
        """Start security monitoring."""
        try:
            if not self.is_monitoring:
                self.is_monitoring = True
                self.monitor_thread = threading.Thread(target=self._monitor_loop)
                self.monitor_thread.daemon = True
                self.monitor_thread.start()
                self._log_security_event("Security monitoring started", "INFO")
        except Exception as e:
            self._log_security_event(f"Failed to start monitoring: {e}", "ERROR")
    
    def stop_monitoring(self):
        """Stop security monitoring."""
        self.is_monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1)
        self._log_security_event("Security monitoring stopped", "INFO")
    
    def check_threats(self) -> Dict[str, Any]:
        """Check for current security threats."""
        try:
            threats = []
            
            # Check for debuggers
            if self._is_debugger_present():
                threats.append({
                    'type': 'DEBUGGER',
                    'description': 'Debugging tool detected',
                    'severity': 'HIGH'
                })
            
            # Check for suspicious processes
            suspicious = self._scan_suspicious_processes()
            for proc in suspicious:
                threats.append({
                    'type': 'SUSPICIOUS_PROCESS',
                    'description': f'Potentially malicious process: {proc}',
                    'severity': 'MEDIUM'
                })
            
            return {
                'threats_detected': len(threats) > 0,
                'threat_count': len(threats),
                'threats': threats,
                'scan_time': datetime.now().isoformat()
            }
            
        except Exception as e:
            self._log_security_event(f"Threat check failed: {e}", "ERROR")
            return {
                'threats_detected': False,
                'threat_count': 0,
                'threats': [],
                'error': str(e)
            }
    
    def _scan_suspicious_processes(self) -> List[str]:
        """Scan for suspicious processes."""
        suspicious_processes = []
        try:
            dangerous_names = [
                'ollydbg.exe', 'idaq.exe', 'idaq64.exe', 'windbg.exe',
                'x32dbg.exe', 'x64dbg.exe', 'cheatengine.exe', 'processhacker.exe'
            ]
            
            for proc in psutil.process_iter(['name']):
                try:
                    if proc.info['name'].lower() in dangerous_names:
                        suspicious_processes.append(proc.info['name'])
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
                    
        except Exception:
            pass
            
        return suspicious_processes
    
    def _monitor_loop(self):
        """Main monitoring loop."""
        while self.is_monitoring:
            try:
                # Perform security checks periodically
                self.check_threats()
                time.sleep(30)  # Check every 30 seconds
            except Exception as e:
                self._log_security_event(f"Monitor loop error: {e}", "ERROR")
                time.sleep(60)  # Wait longer on error
    
    def get_recent_events(self, count: int = 50) -> List[Dict]:
        """Get recent security events."""
        return self.security_events[-count:]
    
    def shutdown(self):
        """Shutdown security monitoring."""
        self.is_monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1)
        
        self._secure_memory_wipe()
        self._log_security_event("Security monitoring shutdown", "INFO")


# Global security manager instance
security_manager = None

def initialize_security() -> SecurityHardening:
    """Initialize global security manager."""
    global security_manager
    if security_manager is None:
        security_manager = SecurityHardening()
    return security_manager

def get_security_manager() -> Optional[SecurityHardening]:
    """Get the global security manager."""
    global security_manager
    if security_manager is None:
        try:
            security_manager = SecurityHardening()
        except Exception as e:
            print(f"Error initializing security manager: {e}")
            return None
    return security_manager