import logging
import os
import flask
import flask_socketio
import hid
import js_to_hid

# Setup logging with formatter that only shows timestamp for INFO level
root_logger = logging.getLogger()
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(message)s', '%Y-%m-%d %H:%M:%S')
handler.setFormatter(formatter)
root_logger.addHandler(flask.logging.default_handler)
root_logger.setLevel(logging.INFO)

app = flask.Flask(__name__, static_url_path='')
socketio = flask_socketio.SocketIO(app)

logger = logging.getLogger(__name__)
logger.info('Starting app')

host = os.environ.get('HOST', '0.0.0.0')
port = int(os.environ.get('PORT', 8000))
debug = 'DEBUG' in os.environ
hid_path = os.environ.get('HID_PATH', '/dev/hidg0')

def _parse_key_event(payload):
    return js_to_hid.JavaScriptKeyEvent(meta_modifier=payload['metaKey'],
                                       alt_modifier=payload['altKey'],
                                       shift_modifier=payload['shiftKey'],
                                       ctrl_modifier=payload['ctrlKey'],
                                       key=payload['key'],
                                       key_code=payload['keyCode'])

@socketio.on('keystroke')
def socket_keystroke(message):
    key_event = _parse_key_event(message)
    hid_keycode = None
    success = False
    
    # Wrap the HID operations in try-except blocks
    try:
        control_keys, hid_keycode = js_to_hid.convert(key_event)
        
        try:
            with open(hid_path, 'wb+') as hid_handle:
                hid.send(hid_handle, control_keys, hid_keycode)
                success = True
        except PermissionError:
            # Silently handle the permission error for file operations
            # But still log the keystroke event
            logger.info(f'Keystroke received: {message}')
            
    except js_to_hid.UnrecognizedKeyCodeError:
        logger.info('Unrecognized key: %s (keycode=%d)', key_event.key,
                   key_event.key_code)
        
    if hid_keycode is None:
        logger.info('Ignoring %s key (keycode=%d)', key_event.key,
                   key_event.key_code)
    
    socketio.emit('keystroke-received', {'success': success})

@socketio.on('connect')
def test_connect():
    logger.info('Client connected')

@socketio.on('disconnect')
def test_disconnect():
    logger.info('Client disconnected')

@app.route('/', methods=['GET'])
def index_get():
    return flask.render_template('index.html')

if __name__ == '__main__':
    socketio.run(app,
                host=host,
                port=port,
                debug=debug,
                use_reloader=True,
                extra_files=[
                    './app/templates/index.html',
                    './app/static/js/app.js',
                    './app/static/css/style.css',
                ])
