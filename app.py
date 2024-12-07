from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS, cross_origin
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import os
import yt_dlp
import threading
import time

app = Flask(__name__)
CORS(app, origins="https://localhost:5173")
app.config['CORS_HEADERS'] = 'Content-Type'

# Initialize Flask-Limiter
limiter = Limiter(
    get_remote_address,  # Use the user's IP address for rate limiting
    app=app,
    default_limits=["10 per 5 minutes"],  # Default rate limit
)

DOWNLOAD_FOLDER = 'downloads'
if not os.path.exists(DOWNLOAD_FOLDER):
    os.makedirs(DOWNLOAD_FOLDER)

# Time (in seconds) after which files will be deleted
FILE_EXPIRATION_TIME = 3600  # 1 hour

def delete_old_files():
    """Background thread to delete files older than FILE_EXPIRATION_TIME."""
    while True:
        current_time = time.time()
        for filename in os.listdir(DOWNLOAD_FOLDER):
            file_path = os.path.join(DOWNLOAD_FOLDER, filename)
            if os.path.isfile(file_path):
                # Check file's last modified time
                file_age = current_time - os.path.getmtime(file_path)
                if file_age > FILE_EXPIRATION_TIME:
                    os.remove(file_path)
                    print(f"Deleted expired file: {file_path}")
        time.sleep(300)  # Check every 5 minutes

@app.route('/download', methods=['POST'])
@cross_origin(origin='*', headers=['Content-Type', 'Authorization'])
@limiter.limit("10 per 5 minutes")  # Apply rate limit to this route
def download_video():
    data = request.json
    video_url = data.get('url')
    quality = data.get('bestvideo+bestaudio/best')  # Default to best quality

    try:
        ydl_opts = {
            'outtmpl': f'{DOWNLOAD_FOLDER}/grab_tube.%(ext)s',
            'format': quality,
            'postprocessors': [{
                'key': 'FFmpegVideoConvertor',
                'preferedformat': 'mp4',  # Corrected spelling
            }],
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)
        
            video_filename = "grab_tube.mp4"
            return jsonify({'status': 'success', 'video_url': f"http://127.0.0.1:5000/downloads/{video_filename}"}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/downloads/<path:filename>', methods=['GET'])
@limiter.limit("20 per hour")  # Optional: Apply rate limit to file downloads
def serve_video(filename):
    """Serve downloaded video files."""
    return send_from_directory(DOWNLOAD_FOLDER, filename)


if __name__ == '__main__':
    # Start the file deletion thread
    deletion_thread = threading.Thread(target=delete_old_files, daemon=True)
    deletion_thread.start()

    app.run(debug=True)