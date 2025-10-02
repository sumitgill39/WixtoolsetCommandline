-- ============================================================
-- MSI Factory Complete Database Schema for MS SQL Server
-- Version: 7.0 - PRODUCTION READY (Current State)
-- Created: 2025-10-02 15:57:25
-- Description: Complete production schema extracted from current database
--              This reflects the ACTUAL current state of the database
-- ============================================================

SET NOCOUNT ON;
GO

-- ============================================================
-- DATABASE CREATION
-- ============================================================
IF NOT EXISTS (SELECT * FROM sys.databases WHERE name = 'MSIFactory')
BEGIN
    CREATE DATABASE MSIFactory;
END
GO

USE MSIFactory;
GO

-- ============================================================
-- TABLES
-- ============================================================

-- Table: artifact_history
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='artifact_history' AND xtype='U')
BEGIN
    CREATE TABLE artifact_history (
        history_id INT IDENTITY(1,1) NOT NULL,
        component_id INT,
        artifact_version VARCHAR(100),
        download_path VARCHAR(500),
        extract_path VARCHAR(500),
        download_time DATETIME,
        branch_name VARCHAR(100),
        artifact_size BIGINT,
        artifact_hash VARCHAR(100),
        status VARCHAR(20) DEFAULT ('downloaded'),
        error_message TEXT,
        PRIMARY KEY (history_id)
    );
END
GO

-- Add foreign key: FK__artifact___compo__18EBB532
IF NOT EXISTS (SELECT * FROM sys.foreign_keys WHERE name = 'FK__artifact___compo__18EBB532')
BEGIN
    ALTER TABLE artifact_history
    ADD CONSTRAINT FK__artifact___compo__18EBB532
    FOREIGN KEY (component_id) REFERENCES components(component_id) ON DELETE CASCADE;
END
GO

-- Add check constraint: CK__artifact___statu__17F790F9
IF NOT EXISTS (SELECT * FROM sys.check_constraints WHERE name = 'CK__artifact___statu__17F790F9')
BEGIN
    ALTER TABLE artifact_history
    ADD CONSTRAINT CK__artifact___statu__17F790F9 CHECK ([status]='deleted' OR [status]='failed' OR [status]='extracted' OR [status]='downloaded' OR [status]='downloading');
END
GO

-- Table: branch_mappings
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='branch_mappings' AND xtype='U')
BEGIN
    CREATE TABLE branch_mappings (
        mapping_id INT IDENTITY(1,1) NOT NULL,
        project_id INT,
        branch_pattern VARCHAR(100),
        repository_path VARCHAR(200),
        environment_type VARCHAR(50),
        auto_deploy BIT DEFAULT ((0)),
        priority INT DEFAULT ((5)),
        is_active BIT NOT NULL DEFAULT ((1)),
        created_date DATETIME DEFAULT (getdate()),
        PRIMARY KEY (mapping_id)
    );
END
GO

-- Add foreign key: FK__branch_ma__proje__14270015
IF NOT EXISTS (SELECT * FROM sys.foreign_keys WHERE name = 'FK__branch_ma__proje__14270015')
BEGIN
    ALTER TABLE branch_mappings
    ADD CONSTRAINT FK__branch_ma__proje__14270015
    FOREIGN KEY (project_id) REFERENCES projects(project_id) ON DELETE CASCADE;
END
GO

-- Table: cmdb_server_changes
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='cmdb_server_changes' AND xtype='U')
BEGIN
    CREATE TABLE cmdb_server_changes (
        change_id INT IDENTITY(1,1) NOT NULL,
        server_id INT NOT NULL,
        change_type VARCHAR(50) NOT NULL,
        field_name VARCHAR(100),
        old_value TEXT,
        new_value TEXT,
        change_reason TEXT,
        changed_date DATETIME DEFAULT (getdate()),
        changed_by VARCHAR(100) NOT NULL,
        PRIMARY KEY (change_id)
    );
END
GO

-- Add foreign key: FK__cmdb_serv__serve__251C81ED
IF NOT EXISTS (SELECT * FROM sys.foreign_keys WHERE name = 'FK__cmdb_serv__serve__251C81ED')
BEGIN
    ALTER TABLE cmdb_server_changes
    ADD CONSTRAINT FK__cmdb_serv__serve__251C81ED
    FOREIGN KEY (server_id) REFERENCES cmdb_servers(server_id) ON DELETE CASCADE;
END
GO

-- Add check constraint: CK__cmdb_serv__chang__2334397B
IF NOT EXISTS (SELECT * FROM sys.check_constraints WHERE name = 'CK__cmdb_serv__chang__2334397B')
BEGIN
    ALTER TABLE cmdb_server_changes
    ADD CONSTRAINT CK__cmdb_serv__chang__2334397B CHECK ([change_type]='assignment_change' OR [change_type]='status_change' OR [change_type]='deleted' OR [change_type]='updated' OR [change_type]='created');
END
GO

-- Table: cmdb_server_group_members
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='cmdb_server_group_members' AND xtype='U')
BEGIN
    CREATE TABLE cmdb_server_group_members (
        membership_id INT IDENTITY(1,1) NOT NULL,
        group_id INT NOT NULL,
        server_id INT NOT NULL,
        role VARCHAR(50) DEFAULT ('member'),
        priority INT DEFAULT ((1)),
        is_active BIT DEFAULT ((1)),
        joined_date DATETIME DEFAULT (getdate()),
        PRIMARY KEY (membership_id)
    );
END
GO

-- Add foreign key: FK__cmdb_serv__serve__0D44F85C
IF NOT EXISTS (SELECT * FROM sys.foreign_keys WHERE name = 'FK__cmdb_serv__serve__0D44F85C')
BEGIN
    ALTER TABLE cmdb_server_group_members
    ADD CONSTRAINT FK__cmdb_serv__serve__0D44F85C
    FOREIGN KEY (server_id) REFERENCES cmdb_servers(server_id) ON DELETE CASCADE;
END
GO

-- Add foreign key: FK__cmdb_serv__group__0C50D423
IF NOT EXISTS (SELECT * FROM sys.foreign_keys WHERE name = 'FK__cmdb_serv__group__0C50D423')
BEGIN
    ALTER TABLE cmdb_server_group_members
    ADD CONSTRAINT FK__cmdb_serv__group__0C50D423
    FOREIGN KEY (group_id) REFERENCES cmdb_server_groups(group_id) ON DELETE CASCADE;
END
GO

-- Add check constraint: CK__cmdb_serve__role__0880433F
IF NOT EXISTS (SELECT * FROM sys.check_constraints WHERE name = 'CK__cmdb_serve__role__0880433F')
BEGIN
    ALTER TABLE cmdb_server_group_members
    ADD CONSTRAINT CK__cmdb_serve__role__0880433F CHECK ([role]='load_balancer' OR [role]='backup' OR [role]='primary' OR [role]='member');
END
GO

-- Add unique constraint: UQ__cmdb_ser__4BA22064FF02595A
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'UQ__cmdb_ser__4BA22064FF02595A')
BEGIN
    ALTER TABLE cmdb_server_group_members
    ADD CONSTRAINT UQ__cmdb_ser__4BA22064FF02595A UNIQUE (group_id, server_id);
END
GO

-- Table: cmdb_server_groups
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='cmdb_server_groups' AND xtype='U')
BEGIN
    CREATE TABLE cmdb_server_groups (
        group_id INT IDENTITY(1,1) NOT NULL,
        group_name VARCHAR(255) NOT NULL,
        group_type VARCHAR(50) NOT NULL,
        description TEXT,
        load_balancer_server_id INT,
        load_balancing_algorithm VARCHAR(50),
        health_check_url VARCHAR(500),
        health_check_interval INT DEFAULT ((30)),
        min_servers INT DEFAULT ((1)),
        max_servers INT DEFAULT ((10)),
        auto_scaling_enabled BIT DEFAULT ((0)),
        created_date DATETIME DEFAULT (getdate()),
        created_by VARCHAR(100),
        is_active BIT DEFAULT ((1)),
        PRIMARY KEY (group_id)
    );
END
GO

-- Add foreign key: FK__cmdb_serv__load___01D345B0
IF NOT EXISTS (SELECT * FROM sys.foreign_keys WHERE name = 'FK__cmdb_serv__load___01D345B0')
BEGIN
    ALTER TABLE cmdb_server_groups
    ADD CONSTRAINT FK__cmdb_serv__load___01D345B0
    FOREIGN KEY (load_balancer_server_id) REFERENCES cmdb_servers(server_id);
END
GO

-- Add check constraint: CK_group_min_max_servers
IF NOT EXISTS (SELECT * FROM sys.check_constraints WHERE name = 'CK_group_min_max_servers')
BEGIN
    ALTER TABLE cmdb_server_groups
    ADD CONSTRAINT CK_group_min_max_servers CHECK ([min_servers]<=[max_servers]);
END
GO

-- Add check constraint: CK_group_health_interval
IF NOT EXISTS (SELECT * FROM sys.check_constraints WHERE name = 'CK_group_health_interval')
BEGIN
    ALTER TABLE cmdb_server_groups
    ADD CONSTRAINT CK_group_health_interval CHECK ([health_check_interval]>(0));
END
GO

-- Add check constraint: CK__cmdb_serv__group__7B264821
IF NOT EXISTS (SELECT * FROM sys.check_constraints WHERE name = 'CK__cmdb_serv__group__7B264821')
BEGIN
    ALTER TABLE cmdb_server_groups
    ADD CONSTRAINT CK__cmdb_serv__group__7B264821 CHECK ([group_type]='development' OR [group_type]='failover' OR [group_type]='load_balancer' OR [group_type]='cluster');
END
GO

-- Add unique constraint: UQ__cmdb_ser__E8F4F58D2650FC60
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'UQ__cmdb_ser__E8F4F58D2650FC60')
BEGIN
    ALTER TABLE cmdb_server_groups
    ADD CONSTRAINT UQ__cmdb_ser__E8F4F58D2650FC60 UNIQUE (group_name);
END
GO

-- Table: cmdb_servers
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='cmdb_servers' AND xtype='U')
BEGIN
    CREATE TABLE cmdb_servers (
        server_id INT IDENTITY(1,1) NOT NULL,
        server_name VARCHAR(255) NOT NULL,
        fqdn VARCHAR(500),
        infra_type VARCHAR(50) NOT NULL,
        ip_address VARCHAR(45) NOT NULL,
        ip_address_internal VARCHAR(45),
        region VARCHAR(100),
        datacenter VARCHAR(100),
        availability_zone VARCHAR(50),
        environment_type VARCHAR(50),
        status VARCHAR(20) DEFAULT ('active'),
        cpu_cores INT,
        memory_gb INT,
        storage_gb BIGINT,
        network_speed VARCHAR(20),
        current_app_count INT DEFAULT ((0)),
        max_concurrent_apps INT DEFAULT ((1)),
        instance_type VARCHAR(100),
        instance_id VARCHAR(200),
        cloud_account_id VARCHAR(200),
        resource_group VARCHAR(200),
        subnet_id VARCHAR(200),
        security_groups TEXT,
        os_name VARCHAR(100),
        os_version VARCHAR(50),
        os_architecture VARCHAR(20),
        patch_level VARCHAR(100),
        public_dns VARCHAR(500),
        private_dns VARCHAR(500),
        vpc_id VARCHAR(200),
        network_acl TEXT,
        owner_team VARCHAR(100),
        technical_contact VARCHAR(100),
        business_contact VARCHAR(100),
        cost_center VARCHAR(50),
        monitoring_enabled BIT DEFAULT ((1)),
        backup_enabled BIT DEFAULT ((1)),
        patching_group VARCHAR(50),
        maintenance_window VARCHAR(100),
        compliance_tags TEXT,
        security_classification VARCHAR(50),
        data_classification VARCHAR(50),
        created_date DATETIME DEFAULT (getdate()),
        created_by VARCHAR(100),
        last_updated DATETIME DEFAULT (getdate()),
        updated_by VARCHAR(100),
        is_active BIT DEFAULT ((1)),
        PRIMARY KEY (server_id)
    );
END
GO

-- Add check constraint: CK__cmdb_serv__infra__690797E6
IF NOT EXISTS (SELECT * FROM sys.check_constraints WHERE name = 'CK__cmdb_serv__infra__690797E6')
BEGIN
    ALTER TABLE cmdb_servers
    ADD CONSTRAINT CK__cmdb_serv__infra__690797E6 CHECK ([infra_type]='HYPERV' OR [infra_type]='VMWARE' OR [infra_type]='WINTEL' OR [infra_type]='AZURE' OR [infra_type]='AWS');
END
GO

-- Add check constraint: CK__cmdb_serv__envir__69FBBC1F
IF NOT EXISTS (SELECT * FROM sys.check_constraints WHERE name = 'CK__cmdb_serv__envir__69FBBC1F')
BEGIN
    ALTER TABLE cmdb_servers
    ADD CONSTRAINT CK__cmdb_serv__envir__69FBBC1F CHECK ([environment_type]='shared' OR [environment_type]='production' OR [environment_type]='staging' OR [environment_type]='testing' OR [environment_type]='development');
END
GO

