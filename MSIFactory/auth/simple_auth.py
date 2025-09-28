#!/usr/bin/env python3
"""
Simple Authentication System for MSI Factory
Handles user login, access requests, and admin approvals
"""

import json
import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash

class SimpleAuth:
    def __init__(self):
        """Initialize authentication system"""
        self.users_file = "database/users.json"
        self.requests_file = "database/access_requests.json"
        self.apps_file = "database/applications.json"
        self.projects_file = "database/projects.json"
        
        # Create database files if they don't exist
        self.init_database()
    
    def init_database(self):
        """Create database files with sample data"""
        
        # Create database folder
        os.makedirs("database", exist_ok=True)
        
        # Sample users database
        if not os.path.exists(self.users_file):
            users_data = {
                "users": [
                    {
                        "username": "john.doe",
                        "email": "john.doe@company.com",
                        "domain": "COMPANY",
                        "first_name": "John",
                        "middle_name": "M",
                        "last_name": "Doe",
                        "status": "approved",
                        "role": "user",
                        "approved_apps": ["WEBAPP01", "PORTAL"],
                        "created_date": "2024-09-01",
                        "approved_by": "admin@company.com"
                    },
                    {
                        "username": "admin",
                        "email": "admin@company.com",
                        "domain": "COMPANY",
                        "first_name": "System",
                        "middle_name": "",
                        "last_name": "Admin",
                        "status": "approved",
                        "role": "admin",
                        "approved_apps": ["*"],
                        "created_date": "2024-08-01",
                        "approved_by": "system"
                    }
                ]
            }
            
            with open(self.users_file, 'w') as f:
                json.dump(users_data, f, indent=2)
        
        # Sample access requests database
        if not os.path.exists(self.requests_file):
            requests_data = {
                "requests": []
            }
            
            with open(self.requests_file, 'w') as f:
                json.dump(requests_data, f, indent=2)
        
        # Sample applications database
        if not os.path.exists(self.apps_file):
            apps_data = {
                "applications": [
                    {
                        "app_short_key": "WEBAPP01",
                        "app_name": "Customer Portal Web App",
                        "description": "Customer-facing web portal",
                        "owner_team": "Customer Experience",
                        "status": "active"
                    },
                    {
                        "app_short_key": "PORTAL",
                        "app_name": "Employee Portal Website",
                        "description": "Employee self-service portal",
                        "owner_team": "HR Technology",
                        "status": "active"
                    },
                    {
                        "app_short_key": "DATASYNC",
                        "app_name": "Data Synchronization Service",
                        "description": "Background data sync service",
                        "owner_team": "Integration Team",
                        "status": "active"
                    }
                ]
            }
            
            with open(self.apps_file, 'w') as f:
                json.dump(apps_data, f, indent=2)
        
        # Sample projects database
        if not os.path.exists(self.projects_file):
            projects_data = {
                "projects": [
                    {
                        "project_id": 1,
                        "project_name": "Customer Portal Web Application",
                        "project_key": "WEBAPP01",
                        "description": "Customer-facing web portal for service requests and account management",
                        "project_type": "WebApp",
                        "owner_team": "Customer Experience Team",
                        "status": "active",
                        "color_primary": "#2c3e50",
                        "color_secondary": "#3498db",
                        "created_date": "2024-08-15",
                        "created_by": "admin",
                        "environments": ["DEV", "QA", "UAT", "PROD"]
                    },
                    {
                        "project_id": 2,
                        "project_name": "Employee Portal Website",
                        "project_key": "PORTAL",
                        "description": "Internal employee self-service portal for HR and IT services",
                        "project_type": "Website",
                        "owner_team": "HR Technology",
                        "status": "active",
                        "color_primary": "#27ae60",
                        "color_secondary": "#2ecc71",
                        "created_date": "2024-08-20",
                        "created_by": "admin",
                        "environments": ["DEV", "QA", "PROD"]
                    },
                    {
                        "project_id": 3,
                        "project_name": "Data Synchronization Service",
                        "project_key": "DATASYNC",
                        "description": "Background service for synchronizing data between systems",
                        "project_type": "Service",
                        "owner_team": "Integration Team",
                        "status": "active",
                        "color_primary": "#e74c3c",
                        "color_secondary": "#c0392b",
                        "created_date": "2024-09-01",
                        "created_by": "admin",
                        "environments": ["DEV", "QA", "UAT", "PREPROD", "PROD"]
                    }
                ]
            }
            
            with open(self.projects_file, 'w') as f:
                json.dump(projects_data, f, indent=2)
    
    def load_users(self):
        """Load users from database"""
        with open(self.users_file, 'r') as f:
            data = json.load(f)
        return data['users']
    
    def save_users(self, users):
        """Save users to database"""
        data = {"users": users}
        with open(self.users_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def load_requests(self):
        """Load access requests from database"""
        with open(self.requests_file, 'r') as f:
            data = json.load(f)
        return data['requests']
    
    def save_requests(self, requests):
        """Save access requests to database"""
        data = {"requests": requests}
        with open(self.requests_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def load_applications(self):
        """Load applications from database"""
        with open(self.apps_file, 'r') as f:
            data = json.load(f)
        return data['applications']
    
    def check_user_login(self, username, domain="COMPANY"):
        """Check if user can login"""
        users = self.load_users()
        
        for user in users:
            if user['username'].lower() == username.lower() and user['domain'] == domain:
                return user
        
        return None
    
    def is_user_approved(self, username):
        """Check if user is approved"""
        user = self.check_user_login(username)
        if user:
            return user['status'] == 'approved'
        return False
    
    def verify_app_short_key(self, app_short_key):
        """Verify if AppShortKey exists in applications database"""
        applications = self.load_applications()
        
        for app in applications:
            if app['app_short_key'].upper() == app_short_key.upper():
                return app
        
        return None
    
    def create_access_request(self, username, email, first_name, middle_name, last_name, app_short_key, reason):
        """Create new access request"""
        
        # Verify AppShortKey exists
        app = self.verify_app_short_key(app_short_key)
        if not app:
            return False, "Invalid AppShortKey - Application not found"
        
        requests = self.load_requests()
        
        # Check if request already exists
        for req in requests:
            if req['username'].lower() == username.lower() and req['app_short_key'].upper() == app_short_key.upper():
                if req['status'] == 'pending':
                    return False, "Access request already pending for this application"
        
        # Create new request
        new_request = {
            "request_id": len(requests) + 1,
            "username": username,
            "email": email,
            "first_name": first_name,
            "middle_name": middle_name,
            "last_name": last_name,
            "app_short_key": app_short_key.upper(),
            "app_name": app['app_name'],
            "reason": reason,
            "status": "pending",
            "requested_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "approved_date": None,
            "approved_by": None
        }
        
        requests.append(new_request)
        self.save_requests(requests)
        
        return True, "Access request submitted successfully"
    
    def get_pending_requests(self):
        """Get all pending access requests for admin"""
        requests = self.load_requests()
        
        pending_requests = [req for req in requests if req['status'] == 'pending']
        return pending_requests
    
    def approve_request(self, request_id, admin_username):
        """Approve access request"""
        requests = self.load_requests()
        users = self.load_users()
        
        # Find the request
        request_found = None
        for req in requests:
            if req['request_id'] == int(request_id):
                request_found = req
                break
        
        if not request_found:
            return False, "Request not found"
        
        if request_found['status'] != 'pending':
            return False, "Request is not pending"
        
        # Approve the request
        request_found['status'] = 'approved'
        request_found['approved_date'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        request_found['approved_by'] = admin_username
        
        # Create or update user
        user_exists = False
        for user in users:
            if user['username'].lower() == request_found['username'].lower():
                # Add app to approved apps
                if request_found['app_short_key'] not in user['approved_apps']:
                    user['approved_apps'].append(request_found['app_short_key'])
                user_exists = True
                break
        
        if not user_exists:
            # Create new user
            new_user = {
                "username": request_found['username'],
                "email": request_found['email'],
                "domain": "COMPANY",
                "first_name": request_found['first_name'],
                "middle_name": request_found['middle_name'],
                "last_name": request_found['last_name'],
                "status": "approved",
                "role": "user",
                "approved_apps": [request_found['app_short_key']],
                "created_date": datetime.now().strftime("%Y-%m-%d"),
                "approved_by": admin_username
            }
            users.append(new_user)
        
        # Save changes
        self.save_requests(requests)
        self.save_users(users)
        
        return True, "Request approved successfully"
    
    def deny_request(self, request_id, admin_username, reason=""):
        """Deny access request"""
        requests = self.load_requests()
        
        # Find the request
        request_found = None
        for req in requests:
            if req['request_id'] == int(request_id):
                request_found = req
                break
        
        if not request_found:
            return False, "Request not found"
        
        if request_found['status'] != 'pending':
            return False, "Request is not pending"
        
        # Deny the request
        request_found['status'] = 'denied'
        request_found['approved_date'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        request_found['approved_by'] = admin_username
        request_found['denial_reason'] = reason
        
        self.save_requests(requests)
        
        return True, "Request denied"
    
    def get_user_apps(self, username):
        """Get applications user has access to"""
        user = self.check_user_login(username)
        if user and user['status'] == 'approved':
            return user['approved_apps']
        return []
    
    def load_projects(self):
        """Load projects from database"""
        with open(self.projects_file, 'r') as f:
            data = json.load(f)
        return data['projects']
    
    def save_projects(self, projects):
        """Save projects to database"""
        data = {"projects": projects}
        with open(self.projects_file, 'w') as f:
            json.dump(data, f, indent=2)
    
    def get_user_projects(self, username):
        """Get projects user has access to"""
        user = self.check_user_login(username)
        if not user or user['status'] != 'approved':
            return []
        
        projects = self.load_projects()
        user_apps = user['approved_apps']
        
        # Admin has access to all projects
        if '*' in user_apps or user['role'] == 'admin':
            return projects
        
        # Filter projects based on user's approved apps
        user_projects = []
        for project in projects:
            if project['project_key'] in user_apps:
                user_projects.append(project)
        
        return user_projects
    
    def get_all_projects(self):
        """Get all projects (admin only)"""
        return self.load_projects()
    
    def add_project(self, project_data):
        """Add new project"""
        projects = self.load_projects()
        
        # Check if project key already exists
        for project in projects:
            if project['project_key'].upper() == project_data['project_key'].upper():
                return False, "Project key already exists"
        
        # Generate new project ID
        max_id = max([p['project_id'] for p in projects]) if projects else 0
        project_data['project_id'] = max_id + 1
        project_data['created_date'] = datetime.now().strftime("%Y-%m-%d")
        
        projects.append(project_data)
        self.save_projects(projects)
        
        return True, "Project added successfully"
    
    def update_project(self, project_id, project_data):
        """Update existing project"""
        projects = self.load_projects()
        
        for i, project in enumerate(projects):
            if project['project_id'] == int(project_id):
                # Preserve original data
                project_data['project_id'] = project['project_id']
                project_data['created_date'] = project['created_date']
                project_data['created_by'] = project['created_by']
                projects[i] = project_data
                
                self.save_projects(projects)
                return True, "Project updated successfully"
        
        return False, "Project not found"
    
    def delete_project(self, project_id):
        """Delete project"""
        projects = self.load_projects()
        
        for i, project in enumerate(projects):
            if project['project_id'] == int(project_id):
                del projects[i]
                self.save_projects(projects)
                return True, "Project deleted successfully"
        
        return False, "Project not found"
    
    def get_project_by_id(self, project_id):
        """Get project by ID"""
        projects = self.load_projects()
        
        for project in projects:
            if project['project_id'] == int(project_id):
                return project
        
        return None
    
    def get_project_by_key(self, project_key):
        """Get project by key"""
        projects = self.load_projects()
        
        for project in projects:
            if project['project_key'].upper() == project_key.upper():
                return project
        
        return None
    
    def get_all_users(self):
        """Get all users (admin only)"""
        return self.load_users()
    
    def update_user_projects(self, username, project_keys, all_projects=False):
        """Update user's project access"""
        users = self.load_users()
        
        for user in users:
            if user['username'].lower() == username.lower():
                if all_projects:
                    user['approved_apps'] = ['*']
                else:
                    user['approved_apps'] = project_keys if project_keys else []
                
                self.save_users(users)
                return True, "User project access updated successfully"
        
        return False, "User not found"
    
    def get_user_project_details(self, username):
        """Get detailed project information for a user"""
        user = self.check_user_login(username)
        if not user or user['status'] != 'approved':
            return {'all_projects': False, 'projects': [], 'project_details': []}
        
        if '*' in user['approved_apps']:
            return {'all_projects': True, 'projects': ['*'], 'project_details': []}
        
        projects = self.load_projects()
        user_project_details = []
        
        for project_key in user['approved_apps']:
            for project in projects:
                if project['project_key'] == project_key:
                    user_project_details.append(project)
                    break
        
        return {
            'all_projects': False,
            'projects': user['approved_apps'],
            'project_details': user_project_details
        }
    
    def toggle_user_status(self, username):
        """Toggle user status between approved and inactive"""
        users = self.load_users()
        
        for user in users:
            if user['username'].lower() == username.lower() and user['role'] != 'admin':
                new_status = 'inactive' if user['status'] == 'approved' else 'approved'
                user['status'] = new_status
                
                self.save_users(users)
                return True, f"User status changed to {new_status}"
        
        return False, "User not found or cannot modify admin user"
    
    def get_user_statistics(self):
        """Get user statistics for dashboard"""
        users = self.load_users()
        requests = self.load_requests()
        
        stats = {
            'total_users': len(users),
            'active_users_count': len([u for u in users if u['status'] == 'approved']),
            'pending_requests_count': len([r for r in requests if r['status'] == 'pending']),
            'admin_users_count': len([u for u in users if u['role'] == 'admin'])
        }
        
        return stats

# Flask Web Application routes are disabled in refactored architecture
# These routes are now handled by core/routes.py
