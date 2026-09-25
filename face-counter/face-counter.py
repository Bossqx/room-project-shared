#!/usr/bin/env python3
"""
face_count.py

Count the number of human faces in an image using OpenCV's Haar Cascade
frontal-face classifier.

Usage:
    python face_count.py --image path/to/photo.jpg
    python face_count.py --image path/to/photo.jpg --output annotated.jpg
    python face_count.py --image path/to/photo.jpg --scale-factor 1.05 --min-neighbors 6
    python face_count.py --webcam
    python face_count.py --webcam --camera-index 1

Exit codes:
    0 - success
    1 - input file not found / unreadable
    2 - cascade classifier failed to load
    3 - webcam could not be opened
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import dataclass
from pathlib import Path

import cv2
import paho.mqtt.client as mqtt

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DetectionParams:
    """Parameters controlling Haar Cascade face detection sensitivity."""

    scale_factor: float = 1.1      # how much the image size is reduced at each scale
    min_neighbors: int = 5         # how many neighbors each candidate rectangle needs
    min_size: tuple[int, int] = (30, 30)  # minimum possible face size (px)


def load_image(image_path: Path) -> "cv2.Mat":
    """Load an image from disk, raising a clear error if it can't be read."""
    if not image_path.is_file():
        raise FileNotFoundError(f"Image file not found: {image_path}")

    image = cv2.imread(str(image_path))
    if image is None:
        raise ValueError(
            f"Could not decode image: {image_path} "
            "(unsupported format or corrupted file)"
        )
    return image


def load_face_cascade() -> cv2.CascadeClassifier:
    """Load OpenCV's bundled frontal-face Haar Cascade classifier."""
    cascade_path = Path(cv2.data.haarcascades) / "haarcascade_frontalface_default.xml"
    classifier = cv2.CascadeClassifier(str(cascade_path))

    if classifier.empty():
        raise RuntimeError(f"Failed to load cascade classifier from {cascade_path}")
    return classifier