-- Add check constraint: CK__cmdb_serv__statu__6BE40491
IF NOT EXISTS (SELECT * FROM sys.check_constraints WHERE name = 'CK__cmdb_serv__statu__6BE40491')
BEGIN
    ALTER TABLE cmdb_servers
    ADD CONSTRAINT CK__cmdb_serv__statu__6BE40491 CHECK ([status]='decommissioned' OR [status]='maintenance' OR [status]='inactive' OR [status]='active');
END
GO

-- Add check constraint: CK_cmdb_cpu_cores
IF NOT EXISTS (SELECT * FROM sys.check_constraints WHERE name = 'CK_cmdb_cpu_cores')
BEGIN
    ALTER TABLE cmdb_servers
    ADD CONSTRAINT CK_cmdb_cpu_cores CHECK ([cpu_cores] IS NULL OR [cpu_cores]>(0));
END
GO

-- Add check constraint: CK_cmdb_memory
IF NOT EXISTS (SELECT * FROM sys.check_constraints WHERE name = 'CK_cmdb_memory')
BEGIN
    ALTER TABLE cmdb_servers
    ADD CONSTRAINT CK_cmdb_memory CHECK ([memory_gb] IS NULL OR [memory_gb]>(0));
END
GO

-- Add check constraint: CK_cmdb_storage
IF NOT EXISTS (SELECT * FROM sys.check_constraints WHERE name = 'CK_cmdb_storage')
BEGIN
    ALTER TABLE cmdb_servers
    ADD CONSTRAINT CK_cmdb_storage CHECK ([storage_gb] IS NULL OR [storage_gb]>(0));
END
GO

-- Add check constraint: CK_cmdb_max_apps
IF NOT EXISTS (SELECT * FROM sys.check_constraints WHERE name = 'CK_cmdb_max_apps')
BEGIN
    ALTER TABLE cmdb_servers
    ADD CONSTRAINT CK_cmdb_max_apps CHECK ([max_concurrent_apps]>(0));
END
GO

-- Add check constraint: CK_cmdb_current_apps
IF NOT EXISTS (SELECT * FROM sys.check_constraints WHERE name = 'CK_cmdb_current_apps')
BEGIN
    ALTER TABLE cmdb_servers
    ADD CONSTRAINT CK_cmdb_current_apps CHECK ([current_app_count]>=(0));
END
GO

-- Add unique constraint: UQ__cmdb_ser__37F8F950F013C55A
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'UQ__cmdb_ser__37F8F950F013C55A')
BEGIN
    ALTER TABLE cmdb_servers
    ADD CONSTRAINT UQ__cmdb_ser__37F8F950F013C55A UNIQUE (server_name);
END
GO

-- Table: component_branches
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='component_branches' AND xtype='U')
BEGIN
    CREATE TABLE component_branches (
        branch_id INT IDENTITY(1,1) NOT NULL,
        component_id INT NOT NULL,
        branch_name VARCHAR(100) NOT NULL,
        current_version INT DEFAULT ((1)),
        last_build_date DATETIME,
        last_build_number VARCHAR(50),
        branch_status VARCHAR(20) DEFAULT ('active'),
        auto_build BIT DEFAULT ((0)),
        description TEXT,
        is_active BIT DEFAULT ((1)),
        created_date DATETIME DEFAULT (getdate()),
        created_by VARCHAR(100),
        updated_date DATETIME,
        updated_by VARCHAR(100),
        major_version INT DEFAULT ((1)),
        minor_version INT DEFAULT ((0)),
        patch_version INT DEFAULT ((0)),
        build_number INT DEFAULT ((0)),
        path_pattern_override VARCHAR(500),
        auto_increment VARCHAR(20) DEFAULT ('build'),
        PRIMARY KEY (branch_id)
    );
END
GO

-- Add foreign key: FK__component__compo__5B78929E
IF NOT EXISTS (SELECT * FROM sys.foreign_keys WHERE name = 'FK__component__compo__5B78929E')
BEGIN
    ALTER TABLE component_branches
    ADD CONSTRAINT FK__component__compo__5B78929E
    FOREIGN KEY (component_id) REFERENCES components(component_id) ON DELETE CASCADE;
END
GO

-- Add check constraint: CK__component__auto___1699586C
IF NOT EXISTS (SELECT * FROM sys.check_constraints WHERE name = 'CK__component__auto___1699586C')
BEGIN
    ALTER TABLE component_branches
    ADD CONSTRAINT CK__component__auto___1699586C CHECK ([auto_increment]='revision' OR [auto_increment]='build' OR [auto_increment]='minor' OR [auto_increment]='major');
END
GO

-- Add check constraint: CK__component__branc__57A801BA
IF NOT EXISTS (SELECT * FROM sys.check_constraints WHERE name = 'CK__component__branc__57A801BA')
BEGIN
    ALTER TABLE component_branches
    ADD CONSTRAINT CK__component__branc__57A801BA CHECK ([branch_status]='archived' OR [branch_status]='inactive' OR [branch_status]='active');
END
GO

-- Add unique constraint: UQ__componen__62467DBE8CF9CA84
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'UQ__componen__62467DBE8CF9CA84')
BEGIN
    ALTER TABLE component_branches
    ADD CONSTRAINT UQ__componen__62467DBE8CF9CA84 UNIQUE (branch_name, component_id);
END
GO

-- Table: component_build_artifacts
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='component_build_artifacts' AND xtype='U')
BEGIN
    CREATE TABLE component_build_artifacts (
        artifact_id INT IDENTITY(1,1) NOT NULL,
        build_id INT NOT NULL,
        artifact_name VARCHAR(255) NOT NULL,
        artifact_type VARCHAR(50) DEFAULT ('zip'),
        artifact_path VARCHAR(500),
        download_url VARCHAR(1000),
        file_size BIGINT,
        checksum VARCHAR(100),
        checksum_type VARCHAR(20) DEFAULT ('SHA256'),
        is_primary BIT DEFAULT ((0)),
        created_date DATETIME DEFAULT (getdate()),
        PRIMARY KEY (artifact_id)
    );
END
GO

-- Add foreign key: FK__component__build__6E8B6712
IF NOT EXISTS (SELECT * FROM sys.foreign_keys WHERE name = 'FK__component__build__6E8B6712')
BEGIN
    ALTER TABLE component_build_artifacts
    ADD CONSTRAINT FK__component__build__6E8B6712
    FOREIGN KEY (build_id) REFERENCES component_builds(build_id) ON DELETE CASCADE;
END
GO

-- Add check constraint: CK__component__artif__6ABAD62E
IF NOT EXISTS (SELECT * FROM sys.check_constraints WHERE name = 'CK__component__artif__6ABAD62E')
BEGIN
    ALTER TABLE component_build_artifacts
    ADD CONSTRAINT CK__component__artif__6ABAD62E CHECK ([artifact_type]='other' OR [artifact_type]='tar' OR [artifact_type]='war' OR [artifact_type]='jar' OR [artifact_type]='dll' OR [artifact_type]='exe' OR [artifact_type]='msi' OR [artifact_type]='zip');
END
GO

-- Table: component_builds
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='component_builds' AND xtype='U')
BEGIN
    CREATE TABLE component_builds (
        build_id INT IDENTITY(1,1) NOT NULL,
        branch_id INT NOT NULL,
        build_number VARCHAR(50) NOT NULL,
        version_number INT NOT NULL,
        build_date DATETIME DEFAULT (getdate()),
        build_status VARCHAR(20) DEFAULT ('pending'),
        jfrog_path VARCHAR(500),
        jfrog_download_url VARCHAR(1000),
        artifact_size BIGINT,
        artifact_checksum VARCHAR(100),
        git_commit_hash VARCHAR(40),
        git_commit_message TEXT,
        build_duration_seconds INT,
        build_log_path VARCHAR(500),
        ci_job_id VARCHAR(100),
        ci_pipeline_id VARCHAR(100),
        ci_system VARCHAR(50),
        tests_passed INT DEFAULT ((0)),
        tests_failed INT DEFAULT ((0)),
        code_coverage_percent DECIMAL(5, 2),
        quality_gate_status VARCHAR(20),
        is_deployed BIT DEFAULT ((0)),
        deployed_environments TEXT,
        created_by VARCHAR(100),
        is_active BIT DEFAULT ((1)),
        PRIMARY KEY (build_id)
    );
END
GO

-- Add foreign key: FK__component__branc__66EA454A
IF NOT EXISTS (SELECT * FROM sys.foreign_keys WHERE name = 'FK__component__branc__66EA454A')
BEGIN
    ALTER TABLE component_builds
    ADD CONSTRAINT FK__component__branc__66EA454A
    FOREIGN KEY (branch_id) REFERENCES component_branches(branch_id) ON DELETE CASCADE;
END
GO

-- Add check constraint: CK__component__build__61316BF4
IF NOT EXISTS (SELECT * FROM sys.check_constraints WHERE name = 'CK__component__build__61316BF4')
BEGIN
    ALTER TABLE component_builds
    ADD CONSTRAINT CK__component__build__61316BF4 CHECK ([build_status]='cancelled' OR [build_status]='failed' OR [build_status]='success' OR [build_status]='building' OR [build_status]='pending');
END
GO

-- Add check constraint: CK__component__quali__640DD89F
IF NOT EXISTS (SELECT * FROM sys.check_constraints WHERE name = 'CK__component__quali__640DD89F')
BEGIN
    ALTER TABLE component_builds
    ADD CONSTRAINT CK__component__quali__640DD89F CHECK ([quality_gate_status]='not_run' OR [quality_gate_status]='warning' OR [quality_gate_status]='failed' OR [quality_gate_status]='passed');
END
GO

-- Add unique constraint: UQ__componen__19B56E55EBACEE40
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'UQ__componen__19B56E55EBACEE40')
BEGIN
    ALTER TABLE component_builds
    ADD CONSTRAINT UQ__componen__19B56E55EBACEE40 UNIQUE (branch_id, build_number);
END
GO

-- Table: component_environments
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='component_environments' AND xtype='U')
BEGIN
    CREATE TABLE component_environments (
        config_id INT IDENTITY(1,1) NOT NULL,
        component_id INT NOT NULL,
        environment_id INT NOT NULL,
        artifact_url VARCHAR(500),
        deployment_path VARCHAR(255),
        configuration_json TEXT,
        is_active BIT DEFAULT ((1)),
        created_date DATETIME DEFAULT (getdate()),
        PRIMARY KEY (config_id)
    );
END
GO

-- Add foreign key: FK__component__envir__65370702
IF NOT EXISTS (SELECT * FROM sys.foreign_keys WHERE name = 'FK__component__envir__65370702')
BEGIN
    ALTER TABLE component_environments
    ADD CONSTRAINT FK__component__envir__65370702
    FOREIGN KEY (environment_id) REFERENCES project_environments(env_id);
END
GO

-- Add foreign key: FK__component__compo__6442E2C9
IF NOT EXISTS (SELECT * FROM sys.foreign_keys WHERE name = 'FK__component__compo__6442E2C9')
BEGIN
    ALTER TABLE component_environments
    ADD CONSTRAINT FK__component__compo__6442E2C9
    FOREIGN KEY (component_id) REFERENCES components(component_id);
END
GO

-- Table: component_servers
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='component_servers' AND xtype='U')
BEGIN
    CREATE TABLE component_servers (
        component_server_id INT IDENTITY(1,1) NOT NULL,
        component_id INT NOT NULL,
        server_id INT NOT NULL,
        assignment_type VARCHAR(50) NOT NULL,
        deployment_path VARCHAR(500),
        status VARCHAR(20) DEFAULT ('active'),
        assigned_date DATETIME DEFAULT (getdate()),
        assigned_by VARCHAR(100),
        PRIMARY KEY (component_server_id)
    );
END
GO

-- Add foreign key: FK__component__serve__2057CCD0
IF NOT EXISTS (SELECT * FROM sys.foreign_keys WHERE name = 'FK__component__serve__2057CCD0')
BEGIN
    ALTER TABLE component_servers
    ADD CONSTRAINT FK__component__serve__2057CCD0
    FOREIGN KEY (server_id) REFERENCES cmdb_servers(server_id) ON DELETE CASCADE;
END
GO

-- Add foreign key: FK__component__compo__1F63A897
IF NOT EXISTS (SELECT * FROM sys.foreign_keys WHERE name = 'FK__component__compo__1F63A897')
BEGIN
    ALTER TABLE component_servers
    ADD CONSTRAINT FK__component__compo__1F63A897
    FOREIGN KEY (component_id) REFERENCES components(component_id);
END
GO

-- Add check constraint: CK__component__assig__1B9317B3
IF NOT EXISTS (SELECT * FROM sys.check_constraints WHERE name = 'CK__component__assig__1B9317B3')
BEGIN
    ALTER TABLE component_servers
    ADD CONSTRAINT CK__component__assig__1B9317B3 CHECK ([assignment_type]='development' OR [assignment_type]='backup' OR [assignment_type]='primary');
END
GO

-- Add check constraint: CK__component__statu__1D7B6025
IF NOT EXISTS (SELECT * FROM sys.check_constraints WHERE name = 'CK__component__statu__1D7B6025')
BEGIN
    ALTER TABLE component_servers
    ADD CONSTRAINT CK__component__statu__1D7B6025 CHECK ([status]='pending' OR [status]='inactive' OR [status]='active');
END
GO

