#!/usr/bin/env python3
import argparse
import json
import sys

from files_api import FilesAPI


def parse_value(raw_value):
    try:
        return json.loads(raw_value)
    except json.JSONDecodeError:
        return raw_value


def parse_named_arg(raw_arg):
    if "=" not in raw_arg:
        raise ValueError(f"Named argument must be key=value: {raw_arg}")
    key, raw_value = raw_arg.split("=", 1)
    key = key.strip()
    if not key:
        raise ValueError(f"Named argument key is empty: {raw_arg}")
    return key, parse_value(raw_value)


def configure_stdout():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")


def main():
    configure_stdout()
    parser = argparse.ArgumentParser(description="Call FilesAPI method by method name")
    parser.add_argument("-m", "--python-method", required=True, help="Python method name from indexes listed in assets/index/manifest.json")
    parser.add_argument(
        "--posarg",
        action="append",
        default=[],
        help="Positional argument value; parsed as JSON when possible",
    )
    parser.add_argument(
        "--arg",
        action="append",
        default=[],
        help="Named argument in key=value form; value is parsed as JSON when possible",
    )
    parser.add_argument(
        "--save-to",
        help="Write raw response bytes to this path instead of printing the response body",
    )
    args = parser.parse_args()

    positional_args = [parse_value(value) for value in args.posarg]
    keyword_args = dict(parse_named_arg(value) for value in args.arg)

    api = FilesAPI()
    result = api.call_by_python_method(
        args.python_method,
        *positional_args,
        save_to=args.save_to,
        **keyword_args,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    raise SystemExit(main())
