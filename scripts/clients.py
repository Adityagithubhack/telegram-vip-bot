from pathlib import Path
import subprocess


WEB_ROOT = Path(__file__).resolve().parents[2]
MASTER_FOLDER = "telegram-vip-bot"


def read_env_value(env_file: Path, key: str) -> str | None:
    if not env_file.exists():
        return None

    for line in env_file.read_text().splitlines():
        if line.startswith(f"{key}="):
            return line.split("=", 1)[1].strip()

    return None


def docker_container_running(name: str) -> bool:
    result = subprocess.run(
        [
            "docker",
            "inspect",
            "-f",
            "{{.State.Running}}",
            name,
        ],
        capture_output=True,
        text=True,
    )

    return result.returncode == 0 and result.stdout.strip() == "true"


def main() -> None:
    clients = []

    for folder in sorted(WEB_ROOT.glob("telegram-vip-*")):
        if not folder.is_dir() or folder.name == MASTER_FOLDER:
            continue

        env_file = folder / ".env"

        if not env_file.exists():
            continue

        brand = read_env_value(env_file, "BRAND_NAME") or folder.name
        admin_brand = read_env_value(env_file, "ADMIN_BRAND_NAME") or "-"
        compose_project = (
            read_env_value(env_file, "COMPOSE_PROJECT_NAME")
            or folder.name.replace("-", "_")
        )

        postgres_name = f"{compose_project}_postgres"
        redis_name = f"{compose_project}_redis"

        postgres_running = docker_container_running(postgres_name)
        redis_running = docker_container_running(redis_name)

        clients.append(
            (
                brand,
                admin_brand,
                folder.name,
                postgres_running,
                redis_running,
            )
        )

    print("\nCLIENTS")
    print("=" * 60)

    if not clients:
        print("No clients found.")
    else:
        for number, (
            brand,
            admin_brand,
            folder,
            postgres_running,
            redis_running,
        ) in enumerate(clients, 1):
            print(f"{number}. {brand}")
            print(f"   Admin:    {admin_brand}")
            print(f"   Folder:   {folder}")
            print(
                f"   Postgres: {'RUNNING' if postgres_running else 'STOPPED'}"
            )
            print(
                f"   Redis:    {'RUNNING' if redis_running else 'STOPPED'}"
            )
            print()

    print(f"Total Clients: {len(clients)}")
    print("=" * 60)


if __name__ == "__main__":
    main()
