"""Utilities for managing modules from online repositories"""
import os
import importlib.util
import importlib
from typing import List, Dict, Optional, Tuple
import yaml
import requests

with open ('config.yml', 'r', encoding='utf-8') as configfile:
    config = yaml.safe_load(configfile)

def getrepos():
    """Get all repos in the config"""
    repos = []
    bwa = "https://raw.githubusercontent.com/enhancedrock/squishymodules/refs/heads/main/repod.json"
    repos.append(bwa)
    # Filter out None/empty values from config repos
    config_repos = [repo for repo in config['market']['repos'] if repo and repo.strip()]
    repos.extend(config_repos)
    return repos

def getrepojson(repoid: int):
    """Get the repo JSON from a repo ID"""
    repos = getrepos()
    repo_url = repos[repoid]
    response = requests.get(repo_url, timeout=5)
    repo_json = response.json()
    return repo_json

def get_installed_modules() -> Dict[str, Dict]:
    """Get all installed modules with their metadata"""
    modules_dir = "modules"
    installed_modules = {}

    if not os.path.exists(modules_dir):
        return installed_modules

    for filename in os.listdir(modules_dir):
        if filename.endswith('.py') and not filename.startswith('__'):
            module_path = os.path.join(modules_dir, filename)
            try:
                spec = importlib.util.spec_from_file_location(filename[:-3], module_path)
                if spec and spec.loader:
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)

                    # Extract module attributes
                    module_info = {}
                    if hasattr(module, 'NAME'):
                        module_info['name'] = module.NAME
                    if hasattr(module, 'VERSION'):
                        module_info['version'] = module.VERSION
                    if hasattr(module, 'SOURCE'):
                        module_info['source'] = module.SOURCE
                    if hasattr(module, 'DESCRIPTION'):
                        module_info['description'] = module.DESCRIPTION
                    if hasattr(module, 'AUTHOR'):
                        module_info['author'] = module.AUTHOR

                    module_info['filename'] = filename
                    installed_modules[filename[:-3]] = module_info
            except (ImportError, AttributeError, FileNotFoundError) as e:
                print(f"Error loading module {filename}: {e}")
                continue

    return installed_modules

def is_module_installed(source_url: str) -> bool:
    """Check if a module is already installed by matching its source URL"""
    installed_modules = get_installed_modules()

    for module_info in installed_modules.values():
        if module_info.get('source') == source_url:
            return True
    return False

def add_module_to_config(module_filename: str) -> bool:
    """Add a module to the enabled modules list in config.yml"""
    try:
        # Read current config
        with open('config.yml', 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f)

        # Get module name without .py extension
        module_name = module_filename[:-3] if module_filename.endswith('.py') else module_filename

        # Ensure market.enabled exists and is a list
        if 'market' not in config_data:
            config_data['market'] = {}
        if 'enabled' not in config_data['market']:
            config_data['market']['enabled'] = []

        # Add module if not already in the list
        if module_name not in config_data['market']['enabled']:
            config_data['market']['enabled'].append(module_name)

            # Write updated config back to file
            with open('config.yml', 'w', encoding='utf-8') as f:
                yaml.dump(config_data, f, default_flow_style=False, sort_keys=False)

            print(f"Added {module_name} to enabled modules in config.yml")
            return True
        else:
            print(f"Module {module_name} is already enabled in config.yml")
            return True

    except (IOError, yaml.YAMLError) as e:
        print(f"Failed to update config.yml: {e}")
        return False

def install_module(module_data: Dict) -> bool:
    """Install a module from module data"""
    try:
        source_url = module_data['source']
        module_name = module_data['name']

        # Check if already installed
        if is_module_installed(source_url):
            print(f"Module {module_name} is already installed.")
            return False

        # Download the module
        response = requests.get(source_url, timeout=10)
        response.raise_for_status()

        # Generate filename from module name (sanitize for filesystem)
        filename = module_name.lower().replace(' ', '_').replace('-', '_')
        # Remove any characters that aren't alphanumeric or underscore
        filename = ''.join(c for c in filename if c.isalnum() or c == '_')
        filename += '.py'

        # Ensure modules directory exists
        os.makedirs('modules', exist_ok=True)

        # Save the module
        module_path = os.path.join('modules', filename)
        with open(module_path, 'w', encoding='utf-8') as file:
            file.write(response.text)

        # Add module to config.yml enabled list
        if not add_module_to_config(filename):
            print(f"Warning: Failed to add {module_name} to config.yml enabled list")

        print(f"Successfully installed module: {module_name}")
        return True

    except (requests.RequestException, IOError, OSError) as e:
        print(f"Failed to install module {module_data.get('name', 'Unknown')}: {e}")
        return False

