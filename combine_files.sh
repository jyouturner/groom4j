#!/bin/bash

# Debug print function
debug_print() {
    if [ "$debug_mode" = "true" ]; then
        echo "DEBUG: $1" >&2
    fi
}

# Help message function
print_usage() {
    echo "Usage: $0 [-p project_root] [-o output_name] [-t] [-s] [-e exclude_pattern] [--e exclude_file_pattern]"
    echo "Options:"
    echo "  -p : Specify project root directory (default: current directory)"
    echo "  -o : Specify output file name (default: project_context.txt)"
    echo "  -t : Exclude test files and directories"
    echo "  -s : Only include files from src directory"
    echo "  -e : Exclude directories matching pattern (can be used multiple times)"
    echo "  --e : Exclude files matching pattern (can be used multiple times, e.g., --e \"*.md\")"
    echo "  -d : Enable debug mode"
    exit 1
}

# Check for help flag first
if [[ "$1" == "--help" || "$1" == "-h" ]]; then
    print_usage
fi

# Default values
project_root="."
output_dir="output"
output_name="project_context.txt"
include_tests="true"
src_only="false"
exclude_patterns=""
exclude_file_patterns=""
debug_mode="false"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -p) project_root="$2"; shift 2 ;;
        -o) output_name="$2"; shift 2 ;;
        -t) include_tests="false"; shift ;;
        -s) src_only="true"; shift ;;
        -e) exclude_patterns="$exclude_patterns $2"; shift 2 ;;
        --e) exclude_file_patterns="$exclude_file_patterns $2"; shift 2 ;;
        -d) debug_mode="true"; shift ;;
        -*) echo "Unknown option: $1" >&2; print_usage ;;
        *) break ;;
    esac
done

# Update output handling
if [[ "$output_name" == *"/"* ]]; then
    # If output_name contains a path, split it
    output_dir=$(dirname "$output_name")
    output_name=$(basename "$output_name")
else
    # Default to output directory if no path specified
    output_dir="output"
fi

# Ensure output directory exists
mkdir -p "$output_dir"

# Create full output path
output_file="$output_dir/$output_name"

# Check and update .gitignore
if [ ! -f .gitignore ]; then
    echo "output/" > .gitignore
    echo "Created .gitignore with output/ entry"
elif ! grep -v "^output/$" .gitignore; then
    echo >> .gitignore
    echo "output/" >> .gitignore
    echo "Added output/ to .gitignore"
fi

# Check for tree command and provide installation instructions if missing
check_tree_command() {
    if ! command -v tree >/dev/null 2>&1; then
        echo "Warning: 'tree' command not found. For better directory visualization, please install tree:"
        echo
        if [[ "$OSTYPE" == "darwin"* ]]; then
            echo "On macOS (using Homebrew):"
            echo "    brew install tree"
        elif [[ -f "/etc/debian_version" ]]; then
            echo "On Debian/Ubuntu:"
            echo "    sudo apt-get install tree"
        elif [[ -f "/etc/redhat-release" ]]; then
            echo "On RHEL/CentOS/Fedora:"
            echo "    sudo yum install tree"
        else
            echo "Please install the 'tree' package using your system's package manager."
        fi
        echo
        echo "Proceeding with basic directory structure visualization..."
        echo
        return 1
    fi
    return 0
}

# Add this function near the top of the script
get_relative_path() {
    local target="$1"
    local base="$2"
    
    # Convert both paths to absolute paths
    local abs_target=$(cd "$(dirname "$target")" && pwd)/$(basename "$target")
    local abs_base=$(cd "$base" && pwd)
    
    # Remove common prefix
    local result="${abs_target#$abs_base/}"
    
    # If the result is the same as input, paths don't share common prefix
    if [ "$result" = "$abs_target" ]; then
        echo "$target"
    else
        echo "$result"
    fi
}

# Replace the problematic realpath section with this
cd "$project_root" || exit 1
project_root=$(pwd)
output_file_abs=$(cd "$(dirname "$output_file")" 2>/dev/null && pwd)/$(basename "$output_file") || output_file_abs="$output_file"
output_dir_relative=$(get_relative_path "$(dirname "$output_file_abs")" "$project_root")

