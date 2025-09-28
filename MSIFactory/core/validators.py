"""
Validators Module
Server-side validation functions - replaces JavaScript validation
"""

import re
import os
import urllib.parse
from typing import List, Tuple, Dict, Any
from logger import get_logger, log_info, log_error
from core.utilities import validate_guid_format, get_framework_options, get_component_type_options

logger = get_logger()

class ValidationResult:
    """Container for validation results"""
    def __init__(self, is_valid: bool = True, errors: List[str] = None, warnings: List[str] = None):
        self.is_valid = is_valid
        self.errors = errors or []
        self.warnings = warnings or []

    def add_error(self, error: str):
        self.errors.append(error)
        self.is_valid = False

    def add_warning(self, warning: str):
        self.warnings.append(warning)

    def merge(self, other):
        """Merge another validation result"""
        if not other.is_valid:
            self.is_valid = False
        self.errors.extend(other.errors)
        self.warnings.extend(other.warnings)

class ProjectValidator:
    """Validates project-related data"""

    @staticmethod
    def validate_project_data(project_data: Dict[str, Any]) -> ValidationResult:
        """
        Validate complete project data
        Replaces JavaScript validateAndSubmit()
        """
        result = ValidationResult()

        # Required fields validation
        required_fields = {
            'project_name': 'Project name',
            'project_key': 'Project key',
            'project_type': 'Project type',
            'owner_team': 'Owner team'
        }

        for field, display_name in required_fields.items():
            if not project_data.get(field, '').strip():
                result.add_error(f"{display_name} is required")

        # Project name validation
        name_validation = ProjectValidator.validate_project_name(project_data.get('project_name', ''))
        result.merge(name_validation)

        # Project key validation
        key_validation = ProjectValidator.validate_project_key(project_data.get('project_key', ''))
        result.merge(key_validation)

        # GUID validation
        if project_data.get('project_guid'):
            guid_validation = ProjectValidator.validate_guid(project_data['project_guid'])
            result.merge(guid_validation)

        # Project type validation
        type_validation = ProjectValidator.validate_project_type(project_data.get('project_type', ''))
        result.merge(type_validation)

        # Owner team validation
        team_validation = ProjectValidator.validate_owner_team(project_data.get('owner_team', ''))
        result.merge(team_validation)

        # Color validation
        color_validation = ProjectValidator.validate_colors(
            project_data.get('color_primary', ''),
            project_data.get('color_secondary', '')
        )
        result.merge(color_validation)

        # Description length validation
        description = project_data.get('description', '')
        if description and len(description) > 1000:
            result.add_warning("Description is very long and may be truncated")

        log_info(f"Project validation completed: {'PASSED' if result.is_valid else 'FAILED'}")
        return result

    @staticmethod
    def validate_project_name(project_name: str) -> ValidationResult:
        """Validate project name"""
        result = ValidationResult()

        if not project_name or not project_name.strip():
            result.add_error("Project name is required")
            return result

        name = project_name.strip()

        # Length validation
        if len(name) < 2:
            result.add_error("Project name must be at least 2 characters")
        elif len(name) > 100:
            result.add_error("Project name must be less than 100 characters")

        # Character validation
        if not re.match(r'^[a-zA-Z0-9\s\-_\.]+$', name):
            result.add_error("Project name contains invalid characters. Use only letters, numbers, spaces, hyphens, underscores, and periods")

        # Reserved names
        reserved_names = ['admin', 'api', 'system', 'config', 'test', 'temp', 'log', 'logs']
        if name.lower() in reserved_names:
            result.add_error(f"'{name}' is a reserved name and cannot be used")

        return result

    @staticmethod
    def validate_project_key(project_key: str) -> ValidationResult:
        """
        Validate project key format
        Replaces JavaScript pattern validation
        """
        result = ValidationResult()

        if not project_key or not project_key.strip():
            result.add_error("Project key is required")
            return result

        key = project_key.strip().upper()

        # Length validation
        if len(key) < 2:
            result.add_error("Project key must be at least 2 characters")
        elif len(key) > 10:
            result.add_error("Project key must be 10 characters or less")

        # Format validation
        if not re.match(r'^[A-Z0-9]+$', key):
            result.add_error("Project key must contain only uppercase letters and numbers")

        # Must start with letter
        if key and not key[0].isalpha():
            result.add_error("Project key must start with a letter")

        # Reserved keys
        reserved_keys = ['ADMIN', 'API', 'SYS', 'TEST', 'TEMP', 'LOG', 'NULL', 'TRUE', 'FALSE']
        if key in reserved_keys:
            result.add_error(f"'{key}' is a reserved key and cannot be used")

        return result

    @staticmethod
    def validate_guid(guid: str) -> ValidationResult:
        """Validate GUID format"""
        result = ValidationResult()

        if not guid:
            result.add_error("GUID is required")
            return result

        is_valid, error_msg = validate_guid_format(guid)
        if not is_valid:
            result.add_error(error_msg)

        return result

    @staticmethod
    def validate_project_type(project_type: str) -> ValidationResult:
        """Validate project type"""
        result = ValidationResult()

        valid_types = ['WebApp', 'Service', 'Website', 'Desktop', 'API']

        if not project_type:
            result.add_error("Project type is required")
        elif project_type not in valid_types:
            result.add_error(f"Invalid project type. Must be one of: {', '.join(valid_types)}")

        return result

    @staticmethod
    def validate_owner_team(owner_team: str) -> ValidationResult:
        """Validate owner team"""
        result = ValidationResult()

        if not owner_team or not owner_team.strip():
            result.add_error("Owner team is required")
            return result

        team = owner_team.strip()

        if len(team) < 2:
            result.add_error("Owner team name must be at least 2 characters")
        elif len(team) > 100:
            result.add_error("Owner team name must be less than 100 characters")

        # Basic format validation
        if not re.match(r'^[a-zA-Z0-9\s\-_\.]+$', team):
            result.add_error("Owner team contains invalid characters")

        return result

    @staticmethod
    def validate_colors(primary_color: str, secondary_color: str) -> ValidationResult:
        """Validate color values"""
        result = ValidationResult()

        # Hex color pattern
        hex_pattern = r'^#[0-9A-Fa-f]{6}$'

        if primary_color and not re.match(hex_pattern, primary_color):
            result.add_error("Primary color must be a valid hex color (e.g., #2c3e50)")

        if secondary_color and not re.match(hex_pattern, secondary_color):
            result.add_error("Secondary color must be a valid hex color (e.g., #3498db)")

        return result

