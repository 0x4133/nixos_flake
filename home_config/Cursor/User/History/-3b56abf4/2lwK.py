#!/usr/bin/env python3
"""
Transport Layer Integration Example

This example demonstrates how to integrate the steganographic QR code generator
with transport layers to create a complete mesh network communication system.
"""

import sys
import os
import time
import threading
import json
from typing import Dict, Any

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from stego_qr import StegoQRGenerator
from transport_layers import LoRaTransport, BluetoothTransport, CellularTransport, TransportManager
from utils import generate_random_mesh_data, format_timestamp, PerformanceMonitor


class MeshNetworkNode:
    """
    A mesh network node that can send and receive steganographic QR codes
    through multiple transport layers.
    """
    
    def __init__(self, node_id: str, location: Dict[str, float]):
        """
        Initialize a mesh network node.
        
        Args:
            node_id: Unique identifier for this node
            location: GPS coordinates of this node
        """
        self.node_id = node_id
        self.location = location
        self.stego_generator = StegoQRGenerator()
        self.transport_manager = TransportManager()
        self.performance_monitor = PerformanceMonitor()
        self.running = False
        self.received_messages = []
        
        # Configure transport layers
        self._setup_transports()
        
        # Register message handler
        self.transport_manager.add_message_handler(self._handle_message)
    
    def _setup_transports(self):
        """Setup transport layers for this node."""
        # LoRa transport for long-range communication
        lora_config = {
            'frequency': 915000000,
            'bandwidth': 125000,
            'spreading_factor': 7,
            'network_id': 'stego_mesh_network',
            'simulation_mode': True
        }
        lora_transport = LoRaTransport(self.node_id, lora_config)
        self.transport_manager.add_transport('lora', lora_transport)
        
        # Bluetooth transport for short-range communication
        bluetooth_config = {
            'service_uuid': '12345678-1234-1234-1234-123456789abc',
            'scan_interval': 100,
            'simulation_mode': True
        }
        bluetooth_transport = BluetoothTransport(self.node_id, bluetooth_config)
        self.transport_manager.add_transport('bluetooth', bluetooth_transport)
        
        # Cellular transport for wide-area communication
        cellular_config = {
            'apn': 'internet',
            'server_url': 'https://mesh.example.com/api',
            'simulation_mode': True
        }
        cellular_transport = CellularTransport(self.node_id, cellular_config)
        self.transport_manager.add_transport('cellular', cellular_transport)
    
    def start(self):
        """Start the mesh network node."""
        print(f"[{self.node_id}] Starting mesh network node...")
        
        # Connect to all transport layers
        results = self.transport_manager.connect_all()
        for transport_name, success in results.items():
            if success:
                print(f"[{self.node_id}] Connected to {transport_name}")
            else:
                print(f"[{self.node_id}] Failed to connect to {transport_name}")
        
        self.running = True
        
        # Start message receiving thread
        self.receive_thread = threading.Thread(target=self._receive_loop)
        self.receive_thread.daemon = True
        self.receive_thread.start()
        
        print(f"[{self.node_id}] Node started successfully")
    
    def stop(self):
        """Stop the mesh network node."""
        print(f"[{self.node_id}] Stopping mesh network node...")
        self.running = False
        
        # Disconnect from all transport layers
        results = self.transport_manager.disconnect_all()
        for transport_name, success in results.items():
            if success:
                print(f"[{self.node_id}] Disconnected from {transport_name}")
        
        print(f"[{self.node_id}] Node stopped")
    
    def send_mesh_data(self, mesh_data: Dict[str, Any], destination: str = None, 
                      transport_preference: str = None) -> bool:
        """
        Send mesh data as steganographic QR code.
        
        Args:
            mesh_data: Mesh network data to send
            destination: Optional destination node ID
            transport_preference: Preferred transport layer
            
        Returns:
            True if message sent successfully
        """
        try:
            # Start performance monitoring
            self.performance_monitor.start_timer()
            
            # Generate steganographic QR code
            qr_image = self.stego_generator.encode_as_wifi_password(
                mesh_data, f"Mesh_{self.node_id}", "MeshPassword123"
            )
            
            # Convert QR code to bytes (simplified - in real implementation, 
            # you'd send the QR code image or extract the data)
            qr_data = self._qr_to_bytes(qr_image)
            
            # Send through transport layers
            results = self.transport_manager.send_message(
                qr_data, destination, transport_preference
            )
            
            # Record performance metrics
            elapsed_time = self.performance_monitor.stop_timer()
            self.performance_monitor.record_encoding_time(elapsed_time)
            self.performance_monitor.record_throughput(len(qr_data), elapsed_time)
            
            # Check if any transport succeeded
            success = any(results.values())
            
            if success:
                print(f"[{self.node_id}] Sent mesh data via {list(results.keys())}")
            else:
                print(f"[{self.node_id}] Failed to send mesh data")
            
            return success
            
        except Exception as e:
            print(f"[{self.node_id}] Error sending mesh data: {e}")
            return False
    
    def _qr_to_bytes(self, qr_image) -> bytes:
        """Convert QR code image to bytes for transmission."""
        # In a real implementation, you might:
        # 1. Extract the QR code data directly
        # 2. Compress the image
        # 3. Use a more efficient format
        
        # For this example, we'll use a simplified approach
        import io
        img_byte_arr = io.BytesIO()
        qr_image.save(img_byte_arr, format='PNG')
        return img_byte_arr.getvalue()
    
    def _handle_message(self, message: Dict[str, Any]):
        """
        Handle incoming messages from transport layers.
        
        Args:
            message: Received message with transport information
        """
        try:
            print(f"[{self.node_id}] Received message from {message.get('source', 'unknown')}")
            
            # Start performance monitoring for decoding
            self.performance_monitor.start_timer()
            
            # Convert bytes back to QR code image
            qr_image = self._bytes_to_qr(message['data'])
            
            # Decode steganographic data
            mesh_data = self.stego_generator.decode_from_qr(qr_image)
            
            # Record performance metrics
            elapsed_time = self.performance_monitor.stop_timer()
            self.performance_monitor.record_decoding_time(elapsed_time)
            
            if mesh_data:
                print(f"[{self.node_id}] Decoded mesh data:")
                print(f"  GPS: {mesh_data['gps']['lat']:.4f}, {mesh_data['gps']['lon']:.4f}")
                print(f"  Status: {mesh_data['node_status']}")
                print(f"  Timestamp: {format_timestamp(mesh_data['timestamp'])}")
                
                # Store received message
                self.received_messages.append({
                    'source': message.get('source'),
                    'transport': message.get('transport'),
                    'timestamp': time.time(),
                    'data': mesh_data
                })
            else:
                print(f"[{self.node_id}] Failed to decode mesh data")
                
        except Exception as e:
            print(f"[{self.node_id}] Error handling message: {e}")
    
    def _bytes_to_qr(self, data: bytes):
        """Convert bytes back to QR code image."""
        import io
        from PIL import Image
        return Image.open(io.BytesIO(data))
    
    def _receive_loop(self):
        """Main receive loop for handling incoming messages."""
        while self.running:
            try:
                # Receive message from any transport layer
                message = self.transport_manager.receive_message(timeout=0.1)
                if message:
                    self._handle_message(message)
            except Exception as e:
                print(f"[{self.node_id}] Error in receive loop: {e}")
    
    def get_status(self) -> Dict[str, Any]:
        """Get current node status."""
        transport_status = self.transport_manager.get_transport_status()
        
        return {
            'node_id': self.node_id,
            'location': self.location,
            'running': self.running,
            'transports': transport_status,
            'messages_received': len(self.received_messages),
            'performance': self.performance_monitor.get_average_metrics()
        }
    
    def generate_status_report(self) -> str:
        """Generate a status report for this node."""
        status = self.get_status()
        
        report = f"=== Mesh Network Node Status Report ===\n"
        report += f"Node ID: {status['node_id']}\n"
        report += f"Location: {status['location']['lat']:.4f}, {status['location']['lon']:.4f}\n"
        report += f"Status: {'Running' if status['running'] else 'Stopped'}\n"
        report += f"Messages Received: {status['messages_received']}\n\n"
        
        report += f"Transport Status:\n"
        for transport_name, transport_status in status['transports'].items():
            report += f"  {transport_name}: {'Connected' if transport_status['connected'] else 'Disconnected'}\n"
        
        report += f"\nPerformance Metrics:\n"
        for metric_name, value in status['performance'].items():
            if 'time' in metric_name:
                report += f"  {metric_name}: {value:.4f} seconds\n"
            elif 'ratio' in metric_name:
                report += f"  {metric_name}: {value:.2f}x\n"
            else:
                report += f"  {metric_name}: {value:.2f}\n"
        
        return report


