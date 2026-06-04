import sys
import os
import shutil
from typing import Any

# Detect if running as packaged executable (frozen) or in development mode
IS_FROZEN = getattr(sys, "frozen", False)
BUNDLE_DIR = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))

if IS_FROZEN:
    app_data = os.environ.get("LOCALAPPDATA")
    if app_data:
        USER_DATA_DIR = os.path.join(app_data, "OracleOS")
    else:
        USER_DATA_DIR = os.path.join(os.path.expanduser("~"), ".oracle_bot")
    os.makedirs(USER_DATA_DIR, exist_ok=True)
else:
    USER_DATA_DIR = os.path.dirname(os.path.abspath(__file__))

DEFAULT_PROFILE = "options.ini"
optionsFilePath = os.path.join(USER_DATA_DIR, DEFAULT_PROFILE)

# Check for custom .ini in command line arguments
for arg in sys.argv[1:]:
    if arg.endswith(".ini"):
        # Resolve target path relative to USER_DATA_DIR if not absolute
        if os.path.isabs(arg):
            target_path = arg
        else:
            target_path = os.path.join(USER_DATA_DIR, os.path.basename(arg))
            
        if os.path.exists(target_path):
            optionsFilePath = target_path
            break
        else:
            print(f"Warning: Configuration file '{arg}' not found. Using default.")

# Auto-initialize default options.ini in USER_DATA_DIR if missing
if not os.path.exists(os.path.join(USER_DATA_DIR, DEFAULT_PROFILE)):
    example_src = os.path.join(BUNDLE_DIR, "options_example.ini")
    if os.path.exists(example_src):
        try:
            shutil.copy2(example_src, os.path.join(USER_DATA_DIR, DEFAULT_PROFILE))
        except Exception:
            pass
    else:
        try:
            with open(os.path.join(USER_DATA_DIR, DEFAULT_PROFILE), "w", encoding="utf-8") as f:
                f.write("# Oracle configuration\n")
        except Exception:
            pass


def normalize_profile_name(profile: str | None) -> str:
    if not profile:
        return DEFAULT_PROFILE

    profile_name = os.path.basename(str(profile).strip())
    if not profile_name:
        return DEFAULT_PROFILE

    if not profile_name.endswith(".ini"):
        profile_name = f"{profile_name}.ini"

    return profile_name


def resolve_profile_path(profile: str | None = None, base_dir: str | None = None, ensure_exists: bool = True) -> str:
    root = os.path.abspath(base_dir or USER_DATA_DIR)
    profile_name = normalize_profile_name(profile)
    target = os.path.abspath(os.path.join(root, profile_name))

    if os.path.commonpath([root, target]) != root:
        raise ValueError("Invalid profile path")

    if ensure_exists and not os.path.exists(target):
        if profile_name == DEFAULT_PROFILE:
            example_src = os.path.join(BUNDLE_DIR, "options_example.ini")
            if os.path.exists(example_src):
                try:
                    shutil.copy2(example_src, target)
                except Exception:
                    pass
            else:
                with open(target, "w", encoding="utf-8") as f:
                    f.write("# Oracle configuration\n")
        else:
            raise FileNotFoundError(f"Profile not found: {profile_name}")

    return target


def importData(filePath=None):
    if filePath is None:
        filePath = optionsFilePath
    retList = {}
    with open(filePath, "r", encoding="utf-8") as optionsFile:
        optionsData = optionsFile.read().splitlines()
    for line in optionsData:
        if "=" in line:
            option, value = line.split("=", 1)
            retList[option.strip()] = value.strip()
    
    return retList


def editData(option, value, filePath=None):
    if filePath is None:
        filePath = optionsFilePath
    newOptionsData = ""
    with open(filePath, "r", encoding="utf-8") as optionsFile:
        optionsData = optionsFile.read()
    
    found = False
    for line in optionsData.splitlines():
        if "=" in line:
            key = line.split("=", 1)[0].strip()
            if key == option:
                newOptionsData += f"{option}={value}\n"
                found = True
                continue
        newOptionsData += line + "\n"
    
    if not found:
        newOptionsData += f"{option}={value}\n"
        
    with open(filePath, "w", encoding="utf-8") as optionsFile:
        optionsFile.write(newOptionsData)


def import_profile_data(profile: str | None = None, base_dir: str | None = None):
    file_path = resolve_profile_path(profile=profile, base_dir=base_dir, ensure_exists=True)
    return importData(filePath=file_path)


def _to_ini_string(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return ""
    return str(value)


def edit_many_data(settings: dict[str, Any], filePath=None):
    if filePath is None:
        filePath = optionsFilePath
    with open(filePath, "r", encoding="utf-8") as optionsFile:
        existing_lines = optionsFile.read().splitlines()

    pending = {str(key).strip(): _to_ini_string(value) for key, value in settings.items() if str(key).strip()}
    seen_keys = set()
    output_lines = []

    for line in existing_lines:
        stripped = line.strip()
        if stripped.startswith("#") or "=" not in line:
            output_lines.append(line)
            continue

        key = line.split("=", 1)[0].strip()
        if key in pending:
            output_lines.append(f"{key}={pending[key]}")
            seen_keys.add(key)
            continue

        output_lines.append(line)

    for key, value in pending.items():
        if key not in seen_keys:
            output_lines.append(f"{key}={value}")

    new_content = "\n".join(output_lines).rstrip("\n") + "\n"
    with open(filePath, "w", encoding="utf-8") as optionsFile:
        optionsFile.write(new_content)


def edit_profile_data(settings: dict[str, Any], profile: str | None = None, base_dir: str | None = None):
    file_path = resolve_profile_path(profile=profile, base_dir=base_dir, ensure_exists=True)
    edit_many_data(settings=settings, filePath=file_path)
