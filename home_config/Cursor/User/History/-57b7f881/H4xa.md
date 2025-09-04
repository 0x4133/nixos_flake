# Lidar Data Visualizer

A Go program that parses lidar data packets and displays them in a live web-based chart with real-time serial port streaming.

## Features

- **Real-time Serial Streaming**: Streams data directly from `/dev/ttyACM0` at 115200 baud
- **Raw Output Display**: View raw serial port data in hex format for debugging
- **Manual Hex Input**: Parse individual hex strings for testing and debugging
- **Live Visualization**: Real-time chart updates using Chart.js
- **Packet Validation**: Validates packet checksums for data integrity
- **42-byte Packet Parsing**: Follows the LDS Basic Specification exactly
- **Web Interface**: Accessible via any web browser

## Data Format

Each lidar packet contains:
- **Sync byte**: 0xA0~0xDB for synchronization
- **Angle Index**: 0-60 for the base angle
- **RPM**: 16-bit rotation speed
- **6 Data Blocks**: Each containing intensity, distance, and reserved fields
- **Checksum**: 16-bit validation value

### Angle Calculation
```
angle = angle_index × 6 + angle_offset
```

### Checksum Validation
```
checksum = 0xFF - (sum of first 40 bytes)
```

## Installation & Usage

### Prerequisites
- Go 1.21 or later
- Access to `/dev/ttyACM0` (usually requires being in the `dialout` group)

### Setup Serial Port Access
```bash
# Add your user to the dialout group (Linux)
sudo usermod -a -G dialout $USER

# Or temporarily change permissions
sudo chmod 666 /dev/ttyACM0
```

### Running the Program

1. **Clone or download the project**
   ```bash
   cd /path/to/lidar
   ```

2. **Install dependencies**
   ```bash
   go mod tidy
   ```

3. **Run the program**
   ```bash
   go run main.go
   # Or build and run
   go build -o lidar main.go
   ./lidar
   ```

4. **Open your web browser**
   Navigate to: `http://localhost:8080`

## Using the Interface

### Serial Port Streaming
1. **Connect your lidar device** to `/dev/ttyACM0`
2. **Click "Start Streaming"** to begin real-time data collection
3. **Monitor the chart** as it updates with live data
4. **Click "Stop Streaming"** to halt data collection

### Raw Output Control
1. **Start streaming** to capture raw serial data
2. **Click "Show Raw Output"** to display the raw hex data in a readable format
3. **Monitor the buffer size** shown in the status indicator
4. **Click "Clear Raw Output"** to reset the raw data buffer
5. **Use for debugging** to verify data integrity and troubleshoot issues

### Manual Hex Input
1. **Enter Hex Data**: Paste your 42-byte hex string into the text area
2. **Parse Data**: Click "Parse Data" to process the hex string
3. **View Results**: See the parsed data points on the chart
4. **Sample Data**: Use "Load Sample Data" to see an example
5. **Clear Data**: Use "Clear All Data" to reset the visualization

## Example Hex Data

Here's a sample 42-byte packet:
```
A1C30BB0228B00000000B0228B00000000B0228B00000000B0228B00000000B0228B00000000B0228B000000001313
```

This represents:
- Sync: A1
- Angle Index: C3 (195)
- RPM: 0BC3 (3011)
- 6 data blocks with distance measurements
- Checksum: 1313

## Technical Details

- **Server**: Built-in Go HTTP server on port 8080
- **Serial Port**: `/dev/ttyACM0` at 115200 baud, 8N1
- **Frontend**: HTML/JavaScript with Chart.js for visualization
- **Data Storage**: In-memory storage (last 1000 points)
- **Raw Output Buffer**: Captures last 10KB of raw serial data
- **Real-time Updates**: Chart updates every 100ms during streaming
- **Packet Parsing**: Automatic sync byte detection and 42-byte packet assembly

## Serial Port Configuration

The program automatically configures the serial port with:
- **Baud Rate**: 115200
- **Data Bits**: 8
- **Parity**: None
- **Stop Bits**: 1
- **Flow Control**: None

## Troubleshooting

### Serial Port Issues
- **Permission denied**: Ensure your user is in the `dialout` group or has read/write access to `/dev/ttyACM0`
- **Device not found**: Check if the device is connected and the port name is correct
- **No data**: Verify the lidar device is powered and transmitting data

### General Issues
- **Port already in use**: Change the port number in the `main()` function
- **Chart not displaying**: Check browser console for JavaScript errors
- **Parsing errors**: Ensure your hex string is exactly 42 bytes (84 hex characters)
- **Checksum failures**: Verify the data integrity of your packets

### Performance
- **Slow updates**: The chart updates every 100ms during streaming for smooth visualization
- **Memory usage**: Only the last 1000 points are kept in memory to prevent excessive memory usage

## Customization

- Modify the `maxPoints` variable to change how many points are kept in memory
- Adjust the chart update frequency by changing the `setInterval` value in the JavaScript
- Change the serial port settings in the `StartSerialStream()` function
- Modify the chart dimensions and styling in the HTML template

## License

This project is open source and available under the MIT License. 