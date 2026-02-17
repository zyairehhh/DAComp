from huggingface_hub import hf_hub_download, list_repo_files
import os

repo_id = "DAComp/dacomp-da"

# Local download directory
base_dir = "/Users/zhongyiliu/Desktop/data_agent/DAComp/dacomp-da/tasks"
os.makedirs(base_dir, exist_ok=True)

# List and download all files from the dataset
all_files = list_repo_files(repo_id=repo_id, repo_type="dataset")

for file in all_files:
    print(f"Downloading: {file}")
    file_path = hf_hub_download(
        repo_id=repo_id,
        filename=file,
        repo_type="dataset",
        local_dir=base_dir,
        local_dir_use_symlinks=False,
    )
    print(f"Saved to: {file_path}")
