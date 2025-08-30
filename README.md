# AutoPkg-Windows

> 🚀 Simplify program installation on Windows using Winget, Chocolatey, or Scoop

---

## Features

- **Automatic Dependency Management**:
  - Installs Package Managers if it is not already installed.
- **Application Installation**:
  - Provides a menu to select programs for installation.
  - Support for installing multiple applications at once.
  - Reads applications lists from JSON files.
  - Silent mode to install and update packages with Winget.

---

## Prerequisites 

- **Operating System**: Windows (PowerShell required)
- **Privileges**: Administrator access
- **Python**: Version 3.10 or higher
- **Python Package Manager**: [uv](https://github.com/astral-sh/uv)

---

## Usage

### Clone the Repository:

```
git clone https://github.com/raphaelantoniocampos/autopkg-windows
cd autopkg-windows
```

### Install uv if already not installed

To install uv follow the [instructions](https://docs.astral.sh/uv/getting-started/installation). 

### Prepare the JSON file

- The data directory already includes an example JSON file for you to use:

    - **packages.json**: A list of general-purpose packagelications.

- You can modify these files or create your own JSON file with the following format:

```json
[
    {
        "package_manager": "Winget",
        "name": "Google Chrome",
        "package_name": ["Google.Chrome"]
    }
]
```

- You can also include batch scripts using Custom as the package manager:

```json
[
    {
        "package_manager": "Custom",
        "name": "Winget Update All",
        "package_name": [
            "powershell", 
            "winget", 
            "update", 
            "--all"
        ]
    }
]
```


### Run the Script

- Run the script by passing the JSON file path as an argument:

```
uv run .\main.py .\data\packages.json
```

### Run in silent mode

- If you want to run the script in silent mode use *--silent*. (Runs installations without user interaction):

```
uv run .\main.py -s .\data\packages.json
uv run .\main.py --silent .\data\packages.json
```

---

### Generate an Executable (Optional)

- To create a standalone executable, use the build flag:

```
uv run .\main.py -b .\data\packages.json
uv run .\main.py --build .\data\packages.json
```

- The generated executable will be located in dist/autopkg-windows.exe. 

- Also supports silent mode

```
uv run .\main.py -s -b .\data\packages.json
uv run .\main.py --silent --build .\data\packages.json
```

---

## Dependencies

The project uses the following Python libraries:

- **[InquirerPy](https://github.com/kazhala/InquirerPy)**: For interactive terminal menus.
- **[rich](https://github.com/Textualize/rich)**: For styled terminal output.
- **[pyinstaller](https://www.pyinstaller.org/)** *(dev)*: For building executables.
- **[ruff](https://docs.astral.sh/ruff/)** *(dev)*: For linting and formatting.

---

## Contributing

Contributions are welcome! Feel free to open issues or submit pull requests.

---

## License

This project is licensed under the MIT License. See the LICENSE file for details.

For more details, see the [LICENSE](LICENSE) file.
