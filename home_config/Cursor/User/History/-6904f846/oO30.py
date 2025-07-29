"""
Mesh Data Encoder - Compact Symbolic Encoding System

This module implements a sophisticated encoding system that converts mesh network data
into compact symbolic representations for steganographic embedding.
"""

import json
import base64
import hashlib
import struct
from typing import Dict, List, Any, Tuple
from datetime import datetime
import math


class MeshDataEncoder:
    """
    Compact symbolic encoding system for mesh network data.
    
    Features:
    - GPS coordinates: Base-36 encoding with precision optimization
    - MAC addresses: Frequency analysis and delta encoding
    - Timestamps: Relative encoding with epoch optimization
    - Node status: Huffman-coded status indicators
    """
    
    def __init__(self):
        # Huffman codes for common node statuses
        self.status_codes = {
            'active': '0',
            'inactive': '10',
            'error': '110',
            'maintenance': '1110',
            'offline': '1111'
        }
        
        # Common MAC address prefixes for compression
        self.mac_prefixes = {
            'AA:BB:CC': 0,
            '11:22:33': 1,
            '44:55:66': 2,
            '77:88:99': 3,
            'AA:11:BB': 4,
            'CC:22:DD': 5
        }
        
        # Epoch for timestamp optimization
        self.epoch = 1640995200  # 2022-01-01 00:00:00 UTC
    
    def encode_mesh_data(self, mesh_data: Dict[str, Any]) -> str:
        """
        Encode mesh network data into a compact symbolic string.
        
        Args:
            mesh_data: Dictionary containing mesh network data
            
        Returns:
            Compact encoded string ready for steganographic embedding
        """
        encoded_parts = []
        
        # Encode GPS coordinates
        if 'gps' in mesh_data:
            gps_encoded = self._encode_gps(mesh_data['gps'])
            encoded_parts.append(f"G{gps_encoded}")
        
        # Encode MAC addresses
        if 'mac_addresses' in mesh_data:
            mac_encoded = self._encode_mac_addresses(mesh_data['mac_addresses'])
            encoded_parts.append(f"M{mac_encoded}")
        
        # Encode node status
        if 'node_status' in mesh_data:
            status_encoded = self._encode_node_status(mesh_data['node_status'])
            encoded_parts.append(f"S{status_encoded}")
        
        # Encode timestamp
        if 'timestamp' in mesh_data:
            timestamp_encoded = self._encode_timestamp(mesh_data['timestamp'])
            encoded_parts.append(f"T{timestamp_encoded}")
        
        # Encode additional data
        if 'additional_data' in mesh_data:
            additional_encoded = self._encode_additional_data(mesh_data['additional_data'])
            encoded_parts.append(f"A{additional_encoded}")
        
        # Join all parts with separator
        encoded_string = "|".join(encoded_parts)
        
        # Add checksum for error detection
        checksum = self._calculate_checksum(encoded_string)
        final_encoded = f"{encoded_string}|C{checksum}"
        
        return final_encoded
    
    def decode_mesh_data(self, encoded_string: str) -> Dict[str, Any]:
        """
        Decode a compact symbolic string back into mesh network data.
        
        Args:
            encoded_string: Compact encoded string from steganographic extraction
            
        Returns:
            Dictionary containing decoded mesh network data
        """
        # Verify checksum
        parts = encoded_string.split("|")
        if len(parts) < 2:
            raise ValueError("Invalid encoded string format")
        
        checksum = parts[-1][1:]  # Remove 'C' prefix
        data_parts = parts[:-1]
        
        # Reconstruct data string for checksum verification
        data_string = "|".join(data_parts)
        expected_checksum = self._calculate_checksum(data_string)
        
        if checksum != expected_checksum:
            raise ValueError("Checksum verification failed")
        
        # Decode each part
        decoded_data = {}
        
        for part in data_parts:
            if not part:
                continue
                
            prefix = part[0]
            data = part[1:]
            
            if prefix == 'G':
                decoded_data['gps'] = self._decode_gps(data)
            elif prefix == 'M':
                decoded_data['mac_addresses'] = self._decode_mac_addresses(data)
            elif prefix == 'S':
                decoded_data['node_status'] = self._decode_node_status(data)
            elif prefix == 'T':
                decoded_data['timestamp'] = self._decode_timestamp(data)
            elif prefix == 'A':
                decoded_data['additional_data'] = self._decode_additional_data(data)
        
        return decoded_data
    
    def _encode_gps(self, gps_data: Dict[str, float]) -> str:
        """Encode GPS coordinates using base-36 with precision optimization."""
        lat = gps_data.get('lat', 0.0)
        lon = gps_data.get('lon', 0.0)
        
        # Convert to fixed-point integers (6 decimal places precision)
        lat_int = int(lat * 1000000)
        lon_int = int(lon * 1000000)
        
        # Encode as base-36 strings
        lat_encoded = self._int_to_base36(lat_int)
        lon_encoded = self._int_to_base36(lon_int)
        
        return f"{lat_encoded},{lon_encoded}"
    
    def _decode_gps(self, encoded_gps: str) -> Dict[str, float]:
        """Decode GPS coordinates from base-36 encoding."""
        lat_encoded, lon_encoded = encoded_gps.split(',')
        
        lat_int = self._base36_to_int(lat_encoded)
        lon_int = self._base36_to_int(lon_encoded)
        
        lat = lat_int / 1000000.0
        lon = lon_int / 1000000.0
        
        return {'lat': lat, 'lon': lon}
    
    def _encode_mac_addresses(self, mac_addresses: List[str]) -> str:
        """Encode MAC addresses using frequency analysis and delta encoding."""
        encoded_parts = []
        
        for mac in mac_addresses:
            # Check if MAC starts with known prefix
            prefix_found = False
            for prefix, code in self.mac_prefixes.items():
                if mac.startswith(prefix):
                    # Use prefix code + remaining bytes
                    remaining = mac[len(prefix):]
                    encoded_parts.append(f"P{code}{remaining}")
                    prefix_found = True
                    break
            
            if not prefix_found:
                # Full MAC encoding
                encoded_parts.append(f"F{mac}")
        
        return ";".join(encoded_parts)
    
    def _decode_mac_addresses(self, encoded_macs: str) -> List[str]:
        """Decode MAC addresses from frequency analysis encoding."""
        mac_addresses = []
        
        for part in encoded_macs.split(';'):
            if part.startswith('P'):
                # Prefix-based encoding
                code = int(part[1])
                remaining = part[2:]
                
                # Find prefix by code
                prefix = None
                for p, c in self.mac_prefixes.items():
                    if c == code:
                        prefix = p
                        break
                
                if prefix:
                    mac_addresses.append(prefix + remaining)
            elif part.startswith('F'):
                # Full MAC encoding
                mac_addresses.append(part[1:])
        
        return mac_addresses
    
    def _encode_node_status(self, status: str) -> str:
        """Encode node status using Huffman codes."""
        if status in self.status_codes:
            return self.status_codes[status]
        else:
            # Fallback: encode as base-36
            return f"X{self._int_to_base36(hash(status) % 1000000)}"
    
    def _decode_node_status(self, encoded_status: str) -> str:
        """Decode node status from Huffman codes."""
        # Reverse lookup for Huffman codes
        reverse_codes = {v: k for k, v in self.status_codes.items()}
        
        if encoded_status in reverse_codes:
            return reverse_codes[encoded_status]
        elif encoded_status.startswith('X'):
            # Fallback decoding
            return f"unknown_status_{self._base36_to_int(encoded_status[1:])}"
        else:
            return "unknown"
    
    def _encode_timestamp(self, timestamp: int) -> str:
        """Encode timestamp using relative encoding with epoch optimization."""
        # Use relative encoding from epoch
        relative_time = timestamp - self.epoch
        
        # Encode as base-36
        return self._int_to_base36(relative_time)
    
    def _decode_timestamp(self, encoded_timestamp: str) -> int:
        """Decode timestamp from relative encoding."""
        relative_time = self._base36_to_int(encoded_timestamp)
        return self.epoch + relative_time
    
    def _encode_additional_data(self, data: Dict[str, Any]) -> str:
        """Encode additional data using JSON compression."""
        json_str = json.dumps(data, separators=(',', ':'))
        # Base64 encode for binary safety
        return base64.urlsafe_b64encode(json_str.encode()).decode()
    
    def _decode_additional_data(self, encoded_data: str) -> Dict[str, Any]:
        """Decode additional data from JSON compression."""
        json_str = base64.urlsafe_b64decode(encoded_data.encode()).decode()
        return json.loads(json_str)
    
    def _calculate_checksum(self, data: str) -> str:
        """Calculate checksum for error detection."""
        return hashlib.md5(data.encode()).hexdigest()[:8]
    
    def _int_to_base36(self, num: int) -> str:
        """Convert integer to base-36 string."""
        if num == 0:
            return '0'
        
        digits = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'
        result = ''
        
        while num > 0:
            num, remainder = divmod(num, 36)
            result = digits[remainder] + result
        
        return result
    
    def _base36_to_int(self, s: str) -> int:
        """Convert base-36 string to integer."""
        return int(s.upper(), 36)
    
    def get_compression_ratio(self, original_data: Dict[str, Any]) -> float:
        """
        Calculate compression ratio achieved by the encoding system.
        
        Args:
            original_data: Original mesh network data
            
        Returns:
            Compression ratio (original_size / encoded_size)
        """
        # Calculate original size (approximate)
        original_json = json.dumps(original_data, separators=(',', ':'))
        original_size = len(original_json)
        
        # Calculate encoded size
        encoded_string = self.encode_mesh_data(original_data)
        encoded_size = len(encoded_string)
        
        return original_size / encoded_size if encoded_size > 0 else 1.0 