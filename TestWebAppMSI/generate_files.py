#!/usr/bin/env python3
"""
Dynamic Files.wxs Generator for WiX v6
Recursively scans directories and generates Files.wxs with all files and empty folders
Similar to heat.exe functionality but with more control
"""

import os
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path
import hashlib

class WixFilesGenerator:
    def __init__(self, source_directory, output_file="Files.wxs", wix_namespace="http://wixtoolset.org/schemas/v4/wxs"):
        self.source_directory = Path(source_directory)
        self.output_file = output_file
        self.wix_namespace = wix_namespace
        self.components = []
        self.directories = {}
        self.file_counter = 0
        self.dir_counter = 0
    
    def generate_guid(self, seed_text):
        """Generate deterministic GUID based on file path"""
        hash_obj = hashlib.md5(seed_text.encode())
        hash_hex = hash_obj.hexdigest()
        
        # Format as GUID: XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX
        guid = f"{hash_hex[:8]}-{hash_hex[8:12]}-{hash_hex[12:16]}-{hash_hex[16:20]}-{hash_hex[20:32]}"
        return guid.upper()
    
    def get_relative_path(self, full_path):
        """Get path relative to source directory"""
        return str(Path(full_path).relative_to(self.source_directory))
    
    def sanitize_id(self, name):
        """Convert file/folder name to valid WiX ID"""
        # Remove invalid characters and spaces
        sanitized = ''.join(c if c.isalnum() else '_' for c in name)
        # Ensure it starts with letter or underscore
        if sanitized and sanitized[0].isdigit():
            sanitized = '_' + sanitized
        return sanitized or 'EmptyName'
    
    def scan_directory(self, directory):
        """Recursively scan directory and collect files and folders - FULLY DYNAMIC"""
        directory = Path(directory)
        
        if not directory.exists():
            print(f"Warning: Directory {directory} does not exist")
            return
        
        print(f"Scanning: {directory}")
        
        # Track ALL directories in the hierarchy
        rel_dir = self.get_relative_path(directory) if directory != self.source_directory else ""
        if rel_dir:
            self.directories[rel_dir] = {
                'path': rel_dir,
                'name': directory.name,
                'files': [],
                'subdirs': [],
                'empty': True,
                'parent': str(Path(rel_dir).parent) if Path(rel_dir).parent != Path('.') else None
            }
        
        try:
            items = list(directory.iterdir())
            
            # Process files first
            files_in_dir = []
            dirs_in_dir = []
            
            for item in items:
                if item.is_file():
                    files_in_dir.append(item)
                    if rel_dir:
                        self.directories[rel_dir]['empty'] = False
                        self.directories[rel_dir]['files'].append(item.name)
                elif item.is_dir():
                    dirs_in_dir.append(item)
                    if rel_dir:
                        self.directories[rel_dir]['empty'] = False
                        self.directories[rel_dir]['subdirs'].append(item.name)
            
            # Add files as components
            for file_path in files_in_dir:
                self.add_file_component(file_path)
            
            # Process subdirectories recursively
            for subdir in dirs_in_dir:
                self.scan_directory(subdir)
                    
            # Handle empty directories (preserve them)
            if rel_dir and self.directories[rel_dir]['empty']:
                self.add_empty_directory_component(directory)
                
        except PermissionError:
            print(f"Permission denied: {directory}")
    
    def add_file_component(self, file_path):
        """Add a file component"""
        rel_path = self.get_relative_path(file_path)
        file_name = file_path.name
        
        # Generate unique IDs
        component_id = f"File_{self.sanitize_id(file_name)}_{self.file_counter}"
        file_id = f"File_{self.sanitize_id(file_name)}_F_{self.file_counter}"
        
        # Generate GUID based on relative path
        guid = self.generate_guid(f"file_{rel_path}")
        
        component = {
            'type': 'file',
            'id': component_id,
            'guid': guid,
            'file_id': file_id,
            'source': rel_path.replace('\\', '/'),  # Use forward slashes for source
            'name': file_name,
            'directory': self.get_directory_id(file_path.parent)
        }
        
        self.components.append(component)
        self.file_counter += 1
        
        print(f"  File: {rel_path}")
    
    def add_empty_directory_component(self, dir_path):
        """Add component for empty directory to preserve it"""
        rel_path = self.get_relative_path(dir_path)
        dir_name = dir_path.name
        
        # Generate unique IDs
        component_id = f"EmptyDir_{self.sanitize_id(dir_name)}_{self.dir_counter}"
        
        # Generate GUID based on relative path
        guid = self.generate_guid(f"emptydir_{rel_path}")
        
        component = {
            'type': 'empty_directory',
            'id': component_id,
            'guid': guid,
            'name': dir_name,
            'directory': self.get_directory_id(dir_path)
        }
        
        self.components.append(component)
        self.dir_counter += 1
        
        print(f"  Empty Dir: {rel_path}")
    
    def get_directory_id(self, dir_path):
        """Get or create directory ID for WiX"""
        if dir_path == self.source_directory:
            return "INSTALLFOLDER"
        
        rel_path = self.get_relative_path(dir_path)
        # Create hierarchical directory ID
        parts = rel_path.replace('\\', '/').split('/')
        return f"Dir_{'_'.join([self.sanitize_id(part) for part in parts])}"
    
    def generate_directory_structure(self):
        """Generate directory structure XML - REMOVED to fix directory nesting"""
        # WiX v6 requires directories to be properly nested in Product.wxs
        # Instead of creating separate Directory elements, we'll add them 
        # to Product.wxs where they belong in the directory hierarchy
        return {}
    
    def generate_files_wxs(self):
        """Generate the Files.wxs content"""
        print(f"\nGenerating Files.wxs...")
        print(f"Found {self.file_counter} files and {self.dir_counter} empty directories")
        
        # Create root element
        root = ET.Element("Wix")
        root.set("xmlns", self.wix_namespace)
        
        # Add comment
        comment = ET.Comment(f" Files.wxs - Auto-generated from {self.source_directory} ")
        root.append(comment)
        
        # Create Fragment
        fragment = ET.SubElement(root, "Fragment")
        
        # Build complete directory tree dynamically from ALL discovered directories
        if self.directories:
            # Create INSTALLFOLDER as root directory element
            install_dir = ET.SubElement(fragment, "DirectoryRef")
            install_dir.set("Id", "INSTALLFOLDER")
            
            # Create mapping of directory elements
            created_dirs = {"INSTALLFOLDER": install_dir}
            
            # Get all directory paths and sort by depth (parents first)
            all_paths = list(self.directories.keys())
            sorted_paths = sorted(all_paths, key=lambda x: x.count(os.sep))
            
            print(f"Creating directory structure for paths: {sorted_paths}")
            
            # Create directory tree incrementally
            for rel_path in sorted_paths:
                # Normalize path separators for consistent processing
                normalized_path = rel_path.replace('\\', '/')
                parts = normalized_path.split('/')
                
                # Build each level of the directory hierarchy
                cumulative_path = []
                parent_element = install_dir
                
                for part in parts:
                    cumulative_path.append(part)
                    current_rel_path = '/'.join(cumulative_path)
                    current_id = self.get_directory_id(self.source_directory / current_rel_path.replace('/', os.sep))
                    
                    # Only create if not already created
                    if current_id not in created_dirs:
                        print(f"  Creating Directory: Id='{current_id}' Name='{part}'")
                        directory = ET.SubElement(parent_element, "Directory")
                        directory.set("Id", current_id)
                        directory.set("Name", part)
                        created_dirs[current_id] = directory
                        parent_element = directory
                    else:
                        parent_element = created_dirs[current_id]
        
        # Create ComponentGroup
        comp_group = ET.SubElement(fragment, "ComponentGroup")
        comp_group.set("Id", "WebApplicationFiles")
        comp_group.set("Directory", "INSTALLFOLDER")
        
        # Add all components
        for component in self.components:
            comp_elem = ET.SubElement(comp_group, "Component")
            comp_elem.set("Id", component['id'])
            comp_elem.set("Guid", component['guid'])
            
            # Set Directory attribute if component is not in INSTALLFOLDER
            if component['directory'] != "INSTALLFOLDER":
                comp_elem.set("Directory", component['directory'])
            
            if component['type'] == 'file':
                file_elem = ET.SubElement(comp_elem, "File")
                file_elem.set("Id", component['file_id'])
                file_elem.set("Source", f"{self.source_directory.name}/{component['source']}")
                file_elem.set("Name", component['name'])
                
            elif component['type'] == 'empty_directory':
                # Use CreateFolder to preserve empty directories
                folder_elem = ET.SubElement(comp_elem, "CreateFolder")
                # Set the Directory attribute to the specific directory ID
                folder_elem.set("Directory", component['directory'])
        
        return root
    
    def write_files_wxs(self):
        """Write the Files.wxs file"""
        root = self.generate_files_wxs()
        
        # Create XML tree with pretty formatting
        self.indent_xml(root)
        tree = ET.ElementTree(root)
        
        # Write to file with XML declaration
        with open(self.output_file, 'wb') as f:
            f.write(b'<?xml version="1.0" encoding="UTF-8"?>\n')
            tree.write(f, encoding='utf-8', xml_declaration=False)
        
        print(f"SUCCESS: Generated {self.output_file}")
        print(f"   Components: {len(self.components)}")
        print(f"   Files: {self.file_counter}")
        print(f"   Empty Dirs: {self.dir_counter}")
    
    def indent_xml(self, elem, level=0):
        """Add pretty formatting to XML"""
        i = "\n" + level * "  "
        if len(elem):
            if not elem.text or not elem.text.strip():
                elem.text = i + "  "
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
            for elem in elem:
                self.indent_xml(elem, level + 1)
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
        else:
            if level and (not elem.tail or not elem.tail.strip()):
                elem.tail = i

