# MarkdownToMedium

A python cl utility to convert a markdown file to a usable medium format. All code snippets are replaced either by gist or images generated using carbon.

For example, the following markdown file

![img](/images/test_md.png)

is converted into

![img](/images/test_md_converted.png)

To use in on medium, just **copy and paste** the final file from something that shows its rendered version, e.g. GitHub 

## Installation
Clone this repo. 

You need **python**, I've used `python 3.9`. Then

```
pip install -r requirements.txt
```

If you want to use `--image-format carbon`, you need to install it. We use it's cli, [carbon-now-cli](https://github.com/mixn/carbon-now-cli)

```
npm i -g carbon-now-cli
```

## Usage

```
python main.py --help
```