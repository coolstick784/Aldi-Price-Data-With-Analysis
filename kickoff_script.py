# kickoff_script.py
import asyncio
from aldi import scrape_aldi_data
from concat_data import concat_data, get_anomalies
import subprocess
from pathlib import Path
from datetime import date
def git_commit_and_push():
    repo_dir = Path(r"C:\Users\cools\grocery\aldi")

    # Stage everything
    subprocess.run(["git", "add", "."], cwd=repo_dir, check=True)

    # Commit with today's date
    msg = f"Auto-update Aldi data {date.today().isoformat()}"
    # If there are no changes, this will fail; we can ignore that
    try:
        subprocess.run(["git", "commit", "-m", msg], cwd=repo_dir, check=True)
    except subprocess.CalledProcessError:
        print("No changes to commit.")
        return

    # Push to origin/main
    subprocess.run(["git", "push", "origin", "main"], cwd=repo_dir, check=True)

    
def main():
    base_dir = r"C:\Users\cools\grocery\aldi\data"
    print("Started Aldi…")
    asyncio.run(scrape_aldi_data(base_dir))

    concat_data()
    get_anomalies()

    # New: commit & push
    git_commit_and_push()




if __name__ == "__main__":
    main()





