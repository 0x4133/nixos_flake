"""
Utility Functions and Helpers

This module provides utility functions and helper classes for the steganographic
QR code generator system.
"""

import json
import hashlib
import base64
import time
import random
import string
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone
import math


class MeshDataValidator:
    """
    Validator for mesh network data structures.
    
    Ensures that mesh data conforms to expected formats and constraints
    before encoding and transmission.
    """
    
    def __init__(self):
        self.required_fields = ['gps', 'timestamp']
        self.optional_fields = ['mac_addresses', 'node_status', 'additional_data']
        
        # Validation rules
        self.validation_rules = {
            'gps': {
                'lat': {'type': float, 'min': -90.0, 'max': 90.0},
                'lon': {'type': float, 'min': -180.0, 'max': 180.0}
            },
            'mac_addresses': {
                'type': list,
                'item_type': str,
                'pattern': r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$'
            },
            'node_status': {
                'type': str,
                'allowed_values': ['active', 'inactive', 'error', 'maintenance', 'offline']
            },
            'timestamp': {
                'type': int,
                'min': 0
            },
            'additional_data': {
                'type': dict
            }
        }
    
    def validate_mesh_data(self, mesh_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate mesh network data structure.
        
        Args:
            mesh_data: Mesh network data to validate
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        # Check required fields
        for field in self.required_fields:
            if field not in mesh_data:
                errors.append(f"Missing required field: {field}")
        
        # Validate each field
        for field, value in mesh_data.items():
            if field in self.validation_rules:
                field_errors = self._validate_field(field, value)
                errors.extend(field_errors)
        
        return len(errors) == 0, errors
    
    def _validate_field(self, field_name: str, value: Any) -> List[str]:
        """Validate a specific field according to its rules."""
        errors = []
        rules = self.validation_rules.get(field_name, {})
        
        # Type validation
        if 'type' in rules:
            if not isinstance(value, rules['type']):
                errors.append(f"Field '{field_name}' must be of type {rules['type'].__name__}")
                return errors
        
        # GPS validation
        if field_name == 'gps':
            if not isinstance(value, dict):
                errors.append("GPS must be a dictionary")
            else:
                for coord, coord_value in value.items():
                    if coord in rules:
                        coord_errors = self._validate_field(f"{field_name}.{coord}", coord_value)
                        errors.extend(coord_errors)
        
        # MAC addresses validation
        elif field_name == 'mac_addresses':
            if not isinstance(value, list):
                errors.append("MAC addresses must be a list")
            else:
                import re
                pattern = rules['pattern']
                for i, mac in enumerate(value):
                    if not isinstance(mac, str):
                        errors.append(f"MAC address {i} must be a string")
                    elif not re.match(pattern, mac):
                        errors.append(f"MAC address {i} has invalid format: {mac}")
        
        # Node status validation
        elif field_name == 'node_status':
            if value not in rules['allowed_values']:
                errors.append(f"Node status must be one of: {rules['allowed_values']}")
        
        # Timestamp validation
        elif field_name == 'timestamp':
            if value < rules['min']:
                errors.append(f"Timestamp must be >= {rules['min']}")
        
        # Range validation for numeric fields
        if 'min' in rules and isinstance(value, (int, float)):
            if value < rules['min']:
                errors.append(f"Field '{field_name}' must be >= {rules['min']}")
        
        if 'max' in rules and isinstance(value, (int, float)):
            if value > rules['max']:
                errors.append(f"Field '{field_name}' must be <= {rules['max']}")
        
        return errors


class DataCompressor:
    """
    Data compression utilities for mesh network data.
    
    Provides various compression techniques to reduce data size
    before steganographic embedding.
    """
    
    def __init__(self):
        self.compression_methods = {
            'gzip': self._compress_gzip,
            'lzma': self._compress_lzma,
            'zlib': self._compress_zlib,
            'custom': self._compress_custom
        }
    
    def compress_data(self, data: bytes, method: str = 'gzip') -> bytes:
        """
        Compress data using specified method.
        
        Args:
            data: Data to compress
            method: Compression method to use
            
        Returns:
            Compressed data
        """
        if method not in self.compression_methods:
            raise ValueError(f"Unknown compression method: {method}")
        
        return self.compression_methods[method](data)
    
    def decompress_data(self, compressed_data: bytes, method: str = 'gzip') -> bytes:
        """
        Decompress data using specified method.
        
        Args:
            compressed_data: Compressed data
            method: Compression method used
            
        Returns:
            Decompressed data
        """
        if method == 'gzip':
            import gzip
            return gzip.decompress(compressed_data)
        elif method == 'lzma':
            import lzma
            return lzma.decompress(compressed_data)
        elif method == 'zlib':
            import zlib
            return zlib.decompress(compressed_data)
        elif method == 'custom':
            return self._decompress_custom(compressed_data)
        else:
            raise ValueError(f"Unknown compression method: {method}")
    
    def _compress_gzip(self, data: bytes) -> bytes:
        """Compress data using gzip."""
        import gzip
        return gzip.compress(data)
    
    def _compress_lzma(self, data: bytes) -> bytes:
        """Compress data using LZMA."""
        import lzma
        return lzma.compress(data)
    
    def _compress_zlib(self, data: bytes) -> bytes:
        """Compress data using zlib."""
        import zlib
        return zlib.compress(data)
    
    def _compress_custom(self, data: bytes) -> bytes:
        """Custom compression algorithm for mesh data."""
        # Simple run-length encoding for demonstration
        compressed = bytearray()
        i = 0
        while i < len(data):
            count = 1
            while i + count < len(data) and data[i] == data[i + count] and count < 255:
                count += 1
            
            if count > 3:
                compressed.extend([0xFF, data[i], count])
                i += count
            else:
                compressed.append(data[i])
                i += 1
        
        return bytes(compressed)
    
    def _decompress_custom(self, compressed_data: bytes) -> bytes:
        """Decompress custom compressed data."""
        decompressed = bytearray()
        i = 0
        while i < len(compressed_data):
            if compressed_data[i] == 0xFF and i + 2 < len(compressed_data):
                value = compressed_data[i + 1]
                count = compressed_data[i + 2]
                decompressed.extend([value] * count)
                i += 3
            else:
                decompressed.append(compressed_data[i])
                i += 1
        
        return bytes(decompressed)


class SecurityUtils:
    """
    Security utilities for steganographic data protection.
    
    Provides encryption, authentication, and integrity checking
    for sensitive mesh network data.
    """
    
    def __init__(self, encryption_key: Optional[bytes] = None):
        """
        Initialize security utilities.
        
        Args:
            encryption_key: Optional encryption key for data protection
        """
        self.encryption_key = encryption_key or self._generate_key()
    
    def _generate_key(self) -> bytes:
        """Generate a random encryption key."""
        return hashlib.sha256(str(time.time()).encode()).digest()
    
    def encrypt_data(self, data: bytes) -> bytes:
        """
        Encrypt data using AES encryption.
        
        Args:
            data: Data to encrypt
            
        Returns:
            Encrypted data with IV
        """
        from cryptography.fernet import Fernet
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
        
        # Generate key from master key
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'stego_salt',
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(self.encryption_key))
        
        # Encrypt data
        f = Fernet(key)
        return f.encrypt(data)
    
    def decrypt_data(self, encrypted_data: bytes) -> bytes:
        """
        Decrypt data using AES decryption.
        
        Args:
            encrypted_data: Encrypted data with IV
            
        Returns:
            Decrypted data
        """
        from cryptography.fernet import Fernet
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
        
        # Generate key from master key
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'stego_salt',
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(self.encryption_key))
        
        # Decrypt data
        f = Fernet(key)
        return f.decrypt(encrypted_data)
    
    def calculate_checksum(self, data: bytes) -> str:
        """
        Calculate SHA-256 checksum for data integrity.
        
        Args:
            data: Data to checksum
            
        Returns:
            Hex checksum string
        """
        return hashlib.sha256(data).hexdigest()
    
    def verify_checksum(self, data: bytes, expected_checksum: str) -> bool:
        """
        Verify data integrity using checksum.
        
        Args:
            data: Data to verify
            expected_checksum: Expected checksum
            
        Returns:
            True if checksum matches, False otherwise
        """
        actual_checksum = self.calculate_checksum(data)
        return actual_checksum == expected_checksum


