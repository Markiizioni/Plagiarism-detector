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
    Clones repositories listed in the .env file and processes the files to move them into respective folders.
    """
    repos = get_repository_urls()

    if not repos:
        print("No repositories found to clone.")
        return

    cloned_repos = []
    failed_repos = []

    for repo_url in repos:
        repo_name = repo_url.split("/")[-1].replace(".git", "")
        repo_path = os.path.join(BASE_DIR, repo_name)

        # Check if the repository already exists
        if os.path.exists(repo_path):
            print(f"Repository {repo_name} already cloned.")
            continue

        try:
            # Clone the repository
            Repo.clone_from(repo_url, repo_path)
            cloned_repos.append(repo_name)

            # Now go through the files and move them to the right directories
            for root, _, files in os.walk(repo_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    # Create a repository structure based on file extension
                    create_repository_and_add_file(file_path)

        except Exception as e:
            failed_repos.append(repo_name)

    if cloned_repos:
        print(f"Successfully cloned repositories: {', '.join(cloned_repos)}")
    if failed_repos:
        print(f"Failed to clone repositories: {', '.join(failed_repos)}")

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
clone_repositories()
