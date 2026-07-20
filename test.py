
import cv2
import time
import numpy

#frame = cv2.imread('stream_photo_20260108-222044.jpg')
frame = cv2.imread('temp.jpg')
print(frame.shape)
cv2.imshow('frame', frame)
cv2.waitKey(1000)
time.sleep(1)
