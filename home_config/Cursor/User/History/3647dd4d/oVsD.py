"""
Simplified Steganographic QR Code Generator - No External Dependencies

Main module for embedding mesh network data into QR codes that appear as legitimate content
(WiFi passwords, contact info, URLs, etc.) while maintaining stealth and functionality.
This version uses only standard Python libraries.
"""

import base64
import hashlib
import json
import re
import random
import string
from typing import Dict, List, Any, Optional, Tuple, Union
import io

from mesh_encoder import MeshDataEncoder
from error_correction_simple import ErrorCorrectionManager


class StegoQRGenerator:
    """
    Steganographic QR code generator for mesh network data.
    
    Embeds encoded mesh network data into QR codes that appear as legitimate content
    while maintaining the original functionality of the QR code.
    """
    
    def __init__(self, error_correction_level: str = 'M'):
        """
        Initialize steganographic QR generator.
        
        Args:
            error_correction_level: QR code error correction level (L, M, Q, H)
        """
        self.error_correction_level = error_correction_level
        self.mesh_encoder = MeshDataEncoder()
        self.error_correction = ErrorCorrectionManager()
        
        # Steganographic techniques configuration
        self.stego_config = {
            'wifi': {
                'max_ssid_length': 32,
                'max_password_length': 63,
                'stealth_chars': ['\u200B', '\u200C', '\u200D', '\uFEFF']  # Zero-width characters
            },
            'contact': {
                'max_name_length': 50,
                'max_phone_length': 20,
                'max_email_length': 100
            },
            'url': {
                'max_url_length': 2000,
                'param_separator': '&',
                'stealth_param': '_stego'
            },
            'text': {
                'max_text_length': 3000,
                'stealth_chars': ['\u200B', '\u200C', '\u200D', '\uFEFF']
            }
        }
    
    def encode_as_wifi_password(self, mesh_data: Dict[str, Any], ssid: str, 
                               password: str) -> str:
        """
        Encode mesh data into a QR code that appears as a WiFi network.
        
        Args:
            mesh_data: Mesh network data to encode
            ssid: WiFi network name
            password: WiFi password
            
        Returns:
            QR code data string (ready for QR code generation)
        """
        # Encode mesh data
        encoded_data = self.mesh_encoder.encode_mesh_data(mesh_data)
        
        # Add error correction
        data_bytes = encoded_data.encode('utf-8')
        error_corrected_data = self.error_correction.encode_with_error_correction(data_bytes)
        
        # Convert to base64 for embedding
        stego_data = base64.b64encode(error_corrected_data).decode('utf-8')
        
        # Create WiFi QR code format
        wifi_format = f"WIFI:S:{ssid};T:WPA;P:{password};;"
        
        # Embed steganographic data using zero-width characters
        stealth_chars = self.stego_config['wifi']['stealth_chars']
        embedded_password = self._embed_in_text(password, stego_data, stealth_chars)
        
        # Create final WiFi QR code
        final_wifi_format = f"WIFI:S:{ssid};T:WPA;P:{embedded_password};;"
        
        return final_wifi_format
    
    def encode_as_contact(self, mesh_data: Dict[str, Any], name: str, 
                         phone: str, email: str) -> str:
        """
        Encode mesh data into a QR code that appears as contact information.
        
        Args:
            mesh_data: Mesh network data to encode
            name: Contact name
            phone: Phone number
            email: Email address
            
        Returns:
            QR code data string (ready for QR code generation)
        """
        # Encode mesh data
        encoded_data = self.mesh_encoder.encode_mesh_data(mesh_data)
        data_bytes = encoded_data.encode('utf-8')
        error_corrected_data = self.error_correction.encode_with_error_correction(data_bytes)
        stego_data = base64.b64encode(error_corrected_data).decode('utf-8')
        
        # Create contact QR code format
        contact_format = f"BEGIN:VCARD\nVERSION:3.0\nFN:{name}\nTEL:{phone}\nEMAIL:{email}\nEND:VCARD"
        
        # Embed steganographic data in email field
        stealth_chars = self.stego_config['contact']['stealth_chars']
        embedded_email = self._embed_in_text(email, stego_data, stealth_chars)
        
        # Create final contact QR code
        final_contact_format = f"BEGIN:VCARD\nVERSION:3.0\nFN:{name}\nTEL:{phone}\nEMAIL:{embedded_email}\nEND:VCARD"
        
        return final_contact_format
    
    def encode_as_url(self, mesh_data: Dict[str, Any], base_url: str) -> str:
        """
        Encode mesh data into a QR code that appears as a URL.
        
        Args:
            mesh_data: Mesh network data to encode
            base_url: Base URL for the QR code
            
        Returns:
            QR code data string (ready for QR code generation)
        """
        # Encode mesh data
        encoded_data = self.mesh_encoder.encode_mesh_data(mesh_data)
        data_bytes = encoded_data.encode('utf-8')
        error_corrected_data = self.error_correction.encode_with_error_correction(data_bytes)
        stego_data = base64.b64encode(error_corrected_data).decode('utf-8')
        
        # Create URL with steganographic parameter
        separator = '&' if '?' in base_url else '?'
        stealth_param = self.stego_config['url']['stealth_param']
        final_url = f"{base_url}{separator}{stealth_param}={stego_data}"
        
        return final_url
    
    def encode_as_text(self, mesh_data: Dict[str, Any], cover_text: str) -> str:
        """
        Encode mesh data into a QR code that appears as plain text.
        
        Args:
            mesh_data: Mesh network data to encode
            cover_text: Cover text for the QR code
            
        Returns:
            QR code data string (ready for QR code generation)
        """
        # Encode mesh data
        encoded_data = self.mesh_encoder.encode_mesh_data(mesh_data)
        data_bytes = encoded_data.encode('utf-8')
        error_corrected_data = self.error_correction.encode_with_error_correction(data_bytes)
        stego_data = base64.b64encode(error_corrected_data).decode('utf-8')
        
        # Embed steganographic data using zero-width characters
        stealth_chars = self.stego_config['text']['stealth_chars']
        embedded_text = self._embed_in_text(cover_text, stego_data, stealth_chars)
        
        return embedded_text
    
    def decode_from_qr_data(self, qr_data: str) -> Optional[Dict[str, Any]]:
        """
        Decode mesh data from a steganographic QR code data string.
        
        Args:
            qr_data: QR code data string
            
        Returns:
            Decoded mesh data or None if decoding fails
        """
        try:
            # Try different decoding methods
            decoded_data = None
            
            # Try WiFi format
            if qr_data.startswith('WIFI:'):
                decoded_data = self._decode_from_wifi(qr_data)
            
            # Try contact format
            elif qr_data.startswith('BEGIN:VCARD'):
                decoded_data = self._decode_from_contact(qr_data)
            
            # Try URL format
            elif qr_data.startswith(('http://', 'https://')):
                decoded_data = self._decode_from_url(qr_data)
            
            # Try plain text format
            else:
                decoded_data = self._decode_from_text(qr_data)
            
            return decoded_data
            
        except Exception as e:
            print(f"Error decoding QR code: {e}")
            return None
    
    def _embed_in_text(self, text: str, stego_data: str, stealth_chars: List[str]) -> str:
        """
        Embed steganographic data into text using zero-width characters.
        
        Args:
            text: Cover text
            stego_data: Data to embed
            stealth_chars: List of stealth characters to use
            
        Returns:
            Text with embedded steganographic data
        """
        # Convert stego data to binary
        binary_data = ''.join(format(ord(c), '08b') for c in stego_data)
        
        # Embed binary data using stealth characters
        embedded_text = text
        for i, bit in enumerate(binary_data):
            if i < len(stealth_chars):
                if bit == '1':
                    embedded_text += stealth_chars[i % len(stealth_chars)]
        
        return embedded_text
    
    def _extract_from_text(self, text: str, stealth_chars: List[str]) -> str:
        """
        Extract steganographic data from text using zero-width characters.
        
        Args:
            text: Text with embedded data
            stealth_chars: List of stealth characters used
            
        Returns:
            Extracted steganographic data
        """
        # Extract stealth characters
        binary_data = ""
        for char in text:
            if char in stealth_chars:
                binary_data += "1"
            elif char in ['\u200B', '\u200C', '\u200D', '\uFEFF']:
                binary_data += "0"
        
        # Convert binary to string
        if len(binary_data) % 8 != 0:
            return ""
        
        stego_data = ""
        for i in range(0, len(binary_data), 8):
            byte = binary_data[i:i+8]
            if byte:
                stego_data += chr(int(byte, 2))
        
        return stego_data
    
    def _decode_from_wifi(self, wifi_text: str) -> Optional[Dict[str, Any]]:
        """Decode mesh data from WiFi QR code format."""
        try:
            # Extract password field
            password_match = re.search(r'P:([^;]+);', wifi_text)
            if not password_match:
                return None
            
            password = password_match.group(1)
            
            # Extract steganographic data
            stealth_chars = self.stego_config['wifi']['stealth_chars']
            stego_data = self._extract_from_text(password, stealth_chars)
            
            if not stego_data:
                return None
            
            # Decode error correction and mesh data
            return self._decode_stego_data(stego_data)
            
        except Exception as e:
            print(f"Error decoding from WiFi format: {e}")
            return None
    
    def _decode_from_contact(self, contact_text: str) -> Optional[Dict[str, Any]]:
        """Decode mesh data from contact QR code format."""
        try:
            # Extract email field
            email_match = re.search(r'EMAIL:([^\n]+)', contact_text)
            if not email_match:
                return None
            
            email = email_match.group(1)
            
            # Extract steganographic data
            stealth_chars = self.stego_config['contact']['stealth_chars']
            stego_data = self._extract_from_text(email, stealth_chars)
            
            if not stego_data:
                return None
            
            # Decode error correction and mesh data
            return self._decode_stego_data(stego_data)
            
        except Exception as e:
            print(f"Error decoding from contact format: {e}")
            return None
    
    def _decode_from_url(self, url_text: str) -> Optional[Dict[str, Any]]:
        """Decode mesh data from URL QR code format."""
        try:
            # Extract steganographic parameter
            stealth_param = self.stego_config['url']['stealth_param']
            param_match = re.search(f'{stealth_param}=([^&]+)', url_text)
            
            if not param_match:
                return None
            
            stego_data = param_match.group(1)
            
            # Decode error correction and mesh data
            return self._decode_stego_data(stego_data)
            
        except Exception as e:
            print(f"Error decoding from URL format: {e}")
            return None
    
    def _decode_from_text(self, text: str) -> Optional[Dict[str, Any]]:
        """Decode mesh data from plain text QR code format."""
        try:
            # Extract steganographic data
            stealth_chars = self.stego_config['text']['stealth_chars']
            stego_data = self._extract_from_text(text, stealth_chars)
            
            if not stego_data:
                return None
            
            # Decode error correction and mesh data
            return self._decode_stego_data(stego_data)
            
        except Exception as e:
            print(f"Error decoding from text format: {e}")
            return None
    
    def _decode_stego_data(self, stego_data: str) -> Optional[Dict[str, Any]]:
        """
        Decode steganographic data through error correction and mesh encoding.
        
        Args:
            stego_data: Base64 encoded steganographic data
            
        Returns:
            Decoded mesh data or None if decoding fails
        """
        try:
            # Decode base64
            error_corrected_data = base64.b64decode(stego_data)
            
            # Decode error correction
            decoded_data, success = self.error_correction.decode_with_error_correction(error_corrected_data)
            
            if not success:
                print("Error correction decoding failed")
                return None
            
            # Decode mesh data
            encoded_string = decoded_data.decode('utf-8')
            mesh_data = self.mesh_encoder.decode_mesh_data(encoded_string)
            
            return mesh_data
            
        except Exception as e:
            print(f"Error decoding steganographic data: {e}")
            return None
    
    def get_compression_stats(self, mesh_data: Dict[str, Any]) -> Dict[str, float]:
        """
        Get compression statistics for mesh data encoding.
        
        Args:
            mesh_data: Mesh network data
            
        Returns:
            Dictionary with compression statistics
        """
        # Original size
        original_json = json.dumps(mesh_data, separators=(',', ':'))
        original_size = len(original_json)
        
        # Mesh encoding compression
        mesh_compression = self.mesh_encoder.get_compression_ratio(mesh_data)
        
        # Error correction expansion
        encoded_data = self.mesh_encoder.encode_mesh_data(mesh_data)
        data_bytes = encoded_data.encode('utf-8')
        error_correction_expansion = self.error_correction.get_compression_ratio(len(data_bytes))
        
        # Overall compression
        overall_compression = original_size / (len(data_bytes) * error_correction_expansion)
        
        return {
            'original_size': original_size,
            'mesh_compression_ratio': mesh_compression,
            'error_correction_expansion': error_correction_expansion,
            'overall_compression_ratio': overall_compression
        } 