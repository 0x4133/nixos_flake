package main

import (
	"encoding/hex"
	"encoding/json"
	"fmt"
	"html/template"
	"log"
	"net/http"
	"strings"
	"time"
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

// Global storage for points
var allPoints []LidarPoint

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
        textarea { width: 100%; height: 100px; font-family: monospace; }
        button { padding: 10px 20px; margin: 5px; font-size: 16px; }
        .chart-container { border: 1px solid #ccc; padding: 20px; margin: 20px 0; }
        .info { background: #f0f0f0; padding: 10px; margin: 10px 0; border-radius: 5px; }
        .error { background: #ffebee; color: #c62828; padding: 10px; margin: 10px 0; border-radius: 5px; }
        .success { background: #e8f5e8; color: #2e7d32; padding: 10px; margin: 10px 0; border-radius: 5px; }
    </style>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body>
    <div class="container">
        <h1>Lidar Data Visualizer</h1>
        
        <div class="input-section">
            <h3>Enter Hex Data (42 bytes)</h3>
            <textarea id="hexInput" placeholder="Enter 42-byte hex data here..."></textarea>
            <br>
            <button onclick="parseData()">Parse Data</button>
            <button onclick="clearData()">Clear All Data</button>
            <button onclick="loadSampleData()">Load Sample Data</button>
        </div>
        
        <div id="message"></div>
        
        <div class="chart-container">
            <h3>Lidar Visualization</h3>
            <canvas id="lidarChart" width="800" height="600"></canvas>
        </div>
        
        <div class="info">
            <h4>Data Format:</h4>
            <p>Each packet contains 42 bytes with 6 measurement points.</p>
            <p>Angle calculation: angle = angle_index × 6 + angle_offset</p>
            <p>Distance is converted from mm to meters.</p>
        </div>
    </div>

    <script>
        let chart;
        let allPoints = [];
        
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
        
        // Parse hex data
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

func main() {
	// Initialize global storage
	allPoints = make([]LidarPoint, 0)

	// Set up HTTP routes
	http.HandleFunc("/", handleRoot)
	http.HandleFunc("/parse", handleParse)

	// Start server
	port := ":8080"
	log.Printf("Starting Lidar Data Visualizer on port %s", port)
	log.Printf("Open http://localhost%s in your web browser", port)

	if err := http.ListenAndServe(port, nil); err != nil {
		log.Fatal("Failed to start server:", err)
	}
}