def remove_module_from_config(module_filename: str) -> bool:
    """Remove a module from the enabled modules list in config.yml"""
    try:
        # Read current config
        with open('config.yml', 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f)

        # Get module name without .py extension
        module_name = module_filename[:-3] if module_filename.endswith('.py') else module_filename

        # Check if market.enabled exists and remove the module
        if 'market' in config_data and 'enabled' in config_data['market']:
            if module_name in config_data['market']['enabled']:
                config_data['market']['enabled'].remove(module_name)

                # Write updated config back to file
                with open('config.yml', 'w', encoding='utf-8') as f:
                    yaml.dump(config_data, f, default_flow_style=False, sort_keys=False)

                print(f"Removed {module_name} from enabled modules in config.yml")
                return True
            else:
                print(f"Module {module_name} was not in enabled list")
                return True
        else:
            print("No enabled modules list found in config.yml")
            return True

    except (IOError, yaml.YAMLError) as e:
        print(f"Failed to update config.yml: {e}")
        return False

def uninstall_module(source_url: str) -> bool:
    """Uninstall a module by its source URL"""
    installed_modules = get_installed_modules()

    for module_name, module_info in installed_modules.items():
        if module_info.get('source') == source_url:
            try:
                module_path = os.path.join('modules', module_info['filename'])
                os.remove(module_path)

                # Remove module from config.yml enabled list
                if not remove_module_from_config(module_info['filename']):
                    name = module_info.get('name', 'Unknown')
                    print(f"Warning: Failed to remove {name} from config.yml enabled list")

                print(f"Successfully uninstalled module: {module_info.get('name', 'Unknown')}")
                return True
            except (OSError, FileNotFoundError) as e:
                print(f"Failed to uninstall module {module_info.get('name', 'Unknown')}: {e}")
                return False

    print("Module not found for uninstallation.")
    return False

def can_module_be_updated(module_data: Dict) -> Tuple[bool, Optional[str], Optional[str]]:
    """Check if a module can be updated (installed version is lower than repo version)"""
    source_url = module_data['source']
    repo_version = module_data['version']

    installed_modules = get_installed_modules()

    for module_info in installed_modules.values():
        if module_info.get('source') == source_url:
            installed_version = module_info.get('version')
            if installed_version and _compare_versions(installed_version, repo_version) < 0:
                return True, installed_version, repo_version
            else:
                return False, installed_version, repo_version

    return False, None, repo_version

def _compare_versions(version1: str, version2: str) -> int:
    """Compare two versions. -1 if version1 < version2, 0 if equal, 1 if version1 > version2"""
    def normalize_version(v):
        parts = v.split('.')
        # Pad with zeros to ensure same length
        while len(parts) < 3:
            parts.append('0')
        return [int(x) for x in parts]

    v1_parts = normalize_version(version1)
    v2_parts = normalize_version(version2)

    for i in range(max(len(v1_parts), len(v2_parts))):
        v1_part = v1_parts[i] if i < len(v1_parts) else 0
        v2_part = v2_parts[i] if i < len(v2_parts) else 0

        if v1_part < v2_part:
            return -1
        elif v1_part > v2_part:
            return 1

    return 0

def update_module(module_data: Dict) -> bool:
    """Update an installed module"""
    source_url = module_data['source']

    # Check if update is needed
    can_update, current_version, new_version = can_module_be_updated(module_data)
    if not can_update:
        print(f"Module {module_data['name']} is already up to date (version {current_version}).")
        return False

    # Uninstall the old version
    if not uninstall_module(source_url):
        print(f"Failed to uninstall old version of {module_data['name']}")
        return False

    # Install the new version
    if install_module(module_data):
        print(f"Successfully updated {module_data['name']} from {current_version} to {new_version}")
        return True
    else:
        print(f"Failed to install new version of {module_data['name']}")
        return False

