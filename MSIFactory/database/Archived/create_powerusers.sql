-- Create PowerUsers (Technical Project Managers) for MSI Factory
-- This script creates sample PowerUsers for testing the authorization system

-- PowerUser 1: Technical Project Manager
IF NOT EXISTS (SELECT 1 FROM users WHERE username = 'tech.pm')
BEGIN
    INSERT INTO users (username, email, first_name, last_name, role, status, is_active)
    VALUES ('tech.pm', 'tech.pm@msifactory.com', 'Technical', 'Project Manager', 'poweruser', 'approved', 1);
    PRINT 'PowerUser "tech.pm" created successfully';
END
ELSE
BEGIN
    PRINT 'PowerUser "tech.pm" already exists';
END

-- PowerUser 2: Development Lead
IF NOT EXISTS (SELECT 1 FROM users WHERE username = 'dev.lead')
BEGIN
    INSERT INTO users (username, email, first_name, last_name, role, status, is_active)
    VALUES ('dev.lead', 'dev.lead@msifactory.com', 'Development', 'Lead', 'poweruser', 'approved', 1);
    PRINT 'PowerUser "dev.lead" created successfully';
END
ELSE
BEGIN
    PRINT 'PowerUser "dev.lead" already exists';
END

-- PowerUser 3: Component Manager
IF NOT EXISTS (SELECT 1 FROM users WHERE username = 'comp.manager')
BEGIN
    INSERT INTO users (username, email, first_name, last_name, role, status, is_active)
    VALUES ('comp.manager', 'comp.manager@msifactory.com', 'Component', 'Manager', 'poweruser', 'approved', 1);
    PRINT 'PowerUser "comp.manager" created successfully';
END
ELSE
BEGIN
    PRINT 'PowerUser "comp.manager" already exists';
END

-- Verification: Show all PowerUsers created
SELECT
    username,
    email,
    first_name + ' ' + last_name AS full_name,
    role,
    status,
    is_active,
    created_date
FROM users
WHERE role = 'poweruser'
ORDER BY created_date;

PRINT '';
PRINT 'PowerUser creation completed. These users can now:';
PRINT '- Create, Read, Update, Delete Components';
PRINT '- Enable/Disable Components';
PRINT '- Update Projects';
PRINT '- Generate MSI packages';
PRINT '- Update CMDB entries';
PRINT '';
PRINT 'PowerUsers CANNOT:';
PRINT '- Manage users or roles';
PRINT '- Create/Delete projects';
PRINT '- Access system settings';