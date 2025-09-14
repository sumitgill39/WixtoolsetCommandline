#!/usr/bin/env python3
"""
Simple MSI Factory - Easy to understand version
Generates MSI packages for different environments
"""

import json
import os
import shutil
import zipfile
from pathlib import Path

class SimpleMSIFactory:
    def __init__(self, config_file):
        """Start the MSI Factory with a config file"""
        self.config_file = config_file
        self.output_folder = "output"
        self.temp_folder = "temp"
        
        # Load the component configuration
        self.config = self.load_config()
        
        print(f"MSI Factory started for: {self.config['componentName']}")
    
    def load_config(self):
        """Load configuration from JSON file"""
        print(f"Loading config from: {self.config_file}")
        
        with open(self.config_file, 'r') as file:
            config = json.load(file)
        
        print(f"Config loaded for: {config['appShortKey']}")
        return config
    
    def create_folders(self):
        """Create output and temp folders"""
        print("Creating work folders...")
        
        # Create output folder
        if not os.path.exists(self.output_folder):
            os.makedirs(self.output_folder)
        
        # Create temp folder
        if not os.path.exists(self.temp_folder):
            os.makedirs(self.temp_folder)
        
        print("Work folders created")
    
    def download_app_files(self):
        """Download application files (simulated for now)"""
        print("Downloading application files...")
        
        app_name = self.config['appShortKey']
        component_type = self.config['componentType']
        
        # Create a sample zip file with app files
        zip_file = f"{self.temp_folder}/{app_name}.zip"
        
        with zipfile.ZipFile(zip_file, 'w') as zip_ref:
            if component_type == 'webapp':
                zip_ref.writestr('MyApp.dll', 'Sample web application')
                zip_ref.writestr('web.config', '<configuration></configuration>')
                zip_ref.writestr('index.html', '<html>Web App</html>')
            
            elif component_type == 'service':
                zip_ref.writestr('MyService.exe', 'Sample Windows service')
                zip_ref.writestr('config.xml', '<config></config>')
            
            elif component_type == 'website':
                zip_ref.writestr('index.html', '<html>Website</html>')
                zip_ref.writestr('style.css', 'body { color: blue; }')
                zip_ref.writestr('app.js', 'console.log("Hello");')
        
        print(f"Downloaded: {zip_file}")
        return zip_file
    
    def extract_files(self, zip_file):
        """Extract downloaded files"""
        print(f"Extracting files from: {zip_file}")
        
        extract_folder = f"{self.temp_folder}/extracted"
        
        with zipfile.ZipFile(zip_file, 'r') as zip_ref:
            zip_ref.extractall(extract_folder)
        
        print(f"Files extracted to: {extract_folder}")
        return extract_folder
    
    def update_config_files(self, files_folder, environment):
        """Update config files for specific environment"""
        print(f"Updating config for environment: {environment}")
        
        env_config = self.config['environments'][environment]
        config_changes = env_config.get('configOverrides', {})
        
        if not config_changes:
            print("No config changes needed")
            return
        
        # Find and update config files
        for file_path in Path(files_folder).rglob('*'):
            if file_path.is_file():
                file_name = file_path.name.lower()
                
                # Update JSON config files
                if file_name.endswith('.json'):
                    self.update_json_file(file_path, config_changes)
                
                # Update XML config files
                elif file_name.endswith('.config') or file_name.endswith('.xml'):
                    self.update_xml_file(file_path, config_changes)
        
        print(f"Config updated for {environment}")
    
    def update_json_file(self, file_path, config_changes):
        """Update JSON configuration file"""
        try:
            with open(file_path, 'r') as file:
                config = json.load(file)
            
            # Update config with new values
            for key, value in config_changes.items():
                config[key] = value
            
            with open(file_path, 'w') as file:
                json.dump(config, file, indent=2)
            
            print(f"  Updated JSON: {file_path.name}")
        except:
            print(f"  Could not update: {file_path.name}")
    
    def update_xml_file(self, file_path, config_changes):
        """Update XML configuration file (simple text replacement)"""
        try:
            with open(file_path, 'r') as file:
                content = file.read()
            
            # Simple replacement for demo
            for key, value in config_changes.items():
                placeholder = f"{{{key}}}"
                content = content.replace(placeholder, str(value))
            
            with open(file_path, 'w') as file:
                file.write(content)
            
            print(f"  Updated XML: {file_path.name}")
        except:
            print(f"  Could not update: {file_path.name}")
    
    def create_wix_files(self, files_folder, environment):
        """Create WiX files for MSI building"""
        print(f"Creating WiX files for: {environment}")
        
        env_config = self.config['environments'][environment]
        
        # Create Product.wxs
        product_wxs = self.create_product_wxs(environment, env_config)
        
        # Create Files.wxs
        files_wxs = self.create_files_wxs(files_folder)
        
        print("WiX files created")
        return product_wxs, files_wxs
    
    def create_product_wxs(self, environment, env_config):
        """Create Product.wxs file"""
        app_name = self.config['componentName']
        app_key = self.config['appShortKey']
        version = self.config.get('version', '1.0.0')
        install_path = env_config['installPath']
        
        product_wxs = f"""<?xml version="1.0" encoding="UTF-8"?>
<Wix xmlns="http://wixtoolset.org/schemas/v4/wxs">
  
  <Package 
    Name="{app_name} - {environment}"
    Version="{version}"
    Manufacturer="MSI Factory"
    UpgradeCode="12345678-1234-5678-9012-123456789012">
    
    <Property Id="INSTALLFOLDER" Value="{install_path}" />
    
    <StandardDirectory Id="ProgramFiles64Folder">
      <Directory Id="INSTALLFOLDER" Name="{app_key}" />
    </StandardDirectory>
    
    <Feature Id="Complete" Title="{app_name}" Level="1">
      <FeatureRef Id="ApplicationFiles" />
    </Feature>
    
  </Package>
</Wix>"""
        
        # Save Product.wxs
        wxs_file = f"{self.temp_folder}/Product_{environment}.wxs"
        with open(wxs_file, 'w') as file:
            file.write(product_wxs)
        
        return wxs_file
    
    def create_files_wxs(self, files_folder):
        """Create Files.wxs with all application files"""
        files_wxs_content = '''<?xml version="1.0" encoding="UTF-8"?>
<Wix xmlns="http://wixtoolset.org/schemas/v4/wxs">
  <Fragment>
    
    <!-- Application Files -->
'''
        
        # Add each file as a component
        file_count = 0
        component_refs = []
        
        for file_path in Path(files_folder).rglob('*'):
            if file_path.is_file():
                file_count += 1
                component_id = f"FileComp{file_count}"
                file_id = f"File{file_count}"
                
                files_wxs_content += f'''
    <DirectoryRef Id="INSTALLFOLDER">
      <Component Id="{component_id}" Guid="*">
        <File Id="{file_id}" Source="{file_path}" Name="{file_path.name}" KeyPath="yes" />
      </Component>
    </DirectoryRef>'''
                
                component_refs.append(component_id)
        
        # Add feature
        files_wxs_content += '''
    
    <Feature Id="ApplicationFiles" Title="Application Files" Level="1">
'''
        
        for comp_id in component_refs:
            files_wxs_content += f'      <ComponentRef Id="{comp_id}" />\n'
        
        files_wxs_content += '''    </Feature>
    
  </Fragment>
</Wix>'''
        
        # Save Files.wxs
        files_wxs_file = f"{self.temp_folder}/Files.wxs"
        with open(files_wxs_file, 'w') as file:
            file.write(files_wxs_content)
        
        return files_wxs_file
    
    def build_msi(self, product_wxs, files_wxs, environment):
        """Build MSI package using WiX"""
        print(f"Building MSI for: {environment}")
        
        app_key = self.config['appShortKey']
        version = self.config.get('version', '1.0.0')
        msi_name = f"{app_key}_{environment}_{version}.msi"
        msi_path = f"{self.output_folder}/{msi_name}"
        
        # Build command
        build_command = f'wix build "{product_wxs}" "{files_wxs}" -o "{msi_path}"'
        
        print(f"Running: {build_command}")
        result = os.system(build_command)
        
        if result == 0:
            print(f"SUCCESS: {msi_name}")
            return msi_path
        else:
            print(f"FAILED: Could not build {msi_name}")
            return None
    
    def cleanup(self):
        """Clean up temporary files"""
        print("Cleaning up temporary files...")
        
        if os.path.exists(self.temp_folder):
            shutil.rmtree(self.temp_folder)
        
        print("Cleanup complete")
    
    def generate_all_msis(self):
        """Main function - Generate MSI for all environments"""
        print("=== Starting MSI Generation ===")
        
        try:
            # Step 1: Create work folders
            self.create_folders()
            
            # Step 2: Download application files
            zip_file = self.download_app_files()
            
            # Step 3: Extract files
            files_folder = self.extract_files(zip_file)
            
            # Step 4: Generate MSI for each environment
            results = {}
            environments = self.config['environments']
            
            for env_name in environments:
                print(f"\n--- Processing {env_name} ---")
                
                # Copy files to environment folder
                env_files_folder = f"{self.temp_folder}/{env_name}_files"
                shutil.copytree(files_folder, env_files_folder)
                
                # Update config for this environment
                self.update_config_files(env_files_folder, env_name)
                
                # Create WiX files
                product_wxs, files_wxs = self.create_wix_files(env_files_folder, env_name)
                
                # Build MSI
                msi_path = self.build_msi(product_wxs, files_wxs, env_name)
                results[env_name] = msi_path
            
            # Show results
            print("\n=== Generation Complete ===")
            for env, msi in results.items():
                status = "SUCCESS" if msi else "FAILED"
                print(f"{env}: {status}")
            
            return results
            
        except Exception as e:
            print(f"ERROR: {e}")
            return {}
        
        finally:
            # Always cleanup
            self.cleanup()

# Simple way to run the factory
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python simple_msi_factory.py <config-file>")
        print("Example: python simple_msi_factory.py ../samples/webapp-sample.json")
        exit(1)
    
    config_file = sys.argv[1]
    
    # Create and run the factory
    factory = SimpleMSIFactory(config_file)
    results = factory.generate_all_msis()
    
    print("\nDone!")