class ComponentValidator:
    """Validates component-related data"""

    @staticmethod
    def validate_component_data(component_data: Dict[str, Any], existing_components: List[str] = None) -> ValidationResult:
        """
        Validate complete component data
        Replaces JavaScript component validation
        """
        result = ValidationResult()

        # Required fields validation
        required_fields = {
            'component_name': 'Component name',
            'component_type': 'Component type',
            'framework': 'Framework'
        }

        for field, display_name in required_fields.items():
            if not component_data.get(field, '').strip():
                result.add_error(f"{display_name} is required")

        # Component name validation
        name_validation = ComponentValidator.validate_component_name(
            component_data.get('component_name', ''),
            existing_components or []
        )
        result.merge(name_validation)

        # Component type validation
        type_validation = ComponentValidator.validate_component_type(component_data.get('component_type', ''))
        result.merge(type_validation)

        # Framework validation
        framework_validation = ComponentValidator.validate_framework(component_data.get('framework', ''))
        result.merge(framework_validation)

        # GUID validation
        if component_data.get('component_guid'):
            guid_validation = ComponentValidator.validate_guid(component_data['component_guid'])
            result.merge(guid_validation)

        log_info(f"Component validation completed: {'PASSED' if result.is_valid else 'FAILED'}")
        return result

    @staticmethod
    def validate_component_name(component_name: str, existing_names: List[str] = None) -> ValidationResult:
        """Validate component name and check for duplicates"""
        result = ValidationResult()

        if not component_name or not component_name.strip():
            result.add_error("Component name is required")
            return result

        name = component_name.strip()

        # Length validation
        if len(name) < 2:
            result.add_error("Component name must be at least 2 characters")
        elif len(name) > 50:
            result.add_error("Component name must be less than 50 characters")

        # Character validation (more restrictive for components)
        if not re.match(r'^[a-zA-Z0-9\-_]+$', name):
            result.add_error("Component name can only contain letters, numbers, hyphens, and underscores")

        # Must start with letter
        if name and not name[0].isalpha():
            result.add_error("Component name must start with a letter")

        # Check for duplicates
        if existing_names and name.lower() in [n.lower() for n in existing_names]:
            result.add_error(f"Component name '{name}' already exists in this project")

        # Reserved names
        reserved_names = ['admin', 'api', 'system', 'config', 'test', 'temp', 'log', 'main', 'default']
        if name.lower() in reserved_names:
            result.add_error(f"'{name}' is a reserved name and cannot be used")

        return result

    @staticmethod
    def validate_component_type(component_type: str) -> ValidationResult:
        """Validate component type"""
        result = ValidationResult()

        valid_types = [option[0] for option in get_component_type_options()]

        if not component_type:
            result.add_error("Component type is required")
        elif component_type not in valid_types:
            result.add_error(f"Invalid component type. Must be one of: {', '.join(valid_types)}")

        return result

    @staticmethod
    def validate_framework(framework: str) -> ValidationResult:
        """Validate framework"""
        result = ValidationResult()

        valid_frameworks = [option[0] for option in get_framework_options()]

        if not framework:
            result.add_error("Framework is required")
        elif framework not in valid_frameworks:
            result.add_error(f"Invalid framework. Must be one of: {', '.join(valid_frameworks)}")

        return result

    @staticmethod
    def validate_guid(guid: str) -> ValidationResult:
        """Validate component GUID"""
        result = ValidationResult()

        if guid:
            is_valid, error_msg = validate_guid_format(guid)
            if not is_valid:
                result.add_error(error_msg)

        return result