-- Add unique constraint: UQ__componen__EB0B8EBFA2EDDCC4
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'UQ__componen__EB0B8EBFA2EDDCC4')
BEGIN
    ALTER TABLE component_servers
    ADD CONSTRAINT UQ__componen__EB0B8EBFA2EDDCC4 UNIQUE (assignment_type, component_id, server_id);
END
GO

-- Table: components
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='components' AND xtype='U')
BEGIN
    CREATE TABLE components (
        component_id INT IDENTITY(1,1) NOT NULL,
        component_guid UNIQUEIDENTIFIER DEFAULT (newid()),
        project_id INT NOT NULL,
        component_name VARCHAR(100) NOT NULL,
        component_type VARCHAR(20) NOT NULL,
        framework VARCHAR(20) NOT NULL,
        description TEXT,
        branch_name VARCHAR(100),
        polling_enabled BIT DEFAULT ((1)),
        last_poll_time DATETIME,
        last_artifact_version VARCHAR(100),
        last_download_path VARCHAR(500),
        last_extract_path VARCHAR(500),
        last_artifact_time DATETIME,
        artifact_source VARCHAR(255),
        is_enabled BIT NOT NULL DEFAULT ((1)),
        order_index INT DEFAULT ((1)),
        dependencies VARCHAR(500),
        app_name VARCHAR(100),
        app_version VARCHAR(50) DEFAULT ('1.0.0.0'),
        manufacturer VARCHAR(100) DEFAULT ('Your Company'),
        target_server VARCHAR(100),
        install_folder VARCHAR(500),
        iis_website_name VARCHAR(100),
        iis_app_pool_name VARCHAR(100),
        port INT,
        service_name VARCHAR(100),
        service_display_name VARCHAR(100),
        artifact_url VARCHAR(500),
        preferred_server_id INT,
        deployment_strategy VARCHAR(50) DEFAULT ('single_server'),
        resource_requirements TEXT,
        created_date DATETIME DEFAULT (getdate()),
        created_by VARCHAR(50) NOT NULL,
        updated_date DATETIME DEFAULT (getdate()),
        updated_by VARCHAR(50),
        jfrog_path_pattern VARCHAR(500) DEFAULT ('{branch}/Build{date}.{buildNumber}/{componentName}.zip'),
        version_strategy VARCHAR(50) DEFAULT ('auto_increment'),
        version_format VARCHAR(50) DEFAULT ('{major}.{minor}.{patch}.{build}'),
        current_major_version INT DEFAULT ((1)),
        current_minor_version INT DEFAULT ((0)),
        current_patch_version INT DEFAULT ((0)),
        current_build_number INT DEFAULT ((0)),
        date_format VARCHAR(20) DEFAULT ('yyyyMMdd'),
        build_number_format VARCHAR(50) DEFAULT ('{date}.{sequence}'),
        auto_version_increment BIT DEFAULT ((1)),
        PRIMARY KEY (component_id)
    );
END
GO

-- Add foreign key: FK__component__proje__03F0984C
IF NOT EXISTS (SELECT * FROM sys.foreign_keys WHERE name = 'FK__component__proje__03F0984C')
BEGIN
    ALTER TABLE components
    ADD CONSTRAINT FK__component__proje__03F0984C
    FOREIGN KEY (project_id) REFERENCES projects(project_id) ON DELETE CASCADE;
END
GO

-- Add foreign key: FK_components_preferred_server
IF NOT EXISTS (SELECT * FROM sys.foreign_keys WHERE name = 'FK_components_preferred_server')
BEGIN
    ALTER TABLE components
    ADD CONSTRAINT FK_components_preferred_server
    FOREIGN KEY (preferred_server_id) REFERENCES cmdb_servers(server_id);
END
GO

-- Add check constraint: CK__component__deplo__01142BA1
IF NOT EXISTS (SELECT * FROM sys.check_constraints WHERE name = 'CK__component__deplo__01142BA1')
BEGIN
    ALTER TABLE components
    ADD CONSTRAINT CK__component__deplo__01142BA1 CHECK ([deployment_strategy]='clustered' OR [deployment_strategy]='load_balanced' OR [deployment_strategy]='single_server' OR [deployment_strategy] IS NULL);
END
GO

-- Add check constraint: CK_components_name_not_empty
IF NOT EXISTS (SELECT * FROM sys.check_constraints WHERE name = 'CK_components_name_not_empty')
BEGIN
    ALTER TABLE components
    ADD CONSTRAINT CK_components_name_not_empty CHECK (len(Trim([component_name]))>(0));
END
GO

-- Add check constraint: CK__component__versi__056ECC6A
IF NOT EXISTS (SELECT * FROM sys.check_constraints WHERE name = 'CK__component__versi__056ECC6A')
BEGIN
    ALTER TABLE components
    ADD CONSTRAINT CK__component__versi__056ECC6A CHECK ([version_strategy]='date_based' OR [version_strategy]='manual' OR [version_strategy]='semantic' OR [version_strategy]='auto_increment');
END
GO

-- Add check constraint: CK__component__date___0C1BC9F9
IF NOT EXISTS (SELECT * FROM sys.check_constraints WHERE name = 'CK__component__date___0C1BC9F9')
BEGIN
    ALTER TABLE components
    ADD CONSTRAINT CK__component__date___0C1BC9F9 CHECK ([date_format]='yyMMdd' OR [date_format]='yyyy.MM.dd' OR [date_format]='yyyy-MM-dd' OR [date_format]='yyyyMMdd');
END
GO

-- Add check constraint: CK__component__compo__797309D9
IF NOT EXISTS (SELECT * FROM sys.check_constraints WHERE name = 'CK__component__compo__797309D9')
BEGIN
    ALTER TABLE components
    ADD CONSTRAINT CK__component__compo__797309D9 CHECK ([component_type]='library' OR [component_type]='desktop' OR [component_type]='api' OR [component_type]='scheduler' OR [component_type]='service' OR [component_type]='website' OR [component_type]='webapp');
END
GO

-- Add check constraint: CK__component__frame__7A672E12
IF NOT EXISTS (SELECT * FROM sys.check_constraints WHERE name = 'CK__component__frame__7A672E12')
BEGIN
    ALTER TABLE components
    ADD CONSTRAINT CK__component__frame__7A672E12 CHECK ([framework]='nodejs' OR [framework]='vue' OR [framework]='static' OR [framework]='python' OR [framework]='angular' OR [framework]='react' OR [framework]='netcore' OR [framework]='netframework');
END
GO

-- Add unique constraint: UK_components_project_name
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'UK_components_project_name')
BEGIN
    ALTER TABLE components
    ADD CONSTRAINT UK_components_project_name UNIQUE (component_name, project_id);
END
GO

-- Table: global_credentials
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='global_credentials' AND xtype='U')
BEGIN
    CREATE TABLE global_credentials (
        credential_id INT IDENTITY(1,1) NOT NULL,
        credential_name VARCHAR(100) NOT NULL,
        credential_type VARCHAR(50) NOT NULL,
        service_url VARCHAR(500),
        username VARCHAR(100) NOT NULL,
        password VARCHAR(255) NOT NULL,
        domain VARCHAR(100),
        additional_config TEXT,
        is_active BIT DEFAULT ((1)),
        is_default BIT DEFAULT ((0)),
        description TEXT,
        created_date DATETIME DEFAULT (getdate()),
        created_by VARCHAR(100),
        updated_date DATETIME,
        updated_by VARCHAR(100),
        last_used_date DATETIME,
        PRIMARY KEY (credential_id)
    );
END
GO

-- Add check constraint: CHK_credential_type
IF NOT EXISTS (SELECT * FROM sys.check_constraints WHERE name = 'CHK_credential_type')
BEGIN
    ALTER TABLE global_credentials
    ADD CONSTRAINT CHK_credential_type CHECK ([credential_type]='other' OR [credential_type]='database' OR [credential_type]='api' OR [credential_type]='ssh' OR [credential_type]='ftp' OR [credential_type]='git' OR [credential_type]='unc' OR [credential_type]='jfrog');
END
GO

-- Add unique constraint: UQ__global_c__AE195F616C6B2E9F
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'UQ__global_c__AE195F616C6B2E9F')
BEGIN
    ALTER TABLE global_credentials
    ADD CONSTRAINT UQ__global_c__AE195F616C6B2E9F UNIQUE (credential_name);
END
GO

-- Table: integrations_config
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='integrations_config' AND xtype='U')
BEGIN
    CREATE TABLE integrations_config (
        config_id INT IDENTITY(1,1) NOT NULL,
        integration_type VARCHAR(50) NOT NULL,
        integration_name VARCHAR(100) NOT NULL,
        base_url VARCHAR(500) NOT NULL,
        username VARCHAR(100),
        password VARCHAR(255),
        token VARCHAR(500),
        auth_type VARCHAR(20) NOT NULL DEFAULT ('username_password'),
        additional_config TEXT,
        is_enabled BIT NOT NULL DEFAULT ((1)),
        is_validated BIT DEFAULT ((0)),
        last_test_date DATETIME,
        last_test_result VARCHAR(20),
        last_test_message TEXT,
        timeout_seconds INT DEFAULT ((30)),
        retry_count INT DEFAULT ((3)),
        ssl_verify BIT DEFAULT ((1)),
        created_date DATETIME NOT NULL DEFAULT (getdate()),
        created_by VARCHAR(50) NOT NULL,
        updated_date DATETIME NOT NULL DEFAULT (getdate()),
        updated_by VARCHAR(50) NOT NULL,
        version_number INT DEFAULT ((1)),
        encryption_enabled BIT DEFAULT ((1)),
        last_password_change DATETIME,
        password_expires_date DATETIME,
        last_used_date DATETIME,
        usage_count INT DEFAULT ((0)),
        PRIMARY KEY (config_id)
    );
END
GO

-- Add check constraint: CK__integrati__auth___1B5E0D89
IF NOT EXISTS (SELECT * FROM sys.check_constraints WHERE name = 'CK__integrati__auth___1B5E0D89')
BEGIN
    ALTER TABLE integrations_config
    ADD CONSTRAINT CK__integrati__auth___1B5E0D89 CHECK ([auth_type]='basic_auth' OR [auth_type]='api_key' OR [auth_type]='token' OR [auth_type]='username_password');
END
GO

-- Add check constraint: CK__integrati__last___1E3A7A34
IF NOT EXISTS (SELECT * FROM sys.check_constraints WHERE name = 'CK__integrati__last___1E3A7A34')
BEGIN
    ALTER TABLE integrations_config
    ADD CONSTRAINT CK__integrati__last___1E3A7A34 CHECK ([last_test_result]='pending' OR [last_test_result]='failed' OR [last_test_result]='success' OR [last_test_result] IS NULL);
END
GO

-- Add check constraint: CK_integrations_base_url_format
IF NOT EXISTS (SELECT * FROM sys.check_constraints WHERE name = 'CK_integrations_base_url_format')
BEGIN
    ALTER TABLE integrations_config
    ADD CONSTRAINT CK_integrations_base_url_format CHECK ([base_url] like 'http://%' OR [base_url] like 'https://%');
END
GO

-- Add check constraint: CK_integrations_timeout
IF NOT EXISTS (SELECT * FROM sys.check_constraints WHERE name = 'CK_integrations_timeout')
BEGIN
    ALTER TABLE integrations_config
    ADD CONSTRAINT CK_integrations_timeout CHECK ([timeout_seconds]>(0) AND [timeout_seconds]<=(300));
END
GO

-- Add check constraint: CK_integrations_retry
IF NOT EXISTS (SELECT * FROM sys.check_constraints WHERE name = 'CK_integrations_retry')
BEGIN
    ALTER TABLE integrations_config
    ADD CONSTRAINT CK_integrations_retry CHECK ([retry_count]>=(0) AND [retry_count]<=(10));
END
GO

-- Add check constraint: CK_integrations_auth_requirements
IF NOT EXISTS (SELECT * FROM sys.check_constraints WHERE name = 'CK_integrations_auth_requirements')
BEGIN
    ALTER TABLE integrations_config
    ADD CONSTRAINT CK_integrations_auth_requirements CHECK ([auth_type]='username_password' AND [username] IS NOT NULL AND [password] IS NOT NULL OR [auth_type]='token' AND [token] IS NOT NULL OR [auth_type]='basic_auth' AND [username] IS NOT NULL AND [password] IS NOT NULL);
END
GO

-- Add unique constraint: UK_integrations_type_name
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'UK_integrations_type_name')
BEGIN
    ALTER TABLE integrations_config
    ADD CONSTRAINT UK_integrations_type_name UNIQUE (integration_name, integration_type);
END
GO

-- Table: msi_build_queue
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='msi_build_queue' AND xtype='U')
BEGIN
    CREATE TABLE msi_build_queue (
        queue_id INT IDENTITY(1,1) NOT NULL,
        component_id INT,
        project_id INT,
        source_path VARCHAR(500),
        status VARCHAR(50),
        queued_time DATETIME,
        start_time DATETIME,
        end_time DATETIME,
        error_message TEXT,
        msi_output_path VARCHAR(500),
        build_log TEXT,
        priority INT DEFAULT ((5)),
        PRIMARY KEY (queue_id)
    );
END
GO

