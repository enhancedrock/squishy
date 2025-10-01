"""Web dashboard for managing bot configurations and modules"""
import os
from functools import wraps
import yaml
from flask import Flask, send_from_directory, request, jsonify, session, redirect, url_for
import market

app = Flask(__name__)

with open ('config.yml', 'r', encoding='utf-8') as configfile:
    config = yaml.safe_load(configfile)

def require_auth(f):
    """Decorator to require authentication for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'authenticated' not in session or not session['authenticated']:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def require_auth_api(f):
    """Decorator to require authentication for API routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'authenticated' not in session or not session['authenticated']:
            return jsonify({'error': 'Authentication required'}), 401
        return f(*args, **kwargs)
    return decorated_function

@app.route('/login')
def login():
    """Serve the login page"""
    return send_from_directory('webui', 'login.html')

@app.route('/login', methods=['POST'])
def login_post():
    """Handle login form submission"""
    data = request.get_json()
    password = data.get('password')

    if password == config['dashboard']['password']:
        session['authenticated'] = True
        return jsonify({'success': True})
    else:
        return jsonify({'success': False, 'error': 'Invalid password'}), 401

@app.route('/logout')
def logout():
    """Log out the user"""
    session.pop('authenticated', None)
    return redirect(url_for('login'))

@app.route('/')
@app.route('/index')
@require_auth
def index():
    """Serve the main dashboard page"""
    return send_from_directory('webui', 'dash.html')

@app.route('/configs')
@require_auth_api
def get_configs():
    """Get list of available configuration files"""
    configs = []
    if config['dashboard']['allow-config-edit']:
        configs.append('Main Bot Config')
    for file in os.listdir('config'):
        if file.endswith('.yml') or file.endswith('.yaml'):
            configs.append(file.strip('.yml').strip('.yaml'))
    return {'configs': configs}

@app.route('/marketenabled')
@require_auth_api
def market_enabled():
    """Check if module editing is enabled"""
    return {'enabled': config['dashboard']['allow-module-edit']}

@app.route('/market')
@require_auth
def marketroute():
    """Serve the module marketplace page"""
    if not config['dashboard']['allow-module-edit']:
        return "Module installation is disabled", 403
    return send_from_directory('webui', 'market.html')

@app.route('/api/repos')
@require_auth_api
def get_repos():
    """Get list of module repositories"""
    if not config['dashboard']['allow-module-edit']:
        return jsonify({'error': 'Module installation is disabled'}), 403

    try:
        repos = market.getrepos()
        return jsonify({'repos': repos})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/modules')
@require_auth_api
def get_modules():
    """Get list of available modules from a repository"""
    if not config['dashboard']['allow-module-edit']:
        return jsonify({'error': 'Module installation is disabled'}), 403

    repo_id = request.args.get('repo_id', 0, type=int)

    try:
        modules = market.list_available_modules(repo_id)
        return jsonify({'modules': modules})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/installed')
@require_auth_api
def get_installed_modules():
    """Get list of currently installed modules"""
    if not config['dashboard']['allow-module-edit']:
        return jsonify({'error': 'Module installation is disabled'}), 403

    try:
        installed = market.get_installed_modules()
        return jsonify({'modules': installed})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/install', methods=['POST'])
@require_auth_api
def install_module():
    """Install a module by name from a repository"""
    if not config['dashboard']['allow-module-edit']:
        return jsonify({'error': 'Module installation is disabled'}), 403

    data = request.get_json()
    module_name = data.get('module_name')
    repo_id = data.get('repo_id', 0)

    if not module_name:
        return jsonify({'error': 'Module name is required'}), 400

    try:
        success = market.install_module_by_name(module_name, repo_id)
        message = 'Module installed successfully' if success else 'Failed to install module'
        return jsonify({'success': success, 'message': message})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/uninstall', methods=['POST'])
@require_auth_api
def uninstall_module():
    """Uninstall a module by source URL"""
    if not config['dashboard']['allow-module-edit']:
        return jsonify({'error': 'Module installation is disabled'}), 403

    data = request.get_json()
    source_url = data.get('source_url')

    if not source_url:
        return jsonify({'error': 'Source URL is required'}), 400

    try:
        success = market.uninstall_module(source_url)
        message = 'Module uninstalled successfully' if success else 'Failed to uninstall module'
        return jsonify({'success': success, 'message': message})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/update', methods=['POST'])