def get_module_soft_dependencies(module_data: Dict) -> List[Dict]:
    """Get soft dependencies for a module"""
    soft_deps = []

    if 'dependencies' in module_data:
        for dep in module_data['dependencies']:
            if dep.get('soft', False):
                soft_deps.append(dep)

    return soft_deps

def get_module_dependencies(module_data: Dict) -> List[Dict]:
    """Get all dependencies (both hard and soft) for a module"""
    return module_data.get('dependencies', [])

def find_module_in_repos(module_source_url: str) -> Optional[Dict]:
    """Find a module in available repos by its source URL"""
    repos = getrepos()

    for i, repo_url in enumerate(repos):
        try:
            repo_json = getrepojson(i)
            for module in repo_json.get('modules', []):
                if module.get('source') == module_source_url:
                    return module
        except (requests.RequestException, KeyError, ValueError) as e:
            print(f"Error searching repo {repo_url}: {e}")
            continue

    return None

def install_module_dependencies(module_data: Dict, include_soft: bool = False) -> bool:
    """Install dependencies for a module"""
    dependencies = get_module_dependencies(module_data)
    if not dependencies:
        print(f"No dependencies found for module {module_data['name']}")
        return True

    success = True
    for dep in dependencies:
        # Skip soft dependencies unless requested
        if dep.get('soft', False) and not include_soft:
            print(f"Skipping soft dependency: {dep.get('module', 'Unknown')}")
            continue

        dep_source = dep.get('module')
        if not dep_source:
            print(f"Invalid dependency specification in {module_data['name']}")
            success = False
            continue

        # Check if dependency is already installed
        if is_module_installed(dep_source):
            print(f"Dependency already installed: {dep_source}")
            continue

        # Find the dependency module in repos
        dep_module = find_module_in_repos(dep_source)
        if not dep_module:
            print(f"Could not find dependency module: {dep_source}")
            success = False
            continue

        # Recursively install dependencies of this dependency
        if not install_module_dependencies(dep_module, include_soft):
            print(f"Failed to install dependencies for: {dep_module['name']}")
            success = False

        # Install the dependency
        if not install_module(dep_module):
            print(f"Failed to install dependency: {dep_module['name']}")
            success = False

    return success

def install_module_by_name(module_name: str, repo_id: int = 0) -> bool:
    """Install a module by its name from a specific repository"""
    try:
        repo_json = getrepojson(repo_id)
        for module in repo_json.get('modules', []):
            if module.get('name').lower() == module_name.lower():
                # Install dependencies first
                if not install_module_dependencies(module, include_soft=False):
                    print(f"Warning: Some dependencies failed to install for {module_name}")

                return install_module(module)

        print(f"Module '{module_name}' not found in repository")
        return False

    except (requests.RequestException, KeyError, ValueError) as e:
        print(f"Error installing module {module_name}: {e}")
        return False

def update_all_modules() -> Dict[str, bool]:
    """Update all installed modules that have updates available"""
    installed_modules = get_installed_modules()
    update_results = {}

    for module_info in installed_modules.values():
        source_url = module_info.get('source')
        if not source_url:
            continue

        # Find the module in repos
        repo_module = find_module_in_repos(source_url)
        if not repo_module:
            continue

        # Check if update is available
        can_update, current_version, new_version = can_module_be_updated(repo_module)
        if can_update:
            module_name = module_info.get('name', 'Unknown')
            print(f"Updating {module_name} from {current_version} to {new_version}")
            update_results[module_name] = update_module(repo_module)

    return update_results

def list_available_modules(repo_id: int = 0) -> List[Dict]:
    """List all available modules in a repository"""
    try:
        repo_json = getrepojson(repo_id)
        return repo_json.get('modules', [])
    except (requests.RequestException, KeyError, ValueError) as e:
        print(f"Error fetching repository modules: {e}")
        return []

def get_module_info(module_name: str, repo_id: int = 0) -> Optional[Dict]:
    """Get detailed information about a specific module"""
    try:
        repo_json = getrepojson(repo_id)
        for module in repo_json.get('modules', []):
            if module.get('name').lower() == module_name.lower():
                return module
        return None
    except (requests.RequestException, KeyError, ValueError) as e:
        print(f"Error fetching module info for {module_name}: {e}")
        return None
