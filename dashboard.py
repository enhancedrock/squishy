import yaml
from flask import Flask, send_from_directory, request, jsonify
import os

app = Flask(__name__)

with open ('config.yml', 'r', encoding='utf-8') as f:
    config = yaml.safe_load(f)

@app.route('/')
@app.route('/index')
def index():
    return send_from_directory('webui', 'dash.html')

@app.route('/configs')
def get_configs():
    configs = []
    if config['dashboard']['allow-config-edit']:
        configs.append('Main Bot Config')
    for file in os.listdir('config'):
        if file.endswith('.yml') or file.endswith('.yaml'):
            configs.append(file.strip('.yml').strip('.yaml'))
    return {'configs': configs}

@app.route('/marketenabled')
def market_enabled():
    return {'enabled': config['dashboard']['allow-module-edit']}

@app.route('/market')
def market():
    if not config['dashboard']['allow-module-edit']:
        return "Module installation is disabled", 403
    return send_from_directory('webui', 'market.html')

@app.route('/api/repos')
def get_repos():
    if not config['dashboard']['allow-module-edit']:
        return jsonify({'error': 'Module installation is disabled'}), 403
    
    try:
        import market
        repos = market.getrepos()
        return jsonify({'repos': repos})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/modules')
def get_modules():
    if not config['dashboard']['allow-module-edit']:
        return jsonify({'error': 'Module installation is disabled'}), 403
    
    repo_id = request.args.get('repo_id', 0, type=int)
    
    try:
        import market
        modules = market.list_available_modules(repo_id)
        return jsonify({'modules': modules})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/installed')
def get_installed_modules():
    if not config['dashboard']['allow-module-edit']:
        return jsonify({'error': 'Module installation is disabled'}), 403
    
    try:
        import market
        installed = market.get_installed_modules()
        return jsonify({'modules': installed})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/install', methods=['POST'])
def install_module():
    if not config['dashboard']['allow-module-edit']:
        return jsonify({'error': 'Module installation is disabled'}), 403
    
    data = request.get_json()
    module_name = data.get('module_name')
    repo_id = data.get('repo_id', 0)
    
    if not module_name:
        return jsonify({'error': 'Module name is required'}), 400
    
    try:
        import market
        success = market.install_module_by_name(module_name, repo_id)
        return jsonify({'success': success, 'message': 'Module installed successfully' if success else 'Failed to install module'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/uninstall', methods=['POST'])
def uninstall_module():
    if not config['dashboard']['allow-module-edit']:
        return jsonify({'error': 'Module installation is disabled'}), 403
    
    data = request.get_json()
    source_url = data.get('source_url')
    
    if not source_url:
        return jsonify({'error': 'Source URL is required'}), 400
    
    try:
        import market
        success = market.uninstall_module(source_url)
        return jsonify({'success': success, 'message': 'Module uninstalled successfully' if success else 'Failed to uninstall module'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/update', methods=['POST'])
def update_module():
    if not config['dashboard']['allow-module-edit']:
        return jsonify({'error': 'Module installation is disabled'}), 403
    
    data = request.get_json()
    source_url = data.get('source_url')
    
    if not source_url:
        return jsonify({'error': 'Source URL is required'}), 400
    
    try:
        import market
        # Find module in repos
        repo_module = market.find_module_in_repos(source_url)
        if not repo_module:
            return jsonify({'error': 'Module not found in repositories'}), 404
        
        success = market.update_module(repo_module)
        return jsonify({'success': success, 'message': 'Module updated successfully' if success else 'Failed to update module'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/update-all', methods=['POST'])
def update_all_modules():
    if not config['dashboard']['allow-module-edit']:
        return jsonify({'error': 'Module installation is disabled'}), 403
    
    try:
        import market
        results = market.update_all_modules()
        return jsonify({'results': results})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/getconfig')
def get_config():
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
        return jsonify({'error': f'Config file not found'}), 404
    except Exception as e:
        return jsonify({'error': f'Unexpected error: {str(e)}'}), 500

@app.route('/saveconfig', methods=['POST'])
def save_config():
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
        return jsonify({'error': f'Config file not found'}), 404
    except Exception as e:
        return jsonify({'error': f'Unexpected error: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(debug=False, port=config['dashboard']['port'], host=config['dashboard']['host'])