from flask import Flask, request, render_template, jsonify
import subprocess
import uuid
import logging
from datetime import datetime

app = Flask(__name__)

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 配置
FFMPEG_PATH = "/usr/bin/ffmpeg"
RTMP_SERVER = "rtmp://srs:1935/live"  # SRS 容器地址
THIRD_PARTY_BASE_PATH = "rtmp://push-rtmp-l6.douyincdn.com/third/"

# 存储推流进程和配置
stream_processes = {}  # stream_key -> FFmpeg 进程
third_party_configs = {}  # stream_key -> 第三方地址

def generate_stream_key():
    """生成唯一流密钥"""
    return f"stream-{uuid.uuid4().hex}"

def start_ffmpeg_process(stream_key, third_party_url):
    """启动 FFmpeg 转推"""
    input_url = f"{RTMP_SERVER}/{stream_key}"
    ffmpeg_cmd = [
        FFMPEG_PATH, "-i", input_url,
        "-c:v", "copy", "-c:a", "copy", "-f", "flv",
        third_party_url
    ]
    try:
        process = subprocess.Popen(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        logging.info(f"启动 FFmpeg 进程，stream_key: {stream_key}, PID: {process.pid}")
        stream_processes[stream_key] = process
        return True
    except Exception as e:
        logging.error(f"启动 FFmpeg 失败，stream_key: {stream_key}: {str(e)}")
        return False

def stop_ffmpeg_process(stream_key):
    """停止 FFmpeg 进程"""
    if stream_key in stream_processes:
        process = stream_processes[stream_key]
        process.terminate()
        try:
            process.wait(timeout=5)
            logging.info(f"停止 FFmpeg 进程，stream_key: {stream_key}")
        except subprocess.TimeoutExpired:
            process.kill()
            logging.warning(f"强制终止 FFmpeg 进程，stream_key: {stream_key}")
        del stream_processes[stream_key]

@app.route('/')
def index():
    """推流地址生成页面"""
    return render_template('index.html')

@app.route('/config')
def config():
    """第三方地址配置页面"""
    return render_template('config.html')

@app.route('/generate_push_url', methods=['POST'])
def generate_push_url():
    """生成推流地址"""
    client_id = request.form.get('client_id', 'anonymous')
    stream_key = generate_stream_key()
    push_url = f"{RTMP_SERVER}/{stream_key}"
    
    # 默认第三方地址
    timestamp = int(datetime.now().timestamp())
    third_party_params = f"{stream_key}?k=c3625be1c7f8a552&t={timestamp}&t_id={client_id}"
    third_party_url = f"{THIRD_PARTY_BASE_PATH}{third_party_params}"
    third_party_configs[stream_key] = third_party_url
    
    return jsonify({
        'status': 'success',
        'push_url': push_url,
        'stream_key': stream_key,
        'third_party_url': third_party_url
    })

@app.route('/configure_third_party', methods=['POST'])
def configure_third_party():
    """配置第三方推流地址"""
    stream_key = request.form.get('stream_key')
    third_party_url = request.form.get('third_party_url')
    
    if not stream_key or not third_party_url:
        return jsonify({'status': 'error', 'message': '缺少 stream_key 或 third_party_url'}), 400
    
    third_party_configs[stream_key] = third_party_url
    logging.info(f"配置第三方地址，stream_key: {stream_key}, URL: {third_party_url}")
    
    # 如果流正在运行，重新启动 FFmpeg
    if stream_key in stream_processes:
        stop_ffmpeg_process(stream_key)
        start_ffmpeg_process(stream_key, third_party_url)
    
    return jsonify({'status': 'success', 'message': '第三方地址已配置'})

@app.route('/start_stream', methods=['POST'])
def start_stream():
    """启动转推"""
    stream_key = request.form.get('stream_key')
    if stream_key not in third_party_configs:
        return jsonify({'status': 'error', 'message': '流密钥不存在'}), 404
    
    third_party_url = third_party_configs[stream_key]
    if start_ffmpeg_process(stream_key, third_party_url):
        return jsonify({'status': 'success', 'message': '转推已启动'})
    return jsonify({'status': 'error', 'message': '启动转推失败'}), 500

@app.route('/stop_stream', methods=['POST'])
def stop_stream():
    """停止转推"""
    stream_key = request.form.get('stream_key')
    if stream_key not in stream_processes:
        return jsonify({'status': 'error', 'message': '流未运行'}), 404
    
    stop_ffmpeg_process(stream_key)
    return jsonify({'status': 'success', 'message': '转推已停止'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