def count_faces(
    image: "cv2.Mat",
    classifier: cv2.CascadeClassifier,
    params: DetectionParams = DetectionParams(),
) -> list[tuple[int, int, int, int]]:
    """
    Detect faces in an image.

    Returns a list of bounding boxes as (x, y, width, height) tuples.
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = cv2.equalizeHist(gray)  # improves detection under uneven lighting

    faces = classifier.detectMultiScale(
        gray,
        scaleFactor=params.scale_factor,
        minNeighbors=params.min_neighbors,
        minSize=params.min_size,
    )
    return [tuple(face) for face in faces]


def draw_annotations(
    image: "cv2.Mat", faces: list[tuple[int, int, int, int]]
) -> "cv2.Mat":
    """Return a copy of the image with rectangles drawn around detected faces."""
    annotated = image.copy()
    for (x, y, w, h) in faces:
        cv2.rectangle(annotated, (x, y), (x + w, y + h), (0, 255, 0), 2)
    return annotated
 

def connect_mqtt(host: str, port: int) -> mqtt.Client | None:
    """Connect to the MQTT broker, returning None (and logging) on failure."""
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="face-counter")
    try:
        client.connect(host, port)
        client.loop_start()
        logger.info("Connected to MQTT broker at %s:%d", host, port)
        return client
    except OSError as exc:
        logger.warning("Could not connect to MQTT broker at %s:%d (%s) — continuing without publishing", host, port, exc)
        return None


def run_webcam(
    classifier: cv2.CascadeClassifier,
    params: DetectionParams,
    camera_index: int = 1,
    mqtt_host: str = "10.27.127.25",
    mqtt_port: int = 1883,
    mqtt_topic: str = "camera/face-count",
    display: bool = True,
) -> int:
    """
    Open a webcam feed and show a live face count overlaid on each frame.

    Whenever the count changes, publishes {"count": N} to mqtt_topic.
    If display is True, press 'q' or Esc in the video window to quit;
    if False, no window is shown and Ctrl+C stops the loop instead.
    """
    capture = cv2.VideoCapture(camera_index)
    if not capture.isOpened():
        logger.error("Could not open webcam at index %d", camera_index)
        return 3

    mqtt_client = connect_mqtt(mqtt_host, mqtt_port)
    last_published_count: int | None = None

    window_name = "Face Counter (press q to quit)"
    try:
        while True:
            ok, frame = capture.read()
            if not ok:
                logger.error("Failed to read frame from webcam")
                break

            faces = count_faces(frame, classifier, params)

            if mqtt_client is not None and len(faces) != last_published_count:
                last_published_count = len(faces)
                mqtt_client.publish(mqtt_topic, json.dumps({"count": last_published_count}))
                logger.info("Published count=%d to %s", last_published_count, mqtt_topic)

            if not display:
                continue

            annotated = draw_annotations(frame, faces)
            cv2.putText(
                annotated,
                f"Faces: {len(faces)}",
                (10, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                1.0,
                (0, 255, 0),
                2,
                cv2.LINE_AA,
            )

            cv2.imshow(window_name, annotated)

            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), 27):  # 'q' or Esc
                break
    except KeyboardInterrupt:
        logger.info("Interrupted, stopping.")
    finally:
        capture.release()
        cv2.destroyAllWindows()
        if mqtt_client is not None:
            mqtt_client.loop_stop()
            mqtt_client.disconnect()

    return 0


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Count human faces in an image using OpenCV Haar Cascades."
    )
    parser.add_argument(
        "--image", "-i", type=Path, default=None, help="Path to the input image."
    )
    parser.add_argument(
        "--webcam",
        action="store_true",
        help="Show a live face count from the webcam instead of processing a still image.",
    )
    parser.add_argument(
        "--camera-index",
        type=int,
        default=1,
        help="Webcam device index to use with --webcam (default: 1, the external webcam; "
        "use 0 for the built-in camera).",
    )
    parser.add_argument(
        "--mqtt-host",
        default="10.27.127.25",
        help="MQTT broker host to publish face counts to (default: 10.27.127.25).",
    )
    parser.add_argument(
        "--mqtt-port",
        type=int,
        default=1883,
        help="MQTT broker port (default: 1883).",
    )
    parser.add_argument(
        "--mqtt-topic",
        default="camera/face-count",
        help="MQTT topic to publish face counts to (default: camera/face-count).",
    )
    parser.add_argument(
        "--display",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Show the live video window with --webcam (default: on). "
        "Use --no-display to run headless (Ctrl+C to stop).",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=None,
        help="Optional path to save an annotated copy with faces boxed.",
    )
    parser.add_argument(
        "--scale-factor",
        type=float,
        default=1.1,
        help="Image pyramid scale factor (default: 1.1). Lower = more accurate, slower.",
    )
    parser.add_argument(
        "--min-neighbors",
        type=int,
        default=5,
        help="Minimum neighbor rectangles to retain a detection (default: 5). "
        "Higher = fewer false positives.",
    )
    parser.add_argument(
        "--min-size",
        type=int,
        nargs=2,
        default=(30, 30),
        metavar=("WIDTH", "HEIGHT"),
        help="Minimum face size in pixels (default: 30 30).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    if not args.webcam and args.image is None:
        logger.error("Provide --image PATH or --webcam.")
        return 1

    try:
        classifier = load_face_cascade()
    except RuntimeError as exc:
        logger.error(exc)
        return 2

    params = DetectionParams(
        scale_factor=args.scale_factor,
        min_neighbors=args.min_neighbors,
        min_size=tuple(args.min_size),
    )

    if args.webcam:
        return run_webcam(
            classifier,
            params,
            camera_index=args.camera_index,
            mqtt_host=args.mqtt_host,
            mqtt_port=args.mqtt_port,
            mqtt_topic=args.mqtt_topic,
            display=args.display,
        )

    try:
        image = load_image(args.image)
    except (FileNotFoundError, ValueError) as exc:
        logger.error(exc)
        return 1

    faces = count_faces(image, classifier, params)

    logger.info("Detected %d face(s) in %s", len(faces), args.image)
    for idx, (x, y, w, h) in enumerate(faces, start=1):
        logger.info("  Face %d: x=%d y=%d w=%d h=%d", idx, x, y, w, h)

    if args.output:
        annotated = draw_annotations(image, faces)
        cv2.imwrite(str(args.output), annotated)
        logger.info("Annotated image saved to %s", args.output)

    print(len(faces))  # machine-readable result on stdout
    return 0


if __name__ == "__main__":
    sys.exit(main())