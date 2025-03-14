import os
import shutil

def get_file_extension(file_name: str) -> str:
    """
    Extracts the file extension from the given file name.
    """
    return os.path.splitext(file_name)[1][1:] if '.' in file_name else ''

def create_repository_and_add_file(file_path: str) -> None:
    """
    Creates a folder named after the file extension inside the 'repositories' folder 
    and moves the file into it. If a folder with that name already exists, the file is added to that folder.
    """
    file_name = os.path.basename(file_path)
    file_extension = get_file_extension(file_name)

    if not file_extension:
        print(f"Skipping {file_name} as it has no extension.")
        return

    # Assuming repositories folder is already created at the root of the project (Plagiarism-detector)
    repositories_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'repositories')

    # Create a directory inside 'repositories' based on the file extension (if not exists)
    directory = os.path.join(repositories_dir, file_extension)

    if not os.path.exists(directory):
        os.makedirs(directory)  # Create directory based on extension if it does not exist
        print(f"Created new directory: {directory}")
    else:
        print(f"Directory {directory} already exists.")

    # Move the file to the created directory
    destination_path = os.path.join(directory, file_name)

    # Check if the file already exists in the directory, if so, avoid overwriting
    if os.path.exists(destination_path):
        print(f"File {file_name} already exists in the directory. Skipping...")
    else:
        shutil.move(file_path, destination_path)  # Move the file
        print(f"File {file_name} has been moved to {directory}")
