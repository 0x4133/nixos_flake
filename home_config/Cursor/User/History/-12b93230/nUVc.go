package readmemory
package main

import (
	"bufio"
	"errors"
	"fmt"
	"io"
	"os"
	"path/filepath"
	"strconv"
	"strings"
	"unsafe"

	"golang.org/x/sys/unix"
)

const (
	FIBMAP       = 1 // legacy ioctl to map logical->physical blocks
	BLKSSZGET    = 0x1268
	O_LARGEFILE  = 0 // on 64-bit this is a no-op; kept for clarity
	SEEK_SET     = 0
	defaultSect  = 512
	readBufLimit = 1 << 20 // 1 MiB streaming buffer cap per chunk
)

type FileExtent struct {
	LogicalBlock  int
	PhysicalBlock int
	BlockCount    int
}

type FileCarver struct {
	devicePath string
	blockSize  int
	sectorSize int
}

func NewFileCarver(devicePath string, filePath string) (*FileCarver, error) {
	fc := &FileCarver{devicePath: devicePath, sectorSize: defaultSect}

	// 1) Get filesystem block size from the FILE (or its mountpoint), not from the block device
	var sfs unix.Statfs_t
	if err := unix.Statfs(filePath, &sfs); err != nil {
		return nil, fmt.Errorf("statfs(%s): %w", filePath, err)
	}
	fc.blockSize = int(sfs.Bsize)

	// 2) Try to detect device sector size via BLKSSZGET
	dev, err := os.Open(devicePath)
	if err != nil {
		return nil, fmt.Errorf("open device %s: %w", devicePath, err)
	}
	defer dev.Close()

	var sect int
	if _, _, errno := unix.Syscall(unix.SYS_IOCTL, dev.Fd(), BLKSSZGET, uintptr(unsafe.Pointer(&sect))); errno == 0 && sect > 0 {
		fc.sectorSize = sect
	}

	return fc, nil
}

func (fc *FileCarver) getFileBlocks(filePath string) ([]FileExtent, error) {
	f, err := os.Open(filePath)
	if err != nil {
		return nil, fmt.Errorf("open file: %w", err)
	}
	defer f.Close()

	st, err := f.Stat()
	if err != nil {
		return nil, fmt.Errorf("stat file: %w", err)
	}
	fileSize := st.Size()
	blocksNeeded := int((fileSize + int64(fc.blockSize) - 1) / int64(fc.blockSize))

	var extents []FileExtent
	var cur *FileExtent

	for l := 0; l < blocksNeeded; l++ {
		// ioctl(FIBMAP) takes an int *in/out*: in = logical block index; out = physical block number
		block := l
		_, _, errno := unix.Syscall(unix.SYS_IOCTL, f.Fd(), FIBMAP, uintptr(unsafe.Pointer(&block)))
		if errno != 0 {
			return nil, fmt.Errorf("FIBMAP failed at logical %d: %v", l, errno)
		}

		phys := block
		if phys == 0 {
			// hole/sparse: terminate current extent if any
			if cur != nil {
				extents = append(extents, *cur)
				cur = nil
			}
			continue
		}

		if cur != nil && cur.PhysicalBlock+cur.BlockCount == phys {
			cur.BlockCount++
		} else {
			if cur != nil {
				extents = append(extents, *cur)
			}
			cur = &FileExtent{
				LogicalBlock:  l,
				PhysicalBlock: phys,
				BlockCount:    1,
			}
		}
	}
	if cur != nil {
		extents = append(extents, *cur)
	}
	return extents, nil
}

