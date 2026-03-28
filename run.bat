@echo off

:: Check if an argument was provided
if "%~1"=="" (
    echo Error: Please specify a game to run.
    echo Usage: run.bat [1^|2^|3]
    exit /b
)

if "%~1"=="1" (
    echo Starting Game 1...
    cd "T"
    python TGame.py
    cd ..
    exit /b
)

if "%~1"=="2" (
    echo Starting Game 2...
    cd "TR"
    python TR.py
    cd ..
    exit /b
)

if "%~1"=="3" (
    echo Starting Game 3...
    cd "PT_game"
    python PT.py
    cd ..
    exit /b
)

echo Error: Invalid game number '%~1'.
echo Please choose 1, 2, or 3.