def simulate_mesh_network():
    """Simulate a mesh network with multiple nodes."""
    print("=== Mesh Network Simulation ===\n")
    
    # Create mesh network nodes
    nodes = {
        'node_001': MeshNetworkNode('node_001', {'lat': 40.7128, 'lon': -74.0060}),  # NYC
        'node_002': MeshNetworkNode('node_002', {'lat': 34.0522, 'lon': -118.2437}), # LA
        'node_003': MeshNetworkNode('node_003', {'lat': 41.8781, 'lon': -87.6298}),  # Chicago
    }
    
    # Start all nodes
    print("Starting mesh network nodes...")
    for node_id, node in nodes.items():
        node.start()
        time.sleep(0.5)  # Small delay between starts
    
    print("\nMesh network started. Simulating communication...\n")
    
    # Simulate network communication
    try:
        for i in range(5):
            print(f"\n--- Round {i+1} ---")
            
            # Each node sends its status
            for node_id, node in nodes.items():
                # Generate current mesh data
                mesh_data = generate_random_mesh_data()
                mesh_data['gps'] = node.location  # Use actual node location
                mesh_data['node_id'] = node_id
                
                # Send to other nodes
                for target_id in nodes.keys():
                    if target_id != node_id:
                        success = node.send_mesh_data(mesh_data, target_id)
                        if success:
                            print(f"{node_id} -> {target_id}: Status sent")
            
            time.sleep(2)  # Wait between rounds
        
        # Generate final reports
        print("\n=== Final Status Reports ===")
        for node_id, node in nodes.items():
            print(f"\n{node_id} Report:")
            print(node.generate_status_report())
        
        # Performance summary
        print("\n=== Performance Summary ===")
        for node_id, node in nodes.items():
            print(f"\n{node_id} Performance:")
            print(node.performance_monitor.generate_report())
    
    except KeyboardInterrupt:
        print("\nSimulation interrupted by user")
    
    finally:
        # Stop all nodes
        print("\nStopping mesh network nodes...")
        for node_id, node in nodes.items():
            node.stop()


def main():
    """Main function to run the transport integration example."""
    print("Steganographic QR Code Transport Integration Example")
    print("=" * 60)
    print()
    print("This example demonstrates:")
    print("1. Integration of steganographic QR codes with transport layers")
    print("2. Multi-transport mesh network communication")
    print("3. Performance monitoring and reporting")
    print("4. Real-time data transmission and reception")
    print()
    
    # Run the simulation
    simulate_mesh_network()
    
    print("\nExample completed successfully!")
    print("\nKey features demonstrated:")
    print("- Steganographic QR code generation and decoding")
    print("- Multi-transport layer communication (LoRa, Bluetooth, Cellular)")
    print("- Mesh network node coordination")
    print("- Performance monitoring and optimization")
    print("- Error handling and resilience")


if __name__ == "__main__":
    main() 