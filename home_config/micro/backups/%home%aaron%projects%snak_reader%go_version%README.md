# Go OCR Webcam Reader

A high-performance OCR webcam application written in Go, optimized for NixOS and Wayland.
Nemeses-Idealize-Relight-Wobbly-Plated-Freebie
## Features

- **High Performance**: Native Go implementation with optimized OpenCV bindings
- **Real-time OCR**: Fast text recognition using Tesseract
- **Interactive Controls**: Trackbars for real-time parameter adjustment
- **ROI Processing**: Only processes center region for speed
- **Debug Mode**: Toggle to see preprocessing results
- **Wayland Support**: Native support for modern Linux desktop environments

## Setup

### NixOS with Wayland

1. Enter the Nix shell:
```bash
cd go_version
nix-shell
```

2. Initialize Go modules:
```bash
go mod tidy
```

3. Run the application:
```bash
go run main.go
```

Or build and run:
```bash
go build -o snak_reader main.go
./snak_reader
```

## Controls

### Trackbars
- **Block Size** (3-25): Adaptive threshold block size
- **C Value** (0-20): Threshold sensitivity
- **Laplacian %** (0-100): Edge enhancement strength
- **Blur** (1-9): Noise reduction level
- **Debug Mode** (0/1): Toggle preprocessing visualization

### Keyboard
- **'q'** or **ESC**: Quit application

## Performance Optimizations

1. **Native Go**: Compiled language for better performance
2. **ROI Processing**: Only processes center 50% of frame
3. **Image Scaling**: Reduces image size by 30% before OCR
4. **Configurable Processing**: Adjust OCR frequency (default: 2 seconds)
5. **Fast Tesseract Config**: Optimized OCR settings
6. **Efficient Memory Management**: Proper cleanup of OpenCV Mats

## Architecture

- **gocv.io/x/gocv**: Go bindings for OpenCV
- **gosseract**: Go bindings for Tesseract OCR
- **ROI-based processing**: Reduces computational load
- **Threaded design**: Non-blocking UI updates

## Requirements

- Go 1.21+
- OpenCV 4.x
- Tesseract OCR
- Wayland/X11 display server
- Webcam device

## Troubleshooting

### Build Issues
- Ensure `CGO_ENABLED=1`
- Check `PKG_CONFIG_PATH` includes OpenCV and Tesseract

### Display Issues
- For Wayland: Ensure `XDG_SESSION_TYPE=wayland`
- For X11 fallback: Set `DISPLAY` environment variable

### Performance Issues
- Increase processing interval in code
- Reduce ROI size
- Lower image scaling factor