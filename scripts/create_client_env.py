from pathlib import Path
import secrets

print("\n=== NEW CLIENT SETUP ===\n")

client_slug = input("Client slug (example: client2): ").strip().lower().replace(" ", "_")
brand_name = input("Brand name: ").strip()
admin_brand_name = input("Admin brand name: ").strip()
bot_token = input("Bot token: ").strip()
super_admin_id = input("Owner Telegram ID: ").strip()
postgres_port = input("Postgres port [5433]: ").strip() or "5433"
redis_port = input("Redis port [6380]: ").strip() or "6380"

if not client_slug:
    raise SystemExit("❌ Client slug is required")

if not brand_name:
    raise SystemExit("❌ Brand name is required")

if not bot_token:
    raise SystemExit("❌ Bot token is required")

db_name = f"telegram_vip_{client_slug}"
db_user = f"telegram_vip_{client_slug}"
db_password = secrets.token_urlsafe(24)
compose_project = f"telegram_vip_{client_slug}"

env_content = f"""ENVIRONMENT=development
LOG_LEVEL=INFO

BOT_TOKEN={bot_token}

BOT_MODE=polling
WEBHOOK_BASE_URL=
WEBHOOK_PATH=/telegram/webhook
WEBHOOK_SECRET={secrets.token_urlsafe(32)}

DATABASE_URL=postgresql+asyncpg://{db_user}:{db_password}@localhost:{postgres_port}/{db_name}
REDIS_URL=redis://localhost:{redis_port}/0

SUPER_ADMIN_TELEGRAM_ID={super_admin_id}

BRAND_NAME={brand_name}
ADMIN_BRAND_NAME={admin_brand_name or brand_name + " ADMIN"}

COMPOSE_PROJECT_NAME={compose_project}
POSTGRES_DB={db_name}
POSTGRES_USER={db_user}
POSTGRES_PASSWORD={db_password}
POSTGRES_PORT={postgres_port}
REDIS_PORT={redis_port}
"""

output = Path(f".env.{client_slug}")

if output.exists():
    raise SystemExit(f"❌ {output} already exists")

output.write_text(env_content)

print(f"\n✅ Created {output}")
print("✅ Unique database credentials generated")
print("✅ Client branding configured")
print("\nIMPORTANT: Do not commit this file to Git.")

print("\n=== NEXT COMMANDS ===")
print(f"cp {output} .env")
print("docker compose up -d")
print(".venv/bin/alembic upgrade head")
print(".venv/bin/python scripts/seed_content_screens.py")
print(".venv/bin/python app/main.py")
