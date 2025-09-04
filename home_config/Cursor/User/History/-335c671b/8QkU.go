package main

import (
	"encoding/hex"
	"fmt"
	"log"
	"math"
	"strconv"
	"strings"
	"time"

	"fyne.io/fyne/v2"
	"fyne.io/fyne/v2/app"
	"fyne.io/fyne/v2/canvas"
	"fyne.io/fyne/v2/container"
	"fyne.io/fyne/v2/widget"
)

// LidarPacket represents the 42-byte lidar data packet structure
type LidarPacket struct {
	Sync      byte     `json:"sync"`
	Degree   byte     `json:"degree"`
	RPM      uint16   `json:"rpm"`
	Data     []DataBlock `json:"data"`
	Checksum uint16   `json:"checksum"`
}

// DataBlock represents one of the six data blocks in the packet
type DataBlock struct {
	Intensity uint16 `json:"intensity"`
	Distance  uint16 `json:"distance"`
	Reserved  uint16 `json:"reserved"`
}

// LidarPoint represents a single measurement point
type LidarPoint struct {
	Angle      float64 `json:"angle"`
	Distance   float64 `json:"distance"`
	Intensity  uint16  `json:"intensity"`
	Timestamp  time.Time `json:"timestamp"`
}

// LidarVisualizer handles the visualization of lidar data
type LidarVisualizer struct {
	points     []LidarPoint
	maxPoints  int
	window     fyne.Window
	canvas     *canvas.Circle
	container  *fyne.Container
}

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
		Sync:    data[0],
		Degree:  data[1],
		RPM:     uint16(data[2]) | uint16(data[3])<<8, // Little endian
		Data:    make([]DataBlock, 6),
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

// NewLidarVisualizer creates a new lidar visualizer
func NewLidarVisualizer() *LidarVisualizer {
	return &LidarVisualizer{
		points:    make([]LidarPoint, 0),
		maxPoints: 1000, // Keep last 1000 points
	}
}

// AddPoints adds new points to the visualizer
func (lv *LidarVisualizer) AddPoints(points []LidarPoint) {
	lv.points = append(lv.points, points...)
	
	// Keep only the last maxPoints
	if len(lv.points) > lv.maxPoints {
		lv.points = lv.points[len(lv.points)-lv.maxPoints:]
	}
	
	// Trigger redraw
	lv.redraw()
}

// redraw redraws the visualization
func (lv *LidarVisualizer) redraw() {
	if lv.container != nil {
		lv.container.Refresh()
	}
}

// CreateVisualization creates the visualization UI
func (lv *LidarVisualizer) CreateVisualization() fyne.CanvasObject {
	// Create a simple text display for now
	// In a real implementation, you'd want to use a proper charting library
	infoLabel := widget.NewLabel("Lidar Data Visualization")
	infoLabel.TextStyle = fyne.TextStyle{Bold: true}
	
	// Create a container for the visualization
	lv.container = container.NewVBox(
		infoLabel,
		widget.NewLabel("Enter hex data below and press Parse"),
	)
	
	return lv.container
}

func main() {
	myApp := app.New()
	myWindow := myApp.NewWindow("Lidar Data Visualizer")
	
	visualizer := NewLidarVisualizer()
	
	// Create input field for hex data
	hexInput := widget.NewMultiLineEntry()
	hexInput.SetPlaceHolder("Enter 42-byte hex data here...")
	
	// Create parse button
	parseBtn := widget.NewButton("Parse Data", func() {
		hexStr := hexInput.Text
		if hexStr == "" {
			return
		}
		
		packet, err := ParseHexString(hexStr)
		if err != nil {
			log.Printf("Error parsing hex: %v", err)
			return
		}
		
		// Validate checksum
		if !packet.ValidateChecksum() {
			log.Printf("Warning: Checksum validation failed")
		}
		
		// Extract points
		points := packet.ExtractPoints()
		visualizer.AddPoints(points)
		
		// Display packet info
		log.Printf("Parsed packet - Degree: %d, RPM: %d, Points: %d", 
			packet.Degree, packet.RPM, len(points))
		
		for i, point := range points {
			log.Printf("Point %d: Angle=%.1f°, Distance=%.3fm, Intensity=%d", 
				i, point.Angle, point.Distance, point.Intensity)
		}
	})
	
	// Create clear button
	clearBtn := widget.NewButton("Clear Data", func() {
		visualizer.points = make([]LidarPoint, 0)
		visualizer.redraw()
		hexInput.SetText("")
	})
	
	// Create the main layout
	content := container.NewVBox(
		visualizer.CreateVisualization(),
		widget.NewLabel("Hex Input:"),
		hexInput,
		container.NewHBox(parseBtn, clearBtn),
	)
	
	myWindow.SetContent(content)
	myWindow.Resize(fyne.NewSize(800, 600))
	myWindow.ShowAndRun()
} 