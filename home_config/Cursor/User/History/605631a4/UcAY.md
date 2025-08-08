# Steganographic QR Code Generator for Mesh Networks

A sophisticated steganographic communication system that embeds mesh network data into QR codes that appear as legitimate content (WiFi passwords, contact info, URLs).

## Features

- **Steganographic Encoding**: Embeds mesh network data into QR codes that look like normal content
- **Compact Symbolic Encoding**: Efficient mathematical encoding system for GPS coordinates, MAC addresses, timestamps
- **Error Correction**: Built-in Reed-Solomon error correction for reliable transmission
- **Modular Design**: Separate modules for encoding, decoding, and transport layers
- **Multiple Transport Support**: LoRa, Bluetooth, and cellular transport layers
- **Stealth Mode**: QR codes pass casual inspection as legitimate content

## Installation

```bash
pip install -r requirements.txt
```

## Quick Start

```python
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
```

## Architecture

### Core Modules

1. **`stego_qr.py`** - Main steganographic QR code generator
2. **`mesh_encoder.py`** - Compact symbolic encoding system
3. **`transport_layers.py`** - Transport layer abstractions
4. **`error_correction.py`** - Reed-Solomon error correction
5. **`utils.py`** - Utility functions and helpers

### Symbolic Encoding System

The system uses a compact mathematical encoding that converts mesh data into symbolic representations:

- **GPS Coordinates**: Converted to base-36 encoded strings with precision optimization
- **MAC Addresses**: Compressed using frequency analysis and delta encoding
- **Timestamps**: Relative encoding with epoch optimization
- **Node Status**: Huffman-coded status indicators

### Steganographic Techniques

1. **WiFi QR Codes**: Embed data in SSID/password fields
2. **Contact QR Codes**: Hide data in phone/email fields
3. **URL QR Codes**: Encode data in URL parameters
4. **Text QR Codes**: Use invisible Unicode characters

## Usage Examples

See `examples/` directory for complete usage examples and test cases.

## Testing

```bash
pytest tests/
```

## License

MIT License - See LICENSE file for details. 