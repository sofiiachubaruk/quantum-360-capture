import os, sys, time, platform, ctypes, gc
import numpy as np
import imageio.v3 as iio

from config import (
    CAM_DLL_DIR, KINESIS_DIR, SAVE_DIR,
    EXPOSURE_US, FRAME_TIMEOUT_S,
    P_LO, P_HI, GAMMA,
    KIM_SERIAL, ROT_CHANNEL_NUM,
    JOG_STEP_SIZE, N_IMAGES, SETTLE_S, JOG_TIMEOUT_MS,
)

# ============================================================
# CAMERA DLL FIX
# Ensures Python can find and load camera DLL properly
# ============================================================
assert platform.architecture()[0] == "64bit", "You are not running 64-bit Python."

CAM_DLL_FULL = os.path.join(CAM_DLL_DIR, "thorlabs_tsi_camera_sdk.dll")

# Add DLL directory so Python can load it
os.environ["PATH"] = CAM_DLL_DIR + os.pathsep + os.environ.get("PATH", "")
os.add_dll_directory(CAM_DLL_DIR)
ctypes.WinDLL(CAM_DLL_FULL)

# Import camera SDK after DLL is loaded
from thorlabs_tsi_sdk.tl_camera import TLCameraSDK, TLCameraError

os.makedirs(SAVE_DIR, exist_ok=True)

# ============================================================

def acquire_one_frame(cam):
    """
    Trigger the camera and retrieve ONE frame.
    Waits until a frame is available or times out.
    Returns a 2D numpy array (image).
    """
    cam.issue_software_trigger()

    t0 = time.time()
    frame = cam.get_pending_frame_or_null()

    # Wait until frame arrives
    while frame is None:
        if time.time() - t0 > FRAME_TIMEOUT_S:
            raise RuntimeError("Timed out waiting for camera frame.")
        time.sleep(0.005)
        frame = cam.get_pending_frame_or_null()

    # Convert buffer to numpy array
    buf = np.array(frame.image_buffer, copy=True)

    # If already 2D => return directly
    if buf.ndim == 2:
        return buf

    # Otherwise reshape manually
    h = int(cam.image_height_pixels)
    w = int(cam.image_width_pixels)
    return buf.reshape(h, w)


def to_uint8_leftlook(img16: np.ndarray) -> np.ndarray:
    """
    Convert 16-bit image to 8-bit with auto contrast.
    This mimics the "viewer" look (NOT physical intensity).
    """
    img = img16.astype(np.float32)

    # Compute percentile-based scaling
    lo = np.percentile(img, P_LO)
    hi = np.percentile(img, P_HI)

    # Avoid division issues
    if hi <= lo:
        return np.zeros(img.shape, dtype=np.uint8)

    # Normalize to [0,1]
    x = (img - lo) / (hi - lo)
    x = np.clip(x, 0, 1)

    # Apply Gamma correction
    x = x ** GAMMA

    # Convert to 8-bit
    return (x * 255.0).astype(np.uint8)


def safe_close_camera(cam):
    """
    Safely shut down camera without crashing Python.
    """
    try:
        cam.disarm()
    except Exception:
        pass
    if hasattr(cam, "dispose"):
        try:
            cam.dispose()
            return
        except Exception:
            pass
    try:
        cam.close()
    except Exception:
        pass


def safe_dispose_sdk(sdk):
    """
    Cleanly dispose SDK.
    Ignores known harmless error (1004 in Spyder).
    """
    try:
        sdk.dispose()
    except TLCameraError as e:
        if "1004" in str(e):
            print(" Ignoring SDK close error 1004 (Spyder cleanup issue).")
        else:
            raise


