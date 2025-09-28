#!/usr/bin/env python3
"""
Windows Service for JFrog Artifact Polling
Runs as a background service to continuously monitor JFrog repositories
"""

import win32serviceutil
import win32service
import win32event
import servicemanager
import socket
import sys
import os
import time
import threading
from artifact_poller import JFrogArtifactPoller

class ArtifactPollerService(win32serviceutil.ServiceFramework):
    _svc_name_ = "MSIFactoryArtifactPoller"
    _svc_display_name_ = "MSI Factory - Artifact Polling Service"
    _svc_description_ = "Monitors JFrog repositories for new artifacts and downloads them for MSI generation"
    
    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)
        socket.setdefaulttimeout(60)
        self.poller = None
        self.polling_thread = None
        
    def SvcStop(self):
        """Stop the service"""
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        win32event.SetEvent(self.hWaitStop)
        
        # Stop the poller
        if self.poller:
            self.poller.stop()
            
    def SvcDoRun(self):
        """Run the service"""
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, '')
        )
        
        # Start the main service
        self.main()
        
    def main(self):
        """Main service logic"""
        try:
            # Initialize the poller
            self.poller = JFrogArtifactPoller()
            
            # Start polling in a separate thread
            self.polling_thread = threading.Thread(target=self.poller.start_polling)
            self.polling_thread.daemon = True
            self.polling_thread.start()
            
            # Wait for stop signal
            win32event.WaitForSingleObject(self.hWaitStop, win32event.INFINITE)
            
        except Exception as e:
            servicemanager.LogErrorMsg(f"Service error: {str(e)}")

if __name__ == '__main__':
    if len(sys.argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(ArtifactPollerService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        win32serviceutil.HandleCommandLine(ArtifactPollerService)