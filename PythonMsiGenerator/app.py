from flask import Flask, render_template, request, jsonify, send_file
import os
import subprocess
import tempfile
import uuid
import shutil
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max file size
app.config['UPLOAD_FOLDER'] = 'temp_uploads'

# Create temp directory if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

class ApplicationType:
    WEB_APPLICATION = "WebApplication"
    CUSTOM_WEBSITE = "CustomWebSite"
    WINDOWS_SERVICE = "WindowsService"
    POWERSHELL_SCRIPT = "PowerShellScript"
    DESKTOP_APPLICATION = "DesktopApplication"

class WixGenerator:
    def __init__(self):
        self.temp_dir = tempfile.gettempdir()
    
    def generate_msi(self, config, uploaded_files):
        """Generate MSI package based on configuration"""
        session_id = str(uuid.uuid4()).replace('-', '')
        session_dir = os.path.join(self.temp_dir, f"wix_session_{session_id}")
        os.makedirs(session_dir, exist_ok=True)
        
        try:
            # Generate WiX source file
            wxs_content = self.generate_wix_source(config)
            wxs_path = os.path.join(session_dir, "Product.wxs")
            
            with open(wxs_path, 'w', encoding='utf-8') as f:
                f.write(wxs_content)
            
            # Save uploaded files
            files_dir = os.path.join(session_dir, "files")
            os.makedirs(files_dir, exist_ok=True)
            
            for file in uploaded_files:
                if file.filename:
                    filename = secure_filename(file.filename)
                    file.save(os.path.join(files_dir, filename))
            
            # Build MSI using wix.exe
            msi_path = os.path.join(session_dir, f"{config['application_name']}.msi")
            self.build_msi(wxs_path, msi_path, files_dir)
            
            return msi_path
            
        except Exception as e:
            # Clean up on error
            if os.path.exists(session_dir):
                shutil.rmtree(session_dir, ignore_errors=True)
            raise e
    
    def generate_wix_source(self, config):
        """Generate WiX v6 source code based on configuration"""
        app_type = config.get('app_type')
        
        # Start building WiX source
        wxs = []
        wxs.append('<?xml version="1.0" encoding="UTF-8"?>')
        wxs.append('<Wix xmlns="http://wixtoolset.org/schemas/v4/wxs"')
        
        # Add namespaces based on app type
        if app_type in [ApplicationType.WEB_APPLICATION, ApplicationType.CUSTOM_WEBSITE]:
            wxs.append('     xmlns:iis="http://wixtoolset.org/schemas/v4/wxs/iis">')
        else:
            wxs.append('>')
        
        wxs.append('')
        wxs.append(f'  <?define AppName = "{config["application_name"]}" ?>')
        wxs.append(f'  <?define AppVersion = "{config.get("version", "1.0.0.0")}" ?>')
        wxs.append(f'  <?define CompanyName = "{config.get("manufacturer", "")}" ?>')
        wxs.append(f'  <?define AppUpgradeCode = "{config.get("upgrade_code", str(uuid.uuid4()))}" ?>')
        wxs.append('')
        
        # Package element
        wxs.append('  <Package')
        wxs.append('    Name="$(var.AppName)"')
        wxs.append('    Version="$(var.AppVersion)"')
        wxs.append('    Manufacturer="$(var.CompanyName)"')
        wxs.append('    UpgradeCode="$(var.AppUpgradeCode)"')
        wxs.append('    Compressed="true"')
        wxs.append('    Scope="perMachine">')
        wxs.append('')
        
        # Installation location
        if config.get('install_location'):
            wxs.append(f'    <Property Id="INSTALLFOLDER" Value="{config["install_location"]}" />')
        wxs.append('')
        
        # Files
        wxs.append('    <!-- Include all uploaded files -->')
        wxs.append('    <Files Include="$(SourceDir)\\**\\*.*" />')
        wxs.append('')
        
        # Generate components based on app type
        if app_type == ApplicationType.WEB_APPLICATION:
            wxs.extend(self.generate_web_app_components(config))
        elif app_type == ApplicationType.CUSTOM_WEBSITE:
            wxs.extend(self.generate_custom_website_components(config))
        elif app_type == ApplicationType.WINDOWS_SERVICE:
            wxs.extend(self.generate_service_components(config))
        elif app_type == ApplicationType.POWERSHELL_SCRIPT:
            wxs.extend(self.generate_powershell_components(config))
        
        # Feature
        wxs.append('    <Feature Id="Complete" Title="$(var.AppName)" Level="1">')
        wxs.append('      <!-- Components are automatically included -->')
        wxs.append('    </Feature>')
        wxs.append('')
        
        # UI
        wxs.append('    <UI>')
        wxs.append('      <UIRef Id="WixUI_InstallDir" />')
        wxs.append('    </UI>')
        wxs.append('')
        
        wxs.append('  </Package>')
        wxs.append('</Wix>')
        
        return '\n'.join(wxs)
    
    def generate_web_app_components(self, config):
        """Generate web application components"""
        web_config = config.get('web_app', {})
        components = []
        
        components.append('    <!-- Application Pool -->')
        components.append('    <Component Id="CreateAppPool" Directory="INSTALLFOLDER">')
        components.append(f'      <iis:WebAppPool Id="MyAppPool"')
        components.append(f'                      Name="{web_config.get("app_pool_name", "$(var.AppName)AppPool")}"')
        components.append(f'                      ManagedRuntimeVersion="{web_config.get("runtime_version", "v4.0")}" />')
        components.append('    </Component>')
        components.append('')
        
        components.append('    <!-- Web Application -->')
        components.append('    <Component Id="CreateWebApp" Directory="INSTALLFOLDER">')
        components.append(f'      <iis:WebVirtualDir Id="MyVirtualDir"')
        components.append(f'                         Alias="{web_config.get("virtual_directory", "$(var.AppName)")}"')
        components.append(f'                         Directory="INSTALLFOLDER">')
        components.append(f'        <iis:WebApplication Id="MyWebApplication"')
        components.append(f'                            Name="$(var.AppName)"')
        components.append(f'                            WebAppPool="MyAppPool" />')
        components.append(f'      </iis:WebVirtualDir>')
        components.append('    </Component>')
        components.append('')
        
        return components
    
    def generate_custom_website_components(self, config):
        """Generate custom website components"""
        web_config = config.get('web_app', {})
        components = []
        
        components.append('    <!-- Application Pool -->')
        components.append('    <Component Id="CreateAppPool" Directory="INSTALLFOLDER">')
        components.append(f'      <iis:WebAppPool Id="MyAppPool"')
        components.append(f'                      Name="{web_config.get("app_pool_name", "$(var.AppName)AppPool")}"')
        components.append(f'                      ManagedRuntimeVersion="{web_config.get("runtime_version", "v4.0")}" />')
        components.append('    </Component>')
        components.append('')
        
        components.append('    <!-- Custom Website -->')
        components.append('    <Component Id="CreateWebSite" Directory="INSTALLFOLDER">')
        components.append(f'      <iis:WebSite Id="MyWebSite"')
        components.append(f'                   Description="{web_config.get("website_name", "$(var.AppName) Website")}"')
        components.append(f'                   Directory="INSTALLFOLDER"')
        components.append(f'                   AutoStart="yes">')
        components.append(f'        <iis:WebAddress Id="WebSiteAddress" Port="{web_config.get("port", "8080")}" IP="*" />')
        components.append(f'        <iis:WebApplication Id="MyWebApplication"')
        components.append(f'                            Name="$(var.AppName)"')
        components.append(f'                            WebAppPool="MyAppPool" />')
        components.append(f'      </iis:WebSite>')
        components.append('    </Component>')
        components.append('')
        
        return components
    
    def generate_service_components(self, config):
        """Generate Windows service components"""
        service_config = config.get('service', {})
        components = []
        
        components.append('    <!-- Windows Service -->')
        components.append('    <Component Id="ServiceComponent" Directory="INSTALLFOLDER">')
        components.append('      <ServiceInstall')
        components.append(f'        Id="{service_config.get("service_name", "$(var.AppName)Service")}"')
        components.append('        Type="ownProcess"')
        components.append('        Vital="yes"')
        components.append(f'        Name="{service_config.get("service_name", "$(var.AppName)Service")}"')
        components.append(f'        DisplayName="{service_config.get("display_name", "$(var.AppName) Service")}"')
        components.append(f'        Description="{service_config.get("description", "")}"')
        components.append(f'        Start="{service_config.get("start_type", "auto")}"')
        components.append(f'        Account="{service_config.get("account", "NT AUTHORITY\\LocalService")}"')
        components.append('        ErrorControl="ignore"')
        components.append('        Interactive="no" />')
        components.append('')
        components.append('      <ServiceControl')
        components.append('        Id="StartService"')
        components.append('        Stop="both"')
        components.append('        Remove="both"')
        components.append(f'        Name="{service_config.get("service_name", "$(var.AppName)Service")}"')
        components.append('        Wait="yes" />')
        components.append('    </Component>')
        components.append('')
        
        return components
    
    def generate_powershell_components(self, config):
        """Generate PowerShell script components"""
        ps_config = config.get('powershell', {})
        components = []
        
        components.append('    <!-- PowerShell Custom Action -->')
        components.append(f'    <CustomAction Id="RunPowerShell"')
        execution_policy = ps_config.get('execution_policy', 'Bypass')
        script_path = ps_config.get('script_path', 'script.ps1')
        components.append(f'                  ExeCommand="powershell.exe -ExecutionPolicy {execution_policy} -File &quot;[INSTALLFOLDER]{script_path}&quot;"')
        components.append(f'                  Directory="INSTALLFOLDER"')
        components.append(f'                  Execute="deferred"')
        components.append(f'                  Return="check" />')
        components.append('')
        components.append('    <InstallExecuteSequence>')
        
        timing = "After=\"InstallFiles\"" if ps_config.get('run_pre_install') else "Before=\"InstallFinalize\""
        components.append(f'      <Custom Action="RunPowerShell" {timing}>NOT REMOVE</Custom>')
        components.append('    </InstallExecuteSequence>')
        components.append('')
        
        return components
    
    def build_msi(self, wxs_path, msi_path, source_dir):
        """Build MSI using wix.exe command"""
        cmd = [
            'wix', 'build',
            wxs_path,
            '-o', msi_path,
            '-bindpath', source_dir
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            print(f"WiX build successful: {result.stdout}")
        except subprocess.CalledProcessError as e:
            error_msg = f"WiX build failed: {e.stderr}\nOutput: {e.stdout}"
            print(error_msg)
            raise Exception(error_msg)

# Initialize the WiX generator
wix_generator = WixGenerator()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/health')
def health_check():
    return jsonify({'status': 'healthy', 'wix_available': check_wix_available()})

def check_wix_available():
    try:
        result = subprocess.run(['wix', '--version'], capture_output=True, text=True)
        return True
    except FileNotFoundError:
        return False

@app.route('/api/generate', methods=['POST'])
def generate_msi():
    print("=== MSI Generation Request ===")
    print(f"Form data: {dict(request.form)}")
    print(f"Files: {[f.filename for f in request.files.getlist('files')]}")
    
    try:
        # Get form data
        config = {
            'application_name': request.form.get('application_name'),
            'version': request.form.get('version', '1.0.0.0'),
            'manufacturer': request.form.get('manufacturer'),
            'install_location': request.form.get('install_location'),
            'app_type': request.form.get('app_type')
        }
        
        print(f"Config: {config}")
        
        # Validate required fields
        if not config['application_name']:
            return jsonify({'error': 'Application name is required'}), 400
        if not config['manufacturer']:
            return jsonify({'error': 'Manufacturer is required'}), 400
        
        # Get type-specific configuration
        if config['app_type'] in [ApplicationType.WEB_APPLICATION, ApplicationType.CUSTOM_WEBSITE]:
            config['web_app'] = {
                'app_pool_name': request.form.get('web_app_pool_name'),
                'virtual_directory': request.form.get('web_virtual_directory'),
                'port': request.form.get('web_port', '80'),
                'runtime_version': request.form.get('web_runtime_version', 'v4.0'),
                'website_name': request.form.get('web_site_name')
            }
        elif config['app_type'] == ApplicationType.WINDOWS_SERVICE:
            config['service'] = {
                'service_name': request.form.get('service_name'),
                'display_name': request.form.get('service_display_name'),
                'description': request.form.get('service_description'),
                'start_type': request.form.get('service_start_type', 'auto'),
                'account': request.form.get('service_account', 'NT AUTHORITY\\LocalService')
            }
        elif config['app_type'] == ApplicationType.POWERSHELL_SCRIPT:
            config['powershell'] = {
                'script_path': request.form.get('ps_script_path'),
                'execution_policy': request.form.get('ps_execution_policy', 'Bypass'),
                'run_pre_install': request.form.get('ps_run_pre_install') == 'on'
            }
        
        # Get uploaded files
        files = request.files.getlist('files')
        
        # Generate MSI
        msi_path = wix_generator.generate_msi(config, files)
        
        # Send file as download
        return send_file(msi_path, as_attachment=True, 
                        download_name=f"{config['application_name']}.msi")
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/preview', methods=['POST'])
def preview_wix():
    try:
        config = request.get_json()
        wix_source = wix_generator.generate_wix_source(config)
        return jsonify({'wix_source': wix_source})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/app_types')
def get_app_types():
    types = [
        {'value': ApplicationType.WEB_APPLICATION, 'name': 'Web Application (IIS)'},
        {'value': ApplicationType.CUSTOM_WEBSITE, 'name': 'Custom Web Site'},
        {'value': ApplicationType.WINDOWS_SERVICE, 'name': 'Windows Service'},
        {'value': ApplicationType.POWERSHELL_SCRIPT, 'name': 'PowerShell Script'},
        {'value': ApplicationType.DESKTOP_APPLICATION, 'name': 'Desktop Application'}
    ]
    return jsonify(types)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)