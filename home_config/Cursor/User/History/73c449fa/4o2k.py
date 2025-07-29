#!/usr/bin/env python3
"""
Basic Usage Example - Steganographic QR Code Generator

This example demonstrates the basic usage of the steganographic QR code generator
for embedding mesh network data into QR codes that appear as legitimate content.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from stego_qr import StegoQRGenerator
from utils import generate_random_mesh_data, format_timestamp
import json


def main():
    """Demonstrate basic steganographic QR code generation and decoding."""
    
    print("=== Steganographic QR Code Generator - Basic Usage ===\n")
    
    # Initialize the steganographic QR generator
    generator = StegoQRGenerator()
    
    # Create sample mesh network data
    print("1. Creating sample mesh network data...")
    mesh_data = {
        'gps': {'lat': 40.7128, 'lon': -74.0060},  # New York City
        'mac_addresses': ['AA:BB:CC:DD:EE:FF', '11:22:33:44:55:66'],
        'node_status': 'active',
        'timestamp': 1640995200,
        'additional_data': {
            'battery_level': 85,
            'signal_strength': -45,
            'temperature': 22.5,
            'humidity': 65.2
        }
    }
    
    print(f"   GPS: {mesh_data['gps']['lat']:.4f}, {mesh_data['gps']['lon']:.4f}")
    print(f"   MAC Addresses: {mesh_data['mac_addresses']}")
    print(f"   Status: {mesh_data['node_status']}")
    print(f"   Timestamp: {format_timestamp(mesh_data['timestamp'])}")
    print(f"   Battery: {mesh_data['additional_data']['battery_level']}%")
    print()
    
    # Example 1: Encode as WiFi QR code
    print("2. Encoding as WiFi QR code...")
    wifi_qr = generator.encode_as_wifi_password(
        mesh_data, 
        ssid="MySecureWiFi", 
        password="SuperSecretPassword123!"
    )
    
    # Save the QR code
    wifi_qr.save("examples/wifi_stego_qr.png")
    print("   Saved as: examples/wifi_stego_qr.png")
    
    # Decode the hidden data
    print("   Decoding hidden data...")
    decoded_wifi_data = generator.decode_from_qr(wifi_qr)
    
    if decoded_wifi_data:
        print("   ✓ Successfully decoded mesh data from WiFi QR code")
        print(f"   GPS: {decoded_wifi_data['gps']['lat']:.4f}, {decoded_wifi_data['gps']['lon']:.4f}")
    else:
        print("   ✗ Failed to decode mesh data from WiFi QR code")
    print()
    
    # Example 2: Encode as Contact QR code
    print("3. Encoding as Contact QR code...")
    contact_qr = generator.encode_as_contact(
        mesh_data,
        name="John Doe",
        phone="+1-555-123-4567",
        email="john.doe@example.com"
    )
    
    # Save the QR code
    contact_qr.save("examples/contact_stego_qr.png")
    print("   Saved as: examples/contact_stego_qr.png")
    
    # Decode the hidden data
    print("   Decoding hidden data...")
    decoded_contact_data = generator.decode_from_qr(contact_qr)
    
    if decoded_contact_data:
        print("   ✓ Successfully decoded mesh data from Contact QR code")
        print(f"   Status: {decoded_contact_data['node_status']}")
    else:
        print("   ✗ Failed to decode mesh data from Contact QR code")
    print()
    
    # Example 3: Encode as URL QR code
    print("4. Encoding as URL QR code...")
    url_qr = generator.encode_as_url(
        mesh_data,
        base_url="https://example.com/api/status"
    )
    
    # Save the QR code
    url_qr.save("examples/url_stego_qr.png")
    print("   Saved as: examples/url_stego_qr.png")
    
    # Decode the hidden data
    print("   Decoding hidden data...")
    decoded_url_data = generator.decode_from_qr(url_qr)
    
    if decoded_url_data:
        print("   ✓ Successfully decoded mesh data from URL QR code")
        print(f"   MAC Addresses: {decoded_url_data['mac_addresses']}")
    else:
        print("   ✗ Failed to decode mesh data from URL QR code")
    print()
    
    # Example 4: Encode as Text QR code
    print("5. Encoding as Text QR code...")
    text_qr = generator.encode_as_text(
        mesh_data,
        cover_text="This is a sample text message for demonstration purposes."
    )
    
    # Save the QR code
    text_qr.save("examples/text_stego_qr.png")
    print("   Saved as: examples/text_stego_qr.png")
    
    # Decode the hidden data
    print("   Decoding hidden data...")
    decoded_text_data = generator.decode_from_qr(text_qr)
    
    if decoded_text_data:
        print("   ✓ Successfully decoded mesh data from Text QR code")
        print(f"   Additional Data: {decoded_text_data['additional_data']}")
    else:
        print("   ✗ Failed to decode mesh data from Text QR code")
    print()
    
    # Performance and compression statistics
    print("6. Performance and compression statistics...")
    stats = generator.get_compression_stats(mesh_data)
    
    print(f"   Original size: {stats['original_size']} bytes")
    print(f"   Mesh compression ratio: {stats['mesh_compression_ratio']:.2f}x")
    print(f"   Error correction expansion: {stats['error_correction_expansion']:.2f}x")
    print(f"   Overall compression ratio: {stats['overall_compression_ratio']:.2f}x")
    print()
    
    # Verification
    print("7. Data integrity verification...")
    all_decoded = [decoded_wifi_data, decoded_contact_data, decoded_url_data, decoded_text_data]
    
    for i, decoded in enumerate(all_decoded):
        if decoded:
            # Compare with original
            if decoded == mesh_data:
                print(f"   ✓ QR code {i+1}: Data integrity verified")
            else:
                print(f"   ✗ QR code {i+1}: Data integrity check failed")
        else:
            print(f"   ✗ QR code {i+1}: Decoding failed")
    
    print("\n=== Basic Usage Example Complete ===")
    print("\nGenerated QR codes:")
    print("  - examples/wifi_stego_qr.png (WiFi format)")
    print("  - examples/contact_stego_qr.png (Contact format)")
    print("  - examples/url_stego_qr.png (URL format)")
    print("  - examples/text_stego_qr.png (Text format)")
    print("\nYou can scan these QR codes with any QR code scanner to see the legitimate content,")
    print("while the hidden mesh network data can only be extracted using this system.")


if __name__ == "__main__":
    # Create examples directory if it doesn't exist
    os.makedirs("examples", exist_ok=True)
    main() 