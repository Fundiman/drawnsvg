from flask import Flask, render_template, Response
from flask_socketio import SocketIO, emit
import io, threading, time, logging, os
from datetime import datetime

ip = '37.27.51.34'
port = 3219

app = Flask(__name__)
socketio = SocketIO(app)

svg_elements = []
cached_svg = None
is_svg_dirty = True

# 🧠 Logging setup — we're goin' deep bruh
logging.basicConfig(
    level=logging.DEBUG,
    format='[%(asctime)s] [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler("server.log"),  # Logs to file
        logging.StreamHandler()             # Also logs to console
    ]
)

def save_svg_to_disk():
    global cached_svg
    logging.info("🧠 Background disk-saving thread started.")
    while True:
        time.sleep(60)
        if cached_svg:
            try:
                file_path = os.path.abspath("drawing.svg")
                with open(file_path, "wb") as f:
                    f.write(cached_svg)
                logging.info(f"💾 SVG cached content saved to disk at {file_path}")
            except Exception as e:
                logging.error(f"❌ Error saving SVG to disk: {e}")
        else:
            logging.debug("⏳ No SVG in cache to save.")

@app.route('/')
def index():
    logging.info("🌐 GET / -> Sending index.html to client")
    return render_template('index.html')

@app.route('/drawing.svg')
def drawing_svg():
    global cached_svg, is_svg_dirty
    logging.info("🖼️ GET /drawing.svg -> Client wants the SVG")

    if is_svg_dirty or cached_svg is None:
        logging.info("🔧 SVG is dirty or missing. Rebuilding cache...")
        try:
            svg_content = '<svg xmlns="http://www.w3.org/2000/svg" width="1920" height="1080">\n'
            for i, line in enumerate(svg_elements):
                svg_content += f'<line x1="{line["x1"]}" y1="{line["y1"]}" x2="{line["x2"]}" y2="{line["y2"]}" stroke="black" stroke-width="2"/>\n'
                logging.debug(f"📏 Line {i+1}: {line}")
            svg_content += '</svg>'
            cached_svg = svg_content.encode('utf-8')
            is_svg_dirty = False
            logging.info("✅ SVG cache rebuilt successfully.")
        except Exception as e:
            logging.error(f"❌ Error building SVG: {e}")
            return Response("Error generating SVG", status=500)

    return Response(cached_svg, mimetype='image/svg+xml')

@socketio.on('connect')
def handle_connect():
    logging.info("⚡ Socket connected: Sending existing lines to new client.")
    for line in svg_elements:
        emit('line', line)
    logging.debug(f"📤 Sent {len(svg_elements)} lines to new client.")

@socketio.on('line')
def handle_line(data):
    global is_svg_dirty, cached_svg
    logging.info(f"🎨 Received line from client: {data}")
    svg_elements.append(data)
    is_svg_dirty = True

    # Try to rebuild cache immediately
    try:
        svg_content = '<svg xmlns="http://www.w3.org/2000/svg" width="1920" height="1080">\n'
        for line in svg_elements:
            svg_content += f'<line x1="{line["x1"]}" y1="{line["y1"]}" x2="{line["x2"]}" y2="{line["y2"]}" stroke="black" stroke-width="2"/>\n'
        svg_content += '</svg>'
        cached_svg = svg_content.encode('utf-8')
        logging.debug("🔁 SVG cache updated on new line.")
    except Exception as e:
        logging.error(f"❌ Error updating SVG cache after line: {e}")

    emit('line', data, broadcast=True)
    logging.info("📡 Broadcasted new line to all clients.")

if __name__ == '__main__':
    logging.info(f"🚀 DrawnSVG Collab Server STARTING on http://{ip}:{port}")
    logging.info(f"📁 Current working directory: {os.getcwd()}")

    threading.Thread(target=save_svg_to_disk, daemon=True).start()
    socketio.run(app, port=port, host='0.0.0.0')
