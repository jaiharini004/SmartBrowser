import os
import json
from typing import Dict, List, Optional


def _first_existing(paths: List[str]) -> Optional[str]:
    for path in paths:
        if path and os.path.exists(path):
            return path
    return None


def _profile_dirs(base_user_data_dir: str) -> List[str]:
    if not base_user_data_dir or not os.path.isdir(base_user_data_dir):
        return []

    allowed_prefixes = ("Default", "Profile ")
    ignored = {"System Profile", "Guest Profile"}

    names: List[str] = []
    for entry in os.listdir(base_user_data_dir):
        full_path = os.path.join(base_user_data_dir, entry)
        if not os.path.isdir(full_path):
            continue
        if entry in ignored:
            continue
        if entry.startswith(allowed_prefixes):
            names.append(entry)

    # Keep stable order: Default first, then Profile 1..N
    names.sort(key=lambda n: (0 if n == "Default" else 1, n))
    return names


def _read_profile_name_map(base_user_data_dir: str) -> Dict[str, str]:
    """
    Read Chromium profile display names from Local State:
    profile.info_cache.<profile_directory>.name
    """
    local_state_path = os.path.join(base_user_data_dir, "Local State")
    if not os.path.exists(local_state_path):
        return {}

    try:
        with open(local_state_path, "r", encoding="utf-8", errors="ignore") as f:
            data = json.load(f)
        info_cache = data.get("profile", {}).get("info_cache", {})
        name_map: Dict[str, str] = {}
        for profile_dir, metadata in info_cache.items():
            display_name = (metadata or {}).get("name")
            if isinstance(display_name, str) and display_name.strip():
                name_map[profile_dir] = display_name.strip()
        return name_map
    except Exception:
        return {}


def _normalize_manual_profile_path(manual_user_data_dir: Optional[str]) -> Dict[str, Optional[str]]:
    raw_value = (manual_user_data_dir or "").strip()
    if not raw_value:
        return {"user_data_dir": None, "profile_directory": None}

    normalized = os.path.normpath(raw_value)
    base_name = os.path.basename(normalized)
    parent = os.path.dirname(normalized)

    if base_name == "Default" or base_name.startswith("Profile "):
        local_state_path = os.path.join(parent, "Local State")
        if os.path.exists(local_state_path):
            return {
                "user_data_dir": parent,
                "profile_directory": base_name,
            }

    return {
        "user_data_dir": normalized,
        "profile_directory": None,
    }


def discover_browser_profiles() -> List[Dict[str, str]]:
    """
    Return launchable browser profile presets with label/user_data_dir/binary_path.
    This intentionally focuses on Chromium-based Chrome/Edge profiles.
    """
    local_appdata = os.getenv("LOCALAPPDATA", "")
    program_files = os.getenv("ProgramFiles", "")
    program_files_x86 = os.getenv("ProgramFiles(x86)", "")

    chrome_user_data = os.path.join(local_appdata, "Google", "Chrome", "User Data")
    edge_user_data = os.path.join(local_appdata, "Microsoft", "Edge", "User Data")

    chrome_binary = _first_existing([
        os.path.join(program_files, "Google", "Chrome", "Application", "chrome.exe"),
        os.path.join(program_files_x86, "Google", "Chrome", "Application", "chrome.exe"),
        os.path.join(local_appdata, "Google", "Chrome", "Application", "chrome.exe"),
    ])
    edge_binary = _first_existing([
        os.path.join(program_files_x86, "Microsoft", "Edge", "Application", "msedge.exe"),
        os.path.join(program_files, "Microsoft", "Edge", "Application", "msedge.exe"),
        os.path.join(local_appdata, "Microsoft", "Edge", "Application", "msedge.exe"),
    ])

    presets: List[Dict[str, str]] = []

    chrome_name_map = _read_profile_name_map(chrome_user_data)
    edge_name_map = _read_profile_name_map(edge_user_data)

    for profile_name in _profile_dirs(chrome_user_data):
        display_name = chrome_name_map.get(profile_name, profile_name)
        presets.append(
            {
                "label": f"Chrome - {display_name}",
                "user_data_dir": chrome_user_data,
                "profile_directory": profile_name,
                "binary_path": chrome_binary or "",
            }
        )

    for profile_name in _profile_dirs(edge_user_data):
        display_name = edge_name_map.get(profile_name, profile_name)
        presets.append(
            {
                "label": f"Edge - {display_name}",
                "user_data_dir": edge_user_data,
                "profile_directory": profile_name,
                "binary_path": edge_binary or "",
            }
        )

    return presets


def resolve_profile_selection(
        profile_label: Optional[str],
        manual_user_data_dir: Optional[str],
        manual_binary_path: Optional[str],
) -> Dict[str, Optional[str]]:
    """
    Resolve the final launch paths from profile dropdown + manual overrides.

    Manual values always win; dropdown presets only fill missing values.
    """
    manual_resolution = _normalize_manual_profile_path(manual_user_data_dir)
    chosen_user_data = manual_resolution["user_data_dir"]
    chosen_profile_directory = manual_resolution["profile_directory"]
    chosen_binary = (manual_binary_path or "").strip() or None

    if not profile_label or profile_label == "Custom (manual path)":
        return {
            "user_data_dir": chosen_user_data,
            "profile_directory": chosen_profile_directory,
            "binary_path": chosen_binary,
        }

    for preset in discover_browser_profiles():
        if preset["label"] == profile_label:
            return {
                "user_data_dir": chosen_user_data or preset["user_data_dir"],
                "profile_directory": chosen_profile_directory or preset.get("profile_directory"),
                "binary_path": chosen_binary or (preset["binary_path"] or None),
            }

    return {
        "user_data_dir": chosen_user_data,
        "profile_directory": chosen_profile_directory,
        "binary_path": chosen_binary,
    }