from cmath import log
from time import time
from typing import List, Optional, Dict, Any, Tuple
import requests
import re
from argparse import ArgumentParser
from pathlib import Path
import json
import subprocess
import logging

# a dict to map the markdown programming language syntax highlighter to its extension
# ```python -> is for python so `.py`
extensions_map = {"python": "py"}
# if you think I wrote you overestimate my power
REGEX_TO_FIND_CODE_IN_MD: str = r"```[a-z]*\n[\s\S]*?\n```"

logging.basicConfig(level=logging.INFO)


def read_md(path: Path) -> str:
    with path.open("r") as f:
        data: str = f.read()
    return data


def find_code_in_md(data: str) -> re.Match:
    match: re.Match = re.search(REGEX_TO_FIND_CODE_IN_MD, data, re.MULTILINE)
    return match


def parse_match(match: re.Match) -> Tuple[str, str]:
    """A match contains the code snippet, so e.g. ```python .... ```. Here we remove the "```" and we get the correct language, e.g. `python`

    Args:
        match (re.Match): Our match

    Returns:
        Tuple[str, str]: The snippet, the language (e.g. `python`)
    """
    data = match.group()
    data = data.replace("```", "")
    data_splitted: List[str] = data.split("\n")
    language: str = data_splitted[0].strip()
    code = "\n".join(data_splitted[1:])
    return code, language


def create_gist(
    code: str, name: str, language: str, token: str, prefix: Optional[str] = ""
) -> Tuple[str, str]:
    """Using git apis, create a gist

    Args:
        code (str): _description_
        name (str): _description_
        language (str): _description_
        token (str): _description_
        prefix (Optional[str], optional): _description_. Defaults to "".

    Returns:
        Tuple[str, str]: The gist id and the gist url
    """
    extension: str = extensions_map.get(language, "txt")
    data: Dict[str, Any] = {
        "files": {f"{prefix}-{name}.{extension}": {"content": code}},
        "public": True,
        "description": "Test",
    }
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "Content-Type": "application/json",
        "Authorization": f"token {token}",
    }

    res = requests.post(
        "https://api.github.com/gists", headers=headers, data=json.dumps(data)
    )
    res.raise_for_status()
    output = json.loads(res.content)

    gist_id: str = output["id"]
    gist_url: str = output["html_url"]
    # wait a while
    time.sleep(0.2)

    return gist_id, gist_url


def create_carbon_img(code: str, language: str, out_dir: Path, code_id: int) -> str:
    """This is tricky, using `carbon-now` create a cool image of our code. First we create a temp file with the code, we use it as input to carbon-now and we store the output in `out_dir`

    Args:
        code (str): _description_
        language (str): _description_
        out_dir (Path): _description_
        code_id (int): _description_

    Returns:
        str: _description_
    """
    temp_code_file_path: Path = Path(
        f"{'temp_code'}.{extensions_map.get(language, '.txt')}"
    )

    with temp_code_file_path.open("w") as f:
        f.write(code)

    filename: str = f"code-{code_id}"

    process = subprocess.Popen(
        [
            "carbon-now",
            str(temp_code_file_path),
            "-h",
            "-l",
            str(out_dir),
            "-t",
            filename,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    stdout, stderr = process.communicate()
    temp_code_file_path.unlink()

    return filename


def replace_code_in_md(match: re.Match, data: str, to_replace: str):
    """Using our match, we finally replace the markdown code snipepet with `to_replace`

    Args:
        match (re.Match): _description_
        data (str): _description_
        to_replace (str): _description_

    Returns:
        _type_: _description_
    """
    start, end = match.span()
    return data[:start] + to_replace + data[end:]


def write_to_md(data: str, out_dir: Path, filename: str) -> Path:
    out_path: Path = out_dir / (f"{filename}.md")
    with out_path.open("w") as f:
        f.write(data)
    return out_path


if __name__ == "__main__":
    parser = ArgumentParser(
        "Convert a markdown file to an usable medium markdown. Code snippets are replace by gist or images generated using carbon"
    )
    parser.add_argument(
        "-i",
        "--input",
        type=Path,
        default=Path("./README.md"),
        help="The markdown file path",
    )
    parser.add_argument(
        "-o", type=Path, default=Path("./medium/"), help="The output directory"
    )
    parser.add_argument(
        "--gh-token",
        type=str,
        required=True,
        help="Your github personal token, see https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token",
    )
    parser.add_argument(
        "--replace-latex", type=bool, default=False, help="Currently not implemented"
    )
    parser.add_argument(
        "--image-format",
        type=str,
        default="carbon",
        choices=["carbon, gist"],
        help="How to convert the code snippets.",
    )
    parser.add_argument(
        "--link-prefix",
        type=str,
        default="The prefix to the links used to replace your code snippets",
    )

    args = parser.parse_args()
    out_dir: Path = args.o
    out_dir.mkdir(exist_ok=True, parents=True)

    gh_token: str = args.gh_token

    data: str = read_md(args.input)

    match: re.Match = find_code_in_md(data)
    match_num: int = -1
    logging.info(f"Ready to convert {args.input.stem} using {args.image_format}")
    while match is not None:
        logging.info("Finding code snippets...")
        match_num += 1
        code, language = parse_match(match)
        if args.image_format == "gist":
            gist_id, gist_url = create_gist(
                code,
                name=match_num,
                language=language,
                prefix="test",
                token=gh_token,
            )
            to_replace: str = f"{gist_url}"
            logging.info(f"See your gist at {gist_url}")
        elif args.image_format == "carbon":
            filename: str = create_carbon_img(
                code, language, out_dir, code_id=match_num
            )
            image_url: str = f"{args.link_prefix}/{out_dir.stem}/{filename}.png"
            to_replace = f"![img]({image_url})"
            logging.info(
                f"Created code image using carbon at {out_dir.stem}/{filename}.png"
            )
        data = replace_code_in_md(match, data, to_replace)
        match: re.Match = find_code_in_md(data)
        logging.info(f"Snippet {match_num} replaced")

    filename: str = args.input.stem
    out_path = write_to_md(data, out_dir, filename)
    logging.info(f"Done, your new file is at {out_path}")
