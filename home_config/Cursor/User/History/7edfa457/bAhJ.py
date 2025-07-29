#!/usr/bin/env python3
"""
Test Suite for Steganographic QR Code Generator

Comprehensive test cases for all components of the steganographic QR code system.
"""

import sys
import os
import unittest
import tempfile
import json
import time
from PIL import Image

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from stego_qr import StegoQRGenerator
from mesh_encoder import MeshDataEncoder
from error_correction import ErrorCorrectionManager, ReedSolomonEncoder
from transport_layers import LoRaTransport, BluetoothTransport, CellularTransport, TransportManager
from utils import MeshDataValidator, DataCompressor, SecurityUtils, PerformanceMonitor, generate_random_mesh_data


class TestMeshDataEncoder(unittest.TestCase):
    """Test cases for mesh data encoding and decoding."""
    
    def setUp(self):
        self.encoder = MeshDataEncoder()
        
        self.sample_data = {
            'gps': {'lat': 40.7128, 'lon': -74.0060},
            'mac_addresses': ['AA:BB:CC:DD:EE:FF', '11:22:33:44:55:66'],
            'node_status': 'active',
            'timestamp': 1640995200,
            'additional_data': {
                'battery_level': 85,
                'signal_strength': -45
            }
        }
    
    def test_encode_decode_roundtrip(self):
        """Test that encoding and decoding preserves data integrity."""
        encoded = self.encoder.encode_mesh_data(self.sample_data)
        decoded = self.encoder.decode_mesh_data(encoded)
        
        self.assertEqual(decoded, self.sample_data)
    
    def test_gps_encoding(self):
        """Test GPS coordinate encoding accuracy."""
        gps_data = {'gps': {'lat': 40.7128, 'lon': -74.0060}}
        encoded = self.encoder.encode_mesh_data(gps_data)
        decoded = self.encoder.decode_mesh_data(encoded)
        
        self.assertAlmostEqual(decoded['gps']['lat'], gps_data['gps']['lat'], places=6)
        self.assertAlmostEqual(decoded['gps']['lon'], gps_data['gps']['lon'], places=6)
    
    def test_mac_address_encoding(self):
        """Test MAC address encoding and decoding."""
        mac_data = {'mac_addresses': ['AA:BB:CC:DD:EE:FF', '11:22:33:44:55:66']}
        encoded = self.encoder.encode_mesh_data(mac_data)
        decoded = self.encoder.decode_mesh_data(encoded)
        
        self.assertEqual(decoded['mac_addresses'], mac_data['mac_addresses'])
    
    def test_node_status_encoding(self):
        """Test node status encoding with Huffman codes."""
        statuses = ['active', 'inactive', 'error', 'maintenance', 'offline']
        
        for status in statuses:
            status_data = {'node_status': status}
            encoded = self.encoder.encode_mesh_data(status_data)
            decoded = self.encoder.decode_mesh_data(encoded)
            
            self.assertEqual(decoded['node_status'], status)
    
    def test_timestamp_encoding(self):
        """Test timestamp encoding with relative encoding."""
        timestamp_data = {'timestamp': 1640995200}
        encoded = self.encoder.encode_mesh_data(timestamp_data)
        decoded = self.encoder.decode_mesh_data(encoded)
        
        self.assertEqual(decoded['timestamp'], timestamp_data['timestamp'])
    
    def test_compression_ratio(self):
        """Test that encoding provides compression."""
        ratio = self.encoder.get_compression_ratio(self.sample_data)
        self.assertGreater(ratio, 1.0)  # Should compress data
    
    def test_checksum_validation(self):
        """Test checksum validation for error detection."""
        encoded = self.encoder.encode_mesh_data(self.sample_data)
        
        # Corrupt the encoded data
        corrupted = encoded[:-8] + "INVALID"
        
        with self.assertRaises(ValueError):
            self.encoder.decode_mesh_data(corrupted)


