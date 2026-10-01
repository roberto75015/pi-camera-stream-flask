import cv2
import numpy as np

class haarDetector():
    def __init__(self):
        self.faceModel = cv2.CascadeClassifier("/usr/share/opencv4/haarcascades/haarcascade_frontalface_default.xml")

    def convert(self, frame):
        #gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        return cv2.cvtColor(frame, cv2.COLOR_YUV420p2GRAY)

    def resize(self, frame):
        if frame.shape[1]/frame.shape[0] > 1.55:
            size = (256*2, 155*2)
        else:   
            size = (216*2, 162*2)
        frame = cv2.resize(frame, size, interpolation=cv2.INTER_AREA)
        return (frame, size)

    def detect(self, gray):
        faces = self.faceModel.detectMultiScale(gray, minNeighbors=6)
        return faces
