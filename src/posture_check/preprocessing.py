"""Conservative black-border removal with reversible landmark coordinates.

Only paired, nearly uniform black margins are removed. No person bounding box
is used: cropping around a false pose would defeat the existing size gates.
"""
from copy import copy
import math
import cv2
import numpy as np

PARAMETERS = {'black_level': 12, 'black_fraction': .995,
              'minimum_border_pixels': 2, 'minimum_content_fraction': .25}


def _paired_bounds(black):
    length = len(black)
    occupied = np.flatnonzero(~black)
    if not len(occupied):
        return 0, length
    first, last = int(occupied[0]), int(occupied[-1]) + 1
    if (first < PARAMETERS['minimum_border_pixels']
            or length-last < PARAMETERS['minimum_border_pixels']
            or last-first < PARAMETERS['minimum_content_fraction']*length):
        return 0, length
    return first, last


def active_region(frame):
    """Return BGR crop and (left, top, right, bottom) in input pixels."""
    h, w = frame.shape[:2]
    limit = PARAMETERS['black_level']
    mask = cv2.inRange(frame, (0, 0, 0), (limit, limit, limit))
    rows = cv2.reduce(mask, 1, cv2.REDUCE_SUM, dtype=cv2.CV_32S).ravel()
    top, bottom = _paired_bounds(rows >= math.ceil(PARAMETERS['black_fraction']*w)*255)
    columns = cv2.reduce(mask[top:bottom], 0, cv2.REDUCE_SUM, dtype=cv2.CV_32S).ravel()
    left, right = _paired_bounds(columns >= math.ceil(PARAMETERS['black_fraction']*(bottom-top))*255)
    return frame[top:bottom, left:right], (left, top, right, bottom)


def restore_landmarks(landmarks, region, width, height):
    left, top, right, bottom = region
    if region == (0, 0, width, height):
        return landmarks
    restored = []
    for landmark in landmarks:
        point = copy(landmark)
        point.x = (left + landmark.x*(right-left))/width
        point.y = (top + landmark.y*(bottom-top))/height
        restored.append(point)
    return restored
