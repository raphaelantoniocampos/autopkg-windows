import json
import subprocess
from pathlib import Path

import tomllib


PYPROJECT_PATH = Path.cwd() / Path("pyproject.toml").absolute()


def get_project_version() -> str:
    """Reads and returns the project version from the pyproject.toml file."""
    try:
        with open(PYPROJECT_PATH, "rb") as f:
            data = tomllib.load(f)
        return data["project"]["version"]
    except FileNotFoundError:
        return "filenotfound"
    except KeyError:
        return "keyerror"


PROJECT_VERSION = get_project_version()


def rewrite_load_json(json_path, temp_f):
    with open(json_path, "r", encoding="utf-8") as file:
        packages_data = json.load(file)
        packages_list = """
    PACKAGES = [
"""
        for package in packages_data:
            packages_list += f'        Package(name="{package["name"]}", package_name={
                package["package_name"]
            }, package_manager="{package["package_manager"]}"),\n'
        packages_list += "    ]\n"

    temp_f.write("def load_packages_from_json(json_path):")
    temp_f.write(packages_list)
    temp_f.write("\n    return PACKAGES\n\n")


def rewrite_if_name_main(temp_f, silent):
    temp_f.write(f"""
if __name__ == "__main__":
    silent = {str(silent)}
    console = Console()
    main("", silent)
""")


def rewrite_project_version(temp_f):
    temp_f.write(f"""
project_version = "{PROJECT_VERSION}"
""")


def build_exe(json_path: str, silent: bool, hide_console: bool = False):
    original_script = Path("./main.py")
    temp_script = Path("./autopkg.py")
    json_path = Path(json_path)

    with open(original_script, "r", encoding="utf-8") as original_f:
        original_lines = original_f.read().split("\n")
        with open(temp_script, "w", encoding="utf-8") as temp_f:
            ignore = False
            blank_lines = 0
            for line in original_lines:
                if line == "":
                    blank_lines += 1

                if blank_lines >= 2:
                    ignore = False
                    blank_lines = 0

                if line.startswith("from builder import"):
                    temp_f.write("# ")

                if line.startswith("project_version = get_project_version()"):
                    rewrite_project_version(temp_f)
                    ignore = True

                if line.startswith("def load_packages_from_json"):
                    rewrite_load_json(json_path, temp_f)
                    ignore = True

                if line.startswith('if __name__ == "__main__":'):
                    rewrite_if_name_main(temp_f=temp_f, silent=silent)
                    break

                if not ignore:
                    temp_f.write(line)
                    temp_f.write("\n")

    subprocess.run(["uv", "run", "ruff", "check", "--fix", "autopkg.py"])
    ico_path = (
        "icos/autopkg-windows-green.ico"
        if not silent
        else "icos/autopkg-windows-blue.ico"
    )
    name = "autopkg-windows" if not silent else "autopkg-windows-silent"
    hide_console = "autopkg.py" if not hide_console else "--hide-console=hide-early"
    subprocess.run(
        [
            "uv",
            "run",
            "pyinstaller",
            "--onefile",
            f"--icon={ico_path}",
            f"-n={name}",
            hide_console,
            "autopkg.py",
        ]
    )
    temp_script.unlink()
    return 0
