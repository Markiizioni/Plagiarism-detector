import os
from git import Repo
from dotenv import load_dotenv
import shutil

# Import the utility functions
from utilities import get_file_extension, create_repository_and_add_file

# Load environment variables from the .env file
load_dotenv()

# Set the base directory where repositories will be cloned
if '__file__' in globals():
    BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'repositories')
else:
    BASE_DIR = os.path.join(os.getcwd(), 'repositories')  # Default to current working directory

# Create the 'repositories' folder if it does not exist
if not os.path.exists(BASE_DIR):
    os.makedirs(BASE_DIR)

def is_code_file(file_path):
    """
    Determines if a file is likely a code file based on extension and basic content analysis.
    """
    # Common code file extensions
    code_extensions = {
        # Programming languages
        'py', 'js', 'java', 'c', 'cpp', 'cs', 'go', 'rb', 'php', 'ts', 'scala', 
        'rs', 'sh', 'swift', 'kt', 'dart', 'lua', 'pl', 'r', 'sql', 'groovy',
        # Web development
        'html', 'css', 'jsx', 'tsx', 'vue', 'svelte',
        # Configuration and markup
        'json', 'xml', 'yaml', 'yml', 'toml', 'ini',
        # Shell scripts
        'bash', 'zsh', 'fish', 'bat', 'cmd',
        # Other languages
        'm', 'h', 'mm', 'f', 'f90', 'asm', 'S', 's'
    }
    
    ext = get_file_extension(file_path).lower()
    
    # Quick check based on extension
    if ext in code_extensions:
        return True
    
    # For files without recognized extension, do a basic content check
    if ext and ext not in ['jpg', 'png', 'gif', 'pdf', 'zip', 'rar', 'exe', 'dll', 
                          'mp3', 'mp4', 'avi', 'mov', 'docx', 'xlsx', 'pptx']:
        try:
            # Try to open the file and check first few lines for code patterns
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                first_lines = [next(f, '') for _ in range(10)]
                
            # Simple code pattern detection
            code_indicators = ['import ', 'function ', 'class ', 'def ', '#include', 
                              'package ', 'using ', 'var ', 'const ', 'public ', 
                              'private ', 'if(', 'for(', 'while(']
                
            for line in first_lines:
                for indicator in code_indicators:
                    if indicator in line:
                        return True
                        
        except (UnicodeDecodeError, IOError):
            # Binary or unreadable files are not considered code
            pass
            
    return False

# Function to retrieve repository URLs from environment variables
def get_repository_urls():
    """
    Retrieves the list of GitHub repository URLs from environment variables dynamically.
    """
    repo_urls = []
    
    # Loop through all environment variables to find those with REPO_URL_ prefix
    for key, value in os.environ.items():
        if key.startswith("REPO_URL_"):
            repo_urls.append(value)
    
    return repo_urls

def clone_repositories():
    """
    Clones repositories listed in the .env file and processes only the code files.
    """
    repos = get_repository_urls()

    if not repos:
        print("No repositories found to clone.")
        return

    cloned_repos = []
    failed_repos = []
    temp_dir = os.path.join(BASE_DIR, 'temp_clone')

    for repo_url in repos:
        repo_name = repo_url.split("/")[-1].replace(".git", "")
        
        # Create a temporary directory for initial cloning
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)
        os.makedirs(temp_dir)
        
        try:
            # Clone the repository to temp directory
            Repo.clone_from(repo_url, temp_dir)
            cloned_repos.append(repo_name)
            print(f"Repository {repo_name} cloned to temporary directory.")
            
            # Process only code files from the cloned repository
            code_file_count = 0
            for root, _, files in os.walk(temp_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    
                    # Check if it's a code file before processing
                    if is_code_file(file_path):
                        create_repository_and_add_file(file_path)
                        code_file_count += 1
            
            print(f"Processed {code_file_count} code files from {repo_name}")
                
        except Exception as e:
            failed_repos.append(repo_name)
            print(f"Error processing {repo_name}: {str(e)}")
        
        # Clean up temporary clone
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir)

    if cloned_repos:
        print(f"Successfully processed repositories: {', '.join(cloned_repos)}")
    if failed_repos:
        print(f"Failed to process repositories: {', '.join(failed_repos)}")

def remove_repository(repo_name: str):
    """
    Removes a cloned repository.
    """
    repo_path = os.path.join(BASE_DIR, repo_name)
    if not os.path.exists(repo_path):
        print(f"Repository {repo_name} not found.")
        return

    # Remove the repository directory
    shutil.rmtree(repo_path)
    print(f"Repository {repo_name} removed successfully!")

# Run the function to clone repositories and organize files
if __name__ == "__main__":
    clone_repositories()