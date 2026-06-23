# ============================================================
# USER CONFIGURATION
# Copy this file, fill in your values, and save as config.py
# DO NOT commit config.py to GitHub if it contains real paths/serials
# ============================================================

# ---- Paths ----
CAM_DLL_DIR = r"C:\path\to\Thorlabs_SDK\Native Toolkit\dlls\Native_64_lib"
KINESIS_DIR = r"C:\Program Files\Thorlabs\Kinesis"
SAVE_DIR    = r"D:\your\output\folder"

# ---- Camera ----
EXPOSURE_US      = 10000   # Exposure in microseconds
FRAME_TIMEOUT_S  = 3.0     # Max wait time for a frame (seconds)

# ---- Image Processing ----
P_LO  = 0.5    # Low percentile clip
P_HI  = 99.5   # High percentile clip
GAMMA = 0.85   # Gamma correction (<1 brightens midtones)

# ---- Motor (KIM101) ----
KIM_SERIAL      = "XXXXXXXX"  # Your KIM101 serial number (found in Kinesis GUI)
ROT_CHANNEL_NUM = 2           # Channel connected to rotation stage

# ---- Acquisition ----
JOG_STEP_SIZE  = 22     # Motor steps per increment
N_IMAGES       = 720    # Total images (720 = 0.5° resolution)
SETTLE_S       = 0.03   # Settle time after each motor move (seconds)
JOG_TIMEOUT_MS = 15000  # Motor jog timeout (milliseconds)
