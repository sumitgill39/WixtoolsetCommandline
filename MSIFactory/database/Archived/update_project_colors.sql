-- ============================================================
-- Update Project Colors Script
-- Purpose: Populate color_primary and color_secondary fields for existing projects
-- Author: Claude Code Assistant
-- Date: 2025-09-30
-- ============================================================

USE MSIFactory;
GO

SET NOCOUNT ON;

PRINT '============================================================';
PRINT 'Updating Project Colors - Starting Process...';
PRINT '============================================================';

-- Check current state
DECLARE @total_projects INT;
DECLARE @projects_without_colors INT;

SELECT @total_projects = COUNT(*) FROM projects WHERE is_active = 1;
SELECT @projects_without_colors = COUNT(*)
FROM projects
WHERE is_active = 1
  AND (color_primary IS NULL OR color_primary = ''
       OR color_secondary IS NULL OR color_secondary = '');

PRINT 'Total active projects: ' + CAST(@total_projects AS VARCHAR(10));
PRINT 'Projects needing color updates: ' + CAST(@projects_without_colors AS VARCHAR(10));
PRINT '';

-- Define color palette for different project types
-- Using professional gradient combinations that work well together

IF @projects_without_colors > 0
BEGIN
    PRINT 'Updating project colors based on project type and position...';

    -- Temporary table to hold color combinations
    CREATE TABLE #ColorPalette (
        id INT IDENTITY(1,1) PRIMARY KEY,
        primary_color VARCHAR(7),
        secondary_color VARCHAR(7),
        theme_name VARCHAR(50)
    );

    -- Insert predefined color combinations
    INSERT INTO #ColorPalette (primary_color, secondary_color, theme_name) VALUES
    ('#667eea', '#764ba2', 'Purple Gradient'),
    ('#f093fb', '#f5576c', 'Pink Gradient'),
    ('#4facfe', '#00f2fe', 'Blue Gradient'),
    ('#43e97b', '#38f9d7', 'Green Gradient'),
    ('#fa709a', '#fee140', 'Sunset Gradient'),
    ('#a8edea', '#fed6e3', 'Soft Gradient'),
    ('#ff9a9e', '#fecfef', 'Rose Gradient'),
    ('#ffecd2', '#fcb69f', 'Orange Gradient'),
    ('#a18cd1', '#fbc2eb', 'Lavender Gradient'),
    ('#fad0c4', '#ffd1ff', 'Peach Gradient'),
    ('#ff8a80', '#ffb74d', 'Coral Gradient'),
    ('#81c784', '#4fc3f7', 'Ocean Gradient');

    -- Update projects with colors based on project type and cycling through palette
    WITH ProjectsToUpdate AS (
        SELECT
            project_id,
            project_name,
            project_type,
            ROW_NUMBER() OVER (ORDER BY project_id) as row_num
        FROM projects
        WHERE is_active = 1
          AND (color_primary IS NULL OR color_primary = ''
               OR color_secondary IS NULL OR color_secondary = '')
    ),
    ColorAssignment AS (
        SELECT
            ptu.project_id,
            ptu.project_name,
            ptu.project_type,
            cp.primary_color,
            cp.secondary_color,
            cp.theme_name
        FROM ProjectsToUpdate ptu
        CROSS APPLY (
            SELECT TOP 1
                primary_color,
                secondary_color,
                theme_name
            FROM #ColorPalette
            WHERE id = ((ptu.row_num - 1) % (SELECT COUNT(*) FROM #ColorPalette)) + 1
        ) cp
    )
    UPDATE p
    SET
        color_primary = ca.primary_color,
        color_secondary = ca.secondary_color,
        updated_date = GETDATE(),
        updated_by = 'system_color_update'
    FROM projects p
    INNER JOIN ColorAssignment ca ON p.project_id = ca.project_id;

    -- Report updated projects
    PRINT 'Projects updated with colors:';
    SELECT
        project_name,
        project_type,
        color_primary,
        color_secondary,
        'Updated' as status
    FROM projects
    WHERE updated_by = 'system_color_update'
      AND updated_date >= DATEADD(minute, -1, GETDATE())
    ORDER BY project_name;

    -- Clean up
    DROP TABLE #ColorPalette;

    PRINT '';
    PRINT 'Color assignment complete!';
END
ELSE
BEGIN
    PRINT 'All projects already have colors assigned.';
END

-- Verify results
PRINT '';
PRINT 'Final verification:';
SELECT
    COUNT(*) as total_active_projects,
    SUM(CASE WHEN color_primary IS NOT NULL AND color_primary != ''
             AND color_secondary IS NOT NULL AND color_secondary != ''
        THEN 1 ELSE 0 END) as projects_with_colors,
    SUM(CASE WHEN color_primary IS NULL OR color_primary = ''
             OR color_secondary IS NULL OR color_secondary = ''
        THEN 1 ELSE 0 END) as projects_without_colors
FROM projects
WHERE is_active = 1;

PRINT '';
PRINT '============================================================';
PRINT 'Project Color Update Complete';
PRINT '============================================================';

SET NOCOUNT OFF;