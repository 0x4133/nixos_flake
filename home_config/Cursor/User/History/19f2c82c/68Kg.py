"""
Transport Layers Module - Multi-Protocol Support

This module provides transport layer abstractions for different communication protocols
used in the steganographic mesh network system.
"""

import json
import base64
import hashlib
from typing import Dict, List, Any, Optional, Callable
from abc import ABC, abstractmethod
import time
import random


class TransportLayer(ABC):
    """
    Abstract base class for transport layer implementations.
    
    Defines the interface that all transport layers must implement
    for the steganographic mesh network system.
    """
    
    def __init__(self, node_id: str, config: Dict[str, Any]):
        """
        Initialize transport layer.
        
        Args:
            node_id: Unique identifier for this node
            config: Configuration dictionary for the transport layer
        """
        self.node_id = node_id
        self.config = config
        self.is_connected = False
        self.message_handlers: List[Callable] = []
    
    @abstractmethod
    def connect(self) -> bool:
        """
        Establish connection to the transport medium.
        
        Returns:
            True if connection successful, False otherwise
        """
        pass
    
    @abstractmethod
    def disconnect(self) -> bool:
        """
        Disconnect from the transport medium.
        
        Returns:
            True if disconnection successful, False otherwise
        """
        pass
    
    @abstractmethod
    def send_message(self, message: bytes, destination: Optional[str] = None) -> bool:
        """
        Send a message through the transport layer.
        
        Args:
            message: Message data to send
            destination: Optional destination identifier
            
        Returns:
            True if message sent successfully, False otherwise
        """
        pass
    
    @abstractmethod
    def receive_message(self, timeout: float = 1.0) -> Optional[Dict[str, Any]]:
        """
        Receive a message from the transport layer.
        
        Args:
            timeout: Timeout in seconds for receiving
            
        Returns:
            Message dictionary or None if timeout
        """
        pass
    
    def add_message_handler(self, handler: Callable):
        """Add a message handler callback."""
        self.message_handlers.append(handler)
    
    def remove_message_handler(self, handler: Callable):
        """Remove a message handler callback."""
        if handler in self.message_handlers:
            self.message_handlers.remove(handler)
    
    def _notify_handlers(self, message: Dict[str, Any]):
        """Notify all registered message handlers."""
        for handler in self.message_handlers:
            try:
                handler(message)
            except Exception as e:
                print(f"Error in message handler: {e}")


class LoRaTransport(TransportLayer):
    """
    LoRa (Long Range) transport layer implementation.
    
    Simulates LoRa communication for long-range, low-power mesh networking.
    """
    
    def __init__(self, node_id: str, config: Dict[str, Any]):
        super().__init__(node_id, config)
        self.frequency = config.get('frequency', 915000000)  # 915 MHz
        self.bandwidth = config.get('bandwidth', 125000)     # 125 kHz
        self.spreading_factor = config.get('spreading_factor', 7)
        self.tx_power = config.get('tx_power', 14)          # dBm
        self.network_id = config.get('network_id', 'mesh_network')
        self.message_queue = []
        self.simulation_mode = config.get('simulation_mode', True)
    
    def connect(self) -> bool:
        """Establish LoRa connection."""
        if self.simulation_mode:
            print(f"[LoRa] Node {self.node_id} connecting to network {self.network_id}")
            self.is_connected = True
            return True
        else:
            # Real LoRa implementation would go here
            # This would interface with actual LoRa hardware
            try:
                # Initialize LoRa hardware
                # Configure frequency, bandwidth, spreading factor
                self.is_connected = True
                return True
            except Exception as e:
                print(f"LoRa connection failed: {e}")
                return False
    
    def disconnect(self) -> bool:
        """Disconnect from LoRa network."""
        if self.simulation_mode:
            print(f"[LoRa] Node {self.node_id} disconnecting from network")
            self.is_connected = False
            return True
        else:
            # Real LoRa disconnection
            try:
                self.is_connected = False
                return True
            except Exception as e:
                print(f"LoRa disconnection failed: {e}")
                return False
    
    def send_message(self, message: bytes, destination: Optional[str] = None) -> bool:
        """Send message via LoRa."""
        if not self.is_connected:
            return False
        
        # Create LoRa packet
        packet = {
            'source': self.node_id,
            'destination': destination or 'broadcast',
            'network_id': self.network_id,
            'timestamp': time.time(),
            'data': base64.b64encode(message).decode(),
            'checksum': hashlib.md5(message).hexdigest()[:8]
        }
        
        if self.simulation_mode:
            # Simulate LoRa transmission
            print(f"[LoRa] Sending packet from {self.node_id} to {packet['destination']}")
            # Simulate network delay and packet loss
            if random.random() > 0.1:  # 90% success rate
                self.message_queue.append(packet)
            return True
        else:
            # Real LoRa transmission
            try:
                # Encode packet for LoRa transmission
                packet_bytes = json.dumps(packet).encode()
                # Send via LoRa hardware
                return True
            except Exception as e:
                print(f"LoRa send failed: {e}")
                return False
    
    def receive_message(self, timeout: float = 1.0) -> Optional[Dict[str, Any]]:
        """Receive message via LoRa."""
        if not self.is_connected:
            return None
        
        if self.simulation_mode:
            # Simulate LoRa reception
            if self.message_queue:
                packet = self.message_queue.pop(0)
                # Verify checksum
                received_data = base64.b64decode(packet['data'])
                expected_checksum = hashlib.md5(received_data).hexdigest()[:8]
                
                if packet['checksum'] == expected_checksum:
                    return {
                        'source': packet['source'],
                        'data': received_data,
                        'timestamp': packet['timestamp']
                    }
            return None
        else:
            # Real LoRa reception
            try:
                # Receive from LoRa hardware
                # Decode packet
                return None
            except Exception as e:
                print(f"LoRa receive failed: {e}")
                return None


