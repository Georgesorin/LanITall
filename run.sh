#!/bin/bash

# Check if an argument was provided
if [ -z "$1" ]; then
    echo "Error: Please specify a game to run."
    echo "Usage: ./run.sh [1|2|3]"
    exit 1
fi

case "$1" in
    1)
        echo "Starting Game 1..."
        cd "./T/" || exit
        python3 TGame.py
        ;;
    2)
        echo "Starting Game 2..."
        cd "./TR/" || exit
        python3 TR.py
        ;;
    3)
        echo "Starting Game 3..."
        cd "./PT_game/" || exit
        python3 PT.py
        ;;
    *)
        echo "Error: Invalid game number '$1'."
        echo "Please choose 1, 2, or 3."
        ;;
esac