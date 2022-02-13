from distutils import extension
from importlib.resources import contents
from pprint import pprint
from sre_constants import ANY
from typing import Iterable, Iterator, List, Optional, Dict, Any, Tuple
import requests
import re
from argparse import ArgumentParser
from pathlib import Path
import json
import subprocess

extensions_map = {"python": "py"}


def read_md(path: Path) -> str:
    with path.open("r") as f:
        data: str = f.read()
    return data


def find_code_in_md(data: str) -> re.Match:
    match: re.Match = re.search(r"```[a-z]*\n[\s\S]*?\n```", data, re.MULTILINE)
    return match


def parse_match(match: re.Match) -> Tuple[str, str]:
    data = match.group()
    data = data.replace("```", "")
    data_splitted: List[str] = data.split("\n")
    language: str = data_splitted[0].strip()
    data = "\n".join(data_splitted[1:])
    return data, language


def create_gist(
    data: str, name: str, language: str, token: str, prefix: Optional[str] = ""
) -> Tuple[str, str]:

    extension: str = extensions_map.get(language, "txt")
    payload: Dict[str, Any] = {
        "files": {f"{prefix}-{name}.{extension}": {"content": data}},
        "public": True,
        "description": "Test",
    }
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json",
        "Authorization": f"token {token}",
    }

    res = requests.post(
        "https://api.github.com/gists", headers=headers, data=json.dumps(payload)
    )
    res.raise_for_status()
    output = json.loads(res.content)

    gist_id: str = output["id"]
    gist_url: str = output["html_url"]

    return gist_id, gist_url


def create_carbon_img(code: str, language: str, out_dir: Path, code_id: int) -> str:
    temp_code_file_path: Path = Path(
        f"{'temp_code'}.{extensions_map.get(language, '.txt')}"
    )

    with temp_code_file_path.open("w") as f:
        f.write(code)

    filename: str = f"code-{code_id}"

    process = subprocess.Popen(
        ["carbon-now", str(temp_code_file_path), "-h", "-l", str(out_dir), "-t", filename],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    stdout, stderr = process.communicate()
    temp_code_file_path.unlink()

    return filename


def replace_code_in_md(match: re.Match, data: str, to_replace: str):
    start, end = match.span()
    return data[:start] + to_replace + data[end:]

def write_to_md(data: str, out_dir: Path, filename: str) -> Path:
    out_path: Path = out_dir / (f"{filename}.md")
    with out_path.open('w') as f:
        f.write(data)
    return out_path

if __name__ == "__main__":
    parser = ArgumentParser("Convert a markdown file to an usable medium markdown")
    parser.add_argument("-i", "--input", type=Path, default=Path("./README.md"))
    parser.add_argument("-o", type=Path, default=Path("./medium/"))
    parser.add_argument("--gh-token", type=str, default=False)
    parser.add_argument("--replace-latex", type=bool, default=False)
    parser.add_argument(
        "--image-format", type=str, default="carbon", choices=["carbon, gist"]
    )
    parser.add_argument("--link_prefix", type=str, default="")

    args = parser.parse_args()
    out_dir: Path = args.o
    out_dir.mkdir(exist_ok=True, parents=True)

    gh_token: str =  args.gh_token

    data: str = read_md(args.input)

    match: re.Match = find_code_in_md(data)
    match_num: int = -1

    while match is not None:
        match_num += 1
        parsed_match_content, language = parse_match(match)
        if args.image_format == "gist":
            gist_id, gist_url = create_gist(
                parsed_match_content,
                name=match_num,
                language=language,
                prefix="test",
                token=gh_token,
            )
            to_replace: str = f"{gist_url}"
        elif args.image_format == "carbon":
            filename: str = create_carbon_img(
                parsed_match_content,
                language,
                out_dir,
                code_id=match_num
            )
            image_url: str = f"{args.link_prefix}/{out_dir.stem}/{filename}.png"
            to_replace = f"![img]({image_url})"
        data = replace_code_in_md(match, data, to_replace)
        match: re.Match = find_code_in_md(data)

    filename: str = args.input.stem
    write_to_md(data, out_dir, filename)

    print(data)

    # data, language = parse_match(match)

    # print(find_code_in_md(read_md(Path('./test/test.md'))))
