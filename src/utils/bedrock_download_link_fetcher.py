import requests
import re

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
        r = requests.get(API_URL, headers=headers, timeout=TIMEOUT)
        r.raise_for_status()
        data = r.json()
        return data
    
    @staticmethod
    def _find_dicts_with_value(obj, target_value):
        if isinstance(obj, dict):
            # If this dict has the target value, return the download link
            value = obj.get(TYPE_KEY)
            if value == target_value:
                return obj.get(URL_KEY)
            # Otherwise, recurse into its values
            for item in obj.values():
                return BedrockDownloadLinksFetcher._find_dicts_with_value(item, target_value)
        elif isinstance(obj, list):
            # Recurse into list elements
            for item in obj:
                return BedrockDownloadLinksFetcher._find_dicts_with_value(item, target_value)
    
    @staticmethod
    def check_for_update(current_version: str, download_type: str):
        """
        Checks for an update and returns the download link and version if available.
        Args:
            current_version (str): The current version of the Bedrock server.
            download_type (str): The type of download to look for (e.g., "BEDROCK_SERVER").
        Returns:
            tuple: A tuple containing the latest version (str) and download link (str) if an update is available, otherwise (None, None).
        """
        data = BedrockDownloadLinksFetcher._fetch_links()
        link = BedrockDownloadLinksFetcher._find_dicts_with_value(data, download_type)
        match = re.search(r"bedrock-server-([0-9.]+)\.zip", link)
        if match:
            latest_version = match.group(1)
            if latest_version != current_version:
                return latest_version, link
        return None, None