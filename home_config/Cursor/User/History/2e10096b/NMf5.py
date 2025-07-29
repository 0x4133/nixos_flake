# Simple Steganographic Mesh System - KISS Method

import qrcode
import base64
import json
import hashlib
from datetime import datetime

class MeshStego:
    """Dead simple mesh data hiding in QR codes"""
    
    def __init__(self):
        pass
    
    def hide_data_in_qr(self, node_id, lat, lon, bluetooth_macs, battery):
        """Hide mesh data in a fake WiFi QR code"""
        
        # Pack all data into simple dict
        mesh_data = {
            'id': node_id,
            'lat': lat,
            'lon': lon,
            'bt': bluetooth_macs,
            'bat': battery,
            'time': int(datetime.now().timestamp())
        }
        
        # Convert to JSON and encode
        json_str = json.dumps(mesh_data)
        encoded_data = base64.b64encode(json_str.encode()).decode()
        
        # Make it look like a WiFi password
        fake_ssid = f"MeshNet_{hash(node_id) % 9999:04d}"
        wifi_qr = f"WIFI:T:WPA;S:{fake_ssid};P:{encoded_data};;"
        
        # Generate QR code
        qr = qrcode.QRCode(box_size=10, border=4)
        qr.add_data(wifi_qr)
        qr.make()
        
        return qr.make_image(), wifi_qr
    
    def extract_data_from_qr(self, qr_text):
        """Extract mesh data from fake WiFi QR code"""
        
        # Find the password field
        if 'P:' not in qr_text:
            return None
            
        # Extract encoded data
        start = qr_text.find('P:') + 2
        end = qr_text.find(';', start)
        encoded_data = qr_text[start:end]
        
        try:
            # Decode back to JSON
            json_str = base64.b64decode(encoded_data.encode()).decode()
            return json.loads(json_str)
        except:
            return None
    
    def make_bluetooth_signature(self, mac_addresses):
        """Create unique signature from Bluetooth devices"""
        if not mac_addresses:
            return "NONE"
        
        # Sort and hash for consistent signature
        combined = ''.join(sorted(mac_addresses))
        return hashlib.md5(combined.encode()).hexdigest()[:8]

# Example usage
if __name__ == "__main__":
    
    # Create the system
    stego = MeshStego()
    
    # Example mesh node data
    node_id = "NODE001"
    lat, lon = 37.7749, -122.4194  # San Francisco
    bluetooth_devices = ["AA:BB:CC:DD:EE:FF", "11:22:33:44:55:66"]
    battery = 85
    
    # Hide data in QR code
    qr_image, qr_text = stego.hide_data_in_qr(node_id, lat, lon, bluetooth_devices, battery)
    
    print("QR Code Content (looks like WiFi):")
    print(qr_text)
    print()
    
    # Extract hidden data
    hidden_data = stego.extract_data_from_qr(qr_text)
    
    print("Hidden Mesh Data:")
    print(f"Node: {hidden_data['id']}")
    print(f"Location: {hidden_data['lat']}, {hidden_data['lon']}")
    print(f"Bluetooth: {hidden_data['bt']}")
    print(f"Battery: {hidden_data['bat']}%")
    print(f"Timestamp: {hidden_data['time']}")
    
    # Create Bluetooth signature
    bt_sig = stego.make_bluetooth_signature(bluetooth_devices)
    print(f"BT Signature: {bt_sig}")
    
    # Save QR image
    qr_image.save("simple_mesh_qr.png")
    print("\nQR saved as 'simple_mesh_qr.png'")