# Remove git repository check
# if [ ! -d "$project_root/.git" ]; then
#     echo "Error: Not a git repository. Please initialize git first." >&2
#     exit 1
# fi

# Clear or create the output file
mkdir -p "$(dirname "$output_file")"
> "$output_file"

# Function to check if file is an image
is_image_file() {
    local file="$1"
    local ext
    ext=$(echo "${file##*.}" | tr '[:upper:]' '[:lower:]')
    local image_extensions=" jpg jpeg png gif bmp ico svg webp tiff raw "
    
    [[ "$image_extensions" == *" $ext "* ]]
}

# Function to get gitignore patterns
get_gitignore_patterns() {
    local patterns=""
    if [ -f ".gitignore" ]; then
        while IFS= read -r line; do
            # Skip empty lines and comments
            if [[ -n "$line" && ! "$line" =~ ^[[:space:]]*# ]]; then
                # Trim whitespace
                line="${line#"${line%%[![:space:]]*}"}"
                line="${line%"${line##*[![:space:]]}"}"
                
                if [ -n "$line" ]; then
                    # Handle negation patterns (starting with !)
                    if [[ "$line" == !* ]]; then
                        continue  # Skip negation patterns for now
                    fi
                    
                    # Convert glob patterns to find patterns
                    line="${line//\*\*/.*}"  # Convert ** to .*
                    line="${line//\*/[^/]*}"  # Convert * to [^/]*
                    line="${line//\?/.}"      # Convert ? to .
                    
                    # Handle directory patterns (ending with /)
                    if [[ "$line" == */ ]]; then
                        line="${line%/}"
                    fi
                    
                    patterns="$patterns|$line"
                fi
            fi
        done < ".gitignore"
        
        # Remove leading |
        patterns="${patterns#|}"
    fi
    echo "$patterns"
}

# Function to check if file should be excluded
should_exclude_file() {
    local file="$1"
    local excluded_files=" poetry.lock package-lock.json yarn.lock pnpm-lock.yaml Cargo.lock "
    local exclude_dirs=" .git/ target/ build/ .gradle/ .idea/ .settings/ bin/ out/ "
    local basename
    basename=$(basename "$file")
    
    # Check if file is in .git directory first
    if [[ "$file" == ".git"/* ]] || [[ "$file" == *"/.git/"* ]]; then
        debug_print "File '$file' excluded because it's in .git directory"
        return 0
    fi
    
    # Check .gitignore patterns first
    local gitignore_patterns
    gitignore_patterns=$(get_gitignore_patterns)
    if [ -n "$gitignore_patterns" ]; then
        if echo "$file" | grep -qE "($gitignore_patterns)"; then
            debug_print "File '$file' excluded by gitignore pattern"
            return 0
        fi
    fi

    # Check for excluded filenames
    if [[ "$excluded_files" == *" $basename "* ]]; then
        return 0
    fi
    
    # Check for excluded directories
    for dir in $exclude_dirs; do
        if [[ "$file" == *"/$dir"* ]] || [[ "$file" == "$dir"* ]]; then
            return 0
        fi
    done
    
    # Check user-specified exclude patterns for directories
    for pattern in $exclude_patterns; do
        if [[ "$file" == *"$pattern"* ]]; then
            return 0
        fi
    done
    
    # Check user-specified exclude patterns for files
    for pattern in $exclude_file_patterns; do
        if [[ "$file" == $pattern ]]; then
            return 0
        fi
    done
    
    # Handle test exclusion if flag is set
    if [ "$include_tests" = "false" ]; then
        if [[ "$file" == *"/test/"* ]] || [[ "$file" == *"/tests/"* ]] || [[ "$file" =~ Test\.java$ ]] || [[ "$file" =~ Tests\.java$ ]]; then
            return 0
        fi
    fi
    
    # Handle src-only if flag is set
    if [ "$src_only" = "true" ]; then
        if [[ "$file" != *"/src/"* ]] && [[ "$file" != "src/"* ]]; then
            return 0
        fi
    fi
    
    return 1
}

# Function to generate tree structure
generate_tree() {
    local root="$1"
    local output_file="$2"
    local exclude_dir="$3"
    
    echo "Project Structure:" >> "$output_file"
    echo "==================" >> "$output_file"

    # Create temporary file list, excluding image files and lock files
    local tmpfile=$(mktemp)
    find "$root" -type f -not -path '*/\.git/*' | grep -v "^.gitignore$" | grep -v "^$exclude_dir/" | while read -r file; do
        if ! is_image_file "$file" && ! should_exclude_file "$file"; then
            echo "$file"
        fi
    done > "$tmpfile"

    # Generate tree structure
    if check_tree_command; then
        # Use tree command for better visualization
        echo "." >> "$output_file"
        tree --fromfile -F -a --noreport -I ".git" < "$tmpfile" >> "$output_file"
    else
        # Fallback to basic structure
        echo "." >> "$output_file"
        local prev_dir=""
        while IFS= read -r file; do
            dir=$(dirname "$file")
            if [ "$dir" = "." ]; then
                echo "├── $(basename "$file")" >> "$output_file"
            else
                # Only print directory if it's different from previous
                if [ "$dir" != "$prev_dir" ]; then
                    depth=$(echo "$dir" | tr -cd '/' | wc -c)
                    indent=$(printf '%*s' "$((depth * 3))" '')
                    echo "$indent├── $dir/" >> "$output_file"
                    prev_dir="$dir"
                fi
                # Print file
                depth=$(($(echo "$dir" | tr -cd '/' | wc -c) + 1))
                indent=$(printf '%*s' "$((depth * 3))" '')
                echo "$indent├── $(basename "$file")" >> "$output_file"
            fi
        done < "$tmpfile"
    fi

    rm -f "$tmpfile"
    echo -e "\n\n" >> "$output_file"
}

# Function to add a file to the output
add_file() {
    local file="$1"
    local exclude_dir="$2"
    
    # Skip .gitignore, files in output directory, image files, and lock files
    if [ "$file" = ".gitignore" ] || \
       [[ "$file" == "$exclude_dir"/* ]] || \
       is_image_file "$file" || \
       should_exclude_file "$file"; then
        return
    fi
    
    if [ -f "$file" ]; then
        echo "Adding file: $file"
        echo "File: $file" >> "$output_file"
        echo "===================" >> "$output_file"
        echo -e "\n" >> "$output_file"
        cat "$file" >> "$output_file"
        echo -e "\n\n" >> "$output_file"
    fi
}

# Add debug output
echo "Debug: Processing files in $project_root"
echo "Debug: Output will be written to $output_file"
echo "Debug: Include tests: $include_tests"
echo "Debug: Src only: $src_only"
if [ -n "$exclude_patterns" ]; then
    echo "Debug: Exclude directory patterns:$exclude_patterns"
fi
if [ -n "$exclude_file_patterns" ]; then
    echo "Debug: Exclude file patterns:$exclude_file_patterns"
fi

echo "Generating tree structure..."
generate_tree "$project_root" "$output_file" "$output_dir_relative"

echo "Adding file contents..."
# Modify the process_files function
process_files() {
    local total_files=0
    local processed_files=0
    
    # Count total files first, excluding .git directory
    total_files=$(find "$project_root" -type f -not -path '*/\.git/*' | wc -l)
    
    find "$project_root" -type f -not -path '*/\.git/*' | while read -r file; do
        # Get relative path without using realpath
        rel_file=$(get_relative_path "$file" "$project_root")
        
        # Skip if file is in output directory or is the output file itself
        if [[ "$rel_file" == "$output_dir_relative"/* ]] || \
           [[ "$file" == "$output_file_abs" ]]; then
            continue
        fi
        
        processed_files=$((processed_files + 1))
        printf "\rProcessing files: %d/%d" "$processed_files" "$total_files" >&2
        
        add_file "$rel_file" "$output_dir_relative"
    done
    echo >&2  # New line after progress
}

# Replace the final find command with
process_files

# Print completion message
echo "Project context has been compiled into $output_file"
echo "Total size: $(wc -l < "$output_file") lines"