def detect_wix_namespace(product_wxs_path="Product.wxs"):
    """Detect WiX namespace from Product.wxs file"""
    try:
        with open(product_wxs_path, 'r', encoding='utf-8') as f:
            content = f.read()
            # Look for xmlns="http://wixtoolset.org/schemas/vX/wxs"
            import re
            match = re.search(r'xmlns="(http://wixtoolset\.org/schemas/v\d+/wxs)"', content)
            if match:
                return match.group(1)
    except Exception as e:
        print(f"Warning: Could not detect namespace from {product_wxs_path}: {e}")
    
    # Default fallback
    return "http://wixtoolset.org/schemas/v4/wxs"

def main():
    """Main function"""
    import sys
    
    if len(sys.argv) > 1:
        source_dir = sys.argv[1]
    else:
        source_dir = "WebFiles"
    
    if len(sys.argv) > 2:
        output_file = sys.argv[2]
    else:
        output_file = "Files.wxs"
    
    # Auto-detect namespace from Product.wxs
    namespace = detect_wix_namespace()
    
    print("="*50)
    print("WiX Files.wxs Generator")
    print("="*50)
    print(f"Source Directory: {source_dir}")
    print(f"Output File: {output_file}")
    print(f"WiX Namespace: {namespace}")
    print()
    
    generator = WixFilesGenerator(source_dir, output_file, namespace)
    generator.scan_directory(source_dir)
    generator.write_files_wxs()
    
    print("\nSUCCESS: Files.wxs generation complete!")

if __name__ == '__main__':
    main()