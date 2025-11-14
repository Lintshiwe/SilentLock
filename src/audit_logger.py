"""
Comprehensive Audit Logging System for SilentLock
Tracks all administrative actions, password access, security events, and system changes.
"""

import json
import hashlib
import sqlite3
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
import os
import socket
import platform


class AuditLogger:
    """Comprehensive audit logging system for security and compliance tracking."""
    
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.session_id = self._generate_session_id()
        self.lock = threading.Lock()
        
        # System information
        self.hostname = socket.gethostname()
        self.platform_info = f"{platform.system()} {platform.release()}"
        self.process_id = os.getpid()
        
        # Initialize audit database
        self._init_audit_db()
        
        # Log system startup
        self.log_system_event(
            event_type="system_startup",
            details={"hostname": self.hostname, "platform": self.platform_info, "pid": self.process_id}
        )
    
    def _init_audit_db(self):
        """Initialize audit logging database tables."""
        conn = None
        try:
            conn = self.db_manager.get_cursor()
            if conn is None:
                return
            
            cursor = conn.cursor()
            
            # Main audit log table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS audit_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    session_id TEXT,
                    event_type TEXT NOT NULL,
                    event_category TEXT NOT NULL,
                    user_id TEXT,
                    username TEXT,
                    action TEXT NOT NULL,
                    resource_type TEXT,
                    resource_id TEXT,
                    resource_name TEXT,
                    old_values TEXT,
                    new_values TEXT,
                    ip_address TEXT,
                    user_agent TEXT,
                    hostname TEXT,
                    process_id INTEGER,
                    success BOOLEAN DEFAULT TRUE,
                    error_message TEXT,
                    risk_level TEXT DEFAULT 'LOW',
                    additional_data TEXT,
                    hash_verification TEXT
                )
            ''')
            
            # Admin actions audit table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS admin_audit (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    admin_session_id TEXT,
                    admin_user_id TEXT NOT NULL,
                    action_type TEXT NOT NULL,
                    target_user_id TEXT,
                    affected_resource TEXT,
                    action_details TEXT,
                    privilege_level TEXT,
                    ip_address TEXT,
                    success BOOLEAN DEFAULT TRUE,
                    risk_assessment TEXT,
                    approval_required BOOLEAN DEFAULT FALSE,
                    approved_by TEXT,
                    approval_timestamp TIMESTAMP
                )
            ''')
            
            # Password access audit table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS password_audit (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    user_id TEXT NOT NULL,
                    password_id INTEGER,
                    site_name TEXT,
                    access_type TEXT NOT NULL,
                    access_method TEXT,
                    ip_address TEXT,
                    user_agent TEXT,
                    success BOOLEAN DEFAULT TRUE,
                    auto_fill BOOLEAN DEFAULT FALSE,
                    copy_to_clipboard BOOLEAN DEFAULT FALSE,
                    export_action BOOLEAN DEFAULT FALSE,
                    risk_indicators TEXT,
                    FOREIGN KEY (password_id) REFERENCES passwords (id)
                )
            ''')
            
            # Security events audit table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS security_audit (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    event_type TEXT NOT NULL,
                    severity_level TEXT NOT NULL,
                    source_ip TEXT,
                    threat_type TEXT,
                    detection_method TEXT,
                    affected_systems TEXT,
                    mitigation_actions TEXT,
                    false_positive BOOLEAN DEFAULT FALSE,
                    investigation_status TEXT DEFAULT 'PENDING',
                    investigation_notes TEXT,
                    resolved_timestamp TIMESTAMP,
                    resolved_by TEXT
                )
            ''')
            
            # Authentication audit table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS auth_audit (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    user_id TEXT,
                    username TEXT,
                    auth_type TEXT NOT NULL,
                    auth_method TEXT,
                    ip_address TEXT,
                    user_agent TEXT,
                    location_info TEXT,
                    device_fingerprint TEXT,
                    success BOOLEAN NOT NULL,
                    failure_reason TEXT,
                    session_id TEXT,
                    mfa_used BOOLEAN DEFAULT FALSE,
                    risk_score INTEGER DEFAULT 0,
                    blocked BOOLEAN DEFAULT FALSE,
                    rate_limited BOOLEAN DEFAULT FALSE
                )
            ''')
            
            # System configuration audit table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS config_audit (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    admin_user_id TEXT NOT NULL,
                    config_category TEXT NOT NULL,
                    config_key TEXT NOT NULL,
                    old_value TEXT,
                    new_value TEXT,
                    change_reason TEXT,
                    approval_required BOOLEAN DEFAULT FALSE,
                    approved_by TEXT,
                    rollback_possible BOOLEAN DEFAULT TRUE,
                    impact_assessment TEXT,
                    validation_status TEXT DEFAULT 'PENDING'
                )
            ''')
            
            # Compliance audit table
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS compliance_audit (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    compliance_standard TEXT NOT NULL,
                    requirement_id TEXT NOT NULL,
                    check_type TEXT NOT NULL,
                    check_result TEXT NOT NULL,
                    compliance_status TEXT NOT NULL,
                    evidence_location TEXT,
                    remediation_required BOOLEAN DEFAULT FALSE,
                    remediation_deadline TIMESTAMP,
                    responsible_party TEXT,
                    last_review_date TIMESTAMP,
                    next_review_date TIMESTAMP
                )
            ''')
            
            conn.commit()
            
        except Exception as e:
            print(f"Error initializing audit database: {e}")
        finally:
            if conn:
                conn.close()
    
    def _generate_session_id(self) -> str:
        """Generate unique session identifier."""
        import secrets
        return secrets.token_urlsafe(16)
    
    def _calculate_hash_verification(self, data: Dict) -> str:
        """Calculate hash verification for audit integrity."""
        # Create deterministic string from audit data
        hash_data = json.dumps(data, sort_keys=True, default=str)
        return hashlib.sha256(hash_data.encode()).hexdigest()[:16]
    
    def log_admin_action(self, admin_user_id: str, action_type: str, 
                        target_user_id: str = None, affected_resource: str = None,
                        action_details: Dict = None, privilege_level: str = "ADMIN",
                        ip_address: str = None, success: bool = True,
                        risk_assessment: str = "LOW") -> bool:
        """Log administrative actions."""
        conn = None
        try:
            with self.lock:
                conn = self.db_manager.get_cursor()
                if conn is None:
                    return False
                
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO admin_audit 
                    (admin_session_id, admin_user_id, action_type, target_user_id,
                     affected_resource, action_details, privilege_level, ip_address,
                     success, risk_assessment)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    self.session_id,
                    admin_user_id,
                    action_type,
                    target_user_id,
                    affected_resource,
                    json.dumps(action_details) if action_details else None,
                    privilege_level,
                    ip_address,
                    success,
                    risk_assessment
                ))
                
                conn.commit()
                
                # Also log in main audit table
                self._log_main_audit(
                    event_type="admin_action",
                    event_category="ADMINISTRATION",
                    user_id=admin_user_id,
                    action=action_type,
                    resource_type="admin_resource",
                    resource_id=affected_resource,
                    ip_address=ip_address,
                    success=success,
                    risk_level=risk_assessment.upper(),
                    additional_data=action_details
                )
                
                return True
                
        except Exception as e:
            print(f"Error logging admin action: {e}")
            return False
        finally:
            if conn:
                conn.close()
    
    def log_password_access(self, user_id: str, password_id: int, site_name: str,
                           access_type: str, access_method: str = "GUI",
                           ip_address: str = None, user_agent: str = None,
                           success: bool = True, auto_fill: bool = False,
                           copy_to_clipboard: bool = False, export_action: bool = False,
                           risk_indicators: List[str] = None) -> bool:
        """Log password access events."""
        try:
            with self.lock:
                cursor = self.db_manager.get_cursor()
                
                cursor.execute('''
                    INSERT INTO password_audit 
                    (user_id, password_id, site_name, access_type, access_method,
                     ip_address, user_agent, success, auto_fill, copy_to_clipboard,
                     export_action, risk_indicators)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    user_id,
                    password_id,
                    site_name,
                    access_type,
                    access_method,
                    ip_address,
                    user_agent,
                    success,
                    auto_fill,
                    copy_to_clipboard,
                    export_action,
                    json.dumps(risk_indicators) if risk_indicators else None
                ))
                
                cursor.connection.commit()
                
                # Also log in main audit table
                self._log_main_audit(
                    event_type="password_access",
                    event_category="DATA_ACCESS",
                    user_id=user_id,
                    action=access_type,
                    resource_type="password",
                    resource_id=str(password_id),
                    resource_name=site_name,
                    ip_address=ip_address,
                    success=success,
                    risk_level="MEDIUM" if export_action or copy_to_clipboard else "LOW",
                    additional_data={
                        "access_method": access_method,
                        "auto_fill": auto_fill,
                        "copy_to_clipboard": copy_to_clipboard,
                        "export_action": export_action,
                        "risk_indicators": risk_indicators
                    }
                )
                
                return True
                
        except Exception as e:
            print(f"Error logging password access: {e}")
            return False
    
    def log_security_event(self, event_type: str, severity_level: str,
                          source_ip: str = None, threat_type: str = None,
                          detection_method: str = "AUTOMATED",
                          affected_systems: List[str] = None,
                          mitigation_actions: List[str] = None) -> bool:
        """Log security events and threats."""
        try:
            with self.lock:
                cursor = self.db_manager.get_cursor()
                
                cursor.execute('''
                    INSERT INTO security_audit 
                    (event_type, severity_level, source_ip, threat_type,
                     detection_method, affected_systems, mitigation_actions)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    event_type,
                    severity_level,
                    source_ip,
                    threat_type,
                    detection_method,
                    json.dumps(affected_systems) if affected_systems else None,
                    json.dumps(mitigation_actions) if mitigation_actions else None
                ))
                
                cursor.connection.commit()
                
                # Also log in main audit table
                risk_level = "CRITICAL" if severity_level == "HIGH" else severity_level
                self._log_main_audit(
                    event_type="security_event",
                    event_category="SECURITY",
                    action=event_type,
                    resource_type="system",
                    ip_address=source_ip,
                    success=True,
                    risk_level=risk_level,
                    additional_data={
                        "threat_type": threat_type,
                        "detection_method": detection_method,
                        "affected_systems": affected_systems,
                        "mitigation_actions": mitigation_actions
                    }
                )
                
                return True
                
        except Exception as e:
            print(f"Error logging security event: {e}")
            return False
    
    def log_authentication(self, user_id: str, username: str, auth_type: str,
                          auth_method: str, ip_address: str = None,
                          user_agent: str = None, success: bool = True,
                          failure_reason: str = None, mfa_used: bool = False,
                          risk_score: int = 0, blocked: bool = False) -> bool:
        """Log authentication attempts."""
        try:
            with self.lock:
                cursor = self.db_manager.get_cursor()
                
                cursor.execute('''
                    INSERT INTO auth_audit 
                    (user_id, username, auth_type, auth_method, ip_address,
                     user_agent, success, failure_reason, session_id,
                     mfa_used, risk_score, blocked)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    user_id,
                    username,
                    auth_type,
                    auth_method,
                    ip_address,
                    user_agent,
                    success,
                    failure_reason,
                    self.session_id,
                    mfa_used,
                    risk_score,
                    blocked
                ))
                
                cursor.connection.commit()
                
                # Also log in main audit table
                risk_level = "HIGH" if blocked or risk_score > 70 else ("MEDIUM" if risk_score > 30 else "LOW")
                self._log_main_audit(
                    event_type="authentication",
                    event_category="AUTHENTICATION",
                    user_id=user_id,
                    username=username,
                    action=auth_type,
                    ip_address=ip_address,
                    success=success,
                    error_message=failure_reason,
                    risk_level=risk_level,
                    additional_data={
                        "auth_method": auth_method,
                        "mfa_used": mfa_used,
                        "risk_score": risk_score,
                        "blocked": blocked
                    }
                )
                
                return True
                
        except Exception as e:
            print(f"Error logging authentication: {e}")
            return False
    
    def log_config_change(self, admin_user_id: str, config_category: str,
                         config_key: str, old_value: Any, new_value: Any,
                         change_reason: str = None, approval_required: bool = False,
                         impact_assessment: str = None) -> bool:
        """Log configuration changes."""
        try:
            with self.lock:
                cursor = self.db_manager.get_cursor()
                
                cursor.execute('''
                    INSERT INTO config_audit 
                    (admin_user_id, config_category, config_key, old_value,
                     new_value, change_reason, approval_required, impact_assessment)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    admin_user_id,
                    config_category,
                    config_key,
                    str(old_value) if old_value is not None else None,
                    str(new_value) if new_value is not None else None,
                    change_reason,
                    approval_required,
                    impact_assessment
                ))
                
                cursor.connection.commit()
                
                # Also log in main audit table
                self._log_main_audit(
                    event_type="config_change",
                    event_category="CONFIGURATION",
                    user_id=admin_user_id,
                    action="modify_config",
                    resource_type="configuration",
                    resource_id=config_key,
                    resource_name=f"{config_category}.{config_key}",
                    old_values={"value": old_value},
                    new_values={"value": new_value},
                    success=True,
                    risk_level="HIGH" if approval_required else "MEDIUM",
                    additional_data={
                        "config_category": config_category,
                        "change_reason": change_reason,
                        "impact_assessment": impact_assessment
                    }
                )
                
                return True
                
        except Exception as e:
            print(f"Error logging config change: {e}")
            return False
    
    def log_system_event(self, event_type: str, details: Dict = None,
                        success: bool = True, error_message: str = None) -> bool:
        """Log system-level events."""
        try:
            with self.lock:
                return self._log_main_audit(
                    event_type=event_type,
                    event_category="SYSTEM",
                    action=event_type,
                    resource_type="system",
                    hostname=self.hostname,
                    success=success,
                    error_message=error_message,
                    risk_level="LOW",
                    additional_data=details
                )
                
        except Exception as e:
            print(f"Error logging system event: {e}")
            return False
    
    def _log_main_audit(self, event_type: str, event_category: str, action: str,
                       user_id: str = None, username: str = None,
                       resource_type: str = None, resource_id: str = None,
                       resource_name: str = None, old_values: Dict = None,
                       new_values: Dict = None, ip_address: str = None,
                       user_agent: str = None, hostname: str = None,
                       success: bool = True, error_message: str = None,
                       risk_level: str = "LOW", additional_data: Dict = None) -> bool:
        """Log to main audit table."""
        conn = None
        try:
            conn = self.db_manager.get_cursor()
            if conn is None:
                return False
            
            cursor = conn.cursor()
            
            # Prepare audit data
            audit_data = {
                "session_id": self.session_id,
                "event_type": event_type,
                "event_category": event_category,
                "user_id": user_id,
                "username": username,
                "action": action,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "resource_name": resource_name,
                "old_values": json.dumps(old_values) if old_values else None,
                "new_values": json.dumps(new_values) if new_values else None,
                "ip_address": ip_address,
                "user_agent": user_agent,
                "hostname": hostname or self.hostname,
                "process_id": self.process_id,
                "success": success,
                "error_message": error_message,
                "risk_level": risk_level,
                "additional_data": json.dumps(additional_data) if additional_data else None
            }
            
            # Calculate hash verification
            audit_data["hash_verification"] = self._calculate_hash_verification(audit_data)
            
            cursor.execute('''
                INSERT INTO audit_log 
                (session_id, event_type, event_category, user_id, username,
                 action, resource_type, resource_id, resource_name,
                 old_values, new_values, ip_address, user_agent,
                 hostname, process_id, success, error_message,
                 risk_level, additional_data, hash_verification)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', tuple(audit_data.values()))
            
            conn.commit()
            return True
            
        except Exception as e:
            print(f"Error logging main audit: {e}")
            return False
        finally:
            if conn:
                conn.close()
    
    def get_audit_logs(self, event_category: str = None, user_id: str = None,
                      start_date: datetime = None, end_date: datetime = None,
                      limit: int = 1000, risk_level: str = None,
                      success_only: bool = None) -> List[Dict]:
        """Retrieve audit logs with filtering."""
        try:
            cursor = self.db_manager.get_cursor()
            
            # Build query with filters
            query = "SELECT * FROM audit_log WHERE 1=1"
            params = []
            
            if event_category:
                query += " AND event_category = ?"
                params.append(event_category)
            
            if user_id:
                query += " AND user_id = ?"
                params.append(user_id)
            
            if start_date:
                query += " AND timestamp >= ?"
                params.append(start_date.isoformat())
            
            if end_date:
                query += " AND timestamp <= ?"
                params.append(end_date.isoformat())
            
            if risk_level:
                query += " AND risk_level = ?"
                params.append(risk_level)
            
            if success_only is not None:
                query += " AND success = ?"
                params.append(success_only)
            
            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            results = cursor.fetchall()
            
            # Convert to dictionary format
            columns = [desc[0] for desc in cursor.description]
            logs = []
            
            for result in results:
                log_entry = dict(zip(columns, result))
                
                # Parse JSON fields
                for json_field in ['old_values', 'new_values', 'additional_data']:
                    if log_entry.get(json_field):
                        try:
                            log_entry[json_field] = json.loads(log_entry[json_field])
                        except:
                            pass
                
                logs.append(log_entry)
            
            return logs
            
        except Exception as e:
            print(f"Error retrieving audit logs: {e}")
            return []
    
    def get_security_events(self, severity_level: str = None,
                           resolved: bool = None, limit: int = 100) -> List[Dict]:
        """Retrieve security events."""
        try:
            cursor = self.db_manager.get_cursor()
            
            query = "SELECT * FROM security_audit WHERE 1=1"
            params = []
            
            if severity_level:
                query += " AND severity_level = ?"
                params.append(severity_level)
            
            if resolved is not None:
                if resolved:
                    query += " AND resolved_timestamp IS NOT NULL"
                else:
                    query += " AND resolved_timestamp IS NULL"
            
            query += " ORDER BY timestamp DESC LIMIT ?"
            params.append(limit)
            
            cursor.execute(query, params)
            results = cursor.fetchall()
            
            # Convert to dictionary format
            columns = [desc[0] for desc in cursor.description]
            events = []
            
            for result in results:
                event = dict(zip(columns, result))
                
                # Parse JSON fields
                for json_field in ['affected_systems', 'mitigation_actions']:
                    if event.get(json_field):
                        try:
                            event[json_field] = json.loads(event[json_field])
                        except:
                            pass
                
                events.append(event)
            
            return events
            
        except Exception as e:
            print(f"Error retrieving security events: {e}")
            return []
    
    def generate_audit_report(self, report_type: str = "summary",
                             start_date: datetime = None,
                             end_date: datetime = None) -> Dict:
        """Generate comprehensive audit report."""
        try:
            if not start_date:
                start_date = datetime.now() - timedelta(days=30)
            if not end_date:
                end_date = datetime.now()
            
            cursor = self.db_manager.get_cursor()
            
            # Base report structure
            report = {
                "report_type": report_type,
                "generated_at": datetime.now().isoformat(),
                "period": {
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat()
                },
                "summary": {},
                "details": {}
            }
            
            # General activity summary
            cursor.execute('''
                SELECT event_category, COUNT(*) as count
                FROM audit_log 
                WHERE timestamp BETWEEN ? AND ?
                GROUP BY event_category
            ''', (start_date.isoformat(), end_date.isoformat()))
            
            activity_summary = dict(cursor.fetchall())
            report["summary"]["activity_by_category"] = activity_summary
            
            # Risk level distribution
            cursor.execute('''
                SELECT risk_level, COUNT(*) as count
                FROM audit_log 
                WHERE timestamp BETWEEN ? AND ?
                GROUP BY risk_level
            ''', (start_date.isoformat(), end_date.isoformat()))
            
            risk_summary = dict(cursor.fetchall())
            report["summary"]["risk_distribution"] = risk_summary
            
            # Failed events
            cursor.execute('''
                SELECT COUNT(*) as failed_events
                FROM audit_log 
                WHERE timestamp BETWEEN ? AND ? AND success = 0
            ''', (start_date.isoformat(), end_date.isoformat()))
            
            failed_count = cursor.fetchone()[0]
            report["summary"]["failed_events"] = failed_count
            
            # Top users by activity
            cursor.execute('''
                SELECT user_id, COUNT(*) as activity_count
                FROM audit_log 
                WHERE timestamp BETWEEN ? AND ? AND user_id IS NOT NULL
                GROUP BY user_id
                ORDER BY activity_count DESC
                LIMIT 10
            ''', (start_date.isoformat(), end_date.isoformat()))
            
            top_users = cursor.fetchall()
            report["summary"]["most_active_users"] = [
                {"user_id": user[0], "activity_count": user[1]} 
                for user in top_users
            ]
            
            # Security events summary
            cursor.execute('''
                SELECT severity_level, COUNT(*) as count
                FROM security_audit 
                WHERE timestamp BETWEEN ? AND ?
                GROUP BY severity_level
            ''', (start_date.isoformat(), end_date.isoformat()))
            
            security_summary = dict(cursor.fetchall())
            report["summary"]["security_events"] = security_summary
            
            # Admin actions summary
            cursor.execute('''
                SELECT action_type, COUNT(*) as count
                FROM admin_audit 
                WHERE timestamp BETWEEN ? AND ?
                GROUP BY action_type
            ''', (start_date.isoformat(), end_date.isoformat()))
            
            admin_summary = dict(cursor.fetchall())
            report["summary"]["admin_actions"] = admin_summary
            
            # Password access summary
            cursor.execute('''
                SELECT access_type, COUNT(*) as count
                FROM password_audit 
                WHERE timestamp BETWEEN ? AND ?
                GROUP BY access_type
            ''', (start_date.isoformat(), end_date.isoformat()))
            
            password_summary = dict(cursor.fetchall())
            report["summary"]["password_access"] = password_summary
            
            # If detailed report requested
            if report_type == "detailed":
                # Recent high-risk events
                report["details"]["high_risk_events"] = self.get_audit_logs(
                    risk_level="HIGH",
                    start_date=start_date,
                    end_date=end_date,
                    limit=50
                )
                
                # Recent security events
                report["details"]["security_events"] = self.get_security_events(
                    limit=50
                )
                
                # Failed authentication attempts
                cursor.execute('''
                    SELECT * FROM auth_audit 
                    WHERE timestamp BETWEEN ? AND ? AND success = 0
                    ORDER BY timestamp DESC LIMIT 20
                ''', (start_date.isoformat(), end_date.isoformat()))
                
                failed_auth = cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
                report["details"]["failed_authentications"] = [
                    dict(zip(columns, row)) for row in failed_auth
                ]
            
            return report
            
        except Exception as e:
            print(f"Error generating audit report: {e}")
            return {"error": str(e)}
    
    def verify_audit_integrity(self, start_date: datetime = None,
                              end_date: datetime = None) -> Dict:
        """Verify audit log integrity using hash verification."""
        try:
            cursor = self.db_manager.get_cursor()
            
            query = "SELECT * FROM audit_log WHERE hash_verification IS NOT NULL"
            params = []
            
            if start_date:
                query += " AND timestamp >= ?"
                params.append(start_date.isoformat())
            
            if end_date:
                query += " AND timestamp <= ?"
                params.append(end_date.isoformat())
            
            cursor.execute(query, params)
            logs = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            
            verification_result = {
                "verified_count": 0,
                "failed_count": 0,
                "total_checked": len(logs),
                "integrity_status": "PASS",
                "failed_entries": []
            }
            
            for log_data in logs:
                log_dict = dict(zip(columns, log_data))
                stored_hash = log_dict.pop("hash_verification")
                
                # Recalculate hash
                calculated_hash = self._calculate_hash_verification(log_dict)
                
                if stored_hash == calculated_hash:
                    verification_result["verified_count"] += 1
                else:
                    verification_result["failed_count"] += 1
                    verification_result["failed_entries"].append({
                        "id": log_dict["id"],
                        "timestamp": log_dict["timestamp"],
                        "stored_hash": stored_hash,
                        "calculated_hash": calculated_hash
                    })
            
            if verification_result["failed_count"] > 0:
                verification_result["integrity_status"] = "FAIL"
            
            return verification_result
            
        except Exception as e:
            print(f"Error verifying audit integrity: {e}")
            return {"error": str(e)}
    
    def cleanup_old_logs(self, retention_days: int = 365) -> int:
        """Clean up old audit logs based on retention policy."""
        try:
            cutoff_date = datetime.now() - timedelta(days=retention_days)
            cursor = self.db_manager.get_cursor()
            
            # Count logs to be deleted
            cursor.execute('''
                SELECT COUNT(*) FROM audit_log WHERE timestamp < ?
            ''', (cutoff_date.isoformat(),))
            
            count_to_delete = cursor.fetchone()[0]
            
            # Delete old logs
            tables = [
                'audit_log',
                'admin_audit', 
                'password_audit',
                'security_audit',
                'auth_audit',
                'config_audit'
            ]
            
            total_deleted = 0
            for table in tables:
                cursor.execute(f'''
                    DELETE FROM {table} WHERE timestamp < ?
                ''', (cutoff_date.isoformat(),))
                total_deleted += cursor.rowcount
            
            cursor.connection.commit()
            
            # Log the cleanup action
            self.log_system_event(
                event_type="log_cleanup",
                details={
                    "retention_days": retention_days,
                    "cutoff_date": cutoff_date.isoformat(),
                    "logs_deleted": total_deleted
                }
            )
            
            return total_deleted
            
        except Exception as e:
            print(f"Error cleaning up old logs: {e}")
            return 0