def connect_kim101():
    """
    Connect to KIM101 motor controller and configure jog parameters.
    Returns device + channel.
    """
    import clr
    import System

    # Add Kinesis path
    sys.path.append(KINESIS_DIR)
    os.environ["PATH"] = KINESIS_DIR + os.pathsep + os.environ.get("PATH", "")
    os.add_dll_directory(KINESIS_DIR)

    # Load required .NET libraries
    clr.AddReference("Thorlabs.MotionControl.DeviceManagerCLI")
    clr.AddReference("Thorlabs.MotionControl.GenericMotorCLI")
    clr.AddReference("Thorlabs.MotionControl.KCube.InertialMotorCLI")

    from Thorlabs.MotionControl.DeviceManagerCLI import DeviceManagerCLI
    from Thorlabs.MotionControl.KCube.InertialMotorCLI import (
        KCubeInertialMotor,
        InertialMotorStatus,
        InertialMotorJogDirection,
    )

    # Detect devices
    DeviceManagerCLI.BuildDeviceList()
    time.sleep(0.5)
    devices = list(DeviceManagerCLI.GetDeviceList())
    print("Kinesis sees devices:", devices)
    if KIM_SERIAL not in devices:
        raise RuntimeError(f"KIM101 {KIM_SERIAL} not found. Close Kinesis GUI and replug USB/power.")

    # Connect
    dev = KCubeInertialMotor.CreateKCubeInertialMotor(KIM_SERIAL)
    dev.Connect(KIM_SERIAL)
    dev.WaitForSettingsInitialized(5000)
    dev.StartPolling(250)
    time.sleep(0.5)
    dev.EnableDevice()
    time.sleep(0.5)

    # Select channel
    ch = getattr(InertialMotorStatus.MotorChannels, f"Channel{ROT_CHANNEL_NUM}")
    dev.EnableChannel(ch)
    time.sleep(0.2)

    # Configure jog parameters
    dev.RequestJogParameters(ch)
    time.sleep(0.2)
    jp = dev.GetJogParameters(ch)
    jp.JogStepFwd = System.Int32(JOG_STEP_SIZE)
    jp.JogStepRev = System.Int32(JOG_STEP_SIZE)
    jp.JogAcceleration = System.Int32(1000)
    dev.SetJogParameters(ch, jp)
    time.sleep(0.2)

    print(f" KIM101 connected. ROT Channel{ROT_CHANNEL_NUM}. JogStep={JOG_STEP_SIZE}")
    return dev, ch, InertialMotorJogDirection, System


def rotate_cw_one_jog(dev, ch, JogDirEnum, SystemNS):
    """
    Rotate motor one step clockwise.
    """
    dev.Jog(ch, JogDirEnum.Increase, SystemNS.Int32(JOG_TIMEOUT_MS))  # CW
    time.sleep(SETTLE_S)


def main():
    sdk = None
    cam = None
    dev = None
    rot_ch = None

    try:
        # ---- Camera Setup ----
        sdk = TLCameraSDK()
        serials = sdk.discover_available_cameras()
        if not serials:
            raise RuntimeError("No cameras found. Close ThorCam and try again.")

        cam = sdk.open_camera(serials[0])

        # Reset state
        try:
            cam.disarm()
        except Exception:
            pass

        cam.exposure_time_us = int(EXPOSURE_US)
        cam.frames_per_trigger_zero_for_unlimited = 1
        cam.arm(10)

        print(f" Camera connected: {serials[0]}")
        print(f" Exposure: {EXPOSURE_US} us")
        print(f" Saving to: {SAVE_DIR}")

        # ---- Motor Setup ----
        dev, rot_ch, JogDirEnum, SystemNS = connect_kim101()

        # ---- Capture (Main loop) ----
        for k in range(N_IMAGES):
            print(f"[{k+1:03d}/{N_IMAGES}] capture")

            # Capture image
            img16 = acquire_one_frame(cam)
            # Convert to 8-bit
            img8 = to_uint8_leftlook(img16)

            # Save image
            fname = os.path.join(SAVE_DIR, f"angle_{k:03d}.tiff")
            iio.imwrite(fname, img8)
            print(" saved:", fname)

            # Rotate motor (except after last image)
            if k != N_IMAGES - 1:
                rotate_cw_one_jog(dev, rot_ch, JogDirEnum, SystemNS)

        print(" Done.")

    finally:
        # -------------- Cleanup ----------------
        if cam is not None:
            safe_close_camera(cam)
        cam = None
        gc.collect()
        time.sleep(0.2)

        if sdk is not None:
            safe_dispose_sdk(sdk)

        if dev is not None and rot_ch is not None:
            try: dev.Stop(rot_ch)
            except Exception: pass
            try: dev.StopPolling()
            except Exception: pass
            try: dev.Disconnect()
            except Exception: pass

        print("Cleanup done.")


if __name__ == "__main__":
    main()