-- Add foreign key: FK__msi_build__proje__46B27FE2
IF NOT EXISTS (SELECT * FROM sys.foreign_keys WHERE name = 'FK__msi_build__proje__46B27FE2')
BEGIN
    ALTER TABLE msi_build_queue
    ADD CONSTRAINT FK__msi_build__proje__46B27FE2
    FOREIGN KEY (project_id) REFERENCES projects(project_id);
END
GO

-- Add foreign key: FK__msi_build__compo__45BE5BA9
IF NOT EXISTS (SELECT * FROM sys.foreign_keys WHERE name = 'FK__msi_build__compo__45BE5BA9')
BEGIN
    ALTER TABLE msi_build_queue
    ADD CONSTRAINT FK__msi_build__compo__45BE5BA9
    FOREIGN KEY (component_id) REFERENCES components(component_id);
END
GO

-- Table: msi_builds
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='msi_builds' AND xtype='U')
BEGIN
    CREATE TABLE msi_builds (
        build_id INT IDENTITY(1,1) NOT NULL,
        project_id INT NOT NULL,
        component_id INT,
        environment_name VARCHAR(50) NOT NULL,
        build_version VARCHAR(50),
        build_status VARCHAR(20) DEFAULT ('pending'),
        msi_file_path VARCHAR(500),
        build_log TEXT,
        build_started DATETIME DEFAULT (getdate()),
        build_completed DATETIME,
        built_by VARCHAR(50) NOT NULL,
        PRIMARY KEY (build_id)
    );
END
GO

-- Add foreign key: FK__msi_build__proje__4C6B5938
IF NOT EXISTS (SELECT * FROM sys.foreign_keys WHERE name = 'FK__msi_build__proje__4C6B5938')
BEGIN
    ALTER TABLE msi_builds
    ADD CONSTRAINT FK__msi_build__proje__4C6B5938
    FOREIGN KEY (project_id) REFERENCES projects(project_id) ON DELETE CASCADE;
END
GO

-- Add foreign key: FK__msi_build__compo__4D5F7D71
IF NOT EXISTS (SELECT * FROM sys.foreign_keys WHERE name = 'FK__msi_build__compo__4D5F7D71')
BEGIN
    ALTER TABLE msi_builds
    ADD CONSTRAINT FK__msi_build__compo__4D5F7D71
    FOREIGN KEY (component_id) REFERENCES components(component_id);
END
GO

-- Add check constraint: CK__msi_build__build__4A8310C6
IF NOT EXISTS (SELECT * FROM sys.check_constraints WHERE name = 'CK__msi_build__build__4A8310C6')
BEGIN
    ALTER TABLE msi_builds
    ADD CONSTRAINT CK__msi_build__build__4A8310C6 CHECK ([build_status]='cancelled' OR [build_status]='failed' OR [build_status]='success' OR [build_status]='building' OR [build_status]='pending');
END
GO

-- Table: msi_configurations
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='msi_configurations' AND xtype='U')
BEGIN
    CREATE TABLE msi_configurations (
        config_id INT IDENTITY(1,1) NOT NULL,
        component_id INT NOT NULL,
        unique_id UNIQUEIDENTIFIER DEFAULT (newid()),
        app_name VARCHAR(255),
        app_version VARCHAR(50) DEFAULT ('1.0.0.0'),
        auto_increment_version BIT DEFAULT ((1)),
        manufacturer VARCHAR(255),
        upgrade_code UNIQUEIDENTIFIER,
        product_code UNIQUEIDENTIFIER,
        install_folder VARCHAR(500),
        target_server VARCHAR(255),
        target_environment VARCHAR(50),
        target_server_id INT,
        backup_server_id INT,
        component_type VARCHAR(50),
        iis_website_name VARCHAR(255),
        iis_app_path VARCHAR(255),
        iis_app_pool_name VARCHAR(255),
        iis_port INT,
        iis_binding_info TEXT,
        parent_website VARCHAR(255),
        parent_webapp VARCHAR(255),
        app_pool_identity VARCHAR(100),
        app_pool_dotnet_version VARCHAR(20),
        app_pool_pipeline_mode VARCHAR(20),
        app_pool_enable_32bit BIT DEFAULT ((0)),
        app_pool_start_mode VARCHAR(20),
        app_pool_idle_timeout INT DEFAULT ((20)),
        app_pool_recycling_schedule VARCHAR(500),
        enable_preload BIT DEFAULT ((0)),
        enable_anonymous_auth BIT DEFAULT ((1)),
        enable_windows_auth BIT DEFAULT ((0)),
        custom_headers TEXT,
        connection_strings TEXT,
        app_settings TEXT,
        service_name VARCHAR(255),
        service_display_name VARCHAR(255),
        service_description TEXT,
        service_start_type VARCHAR(50),
        service_account VARCHAR(255),
        service_password VARCHAR(500),
        service_dependencies VARCHAR(500),
        features TEXT,
        registry_entries TEXT,
        environment_variables TEXT,
        shortcuts TEXT,
        pre_install_script TEXT,
        post_install_script TEXT,
        pre_uninstall_script TEXT,
        post_uninstall_script TEXT,
        folder_permissions TEXT,
        created_date DATETIME DEFAULT (getdate()),
        created_by VARCHAR(100),
        updated_date DATETIME DEFAULT (getdate()),
        updated_by VARCHAR(100),
        is_template BIT DEFAULT ((0)),
        template_name VARCHAR(100),
        is_active BIT DEFAULT ((1)),
        PRIMARY KEY (config_id)
    );
END
GO

-- Add foreign key: FK_msi_target_server
IF NOT EXISTS (SELECT * FROM sys.foreign_keys WHERE name = 'FK_msi_target_server')
BEGIN
    ALTER TABLE msi_configurations
    ADD CONSTRAINT FK_msi_target_server
    FOREIGN KEY (target_server_id) REFERENCES cmdb_servers(server_id);
END
GO

-- Add foreign key: FK_msi_backup_server
IF NOT EXISTS (SELECT * FROM sys.foreign_keys WHERE name = 'FK_msi_backup_server')
BEGIN
    ALTER TABLE msi_configurations
    ADD CONSTRAINT FK_msi_backup_server
    FOREIGN KEY (backup_server_id) REFERENCES cmdb_servers(server_id);
END
GO

-- Add foreign key: FK__msi_confi__compo__37703C52
IF NOT EXISTS (SELECT * FROM sys.foreign_keys WHERE name = 'FK__msi_confi__compo__37703C52')
BEGIN
    ALTER TABLE msi_configurations
    ADD CONSTRAINT FK__msi_confi__compo__37703C52
    FOREIGN KEY (component_id) REFERENCES components(component_id) ON DELETE CASCADE;
END
GO

-- Add check constraint: CK_msi_port
IF NOT EXISTS (SELECT * FROM sys.check_constraints WHERE name = 'CK_msi_port')
BEGIN
    ALTER TABLE msi_configurations
    ADD CONSTRAINT CK_msi_port CHECK ([iis_port] IS NULL OR [iis_port]>=(1) AND [iis_port]<=(65535));
END
GO

-- Add check constraint: CK_msi_pipeline
IF NOT EXISTS (SELECT * FROM sys.check_constraints WHERE name = 'CK_msi_pipeline')
BEGIN
    ALTER TABLE msi_configurations
    ADD CONSTRAINT CK_msi_pipeline CHECK ([app_pool_pipeline_mode] IS NULL OR ([app_pool_pipeline_mode]='Classic' OR [app_pool_pipeline_mode]='Integrated'));
END
GO

-- Add check constraint: CK_msi_start_mode
IF NOT EXISTS (SELECT * FROM sys.check_constraints WHERE name = 'CK_msi_start_mode')
BEGIN
    ALTER TABLE msi_configurations
    ADD CONSTRAINT CK_msi_start_mode CHECK ([app_pool_start_mode] IS NULL OR ([app_pool_start_mode]='AlwaysRunning' OR [app_pool_start_mode]='OnDemand'));
END
GO

-- Add check constraint: CK_service_start
IF NOT EXISTS (SELECT * FROM sys.check_constraints WHERE name = 'CK_service_start')
BEGIN
    ALTER TABLE msi_configurations
    ADD CONSTRAINT CK_service_start CHECK ([service_start_type] IS NULL OR ([service_start_type]='Disabled' OR [service_start_type]='Manual' OR [service_start_type]='Automatic'));
END
GO

-- Add unique constraint: UQ__msi_conf__AEB1DA58F63A7A7A
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'UQ__msi_conf__AEB1DA58F63A7A7A')
BEGIN
    ALTER TABLE msi_configurations
    ADD CONSTRAINT UQ__msi_conf__AEB1DA58F63A7A7A UNIQUE (component_id);
END
GO

-- Table: msi_environment_configs
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='msi_environment_configs' AND xtype='U')
BEGIN
    CREATE TABLE msi_environment_configs (
        env_config_id INT IDENTITY(1,1) NOT NULL,
        config_id INT NOT NULL,
        environment VARCHAR(50) NOT NULL,
        target_server VARCHAR(255),
        install_folder VARCHAR(500),
        iis_website_name VARCHAR(255),
        iis_app_pool_name VARCHAR(255),
        iis_port INT,
        connection_strings TEXT,
        app_settings TEXT,
        service_account VARCHAR(255),
        approved_by VARCHAR(100),
        approval_date DATETIME,
        notes TEXT,
        PRIMARY KEY (env_config_id)
    );
END
GO

-- Add foreign key: FK__msi_envir__confi__3F115E1A
IF NOT EXISTS (SELECT * FROM sys.foreign_keys WHERE name = 'FK__msi_envir__confi__3F115E1A')
BEGIN
    ALTER TABLE msi_environment_configs
    ADD CONSTRAINT FK__msi_envir__confi__3F115E1A
    FOREIGN KEY (config_id) REFERENCES msi_configurations(config_id);
END
GO

-- Add unique constraint: UQ__msi_envi__2DA6B9866E65D9CE
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'UQ__msi_envi__2DA6B9866E65D9CE')
BEGIN
    ALTER TABLE msi_environment_configs
    ADD CONSTRAINT UQ__msi_envi__2DA6B9866E65D9CE UNIQUE (config_id, environment);
END
GO

-- Table: msi_generation_jobs
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='msi_generation_jobs' AND xtype='U')
BEGIN
    CREATE TABLE msi_generation_jobs (
        job_id INT IDENTITY(1,1) NOT NULL,
        project_id INT NOT NULL,
        build_id INT,
        branch_id INT,
        job_name VARCHAR(255) NOT NULL,
        job_status VARCHAR(20) DEFAULT ('pending'),
        use_specific_build BIT DEFAULT ((0)),
        selected_builds TEXT,
        msi_version VARCHAR(50),
        output_filename VARCHAR(255),
        output_path VARCHAR(500),
        total_components INT DEFAULT ((0)),
        completed_components INT DEFAULT ((0)),
        progress_percent DECIMAL(5, 2) DEFAULT ((0)),
        started_at DATETIME,
        completed_at DATETIME,
        duration_seconds INT,
        success_message TEXT,
        error_message TEXT,
        warnings TEXT,
        created_by VARCHAR(100),
        created_date DATETIME DEFAULT (getdate()),
        PRIMARY KEY (job_id)
    );
END
GO

-- Add foreign key: FK__msi_gener__proje__02925FBF
IF NOT EXISTS (SELECT * FROM sys.foreign_keys WHERE name = 'FK__msi_gener__proje__02925FBF')
BEGIN
    ALTER TABLE msi_generation_jobs
    ADD CONSTRAINT FK__msi_gener__proje__02925FBF
    FOREIGN KEY (project_id) REFERENCES projects(project_id);
END
GO

-- Add check constraint: CK__msi_gener__job_s__7CD98669
IF NOT EXISTS (SELECT * FROM sys.check_constraints WHERE name = 'CK__msi_gener__job_s__7CD98669')
BEGIN
    ALTER TABLE msi_generation_jobs
    ADD CONSTRAINT CK__msi_gener__job_s__7CD98669 CHECK ([job_status]='cancelled' OR [job_status]='failed' OR [job_status]='completed' OR [job_status]='running' OR [job_status]='pending');
END
GO

-- Table: msi_version_history
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='msi_version_history' AND xtype='U')
BEGIN
    CREATE TABLE msi_version_history (
        version_id INT IDENTITY(1,1) NOT NULL,
        component_id INT NOT NULL,
        version_number VARCHAR(50) NOT NULL,
        build_number INT,
        product_code UNIQUEIDENTIFIER,
        msi_file_path VARCHAR(500),
        msi_file_size BIGINT,
        msi_file_hash VARCHAR(100),
        build_date DATETIME,
        build_by VARCHAR(100),
        build_machine VARCHAR(100),
        source_branch VARCHAR(100),
        source_commit VARCHAR(100),
        deployed_environments TEXT,
        deployment_notes TEXT,
        status VARCHAR(50),
        release_date DATETIME,
        deprecated_date DATETIME,
        PRIMARY KEY (version_id)
    );
END
GO

-- Add foreign key: FK__msi_versi__compo__41EDCAC5
IF NOT EXISTS (SELECT * FROM sys.foreign_keys WHERE name = 'FK__msi_versi__compo__41EDCAC5')
BEGIN
    ALTER TABLE msi_version_history
    ADD CONSTRAINT FK__msi_versi__compo__41EDCAC5
    FOREIGN KEY (component_id) REFERENCES components(component_id);
END
GO

