package main

import (
	"bufio"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"html/template"
	"log"
	"net/http"
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

		scanner := bufio.NewScanner(serialPort)
		scanner.Split(bufio.ScanBytes)

		var buffer []byte
		for isStreaming {
			if scanner.Scan() {
				b := scanner.Bytes()
				if len(b) > 0 {
					// Capture raw output
					rawOutputMutex.Lock()
					rawOutput = append(rawOutput, b[0])
					// Keep only last 10KB of raw output
					if len(rawOutput) > 10240 {
						rawOutput = rawOutput[len(rawOutput)-10240:]
					}
					rawOutputMutex.Unlock()

					buffer = append(buffer, b[0])

					// Look for sync byte (0xA0-0xDB)
					if len(buffer) > 0 && buffer[0] >= 0xA0 && buffer[0] <= 0xDB {
						// Try to read a complete 42-byte packet
						if len(buffer) >= 42 {
							packetData := buffer[:42]
							buffer = buffer[42:]

							// Convert to hex string and parse
							hexStr := hex.EncodeToString(packetData)
							packet, err := ParseHexString(hexStr)
							if err == nil {
								// Validate and process packet
								if packet.ValidateChecksum() {
									points := packet.ExtractPoints()
									allPoints = append(allPoints, points...)

									// Keep only last 1000 points
									if len(allPoints) > 1000 {
										allPoints = allPoints[len(allPoints)-1000:]
									}

									log.Printf("Streamed packet - Degree: %d, RPM: %d, Points: %d",
										packet.Degree, packet.RPM, len(points))
								} else {
									log.Printf("Warning: Invalid checksum in streamed packet")
								}
							}
						}
					} else if len(buffer) > 0 {
						// Remove invalid sync bytes
						buffer = buffer[1:]
					}

					// Prevent buffer from growing too large
					if len(buffer) > 100 {
						buffer = buffer[1:]
					}
				}
			} else {
				if err := scanner.Err(); err != nil {
					log.Printf("Serial scanner error: %v", err)
				}
				break
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
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
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
            <h3>Lidar Visualization (Real-time)</h3>
            <canvas id="lidarChart" width="800" height="600"></canvas>
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
        let chart;
        let allPoints = [];
        let isStreaming = false;
        let updateInterval;
        
        // Initialize chart
        function initChart() {
            const ctx = document.getElementById('lidarChart').getContext('2d');
            chart = new Chart(ctx, {
                type: 'scatter',
                data: {
                    datasets: [{
                        label: 'Lidar Points',
                        data: [],
                        backgroundColor: 'rgba(54, 162, 235, 0.6)',
                        borderColor: 'rgba(54, 162, 235, 1)',
                        pointRadius: 3
                    }]
                },
                options: {
                    responsive: true,
                    animation: false,
                    scales: {
                        x: {
                            type: 'linear',
                            position: 'bottom',
                            title: {
                                display: true,
                                text: 'Angle (degrees)'
                            },
                            min: 0,
                            max: 360
                        },
                        y: {
                            title: {
                                display: true,
                                text: 'Distance (meters)'
                            },
                            min: 0
                        }
                    },
                    plugins: {
                        title: {
                            display: true,
                            text: 'Lidar Point Cloud Visualization'
                        }
                    }
                }
            });
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
        
        // Update chart with latest data
        function updateChart() {
            fetch('/get-points')
            .then(response => response.json())
            .then(data => {
                if (data.success && data.points) {
                    allPoints = data.points;
                    const chartData = allPoints.map(point => ({
                        x: point.angle,
                        y: point.distance
                    }));
                    
                    chart.data.datasets[0].data = chartData;
                    chart.update('none'); // Disable animation for performance
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
        
        // Add points to chart
        function addPoints(points) {
            allPoints = allPoints.concat(points);
            
            // Update chart data
            const chartData = allPoints.map(point => ({
                x: point.angle,
                y: point.distance
            }));
            
            chart.data.datasets[0].data = chartData;
            chart.update();
        }
        
        // Clear all data
        function clearData() {
            allPoints = [];
            chart.data.datasets[0].data = [];
            chart.update();
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
            initChart();
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

func main() {
	// Initialize global storage
	allPoints = make([]LidarPoint, 0)

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