class MSIConfigValidator:
    """Validates MSI configuration data"""

    @staticmethod
    def validate_msi_config(config_data: Dict[str, Any]) -> ValidationResult:
        """
        Validate MSI configuration
        Replaces JavaScript MSI validation
        """
        result = ValidationResult()

        # Required fields
        required_fields = {
            'app_name': 'Application name',
            'app_version': 'Application version',
            'manufacturer': 'Manufacturer'
        }

        for field, display_name in required_fields.items():
            if not config_data.get(field, '').strip():
                result.add_error(f"{display_name} is required")

        # App name validation
        app_name_validation = MSIConfigValidator.validate_app_name(config_data.get('app_name', ''))
        result.merge(app_name_validation)

        # Version validation
        version_validation = MSIConfigValidator.validate_version(config_data.get('app_version', ''))
        result.merge(version_validation)

        # Manufacturer validation
        manufacturer_validation = MSIConfigValidator.validate_manufacturer(config_data.get('manufacturer', ''))
        result.merge(manufacturer_validation)

        # Upgrade code validation
        if config_data.get('upgrade_code'):
            upgrade_validation = MSIConfigValidator.validate_upgrade_code(config_data['upgrade_code'])
            result.merge(upgrade_validation)

        # Install folder validation
        install_validation = MSIConfigValidator.validate_install_folder(config_data.get('install_folder', ''))
        result.merge(install_validation)

        return result

    @staticmethod
    def validate_app_name(app_name: str) -> ValidationResult:
        """Validate application name for MSI"""
        result = ValidationResult()

        if not app_name or not app_name.strip():
            result.add_error("Application name is required")
            return result

        name = app_name.strip()

        # Length validation
        if len(name) < 1:
            result.add_error("Application name cannot be empty")
        elif len(name) > 100:
            result.add_error("Application name must be less than 100 characters")

        # Character validation (MSI-safe characters)
        if not re.match(r'^[a-zA-Z0-9\s\-_\.]+$', name):
            result.add_error("Application name contains invalid characters for MSI")

        return result

    @staticmethod
    def validate_version(version: str) -> ValidationResult:
        """
        Validate version number format for MSI
        Replaces JavaScript version validation
        """
        result = ValidationResult()

        if not version or not version.strip():
            result.add_error("Version is required")
            return result

        # MSI version format: X.Y.Z.W where each part is 0-65535
        version_pattern = r'^\d+\.\d+\.\d+\.\d+$'

        if not re.match(version_pattern, version.strip()):
            result.add_error("Version must be in format X.Y.Z.W (e.g., 1.0.0.0)")
            return result

        # Check each part is within MSI limits
        parts = version.strip().split('.')
        for i, part in enumerate(parts):
            try:
                num = int(part)
                if num < 0 or num > 65535:
                    result.add_error(f"Version part {i+1} must be between 0 and 65535")
            except ValueError:
                result.add_error(f"Version part {i+1} must be a number")

        return result

    @staticmethod
    def validate_manufacturer(manufacturer: str) -> ValidationResult:
        """Validate manufacturer name"""
        result = ValidationResult()

        if not manufacturer or not manufacturer.strip():
            result.add_error("Manufacturer is required")
            return result

        name = manufacturer.strip()

        # Length validation
        if len(name) < 1:
            result.add_error("Manufacturer cannot be empty")
        elif len(name) > 100:
            result.add_error("Manufacturer must be less than 100 characters")

        # Character validation
        if not re.match(r'^[a-zA-Z0-9\s\-_\.]+$', name):
            result.add_error("Manufacturer contains invalid characters")

        return result

    @staticmethod
    def validate_upgrade_code(upgrade_code: str) -> ValidationResult:
        """Validate upgrade code (GUID)"""
        result = ValidationResult()

        if upgrade_code:
            is_valid, error_msg = validate_guid_format(upgrade_code)
            if not is_valid:
                result.add_error(f"Upgrade code: {error_msg}")

        return result

    @staticmethod
    def validate_install_folder(install_folder: str) -> ValidationResult:
        """Validate installation folder path"""
        result = ValidationResult()

        if not install_folder or not install_folder.strip():
            result.add_warning("Install folder not specified, will use default")
            return result

        path = install_folder.strip()

        # Windows path validation
        if not re.match(r'^[a-zA-Z]:\\', path):
            result.add_error("Install folder must be a valid Windows path (e.g., C:\\Program Files\\App)")

        # Path length validation
        if len(path) > 260:
            result.add_error("Install folder path is too long (maximum 260 characters)")

        # Invalid characters for Windows paths
        invalid_chars = ['<', '>', ':', '"', '|', '?', '*']
        for char in invalid_chars:
            if char in path:
                result.add_error(f"Install folder contains invalid character: {char}")

        return result

