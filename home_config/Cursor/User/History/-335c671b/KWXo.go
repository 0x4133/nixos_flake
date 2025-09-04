package main

import (
	"bufio"
	"encoding/json"
	"fmt"
	"html/template"
	"log"
	"net/http"
	"regexp"
	"strconv"
	"strings"
	"time"

	"sync"

	"go.bug.st/serial"
)

// LidarPoint represents a single measurement point
type LidarPoint struct {
	Angle     float64   `json:"angle"`
	Distance  float64   `json:"distance"`
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

// heuristicallySelectDistance returns a plausible distance in meters from two uint16 candidates (order unknown)
func heuristicallySelectDistance(a uint16, b uint16) (float64, bool) {
	// plausible in mm: 120..3500
	inRange := func(v uint16) bool { return v >= 120 && v <= 3500 }
	if inRange(a) && !inRange(b) {
		return float64(a) / 1000.0, true
	}
	if inRange(b) && !inRange(a) {
		return float64(b) / 1000.0, true
	}
	if inRange(a) && inRange(b) {
		// pick the smaller (closer object)
		if a < b {
			return float64(a) / 1000.0, true
		}
		return float64(b) / 1000.0, true
	}
	return 0, false
}

// parseAsciiHexLine converts "FA A0 ..." style into bytes
func parseAsciiHexLine(line string) []byte {
	fields := strings.Fields(strings.TrimSpace(line))
	out := make([]byte, 0, len(fields))
	for _, f := range fields {
		if len(f) == 0 {
			continue
		}
		if strings.HasPrefix(f, "0x") || strings.HasPrefix(f, "0X") {
			f = f[2:]
		}
		if len(f) == 1 {
			f = "0" + f
		}
		v, err := strconv.ParseUint(f, 16, 8)
		if err != nil {
			continue
		}
		out = append(out, byte(v))
	}
	return out
}

// tryExtractFrames scans buffer for 42-byte frames and returns consumed points and new buffer
func tryExtractFrames(buffer []byte) ([]LidarPoint, []byte) {
	points := make([]LidarPoint, 0, 24)
	now := time.Now()
	i := 0
	for len(buffer)-i >= 42 {
		// resync to header 0xFA and valid index 0xA0..0xDB
		if buffer[i] != 0xFA || buffer[i+1] < 0xA0 || buffer[i+1] > 0xDB {
			i++
			continue
		}
		frame := buffer[i : i+42]
		// index
		idx := int(frame[1]) - 0xA0 // 0..59/60
		baseAngle := float64(idx) * 6.0

		log.Printf("Frame %d (angle %.1f): %02X %02X %02X %02X %02X %02X...",
			idx, baseAngle, frame[0], frame[1], frame[2], frame[3], frame[4], frame[5])

		// Scan the entire frame for reasonable distance values
		// Try different byte combinations and interpretations
		var framePoints []LidarPoint

		// Method 1: Try consecutive 2-byte pairs throughout the frame
		for pos := 2; pos < len(frame)-1; pos++ {
			// Skip if we're at a sync byte position
			if pos > 0 && frame[pos-1] == 0xFA {
				continue
			}

			// Try little-endian
			distLE := uint16(frame[pos]) | uint16(frame[pos+1])<<8
			// Try big-endian
			distBE := uint16(frame[pos+1]) | uint16(frame[pos])<<8

			// Check if either gives a reasonable distance
			var distM float64
			var valid bool

			if distLE >= 120 && distLE <= 8000 { // Extended range for testing
				distM = float64(distLE) / 1000.0
				valid = true
			} else if distBE >= 120 && distBE <= 8000 {
				distM = float64(distBE) / 1000.0
				valid = true
			}

			if valid {
				// Calculate angle based on position in frame
				// Distribute points across the frame's angular range
				relativePos := float64(pos-2) / float64(len(frame)-2)
				angle := baseAngle + relativePos*6.0
				if angle >= 360 {
					angle -= 360
				}

				point := LidarPoint{Angle: angle, Distance: distM, Timestamp: now}
				framePoints = append(framePoints, point)

				log.Printf("  Found distance at pos %d: LE=%d BE=%d -> %.3fm at %.1f°",
					pos, distLE, distBE, distM, angle)
			}
		}

		// Method 2: Look for patterns that might indicate distance data
		// Some lidars use specific byte patterns or have checksums
		// Let me try to find more systematic patterns

		// If we didn't find enough points with method 1, try alternative parsing
		if len(framePoints) < 3 {
			log.Printf("  Method 1 found only %d points, trying alternative parsing", len(framePoints))

			// Try looking at specific byte positions that might contain distance data
			// Based on common lidar protocols, distance might be in specific locations
			for k := 0; k < 6; k++ {
				// Try different byte combinations
				pos1 := 4 + k*6
				pos2 := 5 + k*6
				pos3 := 6 + k*6
				pos4 := 7 + k*6

				if pos4 >= len(frame) {
					break
				}

				// Try different 2-byte combinations
				combinations := []uint16{
					uint16(frame[pos1]) | uint16(frame[pos2])<<8, // pos1-2 LE
					uint16(frame[pos2]) | uint16(frame[pos1])<<8, // pos1-2 BE
					uint16(frame[pos3]) | uint16(frame[pos4])<<8, // pos3-4 LE
					uint16(frame[pos4]) | uint16(frame[pos3])<<8, // pos3-4 BE
				}

				for _, dist := range combinations {
					if dist >= 120 && dist <= 8000 {
						distM := float64(dist) / 1000.0
						angle := baseAngle + float64(k)*6.0
						if angle >= 360 {
							angle -= 360
						}

						point := LidarPoint{Angle: angle, Distance: distM, Timestamp: now}
						framePoints = append(framePoints, point)

						log.Printf("  Alt method: sample %d -> %.3fm at %.1f°", k, distM, angle)
						break // Found one for this sample, move to next
					}
				}
			}
		}

		// Add all found points
		points = append(points, framePoints...)
		log.Printf("  Frame %d: total %d points found", idx, len(framePoints))

		// advance past frame
		i += 42
	}
	return points, buffer[i:]
}

// ParseLDS01Line parses a line from LDS-01 in format "r[angle]=distance"
func ParseLDS01Line(line string) ([]LidarPoint, error) {
	line = strings.TrimSpace(line)
	if line == "" {
		return nil, nil
	}

	// LDS-01 format: r[359]=0.438000,r[358]=0.385000,r[357]=0.379000,...
	// Parse each r[angle]=distance pair
	re := regexp.MustCompile(`r\[(\d+)\]=([\d.]+)`)
	matches := re.FindAllStringSubmatch(line, -1)

	if len(matches) == 0 {
		return nil, fmt.Errorf("no valid LDS-01 data found in line: %s", line)
	}

	var points []LidarPoint
	now := time.Now()

	for _, match := range matches {
		if len(match) != 3 {
			continue
		}

		angleStr := match[1]
		distanceStr := match[2]

		angle, err := strconv.Atoi(angleStr)
		if err != nil {
			log.Printf("Invalid angle: %s", angleStr)
			continue
		}

		distance, err := strconv.ParseFloat(distanceStr, 64)
		if err != nil {
			log.Printf("Invalid distance: %s", distanceStr)
			continue
		}

		// Convert angle to 0-360 range and convert to radians for 3D positioning
		normalizedAngle := float64(angle)
		if normalizedAngle >= 360.0 {
			normalizedAngle = normalizedAngle - 360.0
		}

		point := LidarPoint{
			Angle:     normalizedAngle,
			Distance:  distance, // Already in meters
			Timestamp: now,
		}

		points = append(points, point)
	}

	return points, nil
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
		var lineBuffer strings.Builder
		var hexBuf []byte

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

			// Assemble line
			if b == '\n' || b == '\r' {
				line := strings.TrimSpace(lineBuffer.String())
				lineBuffer.Reset()
				if line == "" {
					continue
				}

				if strings.Contains(line, "r[") { // LDS-01 text line
					points, err := ParseLDS01Line(line)
					if err == nil && len(points) > 0 {
						allPoints = append(allPoints, points...)
					} else if err != nil {
						log.Printf("Parse error: %v", err)
					}
				} else { // assume ASCII hex bytes
					bytes := parseAsciiHexLine(line)
					if len(bytes) > 0 {
						hexBuf = append(hexBuf, bytes...)
						pts, remain := tryExtractFrames(hexBuf)
						hexBuf = remain
						if len(pts) > 0 {
							allPoints = append(allPoints, pts...)
						}
					}
				}
				// trim storage
				if len(allPoints) > 6000 {
					allPoints = allPoints[len(allPoints)-6000:]
				}
			} else {
				lineBuffer.WriteByte(b)
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
	hexStr := fmt.Sprintf("%x", rawOutput)

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
    <title>LDS-01 Lidar Data Visualizer</title>
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
        <h1>LDS-01 Lidar Data Visualizer</h1>
        
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
        
        <div class="control-section">
            <h3>Visualization Control</h3>
            <label><input type="checkbox" id="fillMode" onchange="toggleFillMode()"> Fill Mode (Denser Points)</label>
            <button onclick="resetView()">Reset View</button>
            <button onclick="toggleWireframe()">Toggle Wireframe</button>
        </div>
        
        <div id="rawOutputSection" style="display: none;">
            <h3>Raw Serial Port Output</h3>
            <div class="raw-output-container">
                <pre id="rawOutputDisplay" class="raw-output"></pre>
            </div>
        </div>
        
        <div class="input-section">
            <h3>Manual LDS-01 Input (r[angle]=distance format)</h3>
            <textarea id="ldsInput" placeholder="Enter LDS-01 data here (e.g., r[359]=0.438000,r[358]=0.385000)"></textarea>
            <br>
            <button onclick="parseLDSData()">Parse Data</button>
            <button onclick="clearData()">Clear All Data</button>
            <button onclick="loadSampleData()">Load Sample Data</button>
        </div>
        
        <div id="message"></div>
        
        <div class="chart-container">
            <h3>3D Lidar Point Cloud Visualization</h3>
            <div id="3dContainer" style="width: 800px; height: 600px; border: 1px solid #ccc;"></div>
            <div id="pointStatus" style="margin-top: 10px; padding: 10px; background: #f0f0f0; border-radius: 5px;">
                <strong>Status:</strong> <span id="pointCount">0</span> points loaded | 
                <strong>Last Update:</strong> <span id="lastUpdate">Never</span>
            </div>
        </div>
        
        <div class="info">
            <h4>LDS-01 Data Format:</h4>
            <p>Each line contains multiple measurements in format: r[angle]=distance</p>
            <p>Example: r[359]=0.438000,r[358]=0.385000,r[357]=0.379000</p>
            <p><strong>Serial Port:</strong> /dev/ttyACM0 at 115200 baud</p>
            <p><strong>Scan Rate:</strong> 300±10 rpm | <strong>Resolution:</strong> 1° | <strong>Range:</strong> 360°</p>
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
            
            // Camera - position it to see the full point cloud
            camera = new THREE.PerspectiveCamera(75, container.clientWidth / container.clientHeight, 0.1, 1000);
            camera.position.set(0, 0, 10);
            
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
            
            // Add coordinate axes for reference
            const axesHelper = new THREE.AxesHelper(5);
            scene.add(axesHelper);
            
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
                console.log("No points to display");
                return;
            }
            
            console.log('Creating point cloud with ' + allPoints.length + ' points');
            
            const geometry = new THREE.BufferGeometry();
            const positions = [];
            const colors = [];
            
            // Calculate bounds for scaling
            let minX = Infinity, maxX = -Infinity;
            let minY = Infinity, maxY = -Infinity;
            let minZ = Infinity, maxZ = -Infinity;
            
            // Create denser point cloud by interpolating between points
            const interpolatedPoints = [];
            
            allPoints.forEach((point, index) => {
                // Add the original point
                interpolatedPoints.push(point);
                
                // Add interpolated points between this and the next point
                if (index < allPoints.length - 1) {
                    const nextPoint = allPoints[index + 1];
                    const steps = 3; // Add 3 interpolated points between each pair
                    
                    for (let i = 1; i <= steps; i++) {
                        const t = i / (steps + 1);
                        const interpolatedPoint = {
                            angle: point.angle + (nextPoint.angle - point.angle) * t,
                            distance: point.distance + (nextPoint.distance - point.distance) * t,
                            timestamp: point.timestamp
                        };
                        interpolatedPoints.push(interpolatedPoint);
                    }
                }
            });
            
            // Use interpolated points for visualization
            interpolatedPoints.forEach(point => {
                // Convert polar coordinates (angle, distance) to 3D Cartesian
                const angleRad = (point.angle * Math.PI) / 180;
                const x = point.distance * Math.cos(angleRad);
                const y = point.distance * Math.sin(angleRad);
                const z = 0; // All points at same height for now
                
                positions.push(x, y, z);
                
                // Track bounds
                minX = Math.min(minX, x);
                maxX = Math.max(maxX, x);
                minY = Math.min(minY, y);
                maxY = Math.max(maxY, y);
                minZ = Math.min(minZ, z);
                maxZ = Math.max(maxZ, z);
                
                // Color based on distance (closer = red, farther = blue)
                const normalizedDistance = Math.min(point.distance / 3.5, 1); // Max range is 3.5m
                colors.push(normalizedDistance, 0.5, 1 - normalizedDistance);
            });
            
            console.log('Point cloud bounds: X[' + minX.toFixed(3) + ', ' + maxX.toFixed(3) + '], Y[' + minY.toFixed(3) + ', ' + maxY.toFixed(3) + '], Z[' + minZ.toFixed(3) + ', ' + maxZ.toFixed(3) + ']');
            console.log('Using ' + interpolatedPoints.length + ' interpolated points for visualization');
            
            geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
            geometry.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3));
            
            // Make points much larger and more visible
            const pointSize = Math.max(0.1, Math.min(0.3, 20 / Math.sqrt(interpolatedPoints.length)));
            
            const material = new THREE.PointsMaterial({
                size: pointSize,
                vertexColors: true,
                transparent: true,
                opacity: 0.9,
                sizeAttenuation: false // Make points same size regardless of distance
            });
            
            pointCloud = new THREE.Points(geometry, material);
            scene.add(pointCloud);
            
            // Auto-adjust camera to fit all points
            const box = new THREE.Box3().setFromObject(pointCloud);
            const center = box.getCenter(new THREE.Vector3());
            const size = box.getSize(new THREE.Vector3());
            const maxDim = Math.max(size.x, size.y, size.z);
            const fov = camera.fov * (Math.PI / 180);
            let cameraZ = Math.abs(maxDim / 2 / Math.tan(fov / 2));
            cameraZ *= 1.5; // Add some padding
            
            camera.position.set(center.x, center.y, center.z + cameraZ);
            camera.lookAt(center);
            controls.target.copy(center);
            controls.update();
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
                    document.getElementById('pointCount').textContent = allPoints.length;
                    document.getElementById('lastUpdate').textContent = new Date().toLocaleTimeString();
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
        
        // Toggle fill mode for denser visualization
        function toggleFillMode() {
            const fillMode = document.getElementById('fillMode').checked;
            if (fillMode) {
                // Create even denser point cloud
                createDensePointCloud();
            } else {
                // Use normal point cloud
                createPointCloud();
            }
        }
        
        // Create very dense point cloud
        function createDensePointCloud() {
            if (pointCloud) {
                scene.remove(pointCloud);
            }
            
            if (allPoints.length === 0) {
                return;
            }
            
            const geometry = new THREE.BufferGeometry();
            const positions = [];
            const colors = [];
            
            // Create much denser interpolation
            const interpolatedPoints = [];
            
            allPoints.forEach((point, index) => {
                interpolatedPoints.push(point);
                
                if (index < allPoints.length - 1) {
                    const nextPoint = allPoints[index + 1];
                    const steps = 10; // Much more interpolation
                    
                    for (let i = 1; i <= steps; i++) {
                        const t = i / (steps + 1);
                        const interpolatedPoint = {
                            angle: point.angle + (nextPoint.angle - point.angle) * t,
                            distance: point.distance + (nextPoint.distance - point.distance) * t,
                            timestamp: point.timestamp
                        };
                        interpolatedPoints.push(interpolatedPoint);
                    }
                }
            });
            
            interpolatedPoints.forEach(point => {
                const angleRad = (point.angle * Math.PI) / 180;
                const x = point.distance * Math.cos(angleRad);
                const y = point.distance * Math.sin(angleRad);
                const z = 0;
                
                positions.push(x, y, z);
                
                const normalizedDistance = Math.min(point.distance / 3.5, 1);
                colors.push(normalizedDistance, 0.5, 1 - normalizedDistance);
            });
            
            geometry.setAttribute('position', new THREE.Float32BufferAttribute(positions, 3));
            geometry.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3));
            
            const material = new THREE.PointsMaterial({
                size: 0.05, // Smaller points for dense mode
                vertexColors: true,
                transparent: true,
                opacity: 0.8,
                sizeAttenuation: false
            });
            
            pointCloud = new THREE.Points(geometry, material);
            scene.add(pointCloud);
            
            // Update status
            document.getElementById('pointCount').textContent = interpolatedPoints.length + ' (dense mode)';
        }
        
        // Reset camera view
        function resetView() {
            if (pointCloud) {
                const box = new THREE.Box3().setFromObject(pointCloud);
                const center = box.getCenter(new THREE.Vector3());
                const size = box.getSize(new THREE.Vector3());
                const maxDim = Math.max(size.x, size.y, size.z);
                const fov = camera.fov * (Math.PI / 180);
                let cameraZ = Math.abs(maxDim / 2 / Math.tan(fov / 2));
                cameraZ *= 1.5;
                
                camera.position.set(center.x, center.y, center.z + cameraZ);
                camera.lookAt(center);
                controls.target.copy(center);
                controls.update();
            }
        }
        
        // Toggle wireframe mode
        function toggleWireframe() {
            if (pointCloud && pointCloud.material) {
                pointCloud.material.wireframe = !pointCloud.material.wireframe;
            }
        }
        
        // Parse LDS-01 data manually
        function parseLDSData() {
            const ldsInput = document.getElementById('ldsInput').value.trim();
            if (!ldsInput) {
                showMessage('Please enter LDS-01 data', 'error');
                return;
            }
            
            fetch('/parse-lds', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-json',
                },
                body: JSON.stringify({lds: ldsInput})
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
            
            // Update status
            document.getElementById('pointCount').textContent = allPoints.length;
            document.getElementById('lastUpdate').textContent = new Date().toLocaleTimeString();
        }
        
        // Clear all data
        function clearData() {
            allPoints = [];
            createPointCloud(); // Clear 3D visualization
            document.getElementById('ldsInput').value = '';
            showMessage('All data cleared', 'success');
        }
        
        // Load sample data
        function loadSampleData() {
            const sampleLDS = "r[359]=0.438000,r[358]=0.385000,r[357]=0.379000,r[356]=0.372000,r[355]=0.365000";
            document.getElementById('ldsInput').value = sampleLDS;
            showMessage('Sample LDS-01 data loaded. Click Parse Data to visualize.', 'success');
        }
        
        // Show message
        function showMessage(text, type) {
            const messageDiv = document.getElementById('message');
            messageDiv.innerHTML = '<div class="' + type + '">' + text + '</div>';
            setTimeout(() => {
                messageDiv.innerHTML = '';
            }, 5000);
        }
        
        // Initialize 3D scene when page loads
        window.onload = function() {
            init3DScene();
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

func handleParseLDS(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}

	var request struct {
		LDS string `json:"lds"`
	}

	if err := json.NewDecoder(r.Body).Decode(&request); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}

	points, err := ParseLDS01Line(request.LDS)
	if err != nil {
		response := map[string]interface{}{
			"success": false,
			"error":   err.Error(),
		}
		json.NewEncoder(w).Encode(response)
		return
	}

	// Add points
	allPoints = append(allPoints, points...)

	// Keep only last 5000 points
	if len(allPoints) > 5000 {
		allPoints = allPoints[len(allPoints)-5000:]
	}

	// Log packet info
	log.Printf("Parsed LDS-01 data: %d points", len(points))

	response := map[string]interface{}{
		"success": true,
		"points":  points,
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
	rawOutput = make([]byte, 0)

	// Set up HTTP routes
	http.HandleFunc("/", handleRoot)
	http.HandleFunc("/parse-lds", handleParseLDS)
	http.HandleFunc("/start-stream", handleStartStream)
	http.HandleFunc("/stop-stream", handleStopStream)
	http.HandleFunc("/get-points", handleGetPoints)
	http.HandleFunc("/get-raw-output", handleGetRawOutput)
	http.HandleFunc("/clear-raw-output", handleClearRawOutput)

	// Start server
	port := ":8080"
	log.Printf("Starting LDS-01 Lidar Data Visualizer on port %s", port)
	log.Printf("Open http://localhost%s in your web browser", port)
	log.Printf("Serial port: /dev/ttyACM0 at 115200 baud")
	log.Printf("Expected format: r[angle]=distance (e.g., r[359]=0.438000)")

	if err := http.ListenAndServe(port, nil); err != nil {
		log.Fatal("Failed to start server:", err)
	}
}
