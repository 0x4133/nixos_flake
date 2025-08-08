"""
Error Correction Module - Reed-Solomon Encoding

This module provides error correction capabilities for the steganographic QR code system
using Reed-Solomon encoding to ensure reliable data transmission.
"""

import numpy as np
from typing import Tuple, List, Optional
import math


class ReedSolomonEncoder:
    """
    Reed-Solomon error correction encoder/decoder for steganographic data.
    
    Implements a simplified Reed-Solomon code that can correct up to t errors
    and detect up to 2t errors in a codeword of length n.
    """
    
    def __init__(self, n: int = 255, k: int = 223):
        """
        Initialize Reed-Solomon encoder.
        
        Args:
            n: Codeword length (must be 2^m - 1 for some m)
            k: Message length (n - 2t where t is error correction capability)
        """
        self.n = n
        self.k = k
        self.t = (n - k) // 2  # Error correction capability
        
        # Generate Galois field GF(2^8)
        self.gf_size = 256
        self.primitive_poly = 0x11d  # x^8 + x^4 + x^3 + x^2 + 1
        
        # Generate Galois field tables
        self.gf_exp = [0] * self.gf_size
        self.gf_log = [0] * self.gf_size
        
        self._generate_gf_tables()
        
        # Generate generator polynomial
        self.generator_poly = self._generate_generator_poly()
    
    def _generate_gf_tables(self):
        """Generate Galois field exponential and logarithm tables."""
        x = 1
        for i in range(self.gf_size):
            self.gf_exp[i] = x
            self.gf_log[x] = i
            x <<= 1
            if x & self.gf_size:
                x ^= self.primitive_poly
    
    def _gf_mult(self, a: int, b: int) -> int:
        """Multiply two elements in Galois field."""
        if a == 0 or b == 0:
            return 0
        return self.gf_exp[(self.gf_log[a] + self.gf_log[b]) % (self.gf_size - 1)]
    
    def _gf_div(self, a: int, b: int) -> int:
        """Divide two elements in Galois field."""
        if a == 0:
            return 0
        if b == 0:
            raise ValueError("Division by zero in Galois field")
        return self.gf_exp[(self.gf_log[a] - self.gf_log[b]) % (self.gf_size - 1)]
    
    def _generate_generator_poly(self) -> List[int]:
        """Generate the generator polynomial for Reed-Solomon encoding."""
        gen_poly = [1]
        for i in range(2 * self.t):
            # Multiply by (x - α^i)
            alpha_i = self.gf_exp[i]
            new_poly = [0] * (len(gen_poly) + 1)
            
            for j in range(len(gen_poly)):
                new_poly[j] ^= gen_poly[j]
                new_poly[j + 1] ^= self._gf_mult(gen_poly[j], alpha_i)
            
            gen_poly = new_poly
        
        return gen_poly
    
    def encode(self, message: bytes) -> bytes:
        """
        Encode a message using Reed-Solomon encoding.
        
        Args:
            message: Input message bytes
            
        Returns:
            Encoded codeword with error correction symbols
        """
        if len(message) > self.k:
            raise ValueError(f"Message too long. Maximum length is {self.k} bytes.")
        
        # Pad message to k bytes
        padded_message = list(message) + [0] * (self.k - len(message))
        
        # Polynomial division to compute remainder
        remainder = self._polynomial_division(padded_message, self.generator_poly)
        
        # Append remainder to message
        codeword = padded_message + remainder
        
        return bytes(codeword)
    
    def decode(self, codeword: bytes) -> Tuple[bytes, bool]:
        """
        Decode a codeword using Reed-Solomon decoding.
        
        Args:
            codeword: Received codeword with possible errors
            
        Returns:
            Tuple of (decoded message, success flag)
        """
        if len(codeword) != self.n:
            raise ValueError(f"Invalid codeword length. Expected {self.n} bytes.")
        
        # Convert to list for processing
        received = list(codeword)
        
        # Calculate syndromes
        syndromes = self._calculate_syndromes(received)
        
        # Check if all syndromes are zero (no errors)
        if all(s == 0 for s in syndromes):
            return bytes(received[:self.k]), True
        
        # Find error locator polynomial
        error_locator = self._berlekamp_massey(syndromes)
        
        # Find error positions
        error_positions = self._find_error_positions(error_locator)
        
        if len(error_positions) == 0:
            return bytes(received[:self.k]), False  # Uncorrectable errors
        
        # Find error values
        error_values = self._find_error_values(syndromes, error_positions)
        
        # Correct errors
        corrected = received.copy()
        for pos, value in zip(error_positions, error_values):
            corrected[pos] ^= value
        
        return bytes(corrected[:self.k]), True
    
    def _polynomial_division(self, dividend: List[int], divisor: List[int]) -> List[int]:
        """Perform polynomial division in Galois field."""
        result = dividend.copy()
        
        for i in range(len(dividend) - len(divisor) + 1):
            if result[i] != 0:
                coef = result[i]
                for j in range(len(divisor)):
                    if divisor[j] != 0:
                        result[i + j] ^= self._gf_mult(divisor[j], coef)
        
        return result[-(len(divisor) - 1):]
    
    def _calculate_syndromes(self, received: List[int]) -> List[int]:
        """Calculate syndromes for error detection."""
        syndromes = []
        for i in range(2 * self.t):
            syndrome = 0
            for j in range(self.n):
                if received[j] != 0:
                    syndrome ^= self._gf_mult(received[j], self.gf_exp[(i * j) % (self.gf_size - 1)])
            syndromes.append(syndrome)
        return syndromes
    
    def _berlekamp_massey(self, syndromes: List[int]) -> List[int]:
        """Berlekamp-Massey algorithm to find error locator polynomial."""
        C = [1]  # Current error locator polynomial
        B = [1]  # Previous error locator polynomial
        L = 0    # Current degree
        m = 1    # Number of iterations since last update
        
        for n in range(len(syndromes)):
            # Calculate discrepancy
            d = syndromes[n]
            for i in range(1, L + 1):
                d ^= self._gf_mult(C[i], syndromes[n - i])
            
            if d != 0:
                # Update error locator polynomial
                T = C.copy()
                scale = self._gf_div(d, syndromes[n - m])
                
                # Extend C if necessary
                while len(C) < len(B) + n - m + 1:
                    C.append(0)
                
                for i in range(len(B)):
                    if i + n - m < len(C):
                        C[i + n - m] ^= self._gf_mult(B[i], scale)
                
                if 2 * L <= n:
                    L = n + 1 - L
                    B = T
                    m = n + 1
        
        return C[:L + 1]
    
    def _find_error_positions(self, error_locator: List[int]) -> List[int]:
        """Find positions of errors using Chien search."""
        error_positions = []
        
        for i in range(self.n):
            # Evaluate error locator polynomial at α^i
            result = 0
            for j, coef in enumerate(error_locator):
                if coef != 0:
                    result ^= self._gf_mult(coef, self.gf_exp[(i * j) % (self.gf_size - 1)])
            
            if result == 0:
                error_positions.append(i)
        
        return error_positions
    
    def _find_error_values(self, syndromes: List[int], error_positions: List[int]) -> List[int]:
        """Find error values using Forney algorithm."""
        error_values = []
        
        for pos in error_positions:
            # Calculate error evaluator polynomial
            numerator = 0
            denominator = 1
            
            for i in range(len(syndromes)):
                if syndromes[i] != 0:
                    numerator ^= self._gf_mult(syndromes[i], self.gf_exp[(i * pos) % (self.gf_size - 1)])
            
            # Calculate denominator
            for other_pos in error_positions:
                if other_pos != pos:
                    factor = self.gf_exp[pos] ^ self.gf_exp[other_pos]
                    denominator = self._gf_mult(denominator, factor)
            
            # Calculate error value
            if denominator != 0:
                error_value = self._gf_div(numerator, denominator)
                error_values.append(error_value)
            else:
                error_values.append(0)
        
        return error_values


