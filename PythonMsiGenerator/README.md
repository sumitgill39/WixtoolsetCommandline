# Python MSI Generator

A web-based MSI package generator using Python Flask and WiX Toolset v6. This application provides an intuitive web interface to create Windows Installer packages without needing to write WiX XML manually.

## Features

🌟 **Multiple Application Types**
- Web Applications (IIS deployment)
- Custom Web Sites (new IIS site creation)
- Windows Services
- PowerShell Scripts
- Desktop Applications

🎯 **User-Friendly Interface**
- Step-by-step wizard
- Real-time form validation
- WiX source preview
- Progress tracking

🔧 **WiX v6 Integration**
- Automatic WiX source generation
- File upload and packaging
- Custom configuration options
- One-click MSI generation

## Prerequisites

1. **Python 3.7+**
2. **WiX Toolset v6**
   ```bash
   dotnet tool install --global wix
   ```
3. **Flask** (installed via requirements.txt)

## Installation

1. **Clone/Download** the application files
2. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
3. **Verify WiX installation**:
   ```bash
   wix --version
   ```

## Usage

### Quick Start
```bash
python run.py
```

Then open your browser to: `http://localhost:5000`

### Step-by-Step Guide

#### Step 1: Choose Application Type
Select from 5 different installer types:
- **Web Application**: Deploy to existing IIS Default Web Site
- **Custom Web Site**: Create new IIS website with custom port
- **Windows Service**: Install and configure background service
- **PowerShell Script**: Package and execute PowerShell scripts
- **Desktop Application**: Simple file deployment

#### Step 2: Configure Installation
- **Basic Info**: Name, version, manufacturer, install location
- **Type-specific settings**: IIS configuration, service settings, PowerShell options
- **File Upload**: Select files to include in the installer

#### Step 3: Generate MSI
- **Preview**: View the generated WiX source code
- **Generate**: Create and download the MSI package

## Configuration Examples

### Web Application
```
Application Name: MyWebApp
Manufacturer: My Company
App Pool Name: MyWebAppAppPool
Virtual Directory: MyWebApp
Port: 80
Runtime Version: v4.0
```

### Windows Service
```
Application Name: MyService
Service Name: MyBackgroundService
Display Name: My Background Service
Description: Handles background processing
Start Type: Automatic
Account: NT AUTHORITY\LocalService
```

### PowerShell Script
```
Application Name: MyScript
Script Path: install.ps1
Execution Policy: Bypass
Run After Installation: ✓
```

## File Structure

```
PythonMsiGenerator/
├── app.py                 # Main Flask application
├── run.py                 # Application launcher
├── requirements.txt       # Python dependencies
├── templates/
│   └── index.html        # Web interface
├── temp_uploads/         # Temporary file storage
└── README.md            # This file
```

## API Endpoints

### `GET /`
Serves the main web interface

### `POST /api/generate`
Generates and returns MSI package
- **Input**: Form data with configuration and files
- **Output**: MSI file download

### `POST /api/preview`
Returns WiX source preview
- **Input**: JSON configuration
- **Output**: Generated WiX XML source

### `GET /api/app_types`
Returns available application types
- **Output**: List of supported installer types

## Technical Details

### WiX Generation Process
1. **Configuration Parsing**: Extract form data and file uploads
2. **Source Generation**: Create WiX v6 XML based on app type
3. **File Management**: Save uploaded files to temporary directory
4. **MSI Compilation**: Execute `wix build` command
5. **File Delivery**: Return MSI as downloadable file

### Supported WiX Features
- Package-level configuration
- File harvesting with `<Files>` element
- IIS web application and website creation
- Windows service installation and control
- Custom actions for PowerShell execution
- Major upgrade handling
- Installation UI (WixUI_InstallDir)

### Security Considerations
- File upload size limits (500MB max)
- Secure filename handling
- Temporary file cleanup
- Input validation and sanitization

## Troubleshooting

### Common Issues

**1. "WiX Toolset not found" error**
```bash
# Install WiX v6 globally
dotnet tool install --global wix

# Verify installation
wix --version
```

**2. "Permission denied" during MSI generation**
- Run as administrator for IIS/service installers
- Check file permissions in temp directory

**3. "MSI build failed" error**
- Check WiX source preview for syntax errors
- Verify all uploaded files are accessible
- Review error messages in console

**4. Large file upload timeouts**
- Increase `MAX_CONTENT_LENGTH` in app.py
- Use smaller file sets or compress files

### Debug Mode
Run with debug enabled:
```bash
python app.py
```
Debug output will show:
- WiX command execution
- File paths and operations
- Detailed error messages

## Extending the Application

### Adding New Application Types
1. Add new type to `ApplicationType` class
2. Create configuration form section in HTML
3. Implement component generation method
4. Add type selection card in interface

### Custom WiX Features
1. Extend `generate_wix_source()` method
2. Add new configuration parameters
3. Update form interface accordingly

### Additional File Formats
Modify file upload handling in:
- `generate_msi()` method
- File validation logic
- Upload UI components

## License

This project is provided as-is for educational and development purposes.

## Contributing

Feel free to submit issues and enhancement requests!

## Support

For WiX-related questions, refer to:
- [WiX Toolset Documentation](https://wixtoolset.org/docs/)
- [WiX v6 Release Notes](https://wixtoolset.org/docs/releasenotes/)

For application issues, check the console output for detailed error messages.