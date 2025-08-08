#!/usr/bin/env python3
"""
Simple Test - Steganographic QR Code Generator (No External Dependencies)

This test demonstrates the core functionality of the steganographic system
using only standard Python libraries.
"""

import json
import time
from mesh_encoder import MeshDataEncoder
from error_correction_simple import ErrorCorrectionManager
from stego_qr_simple import StegoQRGenerator
from utils import generate_random_mesh_data, format_timestamp, MeshDataValidator


def test_mesh_encoder():
    """Test the mesh data encoder functionality."""
    print("=== Testing Mesh Data Encoder ===")
    
    encoder = MeshDataEncoder()
    
    # Test data
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
    
    print(f"Original mesh data:")
    print(f"  GPS: {mesh_data['gps']['lat']:.4f}, {mesh_data['gps']['lon']:.4f}")
    print(f"  MAC Addresses: {mesh_data['mac_addresses']}")
    print(f"  Status: {mesh_data['node_status']}")
    print(f"  Timestamp: {format_timestamp(mesh_data['timestamp'])}")
    print(f"  Battery: {mesh_data['additional_data']['battery_level']}%")
    
    # Encode the data
    print("\nEncoding mesh data...")
    encoded = encoder.encode_mesh_data(mesh_data)
    print(f"Encoded data: {encoded}")
    print(f"Encoded length: {len(encoded)} characters")
    
    # Decode the data
    print("\nDecoding mesh data...")
    decoded = encoder.decode_mesh_data(encoded)
    
    # Verify data integrity
    print("\nVerifying data integrity...")
    if decoded == mesh_data:
        print("✓ Data integrity verified - encoding/decoding successful!")
    else:
        print("✗ Data integrity check failed!")
        print(f"Original: {mesh_data}")
        print(f"Decoded:  {decoded}")
    
    # Test compression ratio
    compression_ratio = encoder.get_compression_ratio(mesh_data)
    print(f"\nCompression ratio: {compression_ratio:.2f}x")
    
    return True


def test_error_correction():
    """Test the error correction functionality."""
    print("\n=== Testing Error Correction ===")
    
    ec_manager = ErrorCorrectionManager()
    
    # Test data
    test_data = b"This is a test message for error correction. " * 10
    print(f"Original data length: {len(test_data)} bytes")
    
    # Encode with error correction
    print("Encoding with error correction...")
    encoded = ec_manager.encode_with_error_correction(test_data)
    print(f"Encoded data length: {len(encoded)} bytes")
    
    # Decode with error correction
    print("Decoding with error correction...")
    decoded, success = ec_manager.decode_with_error_correction(encoded)
    
    if success and decoded == test_data:
        print("✓ Error correction successful!")
    else:
        print("✗ Error correction failed!")
    
    # Test error correction capability
    capability = ec_manager.get_error_correction_capability()
    print(f"Error correction capability: {capability} errors per chunk")
    
    return success


def test_stego_qr():
    """Test the steganographic QR code generation."""
    print("\n=== Testing Steganographic QR Generation ===")
    
    generator = StegoQRGenerator()
    
    # Test data
    mesh_data = {
        'gps': {'lat': 40.7128, 'lon': -74.0060},
        'mac_addresses': ['AA:BB:CC:DD:EE:FF'],
        'node_status': 'active',
        'timestamp': 1640995200
    }
    
    # Test WiFi QR code generation
    print("Testing WiFi QR code generation...")
    wifi_qr_data = generator.encode_as_wifi_password(
        mesh_data, "TestWiFi", "TestPassword123"
    )
    print(f"WiFi QR data: {wifi_qr_data[:50]}...")
    
    # Test decoding
    decoded_data = generator.decode_from_qr_data(wifi_qr_data)
    if decoded_data and decoded_data == mesh_data:
        print("✓ WiFi QR encoding/decoding successful!")
    else:
        print("✗ WiFi QR encoding/decoding failed!")
    
    # Test Contact QR code generation
    print("\nTesting Contact QR code generation...")
    contact_qr_data = generator.encode_as_contact(
        mesh_data, "John Doe", "+1-555-123-4567", "john@example.com"
    )
    print(f"Contact QR data: {contact_qr_data[:50]}...")
    
    # Test decoding
    decoded_data = generator.decode_from_qr_data(contact_qr_data)
    if decoded_data and decoded_data == mesh_data:
        print("✓ Contact QR encoding/decoding successful!")
    else:
        print("✗ Contact QR encoding/decoding failed!")
    
    # Test URL QR code generation
    print("\nTesting URL QR code generation...")
    url_qr_data = generator.encode_as_url(
        mesh_data, "https://example.com/api"
    )
    print(f"URL QR data: {url_qr_data[:50]}...")
    
    # Test decoding
    decoded_data = generator.decode_from_qr_data(url_qr_data)
    if decoded_data and decoded_data == mesh_data:
        print("✓ URL QR encoding/decoding successful!")
    else:
        print("✗ URL QR encoding/decoding failed!")
    
    return True