class TestErrorCorrection(unittest.TestCase):
    """Test cases for error correction functionality."""
    
    def setUp(self):
        self.rs_encoder = ReedSolomonEncoder()
        self.ec_manager = ErrorCorrectionManager()
    
    def test_rs_encode_decode_roundtrip(self):
        """Test Reed-Solomon encoding and decoding."""
        test_data = b"Hello, World! This is a test message for error correction."
        encoded = self.rs_encoder.encode(test_data)
        decoded, success = self.rs_encoder.decode(encoded)
        
        self.assertTrue(success)
        self.assertEqual(decoded, test_data)
    
    def test_error_correction_capability(self):
        """Test that errors can be corrected."""
        test_data = b"Test message"
        encoded = self.rs_encoder.encode(test_data)
        
        # Introduce errors (up to t errors should be correctable)
        encoded_list = list(encoded)
        for i in range(min(3, self.rs_encoder.t)):  # Introduce up to t errors
            encoded_list[i] ^= 0xFF
        
        corrupted = bytes(encoded_list)
        decoded, success = self.rs_encoder.decode(corrupted)
        
        self.assertTrue(success)
        self.assertEqual(decoded, test_data)
    
    def test_manager_chunking(self):
        """Test error correction manager with large data."""
        large_data = b"X" * 1000  # 1000 bytes
        encoded = self.ec_manager.encode_with_error_correction(large_data)
        decoded, success = self.ec_manager.decode_with_error_correction(encoded)
        
        self.assertTrue(success)
        self.assertEqual(decoded, large_data)
    
    def test_error_correction_capability_info(self):
        """Test error correction capability reporting."""
        capability = self.ec_manager.get_error_correction_capability()
        self.assertGreater(capability, 0)
    
    def test_encoded_size_calculation(self):
        """Test encoded size calculation."""
        original_size = 100
        encoded_size = self.ec_manager.get_encoded_size(original_size)
        self.assertGreater(encoded_size, original_size)


class TestStegoQRGenerator(unittest.TestCase):
    """Test cases for steganographic QR code generation."""
    
    def setUp(self):
        self.generator = StegoQRGenerator()
        
        self.mesh_data = {
            'gps': {'lat': 40.7128, 'lon': -74.0060},
            'mac_addresses': ['AA:BB:CC:DD:EE:FF'],
            'node_status': 'active',
            'timestamp': 1640995200
        }
    
    def test_wifi_qr_generation(self):
        """Test WiFi QR code generation and decoding."""
        qr_image = self.generator.encode_as_wifi_password(
            self.mesh_data, "TestWiFi", "TestPassword123"
        )
        
        # Verify QR code was generated
        self.assertIsInstance(qr_image, Image.Image)
        
        # Test decoding
        decoded_data = self.generator.decode_from_qr(qr_image)
        self.assertIsNotNone(decoded_data)
        self.assertEqual(decoded_data, self.mesh_data)
    
    def test_contact_qr_generation(self):
        """Test contact QR code generation and decoding."""
        qr_image = self.generator.encode_as_contact(
            self.mesh_data, "John Doe", "+1-555-123-4567", "john@example.com"
        )
        
        self.assertIsInstance(qr_image, Image.Image)
        
        decoded_data = self.generator.decode_from_qr(qr_image)
        self.assertIsNotNone(decoded_data)
        self.assertEqual(decoded_data, self.mesh_data)
    
    def test_url_qr_generation(self):
        """Test URL QR code generation and decoding."""
        qr_image = self.generator.encode_as_url(
            self.mesh_data, "https://example.com/api"
        )
        
        self.assertIsInstance(qr_image, Image.Image)
        
        decoded_data = self.generator.decode_from_qr(qr_image)
        self.assertIsNotNone(decoded_data)
        self.assertEqual(decoded_data, self.mesh_data)
    
    def test_text_qr_generation(self):
        """Test text QR code generation and decoding."""
        qr_image = self.generator.encode_as_text(
            self.mesh_data, "This is a sample text message."
        )
        
        self.assertIsInstance(qr_image, Image.Image)
        
        decoded_data = self.generator.decode_from_qr(qr_image)
        self.assertIsNotNone(decoded_data)
        self.assertEqual(decoded_data, self.mesh_data)
    
    def test_compression_stats(self):
        """Test compression statistics calculation."""
        stats = self.generator.get_compression_stats(self.mesh_data)
        
        self.assertIn('original_size', stats)
        self.assertIn('mesh_compression_ratio', stats)
        self.assertIn('error_correction_expansion', stats)
        self.assertIn('overall_compression_ratio', stats)
        
        self.assertGreater(stats['original_size'], 0)
        self.assertGreater(stats['mesh_compression_ratio'], 1.0)
    
    def test_qr_code_save_load(self):
        """Test saving and loading QR codes from files."""
        qr_image = self.generator.encode_as_wifi_password(
            self.mesh_data, "TestWiFi", "TestPassword123"
        )
        
        # Save to temporary file
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
            qr_image.save(tmp_file.name)
            tmp_filename = tmp_file.name
        
        try:
            # Load and decode
            decoded_data = self.generator.decode_from_qr(tmp_filename)
            self.assertIsNotNone(decoded_data)
            self.assertEqual(decoded_data, self.mesh_data)
        finally:
            # Clean up
            os.unlink(tmp_filename)


