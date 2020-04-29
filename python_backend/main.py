import cv2
import numpy as np
import dlib
from math import hypot

import pika

cap = cv2.VideoCapture(0)

detector = dlib.get_frontal_face_detector()
predictor = dlib.shape_predictor("shape_predictor_68_face_landmarks.dat")


def getEyeMidpoint(firstPoint, secondPoint):
    return int((firstPoint.x + secondPoint.x) / 2), int((firstPoint.y + secondPoint.y) / 2)

font = cv2.FONT_HERSHEY_PLAIN

def getBlinkingRatio(eyePoints, facialLandmarks):
    leftPoint = (facialLandmarks.part(eyePoints[0]).x, facialLandmarks.part(eyePoints[0]).y)
    rightPoint = (facialLandmarks.part(eyePoints[3]).x, facialLandmarks.part(eyePoints[3]).y)
    centerTopPoint = getEyeMidpoint(facialLandmarks.part(eyePoints[1]), facialLandmarks.part(eyePoints[2]))
    centerBottomPoint = getEyeMidpoint(facialLandmarks.part(eyePoints[5]), facialLandmarks.part(eyePoints[4]))
    horizontalLineHeight = hypot((leftPoint[0] - rightPoint[0]), (leftPoint[1] - rightPoint[1]))
    verticalLineHeight = hypot((centerTopPoint[0] - centerBottomPoint[0]), (centerTopPoint[1] - centerBottomPoint[1]))

    blinkingRatio = horizontalLineHeight / verticalLineHeight
    return blinkingRatio

def getGazeRatio(eyePoints, facialLandmarks, frame, gray):
    eyeRegion = np.array([(facialLandmarks.part(eyePoints[0]).x, facialLandmarks.part(eyePoints[0]).y),
                          (facialLandmarks.part(eyePoints[1]).x, facialLandmarks.part(eyePoints[1]).y),
                          (facialLandmarks.part(eyePoints[2]).x, facialLandmarks.part(eyePoints[2]).y),
                          (facialLandmarks.part(eyePoints[3]).x, facialLandmarks.part(eyePoints[3]).y),
                          (facialLandmarks.part(eyePoints[4]).x, facialLandmarks.part(eyePoints[4]).y),
                          (facialLandmarks.part(eyePoints[5]).x, facialLandmarks.part(eyePoints[5]).y)], np.int32)

    height, width, _ = frame.shape
    mask = np.zeros((height, width), np.uint8)
    cv2.polylines(mask, [eyeRegion], True, 255, 2)
    cv2.fillPoly(mask, [eyeRegion], 255)
    eye = cv2.bitwise_and(gray, gray, mask=mask)

    minX = np.min(eyeRegion[:, 0])
    maxX = np.max(eyeRegion[:, 0])
    minY = np.min(eyeRegion[:, 1])
    maxY = np.max(eyeRegion[:, 1])

    grayEye = eye[minY: maxY, minX: maxX]
    _, eyeThreshold = cv2.threshold(grayEye, 70, 255, cv2.THRESH_BINARY)
    height, width = eyeThreshold.shape

    leftSideThreshold = eyeThreshold[0: height, 0: int(width / 2)]
    leftSideWhite = cv2.countNonZero(leftSideThreshold)

    rightSideThreshold = eyeThreshold[0: height, int(width / 2): width]
    rightSideWhite = cv2.countNonZero(rightSideThreshold)

    # gazeRatio = 0

    if leftSideWhite == 0:
        gazeRatio = 1
    elif rightSideWhite == 0:
        gazeRatio = 5
    else:
        gazeRatio = leftSideWhite / rightSideWhite
    
    return gazeRatio

leftDirectionFrameCount = 0
rightDirectionFrameCount = 0
blinkingFrameCount = 0




connection = pika.BlockingConnection()
channel = connection.channel()

channel.queue_declare(queue='gaze')

while True:
    _, frame = cap.read()
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    faces = detector(gray)

    for face in faces:
        facialLandmarks = predictor(gray, face)

        leftEyeRatio = getBlinkingRatio([36, 37, 38, 39, 40, 41], facialLandmarks)
        rightEyeRatio = getBlinkingRatio([42, 43, 44, 45, 46, 47], facialLandmarks)

        blinkingRatio = (leftEyeRatio + rightEyeRatio) / 2

        if blinkingRatio > 5.7:
            # print('USER IS BLINKING')
            blinkingFrameCount += 1
        
        if blinkingFrameCount == 30:
            print('USER IS BLINKING')
            blinkingFrameCount = 0

        gazeRatioLeftEye = getGazeRatio([36, 37, 38, 39, 40, 41], facialLandmarks, frame, gray)
        gazeRatioRightEye = getGazeRatio([42, 43, 44, 45, 46, 47], facialLandmarks, frame, gray)

        gazeRatio = (gazeRatioLeftEye + gazeRatioRightEye) / 2

        

        if gazeRatio <= 0.9:
            #print('USER IS LOOKING RIGHT')
            rightDirectionFrameCount += 1
            leftDirectionFrameCount = 0
        elif 1 < gazeRatio < 1.7:
            #print('USER IS LOOKING AT THE CENTER')
            leftDirectionFrameCount = 0
            rightDirectionFrameCount = 0
        else:
            #print('USER IS LOOKING LEFT')
            leftDirectionFrameCount += 1
            rightDirectionFrameCount = 0        
        if leftDirectionFrameCount == 30:
            print('USER LOOKED LEFT')
            channel.basic_publish(exchange='',
                    routing_key='gaze',
                    body='L')
            print('EVENT SENT!')
            leftDirectionFrameCount = 0
        elif rightDirectionFrameCount == 30:
            print('USER LOOKED RIGHT')
            channel.basic_publish(exchange='',
                    routing_key='gaze',
                    body='R')
            print('EVENT SENT!')
            rightDirectionFrameCount = 0

    cv2.imshow("Frame", frame)
    
    key = cv2.waitKey(1)
    if key == 27:
        break


cap.release()
cv2.destroyAllWindows()
connection.close()