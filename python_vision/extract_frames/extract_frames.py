import cv2
import os

# Get the absolute path of the directory where this script is located
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Build the exact paths to the video and output folder
# Video to be turned into frames
VIDEO_PATH = os.path.join(SCRIPT_DIR, "Dataset.mp4")

# This is the folder where all the images will be dumped
OUTPUT_FOLDER = os.path.join(SCRIPT_DIR, "dataset_frames")

def extract_frames():
    # 1. Create the output folder if it doesn't already exist
    if not os.path.exists(OUTPUT_FOLDER):
        os.makedirs(OUTPUT_FOLDER)
        print(f"Created directory: {OUTPUT_FOLDER}")

    # 2. Open the video file
    cap = cv2.VideoCapture(VIDEO_PATH)
    
    if not cap.isOpened():
        print(f"ERROR: Could not open '{VIDEO_PATH}'.")
        print("Fix: Ensure the video is in the same folder and the name matches exactly.")
        return

    saved_count = 0

    print(f"Starting extraction from '{VIDEO_PATH}'...")
    
    # 3. Read frame by frame
    while True:
        success, frame = cap.read()
        
        # If success is False, we have reached the end of the video
        if not success:
            break

        # Generate the filename with 4-digit padding (e.g., frame_0042.jpg)
        filename = os.path.join(OUTPUT_FOLDER, f"frame_{saved_count:04d}.jpg")
        
        # Write the image to your hard drive
        cv2.imwrite(filename, frame)
        
        saved_count += 1

    # 4. Clean up resources
    cap.release()
    print(f"SUCCESS: Extracted {saved_count} frames into the '{OUTPUT_FOLDER}' folder.")

if __name__ == "__main__":
    extract_frames()