class TestTransportLayers(unittest.TestCase):
    """Test cases for transport layer implementations."""
    
    def setUp(self):
        self.lora_config = {
            'frequency': 915000000,
            'bandwidth': 125000,
            'spreading_factor': 7,
            'simulation_mode': True
        }
        
        self.bluetooth_config = {
            'service_uuid': '12345678-1234-1234-1234-123456789abc',
            'simulation_mode': True
        }
        
        self.cellular_config = {
            'apn': 'internet',
            'server_url': 'https://mesh.example.com/api',
            'simulation_mode': True
        }
    
    def test_lora_transport(self):
        """Test LoRa transport layer functionality."""
        lora = LoRaTransport("node_001", self.lora_config)
        
        # Test connection
        self.assertTrue(lora.connect())
        self.assertTrue(lora.is_connected)
        
        # Test message sending
        test_message = b"Hello LoRa!"
        self.assertTrue(lora.send_message(test_message))
        
        # Test message receiving
        received = lora.receive_message(timeout=1.0)
        self.assertIsNotNone(received)
        self.assertEqual(received['data'], test_message)
        
        # Test disconnection
        self.assertTrue(lora.disconnect())
        self.assertFalse(lora.is_connected)
    
    def test_bluetooth_transport(self):
        """Test Bluetooth transport layer functionality."""
        bluetooth = BluetoothTransport("node_002", self.bluetooth_config)
        
        self.assertTrue(bluetooth.connect())
        self.assertTrue(bluetooth.is_connected)
        
        test_message = b"Hello Bluetooth!"
        self.assertTrue(bluetooth.send_message(test_message))
        
        received = bluetooth.receive_message(timeout=1.0)
        self.assertIsNotNone(received)
        self.assertEqual(received['data'], test_message)
        
        self.assertTrue(bluetooth.disconnect())
    
    def test_cellular_transport(self):
        """Test cellular transport layer functionality."""
        cellular = CellularTransport("node_003", self.cellular_config)
        
        self.assertTrue(cellular.connect())
        self.assertTrue(cellular.is_connected)
        
        test_message = b"Hello Cellular!"
        self.assertTrue(cellular.send_message(test_message))
        
        received = cellular.receive_message(timeout=1.0)
        self.assertIsNotNone(received)
        self.assertEqual(received['data'], test_message)
        
        self.assertTrue(cellular.disconnect())
    
    def test_transport_manager(self):
        """Test transport manager functionality."""
        manager = TransportManager()
        
        # Add transports
        lora = LoRaTransport("node_001", self.lora_config)
        bluetooth = BluetoothTransport("node_002", self.bluetooth_config)
        
        manager.add_transport("lora", lora)
        manager.add_transport("bluetooth", bluetooth)
        
        # Connect all
        results = manager.connect_all()
        self.assertTrue(results["lora"])
        self.assertTrue(results["bluetooth"])
        
        # Send message
        test_message = b"Hello from manager!"
        results = manager.send_message(test_message)
        self.assertTrue(results["lora"])
        self.assertTrue(results["bluetooth"])
        
        # Receive message
        received = manager.receive_message(timeout=1.0)
        self.assertIsNotNone(received)
        self.assertEqual(received['data'], test_message)
        
        # Disconnect all
        results = manager.disconnect_all()
        self.assertTrue(results["lora"])
        self.assertTrue(results["bluetooth"])