func (fc *FileCarver) carveFile(filePath, outputPath string) error {
	// Sanity: file exists
	st, err := os.Stat(filePath)
	if err != nil {
		return fmt.Errorf("stat target: %w", err)
	}
	origSize := st.Size()

	extents, err := fc.getFileBlocks(filePath)
	if err != nil {
		return fmt.Errorf("get extents: %w", err)
	}
	if len(extents) == 0 {
		return errors.New("no extents found (file may be entirely sparse?)")
	}

	// Open device read-only, refuse to follow symlinks accidentally
	dev, err := os.OpenFile(fc.devicePath, os.O_RDONLY|O_LARGEFILE, 0)
	if err != nil {
		return fmt.Errorf("open device: %w", err)
	}
	defer dev.Close()

	out, err := os.Create(outputPath)
	if err != nil {
		return fmt.Errorf("create output: %w", err)
	}
	defer out.Close()

	fmt.Printf("Carving from %d extents (orig size: %d bytes) using fs block: %d, sector: %d\n",
		len(extents), origSize, fc.blockSize, fc.sectorSize)

	var written int64 = 0
	for i, ex := range extents {
		// Physical byte offset = physical block * filesystem block size
		offset := int64(ex.PhysicalBlock) * int64(fc.blockSize)
		if _, err := dev.Seek(offset, SEEK_SET); err != nil {
			return fmt.Errorf("seek device @%d (extent %d): %w", offset, i+1, err)
		}

		extentBytes := int64(ex.BlockCount) * int64(fc.blockSize)
		remain := origSize - written
		if remain <= 0 {
			break
		}
		if extentBytes > remain {
			extentBytes = remain
		}

		// Stream in chunks to avoid huge single allocations
		var copied int64 = 0
		bufSize := fc.blockSize
		if bufSize > readBufLimit {
			bufSize = readBufLimit
		}
		buf := make([]byte, bufSize)

		for copied < extentBytes {
			want := int(extentBytes - copied)
			if want > len(buf) {
				want = len(buf)
			}
			n, rerr := dev.Read(buf[:want])
			if n > 0 {
				if _, werr := out.Write(buf[:n]); werr != nil {
					return fmt.Errorf("write output: %w", werr)
				}
				copied += int64(n)
				written += int64(n)
			}
			if rerr != nil {
				if rerr == io.EOF && copied == extentBytes {
					break
				}
				return fmt.Errorf("read device (extent %d): %w", i+1, rerr)
			}
		}
		fmt.Printf("  Extent %d: L=%d P=%d Blocks=%d -> %d bytes\n",
			i+1, ex.LogicalBlock, ex.PhysicalBlock, ex.BlockCount, copied)
	}

	// Truncate just in case we wrote exactly, but it’s a no-op otherwise.
	if err := out.Truncate(origSize); err != nil {
		return fmt.Errorf("truncate output: %w", err)
	}

	fmt.Printf("Done. Wrote %d bytes to %s\n", written, outputPath)
	return nil
}

func findDeviceForFile(filePath string) (string, string, error) {
	abs, err := filepath.Abs(filePath)
	if err != nil {
		return "", "", err
	}
	// Read /proc/self/mountinfo (format is stable and includes mount root + device)
	f, err := os.Open("/proc/self/mountinfo")
	if err != nil {
		return "", "", err
	}
	defer f.Close()

	type cand struct {
		mountPoint string
		source     string
	}
	var best cand
	var bestLen int

	sc := bufio.NewScanner(f)
	for sc.Scan() {
		// Fields (simplified):
		// 1:id 2:parent 3:major:minor 4:root 5:mountPoint 6:opts - 7:optional...  -  target: fsType source superOpts
		line := sc.Text()
		parts := strings.Split(line, " - ")
		if len(parts) != 2 {
			continue
		}
		left := strings.Fields(parts[0])
		right := strings.Fields(parts[1])
		if len(left) < 5 || len(right) < 3 {
			continue
		}
		mountPoint := left[4]
		fsType := right[0]
		source := right[1]

		if fsType != "ext4" {
			continue
		}
		if strings.HasPrefix(abs, mountPoint) && len(mountPoint) > bestLen {
			best = cand{mountPoint: mountPoint, source: source}
			bestLen = len(mountPoint)
		}
	}
	if bestLen == 0 {
		return "", "", fmt.Errorf("no ext4 mount found for %s", abs)
	}
	// source is typically /dev/… (block device)
	if !strings.HasPrefix(best.source, "/dev/") {
		return "", "", fmt.Errorf("mount source for %s is not a block device: %s", abs, best.source)
	}
	return best.source, best.mountPoint, nil
}

func requireRoot() {
	if os.Geteuid() != 0 {
		fmt.Fprintln(os.Stderr, "This program must run as root to read block devices.")
		os.Exit(1)
	}
}

func main() {
	if len(os.Args) < 3 {
		fmt.Fprintf(os.Stderr, "Usage: %s <file-path> <output-path> [device-path]\n", os.Args[0])
		os.Exit(1)
	}
	filePath := os.Args[1]
	outputPath := os.Args[2]

	// Sanity
	if _, err := os.Stat(filePath); err != nil {
		fmt.Fprintf(os.Stderr, "Target file stat failed: %v\n", err)
		os.Exit(1)
	}

	devicePath := ""
	if len(os.Args) >= 4 {
		devicePath = os.Args[3]
	} else {
		dev, mp, err := findDeviceForFile(filePath)
		if err != nil {
			fmt.Fprintf(os.Stderr, "Auto-detect device failed: %v\n", err)
			os.Exit(1)
		}
		fmt.Printf("Detected device %s for mount %s\n", dev, mp)
		devicePath = dev
	}

	requireRoot()

	carver, err := NewFileCarver(devicePath, filePath)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Init carver failed: %v\n", err)
		os.Exit(1)
	}
	if err := carver.carveFile(filePath, outputPath); err != nil {
		fmt.Fprintf(os.Stderr, "Carve failed: %v\n", err)
		os.Exit(1)
	}
}
