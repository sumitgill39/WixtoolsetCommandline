"""
Utilities Module
Common utility functions for MSI Factory - replaces JavaScript utilities
"""

import uuid
import re
import os
from datetime import datetime
from logger import get_logger, log_info, log_error

logger = get_logger()

def generate_guid():
    """Generate a cryptographically secure GUID"""
    return str(uuid.uuid4())

def generate_project_component_guid(project_key, component_counter):
    """
    Generate project-specific component GUID
    Format: PROJECTKEY-XXXX-YYYY-ZZZZ
    Replaces JavaScript generateProjectComponentGuid()
    """
    try:
        # Clean and format project key
        clean_project_key = (project_key or 'PROJ').upper()[:8].ljust(8, '0')

        # Generate random sections
        section1 = format(uuid.uuid4().int & 0xFFFF, '04X')
        section2 = format(uuid.uuid4().int & 0xFFFF, '04X')
        section3 = format(component_counter, '04X')

        guid = f"{clean_project_key}-{section1}-{section2}-{section3}"
        log_info(f"Generated component GUID: {guid} for project {project_key}")
        return guid

    except Exception as e:
        log_error(f"Error generating component GUID: {e}")
        return generate_guid()  # Fallback to standard GUID

def validate_project_key(project_key):
    """
    Validate project key format
    Replaces JavaScript pattern validation
    """
    if not project_key:
        return False, "Project key is required"

    # Check length (2-10 characters)
    if len(project_key) < 2 or len(project_key) > 10:
        return False, "Project key must be 2-10 characters"

    # Check format (uppercase letters and numbers only)
    if not re.match(r'^[A-Z0-9]+$', project_key):
        return False, "Project key must contain only uppercase letters and numbers"

    return True, "Valid project key"

def generate_default_values(component_type, component_name, project_key):
    """
    Generate default values for components
    Replaces JavaScript default value setting
    """
    defaults = {
        'app_name': component_name or 'New Application',
        'app_version': '1.0.0.0',
        'manufacturer': 'Your Company',
        'install_folder': f'C:\\Program Files\\{component_name or "Application"}',
        'upgrade_code': generate_guid(),
    }

    # Component-type specific defaults
    if component_type in ['webapp', 'website', 'api']:
        defaults.update({
            'iis_website_name': 'Default Web Site',
            'iis_app_pool_name': f'{component_name}AppPool' if component_name else 'DefaultAppPool',
            'app_pool_dotnet_version': 'v4.0',
            'app_pool_pipeline_mode': 'Integrated',
            'app_pool_identity': 'ApplicationPoolIdentity',
            'app_pool_enable_32bit': False,
            'install_folder': f'C:\\inetpub\\wwwroot\\{component_name or "WebApp"}'
        })

    elif component_type == 'service':
        defaults.update({
            'service_name': component_name or 'NewService',
            'service_display_name': f'{component_name} Service' if component_name else 'New Service',
            'service_description': f'Windows service for {component_name}' if component_name else 'Windows Service',
            'service_start_type': 'Automatic',
            'service_account': 'LocalSystem',
            'install_folder': f'C:\\Program Files\\{component_name or "Service"}'
        })

    elif component_type == 'desktop':
        defaults.update({
            'install_folder': f'C:\\Program Files\\{component_name or "Application"}',
        })

    log_info(f"Generated defaults for {component_type} component: {component_name}")
    return defaults

def format_version_number(version_string):
    """
    Format version number to ensure proper MSI format
    Replaces JavaScript version formatting
    """
    if not version_string:
        return "1.0.0.0"

    # Remove any non-digit, non-dot characters
    clean_version = re.sub(r'[^\d.]', '', version_string)

    # Split by dots and ensure we have 4 parts
    parts = clean_version.split('.')

    # Pad or truncate to 4 parts
    while len(parts) < 4:
        parts.append('0')

    if len(parts) > 4:
        parts = parts[:4]

    # Ensure each part is a valid number
    formatted_parts = []
    for part in parts:
        try:
            num = int(part) if part else 0
            # MSI version parts must be 0-65535
            if num > 65535:
                num = 65535
            formatted_parts.append(str(num))
        except ValueError:
            formatted_parts.append('0')

    result = '.'.join(formatted_parts)
    log_info(f"Formatted version {version_string} -> {result}")
    return result

def increment_version(current_version, increment_type='build'):
    """
    Increment version number
    Replaces JavaScript auto-increment functionality
    """
    try:
        parts = current_version.split('.')
        if len(parts) != 4:
            return format_version_number(current_version)

        major, minor, build, revision = [int(p) for p in parts]

        if increment_type == 'major':
            major += 1
            minor = build = revision = 0
        elif increment_type == 'minor':
            minor += 1
            build = revision = 0
        elif increment_type == 'build':
            build += 1
            revision = 0
        elif increment_type == 'revision':
            revision += 1

        new_version = f"{major}.{minor}.{build}.{revision}"
        log_info(f"Incremented version {current_version} -> {new_version} ({increment_type})")
        return new_version

    except Exception as e:
        log_error(f"Error incrementing version {current_version}: {e}")
        return current_version

