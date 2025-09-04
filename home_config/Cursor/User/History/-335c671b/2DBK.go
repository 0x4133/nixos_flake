package main

import (
	"bufio"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"html/template"
	"log"
	"net/http"
	"strconv"
	"strings"
	"time"

	"sync"

	"go.bug.st/serial"
)

// LidarPacket represents the 42-byte lidar data packet structure
type LidarPacket struct {
	Sync     byte        `json:"sync"`
	Degree   byte        `json:"degree"`
	RPM      uint16      `json:"rpm"`
	Data     []DataBlock `json:"data"`
	Checksum uint16      `json:"checksum"`
}

// DataBlock represents one of the six data blocks in the packet
type DataBlock struct {
	Intensity uint16 `json:"intensity"`
	Distance  uint16 `json:"distance"`
	Reserved  uint16 `json:"reserved"`
}

// LidarPoint represents a single measurement point
type LidarPoint struct {
	Angle     float64   `json:"angle"`
	Distance  float64   `json:"distance"`
	Intensity uint16    `json:"intensity"`
	Timestamp time.Time `json:"timestamp"`
}

// Global storage for points and serial connection
var (
	allPoints      []LidarPoint
	serialPort     serial.Port
	isStreaming    bool
	rawOutput      []byte
	rawOutputMutex sync.Mutex
)

// ParseHexString parses a hex string into a LidarPacket
func ParseHexString(hexStr string) (*LidarPacket, error) {
	// Remove any spaces or separators
	hexStr = strings.ReplaceAll(hexStr, " ", "")
	hexStr = strings.ReplaceAll(hexStr, "\n", "")
	hexStr = strings.ReplaceAll(hexStr, "\r", "")

	// Convert hex string to bytes
	data, err := hex.DecodeString(hexStr)
	if err != nil {
		return nil, fmt.Errorf("failed to decode hex string: %v", err)
	}

	if len(data) != 42 {
		return nil, fmt.Errorf("expected 42 bytes, got %d", len(data))
	}

	packet := &LidarPacket{
		Sync:     data[0],
		Degree:   data[1],
		RPM:      uint16(data[2]) | uint16(data[3])<<8, // Little endian
		Data:     make([]DataBlock, 6),
		Checksum: uint16(data[40]) | uint16(data[41])<<8, // Little endian
	}

	// Parse the six data blocks
	for i := 0; i < 6; i++ {
		offset := 4 + i*6
		packet.Data[i] = DataBlock{
			Intensity: uint16(data[offset]) | uint16(data[offset+1])<<8,
			Distance:  uint16(data[offset+2]) | uint16(data[offset+3])<<8,
			Reserved:  uint16(data[offset+4]) | uint16(data[offset+5])<<8,
		}
	}

	return packet, nil
}

// ValidateChecksum validates the packet checksum
func (p *LidarPacket) ValidateChecksum() bool {
	var sum byte
	// Sum first 40 bytes
	for i := 0; i < 40; i++ {
		sum += p.getByteAt(i)
	}

	calculatedChecksum := 0xFF - sum
	receivedChecksum := byte(p.Checksum & 0xFF)

	return calculatedChecksum == receivedChecksum
}

// getByteAt returns the byte at the specified index in the packet
func (p *LidarPacket) getByteAt(index int) byte {
	switch index {
	case 0:
		return p.Sync
	case 1:
		return p.Degree
	case 2:
		return byte(p.RPM & 0xFF)
	case 3:
		return byte((p.RPM >> 8) & 0xFF)
	default:
		if index >= 4 && index < 40 {
			blockIndex := (index - 4) / 6
			blockOffset := (index - 4) % 6
			if blockIndex < 6 {
				switch blockOffset {
				case 0:
					return byte(p.Data[blockIndex].Intensity & 0xFF)
				case 1:
					return byte((p.Data[blockIndex].Intensity >> 8) & 0xFF)
				case 2:
					return byte(p.Data[blockIndex].Distance & 0xFF)
				case 3:
					return byte((p.Data[blockIndex].Distance >> 8) & 0xFF)
				case 4:
					return byte(p.Data[blockIndex].Reserved & 0xFF)
				case 5:
					return byte((p.Data[blockIndex].Reserved >> 8) & 0xFF)
				}
			}
		}
	}
	return 0
}

