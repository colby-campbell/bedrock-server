import requests
import re
from dataclasses import dataclass
from .platform import Platform


# Constants
VERSION_REGEX = r"bedrock-server-([0-9.]+)\.zip"
# The default API URL to fetch download links from
API_URL = "https://net-secondary.web.minecraft-services.net/api/v1.0/download/links"
# The default timeout for API requests in seconds
TIMEOUT = 20
# Keys used in the API response's JSON structure
URL_KEY = "downloadUrl"
TYPE_KEY = "downloadType"
WINDOWS_TYPE = "serverBedrockWindows"
LINUX_TYPE = "serverBedrockLinux"


def _fetch_links(url: str = API_URL):
    """
    Fetch the Bedrock server download links from the API.
    Returns:
        dict: The dictionary containing the download links.
    Raises:
        requests.RequestException: If the request fails or the response is invalid.
    """
    headers = {
        # Identify as BedrockUpdater
        "User-Agent": "BedrockUpdater",
        # Only accept json responses
        "Accept": "application/json"
    }
    r = requests.get(url, headers=headers, timeout=TIMEOUT)
    r.raise_for_status()
    data = r.json()
    return data


def _find_dicts_with_value(obj, target_value: str):
    """
    Recursively search for a dictionary with a specific TYPE_KEY value and return its URL_KEY value.
    Args:
        obj (dict | list): The object to search.
        target_value (str): The return value for URL_KEY if TYPE_KEY matches target_value.
    Returns:
        str | None: The download URL if found, else None.
    """
    if isinstance(obj, dict):
        # If the current directory has the target TYPE_KEY value, return its URL_KEY value
        if obj.get(TYPE_KEY) == target_value:
            return obj.get(URL_KEY)
        for item in obj.values():
            found = _find_dicts_with_value(item, target_value)
            if found:
                return found
    # Traverse the list and search each internal item
    elif isinstance(obj, list):
        for item in obj:
            found = _find_dicts_with_value(item, target_value)
            if found:
                return found
    return None

@dataclass
class UpdateInfo:
    """
    Dataclass to hold update information.
    Attributes:
        found (bool): Whether a matching download link was found.
        update_available (bool): Whether an update is available.
        latest_version (str): The latest version string if found.
        download_url (str): The download URL if an update is available.
        error (str): Error message if any error occurred during the check.
    """
    found: bool
    update_available: bool
    latest_version: str = None
    download_url: str = None
    error: str = None


def get_bedrock_update_info(current_version: str, platform: Platform):
    """
    Checks for an update and returns an UpdateInfo object.
    Args:
        current_version (str): The current version of the Bedrock server.
        platform (Platform): The platform for which to check updates.
    Returns:
        UpdateInfo: A dataclass containing update information.
    """
    # Fetch the download links from the API
    try:
        data = _fetch_links()
    except requests.RequestException as e:
        return UpdateInfo(
            found=False,
            update_available=False,
            error=str(e)
        )
    

    
    # Find the download link for the specified type
    match platform:
        case Platform.Linux:
            download_type = LINUX_TYPE
        case Platform.Windows:
            download_type = WINDOWS_TYPE
        case _:
            return UpdateInfo(
                found=False,
                update_available=False,
                error="Unsupported platform specified."
            )

    # Search for the download link in the API response
    link = _find_dicts_with_value(data, download_type)
    if not link:
        return UpdateInfo(
            found=False,
            update_available=False,
            error="No download link matched in the API response."
        )
    
    # Extract the version from the link
    match = re.search(VERSION_REGEX, link)
    if match:
        latest_version = match.group(1)
        if latest_version != current_version:
            # An update is available
            return UpdateInfo(
                found=True,
                update_available=True,
                latest_version=latest_version,
                download_url=link
            )
        else:
            # No update available (already up to date)
            return UpdateInfo(
                found=True,
                update_available=False,
                latest_version=latest_version
            )
    
    # If no version could be extracted
    return UpdateInfo(
        found=False,
        update_available=False,
        error="Could not extract version from download link."
    )