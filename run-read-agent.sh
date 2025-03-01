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