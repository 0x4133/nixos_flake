# Lidar Data Visualizer

A Go program that parses lidar data packets and displays them in a live web-based chart.

## Features

- Parses 42-byte lidar data packets according to the LDS Basic Specification
- Validates packet checksums
- Extracts measurement points (angle, distance, intensity)
- Real-time visualization using Chart.js
- Web-based interface accessible via browser

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

### Running the Program

1. **Clone or download the project**
   ```bash
   cd /path/to/lidar
   ```

2. **Run the program**
   ```bash
   go run main.go
   ```

3. **Open your web browser**
   Navigate to: `http://localhost:8080`

## Using the Interface

1. **Enter Hex Data**: Paste your 42-byte hex string into the text area
2. **Parse Data**: Click "Parse Data" to process the hex string
3. **View Visualization**: See the lidar points plotted on the chart
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
- **Frontend**: HTML/JavaScript with Chart.js for visualization
- **Data Storage**: In-memory storage (last 1000 points)
- **Real-time Updates**: Chart updates immediately when new data is parsed

## Customization

- Modify the `maxPoints` variable in the code to change how many points are kept in memory
- Adjust the chart dimensions and styling in the HTML template
- Add additional validation or processing logic in the Go backend

## Troubleshooting

- **Port already in use**: Change the port number in the `main()` function
- **Chart not displaying**: Check browser console for JavaScript errors
- **Parsing errors**: Ensure your hex string is exactly 42 bytes (84 hex characters)
- **Checksum failures**: Verify the data integrity of your packets

## License

This project is open source and available under the MIT License. 