"""
Interactive template capture tool.

Pulls a screenshot from the connected emulator, lets you crop a region by
clicking and dragging, then saves it as a PNG in bot/templates/.

Usage:
    python scripts/capture_template.py
    python scripts/capture_template.py --host 127.0.0.1 --port 5555

Requires cv2 with GUI support (opencv-python, not opencv-python-headless).
Run this on your DEV machine, not inside the bot container.
"""

import argparse
import subprocess
import sys
from pathlib import Path

try:
    import cv2
except ImportError:
    print("Install opencv-python: pip install opencv-python")
    sys.exit(1)


def pull_screenshot(host: str, port: int, out: Path) -> bool:
    subprocess.run(["adb", "connect", f"{host}:{port}"], capture_output=True)
    result = subprocess.run(
        ["adb", "-s", f"{host}:{port}", "exec-out", "screencap", "-p"],
        capture_output=True,
    )
    if result.returncode != 0:
        print(f"adb screencap failed: {result.stderr.decode(errors='ignore')}")
        return False
    out.write_bytes(result.stdout)
    return True


def crop_interactive(img_path: Path, out_dir: Path):
    img = cv2.imread(str(img_path))
    if img is None:
        print(f"Could not read {img_path}")
        return

    # Resize for screen if too large
    h, w = img.shape[:2]
    scale = min(1.0, 900 / max(h, w))
    display = cv2.resize(img, None, fx=scale, fy=scale) if scale < 1 else img.copy()

    print("Drag to select region. Press ENTER or SPACE to confirm. ESC to cancel.")
    roi = cv2.selectROI("capture", display, showCrosshair=True, fromCenter=False)
    cv2.destroyAllWindows()

    if roi == (0, 0, 0, 0):
        print("Cancelled.")
        return

    x, y, w_roi, h_roi = roi
    # Scale back to original
    x, y, w_roi, h_roi = [int(v / scale) for v in (x, y, w_roi, h_roi)]
    crop = img[y:y + h_roi, x:x + w_roi]

    name = input("Template name (no extension): ").strip()
    if not name:
        print("No name given - skipped.")
        return
    out_path = out_dir / f"{name}.png"
    cv2.imwrite(str(out_path), crop)
    print(f"Saved {out_path} ({w_roi}x{h_roi})")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=5555)
    ap.add_argument("--out", default="bot/templates")
    args = ap.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    tmp = Path(".last_screenshot.png")
    if not pull_screenshot(args.host, args.port, tmp):
        sys.exit(1)
    crop_interactive(tmp, out_dir)


if __name__ == "__main__":
    main()