class TestUtils(unittest.TestCase):
    """Test cases for utility functions."""
    
    def setUp(self):
        self.validator = MeshDataValidator()
        self.compressor = DataCompressor()
        self.security = SecurityUtils()
        self.monitor = PerformanceMonitor()
    
    def test_mesh_data_validation(self):
        """Test mesh data validation."""
        valid_data = {
            'gps': {'lat': 40.7128, 'lon': -74.0060},
            'timestamp': 1640995200
        }
        
        is_valid, errors = self.validator.validate_mesh_data(valid_data)
        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)
        
        # Test invalid data
        invalid_data = {
            'gps': {'lat': 200.0, 'lon': -74.0060},  # Invalid latitude
            'timestamp': -1  # Invalid timestamp
        }
        
        is_valid, errors = self.validator.validate_mesh_data(invalid_data)
        self.assertFalse(is_valid)
        self.assertGreater(len(errors), 0)
    
    def test_data_compression(self):
        """Test data compression and decompression."""
        test_data = b"This is a test message that should be compressed. " * 100
        
        # Test gzip compression
        compressed = self.compressor.compress_data(test_data, 'gzip')
        decompressed = self.compressor.decompress_data(compressed, 'gzip')
        self.assertEqual(decompressed, test_data)
        
        # Test custom compression
        compressed = self.compressor.compress_data(test_data, 'custom')
        decompressed = self.compressor.decompress_data(compressed, 'custom')
        self.assertEqual(decompressed, test_data)
    
    def test_security_utils(self):
        """Test security utilities."""
        test_data = b"Sensitive mesh network data"
        
        # Test encryption/decryption
        encrypted = self.security.encrypt_data(test_data)
        decrypted = self.security.decrypt_data(encrypted)
        self.assertEqual(decrypted, test_data)
        
        # Test checksum
        checksum = self.security.calculate_checksum(test_data)
        self.assertTrue(self.security.verify_checksum(test_data, checksum))
        
        # Test invalid checksum
        self.assertFalse(self.security.verify_checksum(test_data, "invalid"))
    
    def test_performance_monitor(self):
        """Test performance monitoring."""
        self.monitor.start_timer()
        time.sleep(0.1)  # Simulate work
        elapsed = self.monitor.stop_timer()
        
        self.assertGreater(elapsed, 0.09)  # Should be around 0.1 seconds
        
        # Record metrics
        self.monitor.record_encoding_time(0.5)
        self.monitor.record_compression_ratio(1000, 500)
        
        # Get averages
        averages = self.monitor.get_average_metrics()
        self.assertIn('avg_encoding_times', averages)
        self.assertIn('avg_compression_ratios', averages)
    
    def test_random_mesh_data_generation(self):
        """Test random mesh data generation."""
        mesh_data = generate_random_mesh_data()
        
        # Verify structure
        self.assertIn('gps', mesh_data)
        self.assertIn('timestamp', mesh_data)
        self.assertIn('mac_addresses', mesh_data)
        self.assertIn('node_status', mesh_data)
        
        # Verify GPS coordinates
        self.assertGreaterEqual(mesh_data['gps']['lat'], -90)
        self.assertLessEqual(mesh_data['gps']['lat'], 90)
        self.assertGreaterEqual(mesh_data['gps']['lon'], -180)
        self.assertLessEqual(mesh_data['gps']['lon'], 180)


class TestIntegration(unittest.TestCase):
    """Integration tests for the complete system."""
    
    def setUp(self):
        self.generator = StegoQRGenerator()
        self.mesh_data = generate_random_mesh_data()
    
    def test_complete_workflow(self):
        """Test complete workflow from data to QR code and back."""
        # Generate QR code
        qr_image = self.generator.encode_as_wifi_password(
            self.mesh_data, "TestNetwork", "TestPassword"
        )
        
        # Decode QR code
        decoded_data = self.generator.decode_from_qr(qr_image)
        
        # Verify data integrity
        self.assertIsNotNone(decoded_data)
        self.assertEqual(decoded_data, self.mesh_data)
    
    def test_multiple_formats(self):
        """Test that data can be encoded in multiple formats."""
        formats = [
            lambda: self.generator.encode_as_wifi_password(self.mesh_data, "WiFi", "Pass"),
            lambda: self.generator.encode_as_contact(self.mesh_data, "Name", "Phone", "Email"),
            lambda: self.generator.encode_as_url(self.mesh_data, "https://example.com"),
            lambda: self.generator.encode_as_text(self.mesh_data, "Sample text")
        ]
        
        for i, format_func in enumerate(formats):
            qr_image = format_func()
            decoded_data = self.generator.decode_from_qr(qr_image)
            
            self.assertIsNotNone(decoded_data, f"Format {i+1} failed")
            self.assertEqual(decoded_data, self.mesh_data, f"Format {i+1} data mismatch")
    
    def test_error_resilience(self):
        """Test system resilience to various error conditions."""
        # Test with minimal data
        minimal_data = {'gps': {'lat': 0.0, 'lon': 0.0}, 'timestamp': 0}
        qr_image = self.generator.encode_as_wifi_password(minimal_data, "Test", "Pass")
        decoded_data = self.generator.decode_from_qr(qr_image)
        
        self.assertIsNotNone(decoded_data)
        self.assertEqual(decoded_data, minimal_data)
        
        # Test with large data
        large_data = self.mesh_data.copy()
        large_data['additional_data'] = {'large_field': 'X' * 1000}
        
        qr_image = self.generator.encode_as_wifi_password(large_data, "Test", "Pass")
        decoded_data = self.generator.decode_from_qr(qr_image)
        
        self.assertIsNotNone(decoded_data)
        self.assertEqual(decoded_data, large_data)


if __name__ == '__main__':
    # Create tests directory if it doesn't exist
    os.makedirs("tests", exist_ok=True)
    
    # Run tests
    unittest.main(verbosity=2) 