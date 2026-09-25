#!/usr/bin/env python3
"""
person-counter.py

Count the number of people in an image or webcam feed using a YOLO
object-detection model (Ultralytics), filtered to the COCO "person" class.

Usage:
    python person-counter.py --image path/to/photo.jpg
    python person-counter.py --image path/to/photo.jpg --output annotated.jpg
    python person-counter.py --image path/to/photo.jpg --confidence 0.4
    python person-counter.py --webcam
    python person-counter.py --webcam --camera-index 1
    python person-counter.py --webcam --model yolov8s.pt

Exit codes:
    0 - success
    1 - input file not found / unreadable
    2 - model failed to load
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
from ultralytics import YOLO

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

COCO_PERSON_CLASS_ID = 0
DEFAULT_CONFIG_PATH = Path(__file__).resolve().parent / "config.json"


@dataclass(frozen=True)
class DetectionParams:
    """Parameters controlling YOLO person detection sensitivity."""

    confidence: float = 0.5  # minimum detection confidence to keep a box
    iou: float = 0.45        # IoU threshold used for NMS


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


def load_config(config_path: Path) -> dict:
    """Load config.json, returning {} (and logging) if missing or invalid."""
    if not config_path.is_file():
        logger.warning("Config file not found: %s — proceeding without it", config_path)
        return {}

    try:
        return json.loads(config_path.read_text())
    except json.JSONDecodeError as exc:
        logger.warning("Could not parse config file %s (%s) — proceeding without it", config_path, exc)
        return {}


def load_model(weights: str) -> YOLO:
    """Load a YOLO model, downloading pretrained weights on first use."""
    try:
        return YOLO(weights)
    except Exception as exc:  # ultralytics raises plain Exception on bad weights
        raise RuntimeError(f"Failed to load YOLO model '{weights}': {exc}") from exc


def count_persons(
    image: "cv2.Mat",
    model: YOLO,
    params: DetectionParams = DetectionParams(),
) -> list[tuple[int, int, int, int]]:
    """
    Detect people in an image.

    Returns a list of bounding boxes as (x, y, width, height) tuples.
    """
    results = model.predict(
        image,
        classes=[COCO_PERSON_CLASS_ID],
        conf=params.confidence,
        iou=params.iou,
        verbose=False,
    )

    boxes: list[tuple[int, int, int, int]] = []
    for box in results[0].boxes:
        x1, y1, x2, y2 = box.xyxy[0].tolist()
        boxes.append((int(x1), int(y1), int(x2 - x1), int(y2 - y1)))
    return boxes


def draw_annotations(
    image: "cv2.Mat", persons: list[tuple[int, int, int, int]]
) -> "cv2.Mat":
    """Return a copy of the image with rectangles drawn around detected people."""
    annotated = image.copy()
    for (x, y, w, h) in persons:
        cv2.rectangle(annotated, (x, y), (x + w, y + h), (0, 255, 0), 2)
    return annotated


def connect_mqtt(host: str, port: int) -> mqtt.Client | None:
    """Connect to the MQTT broker, returning None (and logging) on failure."""
    client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="person-counter")
    try:
        client.connect(host, port)
        client.loop_start()
        logger.info("Connected to MQTT broker at %s:%d", host, port)
        return client
    except OSError as exc:
        logger.warning("Could not connect to MQTT broker at %s:%d (%s) — continuing without publishing", host, port, exc)
        return None


def run_webcam(
    model: YOLO,
    params: DetectionParams,
    camera_index: int = 1,
    mqtt_host: str = "10.27.127.25",
    mqtt_port: int = 1883,
    mqtt_topic: str = "camera/person-count",
    room_no: str | None = None,
    display: bool = True,
) -> int:
    """
    Open a webcam feed and show a live person count overlaid on each frame.

    Whenever the count changes, publishes {"room_no": room_no, "count": N} to mqtt_topic.
    If display is True, press 'q' or Esc in the video window to quit;
    if False, no window is shown and Ctrl+C stops the loop instead.
    """
    capture = cv2.VideoCapture(camera_index)
    if not capture.isOpened():
        logger.error("Could not open webcam at index %d", camera_index)
        return 3

    mqtt_client = connect_mqtt(mqtt_host, mqtt_port)
    last_published_count: int | None = None

    window_name = "Person Counter (press q to quit)"
    if display:
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(window_name, 1280, 720)
    try:
        while True:
            ok, frame = capture.read()
            if not ok:
                logger.error("Failed to read frame from webcam")
                break

            persons = count_persons(frame, model, params)

            if mqtt_client is not None and len(persons) != last_published_count:
                last_published_count = len(persons)
                payload = json.dumps({"room_no": room_no, "count": last_published_count})
                mqtt_client.publish(mqtt_topic, payload)
                logger.info("Published room_no=%s count=%d to %s", room_no, last_published_count, mqtt_topic)

            if not display:
                continue

            annotated = draw_annotations(frame, persons)
            cv2.putText(
                annotated,
                f"People: {len(persons)}",
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
        description="Count people in an image or webcam feed using YOLO."
    )
    parser.add_argument(
        "--image", "-i", type=Path, default=None, help="Path to the input image."
    )
    parser.add_argument(
        "--webcam",
        action="store_true",
        help="Show a live person count from the webcam instead of processing a still image.",
    )
    parser.add_argument(
        "--camera-index",
        type=int,
        default=1,
        help="Webcam device index to use with --webcam (default: 1, the external webcam; "
        "use 0 for the built-in camera).",
    )
    parser.add_argument(
        "--model",
        default="yolov8n.pt",
        help="Ultralytics YOLO weights to use (default: yolov8n.pt, downloaded on first run).",
    )
    parser.add_argument(
        "--mqtt-host",
        default=None,
        help="MQTT broker host to publish person counts to "
        "(default: host from --config, falling back to 10.27.127.25).",
    )
    parser.add_argument(
        "--mqtt-port",
        type=int,
        default=1883,
        help="MQTT broker port (default: 1883).",
    )
    parser.add_argument(
        "--mqtt-topic",
        default=None,
        help="MQTT topic to publish person counts to "
        "(default: camera/person-count; room_no is sent in the JSON payload).",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG_PATH,
        help=f"Path to config.json containing room_no and host (default: {DEFAULT_CONFIG_PATH.name} next to this script).",
    )
    parser.add_argument(
        "--room-no",
        default=None,
        help="Room number/code used to build the default MQTT topic (default: room_no from --config).",
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
        help="Optional path to save an annotated copy with people boxed.",
    )
    parser.add_argument(
        "--confidence",
        type=float,
        default=0.5,
        help="Minimum detection confidence to keep a box (default: 0.5).",
    )
    parser.add_argument(
        "--iou",
        type=float,
        default=0.45,
        help="IoU threshold used for non-max suppression (default: 0.45).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    if not args.webcam and args.image is None:
        logger.error("Provide --image PATH or --webcam.")
        return 1

    try:
        model = load_model(args.model)
    except RuntimeError as exc:
        logger.error(exc)
        return 2

    params = DetectionParams(
        confidence=args.confidence,
        iou=args.iou,
    )

    if args.webcam:
        config = load_config(args.config)
        room_no = args.room_no or config.get("room_no")
        mqtt_host = args.mqtt_host or config.get("host") or "10.27.127.25"
        mqtt_topic = args.mqtt_topic or "camera/person-count"
        if room_no:
            logger.info("Using room_no=%s", room_no)

        return run_webcam(
            model,
            params,
            camera_index=args.camera_index,
            mqtt_host=mqtt_host,
            mqtt_port=args.mqtt_port,
            mqtt_topic=mqtt_topic,
            room_no=room_no,
            display=args.display,
        )

    try:
        image = load_image(args.image)
    except (FileNotFoundError, ValueError) as exc:
        logger.error(exc)
        return 1

    persons = count_persons(image, model, params)

    logger.info("Detected %d person(s) in %s", len(persons), args.image)
    for idx, (x, y, w, h) in enumerate(persons, start=1):
        logger.info("  Person %d: x=%d y=%d w=%d h=%d", idx, x, y, w, h)

    if args.output:
        annotated = draw_annotations(image, persons)
        cv2.imwrite(str(args.output), annotated)
        logger.info("Annotated image saved to %s", args.output)

    print(len(persons))  # machine-readable result on stdout
    return 0


if __name__ == "__main__":
    sys.exit(main())
