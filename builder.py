import json
from pathlib import Path

import tomllib

from PyInstaller.utils.hooks import collect_submodules

hiddenimports = collect_submodules("numpy")


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


def build_exe(json_str: str, silent: bool, hide_console: bool = False):
    import subprocess

    original_script = Path("./main.py")
    temp_script = Path("./autopkg.py")
    json_path: Path = Path(json_str)

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

    # clear pyinstaller cache
    subprocess.run(["rd", "-r", "build"], shell=True)
    subprocess.run(["rd", "-r", "dist", "autopkg.spec"], shell=True)
    subprocess.run(["rd", "-r", "*.spec"], shell=True)

    ico_path = (
        "icos/autopkg-windows-green.ico"
        if not silent
        else "icos/autopkg-windows-blue.ico"
    )
    name = "autopkg-windows"
    if silent:
        name += "-silent"
    name += f"-v{PROJECT_VERSION}"
    console: str = "autopkg.py" if not hide_console else "--hide-console=hide-early"

    # numpy/pandas hook
    hooks_dir = Path("./hooks")
    hooks_dir.mkdir(exist_ok=True)
    with open(hooks_dir / "hook-numpy.py", "w") as f:
        f.write("from PyInstaller.utils.hooks import collect_submodules\n")
        f.write("hiddenimports = collect_submodules('numpy')\n")
    with open(hooks_dir / "hook-pandas.py", "w") as f:
        f.write("from PyInstaller.utils.hooks import collect_submodules\n")
        f.write("hiddenimports = collect_submodules('pandas')\n")

    subprocess.run(
        [
            "uv",
            "run",
            "pyinstaller",
            "--onefile",
            "--additional-hooks-dir=hooks",
            "--hidden-import=numpy",
            "--hidden-import=pandas",
            "--hidden-import=numpy.core._methods",
            "--hidden-import=numpy.lib.format",
            "--hidden-import=pandas._libs.tslibs.base",
            "--hidden-import=pandas._libs.tslibs.np_datetime",
            "--hidden-import=pandas._libs.tslibs.nattype",
            "--hidden-import=pandas._libs.skiplist",
            "--hidden-import=pandas._libs.hashtable",
            "--hidden-import=pandas._libs.interval",
            f"--icon={ico_path}",
            f"-n={name}",
            console,
            "autopkg.py",
        ]
    )
    temp_script.unlink()
    return 0