class PerformanceMonitor:
    """
    Performance monitoring utilities for the steganographic system.
    
    Tracks encoding/decoding performance, compression ratios, and system metrics.
    """
    
    def __init__(self):
        self.metrics = {
            'encoding_times': [],
            'decoding_times': [],
            'compression_ratios': [],
            'error_rates': [],
            'throughput': []
        }
        self.start_time = None
    
    def start_timer(self):
        """Start performance timer."""
        self.start_time = time.time()
    
    def stop_timer(self) -> float:
        """
        Stop performance timer and return elapsed time.
        
        Returns:
            Elapsed time in seconds
        """
        if self.start_time is None:
            return 0.0
        
        elapsed = time.time() - self.start_time
        self.start_time = None
        return elapsed
    
    def record_encoding_time(self, elapsed_time: float):
        """Record encoding time metric."""
        self.metrics['encoding_times'].append(elapsed_time)
    
    def record_decoding_time(self, elapsed_time: float):
        """Record decoding time metric."""
        self.metrics['decoding_times'].append(elapsed_time)
    
    def record_compression_ratio(self, original_size: int, compressed_size: int):
        """Record compression ratio metric."""
        ratio = original_size / compressed_size if compressed_size > 0 else 1.0
        self.metrics['compression_ratios'].append(ratio)
    
    def record_error_rate(self, total_messages: int, failed_messages: int):
        """Record error rate metric."""
        rate = failed_messages / total_messages if total_messages > 0 else 0.0
        self.metrics['error_rates'].append(rate)
    
    def record_throughput(self, data_size: int, elapsed_time: float):
        """Record throughput metric (bytes per second)."""
        throughput = data_size / elapsed_time if elapsed_time > 0 else 0.0
        self.metrics['throughput'].append(throughput)
    
    def get_average_metrics(self) -> Dict[str, float]:
        """
        Calculate average metrics.
        
        Returns:
            Dictionary of average metric values
        """
        averages = {}
        
        for metric_name, values in self.metrics.items():
            if values:
                averages[f'avg_{metric_name}'] = sum(values) / len(values)
                averages[f'min_{metric_name}'] = min(values)
                averages[f'max_{metric_name}'] = max(values)
            else:
                averages[f'avg_{metric_name}'] = 0.0
                averages[f'min_{metric_name}'] = 0.0
                averages[f'max_{metric_name}'] = 0.0
        
        return averages
    
    def generate_report(self) -> str:
        """
        Generate performance report.
        
        Returns:
            Formatted performance report string
        """
        averages = self.get_average_metrics()
        
        report = "=== Steganographic QR Code Performance Report ===\n\n"
        
        report += f"Encoding Performance:\n"
        report += f"  Average time: {averages.get('avg_encoding_times', 0):.4f} seconds\n"
        report += f"  Min time: {averages.get('min_encoding_times', 0):.4f} seconds\n"
        report += f"  Max time: {averages.get('max_encoding_times', 0):.4f} seconds\n\n"
        
        report += f"Decoding Performance:\n"
        report += f"  Average time: {averages.get('avg_decoding_times', 0):.4f} seconds\n"
        report += f"  Min time: {averages.get('min_decoding_times', 0):.4f} seconds\n"
        report += f"  Max time: {averages.get('max_decoding_times', 0):.4f} seconds\n\n"
        
        report += f"Compression Performance:\n"
        report += f"  Average ratio: {averages.get('avg_compression_ratios', 0):.2f}x\n"
        report += f"  Min ratio: {averages.get('min_compression_ratios', 0):.2f}x\n"
        report += f"  Max ratio: {averages.get('max_compression_ratios', 0):.2f}x\n\n"
        
        report += f"Error Rate:\n"
        report += f"  Average: {averages.get('avg_error_rates', 0):.4f} ({averages.get('avg_error_rates', 0)*100:.2f}%)\n\n"
        
        report += f"Throughput:\n"
        report += f"  Average: {averages.get('avg_throughput', 0):.2f} bytes/second\n"
        report += f"  Min: {averages.get('min_throughput', 0):.2f} bytes/second\n"
        report += f"  Max: {averages.get('max_throughput', 0):.2f} bytes/second\n"
        
        return report


