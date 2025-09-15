#!/usr/bin/env python3
"""
MSI Factory Core Engine
Main engine for generating environment-specific MSI packages
"""

import json
import os
import sys
import shutil
import tempfile
import zipfile
import requests
import subprocess
from pathlib import Path
# No complex typing needed
from datetime import datetime
import uuid
import re

class MSIFactoryCore:
    def __init__(self, config_file, output_dir=None):
        """Initialize MSI Factory with component configuration"""
        self.config_file = Path(config_file)
        self.output_dir = Path(output_dir) if output_dir else Path("../output")
        self.temp_dir = Path(tempfile.mkdtemp(prefix="msi_factory_"))
        
        # Load and validate configuration
        self.config = self._load_configuration()
        self.templates_dir = Path("../templates")
        
        print(f"MSI Factory initialized for component: {self.config['componentName']}")
        print(f"Output directory: {self.output_dir.absolute()}")
        print(f"Temp directory: {self.temp_dir}")
    
    def _load_configuration(self):
        """Load and validate component configuration"""
        if not self.config_file.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_file}")
        
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
            
            # Basic validation
            required_fields = ['componentId', 'appShortKey', 'componentName', 
                             'componentType', 'framework', 'environments', 'artifactSources']
            for field in required_fields:
                if field not in config:
                    raise ValueError(f"Missing required field: {field}")
            
            return config
            
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON configuration: {e}")
    
    def download_artifacts(self):
        """Download latest artifacts from configured sources"""
        print(f"Downloading artifacts for {self.config['appShortKey']}...")
        
        artifact_config = self.config['artifactSources']
        primary_url = artifact_config['primary']
        file_pattern = artifact_config.get('filePattern', '*.zip')
        
        # Create artifacts directory
        artifacts_dir = self.temp_dir / "artifacts"
        artifacts_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # Download from primary source
            downloaded_file = self._download_from_source(primary_url, file_pattern, artifacts_dir)
            if downloaded_file:
                print(f"Downloaded: {downloaded_file}")
                return str(downloaded_file)
            
            # Try fallback sources
            for fallback_url in artifact_config.get('fallback', []):
                print(f"Trying fallback source: {fallback_url}")
                downloaded_file = self._download_from_source(fallback_url, file_pattern, artifacts_dir)
                if downloaded_file:
                    print(f"Downloaded from fallback: {downloaded_file}")
                    return str(downloaded_file)
            
            raise Exception("Failed to download artifacts from any source")
            
        except Exception as e:
            raise Exception(f"Artifact download failed: {e}")
    
    def _download_from_source(self, source_url, file_pattern, target_dir):
        """Download artifact from a specific source"""
        try:
            # For demo purposes, we'll simulate downloading the latest matching file
            # In real implementation, this would integrate with JFrog API to find latest artifact
            
            # Simulate finding the latest file
            version = self.config.get('version', '1.0.0')
            app_key = self.config['appShortKey']
            
            # Generate simulated filename based on pattern
            if '*' in file_pattern:
                filename = file_pattern.replace('*', f"{app_key}-v{version}")
            else:
                filename = file_pattern
            
            # Create a dummy zip file for demonstration
            zip_path = target_dir / filename
            
            # In real implementation, this would be:
            # response = requests.get(f"{source_url}/{filename}", auth=auth)
            # with open(zip_path, 'wb') as f:
            #     f.write(response.content)
            
            # For demo, create a sample zip with some files
            self._create_sample_artifact(zip_path)
            
            return str(zip_path)
            
        except Exception as e:
            print(f"❌ Failed to download from {source_url}: {e}")
            return None
    
    def _create_sample_artifact(self, zip_path: Path):
        """Create a sample artifact for demonstration"""
        component_type = self.config['componentType']
        framework = self.config['framework']
        
        with zipfile.ZipFile(zip_path, 'w') as zf:
            if component_type == 'webapp':
                if framework == 'netcore':
                    # .NET Core web app files
                    zf.writestr('MyApp.dll', 'Sample .NET Core application DLL')
                    zf.writestr('appsettings.json', '{"Logging": {"LogLevel": {"Default": "Information"}}}')
                    zf.writestr('web.config', '<?xml version="1.0" encoding="utf-8"?><configuration></configuration>')
                    zf.writestr('wwwroot/index.html', '<html><body>Sample Web App</body></html>')
                    zf.writestr('wwwroot/css/site.css', 'body { font-family: Arial; }')
                elif framework == 'netframework':
                    # .NET Framework web app files
                    zf.writestr('bin/MyApp.dll', 'Sample .NET Framework application DLL')
                    zf.writestr('web.config', '<?xml version="1.0"?><configuration><system.web></system.web></configuration>')
                    zf.writestr('Default.aspx', '<%@ Page Language="C#" %>Sample ASP.NET Page')
                    zf.writestr('App_Data/sample.txt', 'Sample data file')
            
            elif component_type == 'website':
                if framework == 'react':
                    # React build files
                    zf.writestr('index.html', '<html><head><title>React App</title></head><body><div id="root"></div></body></html>')
                    zf.writestr('static/js/main.12345.js', 'console.log("React app bundle");')
                    zf.writestr('static/css/main.12345.css', 'body { margin: 0; font-family: Arial; }')
                    zf.writestr('manifest.json', '{"short_name": "React App", "name": "Sample React Application"}')
                elif framework == 'angular':
                    # Angular build files
                    zf.writestr('index.html', '<html><head><title>Angular App</title></head><body><app-root></app-root></body></html>')
                    zf.writestr('main.12345.js', 'console.log("Angular app bundle");')
                    zf.writestr('styles.12345.css', 'body { margin: 0; font-family: Arial; }')
                    zf.writestr('assets/config.json', '{"apiUrl": "https://api.example.com"}')
            
            elif component_type == 'service':
                if framework == 'netcore':
                    # .NET Core service files
                    zf.writestr('MyService.exe', 'Sample .NET Core service executable')
                    zf.writestr('appsettings.json', '{"Logging": {"LogLevel": {"Default": "Information"}}}')
                    zf.writestr('MyService.dll', 'Sample service DLL')
                    zf.writestr('runtimes/win-x64/native/sample.dll', 'Native dependency')
                elif framework == 'netframework':
                    # .NET Framework service files
                    zf.writestr('MyService.exe', 'Sample .NET Framework service executable')
                    zf.writestr('MyService.exe.config', '<?xml version="1.0"?><configuration></configuration>')
                    zf.writestr('MyService.pdb', 'Debug symbols')
    
    def extract_artifacts(self, zip_file_path: str) -> str:
        """Extract downloaded artifacts"""
        print(f"📂 Extracting artifacts from {Path(zip_file_path).name}...")
        
        extract_dir = self.temp_dir / "extracted"
        extract_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
                zip_ref.extractall(extract_dir)
            
            # List extracted files
            extracted_files = list(extract_dir.rglob('*'))
            print(f"Extracted {len([f for f in extracted_files if f.is_file()])} files")
            
            return str(extract_dir)
            
        except Exception as e:
            raise Exception(f"Failed to extract artifacts: {e}")
    
    def generate_environment_msis(self, extracted_artifacts_dir: str) -> Dict[str, str]:
        """Generate MSI packages for all environments"""
        print(f"🔨 Generating MSI packages for all environments...")
        
        results = {}
        environments = self.config['environments']
        
        for env_name, env_config in environments.items():
            print(f"\n🎯 Processing environment: {env_name}")
            
            try:
                msi_path = self._generate_single_environment_msi(
                    env_name, env_config, extracted_artifacts_dir
                )
                results[env_name] = msi_path
                print(f"Generated MSI for {env_name}: {Path(msi_path).name}")
                
            except Exception as e:
                print(f"❌ Failed to generate MSI for {env_name}: {e}")
                results[env_name] = None
        
        return results
    
    def _generate_single_environment_msi(self, env_name: str, env_config: Dict, artifacts_dir: str) -> str:
        """Generate MSI for a single environment"""
        
        # Create environment-specific working directory
        env_work_dir = self.temp_dir / f"build_{env_name}"
        env_work_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy artifacts to working directory
        artifacts_work_dir = env_work_dir / "artifacts"
        shutil.copytree(artifacts_dir, artifacts_work_dir)
        
        # Apply configuration transformations
        self._apply_config_transformations(env_name, env_config, artifacts_work_dir)
        
        # Generate WiX files
        product_wxs = self._generate_product_wxs(env_name, env_config, env_work_dir)
        files_wxs = self._generate_files_wxs(env_name, env_config, artifacts_work_dir, env_work_dir)
        
        # Build MSI
        msi_filename = f"{self.config['appShortKey']}_{self.config['componentType']}_{env_name}_{self.config.get('version', '1.0.0')}.msi"
        msi_path = self._build_msi(env_work_dir, product_wxs, files_wxs, msi_filename)
        
        return msi_path
    
    def _apply_config_transformations(self, env_name: str, env_config: Dict, artifacts_dir: Path):
        """Apply environment-specific configuration transformations"""
        print(f"🔧 Applying configuration transformations for {env_name}...")
        
        config_overrides = env_config.get('configOverrides', {})
        if not config_overrides:
            print("  No configuration overrides specified")
            return
        
        component_type = self.config['componentType']
        framework = self.config['framework']
        
        # Apply transformations based on component type and framework
        if component_type in ['webapp', 'service'] and framework == 'netcore':
            self._transform_appsettings_json(artifacts_dir, config_overrides)
        elif component_type in ['webapp', 'service'] and framework == 'netframework':
            self._transform_web_config(artifacts_dir, config_overrides)
        elif component_type == 'website' and framework in ['react', 'angular']:
            self._transform_frontend_config(artifacts_dir, config_overrides)
        
        print(f"Applied {len(config_overrides)} configuration overrides")
    
    def _transform_appsettings_json(self, artifacts_dir: Path, config_overrides: Dict):
        """Transform appsettings.json for .NET Core applications"""
        appsettings_file = artifacts_dir / "appsettings.json"
        
        if appsettings_file.exists():
            with open(appsettings_file, 'r') as f:
                settings = json.load(f)
            
            # Apply nested configuration overrides
            for key, value in config_overrides.items():
                if '__' in key:
                    # Handle nested keys like "ConnectionStrings__DefaultConnection"
                    parts = key.split('__')
                    current = settings
                    for part in parts[:-1]:
                        if part not in current:
                            current[part] = {}
                        current = current[part]
                    current[parts[-1]] = value
                else:
                    settings[key] = value
            
            with open(appsettings_file, 'w') as f:
                json.dump(settings, f, indent=2)
    
    def _transform_web_config(self, artifacts_dir: Path, config_overrides: Dict):
        """Transform web.config for .NET Framework applications"""
        # For demo purposes, we'll do basic string replacement
        # In real implementation, use proper XML transformation
        
        config_files = list(artifacts_dir.rglob("*.config"))
        for config_file in config_files:
            if config_file.is_file():
                with open(config_file, 'r') as f:
                    content = f.read()
                
                # Apply basic transformations
                for key, value in config_overrides.items():
                    # Simple placeholder replacement
                    content = content.replace(f"{{{{ {key} }}}}", str(value))
                
                with open(config_file, 'w') as f:
                    f.write(content)
    
    def _transform_frontend_config(self, artifacts_dir: Path, config_overrides: Dict):
        """Transform configuration for frontend applications"""
        # Look for common config files
        config_files = [
            artifacts_dir / "config.json",
            artifacts_dir / "assets" / "config.json",
            artifacts_dir / "environment.js"
        ]
        
        for config_file in config_files:
            if config_file.exists():
                if config_file.suffix == '.json':
                    with open(config_file, 'r') as f:
                        config = json.load(f)
                    
                    config.update(config_overrides)
                    
                    with open(config_file, 'w') as f:
                        json.dump(config, f, indent=2)
    
    def _generate_product_wxs(self, env_name: str, env_config: Dict, work_dir: Path) -> str:
        """Generate environment-specific Product.wxs"""
        print(f"Generating Product.wxs for {env_name}...")
        
        component_type = self.config['componentType']
        template_name = f"{component_type}-template.wxs"
        template_path = self.templates_dir / template_name
        
        # If template doesn't exist, use our existing templates
        if not template_path.exists():
            template_path = self._get_existing_template_path(component_type)
        
        if not template_path.exists():
            raise Exception(f"Template not found for component type: {component_type}")
        
        # Load template
        with open(template_path, 'r') as f:
            template_content = f.read()
        
        # Apply template variables
        template_vars = self._get_template_variables(env_name, env_config)
        product_content = self._apply_template_variables(template_content, template_vars)
        
        # Save Product.wxs
        product_wxs_path = work_dir / "Product.wxs"
        with open(product_wxs_path, 'w') as f:
            f.write(product_content)
        
        return str(product_wxs_path)
    
    def _get_existing_template_path(self, component_type: str) -> Path:
        """Get path to existing template based on component type"""
        template_mapping = {
            'webapp': Path("../../TestWebAppMSI/Product.wxs"),
            'website': Path("../../StandaloneWebSiteMSI/Product.wxs"),
            'service': Path("../../WindowsServiceMSI/Product.wxs")
        }
        
        template_path = self.templates_dir / ".." / template_mapping.get(component_type, "")
        return template_path.resolve()
    
    def _get_template_variables(self, env_name: str, env_config: Dict) -> Dict[str, str]:
        """Get template variables for WiX file generation"""
        config = self.config
        
        return {
            'ComponentId': config['componentId'],
            'AppShortKey': config['appShortKey'],
            'ComponentName': config['componentName'],
            'ComponentType': config['componentType'],
            'Framework': config['framework'],
            'Version': config.get('version', '1.0.0'),
            'Environment': env_name,
            'InstallPath': env_config['installPath'],
            'ServiceAccount': env_config.get('serviceAccount', {}).get('type', 'LocalSystem'),
            'ServiceUser': env_config.get('serviceAccount', {}).get('username', ''),
            'ServiceDomain': env_config.get('serviceAccount', {}).get('domain', ''),
            'CompanyName': 'MSI Factory Generated',
            'Manufacturer': 'MSI Factory',
            'Description': config.get('description', f'{config["componentName"]} - {env_name} Environment')
        }
    
    def _apply_template_variables(self, template_content: str, variables: Dict[str, str]) -> str:
        """Apply template variables to WiX content"""
        content = template_content
        
        # Replace template variables
        for key, value in variables.items():
            content = content.replace(f"$({key})", str(value))
            content = content.replace(f"{{{{ {key} }}}}", str(value))
        
        return content
    
    def _generate_files_wxs(self, env_name: str, env_config: Dict, artifacts_dir: Path, work_dir: Path) -> str:
        """Generate Files.wxs with harvested artifacts"""
        print(f"📁 Generating Files.wxs for {env_name}...")
        
        # Use our existing generate_files.py logic but adapted for this context
        files_wxs_path = work_dir / "Files.wxs"
        
        # Generate Files.wxs content
        files_content = self._generate_files_wxs_content(artifacts_dir)
        
        with open(files_wxs_path, 'w') as f:
            f.write(files_content)
        
        return str(files_wxs_path)
    
    def _generate_files_wxs_content(self, artifacts_dir: Path) -> str:
        """Generate Files.wxs XML content"""
        # Basic Files.wxs structure
        content = '''<?xml version="1.0" encoding="UTF-8"?>
<Wix xmlns="http://wixtoolset.org/schemas/v4/wxs">
  <Fragment>
    
    <!-- File Components -->
'''
        
        # Add file components
        file_id_counter = 1
        component_refs = []
        
        for file_path in artifacts_dir.rglob('*'):
            if file_path.is_file():
                rel_path = file_path.relative_to(artifacts_dir)
                
                file_id = f"File_{file_id_counter}"
                component_id = f"Comp_{file_id_counter}"
                guid = str(uuid.uuid4()).upper()
                
                content += f'''    <DirectoryRef Id="INSTALLFOLDER">
      <Component Id="{component_id}" Guid="{guid}">
        <File Id="{file_id}"
              Source="{artifacts_dir}\\{rel_path}"
              Name="{file_path.name}"
              KeyPath="yes" />
      </Component>
    </DirectoryRef>

'''
                
                component_refs.append(component_id)
                file_id_counter += 1
        
        # Add feature
        content += '''    <!-- Feature for Application Files -->
    <Feature Id="ApplicationFiles" Title="Application Files" Level="1">
'''
        
        for comp_ref in component_refs:
            content += f'      <ComponentRef Id="{comp_ref}" />\n'
        
        content += '''    </Feature>
    
  </Fragment>
</Wix>'''
        
        return content
    
    def _build_msi(self, work_dir: Path, product_wxs: str, files_wxs: str, msi_filename: str) -> str:
        """Build MSI using WiX Toolset"""
        print(f"🔨 Building MSI: {msi_filename}...")
        
        # Prepare output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)
        msi_output_path = self.output_dir / msi_filename
        
        try:
            # Change to working directory
            original_dir = os.getcwd()
            os.chdir(work_dir)
            
            # Build command
            build_cmd = [
                'wix', 'build',
                Path(product_wxs).name,
                Path(files_wxs).name,
                '-ext', 'WixToolset.Util.wixext',
                '-o', str(msi_output_path)
            ]
            
            # Add extensions based on component type
            component_type = self.config['componentType']
            if component_type in ['webapp', 'website']:
                build_cmd.extend(['-ext', 'WixToolset.Iis.wixext'])
            elif component_type == 'service':
                build_cmd.extend(['-ext', 'WixToolset.Firewall.wixext'])
            
            # Execute build
            result = subprocess.run(build_cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                raise Exception(f"WiX build failed: {result.stderr}")
            
            print(f"MSI built successfully: {msi_filename}")
            return str(msi_output_path)
            
        except Exception as e:
            raise Exception(f"MSI build failed: {e}")
        finally:
            os.chdir(original_dir)
    
    def cleanup(self):
        """Clean up temporary directories"""
        try:
            shutil.rmtree(self.temp_dir)
            print(f"🧹 Cleaned up temporary directory: {self.temp_dir}")
        except Exception as e:
            print(f"⚠️  Failed to cleanup: {e}")
    
    def process_component(self) -> Dict[str, str]:
        """Main method to process component and generate MSIs for all environments"""
        print(f"🚀 Starting MSI generation for {self.config['componentName']}")
        print(f"📋 Component: {self.config['appShortKey']} ({self.config['componentType']})")
        print(f"🎯 Environments: {list(self.config['environments'].keys())}")
        
        try:
            # Step 1: Download artifacts
            zip_file_path = self.download_artifacts()
            
            # Step 2: Extract artifacts
            extracted_dir = self.extract_artifacts(zip_file_path)
            
            # Step 3: Generate environment-specific MSIs
            results = self.generate_environment_msis(extracted_dir)
            
            # Summary
            success_count = len([r for r in results.values() if r is not None])
            total_count = len(results)
            
            print(f"\n🎉 MSI Generation Complete!")
            print(f"Successfully generated: {success_count}/{total_count} MSI packages")
            print(f"📁 Output directory: {self.output_dir.absolute()}")
            
            return results
            
        except Exception as e:
            print(f"❌ MSI generation failed: {e}")
            raise
        finally:
            # Always cleanup
            self.cleanup()

def main():
    if len(sys.argv) < 2:
        print("Usage: python msi_factory_core.py <config-file> [output-directory]")
        print("Examples:")
        print("  python msi_factory_core.py ../samples/webapp-sample.json")
        print("  python msi_factory_core.py ../samples/service-sample.json ../output/")
        sys.exit(1)
    
    config_file = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else None
    
    try:
        # Initialize MSI Factory
        factory = MSIFactoryCore(config_file, output_dir)
        
        # Process component
        results = factory.process_component()
        
        # Display results
        print("\n📋 Results Summary:")
        print("-" * 50)
        for env, msi_path in results.items():
            status = "SUCCESS" if msi_path else "FAILED"
            path_display = Path(msi_path).name if msi_path else "FAILED"
            print(f"{status} {env:10} -> {path_display}")
        
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()