// ExtractPoints extracts all measurement points from a packet
func (p *LidarPacket) ExtractPoints() []LidarPoint {
	var points []LidarPoint
	now := time.Now()

	for i, block := range p.Data {
		// Calculate angle using the formula: angle = angle_index * 6 + angle_offset
		angle := float64(p.Degree)*6.0 + float64(i)

		// Convert distance from millimeters to meters (assuming the distance is in mm)
		distance := float64(block.Distance) / 1000.0

		point := LidarPoint{
			Angle:     angle,
			Distance:  distance,
			Intensity: block.Intensity,
			Timestamp: now,
		}

		points = append(points, point)
	}

	return points
}

// StartSerialStream starts streaming data from the serial port
func StartSerialStream() error {
	mode := &serial.Mode{
		BaudRate: 115200,
		DataBits: 8,
		Parity:   serial.NoParity,
		StopBits: serial.OneStopBit,
	}

	var err error
	serialPort, err = serial.Open("/dev/ttyACM0", mode)
	if err != nil {
		return fmt.Errorf("failed to open serial port: %v", err)
	}

	isStreaming = true
	log.Printf("Started streaming from /dev/ttyACM0 at 115200 baud")

	// Start streaming in a goroutine
	go func() {
		defer serialPort.Close()

		reader := bufio.NewReader(serialPort)
		var buffer []byte
		var asciiLine strings.Builder

		for isStreaming {
			b, err := reader.ReadByte()
			if err != nil {
				log.Printf("Serial read error: %v", err)
				break
			}

			// Capture raw output
			rawOutputMutex.Lock()
			rawOutput = append(rawOutput, b)
			if len(rawOutput) > 10240 {
				rawOutput = rawOutput[len(rawOutput)-10240:]
			}
			rawOutputMutex.Unlock()

			// Build ASCII line and parse on newline
			if b == '\n' {
				line := asciiLine.String()
				asciiLine.Reset()

				if len(strings.TrimSpace(line)) > 0 {
					log.Printf("Raw line: %s", line)
					bytesFromLine := parseHexLineToBytes(line)
					if len(bytesFromLine) > 0 {
						log.Printf("Parsed %d bytes: %v", len(bytesFromLine), bytesFromLine)
						buffer = append(buffer, bytesFromLine...)
						log.Printf("Buffer now has %d bytes", len(buffer))
					}
				}

				// Try to assemble packets from buffer
				for len(buffer) >= 42 {
					// Look for sync byte 0xFA (250 in decimal)
					if buffer[0] == 0xFA {
						packetData := buffer[:42]
						buffer = buffer[42:]

						hexStr := hex.EncodeToString(packetData)
						log.Printf("Found packet: %s", hexStr)

						packet, err := ParseHexString(hexStr)
						if err == nil {
							// Ignore checksum validation - accept all packets
							points := packet.ExtractPoints()
							allPoints = append(allPoints, points...)
							if len(allPoints) > 1000 {
								allPoints = allPoints[len(allPoints)-1000:]
							}
							log.Printf("Streamed packet - Degree: %d, RPM: %d, Points: %d", packet.Degree, packet.RPM, len(points))
						} else {
							log.Printf("Packet parse error: %v", err)
						}
					} else {
						// Remove one byte and try again
						buffer = buffer[1:]
					}
				}
			} else {
				asciiLine.WriteByte(b)
			}
		}
	}()

	return nil
}

// StopSerialStream stops the serial streaming
func StopSerialStream() {
	isStreaming = false
	if serialPort != nil {
		serialPort.Close()
		serialPort = nil
	}
	log.Printf("Stopped serial streaming")
}

// ClearRawOutput clears the captured raw output
func ClearRawOutput() {
	rawOutputMutex.Lock()
	rawOutput = make([]byte, 0)
	rawOutputMutex.Unlock()
	log.Printf("Cleared raw output buffer")
}

