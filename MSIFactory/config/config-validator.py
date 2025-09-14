#!/usr/bin/env python3
"""
MSI Factory Component Configuration Validator
Validates component configuration files against the JSON schema
"""

import json
import sys
import os
from pathlib import Path
from typing import Dict, List, Optional
import jsonschema
from jsonschema import validate, ValidationError
import uuid
import re

class ComponentConfigValidator:
    def __init__(self, schema_path: str = None):
        """Initialize the validator with schema"""
        if schema_path is None:
            schema_path = Path(__file__).parent / "component-schema.json"
        
        with open(schema_path, 'r') as f:
            self.schema = json.load(f)
    
    def validate_config(self, config_data: Dict) -> tuple[bool, List[str]]:
        """
        Validate configuration against schema
        Returns: (is_valid, list_of_errors)
        """
        errors = []
        
        try:
            # JSON Schema validation
            validate(instance=config_data, schema=self.schema)
        except ValidationError as e:
            errors.append(f"Schema validation error: {e.message}")
            return False, errors
        
        # Additional business logic validation
        errors.extend(self._validate_business_rules(config_data))
        
        is_valid = len(errors) == 0
        return is_valid, errors
    
    def _validate_business_rules(self, config: Dict) -> List[str]:
        """Apply business logic validation rules"""
        errors = []
        
        # Validate GUID format
        try:
            uuid.UUID(config['componentId'])
        except ValueError:
            errors.append(f"Invalid GUID format for componentId: {config['componentId']}")
        
        # Validate AppShortKey format
        app_key = config['appShortKey']
        if not re.match(r'^[A-Z0-9]{3,10}$', app_key):
            errors.append(f"AppShortKey must be 3-10 uppercase alphanumeric characters: {app_key}")
        
        # Validate environment names
        valid_environments = {'DEV', 'QA', 'UAT', 'PREPROD', 'PROD', 'SIT', 'DR'}
        for env_name in config['environments'].keys():
            if env_name not in valid_environments:
                errors.append(f"Invalid environment name: {env_name}. Must be one of: {valid_environments}")
        
        # Validate server names (basic FQDN check)
        for env_name, env_config in config['environments'].items():
            for server in env_config['servers']:
                if not re.match(r'^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', server):
                    errors.append(f"Invalid server name in {env_name}: {server}")
        
        # Validate component type vs framework compatibility
        component_type = config['componentType']
        framework = config['framework']
        
        compatibility_matrix = {
            'webapp': ['netframework', 'netcore'],
            'website': ['react', 'angular', 'static'],
            'service': ['netframework', 'netcore'],
            'scheduler': ['netframework', 'netcore']
        }
        
        if framework not in compatibility_matrix.get(component_type, []):
            errors.append(f"Framework '{framework}' is not compatible with component type '{component_type}'")
        
        # Validate service account configuration for services
        if component_type == 'service':
            for env_name, env_config in config['environments'].items():
                if 'serviceAccount' in env_config:
                    sa_config = env_config['serviceAccount']
                    if sa_config.get('type') == 'CustomUser':
                        if not sa_config.get('username'):
                            errors.append(f"CustomUser service account in {env_name} requires username")
        
        # Validate install paths are Windows paths
        for env_name, env_config in config['environments'].items():
            install_path = env_config['installPath']
            if not re.match(r'^[A-Za-z]:\\.*', install_path):
                errors.append(f"Invalid Windows install path in {env_name}: {install_path}")
        
        # Validate artifact URL format
        primary_url = config['artifactSources']['primary']
        if not primary_url.startswith(('http://', 'https://')):
            errors.append(f"Primary artifact source must be HTTP/HTTPS URL: {primary_url}")
        
        # Validate polling frequency format
        if 'pollingFrequency' in config['artifactSources']:
            polling = config['artifactSources']['pollingFrequency']
            if not re.match(r'^\d+[mhd]$', polling):
                errors.append(f"Invalid polling frequency format: {polling}. Use format like '5m', '1h', '2d'")
        
        return errors
    
    def validate_file(self, config_file_path: str) -> tuple[bool, List[str]]:
        """Validate a configuration file"""
        try:
            with open(config_file_path, 'r') as f:
                config_data = json.load(f)
            
            return self.validate_config(config_data)
            
        except FileNotFoundError:
            return False, [f"Configuration file not found: {config_file_path}"]
        except json.JSONDecodeError as e:
            return False, [f"Invalid JSON format: {e}"]
        except Exception as e:
            return False, [f"Validation error: {e}"]

def validate_directory(directory_path: str, validator: ComponentConfigValidator) -> Dict[str, tuple[bool, List[str]]]:
    """Validate all JSON files in a directory"""
    results = {}
    
    for json_file in Path(directory_path).glob("*.json"):
        if json_file.name == "component-schema.json":
            continue  # Skip schema file
            
        is_valid, errors = validator.validate_file(str(json_file))
        results[json_file.name] = (is_valid, errors)
    
    return results

def main():
    if len(sys.argv) < 2:
        print("Usage: python config-validator.py <config-file-or-directory>")
        print("Examples:")
        print("  python config-validator.py webapp-sample.json")
        print("  python config-validator.py ../samples/")
        sys.exit(1)
    
    target_path = sys.argv[1]
    validator = ComponentConfigValidator()
    
    if os.path.isfile(target_path):
        # Validate single file
        print(f"Validating: {target_path}")
        is_valid, errors = validator.validate_file(target_path)
        
        if is_valid:
            print("✅ Configuration is valid!")
        else:
            print("❌ Configuration validation failed:")
            for error in errors:
                print(f"  - {error}")
            sys.exit(1)
    
    elif os.path.isdir(target_path):
        # Validate directory
        print(f"Validating all JSON files in: {target_path}")
        results = validate_directory(target_path, validator)
        
        total_files = len(results)
        valid_files = sum(1 for is_valid, _ in results.values() if is_valid)
        
        print(f"\nValidation Results: {valid_files}/{total_files} files valid")
        print("-" * 50)
        
        for filename, (is_valid, errors) in results.items():
            status = "✅" if is_valid else "❌"
            print(f"{status} {filename}")
            
            if not is_valid:
                for error in errors:
                    print(f"    - {error}")
        
        if valid_files != total_files:
            sys.exit(1)
    
    else:
        print(f"Error: Path not found: {target_path}")
        sys.exit(1)

if __name__ == "__main__":
    main()