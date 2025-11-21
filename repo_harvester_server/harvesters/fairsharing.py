import requests
from urllib.parse import urlparse
import os
import json
from .abc import Harvester, Authenticator, Parser

class FAIRsharingAuthenticator(Authenticator):
    """
    An authenticator for FAIRsharing.org that uses JWT for authentication.
    """
    def __init__(self):
        self.fairsharing_api_url = "https://api.fairsharing.org"
        self.jwt_token = None
        self._authenticate()

    def _authenticate(self):
        """
        Authenticates with the FAIRsharing API to get a JWT.
        """
        username = os.environ.get('FAIRSHARING_USERNAME')
        password = os.environ.get('FAIRSHARING_PASSWORD')

        if not username or not password:
            print("FAIRsharing credentials not found in environment variables.")
            return

        url = f"{self.fairsharing_api_url}/users/sign_in"
        payload = {"user": {"login": username, "password": password}}
        headers = {'Accept': 'application/json', 'Content-Type': 'application/json'}

        try:
            response = requests.post(url, headers=headers, data=json.dumps(payload))
            response.raise_for_status()
            data = response.json()
            self.jwt_token = data.get('jwt')
            if self.jwt_token:
                print("Successfully authenticated with FAIRsharing.")
        except requests.exceptions.RequestException as e:
            print(f"Failed to authenticate with FAIRsharing: {e}")

    def get_auth_headers(self):
        """
        Returns the authorization headers needed for FAIRsharing API requests.
        """
        if self.jwt_token:
            return {
                'Accept': 'application/json',
                'Content-Type': 'application/json',
                'Authorization': f"Bearer {self.jwt_token}"
            }
        return None

class FAIRsharingParser(Parser):
    """
    A parser for processing JSON data from the FAIRsharing.org API.
    """
    def __init__(self, raw_data, repository_hostname):
        super().__init__(raw_data)
        self.repository_hostname = repository_hostname

    def parse(self):
        """
        Parses the FAIRsharing JSON search results and populates the metadata dictionary.
        """
        matching_results = []
        normalized_repo_hostname = self.repository_hostname.lower().replace('www.', '', 1)
        
        for result in self.raw_data:
            attributes = result.get('attributes', {})
            homepage = attributes.get('homepage')
            if not homepage: continue

            try:
                fairsharing_hostname = urlparse(homepage).hostname
                if fairsharing_hostname:
                    normalized_fairsharing_hostname = fairsharing_hostname.lower().replace('www.', '', 1)
                    if normalized_fairsharing_hostname == normalized_repo_hostname:
                        matching_results.append(result)
            except Exception:
                continue
        
        if not matching_results:
            return

        active_result = None
        # First pass: look for a 'Ready' record
        for result in matching_results:
            if result.get('attributes', {}).get('status') == 'ready':
                active_result = result
                break
        
        # Second pass (if no 'Ready' one was found): look for the first non-deprecated one
        if not active_result:
            for result in matching_results:
                if result.get('attributes', {}).get('status') != 'deprecated':
                    active_result = result
                    break
        
        if not active_result:
            print(f"Found {len(matching_results)} match(es) on FAIRsharing for {self.repository_hostname}, but none were active or ready.")
            return

        attributes = active_result.get('attributes', {})
        self.metadata = {
            'name': attributes.get('name'),
            'homepage': attributes.get('homepage'),
            'description': attributes.get('description'),
            'keywords': attributes.get('keywords'),
            'fairsharing_id': active_result.get('id')
        }

class FAIRsharingHarvester(Harvester):
    """
    A harvester for fetching metadata from the FAIRsharing.org registry.
    It uses an authenticator to handle API credentials.
    """
    def __init__(self, repository_url):
        super().__init__(repository_url)
        self.fairsharing_api_url = "https://api.fairsharing.org"
        self.authenticator = FAIRsharingAuthenticator()

    def harvest(self):
        """
        Harvests metadata from FAIRsharing.org.
        The harvested metadata is stored in self.metadata.
        """
        auth_headers = self.authenticator.get_auth_headers()
        if not auth_headers:
            print("Skipping FAIRsharing harvesting due to authentication failure.")
            return

        print("Harvesting from FAIRsharing...")
        repository_hostname = urlparse(self.repository_url).hostname
        if not repository_hostname:
            return

        domain_parts = repository_hostname.split('.')
        search_query = domain_parts[-2] if len(domain_parts) > 1 else domain_parts[0]

        search_url = f"{self.fairsharing_api_url}/search/fairsharing_records/"
        payload = {"q": search_query}

        try:
            response = requests.post(search_url, headers=auth_headers, data=json.dumps(payload))
            if response.status_code == 401:
                print("FAIRsharing search failed: 401 Unauthorized. The user may not have permission for this search endpoint.")
                return
            response.raise_for_status()
            results = response.json().get('data', [])
        except requests.exceptions.RequestException as e:
            print(f"Error querying FAIRsharing search API: {e}")
            return
        
        # Delegate parsing to the FAIRsharingParser
        parser = FAIRsharingParser(results, repository_hostname)
        parser.parse()
        self.metadata = parser.metadata
