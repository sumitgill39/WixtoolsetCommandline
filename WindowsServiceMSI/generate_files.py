#!/usr/bin/env python3
"""
WiX v6 Files Generator for Windows Service MSI
Generates Files.wxs with all files except the main service executable
which is handled directly in Product.wxs with ServiceInstall
"""
import os
import sys
import uuid
from pathlib import Path

def generate_guid():
    """Generate a new GUID for WiX components"""
    return str(uuid.uuid4()).upper()

def get_wix_namespace_from_product():
    """Read the WiX namespace from Product.wxs"""
    try:
        with open('Product.wxs', 'r', encoding='utf-8') as f:
            content = f.read()
            # Extract namespace from Product.wxs
            if 'xmlns="http://wixtoolset.org/schemas/v4/wxs"' in content:
                return 'http://wixtoolset.org/schemas/v4/wxs'
            elif 'xmlns="http://schemas.microsoft.com/wix/2006/wi"' in content:
                return 'http://schemas.microsoft.com/wix/2006/wi'
    except:
        pass
    return 'http://wixtoolset.org/schemas/v4/wxs'  # Default to v4

def should_skip_file(file_path, service_exe_name):
    """Check if file should be skipped (service executable)"""
    filename = os.path.basename(file_path)
    return filename.lower() == service_exe_name.lower()

def scan_directory(source_dir, service_exe_name):
    """Scan directory and build file/directory structure, excluding service executable"""
    if not os.path.exists(source_dir):
        print(f"Warning: Source directory '{source_dir}' does not exist")
        return {}, {}
    
    directories = {}
    files = {}
    
    for root, dirs, file_list in os.walk(source_dir):
        rel_path = os.path.relpath(root, source_dir)
        
        # Handle root directory
        if rel_path == '.':
            dir_id = 'INSTALLFOLDER'
        else:
            # Create directory structure
            path_parts = rel_path.split(os.sep)
            current_path = ''
            for part in path_parts:
                parent_path = current_path
                current_path = os.path.join(current_path, part) if current_path else part
                
                if current_path not in directories:
                    parent_id = 'INSTALLFOLDER' if not parent_path else f"Dir_{parent_path.replace(os.sep, '_')}"
                    dir_id = f"Dir_{current_path.replace(os.sep, '_')}"
                    directories[current_path] = {
                        'id': dir_id,
                        'name': part,
                        'parent_id': parent_id,
                        'path': current_path
                    }
            
            dir_id = f"Dir_{rel_path.replace(os.sep, '_')}"
        
        # Process files in current directory (skip service executable)
        for filename in file_list:
            file_path = os.path.join(root, filename)
            
            # Skip the service executable
            if should_skip_file(file_path, service_exe_name):
                print(f"Skipping service executable: {filename}")
                continue
                
            rel_file_path = os.path.relpath(file_path, source_dir)
            
            file_info = {
                'id': f"File_{rel_file_path.replace(os.sep, '_').replace('.', '_')}",
                'name': filename,
                'source': rel_file_path.replace(os.sep, '/'),
                'directory_id': dir_id
            }
            files[rel_file_path] = file_info
    
    return directories, files

def generate_files_wxs(directories, files, namespace):
    """Generate the Files.wxs content"""
    wxs_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<Wix xmlns="{namespace}">
  <Fragment>
'''

    # Generate directory structure
    if directories:
        wxs_content += '    <!-- Directory Structure -->\n'
        
        # Group directories by parent for proper nesting
        root_dirs = [d for d in directories.values() if d['parent_id'] == 'INSTALLFOLDER']
        
        def write_directory_tree(parent_dirs, indent_level=2):
            content = ""
            for dir_info in sorted(parent_dirs, key=lambda x: x['name']):
                indent = "    " * indent_level
                content += f'{indent}<DirectoryRef Id="{dir_info["parent_id"]}">\n'
                content += f'{indent}  <Directory Id="{dir_info["id"]}" Name="{dir_info["name"]}" />\n'
                content += f'{indent}</DirectoryRef>\n'
            return content
        
        wxs_content += write_directory_tree(root_dirs)
        wxs_content += '\n'

    # Generate components for files
    if files:
        wxs_content += '    <!-- File Components -->\n'
        
        # Group files by directory
        files_by_dir = {}
        for file_info in files.values():
            dir_id = file_info['directory_id']
            if dir_id not in files_by_dir:
                files_by_dir[dir_id] = []
            files_by_dir[dir_id].append(file_info)
        
        # Generate components
        for dir_id, dir_files in files_by_dir.items():
            for file_info in dir_files:
                component_id = f"Comp_{file_info['id']}"
                guid = generate_guid()
                
                wxs_content += f'''    <DirectoryRef Id="{dir_id}">
      <Component Id="{component_id}" Guid="{guid}">
        <File Id="{file_info['id']}"
              Source="ServiceFiles/{file_info['source']}"
              Name="{file_info['name']}"
              KeyPath="yes" />
      </Component>
    </DirectoryRef>

'''

    # Generate feature fragment
    if files:
        wxs_content += '    <!-- Feature for Service Files (excluding executable) -->\n'
        wxs_content += '    <Feature Id="ServiceFiles" Title="Service Support Files" Level="1">\n'
        
        for file_info in files.values():
            component_id = f"Comp_{file_info['id']}"
            wxs_content += f'      <ComponentRef Id="{component_id}" />\n'
        
        wxs_content += '    </Feature>\n\n'

    wxs_content += '''  </Fragment>
</Wix>'''
    
    return wxs_content

def main():
    if len(sys.argv) < 3:
        print("Usage: python generate_files.py <source_directory> <service_executable_name>")
        print("Example: python generate_files.py ServiceFiles MyService.exe")
        sys.exit(1)
    
    source_dir = sys.argv[1]
    service_exe_name = sys.argv[2]
    
    print(f"Generating Files.wxs for Windows Service MSI")
    print(f"Source directory: {source_dir}")
    print(f"Service executable (will be skipped): {service_exe_name}")
    print(f"Note: Service executable is handled directly in Product.wxs with ServiceInstall")
    
    # Get WiX namespace from Product.wxs
    namespace = get_wix_namespace_from_product()
    print(f"Using WiX namespace: {namespace}")
    
    # Scan directory structure (excluding service executable)
    directories, files = scan_directory(source_dir, service_exe_name)
    
    print(f"Found {len(directories)} directories and {len(files)} files (excluding service executable)")
    
    # Generate Files.wxs
    wxs_content = generate_files_wxs(directories, files, namespace)
    
    # Write Files.wxs
    with open('Files.wxs', 'w', encoding='utf-8') as f:
        f.write(wxs_content)
    
    print("Files.wxs generated successfully!")
    print("\nTo include in your build:")
    print("1. Add Files.wxs to your wix build command:")
    print("   wix build Product.wxs Files.wxs -ext WixToolset.Util.wixext -ext WixToolset.Firewall.wixext -o WindowsService.msi")
    print("2. Reference the ServiceFiles feature in Product.wxs if needed:")
    print("   <FeatureRef Id=\"ServiceFiles\" />")

if __name__ == "__main__":
    main()