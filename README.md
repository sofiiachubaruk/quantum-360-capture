# 360° Automated Image Capture for Quantum Sensing Dataset Collection

It is the first stage of a four-stage pipeline:

**`quantum-360-capture`** (this repo) → [`microscopy-image-preprocessing-pipeline`](https://github.com/sofiiachubaruk/microscopy-image-preprocessing-pipeline) (data prep) → [`microscopy-image-restoration`](https://github.com/sofiiachubaruk/microscopy-image-restoration) (NAFNet) → [`quantum-360-reconstruction`](https://github.com/sofiiachubaruk/quantum-360-reconstruction) (3D + evaluation)

An automated image acquisition pipeline for collecting ML-ready datasets in quantum sensing research. The system synchronizes a **Thorlabs scientific camera** with a **KIM101 piezoelectric motor controller** to capture a full 360° image sequence with precise angular control : purpose-built for training machine learning models on quantum optical data.

---

## Overview

This script automates the capture of `N` images at evenly spaced angular positions around a full rotation. Each image is acquired, processed from 16-bit to 8-bit with perceptually accurate tone mapping, and saved as a TIFF file — ready for use in ML pipelines.

**Key capabilities:**
- Hardware-synchronized camera + motor control in a single script
- Configurable exposure, step size, settle time, and frame count
- 16-bit → 8-bit conversion with percentile clipping and gamma correction
- Graceful cleanup and error handling for reliable lab use

---

## Hardware Requirements

| Component | Model |
|-----------|-------|
| Scientific Camera | Thorlabs TSI-compatible camera |
| Motor Controller | Thorlabs KIM101 (piezoelectric inertial) |
| OS | Windows 10/11, 64-bit |

---

## Software Dependencies

```bash
pip install numpy imageio pythonnet
```

You also need:
- [Thorlabs Scientific Camera SDK](https://www.thorlabs.com/software_pages/ViewSoftwarePage.cfm?Code=ThorCam) (Native 64-bit DLL + `thorlabs_tsi_sdk` Python package)
- [Thorlabs Kinesis](https://www.thorlabs.com/newgrouppage9.cfm?objectgroup_id=10285) (for KIM101 .NET libraries)

---

## Configuration

Before running, edit the constants near the top of `360caption.py`:

```python
# Paths — update these to match your system
CAM_DLL_DIR  = r"C:\...\SDK\Native Toolkit\dlls\Native_64_lib"
KINESIS_DIR  = r"C:\Program Files\Thorlabs\Kinesis"
SAVE_DIR     = r"D:\your\output\folder"

# Motor
KIM_SERIAL      = "XXXXXXXX"   # Your KIM101 serial number (found in Kinesis GUI)
ROT_CHANNEL_NUM = 2            # Channel connected to your rotation stage
JOG_STEP_SIZE   = 22          # Steps per increment — tune for your stage

# Acquisition
N_IMAGES    = 720              # Number of images (720 → 0.5° resolution)
EXPOSURE_US = 10000            # Camera exposure in microseconds
SETTLE_S    = 0.03             # Settle time after each motor step (seconds)
```

### Motor Channel Reference

| Channel | Increase | Decrease |
|---------|----------|----------|
| 1 | Right | Left |
| 2 | Rotate CW | Rotate CCW |
| 3 | Toward | Away |
| 4 | Up | Down |

---

## Usage

> **Important:** Close Thorlabs ThorCam and Kinesis GUI before running — they will conflict with the SDK.

```bash
python 360caption.py
```

Images are saved as `angle_000.tiff`, `angle_001.tiff`, ... in your configured `SAVE_DIR`.

---

## Image Processing Pipeline

Raw 16-bit frames go through the following before saving:

1. **Percentile clipping** — clips at P_LO / P_HI (default 0.5% / 99.5%) to remove hot pixels and background noise
2. **Normalization** — maps the clipped range to [0, 1]
3. **Gamma correction** — applies γ = 0.85 to brighten midtones (mimics scientific viewer display)
4. **8-bit conversion** — scales to [0, 255] and saves as TIFF

This produces visually consistent, ML-friendly grayscale images regardless of per-session lighting variation.

---

## Dataset Structure

```
SAVE_DIR/
├── angle_000.tiff
├── angle_001.tiff
├── ...
└── angle_719.tiff
```

Each file corresponds to a 0.5° rotation increment (for N=720), giving full azimuthal coverage of the sample.

---

## Project Context

This tool was developed as part of quantum sensing research to automate the collection of structured optical datasets. The resulting image sequences are intended for training and evaluating machine learning models on quantum optical phenomena, where consistent angular sampling and image quality are critical for model generalization.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `No cameras found` | Close ThorCam GUI; replug camera USB |
| `KIM101 not found` | Close Kinesis GUI; replug USB/power; verify serial number |
| `Timed out waiting for frame` | Increase `FRAME_TIMEOUT_S`; check exposure isn't too long |
| SDK error 1004 | Harmless Spyder IDE cleanup artifact — safe to ignore |
| DLL load error | Verify `CAM_DLL_DIR` path and that you're using 64-bit Python |

---

## License

MIT License — free to use, modify, and distribute with attribution.
