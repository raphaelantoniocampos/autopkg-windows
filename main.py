import json
import os
import subprocess
import re
from sys import argv, exit
from time import sleep
from typing import List, Union

import pandas as pd
from InquirerPy import inquirer
from InquirerPy.separator import Separator
from rich.console import Console
from rich.panel import Panel

from builder import build_exe, get_project_version

project_version = get_project_version()

USAGE = """AutoPkg-Windows
Usage: uv run main.py [OPTIONS] json_path
Options:
-b, --build: Build the executable
-s, --silent: Use silent mode"""


INQUIRER_KEYBINDINGS = {
    "answer": [
        {"key": "enter"},
    ],
    "interrupt": [
        {"key": "c-c"},
        {"key": "escape"},
    ],
    "down": [
        {"key": "down"},
        {"key": "j"},
    ],
    "up": [
        {"key": "up"},
        {"key": "k"},
    ],
    "toggle": [
        {"key": "space"},
    ],
    "toggle-all-true": [
        {"key": "a"},
    ],
}


def main(json_path: str, silent: bool):
    """Main function"""
    os.chdir(os.path.expanduser("~"))
    global PACKAGES
    try:
        verify_winget()
        packages = load_packages_from_json(json_path)
        PACKAGES = check_installed_packages(packages)
        if silent:
            silent_mode()
        else:
            interactive_mode()
    except json.decoder.JSONDecodeError as err:
        sleep(1)
        console.log(
            f"\n[yellow]Arquivo JSON com erro.[/]\n{
                err
            }\n\nLeia o [cyan]README.md[/] para mais informações."
        )
        return 1
    except KeyboardInterrupt:
        sleep(0.1)
        console.log("\n[yellow]Interrompido pelo usuário.[/]\n")
        input("\nPressione Enter para sair...")
        return 0


# --- Classes ---


class PackageManager:
    """
    Represents a package manager with its name, cli install cmd,
    and powershell install script.
    """

    def __init__(
        self,
        name: str,
        cli_install: List[str],
        script: str,
    ) -> None:
        self.name = name
        self.cli_install = cli_install
        self.script = script

    def is_installed(self) -> bool:
        """
        Checks if a package manager is installed.
        Returns:
            bool: True if installed, False otherwise.
        """
        try:
            result = subprocess.run(
                f"{self.cli_install[0]} --version",
                shell=True,
                check=False,
            )
            if result.returncode == 0:
                return True
        except Exception:
            return False

    def install(self) -> None:
        """Installs the Package Manager using the powerShell script"""
        console.log(f"[bold yellow]Instalando {self.name}...[/bold yellow]")
        subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-InputFormat",
                "None",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                self.script,
            ],
            shell=True,
        )

        # Also update sources if package manager is winget
        if self.name == "Winget":
            subprocess.run(
                ["winget", "source", "update", "--force"],
                shell=True,
                check=False,
            )
        console.log(f"[green]{self.name} instalado com sucesso![/green]")

    def __eq__(self, other):
        return self.name == other.name


class Package:
    """
    Represents a package with its package manager, name, package name,
    installed method and install status.
    """

    def __init__(
        self,
        name: str,
        package_name: List[str],
        package_manager: str,
    ) -> None:
        self.name = name
        self.package_name = package_name
        self.package_manager = self._get_package_manager(package_manager)
        self.cmd: Union[str, List[str]] = self._normalize_cmd(
            self.package_manager.cli_install + [*package_name]
        )
        self.is_installed: bool = False

    def _normalize_cmd(self, cmd: list[str]) -> Union[str, list[str]]:
        """Treat backslashes in json, in case there are paths with \\"""
        for s in cmd:
            if "\\" in s:
                return " ".join(cmd)
        return cmd

    def _get_package_manager(self, name: str) -> PackageManager:
        """Returns package manager instance by package"""
        match name:
            case "Chocolatey":
                return CHOCOLATEY
            case "Scoop":
                return SCOOP
            case "Winget":
                return WINGET
            case "Custom":
                return CUSTOM
            case _:
                raise ValueError(
                    f"Gerenciador de pacotes desconhecido: {name}",
                )

    def install(self) -> None:
        """Install the package using its package manager"""
        console.log(f'[bold]Instalação/Comando "{self.name}" iniciado...[/bold]')
        result = subprocess.run(
            self.cmd,
            shell=True,
        )
        if result.returncode != 0 and result.stderr is not None:
            console.log(f"Return code{result.returncode}: {result.stderr}")
            return
        console.log(f'[bold]Instalação/Comando "{self.name}" finalizado![/bold]')


