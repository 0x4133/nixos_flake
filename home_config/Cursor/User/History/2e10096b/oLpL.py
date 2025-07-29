# mesh_stego.py - Steganographic Mesh Communication System

import qrcode
import json
import base64
import hashlib
import random
import string
from PIL import Image
from typing import Dict, List, Tuple, Any
from dataclasses import dataclass
from datetime import datetime

@dataclass
class MeshNode:
    """Represents a mesh network node"""
    node_id: str
    gps_lat: float
    gps_lon: float
    bluetooth_devices: List[str]
    timestamp: str
    battery_level: int
    ai_capability: bool = False

class SymbolicEncoder:
    """Converts mesh data into mathematical symbols"""
    
    # Symbol mapping for different data types
    SYMBOLS = {
        'node': '⬢',      # Node identifier
        'gps': '🌐',       # GPS coordinates  
        'bt': '📡',        # Bluetooth data
        'time': '⏰',      # Timestamp
        'battery': '🔋',   # Battery level
        'ai': '🧠',        # AI capability
        'sep': '|',        # Data separator
        'end': '■'         # End marker
    }
    
    def encode_mesh_data(self, node: MeshNode) -> str:
        """Convert mesh node data to symbolic representation"""
        
        # Compress GPS to 6 decimal places and encode
        gps_data = f"{node.gps_lat:.6f},{node.gps_lon:.6f}"
        gps_encoded = self._compress_coordinates(gps_data)
        
        # Encode Bluetooth devices as hash signatures
        bt_signature = self._create_bt_signature(node.bluetooth_devices)
        
        # Create symbolic string
        symbolic = (
            f"{self.SYMBOLS['node']}{node.node_id}"
            f"{self.SYMBOLS['sep']}"
            f"{self.SYMBOLS['gps']}{gps_encoded}"
            f"{self.SYMBOLS['sep']}"
            f"{self.SYMBOLS['bt']}{bt_signature}"
            f"{self.SYMBOLS['sep']}"
            f"{self.SYMBOLS['time']}{self._encode_timestamp(node.timestamp)}"
            f"{self.SYMBOLS['sep']}"
            f"{self.SYMBOLS['battery']}{node.battery_level:02d}"
            f"{self.SYMBOLS['sep']}"
            f"{self.SYMBOLS['ai']}{'1' if node.ai_capability else '0'}"
            f"{self.SYMBOLS['end']}"
        )
        
        return symbolic
    
    def decode_mesh_data(self, symbolic: str) -> MeshNode:
        """Convert symbolic representation back to mesh data"""
        
        parts = symbolic.split(self.SYMBOLS['sep'])
        
        # Extract components
        node_id = parts[0].replace(self.SYMBOLS['node'], '')
        gps_data = self._decompress_coordinates(parts[1].replace(self.SYMBOLS['gps'], ''))
        bt_signature = parts[2].replace(self.SYMBOLS['bt'], '')
        timestamp = self._decode_timestamp(parts[3].replace(self.SYMBOLS['time'], ''))
        battery = int(parts[4].replace(self.SYMBOLS['battery'], ''))
        ai_capable = parts[5].replace(self.SYMBOLS['ai'], '').replace(self.SYMBOLS['end'], '') == '1'
        
        lat, lon = map(float, gps_data.split(','))
        
        return MeshNode(
            node_id=node_id,
            gps_lat=lat,
            gps_lon=lon,
            bluetooth_devices=[bt_signature],  # Simplified for demo
            timestamp=timestamp,
            battery_level=battery,
            ai_capability=ai_capable
        )
    
    def _compress_coordinates(self, gps_str: str) -> str:
        """Compress GPS coordinates using base64"""
        return base64.b64encode(gps_str.encode()).decode()[:16]
    
    def _decompress_coordinates(self, compressed: str) -> str:
        """Decompress GPS coordinates"""
        # Add padding if needed
        compressed += '=' * (4 - len(compressed) % 4)
        try:
            return base64.b64decode(compressed.encode()).decode()
        except:
            return "0.000000,0.000000"  # Fallback
    
    def _create_bt_signature(self, bt_devices: List[str]) -> str:
        """Create unique signature from Bluetooth devices"""
        if not bt_devices:
            return "NONE"
        
        # Sort and hash the device list for consistent signature
        device_str = ''.join(sorted(bt_devices))
        return hashlib.md5(device_str.encode()).hexdigest()[:8]
    
    def _encode_timestamp(self, timestamp: str) -> str:
        """Encode timestamp as compact representation"""
        # Convert to epoch and take last 8 digits
        try:
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            epoch = int(dt.timestamp())
            return str(epoch)[-8:]
        except:
            return ""