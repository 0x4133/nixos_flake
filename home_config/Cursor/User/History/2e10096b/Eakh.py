from stego_qr import StegoQRGenerator, MeshDataEncoder

# Create mesh network data
mesh_data = {
    'gps': {'lat': 40.7128, 'lon': -74.0060},
    'mac_addresses': ['AA:BB:CC:DD:EE:FF', '11:22:33:44:55:66'],
    'node_status': 'active',
    'timestamp': 1640995200
}

# Generate steganographic QR code
generator = StegoQRGenerator()
qr_image = generator.encode_as_wifi_password(mesh_data, "MyWiFi", "password123")

# Decode the hidden data
decoder = StegoQRGenerator()
extracted_data = decoder.decode_from_qr(qr_image)
print(extracted_data)