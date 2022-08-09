import mss
import cv2
import numpy
import time
import os
import logging

from pathlib import Path
import config
from assets.exception_handler import exception_handler
from assets.timeformatter import Formatter
from assets.multifilehandler import MultiFileHandler

THIS_FOLDER = os.path.dirname(os.path.abspath(__file__))

path = Path(THIS_FOLDER)


class AlertScanner:
    def __init__(self, MONITOR_ID, CHART_X_COORDINATE, CHART_Y_COORDINATE, CHART_X2_COORDINATE, CHART_Y2_COORDINATE):
        self.initiation = False
        self.prev_direction = 99999
        self.prev_systemStatus = "RUNNING"
        self.runId = time.strftime("%Y_%m_%d_%H_%M_%S")
        self.threshold = 0.85

        self.monitor_id = MONITOR_ID
        self.chart_x_coordinate = CHART_X_COORDINATE
        self.chart_y_coordinate = CHART_Y_COORDINATE
        self.chart_x2_coordinate = CHART_X2_COORDINATE
        self.chart_y2_coordinate = CHART_Y2_COORDINATE
        self.chart_width = self.chart_x2_coordinate-self.chart_x_coordinate
        self.chart_height = self.chart_y2_coordinate-self.chart_y_coordinate

        # INSTANTIATE LOGGER
        file_handler = MultiFileHandler(filename='logs/error.log', mode='a')

        formatter = Formatter('%(asctime)s [%(levelname)s] %(message)s')

        file_handler.setFormatter(formatter)

        ch = logging.StreamHandler()

        ch.setLevel(level="INFO")

        ch.setFormatter(formatter)

        self.logger = logging.getLogger(__name__)

        self.logger.setLevel(level="INFO")

        self.logger.addHandler(file_handler)

        self.logger.addHandler(ch)

    @exception_handler
    def scanVisualAlerts(self):
        switcher = {
            1: "BUY",
            -1: "SELL",
            0: "CLOSE",
            99999: "Not Available"
        }
        sct = mss.mss()
        mon = sct.monitors[self.monitor_id]
        chart_coordinates = {
            'left': mon['top']+self.chart_x_coordinate,
            'top': mon['top']+self.chart_y_coordinate,
            'width': self.chart_width,
            'height': self.chart_height
        }

        longArrowImg = cv2.imread('./img/Long_Arrow.png')
        shortArrowImg = cv2.imread('./img/Short_Arrow.png')
        exitDownArrowImg = cv2.imread('./img/Close_Down_Arrow.png')
        exitUpArrowImg = cv2.imread('./img/Close_Up_Arrow.png')
        w = longArrowImg.shape[1]
        h = longArrowImg.shape[0]

        trade_signal = None

        current_time = time.strftime("%H:%M:%S")

        scr = numpy.array(sct.grab(chart_coordinates))

        # Cut off alpha
        scr_remove = scr[:, :, :3]
        entryArrowColor=numpy.array([255, 255, 255])
        exitArrowColor=numpy.array([255, 255, 0])
        entryColorMask = cv2.inRange(scr_remove, entryArrowColor, entryArrowColor)
        entryColorResult = cv2.bitwise_and(scr_remove, scr_remove, mask=entryColorMask)
        longArrowResult = cv2.matchTemplate(entryColorResult, longArrowImg, cv2.TM_CCOEFF_NORMED)
        shortArrowResult = cv2.matchTemplate(entryColorResult, shortArrowImg, cv2.TM_CCOEFF_NORMED)

        exitColorMask = cv2.inRange(scr_remove, exitArrowColor, exitArrowColor)
        exitColorResult = cv2.bitwise_and(scr_remove, scr_remove, mask=exitColorMask)
        exitUpArrowResult = cv2.matchTemplate(exitColorResult, exitUpArrowImg, cv2.TM_CCOEFF_NORMED)
        exitDownArrowResult = cv2.matchTemplate(exitColorResult, exitDownArrowImg, cv2.TM_CCOEFF_NORMED)

        allLongArrows = numpy.where(longArrowResult >= self.threshold)
        allShortArrows = numpy.where(shortArrowResult >= self.threshold)
        allExitUpArrows = numpy.where(exitUpArrowResult >= self.threshold)
        allExitDownArrows = numpy.where(exitDownArrowResult >= self.threshold)

        longArrow = None
        shortArrow = None
        exitUpArrow = None
        exitDownArrow = None
        exitArrow = None

        if len(allLongArrows[0]) > 0:
            longArrow = sorted(zip(allLongArrows[1], allLongArrows[0]), reverse=True)[0]
        if len(allShortArrows[0]) > 0:
            shortArrow = sorted(zip(allShortArrows[1], allShortArrows[0]), reverse=True)[0]

        if len(allExitUpArrows[0]) > 0:
            exitUpArrow = sorted(zip(allExitUpArrows[1], allExitUpArrows[0]), reverse=True)[0]
        if len(allExitDownArrows[0]) > 0:
            exitDownArrow = sorted(zip(allExitDownArrows[1], allExitDownArrows[0]), reverse=True)[0]

        if exitUpArrow is not None and exitDownArrow is not None:
            # Both exit symbols found. Determine which one is latest
            if exitUpArrow[0] > exitDownArrow[0]:
                exitArrow = exitUpArrow
            else:
                exitArrow = exitDownArrow
        elif exitUpArrow is not None:
            exitArrow = exitUpArrow
        elif exitDownArrow is not None:
            exitArrow = exitDownArrow

        if longArrow is not None and shortArrow is not None:
            # Both symbols found. Determine which one is latest
            if longArrow[0] > shortArrow[0]:
                direction = 1
            else:
                direction = -1
        elif longArrow is not None:
            direction = 1
        elif shortArrow is not None:
            direction = -1
        else:
            direction = 99999

        # Find out if latest is exitArrow
        if exitArrow is not None:
            if direction == 1 and exitArrow[0] > longArrow[0]:
                direction = 0
            elif direction == -1 and exitArrow[0] > shortArrow[0]:
                direction = 0
            elif direction == 99999:
                direction = 0

        if direction == 1:
            max_loc = longArrow
        elif direction == -1:
            max_loc = shortArrow
        elif direction == 0:
            max_loc = exitArrow
        else:
            max_loc = (0, 0)

        # if direction == 99999:
        #     systemStatus = "ERROR"
        # else:
        #     systemStatus = "RUNNING"
        #
        # if systemStatus == "RUNNING":
        #     sendAlert = True
        # else:
        #     sendAlert = False

        systemStatus = "RUNNING"
        sendAlert = True

        scr = scr.copy()
        for (x, y) in zip(allLongArrows[1], allLongArrows[0]):
            # draw the bounding box on the image
            cv2.rectangle(scr, (x, y), (x + w, y + h), (0, 255, 0), 1)

        for (x, y) in zip(allShortArrows[1], allShortArrows[0]):
            # draw the bounding box on the image
            cv2.rectangle(scr, (x, y), (x + w, y + h), (0, 0, 255), 1)

        for (x, y) in zip(allExitUpArrows[1], allExitUpArrows[0]):
            # draw the bounding box on the image
            cv2.rectangle(scr, (x, y), (x + w, y + h), (255, 255, 255), 1)

        for (x, y) in zip(allExitDownArrows[1], allExitDownArrows[0]):
            # draw the bounding box on the image
            cv2.rectangle(scr, (x, y), (x + w, y + h), (255, 255, 255), 1)

        if direction != 99999:
            cv2.rectangle(scr, max_loc, (max_loc[0] + w, max_loc[1] + h), (0, 255, 255), 2)

        cv2.imshow('Screen Shot', scr)

        if sendAlert:
            if config.GIVE_CONTINUOUS_UPDATES:
                print(f"\n{current_time} --> Status : {systemStatus}, prev_direction={switcher.get(self.prev_direction)}, direction={switcher.get(direction)},  sendAlert= {sendAlert}")
            trade_signal = switcher.get(direction)

        self.prev_direction = direction
        self.prev_systemStatus = systemStatus
        cv2.waitKey(1)

        return trade_signal

