import json
from yen.github import trim_github_release_data


def generate_trimmed_release_data(filename: str) -> None:
    with open(filename) as file:
        data = json.load(file)

    trimmed_data = trim_github_release_data(data)
    print(json.dumps(trimmed_data, indent=2))
