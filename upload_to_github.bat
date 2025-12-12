@echo off
echo ================================================================================
echo pycontroldae - Upload to GitHub Script
echo ================================================================================
echo.

echo [Step 1] Initializing Git repository...
git init
if errorlevel 1 (
    echo ERROR: Failed to initialize git repository
    pause
    exit /b 1
)
echo [OK] Git repository initialized
echo.

echo [Step 2] Adding all files...
git add .
if errorlevel 1 (
    echo ERROR: Failed to add files
    pause
    exit /b 1
)
echo [OK] Files added
echo.

echo [Step 3] Creating initial commit...
git commit -m "Initial commit: Complete Port system implementation"
if errorlevel 1 (
    echo ERROR: Failed to create commit
    pause
    exit /b 1
)
echo [OK] Commit created
echo.

echo [Step 4] Adding remote repository...
echo.
echo IMPORTANT: Please enter your GitHub repository URL
echo Format: https://github.com/YOUR_USERNAME/pycontroldae.git
echo.
set /p REPO_URL="Enter repository URL: "

git remote add origin %REPO_URL%
if errorlevel 1 (
    echo ERROR: Failed to add remote
    pause
    exit /b 1
)
echo [OK] Remote added
echo.

echo [Step 5] Pushing to GitHub...
echo You may need to enter your GitHub credentials...
echo.
git branch -M main
git push -u origin main
if errorlevel 1 (
    echo ERROR: Failed to push to GitHub
    echo.
    echo Common issues:
    echo 1. Authentication failed - check your GitHub username/password or token
    echo 2. Repository URL is incorrect
    echo 3. Repository already exists with content
    echo.
    pause
    exit /b 1
)

echo.
echo ================================================================================
echo SUCCESS! Your repository has been uploaded to GitHub!
echo ================================================================================
echo.
echo Repository URL: %REPO_URL%
echo.
echo Next steps:
echo 1. Visit your repository on GitHub
echo 2. Add topics/tags to make it easier to find
echo 3. Edit repository description if needed
echo 4. Share with the community!
echo.
pause
