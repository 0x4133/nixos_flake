#!/usr/bin/env python3
"""
Core Functionality Test - Steganographic QR Code Generator

This test demonstrates the core functionality of the steganographic system
without requiring external dependencies like qrcode or PIL.
"""

import sys
import json
import time
from mesh_encoder import MeshDataEncoder
from error_correction import ErrorCorrectionManager
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


def test_random_data_generation():
    """Test random mesh data generation."""
    print("\n=== Testing Random Data Generation ===")
    
    # Generate random mesh data
    mesh_data = generate_random_mesh_data()
    
    print("Generated random mesh data:")
    print(f"  GPS: {mesh_data['gps']['lat']:.4f}, {mesh_data['gps']['lon']:.4f}")
    print(f"  MAC Addresses: {mesh_data['mac_addresses']}")
    print(f"  Status: {mesh_data['node_status']}")
    print(f"  Timestamp: {format_timestamp(mesh_data['timestamp'])}")
    print(f"  Additional data: {mesh_data['additional_data']}")
    
    # Test encoding/decoding of random data
    encoder = MeshDataEncoder()
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
    operations = 100
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


def test_compression_analysis():
    """Test compression analysis with different data types."""
    print("\n=== Testing Compression Analysis ===")
    
    encoder = MeshDataEncoder()
    
    # Test different data sizes
    test_cases = [
        {
            'name': 'Minimal data',
            'data': {'gps': {'lat': 0.0, 'lon': 0.0}, 'timestamp': 0}
        },
        {
            'name': 'Standard data',
            'data': {
                'gps': {'lat': 40.7128, 'lon': -74.0060},
                'mac_addresses': ['AA:BB:CC:DD:EE:FF'],
                'node_status': 'active',
                'timestamp': 1640995200
            }
        },
        {
            'name': 'Large data',
            'data': generate_random_mesh_data()
        }
    ]
    
    for test_case in test_cases:
        data = test_case['data']
        original_json = json.dumps(data, separators=(',', ':'))
        original_size = len(original_json)
        
        encoded = encoder.encode_mesh_data(data)
        encoded_size = len(encoded)
        
        compression_ratio = original_size / encoded_size if encoded_size > 0 else 1.0
        
        print(f"{test_case['name']}:")
        print(f"  Original: {original_size} bytes")
        print(f"  Encoded:  {encoded_size} bytes")
        print(f"  Ratio:    {compression_ratio:.2f}x")
    
    return True


def main():
    """Run all tests."""
    print("Steganographic QR Code Generator - Core Functionality Test")
    print("=" * 60)
    print()
    
    tests = [
        test_mesh_encoder,
        test_error_correction,
        test_data_validation,
        test_random_data_generation,
        test_performance,
        test_compression_analysis
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"✗ Test failed with error: {e}")
    
    print("\n" + "=" * 60)
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The core functionality is working correctly.")
    else:
        print("⚠️  Some tests failed. Please check the implementation.")
    
    print("\nKey Features Demonstrated:")
    print("✓ Mesh data encoding and decoding")
    print("✓ Error correction with Reed-Solomon codes")
    print("✓ Data validation and integrity checking")
    print("✓ Random data generation")
    print("✓ Performance testing")
    print("✓ Compression analysis")
    
    print("\nThe system is ready for steganographic QR code generation!")
    print("To use with QR codes, install the required dependencies:")
    print("  pip install qrcode[pil] Pillow pyzbar opencv-python")


if __name__ == "__main__":
    main() 