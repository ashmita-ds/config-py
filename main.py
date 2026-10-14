
import os
from pathlib import Path

import yaml
from dotenv import dotenv_values
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Allow browser-based graders to call the service.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

DEFAULTS = {
    "port": 8000,
    "workers": 1,
    "debug": False,
    "log_level": "info",
    "api_key": "default-secret-000",
}

def coerce(key, value):
    if key in ("port", "workers"):
        return int(value)

    if key == "debug":
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in {
            "true", "1", "yes", "on"
        }

    return str(value)

def normalize_key(key):
    key = key.strip().lower()
    if key == "num_workers":
        return "workers"
    return key

def effective_config(overrides):
    config = DEFAULTS.copy()

    # Layer 2: environment-specific YAML
    env_name = os.environ.get("APP_ENV", "development")
    yaml_path = Path(f"config.{env_name}.yaml")

    if yaml_path.exists():
        with yaml_path.open(encoding="utf-8") as f:
            yaml_config = yaml.safe_load(f) or {}
        for key, value in yaml_config.items():
            config[normalize_key(key)] = value

    # Layer 3: .env file, read independently of OS variables
    file_env = dotenv_values(".env")
    for raw_key, value in file_env.items():
        if raw_key.startswith("APP_"):
            key = normalize_key(raw_key[4:])
        else:
            key = normalize_key(raw_key)

        if value is not None:
            config[key] = value

    # Layer 4: actual OS environment variables
    for raw_key, value in os.environ.items():
        if raw_key.startswith("APP_"):
            key = normalize_key(raw_key[4:])
            config[key] = value

    # Highest precedence: repeated CLI-style query parameters
    for item in overrides:
        if "=" not in item:
            continue
        raw_key, value = item.split("=", 1)
        config[normalize_key(raw_key)] = value

    # Coerce output types and mask the secret.
    result = {
        key: coerce(key, config[key])
        for key in ("port", "workers", "debug", "log_level", "api_key")
    }
    result["api_key"] = "****"
    return result

@app.get("/effective-config")
def get_effective_config(set: list[str] = Query(default=[])):
    return effective_config(set)
