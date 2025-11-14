"""
Password Security Analysis Engine for SilentLock
Provides comprehensive password strength analysis, breach detection, and security recommendations.
"""

import hashlib
import re
import requests
import threading
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Set
import json
import sqlite3
import zxcvbn


class PasswordAnalysisEngine:
    """Comprehensive password security analysis and scoring system."""
    
    def __init__(self, db_manager):
        self.db_manager = db_manager
        
        # Breach detection cache
        self.breach_cache = {}
        self.cache_expiry = timedelta(hours=24)
        self.last_breach_check = {}
        
        # Password analysis results
        self.analysis_results = {}
        self.security_metrics = {}
        
        # Common password patterns
        self.weak_patterns = [
            r'^password\d*$',
            r'^123456\d*$',
            r'^qwerty\d*$',
            r'^admin\d*$',
            r'^welcome\d*$',
            r'^\d+$',  # Only numbers
            r'^[a-z]+$',  # Only lowercase
            r'^[A-Z]+$',  # Only uppercase
            r'^(.)\1{3,}$',  # Repeated characters
        ]
        
        # Initialize analysis database
        self._init_analysis_db()
    
    def _init_analysis_db(self):
        """Initialize password analysis database."""
        try:
            cursor = self.db_manager.get_cursor()
            
            # Password analysis table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS password_analysis (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    password_id INTEGER,
                    strength_score INTEGER,
                    zxcvbn_score INTEGER,
                    is_compromised BOOLEAN,
                    breach_count INTEGER,
                    has_duplicates BOOLEAN,
                    duplicate_count INTEGER,
                    common_patterns TEXT,
                    recommendations TEXT,
                    last_analyzed TIMESTAMP,
                    FOREIGN KEY (password_id) REFERENCES passwords (id)
                )
            ''')
            
            # Security metrics table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS security_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    metric_name TEXT UNIQUE,
                    metric_value TEXT,
                    last_updated TIMESTAMP
                )
            ''')
            
            # Breach monitoring table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS breach_monitoring (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    password_hash TEXT UNIQUE,
                    is_breached BOOLEAN,
                    breach_count INTEGER,
                    first_seen TIMESTAMP,
                    last_checked TIMESTAMP
                )
            ''')
            
            cursor.connection.commit()
            
        except Exception as e:
            print(f"Error initializing analysis database: {e}")
    
    def analyze_password(self, password: str, password_id: Optional[int] = None) -> Dict[str, Any]:
        """Comprehensive password analysis."""
        try:
            analysis = {
                'password_id': password_id,
                'timestamp': datetime.now(),
                'strength_score': 0,
                'zxcvbn_score': 0,
                'is_strong': False,
                'is_compromised': False,
                'breach_count': 0,
                'has_duplicates': False,
                'duplicate_count': 0,
                'common_patterns': [],
                'recommendations': [],
                'security_issues': [],
                'estimated_crack_time': '0 seconds'
            }
            
            # Basic password strength analysis
            analysis.update(self._analyze_basic_strength(password))
            
            # Advanced zxcvbn analysis
            analysis.update(self._analyze_with_zxcvbn(password))
            
            # Check for breaches (async)
            breach_thread = threading.Thread(
                target=self._check_breach_async,
                args=(password, password_id, analysis)
            )
            breach_thread.start()
            
            # Check for duplicates
            if password_id:
                analysis.update(self._check_duplicates(password, password_id))
            
            # Check common patterns
            analysis['common_patterns'] = self._check_common_patterns(password)
            
            # Generate recommendations
            analysis['recommendations'] = self._generate_recommendations(analysis)
            
            # Calculate overall security score
            analysis['security_score'] = self._calculate_security_score(analysis)
            
            # Store analysis results
            if password_id:
                self._store_analysis_results(analysis)
            
            return analysis
            
        except Exception as e:
            print(f"Error analyzing password: {e}")
            return {'error': str(e)}
    
    def _analyze_basic_strength(self, password: str) -> Dict[str, Any]:
        """Basic password strength analysis."""
        results = {
            'length': len(password),
            'has_uppercase': bool(re.search(r'[A-Z]', password)),
            'has_lowercase': bool(re.search(r'[a-z]', password)),
            'has_numbers': bool(re.search(r'\d', password)),
            'has_symbols': bool(re.search(r'[!@#$%^&*(),.?\":{}|<>]', password)),
            'character_variety': 0,
            'entropy': 0
        }
        
        # Calculate character variety
        char_sets = [
            results['has_uppercase'],
            results['has_lowercase'], 
            results['has_numbers'],
            results['has_symbols']
        ]
        results['character_variety'] = sum(char_sets)
        
        # Calculate basic entropy
        charset_size = 0
        if results['has_lowercase']:
            charset_size += 26
        if results['has_uppercase']:
            charset_size += 26
        if results['has_numbers']:
            charset_size += 10
        if results['has_symbols']:
            charset_size += 32
        
        if charset_size > 0:
            import math
            results['entropy'] = len(password) * math.log2(charset_size)
        
        # Basic strength scoring
        strength_score = 0
        
        # Length scoring
        if len(password) >= 12:
            strength_score += 25
        elif len(password) >= 8:
            strength_score += 15
        elif len(password) >= 6:
            strength_score += 5
        
        # Character variety scoring
        strength_score += results['character_variety'] * 15
        
        # Entropy bonus
        if results['entropy'] > 50:
            strength_score += 20
        elif results['entropy'] > 35:
            strength_score += 10
        
        results['strength_score'] = min(strength_score, 100)
        results['is_strong'] = strength_score >= 70
        
        return results
    
    def _analyze_with_zxcvbn(self, password: str) -> Dict[str, Any]:
        """Advanced password analysis using zxcvbn."""
        try:
            result = zxcvbn.zxcvbn(password)
            
            return {
                'zxcvbn_score': result['score'],
                'estimated_crack_time': result['crack_times_display']['offline_slow_hashing_1e4_per_second'],
                'zxcvbn_feedback': result.get('feedback', {}),
                'pattern_matches': [match.get('pattern', '') for match in result.get('sequence', [])],
                'guesses': result.get('guesses', 0),
                'guesses_log10': result.get('guesses_log10', 0)
            }
        except Exception as e:
            print(f"Error in zxcvbn analysis: {e}")
            return {
                'zxcvbn_score': 0,
                'estimated_crack_time': 'unknown',
                'zxcvbn_feedback': {},
                'pattern_matches': [],
                'guesses': 0,
                'guesses_log10': 0
            }
    
    def _check_breach_async(self, password: str, password_id: Optional[int], analysis: Dict):
        """Check password against breach databases asynchronously."""
        try:
            # Create SHA-1 hash for HaveIBeenPwned API
            sha1_hash = hashlib.sha1(password.encode()).hexdigest().upper()
            hash_prefix = sha1_hash[:5]
            hash_suffix = sha1_hash[5:]
            
            # Check cache first
            if self._is_cached_breach_result_valid(sha1_hash):
                cached_result = self.breach_cache[sha1_hash]
                analysis.update(cached_result)
                return
            
            # Query HaveIBeenPwned API
            try:
                response = requests.get(
                    f"https://api.pwnedpasswords.com/range/{hash_prefix}",
                    timeout=10,
                    headers={'User-Agent': 'SilentLock-PasswordManager'}
                )
                
                if response.status_code == 200:
                    breach_count = 0
                    for line in response.text.split('\n'):
                        if line.startswith(hash_suffix):
                            breach_count = int(line.split(':')[1])
                            break
                    
                    breach_result = {
                        'is_compromised': breach_count > 0,
                        'breach_count': breach_count
                    }
                    
                    # Cache result
                    self.breach_cache[sha1_hash] = breach_result
                    self.last_breach_check[sha1_hash] = datetime.now()
                    
                    # Store in database
                    self._store_breach_result(sha1_hash, breach_result)
                    
                    analysis.update(breach_result)
                    
                else:
                    analysis.update({'is_compromised': False, 'breach_count': 0})
                    
            except requests.RequestException:
                # Fallback to local breach database if available
                analysis.update(self._check_local_breach_db(sha1_hash))
                
        except Exception as e:
            print(f"Error checking breaches: {e}")
            analysis.update({'is_compromised': False, 'breach_count': 0})
    
    def _check_duplicates(self, password: str, password_id: int) -> Dict[str, Any]:
        """Check for duplicate passwords in the database."""
        try:
            cursor = self.db_manager.get_cursor()
            
            # Hash the password for comparison
            password_hash = hashlib.sha256(password.encode()).hexdigest()
            
            # Find passwords with same hash
            cursor.execute('''
                SELECT id, site_name, username FROM passwords 
                WHERE password_hash = ? AND id != ?
            ''', (password_hash, password_id))
            
            duplicates = cursor.fetchall()
            
            return {
                'has_duplicates': len(duplicates) > 0,
                'duplicate_count': len(duplicates),
                'duplicate_sites': [{'id': dup[0], 'site': dup[1], 'username': dup[2]} for dup in duplicates]
            }
            
        except Exception as e:
            print(f"Error checking duplicates: {e}")
            return {'has_duplicates': False, 'duplicate_count': 0, 'duplicate_sites': []}
    
    def _check_common_patterns(self, password: str) -> List[str]:
        """Check password against common weak patterns."""
        patterns_found = []
        
        password_lower = password.lower()
        
        for pattern in self.weak_patterns:
            if re.match(pattern, password_lower):
                patterns_found.append(pattern)
        
        # Additional pattern checks
        if password in password[::-1]:  # Palindrome
            patterns_found.append('palindrome')
        
        if len(set(password)) <= 3:  # Limited character variety
            patterns_found.append('limited_charset')
        
        # Keyboard patterns
        keyboard_patterns = ['qwerty', 'asdf', '1234', 'zxcv']
        for kb_pattern in keyboard_patterns:
            if kb_pattern in password_lower:
                patterns_found.append(f'keyboard_pattern_{kb_pattern}')
        
        return patterns_found
    
    def _generate_recommendations(self, analysis: Dict) -> List[str]:
        """Generate security recommendations based on analysis."""
        recommendations = []
        
        # Length recommendations
        if analysis.get('length', 0) < 12:
            recommendations.append("🔢 Use at least 12 characters for better security")
        
        # Character variety
        if not analysis.get('has_uppercase', False):
            recommendations.append("🔤 Add uppercase letters (A-Z)")
        if not analysis.get('has_lowercase', False):
            recommendations.append("🔡 Add lowercase letters (a-z)")
        if not analysis.get('has_numbers', False):
            recommendations.append("🔢 Add numbers (0-9)")
        if not analysis.get('has_symbols', False):
            recommendations.append("🔣 Add special symbols (!@#$%^&*)")
        
        # Compromise warnings
        if analysis.get('is_compromised', False):
            recommendations.append("🚨 CRITICAL: This password has been found in data breaches - change immediately!")
        
        # Duplicate warnings
        if analysis.get('has_duplicates', False):
            recommendations.append("⚠️ This password is used for multiple accounts - use unique passwords")
        
        # Pattern warnings
        if analysis.get('common_patterns', []):
            recommendations.append("🔍 Avoid common patterns like 'password123' or keyboard sequences")
        
        # Strength recommendations
        if analysis.get('strength_score', 0) < 50:
            recommendations.append("💪 Consider using a passphrase with multiple random words")
        
        # General security advice
        if analysis.get('zxcvbn_score', 0) < 3:
            recommendations.append("🛡️ Enable two-factor authentication where available")
            recommendations.append("🔄 Consider using a password generator for stronger passwords")
        
        return recommendations
    
    def _calculate_security_score(self, analysis: Dict) -> int:
        """Calculate overall security score."""
        score = 0
        
        # Base strength score (0-40 points)
        score += min(analysis.get('strength_score', 0) * 0.4, 40)
        
        # zxcvbn score (0-25 points)
        score += analysis.get('zxcvbn_score', 0) * 5
        
        # Breach penalty (-30 points)
        if analysis.get('is_compromised', False):
            score -= 30
        
        # Duplicate penalty (-15 points)
        if analysis.get('has_duplicates', False):
            score -= 15
        
        # Pattern penalty (-10 points)
        if analysis.get('common_patterns', []):
            score -= 10
        
        # Length bonus
        length = analysis.get('length', 0)
        if length >= 16:
            score += 10
        elif length >= 12:
            score += 5
        
        # Entropy bonus
        entropy = analysis.get('entropy', 0)
        if entropy > 60:
            score += 15
        elif entropy > 45:
            score += 10
        
        return max(0, min(100, int(score)))
    
    def _store_analysis_results(self, analysis: Dict):
        """Store password analysis results in database."""
        try:
            cursor = self.db_manager.get_cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO password_analysis 
                (password_id, strength_score, zxcvbn_score, is_compromised, breach_count,
                 has_duplicates, duplicate_count, common_patterns, recommendations, last_analyzed)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                analysis.get('password_id'),
                analysis.get('security_score', 0),
                analysis.get('zxcvbn_score', 0),
                analysis.get('is_compromised', False),
                analysis.get('breach_count', 0),
                analysis.get('has_duplicates', False),
                analysis.get('duplicate_count', 0),
                json.dumps(analysis.get('common_patterns', [])),
                json.dumps(analysis.get('recommendations', [])),
                datetime.now()
            ))
            
            cursor.connection.commit()
            
        except Exception as e:
            print(f"Error storing analysis results: {e}")
    
    def _store_breach_result(self, password_hash: str, breach_result: Dict):
        """Store breach check result in database."""
        try:
            cursor = self.db_manager.get_cursor()
            
            cursor.execute('''
                INSERT OR REPLACE INTO breach_monitoring 
                (password_hash, is_breached, breach_count, first_seen, last_checked)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                password_hash,
                breach_result['is_compromised'],
                breach_result['breach_count'],
                datetime.now(),
                datetime.now()
            ))
            
            cursor.connection.commit()
            
        except Exception as e:
            print(f"Error storing breach result: {e}")
    
    def _is_cached_breach_result_valid(self, password_hash: str) -> bool:
        """Check if cached breach result is still valid."""
        if password_hash not in self.last_breach_check:
            return False
        
        last_check = self.last_breach_check[password_hash]
        return datetime.now() - last_check < self.cache_expiry
    
    def _check_local_breach_db(self, password_hash: str) -> Dict[str, Any]:
        """Check local breach database as fallback."""
        try:
            cursor = self.db_manager.get_cursor()
            
            cursor.execute('''
                SELECT is_breached, breach_count FROM breach_monitoring 
                WHERE password_hash = ?
            ''', (password_hash,))
            
            result = cursor.fetchone()
            
            if result:
                return {
                    'is_compromised': bool(result[0]),
                    'breach_count': result[1]
                }
            else:
                return {'is_compromised': False, 'breach_count': 0}
                
        except Exception as e:
            print(f"Error checking local breach database: {e}")
            return {'is_compromised': False, 'breach_count': 0}
    
    def analyze_all_passwords(self) -> Dict[str, Any]:
        """Analyze all passwords in the database."""
        try:
            cursor = self.db_manager.get_cursor()
            
            # Get all passwords
            cursor.execute('SELECT id, password, site_name, username FROM passwords')
            passwords = cursor.fetchall()
            
            results = {
                'total_passwords': len(passwords),
                'analyzed': 0,
                'strong_passwords': 0,
                'weak_passwords': 0,
                'compromised_passwords': 0,
                'duplicate_passwords': 0,
                'analysis_details': [],
                'security_summary': {}
            }
            
            for password_data in passwords:
                password_id, encrypted_password, site_name, username = password_data
                
                # Decrypt password for analysis
                try:
                    # This would need to be implemented with proper decryption
                    # For now, we'll analyze encrypted form (not ideal)
                    analysis = self.analyze_password(encrypted_password, password_id)
                    
                    results['analyzed'] += 1
                    
                    if analysis.get('is_strong', False):
                        results['strong_passwords'] += 1
                    else:
                        results['weak_passwords'] += 1
                    
                    if analysis.get('is_compromised', False):
                        results['compromised_passwords'] += 1
                    
                    if analysis.get('has_duplicates', False):
                        results['duplicate_passwords'] += 1
                    
                    results['analysis_details'].append({
                        'password_id': password_id,
                        'site_name': site_name,
                        'username': username,
                        'security_score': analysis.get('security_score', 0),
                        'is_compromised': analysis.get('is_compromised', False),
                        'has_duplicates': analysis.get('has_duplicates', False),
                        'recommendations': analysis.get('recommendations', [])
                    })
                    
                except Exception as e:
                    print(f"Error analyzing password {password_id}: {e}")
            
            # Calculate security summary
            results['security_summary'] = self._calculate_security_summary(results)
            
            # Store metrics
            self._store_security_metrics(results)
            
            return results
            
        except Exception as e:
            print(f"Error analyzing all passwords: {e}")
            return {'error': str(e)}
    
    def _calculate_security_summary(self, results: Dict) -> Dict[str, Any]:
        """Calculate overall security summary."""
        total = results['total_passwords']
        
        if total == 0:
            return {}
        
        summary = {
            'overall_score': 0,
            'strong_percentage': (results['strong_passwords'] / total) * 100,
            'weak_percentage': (results['weak_passwords'] / total) * 100,
            'compromised_percentage': (results['compromised_passwords'] / total) * 100,
            'duplicate_percentage': (results['duplicate_passwords'] / total) * 100,
            'security_grade': 'F'
        }
        
        # Calculate overall score
        score = 0
        score += summary['strong_percentage'] * 0.4  # 40% weight for strong passwords
        score -= summary['compromised_percentage'] * 0.3  # 30% penalty for compromised
        score -= summary['duplicate_percentage'] * 0.2  # 20% penalty for duplicates
        score += (100 - summary['weak_percentage']) * 0.1  # 10% bonus for non-weak
        
        summary['overall_score'] = max(0, min(100, score))
        
        # Assign grade
        if summary['overall_score'] >= 90:
            summary['security_grade'] = 'A+'
        elif summary['overall_score'] >= 80:
            summary['security_grade'] = 'A'
        elif summary['overall_score'] >= 70:
            summary['security_grade'] = 'B'
        elif summary['overall_score'] >= 60:
            summary['security_grade'] = 'C'
        elif summary['overall_score'] >= 50:
            summary['security_grade'] = 'D'
        else:
            summary['security_grade'] = 'F'
        
        return summary
    
    def _store_security_metrics(self, results: Dict):
        """Store security metrics in database."""
        try:
            cursor = self.db_manager.get_cursor()
            
            metrics = [
                ('total_passwords', results['total_passwords']),
                ('strong_passwords', results['strong_passwords']),
                ('weak_passwords', results['weak_passwords']),
                ('compromised_passwords', results['compromised_passwords']),
                ('duplicate_passwords', results['duplicate_passwords']),
                ('overall_security_score', results['security_summary'].get('overall_score', 0)),
                ('security_grade', results['security_summary'].get('security_grade', 'F')),
                ('last_full_analysis', datetime.now().isoformat())
            ]
            
            for metric_name, metric_value in metrics:
                cursor.execute('''
                    INSERT OR REPLACE INTO security_metrics 
                    (metric_name, metric_value, last_updated)
                    VALUES (?, ?, ?)
                ''', (metric_name, str(metric_value), datetime.now()))
            
            cursor.connection.commit()
            
        except Exception as e:
            print(f"Error storing security metrics: {e}")
    
    def get_security_recommendations(self) -> List[str]:
        """Get system-wide security recommendations."""
        try:
            cursor = self.db_manager.get_cursor()
            
            # Get current metrics
            cursor.execute('SELECT metric_name, metric_value FROM security_metrics')
            metrics = dict(cursor.fetchall())
            
            recommendations = []
            
            total_passwords = int(metrics.get('total_passwords', 0))
            weak_passwords = int(metrics.get('weak_passwords', 0))
            compromised_passwords = int(metrics.get('compromised_passwords', 0))
            duplicate_passwords = int(metrics.get('duplicate_passwords', 0))
            
            if total_passwords == 0:
                return ["Start by saving some passwords to analyze security"]
            
            weak_percentage = (weak_passwords / total_passwords) * 100
            compromised_percentage = (compromised_passwords / total_passwords) * 100
            duplicate_percentage = (duplicate_passwords / total_passwords) * 100
            
            # Priority recommendations
            if compromised_percentage > 0:
                recommendations.append(f"🚨 URGENT: {compromised_passwords} password(s) found in data breaches - change immediately!")
            
            if weak_percentage > 50:
                recommendations.append(f"💪 {weak_passwords} passwords are weak - consider strengthening them")
            
            if duplicate_percentage > 20:
                recommendations.append(f"🔄 {duplicate_passwords} passwords are reused - create unique passwords for each account")
            
            # General recommendations
            if weak_percentage > 25:
                recommendations.append("🎯 Focus on creating passwords with 12+ characters and mixed character types")
            
            if total_passwords < 10:
                recommendations.append("📝 Consider using the password manager for more of your accounts")
            
            recommendations.append("🛡️ Enable two-factor authentication where available")
            recommendations.append("🔍 Run regular security scans to monitor for new breaches")
            
            return recommendations
            
        except Exception as e:
            print(f"Error getting security recommendations: {e}")
            return ["Error loading recommendations"]