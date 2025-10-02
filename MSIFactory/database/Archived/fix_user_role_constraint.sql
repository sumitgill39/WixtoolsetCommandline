-- Quick Fix: Update users table constraint to allow PowerUser role
-- Run this script first before creating PowerUsers

PRINT 'Updating users table constraint to allow PowerUser role...';

-- Drop the existing constraint (using the exact constraint name from error)
ALTER TABLE users DROP CONSTRAINT IF EXISTS CK__users__role__5EBF139D;

-- Also try the generic constraint name in case it's different
ALTER TABLE users DROP CONSTRAINT IF EXISTS CK__users__role;

-- Create new constraint that includes poweruser
ALTER TABLE users ADD CONSTRAINT CK__users__role
CHECK (role IN ('user', 'admin', 'poweruser'));

PRINT 'Constraint updated successfully!';

-- Verify the constraint is working
PRINT 'Testing constraint by checking allowed values...';

-- Show current constraint definition
SELECT
    tc.CONSTRAINT_NAME,
    cc.CHECK_CLAUSE
FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc
JOIN INFORMATION_SCHEMA.CHECK_CONSTRAINTS cc
    ON tc.CONSTRAINT_NAME = cc.CONSTRAINT_NAME
WHERE tc.TABLE_NAME = 'users'
    AND tc.CONSTRAINT_TYPE = 'CHECK'
    AND cc.CHECK_CLAUSE LIKE '%role%';

PRINT 'Constraint fix completed. You can now create PowerUsers.';