#!/usr/bin/env python3
"""
MSI Factory Database Models using SQLAlchemy
MS SQL Server database models and ORM definitions
"""

from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Text, ForeignKey, Table
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.sql import func
from datetime import datetime
import os

Base = declarative_base()

# Many-to-many association table for user-projects
user_projects_association = Table(
    'user_projects', Base.metadata,
    Column('user_id', Integer, ForeignKey('users.user_id'), primary_key=True),
    Column('project_id', Integer, ForeignKey('projects.project_id'), primary_key=True),
    Column('access_level', String(20), default='user'),
    Column('granted_date', DateTime, default=func.now()),
    Column('granted_by', String(50)),
    Column('is_active', Boolean, default=True)
)

class User(Base):
    """User model for authentication and user management"""
    __tablename__ = 'users'
    
    user_id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    domain = Column(String(20), default='COMPANY')
    first_name = Column(String(50), nullable=False)
    middle_name = Column(String(50))
    last_name = Column(String(50), nullable=False)
    status = Column(String(20), default='pending', index=True)  # pending, approved, inactive, denied
    role = Column(String(20), default='user', index=True)  # user, admin
    created_date = Column(DateTime, default=func.now())
    approved_date = Column(DateTime)
    approved_by = Column(String(50))
    last_login = Column(DateTime)
    login_count = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    projects = relationship("Project", secondary=user_projects_association, back_populates="users")
    access_requests = relationship("AccessRequest", back_populates="user")
    msi_builds = relationship("MSIBuild", back_populates="user")
    user_sessions = relationship("UserSession", back_populates="user")
    system_logs = relationship("SystemLog", back_populates="user")
    
    def __repr__(self):
        return f"<User(username='{self.username}', role='{self.role}')>"

class Project(Base):
    """Project model for MSI generation projects"""
    __tablename__ = 'projects'
    
    project_id = Column(Integer, primary_key=True, autoincrement=True)
    project_name = Column(String(100), nullable=False)
    project_key = Column(String(20), unique=True, nullable=False, index=True)
    description = Column(Text)
    project_type = Column(String(20), nullable=False, index=True)  # WebApp, Service, Website, Desktop, API
    owner_team = Column(String(100), nullable=False)
    status = Column(String(20), default='active', index=True)  # active, inactive, maintenance, archived
    color_primary = Column(String(7), default='#2c3e50')
    color_secondary = Column(String(7), default='#3498db')
    created_date = Column(DateTime, default=func.now())
    created_by = Column(String(50), nullable=False)
    updated_date = Column(DateTime, default=func.now(), onupdate=func.now())
    updated_by = Column(String(50))
    is_active = Column(Boolean, default=True)
    
    # Relationships
    users = relationship("User", secondary=user_projects_association, back_populates="projects")
    environments = relationship("ProjectEnvironment", back_populates="project", cascade="all, delete-orphan")
    access_requests = relationship("AccessRequest", back_populates="project")
    msi_builds = relationship("MSIBuild", back_populates="project")
    
    def __repr__(self):
        return f"<Project(project_key='{self.project_key}', name='{self.project_name}')>"

class ProjectEnvironment(Base):
    """Project environments model"""
    __tablename__ = 'project_environments'
    
    env_id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(Integer, ForeignKey('projects.project_id'), nullable=False)
    environment_name = Column(String(20), nullable=False)  # DEV, QA, UAT, PREPROD, PROD, SIT, DR
    environment_description = Column(String(100))
    is_active = Column(Boolean, default=True)
    created_date = Column(DateTime, default=func.now())
    
    # Relationships
    project = relationship("Project", back_populates="environments")
    
    def __repr__(self):
        return f"<ProjectEnvironment(project_id={self.project_id}, env='{self.environment_name}')>"

class AccessRequest(Base):
    """Access request model for user project access requests"""
    __tablename__ = 'access_requests'
    
    request_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('users.user_id'))
    username = Column(String(50), nullable=False)
    email = Column(String(100), nullable=False)
    first_name = Column(String(50), nullable=False)
    middle_name = Column(String(50))
    last_name = Column(String(50), nullable=False)
    project_id = Column(Integer, ForeignKey('projects.project_id'), nullable=False)
    reason = Column(Text)
    status = Column(String(20), default='pending', index=True)  # pending, approved, denied
    requested_date = Column(DateTime, default=func.now())
    processed_date = Column(DateTime)
    processed_by = Column(String(50))
    denial_reason = Column(Text)
    
    # Relationships
    user = relationship("User", back_populates="access_requests")
    project = relationship("Project", back_populates="access_requests")
    
    def __repr__(self):
        return f"<AccessRequest(username='{self.username}', project_id={self.project_id}, status='{self.status}')>"

