import os
import time
import json
import datetime
import google_auth_httplib2
import google_auth_oauthlib
import googleapiclient.discovery
import googleapiclient.errors
import googleapiclient.http

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
TOKEN_FILE = 'token.json'
CONFIG_FILE = 'last_uploaded.json'  # File to track the last uploaded video
WATCH_FOLDER = 'f:\\VOD'  # Path to the folder containing videos


def authenticate_youtube():
    os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

    if os.path.exists(TOKEN_FILE):
        os.remove(TOKEN_FILE)

    client_secrets_file = "/Users/msaur/Desktop/youtube-uploader/client.json"

    flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
        client_secrets_file, SCOPES
    )
    credentials = flow.run_local_server()

    youtube = googleapiclient.discovery.build(
        "youtube", "v3", credentials=credentials
    )

    return youtube


def get_last_uploaded():
    """Retrieve the last uploaded video's timestamp from the config file."""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            data = json.load(f)
            return data.get("last_uploaded", 0)  # Default to 0 if key is missing
    return 0


def update_last_uploaded(timestamp):
    """Update the last uploaded video's timestamp in the config file."""
    with open(CONFIG_FILE, 'w') as f:
        json.dump({"last_uploaded": timestamp}, f)


def get_new_videos(folder, last_timestamp):
    """Find new videos added since the last timestamp."""
    videos = []
    for file in os.listdir(folder):
        file_path = os.path.join(folder, file)
        if os.path.isfile(file_path) and file.lower().endswith(('.mp4', '.mov', '.avi')):
            if os.path.getmtime(file_path) > last_timestamp:
                videos.append(file_path)

    # Sort videos by modification time (oldest first)
    videos.sort(key=os.path.getmtime)
    return videos


def get_video_date(video_path):
    """Extract the modification date of the video file."""
    timestamp = os.path.getmtime(video_path)
    return datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d')


def upload_video(youtube, video_path):
    """Upload a video to YouTube and delete it locally after upload."""
    video_date = get_video_date(video_path)
    request_body = {
        "snippet": {
            "categoryId": "22",
            "title": f"PRAC {video_date}",  # Set title with 'PRAC' and the video's date
            "description": "This is an awesome video uploaded automatically!",
            "tags": ["test", "python", "api"]
        },
        "status": {
            "privacyStatus": "private"
        }
    }

    request = youtube.videos().insert(
        part="snippet,status",
        body=request_body,
        media_body=googleapiclient.http.MediaFileUpload(video_path, chunksize=-1, resumable=True)
    )

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"Upload {int(status.progress() * 100)}% complete.")

    print(f"Video uploaded with ID: {response['id']}")

    # Delete the video file after successful upload
    try:
        os.remove(video_path)
        print(f"Deleted local file: {video_path}")
    except Exception as e:
        print(f"Error deleting file {video_path}: {e}")


if __name__ == "__main__":
    # Step 1: Authenticate with YouTube
    youtube = authenticate_youtube()

    # Step 2: Get the last uploaded timestamp
    last_uploaded_timestamp = get_last_uploaded()

    # Step 3: Check for new videos in the folder
    new_videos = get_new_videos(WATCH_FOLDER, last_uploaded_timestamp)

    if new_videos:
        # Step 4: Upload new videos and update the last uploaded timestamp
        for video in new_videos:
            print(f"Uploading {video}...")
            upload_video(youtube, video)

        # Update the timestamp of the last uploaded video
        latest_timestamp = max(os.path.getmtime(v) for v in new_videos)
        update_last_uploaded(latest_timestamp)

        print("All new videos have been uploaded.")
    else:
        print("No new videos to upload.")