-- Table: polling_config
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='polling_config' AND xtype='U')
BEGIN
    CREATE TABLE polling_config (
        config_id INT IDENTITY(1,1) NOT NULL,
        component_id INT,
        jfrog_repository VARCHAR(200),
        artifact_path_pattern VARCHAR(500),
        polling_interval_seconds INT DEFAULT ((60)),
        enabled BIT DEFAULT ((1)),
        last_successful_poll DATETIME,
        consecutive_failures INT DEFAULT ((0)),
        max_retries INT DEFAULT ((3)),
        timeout_seconds INT DEFAULT ((300)),
        notification_on_success BIT DEFAULT ((0)),
        notification_on_failure BIT DEFAULT ((1)),
        created_date DATETIME DEFAULT (getdate()),
        updated_date DATETIME DEFAULT (getdate()),
        PRIMARY KEY (config_id)
    );
END
GO

-- Add foreign key: FK__polling_c__compo__25518C17
IF NOT EXISTS (SELECT * FROM sys.foreign_keys WHERE name = 'FK__polling_c__compo__25518C17')
BEGIN
    ALTER TABLE polling_config
    ADD CONSTRAINT FK__polling_c__compo__25518C17
    FOREIGN KEY (component_id) REFERENCES components(component_id) ON DELETE CASCADE;
END
GO

-- Add check constraint: CK_polling_interval
IF NOT EXISTS (SELECT * FROM sys.check_constraints WHERE name = 'CK_polling_interval')
BEGIN
    ALTER TABLE polling_config
    ADD CONSTRAINT CK_polling_interval CHECK ([polling_interval_seconds]>=(30));
END
GO

-- Add check constraint: CK_max_retries
IF NOT EXISTS (SELECT * FROM sys.check_constraints WHERE name = 'CK_max_retries')
BEGIN
    ALTER TABLE polling_config
    ADD CONSTRAINT CK_max_retries CHECK ([max_retries]>=(0));
END
GO

-- Add check constraint: CK_timeout
IF NOT EXISTS (SELECT * FROM sys.check_constraints WHERE name = 'CK_timeout')
BEGIN
    ALTER TABLE polling_config
    ADD CONSTRAINT CK_timeout CHECK ([timeout_seconds]>(0));
END
GO

-- Add unique constraint: UQ__polling___AEB1DA5832F3C42C
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'UQ__polling___AEB1DA5832F3C42C')
BEGIN
    ALTER TABLE polling_config
    ADD CONSTRAINT UQ__polling___AEB1DA5832F3C42C UNIQUE (component_id);
END
GO

-- Table: project_environments
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='project_environments' AND xtype='U')
BEGIN
    CREATE TABLE project_environments (
        env_id INT IDENTITY(1,1) NOT NULL,
        project_id INT NOT NULL,
        environment_name VARCHAR(20) NOT NULL,
        environment_description VARCHAR(100),
        environment_type VARCHAR(20),
        servers TEXT,
        region VARCHAR(50),
        is_active BIT DEFAULT ((1)),
        order_index INT DEFAULT ((1)),
        assigned_server_count INT DEFAULT ((0)),
        load_balancer_server_id INT,
        created_date DATETIME DEFAULT (getdate()),
        PRIMARY KEY (env_id)
    );
END
GO

-- Add foreign key: FK__project_e__proje__0D7A0286
IF NOT EXISTS (SELECT * FROM sys.foreign_keys WHERE name = 'FK__project_e__proje__0D7A0286')
BEGIN
    ALTER TABLE project_environments
    ADD CONSTRAINT FK__project_e__proje__0D7A0286
    FOREIGN KEY (project_id) REFERENCES projects(project_id) ON DELETE CASCADE;
END
GO

-- Add foreign key: FK_env_load_balancer
IF NOT EXISTS (SELECT * FROM sys.foreign_keys WHERE name = 'FK_env_load_balancer')
BEGIN
    ALTER TABLE project_environments
    ADD CONSTRAINT FK_env_load_balancer
    FOREIGN KEY (load_balancer_server_id) REFERENCES cmdb_servers(server_id);
END
GO

-- Add check constraint: CK__project_e__envir__08B54D69
IF NOT EXISTS (SELECT * FROM sys.check_constraints WHERE name = 'CK__project_e__envir__08B54D69')
BEGIN
    ALTER TABLE project_environments
    ADD CONSTRAINT CK__project_e__envir__08B54D69 CHECK ([environment_type]='production' OR [environment_type]='staging' OR [environment_type]='testing' OR [environment_type]='development');
END
GO

-- Add unique constraint: UK_project_env_name
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'UK_project_env_name')
BEGIN
    ALTER TABLE project_environments
    ADD CONSTRAINT UK_project_env_name UNIQUE (environment_name, project_id);
END
GO

-- Table: project_servers
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='project_servers' AND xtype='U')
BEGIN
    CREATE TABLE project_servers (
        assignment_id INT IDENTITY(1,1) NOT NULL,
        project_id INT NOT NULL,
        environment_id INT NOT NULL,
        server_id INT NOT NULL,
        assignment_type VARCHAR(50) NOT NULL,
        purpose TEXT,
        status VARCHAR(20) DEFAULT ('active'),
        assigned_date DATETIME DEFAULT (getdate()),
        assigned_by VARCHAR(100),
        is_active BIT DEFAULT ((1)),
        PRIMARY KEY (assignment_id)
    );
END
GO

-- Add foreign key: FK__project_s__envir__16CE6296
IF NOT EXISTS (SELECT * FROM sys.foreign_keys WHERE name = 'FK__project_s__envir__16CE6296')
BEGIN
    ALTER TABLE project_servers
    ADD CONSTRAINT FK__project_s__envir__16CE6296
    FOREIGN KEY (environment_id) REFERENCES project_environments(env_id);
END
GO

-- Add foreign key: FK__project_s__proje__15DA3E5D
IF NOT EXISTS (SELECT * FROM sys.foreign_keys WHERE name = 'FK__project_s__proje__15DA3E5D')
BEGIN
    ALTER TABLE project_servers
    ADD CONSTRAINT FK__project_s__proje__15DA3E5D
    FOREIGN KEY (project_id) REFERENCES projects(project_id);
END
GO

-- Add foreign key: FK__project_s__serve__17C286CF
IF NOT EXISTS (SELECT * FROM sys.foreign_keys WHERE name = 'FK__project_s__serve__17C286CF')
BEGIN
    ALTER TABLE project_servers
    ADD CONSTRAINT FK__project_s__serve__17C286CF
    FOREIGN KEY (server_id) REFERENCES cmdb_servers(server_id) ON DELETE CASCADE;
END
GO

-- Add check constraint: CK__project_s__assig__11158940
IF NOT EXISTS (SELECT * FROM sys.check_constraints WHERE name = 'CK__project_s__assig__11158940')
BEGIN
    ALTER TABLE project_servers
    ADD CONSTRAINT CK__project_s__assig__11158940 CHECK ([assignment_type]='testing' OR [assignment_type]='development' OR [assignment_type]='load_balancer' OR [assignment_type]='backup' OR [assignment_type]='primary');
END
GO

-- Add check constraint: CK__project_s__statu__12FDD1B2
IF NOT EXISTS (SELECT * FROM sys.check_constraints WHERE name = 'CK__project_s__statu__12FDD1B2')
BEGIN
    ALTER TABLE project_servers
    ADD CONSTRAINT CK__project_s__statu__12FDD1B2 CHECK ([status]='pending' OR [status]='inactive' OR [status]='active');
END
GO

-- Add unique constraint: UQ__project___5A6687064F340307
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'UQ__project___5A6687064F340307')
BEGIN
    ALTER TABLE project_servers
    ADD CONSTRAINT UQ__project___5A6687064F340307 UNIQUE (assignment_type, environment_id, project_id, server_id);
END
GO

-- Table: projects
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='projects' AND xtype='U')
BEGIN
    CREATE TABLE projects (
        project_id INT IDENTITY(1,1) NOT NULL,
        project_guid UNIQUEIDENTIFIER DEFAULT (newid()),
        project_name VARCHAR(100) NOT NULL,
        project_key VARCHAR(20) NOT NULL,
        description TEXT,
        project_type VARCHAR(20) NOT NULL,
        owner_team VARCHAR(100) NOT NULL,
        status VARCHAR(20) DEFAULT ('active'),
        color_primary VARCHAR(7) DEFAULT ('#2c3e50'),
        color_secondary VARCHAR(7) DEFAULT ('#3498db'),
        artifact_source_type VARCHAR(50),
        artifact_url VARCHAR(500),
        artifact_username VARCHAR(100),
        artifact_password VARCHAR(100),
        artifact_api_key VARCHAR(255),
        created_date DATETIME DEFAULT (getdate()),
        created_by VARCHAR(50) NOT NULL,
        updated_date DATETIME DEFAULT (getdate()),
        updated_by VARCHAR(50),
        is_active BIT DEFAULT ((1)),
        auto_version_increment BIT DEFAULT ((1)),
        default_environment VARCHAR(20) DEFAULT ('DEV'),
        notification_email VARCHAR(500),
        default_server_group_id INT,
        preferred_infra_type VARCHAR(50),
        preferred_region VARCHAR(100),
        PRIMARY KEY (project_id)
    );
END
GO

-- Add foreign key: FK_projects_server_group
IF NOT EXISTS (SELECT * FROM sys.foreign_keys WHERE name = 'FK_projects_server_group')
BEGIN
    ALTER TABLE projects
    ADD CONSTRAINT FK_projects_server_group
    FOREIGN KEY (default_server_group_id) REFERENCES cmdb_server_groups(group_id);
END
GO

-- Add check constraint: CK__projects__projec__693CA210
IF NOT EXISTS (SELECT * FROM sys.check_constraints WHERE name = 'CK__projects__projec__693CA210')
BEGIN
    ALTER TABLE projects
    ADD CONSTRAINT CK__projects__projec__693CA210 CHECK ([project_type]='API' OR [project_type]='Desktop' OR [project_type]='Website' OR [project_type]='Service' OR [project_type]='WebApp');
END
GO

-- Add check constraint: CK__projects__status__6B24EA82
IF NOT EXISTS (SELECT * FROM sys.check_constraints WHERE name = 'CK__projects__status__6B24EA82')
BEGIN
    ALTER TABLE projects
    ADD CONSTRAINT CK__projects__status__6B24EA82 CHECK ([status]='archived' OR [status]='maintenance' OR [status]='inactive' OR [status]='active');
END
GO

-- Add check constraint: CK_projects_key_format
IF NOT EXISTS (SELECT * FROM sys.check_constraints WHERE name = 'CK_projects_key_format')
BEGIN
    ALTER TABLE projects
    ADD CONSTRAINT CK_projects_key_format CHECK ([project_key] like '[A-Z]%' AND len([project_key])>=(3));
END
GO

-- Add check constraint: CK_projects_colors
IF NOT EXISTS (SELECT * FROM sys.check_constraints WHERE name = 'CK_projects_colors')
BEGIN
    ALTER TABLE projects
    ADD CONSTRAINT CK_projects_colors CHECK ([color_primary] like '#[0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f][0-9A-Fa-f]');
END
GO

-- Add unique constraint: UQ__projects__30AB21DFFD9B554E
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'UQ__projects__30AB21DFFD9B554E')
BEGIN
    ALTER TABLE projects
    ADD CONSTRAINT UQ__projects__30AB21DFFD9B554E UNIQUE (project_key);
END
GO

-- Table: role_permissions
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='role_permissions' AND xtype='U')
BEGIN
    CREATE TABLE role_permissions (
        role_permission_id INT IDENTITY(1,1) NOT NULL,
        role_name VARCHAR(20) NOT NULL,
        permission_id INT NOT NULL,
        is_granted BIT DEFAULT ((1)),
        created_date DATETIME DEFAULT (getdate()),
        PRIMARY KEY (role_permission_id)
    );
END
GO

-- Add foreign key: FK__role_perm__permi__4A4E069C
IF NOT EXISTS (SELECT * FROM sys.foreign_keys WHERE name = 'FK__role_perm__permi__4A4E069C')
BEGIN
    ALTER TABLE role_permissions
    ADD CONSTRAINT FK__role_perm__permi__4A4E069C
    FOREIGN KEY (permission_id) REFERENCES user_permissions(permission_id);
END
GO

-- Add unique constraint: UQ__role_per__C661651E7293AC61
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'UQ__role_per__C661651E7293AC61')
BEGIN
    ALTER TABLE role_permissions
    ADD CONSTRAINT UQ__role_per__C661651E7293AC61 UNIQUE (permission_id, role_name);
END
GO

-- Table: system_logs
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='system_logs' AND xtype='U')
BEGIN
    CREATE TABLE system_logs (
        log_id INT IDENTITY(1,1) NOT NULL,
        log_level VARCHAR(10) NOT NULL,
        log_category VARCHAR(50) NOT NULL,
        message TEXT NOT NULL,
        username VARCHAR(50),
        ip_address VARCHAR(45),
        user_agent TEXT,
        additional_data TEXT,
        created_date DATETIME DEFAULT (getdate()),
        PRIMARY KEY (log_id)
    );
END
GO

