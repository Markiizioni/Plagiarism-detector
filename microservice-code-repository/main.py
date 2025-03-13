import os
from git import Repo
from dotenv import load_dotenv
import shutil

# Load environment variables from the .env file
load_dotenv()

# Directory where repositories will be cloned
BASE_DIR = "./repositories"
os.makedirs(BASE_DIR, exist_ok=True)

# Function to retrieve repository URLs from the environment variables
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
    Clones repositories listed in the .env file and stores them locally.
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

# Run the function in the script
clone_repositories()