class UserValidator:
    """Validates user-related data"""

    @staticmethod
    def validate_user_projects_assignment(username: str, project_keys: List[str]) -> ValidationResult:
        """Validate user project assignment"""
        result = ValidationResult()

        if not username or not username.strip():
            result.add_error("Username is required")

        if not project_keys:
            result.add_warning("No projects assigned to user")

        # Validate username format
        if username and not re.match(r'^[a-zA-Z0-9\-_\.]+$', username):
            result.add_error("Username contains invalid characters")

        return result

class IntegrationValidator:
    """Validates integration configuration data"""

    @staticmethod
    def validate_servicenow_config(config_data: Dict[str, Any]) -> ValidationResult:
        """Validate ServiceNow configuration"""
        result = ValidationResult()

        # Required fields
        required_fields = {
            'instance': 'Instance URL',
            'username': 'Username',
            'password': 'Password'
        }

        for field, display_name in required_fields.items():
            if not config_data.get(field, '').strip():
                result.add_error(f"{display_name} is required")

        # URL validation
        instance_url = config_data.get('instance', '')
        if instance_url:
            url_validation = IntegrationValidator.validate_url(instance_url)
            result.merge(url_validation)

            # ServiceNow specific URL validation
            if not instance_url.endswith('.service-now.com'):
                result.add_warning("Instance URL should typically end with '.service-now.com'")

        return result

    @staticmethod
    def validate_vault_config(config_data: Dict[str, Any]) -> ValidationResult:
        """Validate Vault configuration"""
        result = ValidationResult()

        # Required fields
        required_fields = {
            'url': 'Vault URL',
            'token': 'Vault token'
        }

        for field, display_name in required_fields.items():
            if not config_data.get(field, '').strip():
                result.add_error(f"{display_name} is required")

        # URL validation
        vault_url = config_data.get('url', '')
        if vault_url:
            url_validation = IntegrationValidator.validate_url(vault_url)
            result.merge(url_validation)

        # Timeout validation
        timeout = config_data.get('timeout', 30)
        try:
            timeout_val = int(timeout)
            if timeout_val < 1 or timeout_val > 300:
                result.add_error("Timeout must be between 1 and 300 seconds")
        except (ValueError, TypeError):
            result.add_error("Timeout must be a valid number")

        return result

    @staticmethod
    def validate_url(url: str) -> ValidationResult:
        """Validate URL format"""
        result = ValidationResult()

        if not url:
            result.add_error("URL is required")
            return result

        try:
            parsed = urllib.parse.urlparse(url)
            if not parsed.scheme in ['http', 'https']:
                result.add_error("URL must start with http:// or https://")
            if not parsed.netloc:
                result.add_error("URL must include a domain name")
        except Exception:
            result.add_error("Invalid URL format")

        return result

def validate_form_data(form_type: str, form_data: Dict[str, Any], **kwargs) -> ValidationResult:
    """
    Main validation entry point
    Replaces all JavaScript validation functions
    """
    log_info(f"Validating form data for type: {form_type}")

    if form_type == 'project':
        return ProjectValidator.validate_project_data(form_data)

    elif form_type == 'component':
        existing_components = kwargs.get('existing_components', [])
        return ComponentValidator.validate_component_data(form_data, existing_components)

    elif form_type == 'msi_config':
        return MSIConfigValidator.validate_msi_config(form_data)

    elif form_type == 'user_projects':
        return UserValidator.validate_user_projects_assignment(
            form_data.get('username', ''),
            form_data.get('project_keys', [])
        )

    elif form_type == 'servicenow':
        return IntegrationValidator.validate_servicenow_config(form_data)

    elif form_type == 'vault':
        return IntegrationValidator.validate_vault_config(form_data)

    else:
        result = ValidationResult()
        result.add_error(f"Unknown form type: {form_type}")
        return result