-- Add check constraint: CK__system_lo__log_l__58D1301D
IF NOT EXISTS (SELECT * FROM sys.check_constraints WHERE name = 'CK__system_lo__log_l__58D1301D')
BEGIN
    ALTER TABLE system_logs
    ADD CONSTRAINT CK__system_lo__log_l__58D1301D CHECK ([log_level]='DEBUG' OR [log_level]='ERROR' OR [log_level]='WARNING' OR [log_level]='INFO');
END
GO

-- Table: user_permission_audit
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='user_permission_audit' AND xtype='U')
BEGIN
    CREATE TABLE user_permission_audit (
        audit_id INT IDENTITY(1,1) NOT NULL,
        user_id INT NOT NULL,
        old_role VARCHAR(20),
        new_role VARCHAR(20),
        changed_by VARCHAR(50),
        change_reason VARCHAR(255),
        change_date DATETIME DEFAULT (getdate()),
        PRIMARY KEY (audit_id)
    );
END
GO

-- Add foreign key: FK__user_perm__user___4E1E9780
IF NOT EXISTS (SELECT * FROM sys.foreign_keys WHERE name = 'FK__user_perm__user___4E1E9780')
BEGIN
    ALTER TABLE user_permission_audit
    ADD CONSTRAINT FK__user_perm__user___4E1E9780
    FOREIGN KEY (user_id) REFERENCES users(user_id);
END
GO

-- Table: user_permissions
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='user_permissions' AND xtype='U')
BEGIN
    CREATE TABLE user_permissions (
        permission_id INT IDENTITY(1,1) NOT NULL,
        permission_name VARCHAR(100) NOT NULL,
        permission_description VARCHAR(255),
        module_name VARCHAR(50) NOT NULL,
        action_type VARCHAR(50) NOT NULL,
        is_active BIT DEFAULT ((1)),
        created_date DATETIME DEFAULT (getdate()),
        PRIMARY KEY (permission_id)
    );
END
GO

-- Add unique constraint: UQ__user_per__81C0F5A215394EA6
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'UQ__user_per__81C0F5A215394EA6')
BEGIN
    ALTER TABLE user_permissions
    ADD CONSTRAINT UQ__user_per__81C0F5A215394EA6 UNIQUE (permission_name);
END
GO

-- Table: user_projects
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='user_projects' AND xtype='U')
BEGIN
    CREATE TABLE user_projects (
        user_project_id INT IDENTITY(1,1) NOT NULL,
        user_id INT NOT NULL,
        project_id INT NOT NULL,
        access_level VARCHAR(20) DEFAULT ('read'),
        granted_date DATETIME DEFAULT (getdate()),
        granted_by VARCHAR(50),
        is_active BIT DEFAULT ((1)),
        PRIMARY KEY (user_project_id)
    );
END
GO

-- Add foreign key: FK__user_proj__user___55009F39
IF NOT EXISTS (SELECT * FROM sys.foreign_keys WHERE name = 'FK__user_proj__user___55009F39')
BEGIN
    ALTER TABLE user_projects
    ADD CONSTRAINT FK__user_proj__user___55009F39
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE;
END
GO

-- Add foreign key: FK__user_proj__proje__55F4C372
IF NOT EXISTS (SELECT * FROM sys.foreign_keys WHERE name = 'FK__user_proj__proje__55F4C372')
BEGIN
    ALTER TABLE user_projects
    ADD CONSTRAINT FK__user_proj__proje__55F4C372
    FOREIGN KEY (project_id) REFERENCES projects(project_id) ON DELETE CASCADE;
END
GO

-- Add check constraint: CK__user_proj__acces__5224328E
IF NOT EXISTS (SELECT * FROM sys.check_constraints WHERE name = 'CK__user_proj__acces__5224328E')
BEGIN
    ALTER TABLE user_projects
    ADD CONSTRAINT CK__user_proj__acces__5224328E CHECK ([access_level]='admin' OR [access_level]='write' OR [access_level]='read');
END
GO

-- Add unique constraint: UQ__user_pro__5279AEEFCE3A2319
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'UQ__user_pro__5279AEEFCE3A2319')
BEGIN
    ALTER TABLE user_projects
    ADD CONSTRAINT UQ__user_pro__5279AEEFCE3A2319 UNIQUE (project_id, user_id);
END
GO

-- Table: user_sessions
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='user_sessions' AND xtype='U')
BEGIN
    CREATE TABLE user_sessions (
        session_id VARCHAR(100) NOT NULL,
        user_id INT NOT NULL,
        username VARCHAR(50) NOT NULL,
        login_time DATETIME DEFAULT (getdate()),
        last_activity DATETIME DEFAULT (getdate()),
        ip_address VARCHAR(45),
        user_agent TEXT,
        is_active BIT DEFAULT ((1)),
        PRIMARY KEY (session_id)
    );
END
GO

-- Add foreign key: FK__user_sess__user___5F7E2DAC
IF NOT EXISTS (SELECT * FROM sys.foreign_keys WHERE name = 'FK__user_sess__user___5F7E2DAC')
BEGIN
    ALTER TABLE user_sessions
    ADD CONSTRAINT FK__user_sess__user___5F7E2DAC
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE;
END
GO

-- Table: users
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='users' AND xtype='U')
BEGIN
    CREATE TABLE users (
        user_id INT IDENTITY(1,1) NOT NULL,
        username VARCHAR(50) NOT NULL,
        email VARCHAR(100) NOT NULL,
        domain VARCHAR(20) DEFAULT ('COMPANY'),
        first_name VARCHAR(50) NOT NULL,
        middle_name VARCHAR(50),
        last_name VARCHAR(50) NOT NULL,
        status VARCHAR(20) DEFAULT ('pending'),
        role VARCHAR(20) DEFAULT ('user'),
        created_date DATETIME DEFAULT (getdate()),
        approved_date DATETIME,
        approved_by VARCHAR(50),
        last_login DATETIME,
        login_count INT DEFAULT ((0)),
        is_active BIT DEFAULT ((1)),
        password_hash VARCHAR(255),
        password_salt VARCHAR(255),
        last_password_change DATETIME,
        failed_login_attempts INT DEFAULT ((0)),
        account_locked_until DATETIME,
        PRIMARY KEY (user_id)
    );
END
GO

-- Add check constraint: CK__users__role
IF NOT EXISTS (SELECT * FROM sys.check_constraints WHERE name = 'CK__users__role')
BEGIN
    ALTER TABLE users
    ADD CONSTRAINT CK__users__role CHECK ([role]='poweruser' OR [role]='admin' OR [role]='user');
END
GO

-- Add check constraint: CK__users__status__5CD6CB2B
IF NOT EXISTS (SELECT * FROM sys.check_constraints WHERE name = 'CK__users__status__5CD6CB2B')
BEGIN
    ALTER TABLE users
    ADD CONSTRAINT CK__users__status__5CD6CB2B CHECK ([status]='denied' OR [status]='inactive' OR [status]='approved' OR [status]='pending');
END
GO

-- Add check constraint: CK_users_email_format
IF NOT EXISTS (SELECT * FROM sys.check_constraints WHERE name = 'CK_users_email_format')
BEGIN
    ALTER TABLE users
    ADD CONSTRAINT CK_users_email_format CHECK ([email] like '%@%.%');
END
GO

-- Add check constraint: CK_users_names_not_empty
IF NOT EXISTS (SELECT * FROM sys.check_constraints WHERE name = 'CK_users_names_not_empty')
BEGIN
    ALTER TABLE users
    ADD CONSTRAINT CK_users_names_not_empty CHECK (len(Trim([first_name]))>(0) AND len(Trim([last_name]))>(0));
END
GO

-- Add unique constraint: UQ__users__AB6E616475B01130
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'UQ__users__AB6E616475B01130')
BEGIN
    ALTER TABLE users
    ADD CONSTRAINT UQ__users__AB6E616475B01130 UNIQUE (email);
END
GO

-- Add unique constraint: UQ__users__F3DBC572094D4415
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'UQ__users__F3DBC572094D4415')
BEGIN
    ALTER TABLE users
    ADD CONSTRAINT UQ__users__F3DBC572094D4415 UNIQUE (username);
END
GO


-- ============================================================
-- INDEXES
-- ============================================================

-- Index: idx_artifact_history_component
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_artifact_history_component')
BEGIN
    CREATE INDEX idx_artifact_history_component
    ON artifact_history (component_id);
END
GO

-- Index: idx_artifact_history_time
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_artifact_history_time')
BEGIN
    CREATE INDEX idx_artifact_history_time
    ON artifact_history (download_time);
END
GO

-- Index: idx_cmdb_changes_date
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_cmdb_changes_date')
BEGIN
    CREATE INDEX idx_cmdb_changes_date
    ON cmdb_server_changes (changed_date);
END
GO

-- Index: idx_cmdb_changes_server
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_cmdb_changes_server')
BEGIN
    CREATE INDEX idx_cmdb_changes_server
    ON cmdb_server_changes (server_id);
END
GO

-- Index: UQ__cmdb_ser__4BA22064FF02595A
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'UQ__cmdb_ser__4BA22064FF02595A')
BEGIN
    CREATE UNIQUE INDEX UQ__cmdb_ser__4BA22064FF02595A
    ON cmdb_server_group_members (group_id, server_id);
END
GO

-- Index: UQ__cmdb_ser__E8F4F58D2650FC60
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'UQ__cmdb_ser__E8F4F58D2650FC60')
BEGIN
    CREATE UNIQUE INDEX UQ__cmdb_ser__E8F4F58D2650FC60
    ON cmdb_server_groups (group_name);
END
GO

-- Index: idx_cmdb_servers_infra_type
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_cmdb_servers_infra_type')
BEGIN
    CREATE INDEX idx_cmdb_servers_infra_type
    ON cmdb_servers (infra_type);
END
GO

-- Index: idx_cmdb_servers_region
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_cmdb_servers_region')
BEGIN
    CREATE INDEX idx_cmdb_servers_region
    ON cmdb_servers (region);
END
GO

-- Index: idx_cmdb_servers_status
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_cmdb_servers_status')
BEGIN
    CREATE INDEX idx_cmdb_servers_status
    ON cmdb_servers (status);
END
GO

-- Index: UQ__cmdb_ser__37F8F950F013C55A
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'UQ__cmdb_ser__37F8F950F013C55A')
BEGIN
    CREATE UNIQUE INDEX UQ__cmdb_ser__37F8F950F013C55A
    ON cmdb_servers (server_name);
END
GO

-- Index: idx_component_branches_active
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_component_branches_active')
BEGIN
    CREATE INDEX idx_component_branches_active
    ON component_branches (is_active);
END
GO

-- Index: idx_component_branches_component
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_component_branches_component')
BEGIN
    CREATE INDEX idx_component_branches_component
    ON component_branches (component_id);
END
GO

-- Index: idx_component_branches_composite
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_component_branches_composite')
BEGIN
    CREATE INDEX idx_component_branches_composite
    ON component_branches (component_id, is_active, branch_status);
END
GO

-- Index: idx_component_branches_name
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_component_branches_name')
BEGIN
    CREATE INDEX idx_component_branches_name
    ON component_branches (branch_name);
END
GO

-- Index: idx_component_branches_status
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_component_branches_status')
BEGIN
    CREATE INDEX idx_component_branches_status
    ON component_branches (branch_status);
END
GO

-- Index: IX_component_branches_branch_name
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_component_branches_branch_name')
BEGIN
    CREATE INDEX IX_component_branches_branch_name
    ON component_branches (branch_name);
END
GO

-- Index: IX_component_branches_component_id
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_component_branches_component_id')
BEGIN
    CREATE INDEX IX_component_branches_component_id
    ON component_branches (component_id);
END
GO

-- Index: UQ__componen__62467DBE8CF9CA84
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'UQ__componen__62467DBE8CF9CA84')
BEGIN
    CREATE UNIQUE INDEX UQ__componen__62467DBE8CF9CA84
    ON component_branches (component_id, branch_name);
END
GO

-- Index: IX_component_build_artifacts_build_id
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_component_build_artifacts_build_id')
BEGIN
    CREATE INDEX IX_component_build_artifacts_build_id
    ON component_build_artifacts (build_id);
END
GO

-- Index: IX_component_builds_branch_id
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_component_builds_branch_id')
BEGIN
    CREATE INDEX IX_component_builds_branch_id
    ON component_builds (branch_id);
END
GO

-- Index: IX_component_builds_build_date
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_component_builds_build_date')
BEGIN
    CREATE INDEX IX_component_builds_build_date
    ON component_builds (build_date);
END
GO

-- Index: IX_component_builds_status
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_component_builds_status')
BEGIN
    CREATE INDEX IX_component_builds_status
    ON component_builds (build_status);
END
GO

-- Index: UQ__componen__19B56E55EBACEE40
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'UQ__componen__19B56E55EBACEE40')
BEGIN
    CREATE UNIQUE INDEX UQ__componen__19B56E55EBACEE40
    ON component_builds (branch_id, build_number);
END
GO

-- Index: UQ__componen__EB0B8EBFA2EDDCC4
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'UQ__componen__EB0B8EBFA2EDDCC4')
BEGIN
    CREATE UNIQUE INDEX UQ__componen__EB0B8EBFA2EDDCC4
    ON component_servers (component_id, server_id, assignment_type);
END
GO

-- Index: idx_components_branch
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_components_branch')
BEGIN
    CREATE INDEX idx_components_branch
    ON components (branch_name);
