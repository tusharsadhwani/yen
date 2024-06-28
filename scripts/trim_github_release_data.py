import json
import sys
from yen.github import trim_github_release_data


def save_trimmed_release_data(filename: str) -> None:
    with open(filename) as file:
        data = json.load(file)

    trimmed_data = trim_github_release_data(data)
    with open(filename, "w") as file:
        json.dump(trimmed_data, file, indent=2)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"Usage: {sys.orig_argv[0]} {sys.orig_argv[1]} filepath.json")
        sys.exit(1)

    save_trimmed_release_data(sys.argv[1])