// GetRawOutput returns the current raw output as hex string
func GetRawOutput() string {
	rawOutputMutex.Lock()
	defer rawOutputMutex.Unlock()

	if len(rawOutput) == 0 {
		return "No raw data captured yet. Start streaming to capture data."
	}

	// Convert to hex string with formatting
	hexStr := hex.EncodeToString(rawOutput)

	// Format with spaces every 2 characters for readability
	var formatted strings.Builder
	for i := 0; i < len(hexStr); i += 2 {
		if i > 0 {
			formatted.WriteString(" ")
		}
		if i+1 < len(hexStr) {
			formatted.WriteString(hexStr[i : i+2])
		} else {
			formatted.WriteString(hexStr[i:])
		}
	}

	return formatted.String()
}

// HTML template for the web interface
const htmlTemplate = `
<!DOCTYPE html>
<html>
<head>
    <title>Lidar Data Visualizer</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .container { max-width: 1200px; margin: 0 auto; }
        .input-section { margin-bottom: 20px; }
        .control-section { margin-bottom: 20px; padding: 15px; background: #f5f5f5; border-radius: 5px; }
        textarea { width: 100%; height: 100px; font-family: monospace; }
        button { padding: 10px 20px; margin: 5px; font-size: 16px; }
        .chart-container { border: 1px solid #ccc; padding: 20px; margin: 20px 0; }
        .info { background: #f0f0f0; padding: 10px; margin: 10px 0; border-radius: 5px; }
        .error { background: #ffebee; color: #c62828; padding: 10px; margin: 10px 0; border-radius: 5px; }
        .success { background: #e8f5e8; color: #2e7d32; padding: 10px; margin: 10px 0; border-radius: 5px; }
        .status { background: #e3f2fd; color: #1565c0; padding: 10px; margin: 10px 0; border-radius: 5px; }
        .streaming { background: #e8f5e8; color: #2e7d32; }
        .not-streaming { background: #ffebee; color: #c62828; }
        .raw-output-container { border: 1px solid #ccc; background: #f8f8f8; padding: 15px; margin: 10px 0; border-radius: 5px; }
        .raw-output { font-family: 'Courier New', monospace; font-size: 12px; line-height: 1.4; margin: 0; white-space: pre-wrap; word-break: break-all; }
    </style>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js"></script>
</head>
<body>
    <div class="container">
        <h1>Lidar Data Visualizer</h1>
        
        <div class="control-section">
            <h3>Serial Port Control</h3>
            <button id="startStream" onclick="startStreaming()">Start Streaming</button>
            <button id="stopStream" onclick="stopStreaming()" disabled>Stop Streaming</button>
            <span id="streamStatus" class="not-streaming">Not Streaming</span>
        </div>
        
        <div class="control-section">
            <h3>Raw Output Control</h3>
            <button onclick="showRawOutput()">Show Raw Output</button>
            <button onclick="clearRawOutput()">Clear Raw Output</button>
            <span id="rawOutputStatus">Raw output buffer: 0 bytes</span>
        </div>
        
        <div id="rawOutputSection" style="display: none;">
            <h3>Raw Serial Port Output</h3>
            <div class="raw-output-container">
                <pre id="rawOutputDisplay" class="raw-output"></pre>
            </div>
        </div>
        
        <div class="input-section">
            <h3>Manual Hex Input (42 bytes)</h3>
            <textarea id="hexInput" placeholder="Enter 42-byte hex data here..."></textarea>
            <br>
            <button onclick="parseData()">Parse Data</button>
            <button onclick="clearData()">Clear All Data</button>
            <button onclick="loadSampleData()">Load Sample Data</button>
        </div>
        
        <div id="message"></div>
        
        <div class="chart-container">
            <h3>3D Lidar Point Cloud Visualization</h3>
            <div id="3dContainer" style="width: 800px; height: 600px; border: 1px solid #ccc;"></div>
        </div>
        
        <div class="info">
            <h4>Data Format:</h4>
            <p>Each packet contains 42 bytes with 6 measurement points.</p>
            <p>Angle calculation: angle = angle_index × 6 + angle_offset</p>
            <p>Distance is converted from mm to meters.</p>
            <p><strong>Serial Port:</strong> /dev/ttyACM0 at 115200 baud</p>
        </div>
    </div>

    <script>
        let scene, camera, renderer, controls;
        let pointCloud;
        let allPoints = [];
        let isStreaming = false;
        let updateInterval;
        
        // Initialize 3D scene
        function init3DScene() {
            const container = document.getElementById('3dContainer');
            
            // Scene
            scene = new THREE.Scene();
            scene.background = new THREE.Color(0x000000);
            
            // Camera
            camera = new THREE.PerspectiveCamera(75, container.clientWidth / container.clientHeight, 0.1, 1000);
            camera.position.set(0, 0, 5);
            
            // Renderer
            renderer = new THREE.WebGLRenderer({ antialias: true });
            renderer.setSize(container.clientWidth, container.clientHeight);
            container.appendChild(renderer.domElement);
            
            // Controls
            controls = new THREE.OrbitControls(camera, renderer.domElement);
            controls.enableDamping = true;
            controls.dampingFactor = 0.05;
            
            // Lighting
            const ambientLight = new THREE.AmbientLight(0x404040, 0.6);
            scene.add(ambientLight);
            
            const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
            directionalLight.position.set(1, 1, 1);
            scene.add(directionalLight);
            
            // Create initial point cloud
            createPointCloud();
            
            // Start render loop
            animate();
        }
        
        // Create or update point cloud
        function createPointCloud() {
            if (pointCloud) {
                scene.remove(pointCloud);
            }
            
            if (allPoints.length === 0) {
                return;
            }
            
            const geometry = new THREE.BufferGeometry();
            const positions = [];
            const colors = [];
            
            allPoints.forEach(point => {
                // Convert polar coordinates (angle, distance) to 3D Cartesian
                const angleRad = (point.angle * Math.PI) / 180;
                const x = point.distance * Math.cos(angleRad);
                const y = point.distance * Math.sin(angleRad);
                const z = 0; // All points at same height for now
                
                positions.push(x, y, z);
                
                // Color based on intensity (normalize to 0-1)
                const intensity = Math.min(point.intensity / 255, 1);
                colors.push(intensity, intensity, 1 - intensity); // Blue to red based on intensity
            });
            
            geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
            geometry.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3));
            
            const material = new THREE.PointsMaterial({
                size: 0.05,
                vertexColors: true,
                transparent: true,
                opacity: 0.8
            });
            
            pointCloud = new THREE.Points(geometry, material);
            scene.add(pointCloud);
        }
        
        // Animation loop
        function animate() {
            requestAnimationFrame(animate);
            controls.update();
            renderer.render(scene, camera);
        }
        
        // Start streaming from serial port
        function startStreaming() {
            fetch('/start-stream', { method: 'POST' })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    isStreaming = true;
                    document.getElementById('startStream').disabled = true;
                    document.getElementById('stopStream').disabled = false;
                    document.getElementById('streamStatus').textContent = 'Streaming...';
                    document.getElementById('streamStatus').className = 'streaming';
                    
                    // Start periodic updates
                    updateInterval = setInterval(updateChart, 100);
                    showMessage('Started streaming from serial port', 'success');
                } else {
                    showMessage('Error: ' + data.error, 'error');
                }
            })
            .catch(error => {
                showMessage('Error: ' + error.message, 'error');
            });
        }
        
        // Stop streaming
        function stopStreaming() {
            fetch('/stop-stream', { method: 'POST' })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    isStreaming = false;
                    document.getElementById('startStream').disabled = false;
                    document.getElementById('stopStream').disabled = true;
                    document.getElementById('streamStatus').textContent = 'Not Streaming';
                    document.getElementById('streamStatus').className = 'not-streaming';
                    
                    // Stop periodic updates
                    if (updateInterval) {
                        clearInterval(updateInterval);
                        updateInterval = null;
                    }
                    showMessage('Stopped streaming', 'success');
                } else {
                    showMessage('Error: ' + data.error, 'error');
                }
            })
            .catch(error => {
                showMessage('Error: ' + error.message, 'error');
            });
        }
        
        // Update 3D visualization with latest data
        function updateChart() {
            fetch('/get-points')
            .then(response => response.json())
            .then(data => {
                if (data.success && data.points) {
                    allPoints = data.points;
                    createPointCloud();
                }
            })
            .catch(error => {
                console.log('Update error:', error);
            });
            
            // Also update raw output status if streaming
            if (isStreaming) {
                updateRawOutputStatus();
            }
        }
        
        // Show raw output
        function showRawOutput() {
            fetch('/get-raw-output')
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    document.getElementById('rawOutputDisplay').textContent = data.rawOutput;
                    document.getElementById('rawOutputSection').style.display = 'block';
                    updateRawOutputStatus();
                    showMessage('Raw output displayed', 'success');
                } else {
                    showMessage('Error: ' + data.error, 'error');
                }
            })
            .catch(error => {
                showMessage('Error: ' + error.message, 'error');
            });
        }
        
        // Clear raw output
        function clearRawOutput() {
            fetch('/clear-raw-output', { method: 'POST' })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    document.getElementById('rawOutputDisplay').textContent = '';
                    document.getElementById('rawOutputSection').style.display = 'none';
                    updateRawOutputStatus();
                    showMessage('Raw output cleared', 'success');
                } else {
                    showMessage('Error: ' + data.error, 'error');
                }
            })
            .catch(error => {
                showMessage('Error: ' + error.message, 'error');
            });
        }
        
        // Update raw output status
        function updateRawOutputStatus() {
            fetch('/get-raw-output')
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    document.getElementById('rawOutputStatus').textContent = 'Raw output buffer: ' + data.byteCount + ' bytes';
                }
            })
            .catch(error => {
                console.log('Status update error:', error);
            });
        }
        
        // Parse hex data manually
        function parseData() {
            const hexInput = document.getElementById('hexInput').value.trim();
            if (!hexInput) {
                showMessage('Please enter hex data', 'error');
                return;
            }
            
            fetch('/parse', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-json',
                },
                body: JSON.stringify({hex: hexInput})
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    showMessage('Data parsed successfully! Added ' + data.points.length + ' points.', 'success');
                    addPoints(data.points);
                } else {
                    showMessage('Error: ' + data.error, 'error');
                }
            })
            .catch(error => {
                showMessage('Error: ' + error.message, 'error');
            });
        }
        
        // Add points to 3D visualization
        function addPoints(points) {
            allPoints = allPoints.concat(points);
            
            // Update 3D point cloud
            createPointCloud();
        }
        
        // Clear all data
        function clearData() {
            allPoints = [];
            createPointCloud(); // Clear 3D visualization
            document.getElementById('hexInput').value = '';
            showMessage('All data cleared', 'success');
        }
        
        // Load sample data
        function loadSampleData() {
            const sampleHex = "A1C30BB0228B00000000B0228B00000000B0228B00000000B0228B00000000B0228B00000000B0228B000000001313";
            document.getElementById('hexInput').value = sampleHex;
            showMessage('Sample data loaded. Click Parse Data to visualize.', 'success');
        }
        
        // Show message
        function showMessage(text, type) {
            const messageDiv = document.getElementById('message');
            messageDiv.innerHTML = '<div class="' + type + '">' + text + '</div>';
            setTimeout(() => {
                messageDiv.innerHTML = '';
            }, 5000);
        }
        
        // Initialize chart when page loads
        window.onload = function() {
            init3DScene(); // Initialize Three.js scene
        };
    </script>
</body>
</html>
`

