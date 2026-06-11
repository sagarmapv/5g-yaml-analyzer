import shutil
import subprocess
from pathlib import Path

INSTALL_HINT = (
    "Install OpenAPI bundler with: npm install -g @apidevtools/swagger-cli\n"
    "Or use: npx @apidevtools/swagger-cli"
)


def remove_path(path: Path) -> None:
    """Remove a file or directory (Windows-safe cleanup for stale build artifacts)."""
    if not path.exists():
        return
    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()


def resolve_swagger_cli() -> list[str]:
    """Return command prefix to invoke swagger-cli (Windows-safe)."""
    for name in ("swagger-cli", "swagger-cli.cmd"):
        path = shutil.which(name)
        if path:
            return [path]

    npx = shutil.which("npx") or shutil.which("npx.cmd")
    if npx:
        return [npx, "@apidevtools/swagger-cli"]

    raise RuntimeError(f"swagger-cli not found.\n{INSTALL_HINT}")


def bundle_yaml_to_json(yaml_path: Path, json_path: Path) -> None:
    """Bundle a YAML OpenAPI spec to JSON using swagger-cli."""
    json_path.parent.mkdir(parents=True, exist_ok=True)
    remove_path(json_path)
    cmd = [
        *resolve_swagger_cli(),
        "bundle",
        str(yaml_path),
        "--outfile",
        str(json_path),
        "--type",
        "json",
    ]
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr or exc.stdout or str(exc)
        raise RuntimeError(f"swagger-cli bundle failed for {yaml_path.name}: {stderr}") from exc
    except FileNotFoundError as exc:
        raise RuntimeError(f"swagger-cli not found.\n{INSTALL_HINT}") from exc

    if not json_path.is_file() or json_path.stat().st_size == 0:
        remove_path(json_path)
        raise RuntimeError(
            f"swagger-cli did not produce a valid JSON file for {yaml_path.name}"
        )
