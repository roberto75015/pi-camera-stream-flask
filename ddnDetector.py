import cv2
import numpy as np
import time

class ddnDetector():
	def __init__(self):
		self.net = cv2.dnn.readNetFromCaffe('deploy.prototxt.txt', 'res10_300x300_ssd_iter_140000.caffemodel')
		self.size = None
		self.resizeTime = 0
		#self.size = (300, 300)

	def convert(self, frame):
		return cv2.cvtColor(frame, cv2.COLOR_YUV420p2BGR)

	def resize(self, frame):
		startTime = time.time_ns()
		factor = 1
		if self.size is None:
			if frame.shape[1]/frame.shape[0] > 1.55:
				self.size = (256*factor, 155*factor)
			else:   
				self.size = (216*factor, 162*factor)
		size = self.size
		frame = cv2.resize(frame, size)
		#size = (frame.shape[1], frame.shape[0])
		self.resizeTime += time.time_ns() - startTime
		return (frame, size)

	def detect(self, frame):
		startTime = time.time_ns()
		(h, w) = frame.shape[:2]
		blob = cv2.dnn.blobFromImage(frame, 1.0, self.size, (104.0, 177.0, 123.0))
		self.net.setInput(blob)
		detections = self.net.forward()
		boxes = []
		confidences = ""
		for i in range(0, detections.shape[2]):
			# extract the confidence (i.e., probability associated with te prediction
			confidence = detections[0, 0, i, 2]
			if (confidence > 0.85):
				confidences += f"{confidence:.2f},"
				box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
				(startX, startY, endX, endY) = box.astype('int')
				boxes.append( (startX, startY, endX-startX, endY-startY) )
		#print(f"Detection time: {(time.time_ns() - startTime)/1_000_000} ms, Resize time total: {self.resizeTime/1_000_000} ms confidences: {confidences}")
		return boxes