// HTTP handlers
func handleRoot(w http.ResponseWriter, r *http.Request) {
	tmpl, err := template.New("lidar").Parse(htmlTemplate)
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	tmpl.Execute(w, nil)
}

func handleParse(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var request struct {
		Hex string `json:"hex"`
	}

	if err := json.NewDecoder(r.Body).Decode(&request); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}

	packet, err := ParseHexString(request.Hex)
	if err != nil {
		response := map[string]interface{}{
			"success": false,
			"error":   err.Error(),
		}
		json.NewEncoder(w).Encode(response)
		return
	}

	// Validate checksum
	checksumValid := packet.ValidateChecksum()
	if !checksumValid {
		log.Printf("Warning: Checksum validation failed for packet")
	}

	// Extract points
	points := packet.ExtractPoints()
	allPoints = append(allPoints, points...)

	// Keep only last 1000 points
	if len(allPoints) > 1000 {
		allPoints = allPoints[len(allPoints)-1000:]
	}

	// Log packet info
	log.Printf("Parsed packet - Degree: %d, RPM: %d, Points: %d, Checksum valid: %v",
		packet.Degree, packet.RPM, len(points), checksumValid)

	response := map[string]interface{}{
		"success": true,
		"points":  points,
		"packet":  packet,
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(response)
}