class ErrorCorrectionManager:
    """
    High-level error correction manager for steganographic data.
    
    Provides convenient methods for encoding and decoding data with error correction,
    handling data chunking and reassembly for large datasets.
    """
    
    def __init__(self, chunk_size: int = 200):
        """
        Initialize error correction manager.
        
        Args:
            chunk_size: Size of data chunks for encoding (must be <= RS encoder k)
        """
        self.chunk_size = min(chunk_size, 223)  # Limit to RS encoder capacity
        self.rs_encoder = ReedSolomonEncoder()
    
    def encode_with_error_correction(self, data: bytes) -> bytes:
        """
        Encode data with error correction, handling chunking for large datasets.
        
        Args:
            data: Input data bytes
            
        Returns:
            Encoded data with error correction symbols
        """
        encoded_chunks = []
        
        # Split data into chunks
        for i in range(0, len(data), self.chunk_size):
            chunk = data[i:i + self.chunk_size]
            encoded_chunk = self.rs_encoder.encode(chunk)
            encoded_chunks.append(encoded_chunk)
        
        # Combine all encoded chunks
        return b''.join(encoded_chunks)
    
    def decode_with_error_correction(self, encoded_data: bytes) -> Tuple[bytes, bool]:
        """
        Decode data with error correction, handling chunk reassembly.
        
        Args:
            encoded_data: Encoded data with error correction symbols
            
        Returns:
            Tuple of (decoded data, success flag)
        """
        decoded_chunks = []
        chunk_size = self.rs_encoder.n
        
        # Split encoded data into chunks
        for i in range(0, len(encoded_data), chunk_size):
            chunk = encoded_data[i:i + chunk_size]
            
            # Pad last chunk if necessary
            if len(chunk) < chunk_size:
                chunk = chunk + b'\x00' * (chunk_size - len(chunk))
            
            # Decode chunk
            decoded_chunk, success = self.rs_encoder.decode(chunk)
            
            if not success:
                return b'', False  # Decoding failed
            
            decoded_chunks.append(decoded_chunk)
        
        # Combine decoded chunks
        return b''.join(decoded_chunks), True
    
    def get_error_correction_capability(self) -> int:
        """Get the number of errors that can be corrected per chunk."""
        return self.rs_encoder.t
    
    def get_encoded_size(self, original_size: int) -> int:
        """Calculate the size of encoded data for a given original size."""
        num_chunks = math.ceil(original_size / self.chunk_size)
        return num_chunks * self.rs_encoder.n
    
    def get_compression_ratio(self, original_size: int) -> float:
        """Calculate the expansion ratio due to error correction."""
        encoded_size = self.get_encoded_size(original_size)
        return encoded_size / original_size if original_size > 0 else 1.0 