class MSIBuild(Base):
    """MSI build history model"""
    __tablename__ = 'msi_builds'
    
    build_id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String(50), unique=True, nullable=False, index=True)
    project_id = Column(Integer, ForeignKey('projects.project_id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    component_type = Column(String(20), nullable=False)
    environments = Column(Text, nullable=False)  # JSON array of environments
    build_status = Column(String(20), default='queued', index=True)  # queued, in_progress, completed, failed, cancelled
    start_time = Column(DateTime, default=func.now())
    end_time = Column(DateTime)
    build_duration = Column(Integer)  # in seconds
    build_log = Column(Text)
    output_files = Column(Text)  # JSON array of generated files
    error_message = Column(Text)
    build_version = Column(String(20))
    created_by = Column(String(50), nullable=False)
    
    # Relationships
    project = relationship("Project", back_populates="msi_builds")
    user = relationship("User", back_populates="msi_builds")
    
    def __repr__(self):
        return f"<MSIBuild(job_id='{self.job_id}', status='{self.build_status}')>"

class SystemLog(Base):
    """System logging model"""
    __tablename__ = 'system_logs'
    
    log_id = Column(Integer, primary_key=True, autoincrement=True)
    log_type = Column(String(20), nullable=False, index=True)  # INFO, WARNING, ERROR, SECURITY, AUDIT
    event_type = Column(String(50), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey('users.user_id'))
    username = Column(String(50), index=True)
    ip_address = Column(String(45))
    user_agent = Column(Text)
    event_data = Column(Text)  # JSON data
    message = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=func.now(), index=True)
    session_id = Column(String(100))
    
    # Relationships
    user = relationship("User", back_populates="system_logs")
    
    def __repr__(self):
        return f"<SystemLog(log_type='{self.log_type}', event_type='{self.event_type}')>"

class UserSession(Base):
    """User session tracking model"""
    __tablename__ = 'user_sessions'
    
    session_id = Column(String(100), primary_key=True)
    user_id = Column(Integer, ForeignKey('users.user_id'), nullable=False)
    username = Column(String(50), nullable=False, index=True)
    ip_address = Column(String(45))
    user_agent = Column(Text)
    login_time = Column(DateTime, default=func.now())
    last_activity = Column(DateTime, default=func.now())
    logout_time = Column(DateTime)
    is_active = Column(Boolean, default=True, index=True)
    session_data = Column(Text)  # JSON data
    
    # Relationships
    user = relationship("User", back_populates="user_sessions")
    
    def __repr__(self):
        return f"<UserSession(username='{self.username}', is_active={self.is_active})>"

class SystemSetting(Base):
    """System settings model"""
    __tablename__ = 'system_settings'
    
    setting_id = Column(Integer, primary_key=True, autoincrement=True)
    setting_key = Column(String(50), unique=True, nullable=False)
    setting_value = Column(Text, nullable=False)
    setting_type = Column(String(20), default='string')  # string, integer, boolean, json
    description = Column(Text)
    category = Column(String(30), default='general')
    is_encrypted = Column(Boolean, default=False)
    created_date = Column(DateTime, default=func.now())
    updated_date = Column(DateTime, default=func.now(), onupdate=func.now())
    updated_by = Column(String(50))
    
    def __repr__(self):
        return f"<SystemSetting(key='{self.setting_key}', value='{self.setting_value}')>"

class Application(Base):
    """Legacy applications model for compatibility"""
    __tablename__ = 'applications'
    
    app_id = Column(Integer, primary_key=True, autoincrement=True)
    app_short_key = Column(String(20), unique=True, nullable=False)
    app_name = Column(String(100), nullable=False)
    description = Column(Text)
    owner_team = Column(String(100), nullable=False)
    status = Column(String(20), default='active')
    created_date = Column(DateTime, default=func.now())
    is_active = Column(Boolean, default=True)
    
    def __repr__(self):
        return f"<Application(app_short_key='{self.app_short_key}', name='{self.app_name}')>"


# Simple database setup
from config import get_config

config = get_config()()
connection_string = config.database_url

engine = create_engine(
    connection_string,
    echo=config.SQLALCHEMY_ECHO,
    poolclass=None
)

SessionLocal = sessionmaker(bind=engine)

def get_db_session():
    """Get database session"""
    return SessionLocal()

def create_tables():
    """Create all database tables"""
    Base.metadata.create_all(bind=engine)
    print("[OK] Database tables created successfully")

def drop_tables():
    """Drop all database tables"""
    Base.metadata.drop_all(bind=engine)
    print("[OK] Database tables dropped successfully")

if __name__ == '__main__':
    # Create tables when run directly
    print("Creating MSI Factory database tables...")
    create_tables()
    print("Database setup complete!")