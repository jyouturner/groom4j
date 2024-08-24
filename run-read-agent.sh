#!/bin/bash

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Docker is not installed. Please install Docker and try again."
    exit 1
fi

# Check if the image exists, if not build it
if [[ "$(docker images -q read-agent-java 2> /dev/null)" == "" ]]; then
    echo "Building Docker image..."
    docker build -t read-agent-java .
fi

# Function to run a command in the Docker container
run_in_docker() {
    local java_project_path="$1"
    shift
    local script="$1"
    shift
    
    # Convert the Java project path to an absolute path
    java_project_path=$(realpath "$java_project_path")
    
    echo "Mapping $java_project_path to /java_project in Docker container"
    
    docker run --rm -it \
        -v "$(pwd):/app" \
        -v "$java_project_path:/java_project:ro" \
        -v "$(pwd)/application.yml:/app/application.yml:ro" \
        read-agent-java "$script" /java_project "$@"
}

# Check the command argument
case "$1" in
    gist-files)
        if [ "$#" -lt 2 ]; then
            echo "Usage: $0 gist-files <path_to_java_project>"
            exit 1
        fi
        java_project_path="$2"
        shift 2
        run_in_docker "$java_project_path" gist_files.py "$@"
        ;;
    gist-packages)
        if [ "$#" -lt 2 ]; then
            echo "Usage: $0 gist-packages <path_to_java_project>"
            exit 1
        fi
        java_project_path="$2"
        shift 2
        run_in_docker "$java_project_path" gist_packages.py "$@"
        ;;
    groom-task)
        if [ "$#" -lt 3 ]; then
            echo "Usage: $0 groom-task <path_to_java_project> --task=\"Your task description\""
            exit 1
        fi
        java_project_path="$2"
        shift 2
        run_in_docker "$java_project_path" grooming_task.py "$@"
        ;;
    *)
        echo "Usage: $0 {gist-files|gist-packages|groom-task} <path_to_java_project> [additional arguments]"
        echo "Example: $0 groom-task /path/to/java/project --task=\"Add a new feature\""
        exit 1
        ;;
esac