@require_auth_api
def update_module():
    """Update a module by source URL"""
    if not config['dashboard']['allow-module-edit']:
        return jsonify({'error': 'Module installation is disabled'}), 403

    data = request.get_json()
    source_url = data.get('source_url')

    if not source_url:
        return jsonify({'error': 'Source URL is required'}), 400

    try:
        # Find module in repos
        repo_module = market.find_module_in_repos(source_url)
        if not repo_module:
            return jsonify({'error': 'Module not found in repositories'}), 404

        success = market.update_module(repo_module)
        message = 'Module updated successfully' if success else 'Failed to update module'
        return jsonify({'success': success, 'message': message})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/update-all', methods=['POST'])
@require_auth_api
def update_all_modules():
    """Update all installed modules"""
    if not config['dashboard']['allow-module-edit']:
        return jsonify({'error': 'Module installation is disabled'}), 403

    try:
        results = market.update_all_modules()
        return jsonify({'results': results})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/getconfig')
@require_auth_api
def get_config():
    """Get the content of a specified configuration file"""
    config_name = request.headers.get('config')

    if not config_name:
        return jsonify({'error': 'No config name provided in header'}), 400

    try:
        if config_name == 'Main Bot Config':
            # Return the main config.yml file
            with open('config.yml', 'r', encoding='utf-8') as f:
                raw_yaml = f.read()
            return jsonify({'config': raw_yaml, 'name': config_name})
        else:
            # Look for the config file in the config folder
            config_file_path = None
            for file in os.listdir('config'):
                if file.endswith('.yml') or file.endswith('.yaml'):
                    file_name_without_ext = file.replace('.yml', '').replace('.yaml', '')
                    if file_name_without_ext == config_name:
                        config_file_path = os.path.join('config', file)
                        break

            if not config_file_path:
                return jsonify({'error': f'Config file for "{config_name}" not found'}), 404

            with open(config_file_path, 'r', encoding='utf-8') as f:
                raw_yaml = f.read()

            return jsonify({'config': raw_yaml, 'name': config_name})

    except FileNotFoundError:
        return jsonify({'error': 'Config file not found'}), 404
    except Exception as e:
        return jsonify({'error': f'Unexpected error: {str(e)}'}), 500

@app.route('/saveconfig', methods=['POST'])
@require_auth_api
def save_config():
    """Save the content to a specified configuration file"""
    config_name = request.headers.get('config')
    yaml_content = request.get_data(as_text=True)

    if not config_name:
        return jsonify({'error': 'No config name provided in header'}), 400

    if not yaml_content:
        return jsonify({'error': 'No YAML content provided'}), 400

    try:
        # Validate YAML syntax before saving
        yaml.safe_load(yaml_content)

        if config_name == 'Main Bot Config':
            # Save to the main config.yml file
            with open('config.yml', 'w', encoding='utf-8') as f:
                f.write(yaml_content)
        else:
            # Find and save to the config file in the config folder
            config_file_path = None
            for file in os.listdir('config'):
                if file.endswith('.yml') or file.endswith('.yaml'):
                    file_name_without_ext = file.replace('.yml', '').replace('.yaml', '')
                    if file_name_without_ext == config_name:
                        config_file_path = os.path.join('config', file)
                        break

            if not config_file_path:
                return jsonify({'error': f'Config file for "{config_name}" not found'}), 404

            with open(config_file_path, 'w', encoding='utf-8') as f:
                f.write(yaml_content)

        return jsonify({'success': True, 'message': f'Config "{config_name}" saved successfully'})

    except yaml.YAMLError as e:
        return jsonify({'error': f'Invalid YAML syntax: {str(e)}'}), 400
    except FileNotFoundError:
        return jsonify({'error': 'Config file not found'}), 404
    except Exception as e:
        return jsonify({'error': f'Unexpected error: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=False, port=config['dashboard']['port'], host=config['dashboard']['host'])