def sanitize_filename(filename):
    """
    Sanitize filename for use in paths
    Replaces JavaScript filename cleaning
    """
    if not filename:
        return "file"

    # Remove or replace invalid characters
    sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)

    # Remove leading/trailing spaces and dots
    sanitized = sanitized.strip(' .')

    # Ensure it's not empty
    if not sanitized:
        sanitized = "file"

    return sanitized

def generate_install_path(component_type, component_name, custom_path=None):
    """
    Generate appropriate install path based on component type
    Replaces JavaScript path generation
    """
    if custom_path:
        return custom_path

    safe_name = sanitize_filename(component_name) if component_name else "Application"

    if component_type in ['webapp', 'website', 'api']:
        return f"C:\\inetpub\\wwwroot\\{safe_name}"
    elif component_type == 'service':
        return f"C:\\Program Files\\{safe_name}"
    elif component_type == 'desktop':
        return f"C:\\Program Files\\{safe_name}"
    else:
        return f"C:\\Program Files\\{safe_name}"

def validate_guid_format(guid_string):
    """
    Validate GUID format
    Replaces JavaScript GUID validation
    """
    if not guid_string:
        return False, "GUID is required"

    # Standard GUID pattern
    guid_pattern = r'^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$'

    if re.match(guid_pattern, guid_string):
        return True, "Valid GUID format"
    else:
        return False, "Invalid GUID format. Expected format: XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX"

def get_framework_options():
    """
    Get available framework options
    Replaces hardcoded JavaScript arrays
    """
    return [
        ('netframework', '.NET Framework'),
        ('netcore', '.NET Core/.NET 5+'),
        ('react', 'React'),
        ('angular', 'Angular'),
        ('vue', 'Vue.js'),
        ('python', 'Python'),
        ('nodejs', 'Node.js'),
        ('static', 'Static HTML')
    ]

def get_component_type_options():
    """
    Get available component type options
    Replaces hardcoded JavaScript arrays
    """
    return [
        ('webapp', 'Web App'),
        ('website', 'Website'),
        ('service', 'Windows Service'),
        ('api', 'API'),
        ('scheduler', 'Scheduler'),
        ('desktop', 'Desktop App'),
        ('library', 'Library/DLL')
    ]

def get_project_type_options():
    """
    Get available project type options
    """
    return [
        ('WebApp', 'Web Application'),
        ('Service', 'Windows Service'),
        ('Website', 'Standalone Website'),
        ('Desktop', 'Desktop Application'),
        ('API', 'API Service')
    ]

def get_environment_options():
    """
    Get available environment options
    """
    return [
        ('DEV', 'Development'),
        ('QA', 'QA/Testing'),
        ('UAT', 'User Acceptance Testing'),
        ('PROD', 'Production')
    ]

def generate_component_name_from_project(project_name, component_type, existing_components=None):
    """
    Generate a unique component name based on project and type
    Replaces JavaScript name generation
    """
    if not project_name:
        base_name = f"New{component_type.title()}"
    else:
        # Take first word of project name and combine with type
        first_word = project_name.split()[0] if project_name.split() else project_name
        base_name = f"{first_word}{component_type.title()}"

    # Ensure uniqueness if existing components provided
    if existing_components:
        existing_names = [comp.get('component_name', '').lower() for comp in existing_components]
        counter = 1
        unique_name = base_name

        while unique_name.lower() in existing_names:
            counter += 1
            unique_name = f"{base_name}{counter}"

        return unique_name

    return base_name

def format_user_display_name(first_name, last_name, username):
    """
    Format user display name consistently
    """
    if first_name and last_name:
        return f"{first_name} {last_name}"
    elif first_name:
        return first_name
    elif last_name:
        return last_name
    else:
        return username or "Unknown User"

def get_user_initials(first_name, last_name, username):
    """
    Get user initials for avatar display
    Replaces JavaScript initial generation
    """
    if first_name and last_name:
        return f"{first_name[0]}{last_name[0]}".upper()
    elif first_name:
        return first_name[0].upper()
    elif last_name:
        return last_name[0].upper()
    elif username and len(username) >= 2:
        return username[:2].upper()
    else:
        return "?"

def calculate_progress_percentage(completed, total):
    """
    Calculate progress percentage safely
    """
    if total == 0:
        return 0
    return min(100, max(0, round((completed / total) * 100)))

def format_file_size(size_bytes):
    """
    Format file size in human readable format
    """
    if size_bytes == 0:
        return "0 B"

    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1

    return f"{size_bytes:.1f} {size_names[i]}"

def validate_url(url):
    """
    Basic URL validation
    """
    if not url:
        return False, "URL is required"

    # Basic URL pattern
    url_pattern = r'^https?://[^\s/$.?#].[^\s]*$'

    if re.match(url_pattern, url, re.IGNORECASE):
        return True, "Valid URL"
    else:
        return False, "Invalid URL format"

def clean_html_input(input_string):
    """
    Clean HTML input to prevent XSS
    Basic cleaning - for production use bleach library
    """
    if not input_string:
        return ""

    # Remove basic HTML tags
    clean = re.sub(r'<[^>]+>', '', input_string)

    # Remove script content
    clean = re.sub(r'<script.*?</script>', '', clean, flags=re.DOTALL | re.IGNORECASE)

    return clean.strip()

def truncate_string(text, max_length=50, suffix="..."):
    """
    Truncate string to specified length
    """
    if not text or len(text) <= max_length:
        return text

    return text[:max_length - len(suffix)] + suffix