END
GO

-- Index: idx_components_project
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_components_project')
BEGIN
    CREATE INDEX idx_components_project
    ON components (project_id);
END
GO

-- Index: UK_components_project_name
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'UK_components_project_name')
BEGIN
    CREATE UNIQUE INDEX UK_components_project_name
    ON components (project_id, component_name);
END
GO

-- Index: IX_global_credentials_active
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_global_credentials_active')
BEGIN
    CREATE INDEX IX_global_credentials_active
    ON global_credentials (is_active);
END
GO

-- Index: IX_global_credentials_default
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_global_credentials_default')
BEGIN
    CREATE INDEX IX_global_credentials_default
    ON global_credentials (credential_type, is_default);
END
GO

-- Index: IX_global_credentials_type
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'IX_global_credentials_type')
BEGIN
    CREATE INDEX IX_global_credentials_type
    ON global_credentials (credential_type);
END
GO

-- Index: UQ__global_c__AE195F616C6B2E9F
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'UQ__global_c__AE195F616C6B2E9F')
BEGIN
    CREATE UNIQUE INDEX UQ__global_c__AE195F616C6B2E9F
    ON global_credentials (credential_name);
END
GO

-- Index: idx_integrations_enabled
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_integrations_enabled')
BEGIN
    CREATE INDEX idx_integrations_enabled
    ON integrations_config (is_enabled);
END
GO

-- Index: idx_integrations_type
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_integrations_type')
BEGIN
    CREATE INDEX idx_integrations_type
    ON integrations_config (integration_type);
END
GO

-- Index: idx_integrations_type_enabled
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_integrations_type_enabled')
BEGIN
    CREATE INDEX idx_integrations_type_enabled
    ON integrations_config (integration_type, is_enabled);
END
GO

-- Index: UK_integrations_type_name
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'UK_integrations_type_name')
BEGIN
    CREATE UNIQUE INDEX UK_integrations_type_name
    ON integrations_config (integration_type, integration_name);
END
GO

-- Index: idx_build_queue_status
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_build_queue_status')
BEGIN
    CREATE INDEX idx_build_queue_status
    ON msi_build_queue (status);
END
GO

-- Index: idx_build_queue_time
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_build_queue_time')
BEGIN
    CREATE INDEX idx_build_queue_time
    ON msi_build_queue (queued_time);
END
GO

-- Index: idx_msi_config_component
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_msi_config_component')
BEGIN
    CREATE INDEX idx_msi_config_component
    ON msi_configurations (component_id);
END
GO

-- Index: idx_msi_config_env
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_msi_config_env')
BEGIN
    CREATE INDEX idx_msi_config_env
    ON msi_configurations (target_environment);
END
GO

-- Index: UQ__msi_conf__AEB1DA58F63A7A7A
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'UQ__msi_conf__AEB1DA58F63A7A7A')
BEGIN
    CREATE UNIQUE INDEX UQ__msi_conf__AEB1DA58F63A7A7A
    ON msi_configurations (component_id);
END
GO

-- Index: UQ__msi_envi__2DA6B9866E65D9CE
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'UQ__msi_envi__2DA6B9866E65D9CE')
BEGIN
    CREATE UNIQUE INDEX UQ__msi_envi__2DA6B9866E65D9CE
    ON msi_environment_configs (config_id, environment);
END
GO

-- Index: idx_version_history
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_version_history')
BEGIN
    CREATE INDEX idx_version_history
    ON msi_version_history (component_id, version_number);
END
GO

-- Index: UQ__polling___AEB1DA5832F3C42C
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'UQ__polling___AEB1DA5832F3C42C')
BEGIN
    CREATE UNIQUE INDEX UQ__polling___AEB1DA5832F3C42C
    ON polling_config (component_id);
END
GO

-- Index: UK_project_env_name
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'UK_project_env_name')
BEGIN
    CREATE UNIQUE INDEX UK_project_env_name
    ON project_environments (project_id, environment_name);
END
GO

-- Index: idx_project_servers_project
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_project_servers_project')
BEGIN
    CREATE INDEX idx_project_servers_project
    ON project_servers (project_id);
END
GO

-- Index: idx_project_servers_server
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_project_servers_server')
BEGIN
    CREATE INDEX idx_project_servers_server
    ON project_servers (server_id);
END
GO

-- Index: UQ__project___5A6687064F340307
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'UQ__project___5A6687064F340307')
BEGIN
    CREATE UNIQUE INDEX UQ__project___5A6687064F340307
    ON project_servers (project_id, environment_id, server_id, assignment_type);
END
GO

-- Index: idx_projects_key
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_projects_key')
BEGIN
    CREATE INDEX idx_projects_key
    ON projects (project_key);
END
GO

-- Index: UQ__projects__30AB21DFFD9B554E
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'UQ__projects__30AB21DFFD9B554E')
BEGIN
    CREATE UNIQUE INDEX UQ__projects__30AB21DFFD9B554E
    ON projects (project_key);
END
GO

-- Index: UQ__role_per__C661651E7293AC61
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'UQ__role_per__C661651E7293AC61')
BEGIN
    CREATE UNIQUE INDEX UQ__role_per__C661651E7293AC61
    ON role_permissions (role_name, permission_id);
END
GO

-- Index: idx_system_logs_date
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_system_logs_date')
BEGIN
    CREATE INDEX idx_system_logs_date
    ON system_logs (created_date);
END
GO

-- Index: UQ__user_per__81C0F5A215394EA6
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'UQ__user_per__81C0F5A215394EA6')
BEGIN
    CREATE UNIQUE INDEX UQ__user_per__81C0F5A215394EA6
    ON user_permissions (permission_name);
END
GO

-- Index: UQ__user_pro__5279AEEFCE3A2319
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'UQ__user_pro__5279AEEFCE3A2319')
BEGIN
    CREATE UNIQUE INDEX UQ__user_pro__5279AEEFCE3A2319
    ON user_projects (user_id, project_id);
END
GO

-- Index: idx_user_sessions_user
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_user_sessions_user')
BEGIN
    CREATE INDEX idx_user_sessions_user
    ON user_sessions (user_id);
END
GO

-- Index: idx_users_email
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_users_email')
BEGIN
    CREATE INDEX idx_users_email
    ON users (email);
END
GO

-- Index: idx_users_username
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'idx_users_username')
BEGIN
    CREATE INDEX idx_users_username
    ON users (username);
END
GO

-- Index: UQ__users__AB6E616475B01130
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'UQ__users__AB6E616475B01130')
BEGIN
    CREATE UNIQUE INDEX UQ__users__AB6E616475B01130
    ON users (email);
END
GO

-- Index: UQ__users__F3DBC572094D4415
IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'UQ__users__F3DBC572094D4415')
BEGIN
    CREATE UNIQUE INDEX UQ__users__F3DBC572094D4415
    ON users (username);
END
GO


-- ============================================================
-- VIEWS
-- ============================================================

-- View: v_user_permissions
IF EXISTS (SELECT * FROM sys.views WHERE name = 'v_user_permissions')
    DROP VIEW v_user_permissions;
GO

CREATE   VIEW v_user_permissions AS
SELECT
    u.user_id,
    u.username,
    u.role,
    up.permission_name,
    up.module_name,
    up.action_type,
    up.permission_description
FROM users u
JOIN role_permissions rp ON u.role = rp.role_name
JOIN user_permissions up ON rp.permission_id = up.permission_id
WHERE u.is_active = 1 AND rp.is_granted = 1 AND up.is_active = 1;


GO

-- View: vw_cmdb_server_inventory
IF EXISTS (SELECT * FROM sys.views WHERE name = 'vw_cmdb_server_inventory')
    DROP VIEW vw_cmdb_server_inventory;
GO


    CREATE VIEW vw_cmdb_server_inventory
    AS
    SELECT
        s.server_id,
        s.server_name,
        s.fqdn,
        s.infra_type,
        s.ip_address,
        s.ip_address_internal,
        s.region,
        s.datacenter,
        s.environment_type,
        s.status,
        s.cpu_cores,
        s.memory_gb,
        s.storage_gb,
        s.current_app_count,
        s.max_concurrent_apps,
        CASE
            WHEN s.max_concurrent_apps > 0 THEN (s.current_app_count * 100.0 / s.max_concurrent_apps)
            ELSE 0
        END as utilization_percentage,
        s.owner_team,
        s.technical_contact,
        s.created_date,
        s.last_updated,
        STRING_AGG(sg.group_name, ', ') as server_groups,
        (SELECT COUNT(*) FROM project_servers ps WHERE ps.server_id = s.server_id AND ps.status = 'active') as active_assignments
    FROM cmdb_servers s
    LEFT JOIN cmdb_server_group_members sgm ON s.server_id = sgm.server_id AND sgm.is_active = 1
    LEFT JOIN cmdb_server_groups sg ON sgm.group_id = sg.group_id AND sg.is_active = 1
    WHERE s.is_active = 1
    GROUP BY
        s.server_id, s.server_name, s.fqdn, s.infra_type, s.ip_address, s.ip_address_internal,
        s.region, s.datacenter, s.environment_type, s.status, s.cpu_cores, s.memory_gb,
        s.storage_gb, s.current_app_count, s.max_concurrent_apps, s.owner_team,
        s.technical_contact, s.created_date, s.last_updated
    
GO

-- View: vw_component_details
IF EXISTS (SELECT * FROM sys.views WHERE name = 'vw_component_details')
    DROP VIEW vw_component_details;
GO


    CREATE VIEW vw_component_details
    AS
    SELECT
        c.component_id,
        c.component_guid,
        c.component_name,
        c.component_type,
        c.framework,
        c.description,

        -- MSI Package Information
        c.app_name,
        c.app_version,
        c.manufacturer,

        -- Deployment Configuration
        c.target_server,
        c.install_folder,

        -- IIS Configuration
        c.iis_website_name,
        c.iis_app_pool_name,
        c.port,

        -- Windows Service Configuration
        c.service_name,
        c.service_display_name,

        -- Artifact Configuration
        c.artifact_url,

        -- Project Information
        p.project_id,
        p.project_name,
        p.project_key,
        p.project_type,
        p.owner_team,
        p.status as project_status,

        -- Legacy MSI Configuration (for backward compatibility)
        mc.config_id,
        mc.unique_id as msi_unique_id,
        mc.target_environment,

        -- Metadata
        c.created_date,
        c.created_by,
        c.updated_date,
        c.updated_by
    FROM components c
    INNER JOIN projects p ON c.project_id = p.project_id
    LEFT JOIN msi_configurations mc ON c.component_id = mc.component_id
    WHERE p.is_active = 1
    
GO

-- View: vw_project_server_assignments
IF EXISTS (SELECT * FROM sys.views WHERE name = 'vw_project_server_assignments')
    DROP VIEW vw_project_server_assignments;
GO


    CREATE VIEW vw_project_server_assignments
    AS
    SELECT
        ps.assignment_id,
        p.project_name,
        p.project_key,
        pe.environment_name,
        pe.environment_description,
        s.server_name,
        s.ip_address,
        s.infra_type,
        s.region,
        ps.assignment_type,
        ps.purpose,
        ps.status,
        ps.assigned_date,
        ps.assigned_by
    FROM project_servers ps
    INNER JOIN projects p ON ps.project_id = p.project_id
    INNER JOIN project_environments pe ON ps.environment_id = pe.env_id
    INNER JOIN cmdb_servers s ON ps.server_id = s.server_id
    WHERE p.is_active = 1 AND s.is_active = 1
    
GO


-- ============================================================
-- STORED PROCEDURES
-- ============================================================

-- Procedure: GetCredentialsByType
IF EXISTS (SELECT * FROM sys.objects WHERE type = 'P' AND name = 'GetCredentialsByType')
    DROP PROCEDURE GetCredentialsByType;
GO


CREATE PROCEDURE GetCredentialsByType
    @CredentialType VARCHAR(50),
    @IncludeInactive BIT = 0
AS
BEGIN
    SELECT
        credential_id,
        credential_name,
        credential_type,
        service_url,
        username,
        domain,
        additional_config,
        is_active,
        is_default,
        description,
        created_date,
        last_used_date
    FROM global_credentials
    WHERE credential_type = @CredentialType
    AND (is_active = 1 OR @IncludeInactive = 1)
    ORDER BY is_default DESC, credential_name;
END;

GO

-- Procedure: GetDefaultCredentials
IF EXISTS (SELECT * FROM sys.objects WHERE type = 'P' AND name = 'GetDefaultCredentials')
    DROP PROCEDURE GetDefaultCredentials;
GO


CREATE PROCEDURE GetDefaultCredentials
    @CredentialType VARCHAR(50)
AS
BEGIN
    SELECT TOP 1
        credential_id,
        credential_name,
        credential_type,
        service_url,
        username,
        password,
        domain,
        additional_config
    FROM global_credentials
    WHERE credential_type = @CredentialType
    AND is_active = 1
    ORDER BY is_default DESC, credential_id;
END;

GO

-- Procedure: LogCredentialUsage
IF EXISTS (SELECT * FROM sys.objects WHERE type = 'P' AND name = 'LogCredentialUsage')
    DROP PROCEDURE LogCredentialUsage;
GO


