
import time
import sys
import json
import atexit

# make sure pigpiod is running, else sudo pigpiod or:
#		sudo systemctl enable pigpiod
#		sudo systemctl start pigpiod
from gpiozero.pins.pigpio import PiGPIOFactory
from gpiozero import AngularServo, Device

class Servo():
	def __init__(self, hfov = 62.2, vfov = 48.8, tilt: int = -1, pan: int = -1):
		self.max_angle = 180
		self.min_angle = 0
		self.cameraHFOV = hfov
		self.cameraVFOV = vfov
		tilt = pan = -1
		try:
			with open("servo.json", "r") as f:
				data = json.load(f)
			if "tilt" in data:
				tilt = data["tilt"]
			if "pan" in data:
				pan = data["pan"]
		except:
			pass

		if tilt == -1 or tilt is None or tilt < self.min_angle or tilt > self.max_angle:
			tilt = self.max_angle//2
		if pan == -1 or pan is None or pan < self.min_angle or pan > self.max_angle:
			pan = self.max_angle//2

		Device.pin_factory = PiGPIOFactory()
		self.tilt = AngularServo(13, min_pulse_width=0.5/1000, max_pulse_width=2.5/1000, min_angle=self.min_angle, max_angle=self.max_angle)
		self.tilt.angle = self.tiltangle = tilt
		self.pan = AngularServo(12, min_pulse_width=0.5/1000, max_pulse_width=2.5/1000, min_angle=self.min_angle, max_angle=self.max_angle)
		self.pan.angle = self.panangle = pan
		atexit.register(self.savejson)

	def savejson(self):
		with open("servo.json", "w") as f:
			data = {
				"tilt": self.tiltangle,
				"pan": self.panangle
			}
			json.dump(data, f)
		time.sleep(0.25)
		self.off()

	def off(self):
		self.tilt.angle = None
		self.pan.angle = None

	def getTilt(self, tilt):
		return self.tiltangle

	def setTilt(self, tilt):
		if tilt >= self.min_angle and tilt <= self.max_angle:
			self.tilt.angle = self.tiltangle = tilt

	def getPan(self, pan):
		return self.panangle

	def setPan(self, pan):
		if pan >= self.min_angle and pan <= self.max_angle:
			self.pan.angle = self.panangle = pan

	def goSlowlyToCloserAngle(self, angles, minmove = 1):
		if len(angles) == 0:
			return
		nxpan = nxtilt = None
		# fine the one closest to middle position
		for (pan, tilt) in angles:
			if nxpan is None or abs(pan)+abs(tilt) < abs(nxpan)+abs(nxtilt):
				nxpan = pan
			if nxtilt is None or abs(pan)+abs(tilt) < abs(nxpan)+abs(nxtilt):
				nxtilt = tilt
		print(f"\rNew move: pan:{self.panangle} + {nxpan} tilt:{self.tiltangle} + {nxtilt}   ", end="")
		panrange = []
		tiltrange = []
		if nxpan != None and nxpan != 0 and abs(nxpan) > minmove:
			panrange = self.moverange(self.panangle, nxpan)
		if nxtilt != None and nxtilt != 0 and abs(nxtilt) > minmove:
			tiltrange = self.moverange(self.tiltangle, nxtilt)
		for i in range(max(len(panrange), len(tiltrange))):
			if i < len(panrange):
				self.setPan(panrange[i])
			if i < len(tiltrange):
				self.setTilt(tiltrange[i])
			time.sleep(0.05)
		return len(panrange) + len(tiltrange)

	def moverange(self, start, next):
		if next > 0:
			return range(start+1, start+next+1)
		else:
			return range(start-1, start+next-1, -1)

	def angles(self, values, sizes):
		pan = -1 * self.angle(values[0], sizes[0], self.cameraHFOV)
		tilt = self.angle(values[1], sizes[1], self.cameraVFOV)
		return (pan, tilt)

	def angle(self, value, max_input, fov):
		if value > max_input:
			value = max_input
		scale = fov / max_input
		angle = value * scale
		return int(angle - fov/2)


if __name__ == "__main__":
	usage = False
	tilt = -1
	pan = -1

	if len(sys.argv) > 1 and sys.argv[1] == "-":
		tilt = None
	else:
		try:
			tilt = int(sys.argv[1])
		except:
			usage = True
	if not usage:
		if len(sys.argv) > 2 and sys.argv[2] == "-":
			pan = None
		else:
			try:
				pan = int(sys.argv[2])
			except:
				usage = True
	if usage:
		print("Usage: servo tilt pan (- to stop the motors)")
	elif len(sys.argv) > 3 and sys.argv[3] == "-old":
		Device.pin_factory = PiGPIOFactory()
		stilt = AngularServo(13, min_pulse_width=0.5/1000, max_pulse_width=2.5/1000, min_angle=0, max_angle=180)
		stilt.angle = tilt
		span = AngularServo(12, min_pulse_width=0.5/1000, max_pulse_width=2.5/1000, min_angle=0, max_angle=180)
		span.angle = pan
	else:
		s = Servo()
		if tilt is not None:
			s.setTilt(tilt)
		if pan is not None:
			s.setPan(pan)


