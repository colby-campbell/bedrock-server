import requests
import re
from dataclasses import dataclass

# Constants
# The default API URL to fetch download links from
API_URL = "https://net-secondary.web.minecraft-services.net/api/v1.0/download/links"
# The default timeout for API requests in seconds
TIMEOUT = 20
# Keys used in the API response's JSON structure
URL_KEY = "downloadUrl"
TYPE_KEY = "downloadType"
# Regex pattern to extract the Bedrock server version from the download link
VERSION_REGEX = r"bedrock-server-([0-9.]+)\.zip"


class BedrockDownloadLinksFetcher:
    @staticmethod
    def _fetch_links(url: str = API_URL):
        """
        Fetch the Bedrock server download links from the API.
        Returns:
            dict: The dictionary containing the download links.
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
    
    @staticmethod
    def _find_dicts_with_value(obj, target_value: str):
        """Recursively search for a dictionary with a specific TYPE_KEY value and return its URL_KEY value."""
        # Traverse entire structure to find first dict with matching TYPE_KEY
        if isinstance(obj, dict):
            if obj.get(TYPE_KEY) == target_value:
                return obj.get(URL_KEY)
            for item in obj.values():
                found = BedrockDownloadLinksFetcher._find_dicts_with_value(item, target_value)
                if found:
                    return found
        elif isinstance(obj, list):
            for item in obj:
                found = BedrockDownloadLinksFetcher._find_dicts_with_value(item, target_value)
                if found:
                    return found
        return None

    @dataclass
    class UpdateInfo:
        """Dataclass to hold update information."""
        found: bool
        update_available: bool
        latest_version: str = None
        download_url: str = None
        error: str = None
    
    @staticmethod
    def check_for_update(current_version: str, download_type: str):
        """
        Checks for an update and returns the download link and version if available.
        Args:
            current_version (str): The current version of the Bedrock server.
            download_type (str): The type of download to look for.
        Returns:
            UpdateInfo: A dataclass containing update information.
        """
        # Fetch the download links from the API
        try:
            data = BedrockDownloadLinksFetcher._fetch_links()
        except requests.RequestException as e:
            return BedrockDownloadLinksFetcher.UpdateInfo(found=False, update_available=False, error=e)
        # Find the download link for the specified type
        link = BedrockDownloadLinksFetcher._find_dicts_with_value(data, download_type)
        if not link:
            return BedrockDownloadLinksFetcher.UpdateInfo(found=False, update_available=False, error="No download link matched in the API response.")
        # Extract the version from the link
        match = re.search(VERSION_REGEX, link)
        if match:
            latest_version = match.group(1)
            if latest_version != current_version:
                # An update is available
                return BedrockDownloadLinksFetcher.UpdateInfo(found=True, update_available=True, latest_version=latest_version, download_url=link)
            else:
                # No update available (already up to date)
                return BedrockDownloadLinksFetcher.UpdateInfo(found=True, update_available=False, latest_version=latest_version)
        # If no version could be extracted
        return BedrockDownloadLinksFetcher.UpdateInfo(found=False, update_available=False, error="Could not extract version from download link.")