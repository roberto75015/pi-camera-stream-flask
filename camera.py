import io
import time
import logging
from threading import Condition
import threading
import imutils
import cv2
from picamera2 import Picamera2
from picamera2.encoders import JpegEncoder
from picamera2.outputs import FileOutput
from servo import Servo
from haarDetector  import haarDetector
from ddnDetector  import ddnDetector

# Set up logging
logging.basicConfig(level=logging.INFO)


class StreamingOutput(io.BufferedIOBase):
    """
    A thread-safe, in-memory stream for the camera's JPEG output.
    """

    def __init__(self):
        self.frame = None
        self.condition = Condition()

    def write(self, buf: bytes) -> int:
        """
        Called by the encoder. Writes the frame to the buffer and notifies
        any waiting threads.
        :param buf: The buffer containing the JPEG frame.
        :type buf: bytes
        """
        with self.condition:
            self.frame = buf
            self.condition.notify_all()
        return len(buf)


class VideoCamera(object):
    """
    A class that manages the Raspberry Pi camera using picamera2 for
    efficient, hardware-accelerated MJPEG streaming.
    """

    def __init__(self, flip: bool = False):
        """
        Initializes the camera, configures it for streaming, and starts
        the hardware encoder.

        :param flip: Whether to flip the camera feed vertically and horizontally.
        :type flip: bool
        """
        logging.info("Initializing camera...")
        self.picam2 = Picamera2()

        # --- Streaming Configuration ---
        # Reduced resolution for smoother web streaming and lower latency.
        # The hardware encoder works with YUV420 format.
            #main={"size": (1280, 720), "format": "YUV420"},
        video_config = self.picam2.create_video_configuration(
            main={"size": (1296, 972), "format": "YUV420"},
            controls={"FrameRate": 30}
        )
        self.picam2.configure(video_config)

        # Preview configuration for display (BGR888 format for OpenCV compatibility)
        self.preview_config = self.picam2.create_preview_configuration(
            main={"size": (1296, 972), "format": "BGR888"},
        )

        # --- Still Image Configuration ---
        # A separate, higher-resolution configuration for taking still photos.
        self.still_config = self.picam2.create_still_configuration()

        # Set flip controls if needed
        if flip:
            self.picam2.set_controls({"VFlip": True, "HFlip": True})

        self.output = StreamingOutput()
        self.encoder = JpegEncoder()

        # Start the encoder in a background thread
        self.picam2.start_recording(self.encoder, FileOutput(self.output))

        logging.info("Camera initialized and recording started.")
        time.sleep(1)  # Allow camera to warm up

        #self.detector = haarDetector()
        self.detector = ddnDetector()
        info = self.picam2.global_camera_info();
        fovs = (62.2, 48.8) 
        match info:
            case "ov5647":
                fovs = (53.5, 41.41)
            case "imx219":
                fovs = (62.2, 48.8)
            case "imx708":
                fovs = (66, 41)
            case "imx477":
                fovs = (70.6, 43.3)
            case "imx500":
                fovs = (66, 52.3)
        self.servo = Servo(fovs[0], fovs[1])
        self.stop_pan_tilt_thread = False
        self.pan_tilt_thread = threading.Thread(target=self.pan_tilt_thread_loop, daemon=True)
        self.pan_tilt_thread.start()

    def __del__(self):
        """
        Stops the recording thread when the object is destroyed.
        """
        logging.info("Stopping camera recording.")
        self.picam2.stop_recording()
        logging.info("Stopping Pan & tilt thread.")
        self.stop_pan_tilt_thread = True
        self.pan_tilt_thread.join(timeout=2)

    def get_frame(self) -> bytes:
        """
        Waits for a new frame from the encoder and returns it.

        :return: A complete JPEG frame as a byte string.
        :rtype: bytes
        """
        with self.output.condition:
            self.output.condition.wait()
            frame = self.output.frame
        return frame

    def take_picture(self):
        """
        Temporarily stops the stream, switches to high-resolution config,
        takes a photo, and then restarts the stream.
        """
        logging.info("Stopping recording to capture a still image.")
        self.picam2.stop_recording()
        time.sleep(0.5)  # Allow time for the encoder to stop

        try:
            # Switch to still configuration and capture
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            filename = f"stream_photo_{timestamp}.jpg"
            logging.info(f"Capturing still image to {filename}...")
            self.picam2.switch_mode_and_capture_file(self.still_config, filename)
            logging.info("Still image captured.")
        finally:
            # Ensure the stream is restarted
            logging.info("Restarting video stream recording.")
            self.picam2.start_recording(self.encoder, FileOutput(self.output))

    def pan_tilt_thread_loop(self):
        print("Pan & tilt thread running...")
        max_sleep_time = 2.5
        sleep_increment = 0.100
        sleep_time = sleep_increment
        moves_threshold = 6
        while self.stop_pan_tilt_thread is False:
            frame = self.picam2.capture_array()
            frame = self.detector.convert(frame)
            (frame, size) = self.detector.resize(frame)
            boxes = self.detector.detect(frame)
            angles = []
            for (x, y, w, h) in boxes:
                cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 2)
                # save target angle to move to center of detected box
                angles.append(self.servo.angles( (x+(w/2), y+(h/2)), size))
            if len(angles) > 0:
                cv2.imshow("Frame", frame)
                cv2.waitKey(1)
                nmoves = self.servo.goSlowlyToCloserAngle(angles)
                if nmoves > moves_threshold:
                    sleep_time = sleep_increment
            # if nothing detected or no moves needed then sleep a bit
            if len(angles) == 0 or nmoves <= moves_threshold:
                time.sleep(sleep_time)
                sleep_time = min(sleep_time + sleep_increment, max_sleep_time)
            