CREATE PROCEDURE LogCredentialUsage
    @CredentialId INT,
    @ComponentId INT = NULL,
    @OperationType VARCHAR(50),
    @OperationResult VARCHAR(20),
    @OperationDetails TEXT = NULL,
    @ErrorMessage TEXT = NULL,
    @UsedBy VARCHAR(100)
AS
BEGIN
    INSERT INTO credential_usage_log (
        credential_id, component_id, operation_type, operation_result,
        operation_details, error_message, used_by
    ) VALUES (
        @CredentialId, @ComponentId, @OperationType, @OperationResult,
        @OperationDetails, @ErrorMessage, @UsedBy
    );

    -- Update last used date on credentials
    UPDATE global_credentials
    SET last_used_date = GETDATE()
    WHERE credential_id = @CredentialId;
END;

GO

-- Procedure: sp_ArchiveOldBranches
IF EXISTS (SELECT * FROM sys.objects WHERE type = 'P' AND name = 'sp_ArchiveOldBranches')
    DROP PROCEDURE sp_ArchiveOldBranches;
GO


CREATE PROCEDURE sp_ArchiveOldBranches
    @days_old INT = 90,
    @archived_by VARCHAR(50) = 'system'
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @archived_count INT = 0;

    -- Archive branches that haven't been updated in specified days
    UPDATE component_branches
    SET branch_status = 'archived',
        updated_by = @archived_by,
        updated_date = GETDATE()
    WHERE updated_date < DATEADD(DAY, -@days_old, GETDATE())
    AND branch_status = 'inactive'
    AND is_active = 1;

    SET @archived_count = @@ROWCOUNT;

    SELECT @archived_count as archived_branches_count;
END

GO

-- Procedure: sp_AssignServerToProject
IF EXISTS (SELECT * FROM sys.objects WHERE type = 'P' AND name = 'sp_AssignServerToProject')
    DROP PROCEDURE sp_AssignServerToProject;
GO


CREATE PROCEDURE sp_AssignServerToProject
    @project_id INT,
    @environment_id INT,
    @server_id INT,
    @assignment_type VARCHAR(50),
    @assigned_by VARCHAR(100)
AS
BEGIN
    SET NOCOUNT ON;

    BEGIN TRY
        IF NOT EXISTS (SELECT 1 FROM project_servers
                      WHERE project_id = @project_id
                        AND environment_id = @environment_id
                        AND server_id = @server_id
                        AND assignment_type = @assignment_type)
        BEGIN
            INSERT INTO project_servers (project_id, environment_id, server_id, assignment_type, assigned_by)
            VALUES (@project_id, @environment_id, @server_id, @assignment_type, @assigned_by);

            INSERT INTO cmdb_server_changes (server_id, change_type, change_reason, changed_by)
            VALUES (@server_id, 'assignment_change',
                   'Assigned to project ' + CAST(@project_id AS VARCHAR), @assigned_by);

            SELECT 1 as success, 'Server assigned successfully' as message;
        END
        ELSE
        BEGIN
            SELECT 0 as success, 'Assignment already exists' as message;
        END
    END TRY
    BEGIN CATCH
        SELECT 0 as success, ERROR_MESSAGE() as message;
    END CATCH
END

GO

-- Procedure: sp_CMDB_DiscoverServer
IF EXISTS (SELECT * FROM sys.objects WHERE type = 'P' AND name = 'sp_CMDB_DiscoverServer')
    DROP PROCEDURE sp_CMDB_DiscoverServer;
GO


CREATE PROCEDURE sp_CMDB_DiscoverServer
    @server_name VARCHAR(255),
    @ip_address VARCHAR(45),
    @infra_type VARCHAR(50),
    @discovered_by VARCHAR(100)
AS
BEGIN
    SET NOCOUNT ON;

    IF NOT EXISTS (SELECT 1 FROM cmdb_servers WHERE server_name = @server_name OR ip_address = @ip_address)
    BEGIN
        INSERT INTO cmdb_servers (server_name, ip_address, infra_type, status, created_by)
        VALUES (@server_name, @ip_address, @infra_type, 'active', @discovered_by);

        DECLARE @server_id INT = SCOPE_IDENTITY();

        INSERT INTO cmdb_server_changes (server_id, change_type, change_reason, changed_by)
        VALUES (@server_id, 'created', 'Server discovered automatically', @discovered_by);

        SELECT @server_id as server_id, 'Server discovered and added' as message;
    END
    ELSE
    BEGIN
        SELECT 0 as server_id, 'Server already exists' as message;
    END
END

GO

-- Procedure: sp_GetBranchStatistics
IF EXISTS (SELECT * FROM sys.objects WHERE type = 'P' AND name = 'sp_GetBranchStatistics')
    DROP PROCEDURE sp_GetBranchStatistics;
GO


CREATE PROCEDURE sp_GetBranchStatistics
AS
BEGIN
    SET NOCOUNT ON;

    SELECT
        'Total Branches' as statistic,
        COUNT(*) as count
    FROM component_branches
    WHERE is_active = 1

    UNION ALL

    SELECT
        'Active Branches',
        COUNT(*)
    FROM component_branches
    WHERE is_active = 1 AND branch_status = 'active'

    UNION ALL

    SELECT
        'Inactive Branches',
        COUNT(*)
    FROM component_branches
    WHERE is_active = 1 AND branch_status = 'inactive'

    UNION ALL

    SELECT
        'Archived Branches',
        COUNT(*)
    FROM component_branches
    WHERE is_active = 1 AND branch_status = 'archived'

    UNION ALL

    SELECT
        'Components with Branches',
        COUNT(DISTINCT component_id)
    FROM component_branches
    WHERE is_active = 1;
END

GO

-- Procedure: sp_GetIntegrationConfig
IF EXISTS (SELECT * FROM sys.objects WHERE type = 'P' AND name = 'sp_GetIntegrationConfig')
    DROP PROCEDURE sp_GetIntegrationConfig;
GO


CREATE PROCEDURE sp_GetIntegrationConfig
    @integration_type VARCHAR(50),
    @integration_name VARCHAR(100) = NULL
AS
BEGIN
    SET NOCOUNT ON;

    IF @integration_name IS NULL
    BEGIN
        -- Get all configurations for the integration type
        SELECT
            config_id, integration_type, integration_name, base_url,
            username, auth_type, is_enabled, is_validated,
            last_test_date, last_test_result, last_test_message,
            timeout_seconds, retry_count, ssl_verify,
            created_date, updated_date, last_used_date, usage_count
        FROM integrations_config
        WHERE integration_type = @integration_type
        ORDER BY integration_name;
    END
    ELSE
    BEGIN
        -- Get specific configuration
        SELECT
            config_id, integration_type, integration_name, base_url,
            username, password, token, api_key, auth_type,
            additional_config, is_enabled, is_validated,
            last_test_date, last_test_result, last_test_message,
            timeout_seconds, retry_count, ssl_verify,
            created_date, updated_date, last_used_date, usage_count
        FROM integrations_config
        WHERE integration_type = @integration_type
        AND integration_name = @integration_name;
    END
END

GO

-- Procedure: sp_GetNextBranchVersion
IF EXISTS (SELECT * FROM sys.objects WHERE type = 'P' AND name = 'sp_GetNextBranchVersion')
    DROP PROCEDURE sp_GetNextBranchVersion;
GO


CREATE PROCEDURE sp_GetNextBranchVersion
    @branch_id INT,
    @auto_increment_type VARCHAR(20),
    @next_version VARCHAR(50) OUTPUT
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @major INT, @minor INT, @patch INT, @build INT;

    -- Get current version
    SELECT
        @major = major_version,
        @minor = minor_version,
        @patch = patch_version,
        @build = build_number
    FROM component_branches
    WHERE branch_id = @branch_id;

    -- Increment based on type
    IF @auto_increment_type = 'major'
    BEGIN
        SET @major = @major + 1;
        SET @minor = 0;
        SET @patch = 0;
        SET @build = 0;
    END
    ELSE IF @auto_increment_type = 'minor'
    BEGIN
        SET @minor = @minor + 1;
        SET @patch = 0;
        SET @build = 0;
    END
    ELSE IF @auto_increment_type = 'build'
    BEGIN
        SET @patch = @patch + 1;
        SET @build = 0;
    END
    ELSE IF @auto_increment_type = 'revision'
    BEGIN
        SET @build = @build + 1;
    END

    -- Update the branch with new version
    UPDATE component_branches
    SET major_version = @major,
        minor_version = @minor,
        patch_version = @patch,
        build_number = @build,
        updated_date = GETDATE()
    WHERE branch_id = @branch_id;

    -- Return formatted version
    SET @next_version = CAST(@major AS VARCHAR) + '.' +
                       CAST(@minor AS VARCHAR) + '.' +
                       CAST(@patch AS VARCHAR) + '.' +
                       CAST(@build AS VARCHAR);
END

GO

-- Procedure: sp_GetNextVersion
IF EXISTS (SELECT * FROM sys.objects WHERE type = 'P' AND name = 'sp_GetNextVersion')
    DROP PROCEDURE sp_GetNextVersion;
GO


CREATE PROCEDURE sp_GetNextVersion
    @component_id INT,
    @next_version VARCHAR(50) OUTPUT
AS
BEGIN
    DECLARE @current_version VARCHAR(50);

    SELECT TOP 1 @current_version = version_number
    FROM msi_version_history
    WHERE component_id = @component_id
    ORDER BY version_id DESC;

    IF @current_version IS NULL
        SET @next_version = '1.0.0.0';
    ELSE
    BEGIN
        DECLARE @major INT, @minor INT, @build INT, @revision INT;

        SET @major = PARSENAME(@current_version, 4);
        SET @minor = PARSENAME(@current_version, 3);
        SET @build = PARSENAME(@current_version, 2);
        SET @revision = PARSENAME(@current_version, 1) + 1;

        IF @revision > 9999
        BEGIN
            SET @revision = 0;
            SET @build = @build + 1;
        END

        SET @next_version = CAST(@major AS VARCHAR) + '.' +
                           CAST(@minor AS VARCHAR) + '.' +
                           CAST(@build AS VARCHAR) + '.' +
                           CAST(@revision AS VARCHAR);
    END
END

GO

-- Procedure: sp_HealthCheck
IF EXISTS (SELECT * FROM sys.objects WHERE type = 'P' AND name = 'sp_HealthCheck')
    DROP PROCEDURE sp_HealthCheck;
GO


CREATE PROCEDURE sp_HealthCheck
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @results TABLE (
        check_name VARCHAR(100),
        status VARCHAR(20),
        details VARCHAR(500)
    );

    -- Check table counts
    INSERT INTO @results SELECT 'Users Count', 'OK', CAST(COUNT(*) AS VARCHAR) + ' users' FROM users;
    INSERT INTO @results SELECT 'Projects Count', 'OK', CAST(COUNT(*) AS VARCHAR) + ' projects' FROM projects;
    INSERT INTO @results SELECT 'Components Count', 'OK', CAST(COUNT(*) AS VARCHAR) + ' components' FROM components;
    INSERT INTO @results SELECT 'CMDB Servers Count', 'OK', CAST(COUNT(*) AS VARCHAR) + ' servers' FROM cmdb_servers;

    -- Check for orphaned records
    IF EXISTS (SELECT 1 FROM components c LEFT JOIN projects p ON c.project_id = p.project_id WHERE p.project_id IS NULL)
        INSERT INTO @results VALUES ('Orphaned Components', 'WARNING', 'Found components without valid projects');
    ELSE
        INSERT INTO @results VALUES ('Orphaned Components', 'OK', 'No orphaned components found');

    -- Check database size
    DECLARE @db_size VARCHAR(20);
    SELECT @db_size = CAST(SUM(size * 8.0 / 1024) AS VARCHAR(20)) + ' MB'
    FROM sys.master_files
    WHERE database_id = DB_ID();

    INSERT INTO @results VALUES ('Database Size', 'OK', @db_size);

    SELECT * FROM @results ORDER BY check_name;
END

GO

-- Procedure: sp_UpdateIntegrationUsage
IF EXISTS (SELECT * FROM sys.objects WHERE type = 'P' AND name = 'sp_UpdateIntegrationUsage')
    DROP PROCEDURE sp_UpdateIntegrationUsage;
GO


CREATE PROCEDURE sp_UpdateIntegrationUsage
    @config_id INT
AS
BEGIN
    SET NOCOUNT ON;

    UPDATE integrations_config
    SET last_used_date = GETDATE(),
        usage_count = usage_count + 1
    WHERE config_id = @config_id;
END

GO


-- ============================================================
-- FUNCTIONS
-- ============================================================

-- Function: CheckUserPermission
IF EXISTS (SELECT * FROM sys.objects WHERE type = 'FN' AND name = 'CheckUserPermission')
    DROP FUNCTION CheckUserPermission;
GO

-- Step 9: Create function to check user permissions
CREATE   FUNCTION dbo.CheckUserPermission(
    @username VARCHAR(50),
    @permission_name VARCHAR(100)
)
RETURNS BIT
AS
BEGIN
    DECLARE @hasPermission BIT = 0;

    SELECT @hasPermission = 1
    FROM v_user_permissions
    WHERE username = @username AND permission_name = @permission_name;

    RETURN ISNULL(@hasPermission, 0);
END;


GO


-- ============================================================
-- SCHEMA EXTRACTION COMPLETE
-- ============================================================
SET NOCOUNT OFF;
