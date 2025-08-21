from flask import Flask, request, jsonify, send_from_directory, render_template
import subprocess
import logging

app = Flask(__name__, static_folder='static', template_folder='templates')

# Set up logging to app.log at INFO level
logging.basicConfig(filename='app.log', level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')

@app.route('/')
def serve_index():
    return render_template('index.html')

@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory(app.static_folder, filename)

@app.route('/execute', methods=['POST'])
def execute():
    data = request.get_json()
    user_command = data.get('command')
    if not user_command:
        return jsonify({'status': 'error', 'error': 'No command provided'}), 400
    
    # Build the full command as a list to avoid shell injection
    full_command = ['python3', 'send_keystrokes.py', user_command]
    
    try:
        result = subprocess.run(full_command, capture_output=True, text=True)
        output = result.stdout.strip() + ('\n' + result.stderr.strip() if result.stderr else '')
        logging.info(f'Executed: {full_command} | Return code: {result.returncode} | Output: {output}')
        
        if result.returncode == 0:
            return jsonify({'status': 'success', 'output': output})
        else:
            return jsonify({'status': 'error', 'error': output}), 500
    except Exception as e:
        logging.error(f'Exception executing command: {e}')
        return jsonify({'status': 'error', 'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