class BluetoothTransport(TransportLayer):
    """
    Bluetooth transport layer implementation.
    
    Simulates Bluetooth Low Energy (BLE) communication for short-range mesh networking.
    """
    
    def __init__(self, node_id: str, config: Dict[str, Any]):
        super().__init__(node_id, config)
        self.service_uuid = config.get('service_uuid', '12345678-1234-1234-1234-123456789abc')
        self.characteristic_uuid = config.get('characteristic_uuid', '87654321-4321-4321-4321-cba987654321')
        self.scan_interval = config.get('scan_interval', 100)  # ms
        self.scan_window = config.get('scan_window', 50)       # ms
        self.connected_devices = set()
        self.simulation_mode = config.get('simulation_mode', True)
    
    def connect(self) -> bool:
        """Establish Bluetooth connection."""
        if self.simulation_mode:
            print(f"[Bluetooth] Node {self.node_id} starting BLE service")
            self.is_connected = True
            return True
        else:
            # Real Bluetooth implementation
            try:
                # Initialize BLE stack
                # Start advertising and scanning
                self.is_connected = True
                return True
            except Exception as e:
                print(f"Bluetooth connection failed: {e}")
                return False
    
    def disconnect(self) -> bool:
        """Disconnect Bluetooth."""
        if self.simulation_mode:
            print(f"[Bluetooth] Node {self.node_id} stopping BLE service")
            self.is_connected = False
            return True
        else:
            try:
                self.is_connected = False
                return True
            except Exception as e:
                print(f"Bluetooth disconnection failed: {e}")
                return False
    
    def send_message(self, message: bytes, destination: Optional[str] = None) -> bool:
        """Send message via Bluetooth."""
        if not self.is_connected:
            return False
        
        # Create BLE packet
        packet = {
            'source': self.node_id,
            'destination': destination or 'broadcast',
            'timestamp': time.time(),
            'data': base64.b64encode(message).decode(),
            'checksum': hashlib.md5(message).hexdigest()[:8]
        }
        
        if self.simulation_mode:
            print(f"[Bluetooth] Broadcasting from {self.node_id}")
            # Simulate BLE broadcast
            if random.random() > 0.05:  # 95% success rate
                self.message_queue.append(packet)
            return True
        else:
            try:
                # Send via BLE characteristic
                return True
            except Exception as e:
                print(f"Bluetooth send failed: {e}")
                return False
    
    def receive_message(self, timeout: float = 1.0) -> Optional[Dict[str, Any]]:
        """Receive message via Bluetooth."""
        if not self.is_connected:
            return None
        
        if self.simulation_mode:
            if self.message_queue:
                packet = self.message_queue.pop(0)
                # Verify checksum
                received_data = base64.b64decode(packet['data'])
                expected_checksum = hashlib.md5(received_data).hexdigest()[:8]
                
                if packet['checksum'] == expected_checksum:
                    return {
                        'source': packet['source'],
                        'data': received_data,
                        'timestamp': packet['timestamp']
                    }
            return None
        else:
            try:
                # Receive from BLE characteristic
                return None
            except Exception as e:
                print(f"Bluetooth receive failed: {e}")
                return None