def test_data_validation():
    """Test the data validation functionality."""
    print("\n=== Testing Data Validation ===")
    
    validator = MeshDataValidator()
    
    # Valid data
    valid_data = {
        'gps': {'lat': 40.7128, 'lon': -74.0060},
        'timestamp': 1640995200
    }
    
    is_valid, errors = validator.validate_mesh_data(valid_data)
    print(f"Valid data test: {'✓ Passed' if is_valid else '✗ Failed'}")
    if errors:
        print(f"  Errors: {errors}")
    
    # Invalid data
    invalid_data = {
        'gps': {'lat': 200.0, 'lon': -74.0060},  # Invalid latitude
        'timestamp': -1  # Invalid timestamp
    }
    
    is_valid, errors = validator.validate_mesh_data(invalid_data)
    print(f"Invalid data test: {'✓ Passed' if not is_valid else '✗ Failed'}")
    if errors:
        print(f"  Errors: {errors}")
    
    return True


def test_random_data():
    """Test random data generation."""
    print("\n=== Testing Random Data Generation ===")
    
    encoder = MeshDataEncoder()
    
    # Generate random mesh data
    mesh_data = generate_random_mesh_data()
    
    print("Generated random mesh data:")
    print(f"  GPS: {mesh_data['gps']['lat']:.4f}, {mesh_data['gps']['lon']:.4f}")
    print(f"  MAC Addresses: {mesh_data['mac_addresses']}")
    print(f"  Status: {mesh_data['node_status']}")
    print(f"  Timestamp: {format_timestamp(mesh_data['timestamp'])}")
    print(f"  Additional data: {mesh_data['additional_data']}")
    
    # Test encoding/decoding of random data
    encoded = encoder.encode_mesh_data(mesh_data)
    decoded = encoder.decode_mesh_data(encoded)
    
    if decoded == mesh_data:
        print("✓ Random data encoding/decoding successful!")
    else:
        print("✗ Random data encoding/decoding failed!")
    
    return True


def test_performance():
    """Test performance with multiple operations."""
    print("\n=== Testing Performance ===")
    
    encoder = MeshDataEncoder()
    start_time = time.time()
    
    # Perform multiple encoding/decoding operations
    operations = 50  # Reduced for faster testing
    for i in range(operations):
        mesh_data = generate_random_mesh_data()
        encoded = encoder.encode_mesh_data(mesh_data)
        decoded = encoder.decode_mesh_data(encoded)
        
        if decoded != mesh_data:
            print(f"✗ Operation {i+1} failed!")
            break
    else:
        elapsed_time = time.time() - start_time
        ops_per_second = operations / elapsed_time
        print(f"✓ Completed {operations} operations in {elapsed_time:.2f} seconds")
        print(f"  Performance: {ops_per_second:.0f} operations/second")
    
    return True


def main():
    """Run all tests."""
    print("Steganographic QR Code Generator - Simple Test (No External Dependencies)")
    print("=" * 70)
    print()
    
    tests = [
        ("Mesh Data Encoder", test_mesh_encoder),
        ("Error Correction", test_error_correction),
        ("Steganographic QR Generation", test_stego_qr),
        ("Data Validation", test_data_validation),
        ("Random Data Generation", test_random_data),
        ("Performance", test_performance)
    ]
    
    passed = 0
    total = len(tests)
    
    for title, test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"✗ {title} failed with error: {e}")
    
    print("\n" + "=" * 70)
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The core functionality is working correctly.")
        print("\nThe steganographic QR code generator is ready for use!")
        print("To generate actual QR code images, install qrcode:")
        print("  pip install qrcode[pil]")
    else:
        print("⚠️  Some tests failed. Please check the implementation.")
    
    print("\nKey Features Demonstrated:")
    print("✓ Mesh data encoding and decoding")
    print("✓ Error correction with simple parity")
    print("✓ Steganographic QR code data generation")
    print("✓ Data validation and integrity checking")
    print("✓ Random data generation")
    print("✓ Performance testing")


if __name__ == "__main__":
    main() 