func handleStartStream(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	err := StartSerialStream()
	response := map[string]interface{}{
		"success": err == nil,
	}

	if err != nil {
		response["error"] = err.Error()
		log.Printf("Failed to start streaming: %v", err)
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(response)
}

func handleStopStream(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	StopSerialStream()
	response := map[string]interface{}{
		"success": true,
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(response)
}

func handleGetPoints(w http.ResponseWriter, r *http.Request) {
	response := map[string]interface{}{
		"success": true,
		"points":  allPoints,
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(response)
}

func handleGetRawOutput(w http.ResponseWriter, r *http.Request) {
	rawData := GetRawOutput()
	response := map[string]interface{}{
		"success":   true,
		"rawOutput": rawData,
		"byteCount": len(rawOutput),
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(response)
}

func handleClearRawOutput(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	ClearRawOutput()
	response := map[string]interface{}{
		"success": true,
	}

	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(response)
}

// TestParseSampleData tests parsing with the sample data format you provided to verify the packet parsing works.
func TestParseSampleData() {
	sampleLine := "20 43 39 20 42 35 20 30 42 20 35 35 20 30 32 20 30 30 20 42 39 20 42 39 20 30 33 20 30 32 20 44 42 20 30 30 20 46 41 20 43 41 20 42 35 20 30 42 20 34 34 20 30 33 20 32 31 20 30 30 20 30 30 20 42 45 20 42 46 20 0d 0a"

	bytes := parseHexLineToBytes(sampleLine)
	log.Printf("Test parse result: %d bytes, %v", len(bytes), bytes)

	// Look for 0xFA in the parsed bytes
	for i, b := range bytes {
		if b == 0xFA {
			log.Printf("Found 0xFA at position %d", i)
		}
	}
}

// parseHexLineToBytes converts a line of space-separated hex (e.g., "20 43 39") to bytes
func parseHexLineToBytes(line string) []byte {
	line = strings.TrimSpace(line)
	if line == "" {
		return nil
	}
	parts := strings.Fields(line)
	out := make([]byte, 0, len(parts))
	for _, p := range parts {
		p = strings.TrimSpace(p)
		if p == "" {
			continue
		}
		// ignore common separators like 0d, 0a as printable newlines already handled
		if len(p) > 2 {
			// in case input is like '0x20'
			if strings.HasPrefix(p, "0x") || strings.HasPrefix(p, "0X") {
				p = p[2:]
			}
		}
		if len(p) == 1 {
			p = "0" + p
		}
		b, err := strconv.ParseUint(p, 16, 8)
		if err != nil {
			continue
		}
		out = append(out, byte(b))
	}
	return out
}

func main() {
	// Initialize global storage
	allPoints = make([]LidarPoint, 0)
	rawOutput = make([]byte, 0)

	// Test parsing with sample data
	TestParseSampleData()

	// Set up HTTP routes
	http.HandleFunc("/", handleRoot)
	http.HandleFunc("/parse", handleParse)
	http.HandleFunc("/start-stream", handleStartStream)
	http.HandleFunc("/stop-stream", handleStopStream)
	http.HandleFunc("/get-points", handleGetPoints)
	http.HandleFunc("/get-raw-output", handleGetRawOutput)
	http.HandleFunc("/clear-raw-output", handleClearRawOutput)

	// Start server
	port := ":8080"
	log.Printf("Starting Lidar Data Visualizer on port %s", port)
	log.Printf("Open http://localhost%s in your web browser", port)
	log.Printf("Serial port: /dev/ttyACM0 at 115200 baud")

	if err := http.ListenAndServe(port, nil); err != nil {
		log.Fatal("Failed to start server:", err)
	}
}