# --- Managers Instances ---


CHOCOLATEY = PackageManager(
    name="Chocolatey",
    cli_install=["choco", "install", "-y"],
    script=(
        "[System.Net.ServicePointManager]::SecurityProtocol = 3072; "
        "iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))"
    ),
)
SCOOP = PackageManager(
    name="Scoop",
    cli_install=["scoop", "install", "-y"],
    script=(
        "Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser;"
        "Invoke-RestMethod -Uri https://get.scoop.sh | Invoke-Expression"
    ),
)
WINGET = PackageManager(
    name="Winget",
    cli_install=[
        "winget",
        "install",
        "--silent",
        "--accept-package-agreements",
        "--accept-source-agreements",
        "--scope",
        "machine",
    ],
    script="Install-Script winget-install -Force",
)

CUSTOM = PackageManager(
    name="Custom",
    cli_install=[],
    script="",
)

# --- Functions ---


def get_missing_package_managers(
    selected_packages: List[Package],
) -> List[PackageManager]:
    """Return missing package managers"""
    package_managers: List[PackageManager] = []
    for package in selected_packages:
        if (
            not package.package_manager.is_installed()
            and not package.package_manager.name == "Custom"
        ):
            console.log(
                f"O programa {package.name} necessita de [cyan]{
                    package.package_manager.name
                }[/] para ser instalado."
            )
            package_managers += [package.package_manager]
    return package_managers


def install_packages(selected_packages: List[Package]) -> None:
    """
    Installs the selected packages.
    Args:
        selected_packages (list): A list of packages selected by the user.
    """
    for package in selected_packages:
        package.install()


def silent_mode():
    """Automated execution mode"""
    try:
        console.log("Instalando pacotes...")
        for package in PACKAGES:
            if not package.is_installed:
                package.install()

    except Exception as e:
        console.log(f"Erro no modo silencioso: {str(e)}")
        return 1

    return 0


def interactive_mode():
    """Interactive execution mode"""
    installed = sum(1 for package in PACKAGES if package.is_installed)
    choices = [
        *[
            f"{'✅ ' if package.is_installed else ''}{package.name}"
            for package in PACKAGES
            if package.package_manager is not CUSTOM
        ],
        Separator(),
        *[
            f"{'✅ ' if package.is_installed else ''}{package.name}"
            for package in PACKAGES
            if package.package_manager is CUSTOM
        ],
    ]

    console.print(
        Panel.fit(
            "[bold cyan]AutoPkg-Windows[/bold cyan] - [yellow]Ferramenta Automática de Pacotes Windows[/yellow]",
            subtitle="[green]github.com/raphaelantoniocampos/autopkg-windows[/green]",
        )
    )

    console.print("")
    console.print(
        Panel.fit(
            f"✅ {installed} programas instalados\n",
            title="[bold]Status do Sistema[/bold]",
        )
    )
    console.print("")
    selected_names = inquirer.checkbox(
        message="Selecione os programas que deseja instalar ou atualizar:",
        choices=choices,
        keybindings=INQUIRER_KEYBINDINGS,
        mandatory=False,
        instruction="Use as teclas de direção para navegar",
        long_instruction=f"[Espaço] seleciona • [Enter] confirma • [Esc] cancela\n{
            project_version
        } • MIT License • © 2025 Raphael Campos",
    ).execute()

    if selected_names:
        selected_names = [name[2:] if "✅" in name else name for name in selected_names]
        selected_packages = [
            package for package in PACKAGES if package.name in selected_names
        ]
        if inquirer.confirm(message="Continuar?", default=True).execute():
            package_managers_to_install = get_missing_package_managers(
                selected_packages
            )
            if package_managers_to_install:
                for package_manager in package_managers_to_install:
                    package_manager.install()
                    console.log("[yellow]Por favor, reinicie o programa.[/]")
                    input("\nPressione Enter para sair...")
                    return
            install_packages(selected_packages)
        else:
            console.log("[bold yellow]Operação cancelada![/bold yellow]")
    else:
        console.log("[bold yellow]Nenhum programa foi selecionado![/bold yellow]")
    input("\nPressione Enter para sair...")
    return 0


