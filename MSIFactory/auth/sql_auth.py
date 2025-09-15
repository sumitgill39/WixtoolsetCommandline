#!/usr/bin/env python3
"""
SQL Server Authentication System for MSI Factory
Handles user login, access requests, and admin approvals using SQL Server database
"""

import sys
import os
from datetime import datetime
from contextlib import contextmanager
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import and_, or_

# Add paths for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'database'))

from database.models import (
    User, Project, ProjectEnvironment, AccessRequest, MSIBuild, 
    SystemLog, UserSession, SystemSetting, Application,
    user_projects_association, Base, engine
)
from database.connection_manager import get_robust_session, execute_with_retry, test_database_connection

class SQLServerAuth:
    """SQL Server-based Authentication System"""
    
    def __init__(self):
        """Initialize authentication system"""
        self.ensure_database_initialized()
    
    def ensure_database_initialized(self):
        """Ensure database tables exist"""
        try:
            # Create tables if they don't exist
            Base.metadata.create_all(bind=engine)
        except Exception as e:
            print(f"[WARNING] Database initialization check failed: {e}")
    
    def get_session(self):
        """Get robust database session"""
        return get_robust_session()
    
    def check_user_login(self, username, domain="COMPANY"):
        """Check if user can login"""
        try:
            with self.get_session() as session:
                user = session.query(User).filter(
                    and_(
                        User.username.ilike(username),
                        User.domain == domain,
                        User.is_active == True
                    )
                ).first()
                
                if user:
                    return {
                        'user_id': user.user_id,
                        'username': user.username,
                        'email': user.email,
                        'domain': user.domain,
                        'first_name': user.first_name,
                        'middle_name': user.middle_name or '',
                        'last_name': user.last_name,
                        'status': user.status,
                        'role': user.role,
                        'approved_apps': self._get_user_project_keys(session, user.user_id),
                        'created_date': user.created_date.strftime('%Y-%m-%d') if user.created_date else None,
                        'approved_by': user.approved_by
                    }
                return None
                
        except Exception as e:
            print(f"[ERROR] User login check failed: {e}")
            return None
    
    def _get_user_project_keys(self, session, user_id):
        """Get project keys for a user"""
        try:
            # Check if user has admin role (access to all projects)
            user = session.query(User).filter_by(user_id=user_id).first()
            if user and user.role == 'admin':
                return ['*']
            
            # Get specific project keys
            result = session.query(Project.project_key).join(
                user_projects_association,
                Project.project_id == user_projects_association.c.project_id
            ).filter(
                and_(
                    user_projects_association.c.user_id == user_id,
                    user_projects_association.c.is_active == True
                )
            ).all()
            
            return [row[0] for row in result]
            
        except Exception as e:
            print(f"[ERROR] Failed to get user project keys: {e}")
            return []
    
    def is_user_approved(self, username):
        """Check if user is approved"""
        user_data = self.check_user_login(username)
        return user_data and user_data['status'] == 'approved' if user_data else False
    
    def verify_project_key(self, project_key):
        """Verify if project key exists"""
        try:
            with self.get_session() as session:
                project = session.query(Project).filter(
                    and_(
                        Project.project_key.ilike(project_key),
                        Project.is_active == True
                    )
                ).first()
                
                if project:
                    return {
                        'project_id': project.project_id,
                        'project_key': project.project_key,
                        'project_name': project.project_name,
                        'description': project.description,
                        'project_type': project.project_type,
                        'owner_team': project.owner_team,
                        'status': project.status
                    }
                return None
                
        except Exception as e:
            print(f"[ERROR] Project verification failed: {e}")
            return None
    
    def create_access_request(self, username, email, first_name, middle_name, last_name, project_key, reason):
        """Create new access request"""
        try:
            # Verify project key exists
            project_data = self.verify_project_key(project_key)
            if not project_data:
                return False, "Invalid project key - Project not found"
            
            with self.get_session() as session:
                # Check if request already exists
                existing_request = session.query(AccessRequest).filter(
                    and_(
                        AccessRequest.username.ilike(username),
                        AccessRequest.project_id == project_data['project_id'],
                        AccessRequest.status == 'pending'
                    )
                ).first()
                
                if existing_request:
                    return False, "Access request already pending for this project"
                
                # Create new request
                new_request = AccessRequest(
                    username=username,
                    email=email,
                    first_name=first_name,
                    middle_name=middle_name or '',
                    last_name=last_name,
                    project_id=project_data['project_id'],
                    reason=reason,
                    status='pending'
                )
                
                session.add(new_request)
                
                return True, "Access request submitted successfully"
                
        except Exception as e:
            print(f"[ERROR] Access request creation failed: {e}")
            return False, f"Failed to create access request: {str(e)}"
    
    def get_pending_requests(self):
        """Get all pending access requests for admin"""
        try:
            with self.get_session() as session:
                requests = session.query(AccessRequest).join(Project).filter(
                    AccessRequest.status == 'pending'
                ).all()
                
                pending_requests = []
                for req in requests:
                    pending_requests.append({
                        'request_id': req.request_id,
                        'username': req.username,
                        'email': req.email,
                        'first_name': req.first_name,
                        'middle_name': req.middle_name or '',
                        'last_name': req.last_name,
                        'project_id': req.project_id,
                        'project_key': req.project.project_key,
                        'project_name': req.project.project_name,
                        'reason': req.reason,
                        'status': req.status,
                        'requested_date': req.requested_date.strftime('%Y-%m-%d %H:%M:%S') if req.requested_date else None
                    })
                
                return pending_requests
                
        except Exception as e:
            print(f"[ERROR] Failed to get pending requests: {e}")
            return []
    
    def approve_request(self, request_id, admin_username):
        """Approve access request"""
        try:
            with self.get_session() as session:
                # Find the request
                request = session.query(AccessRequest).filter_by(request_id=request_id).first()
                
                if not request:
                    return False, "Request not found"
                
                if request.status != 'pending':
                    return False, "Request is not pending"
                
                # Update request status
                request.status = 'approved'
                request.processed_date = datetime.now()
                request.processed_by = admin_username
                
                # Create or update user
                user = session.query(User).filter_by(username=request.username).first()
                
                if not user:
                    # Create new user
                    user = User(
                        username=request.username,
                        email=request.email,
                        domain='COMPANY',
                        first_name=request.first_name,
                        middle_name=request.middle_name or '',
                        last_name=request.last_name,
                        status='approved',
                        role='user',
                        approved_date=datetime.now(),
                        approved_by=admin_username
                    )
                    session.add(user)
                    session.flush()  # Get user_id
                
                # Add user-project relationship
                existing_relationship = session.query(user_projects_association).filter(
                    and_(
                        user_projects_association.c.user_id == user.user_id,
                        user_projects_association.c.project_id == request.project_id
                    )
                ).first()
                
                if not existing_relationship:
                    session.execute(
                        user_projects_association.insert().values(
                            user_id=user.user_id,
                            project_id=request.project_id,
                            access_level='user',
                            granted_by=admin_username
                        )
                    )
                
                return True, "Request approved successfully"
                
        except Exception as e:
            print(f"[ERROR] Request approval failed: {e}")
            return False, f"Failed to approve request: {str(e)}"
    
    def deny_request(self, request_id, admin_username, reason=""):
        """Deny access request"""
        try:
            with self.get_session() as session:
                request = session.query(AccessRequest).filter_by(request_id=request_id).first()
                
                if not request:
                    return False, "Request not found"
                
                if request.status != 'pending':
                    return False, "Request is not pending"
                
                # Update request status
                request.status = 'denied'
                request.processed_date = datetime.now()
                request.processed_by = admin_username
                request.denial_reason = reason
                
                return True, "Request denied"
                
        except Exception as e:
            print(f"[ERROR] Request denial failed: {e}")
            return False, f"Failed to deny request: {str(e)}"
    
    def get_user_projects(self, username):
        """Get projects user has access to"""
        try:
            with self.get_session() as session:
                user = session.query(User).filter_by(username=username).first()
                
                if not user or user.status != 'approved':
                    return []
                
                # Admin has access to all projects
                if user.role == 'admin':
                    projects = session.query(Project).filter_by(is_active=True).all()
                else:
                    # Get specific projects
                    projects = session.query(Project).join(
                        user_projects_association,
                        Project.project_id == user_projects_association.c.project_id
                    ).filter(
                        and_(
                            user_projects_association.c.user_id == user.user_id,
                            user_projects_association.c.is_active == True,
                            Project.is_active == True
                        )
                    ).all()
                
                return [
                    {
                        'project_id': proj.project_id,
                        'project_name': proj.project_name,
                        'project_key': proj.project_key,
                        'description': proj.description,
                        'project_type': proj.project_type,
                        'owner_team': proj.owner_team,
                        'status': proj.status,
                        'color_primary': proj.color_primary,
                        'color_secondary': proj.color_secondary,
                        'created_date': proj.created_date.strftime('%Y-%m-%d') if proj.created_date else None,
                        'created_by': proj.created_by
                    }
                    for proj in projects
                ]
                
        except Exception as e:
            print(f"[ERROR] Failed to get user projects: {e}")
            return []
    
    def get_all_projects(self):
        """Get all projects (admin only)"""
        try:
            with self.get_session() as session:
                projects = session.query(Project).filter_by(is_active=True).all()
                
                return [
                    {
                        'project_id': proj.project_id,
                        'project_name': proj.project_name,
                        'project_key': proj.project_key,
                        'description': proj.description,
                        'project_type': proj.project_type,
                        'owner_team': proj.owner_team,
                        'status': proj.status,
                        'color_primary': proj.color_primary,
                        'color_secondary': proj.color_secondary,
                        'created_date': proj.created_date.strftime('%Y-%m-%d') if proj.created_date else None,
                        'created_by': proj.created_by
                    }
                    for proj in projects
                ]
                
        except Exception as e:
            print(f"[ERROR] Failed to get all projects: {e}")
            return []
    
    def get_all_users(self):
        """Get all users (admin only)"""
        try:
            with self.get_session() as session:
                users = session.query(User).filter_by(is_active=True).all()
                
                return [
                    {
                        'user_id': user.user_id,
                        'username': user.username,
                        'email': user.email,
                        'domain': user.domain,
                        'first_name': user.first_name,
                        'middle_name': user.middle_name or '',
                        'last_name': user.last_name,
                        'status': user.status,
                        'role': user.role,
                        'approved_apps': self._get_user_project_keys(session, user.user_id),
                        'created_date': user.created_date.strftime('%Y-%m-%d') if user.created_date else None,
                        'approved_by': user.approved_by,
                        'last_login': user.last_login.strftime('%Y-%m-%d %H:%M:%S') if user.last_login else None,
                        'login_count': user.login_count
                    }
                    for user in users
                ]
                
        except Exception as e:
            print(f"[ERROR] Failed to get all users: {e}")
            return []
    
    def update_user_projects(self, username, project_keys, all_projects=False):
        """Update user's project access"""
        try:
            with self.get_session() as session:
                user = session.query(User).filter_by(username=username).first()
                
                if not user:
                    return False, "User not found"
                
                # Remove existing project associations
                session.query(user_projects_association).filter(
                    user_projects_association.c.user_id == user.user_id
                ).delete()
                
                if all_projects:
                    # Grant admin role or access to all projects
                    if user.role != 'admin':
                        # Add access to all projects
                        projects = session.query(Project).filter_by(is_active=True).all()
                        for project in projects:
                            session.execute(
                                user_projects_association.insert().values(
                                    user_id=user.user_id,
                                    project_id=project.project_id,
                                    access_level='admin',
                                    granted_by='admin'
                                )
                            )
                else:
                    # Grant access to specific projects
                    if project_keys:
                        projects = session.query(Project).filter(
                            and_(
                                Project.project_key.in_(project_keys),
                                Project.is_active == True
                            )
                        ).all()
                        
                        for project in projects:
                            session.execute(
                                user_projects_association.insert().values(
                                    user_id=user.user_id,
                                    project_id=project.project_id,
                                    access_level='user',
                                    granted_by='admin'
                                )
                            )
                
                return True, "User project access updated successfully"
                
        except Exception as e:
            print(f"[ERROR] Failed to update user projects: {e}")
            return False, f"Failed to update user projects: {str(e)}"
    
    def get_user_statistics(self):
        """Get user statistics for dashboard"""
        try:
            with self.get_session() as session:
                total_users = session.query(User).filter_by(is_active=True).count()
                active_users = session.query(User).filter(
                    and_(User.status == 'approved', User.is_active == True)
                ).count()
                pending_requests = session.query(AccessRequest).filter_by(status='pending').count()
                admin_users = session.query(User).filter(
                    and_(User.role == 'admin', User.is_active == True)
                ).count()
                
                return {
                    'total_users': total_users,
                    'active_users_count': active_users,
                    'pending_requests_count': pending_requests,
                    'admin_users_count': admin_users
                }
                
        except Exception as e:
            print(f"[ERROR] Failed to get user statistics: {e}")
            return {
                'total_users': 0,
                'active_users_count': 0,
                'pending_requests_count': 0,
                'admin_users_count': 0
            }
    
    def log_system_event(self, event_type, message, username=None, ip_address=None):
        """Log system events"""
        try:
            with self.get_session() as session:
                log_entry = SystemLog(
                    log_type='AUDIT',
                    event_type=event_type,
                    username=username,
                    ip_address=ip_address,
                    message=message,
                    timestamp=datetime.now()
                )
                session.add(log_entry)
                
        except Exception as e:
            print(f"[ERROR] Failed to log system event: {e}")

if __name__ == '__main__':
    # Test the authentication system
    auth = SQLServerAuth()
    
    print("Testing SQL Server Authentication System...")
    
    # Test user lookup
    user = auth.check_user_login('admin')
    if user:
        print(f"[OK] Admin user found: {user['username']} ({user['role']})")
    else:
        print("[ERROR] Admin user not found")
    
    # Test statistics
    stats = auth.get_user_statistics()
    print(f"[OK] User statistics: {stats}")
    
    print("SQL Server authentication system test completed.")