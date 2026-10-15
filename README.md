# Real-Time Exercise Posture Detection and Correction Using Computer Vision

A computer vision-based system designed to analyze exercise posture through a webcam, evaluate body movements, and provide real-time feedback to help users improve their exercise form.

## Overview

Performing exercises with improper posture can reduce workout effectiveness and increase the risk of injury. Beginners, in particular, may have difficulty identifying incorrect form without guidance from a trainer.

This project aims to address this problem by developing a real-time exercise posture detection and correction system using computer vision. The system will detect human body landmarks, calculate relevant joint angles and body alignment measurements, and compare these measurements against predefined exercise-specific criteria.

The initial scope covers four common exercises:

- Squats
- Push-ups
- Lunges
- Jumping jacks

The system is being developed as a Computer Vision Final Project for CSST 106 at Laguna State Polytechnic University.

## Objectives

- Detect and track human body landmarks using a webcam.
- Analyze body posture and movement during selected exercises.
- Identify potentially incorrect exercise form using predefined rules.
- Provide real-time visual feedback to users.
- Implement repetition counting where applicable.
- Evaluate posture classification performance and system responsiveness.

## Technology Stack

| Technology | Purpose |
|---|---|
| Python | Primary programming language |
| MediaPipe Pose Landmarker | Human pose estimation and body landmark detection |
| OpenCV | Webcam access, video frame processing, and visual output |
| Geometric calculations | Joint-angle, relative-distance, and body-alignment measurements |
| Rule-based classification | Evaluation of exercise posture against predefined criteria |