def check_installed_packages(packages: List[Package]) -> List[Package]:
    """Updates installed packages list"""

    def check_package(package: Package, df) -> bool:
        """Verifica se o pacote já está instalado (busca por Nome ou ID no DataFrame)."""
        if package.package_manager == CUSTOM:
            return False

        for alias in package.package_name:
            target = alias.lower()

            if (
                df["Nome"].str.lower().str.contains(target, na=False)
                | df["ID"].str.lower().str.contains(target, na=False)
            ).any():
                return True

        return False

    try:
        output = subprocess.check_output(
            ["winget", "list", "--accept-source-agreements"],
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except (FileNotFoundError, subprocess.CalledProcessError, UnicodeDecodeError):
        console.log(
            "[yellow]Aviso: Não foi possível verificar pacotes instalados via Winget.[/yellow]"
        )
        return packages
    else:
        lines = output.splitlines()
        header_index = next(i for i, l in enumerate(lines) if "Nome" in l and "ID" in l)
        data_lines = lines[header_index + 2 :]

        rows = []
        for line in data_lines:
            if not line.strip():
                continue

            parts = re.split(r"\s{2,}", line.strip())

            if len(parts) > 5:
                parts = [" ".join(parts[: len(parts) - 4])] + parts[-4:]

            while len(parts) < 5:
                parts += [""]

            rows += [parts]

        df = pd.DataFrame(
            rows, columns=["Nome", "ID", "Versão", "Disponível", "Origem"]
        )
        df = df.map(lambda x: x.replace("â€¦", "") if isinstance(x, str) else x)

        for package in packages:
            package.is_installed = check_package(package, df)
        return packages


def verify_winget() -> None:
    """Verify if winget is installed and installs it if not"""
    if not WINGET.is_installed():
        WINGET.install()
    return


def load_packages_from_json(json_path: str) -> List[Package]:
    """
    Load packages from a JSON file.
    Args:
        json_path (str): Path to the JSON file.
    Returns:
        list: A list of Package objects.
    """
    with open(json_path, "r") as file:
        packages_data = json.load(file)
    packages = []
    for package_data in packages_data:
        package = Package(**package_data)
        packages += [package]
    return packages


def match_option(arg: str, options: List[str]):
    match arg:
        case "-b":
            options += ["build"]
        case "--build":
            options += ["build"]
        case "-s":
            options += ["silent"]
        case "--silent":
            options += ["silent"]
    if len(options) == 2:
        if options[0] == options[1]:
            print(USAGE)
            exit(1)
    return options


if __name__ == "__main__":
    options = []
    json_path = ""
    match len(argv):
        case 1:
            print(USAGE)
            exit(1)
        case 2:
            options = match_option(argv[1], options)
            if options:
                print(USAGE)
                exit(1)
            json_path = os.path.abspath(argv[1])
        case 3:
            options = match_option(argv[1], options)
            if not options:
                print(USAGE)
                exit(1)
            json_path = os.path.abspath(argv[2])
        case 4:
            options = match_option(argv[1], options)
            if not options:
                print(USAGE)
                exit(1)
            options = match_option(argv[2], options)
            if len(options) != 2:
                print(USAGE)
                exit(1)
            json_path = os.path.abspath(argv[3])
        case _:
            print(USAGE)
            exit(1)

    if json_path[-4:] != "json":
        print(USAGE)
        exit(1)

    silent = "silent" in options
    build = "build" in options
    if build:
        build_exe(json_path=json_path, silent=silent)
        exit(0)

    console = Console()
    exit_code = main(json_path=json_path, silent=silent)
    exit(exit_code)
