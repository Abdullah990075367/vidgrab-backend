import os, re, time, uuid, shutil, threading
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import yt_dlp

app = Flask(__name__)
CORS(app)  # 👈 frontend GitHub Pages se aayega, isliye zaroori

TMP_ROOT = "tmp_downloads"
os.makedirs(TMP_ROOT, exist_ok=True)


def _cleanup_dir(path, delay=20):
    def _do():
        time.sleep(delay)
        shutil.rmtree(path, ignore_errors=True)
    threading.Thread(target=_do, daemon=True).start()


@app.route("/")
def home():
    return jsonify(status="ok", service="VidGrab Backend")


@app.route("/health")
def health():
    return jsonify(ok=True)


@app.route("/info", methods=["POST"])
def get_info():
    data = request.get_json(silent=True) or {}
    url = (data.get("url") or "").strip()
    if not url:
        return jsonify(error="URL zaroori hai"), 400
    try:
        ydl_opts = {"quiet": True, "no_warnings": True,
                    "skip_download": True, "noplaylist": True}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
        heights = set()
        for f in info.get("formats", []):
            if f.get("vcodec") not in (None, "none") and f.get("height"):
                heights.add(int(f["height"]))
        return jsonify({
            "title": info.get("title", "video"),
            "thumbnail": info.get("thumbnail"),
            "duration": info.get("duration"),
            "uploader": info.get("uploader"),
            "resolutions": sorted(heights, reverse=True),
        })
    except Exception as e:
        return jsonify(error=f"Info fetch error: {e}"), 500


@app.route("/download", methods=["POST"])
def download_video():
    data = request.get_json(silent=True) or {}
    url = (data.get("url") or "").strip()
    height_raw = data.get("height", 720)
    if not url:
        return jsonify(error="URL zaroori hai"), 400
    try:
        m = re.match(r"(\d+)", str(height_raw).strip())
        target_height = int(m.group(1)) if m else 720
    except Exception:
        target_height = 720

    job_id = uuid.uuid4().hex[:8]
    job_dir = os.path.join(TMP_ROOT, job_id)
    os.makedirs(job_dir, exist_ok=True)

    fmt = (
        f"bestvideo[height<={target_height}][ext=mp4]+bestaudio[ext=m4a]/"
        f"bestvideo[height<={target_height}]+bestaudio/"
        f"best[height<={target_height}]/best"
    )
    ydl_opts = {
        "format": fmt,
        "outtmpl": os.path.join(job_dir, "%(title)s.%(ext)s"),
        "merge_output_format": "mp4",
        "noplaylist": True,
        "quiet": True, "no_warnings": True,
        "windowsfilenames": True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            final_path = ydl.prepare_filename(info)
        if not final_path.lower().endswith(".mp4"):
            base = os.path.splitext(final_path)[0]
            if os.path.exists(base + ".mp4"):
                final_path = base + ".mp4"
        if not os.path.exists(final_path):
            for f in os.listdir(job_dir):
                if f.lower().endswith(".mp4"):
                    final_path = os.path.join(job_dir, f); break
        if not os.path.exists(final_path):
            return jsonify(error="File create nahi hui"), 500
        safe_name = re.sub(r'[\\/*?:"<>|]', "_", os.path.basename(final_path))
        _cleanup_dir(job_dir, delay=20)
        return send_file(final_path, as_attachment=True,
                         download_name=safe_name, mimetype="video/mp4")
    except Exception as e:
        shutil.rmtree(job_dir, ignore_errors=True)
        return jsonify(error=f"Download error: {e}"), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)