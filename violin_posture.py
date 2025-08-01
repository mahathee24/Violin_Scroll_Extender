import cv2
import mediapipe as mp
import numpy as np
import asyncio
import sys
from bleak import BleakClient

# Windows event loop fix
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# BLE Details
BLE_ADDRESS = "F8:24:41:A3:1C:5B"  # Replace with real MAC or keep dummy
CHAR_UUID = "cba1d466-344c-4be3-ab3f-189f80dd7518"

# Global BLE status
scroll_status = "Connecting..."
scroll_height = "..."

# Mediapipe setup
mp_drawing = mp.solutions.drawing_utils
mp_pose = mp.solutions.pose

def calculate_angle(a, b, c):
    a, b, c = np.array(a), np.array(b), np.array(c)
    radians = np.arctan2(c[1]-b[1], c[0]-b[0]) - np.arctan2(a[1]-b[1], a[0]-b[0])
    angle = np.abs(radians * 180.0 / np.pi)
    return 360 - angle if angle > 180 else angle

def handle_ble(_, data):
    global scroll_status, scroll_height
    message = data.decode().strip()
    if message == "OK":
        scroll_status = "Mounted "
    elif message == "ScrollLoose":
        scroll_status = "Loose Scroll "
    elif message == "ViolinTilted":
        scroll_status = "Tilted Violin "
    elif message.startswith("Height:"):
        scroll_height = message.split(":")[1].strip() + " cm"

async def posture_loop(client=None):
    cap = cv2.VideoCapture(0)
    with mp_pose.Pose(min_detection_confidence=0.7, min_tracking_confidence=0.7) as pose:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            image.flags.writeable = False
            results = pose.process(image)
            image.flags.writeable = True
            image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)

            feedback = ""
            color = (0, 255, 0)

            if results.pose_landmarks:
                lm = results.pose_landmarks.landmark
                R_SH = [lm[mp_pose.PoseLandmark.RIGHT_SHOULDER.value].x, lm[mp_pose.PoseLandmark.RIGHT_SHOULDER.value].y]
                R_EL = [lm[mp_pose.PoseLandmark.RIGHT_ELBOW.value].x, lm[mp_pose.PoseLandmark.RIGHT_ELBOW.value].y]
                R_WR = [lm[mp_pose.PoseLandmark.RIGHT_WRIST.value].x, lm[mp_pose.PoseLandmark.RIGHT_WRIST.value].y]
                R_HIP = [lm[mp_pose.PoseLandmark.RIGHT_HIP.value].x, lm[mp_pose.PoseLandmark.RIGHT_HIP.value].y]
                R_EAR = [lm[mp_pose.PoseLandmark.RIGHT_EAR.value].x, lm[mp_pose.PoseLandmark.RIGHT_EAR.value].y]
                L_SH = [lm[mp_pose.PoseLandmark.LEFT_SHOULDER.value].x, lm[mp_pose.PoseLandmark.LEFT_SHOULDER.value].y]

                right_arm_angle = calculate_angle(R_SH, R_EL, R_WR)
                back_angle = calculate_angle(R_EAR, R_SH, R_HIP)
                shoulder_diff = abs(R_SH[1] - L_SH[1])

                if not (60 <= right_arm_angle <= 110):
                    feedback = "Adjust Bowing Arm"
                    color = (0, 0, 255)
                elif shoulder_diff > 0.08:
                    feedback = "Avoid Leaning, Level Shoulders"
                    color = (0, 0, 180)
                elif back_angle > 110:
                    feedback = "Sit Straight, Avoid Slouching"
                    color = (255, 0, 0)
                else:
                    feedback = "Good Posture"
                    color = (0, 255, 0)

                mp_drawing.draw_landmarks(image, results.pose_landmarks, mp_pose.POSE_CONNECTIONS)

                cv2.putText(image, f'Arm Angle: {int(right_arm_angle)}°', (30, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (150, 255, 100), 2)
                cv2.putText(image, feedback, (30, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.9, color, 2)

            # BLE overlays
            if client:
                cv2.putText(image, f'Scroll: {scroll_status}', (30, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 200, 100), 2)
                cv2.putText(image, f'Height: {scroll_height}', (30, 130), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 150), 2)

            cv2.imshow('🎻 Violin Posture Monitor', image)

            if cv2.waitKey(10) & 0xFF == ord('q'):
                break

    cap.release()
    cv2.destroyAllWindows()

# Main BLE + Posture entry
async def main():
    try:
        async with BleakClient(BLE_ADDRESS) as client:
            await client.start_notify(CHAR_UUID, handle_ble)
            print(" BLE Connected.")
            await posture_loop(client)
    except Exception as e:
        print(" BLE Connection failed or not available. Running posture monitoring only.")
        print(f"Reason: {e}")
        await posture_loop(None)

# Run main
asyncio.run(main())