def generate_random_mesh_data() -> Dict[str, Any]:
    """
    Generate random mesh network data for testing.
    
    Returns:
        Random mesh network data dictionary
    """
    # Random GPS coordinates
    lat = random.uniform(-90, 90)
    lon = random.uniform(-180, 180)
    
    # Random MAC addresses
    mac_addresses = []
    for _ in range(random.randint(1, 5)):
        mac = ':'.join([f"{random.randint(0, 255):02X}" for _ in range(6)])
        mac_addresses.append(mac)
    
    # Random node status
    statuses = ['active', 'inactive', 'error', 'maintenance', 'offline']
    node_status = random.choice(statuses)
    
    # Current timestamp
    timestamp = int(time.time())
    
    # Random additional data
    additional_data = {
        'battery_level': random.randint(0, 100),
        'signal_strength': random.randint(-100, -30),
        'temperature': random.uniform(-40, 85),
        'humidity': random.uniform(0, 100)
    }
    
    return {
        'gps': {'lat': lat, 'lon': lon},
        'mac_addresses': mac_addresses,
        'node_status': node_status,
        'timestamp': timestamp,
        'additional_data': additional_data
    }


def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate distance between two GPS coordinates using Haversine formula.
    
    Args:
        lat1, lon1: First coordinate
        lat2, lon2: Second coordinate
        
    Returns:
        Distance in meters
    """
    R = 6371000  # Earth's radius in meters
    
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    return R * c


def format_timestamp(timestamp: int) -> str:
    """
    Format timestamp as human-readable string.
    
    Args:
        timestamp: Unix timestamp
        
    Returns:
        Formatted timestamp string
    """
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')


def validate_mac_address(mac: str) -> bool:
    """
    Validate MAC address format.
    
    Args:
        mac: MAC address string
        
    Returns:
        True if valid format, False otherwise
    """
    import re
    pattern = r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$'
    return bool(re.match(pattern, mac)) 