class CellularTransport(TransportLayer):
    """
    Cellular transport layer implementation.
    
    Simulates cellular network communication for wide-area mesh networking.
    """
    
    def __init__(self, node_id: str, config: Dict[str, Any]):
        super().__init__(node_id, config)
        self.apn = config.get('apn', 'internet')
        self.username = config.get('username', '')
        self.password = config.get('password', '')
        self.server_url = config.get('server_url', 'https://mesh.example.com/api')
        self.simulation_mode = config.get('simulation_mode', True)
    
    def connect(self) -> bool:
        """Establish cellular connection."""
        if self.simulation_mode:
            print(f"[Cellular] Node {self.node_id} connecting to cellular network")
            self.is_connected = True
            return True
        else:
            try:
                # Initialize cellular modem
                # Configure APN and authentication
                self.is_connected = True
                return True
            except Exception as e:
                print(f"Cellular connection failed: {e}")
                return False
    
    def disconnect(self) -> bool:
        """Disconnect cellular connection."""
        if self.simulation_mode:
            print(f"[Cellular] Node {self.node_id} disconnecting from cellular network")
            self.is_connected = False
            return True
        else:
            try:
                self.is_connected = False
                return True
            except Exception as e:
                print(f"Cellular disconnection failed: {e}")
                return False
    
    def send_message(self, message: bytes, destination: Optional[str] = None) -> bool:
        """Send message via cellular network."""
        if not self.is_connected:
            return False
        
        # Create cellular packet
        packet = {
            'source': self.node_id,
            'destination': destination or 'server',
            'timestamp': time.time(),
            'data': base64.b64encode(message).decode(),
            'checksum': hashlib.md5(message).hexdigest()[:8]
        }
        
        if self.simulation_mode:
            print(f"[Cellular] Sending to server from {self.node_id}")
            # Simulate cellular transmission
            if random.random() > 0.02:  # 98% success rate
                self.message_queue.append(packet)
            return True
        else:
            try:
                # Send via HTTP/HTTPS to server
                return True
            except Exception as e:
                print(f"Cellular send failed: {e}")
                return False
    
    def receive_message(self, timeout: float = 1.0) -> Optional[Dict[str, Any]]:
        """Receive message via cellular network."""
        if not self.is_connected:
            return None
        
        if self.simulation_mode:
            if self.message_queue:
                packet = self.message_queue.pop(0)
                # Verify checksum
                received_data = base64.b64decode(packet['data'])
                expected_checksum = hashlib.md5(received_data).hexdigest()[:8]
                
                if packet['checksum'] == expected_checksum:
                    return {
                        'source': packet['source'],
                        'data': received_data,
                        'timestamp': packet['timestamp']
                    }
            return None
        else:
            try:
                # Receive from server via HTTP/HTTPS
                return None
            except Exception as e:
                print(f"Cellular receive failed: {e}")
                return None


class TransportManager:
    """
    High-level transport manager for coordinating multiple transport layers.
    
    Provides unified interface for sending and receiving messages across
    different transport protocols with automatic failover and load balancing.
    """
    
    def __init__(self):
        self.transports: Dict[str, TransportLayer] = {}
        self.active_transports: List[str] = []
        self.message_handlers: List[Callable] = []
    
    def add_transport(self, name: str, transport: TransportLayer):
        """Add a transport layer to the manager."""
        self.transports[name] = transport
        transport.add_message_handler(self._handle_transport_message)
    
    def remove_transport(self, name: str):
        """Remove a transport layer from the manager."""
        if name in self.transports:
            transport = self.transports[name]
            transport.remove_message_handler(self._handle_transport_message)
            transport.disconnect()
            del self.transports[name]
            if name in self.active_transports:
                self.active_transports.remove(name)
    
    def connect_all(self) -> Dict[str, bool]:
        """Connect to all transport layers."""
        results = {}
        for name, transport in self.transports.items():
            success = transport.connect()
            results[name] = success
            if success:
                self.active_transports.append(name)
        return results
    
    def disconnect_all(self) -> Dict[str, bool]:
        """Disconnect from all transport layers."""
        results = {}
        for name, transport in self.transports.items():
            success = transport.disconnect()
            results[name] = success
            if name in self.active_transports:
                self.active_transports.remove(name)
        return results
    
    def send_message(self, message: bytes, destination: Optional[str] = None, 
                    transport_preference: Optional[str] = None) -> Dict[str, bool]:
        """
        Send message through available transport layers.
        
        Args:
            message: Message data to send
            destination: Optional destination identifier
            transport_preference: Preferred transport layer name
            
        Returns:
            Dictionary mapping transport names to success status
        """
        results = {}
        
        # Try preferred transport first
        if transport_preference and transport_preference in self.active_transports:
            transport = self.transports[transport_preference]
            results[transport_preference] = transport.send_message(message, destination)
        
        # Try other active transports
        for name, transport in self.transports.items():
            if name not in results and name in self.active_transports:
                results[name] = transport.send_message(message, destination)
        
        return results
    
    def receive_message(self, timeout: float = 1.0) -> Optional[Dict[str, Any]]:
        """
        Receive message from any available transport layer.
        
        Args:
            timeout: Timeout in seconds for receiving
            
        Returns:
            Message dictionary with transport information or None if timeout
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            for name, transport in self.transports.items():
                if name in self.active_transports:
                    message = transport.receive_message(0.1)  # Short timeout per transport
                    if message:
                        message['transport'] = name
                        return message
        
        return None
    
    def add_message_handler(self, handler: Callable):
        """Add a message handler for all transports."""
        self.message_handlers.append(handler)
    
    def remove_message_handler(self, handler: Callable):
        """Remove a message handler."""
        if handler in self.message_handlers:
            self.message_handlers.remove(handler)
    
    def _handle_transport_message(self, message: Dict[str, Any]):
        """Handle messages from transport layers."""
        for handler in self.message_handlers:
            try:
                handler(message)
            except Exception as e:
                print(f"Error in transport message handler: {e}")
    
    def get_transport_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all transport layers."""
        status = {}
        for name, transport in self.transports.items():
            status[name] = {
                'connected': transport.is_connected,
                'active': name in self.active_transports,
                'config': transport.config
            }
        return status 