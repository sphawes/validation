import cv2
import time
import math
import serial
import numpy as np
import threading
import json
import sys
import atexit

port = '/dev/ttyACM0' 
ser = serial.Serial(port, 115200, timeout=2)
ser.flushInput()

font = cv2.FONT_HERSHEY_SIMPLEX
hsvLower = (90, 100, 220)
hsvUpper = (120, 255, 255)
w = 640.0
minRadius = 10
buffer_string = ''
last_received = ''

def exit_handler():
    ser.close()

atexit.register(exit_handler)

#connect to webcam
capture = cv2.VideoCapture(0)
#print(capture.get(cv2.CAP_PROP_FPS))

#logging file setup
epoch = str(math.floor(time.time()))
f = open("log/" + epoch + ".csv", "x")
f.write("Index Precision Lifetime Test started at " + epoch + ".\n")

print("homing...")
ser.write("G28 R\n".encode())
ser.write("M205 T75\n".encode())
print("sent homing")
#hang until we get a response from Marlin
last_command_complete = False
while(last_command_complete == False):
    response = ser.read_until()
    print(response)
    if(response == b'ok\n'):
        last_command_complete = True

# # #main loop, one cycle results in a row in the csv
while True:
    print("Starting the while loop!")

    g = open('static.gcode','r')
    for line in g:
        l = line.strip() # Strip all EOL characters for consistency
        print('Sending: ' + l)
        block = l + '\n'
        ser.write(block.encode()) # Send g-code block to grbl
        grbl_out = ser.readline() # Wait for grbl response with carriage return
        print(grbl_out.strip())

    #hang until all moves are complete so we capture an image only after the head is in position
    last_command_complete = False
    timeout_time = time.time()
    while(last_command_complete == False):
        response = ser.read_until()
        print(response)
        if(response == b'test\r\n' or time.time() - timeout_time > 60):
            last_command_complete = True
    last_command_complete = False
    timeout_time = time.time()
    while(last_command_complete == False):
        response = ser.read_until()
        print(response)
        if(response == b'ok\n' or time.time() - timeout_time > 5):
            last_command_complete = True

    time.sleep(1)

    print("about to do the vision stuff!")
    #take image from webcam
    ret, image = capture.read()

    #scaling down for faster processing
    img_height, img_width, depth = image.shape
    scale = w / img_width
    h = img_height * scale
    image = cv2.resize(image, (0,0), fx=scale, fy=scale)
    scaledHeight, scaledWidth, scaledDepth = image.shape

    #image processing
    blurred = cv2.GaussianBlur(image, (11, 11), 0)
    hsv = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)
    mask1 = cv2.inRange(hsv, hsvLower, hsvUpper)
    mask2 = cv2.erode(mask1, None, iterations=2)
    mask = cv2.dilate(mask2, None, iterations=2)

    #find contours
    cnts = cv2.findContours(mask.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)[-2]
    center = None

    #establish coordinate variables for centerpoint of dot
    x = 0
    y = 0

	# only proceed if at least one contour was found
    if len(cnts) > 0:
		# find the largest contour in the mask, then use
		# it to compute the minimum enclosing circle and
		# centroid
        c = max(cnts, key=cv2.contourArea)
        ((x, y), radius) = cv2.minEnclosingCircle(c)
        M = cv2.moments(c)
        center = (int(M["m10"] / M["m00"]), int(M["m01"] / M["m00"]))

		# only proceed if the radius meets a minimum size
        if radius > minRadius:

            cv2.circle(image, (int(x), int(y)), int(radius), (0, 255, 255), 2)
            cv2.circle(image, center, 5, (0, 0, 0), -1)

            posX = 100 - int((x / scaledWidth)*100)
            posY = int((y / scaledHeight)*100)
            posZ = int((radius*2) - (minRadius*2))
    else:
        x = -1
        y = -1

    # prints data to csv
    f.write(str(x) + ", " + str(y) + "\n")

    #prints flipped image with tracked blob superimposed
    image = cv2.flip(image, 1)
    cv2.imshow('precision', image)

    cv2.imshow('test', mask1)

    #turn off the ring light
    ser.write("M150 P0\n".encode())

    if cv2.waitKey(1) & 0xFF is ord(' '):
        break
