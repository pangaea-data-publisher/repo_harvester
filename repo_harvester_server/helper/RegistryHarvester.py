import requests
from urllib.parse import urlparse
import xml.etree.ElementTree as ET
import re
import os
import json

class RegistryHarvester:
    def __init__(self):
        self.re3data_api_url = "https://www.re3data.org/api/v1"
        self.fairsharing_api_url = "https://api.fairsharing.org"

        # FAIRsharing authentication
        self.fairsharing_jwt = None
        self.fairsharing_username = os.environ.get('FAIRSHARING_USERNAME')
        self.fairsharing_password = os.environ.get('FAIRSHARING_PASSWORD')
        if self.fairsharing_username and self.fairsharing_password:
            self._authenticate_fairsharing()
        else:
            print("FAIRsharing credentials (FAIRSHARING_USERNAME, FAIRSHARING_PASSWORD) not found in environment variables. Skipping FAIRsharing harvesting.")

    def _authenticate_fairsharing(self):
        """
        Authenticates with the FAIRsharing API to get a JWT.
        """
        url = f"{self.fairsharing_api_url}/users/sign_in"
        payload = {"user": {"login": self.fairsharing_username, "password": self.fairsharing_password}}
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        try:
            response = requests.post(url, headers=headers, data=json.dumps(payload))
            response.raise_for_status()
            data = response.json()
            self.fairsharing_jwt = data.get('jwt')
            if self.fairsharing_jwt:
                print("Successfully authenticated with FAIRsharing.")
            else:
                print("FAIRsharing authentication successful, but no JWT token found in response.")
        except requests.exceptions.RequestException as e:
            print(f"Failed to authenticate with FAIRsharing: {e}")
            self.fairsharing_jwt = None

    def harvest(self, repository_url):
        """
        Harvest metadata from registries (re3data, FAIRsharing) for a given repository URL.
        """
        metadata = {}
        hostname = urlparse(repository_url).hostname
        if not hostname:
            return {}

        # Harvest from re3data
        try:
            re3data_metadata = self._harvest_re3data(hostname)
            if re3data_metadata:
                metadata['re3data'] = re3data_metadata
        except Exception as e:
            print(f"Error harvesting from re3data: {e}")

        # Harvest from FAIRsharing
        try:
            fairsharing_metadata = self._harvest_fairsharing(hostname)
            if fairsharing_metadata:
                metadata['fairsharing'] = fairsharing_metadata
        except Exception as e:
            print(f"Error harvesting from FAIRsharing: {e}")
            
        return metadata

    def _harvest_re3data(self, repository_hostname):
        """
        Harvest metadata from re3data.org by searching and verifying the repository URL.
        """
        search_url = f"{self.re3data_api_url}/repositories?query={repository_hostname}"
        response = requests.get(search_url, headers={'Accept': 'application/xml'})
        response.raise_for_status()

        search_root = ET.fromstring(response.content)
        ns = {'r3d': 'http://www.re3data.org/schema/2-2'}

        for repo_id_element in search_root.findall('.//id'):
            repo_id = repo_id_element.text
            
            repo_url = f"{self.re3data_api_url}/repository/{repo_id}"
            repo_response = requests.get(repo_url, headers={'Accept': 'application/xml'})
            
            if repo_response.status_code != 200:
                continue

            repo_root = ET.fromstring(repo_response.content)
            
            repo_main_url_element = repo_root.find('.//r3d:repositoryURL', ns)
            
            if repo_main_url_element is not None and repo_main_url_element.text:
                try:
                    re3data_hostname = urlparse(repo_main_url_element.text).hostname
                    if re3data_hostname and re3data_hostname.lower() == repository_hostname.lower():
                        
                        def find_text(element, path):
                            el = element.find(path, ns)
                            return el.text.strip() if el is not None and el.text else None

                        def find_all_text(element, path):
                            return [el.text.strip() for el in element.findall(path, ns) if el.text is not None]

                        institutions = []
                        for el in repo_root.findall('.//r3d:institution', ns):
                            inst = {
                                'name': find_text(el, 'r3d:institutionName'),
                                'additional_names': find_all_text(el, 'r3d:institutionAdditionalName'),
                                'country': find_text(el, 'r3d:institutionCountry'),
                                'responsibility_types': find_all_text(el, 'r3d:responsibilityType'),
                                'type': find_text(el, 'r3d:institutionType'),
                                'url': find_text(el, 'r3d:institutionURL'),
                                'identifiers': find_all_text(el, 'r3d:institutionIdentifier')
                            }
                            institutions.append({k: v for k, v in inst.items() if v})

                        policies = []
                        for el in repo_root.findall('.//r3d:policy', ns):
                            policy = {
                                'name': find_text(el, 'r3d:policyName'),
                                'url': find_text(el, 'r3d:policyURL')
                            }
                            policies.append({k: v for k, v in policy.items() if v})
                        
                        apis = []
                        for el in repo_root.findall('.//r3d:api', ns):
                            api = {
                                'type': el.get('apiType'),
                                'url': el.text.strip() if el.text else None
                            }
                            apis.append({k: v for k, v in api.items() if v})

                        metadata_standards = []
                        for el in repo_root.findall('.//r3d:metadataStandard', ns):
                            standard = {
                                'name': find_text(el, 'r3d:metadataStandardName'),
                                'url': find_text(el, 'r3d:metadataStandardURL')
                            }
                            metadata_standards.append({k: v for k, v in standard.items() if v})

                        syndications = []
                        for el in repo_root.findall('.//r3d:syndication', ns):
                            syndication = {
                                'type': el.get('syndicationType'),
                                'url': el.text.strip() if el.text else None
                            }
                            syndications.append({k: v for k, v in syndication.items() if v})

                        metadata = {
                            're3data_id': find_text(repo_root, './/r3d:re3data.orgIdentifier'),
                            'name': find_text(repo_root, './/r3d:repositoryName'),
                            'additional_names': find_all_text(repo_root, './/r3d:additionalName'),
                            'url': find_text(repo_root, './/r3d:repositoryURL'),
                            'identifiers': find_all_text(repo_root, './/r3d:repositoryIdentifier'),
                            'description': find_text(repo_root, './/r3d:description'),
                            'contacts': find_all_text(repo_root, './/r3d:repositoryContact'),
                            'types': find_all_text(repo_root, './/r3d:type'),
                            'start_date': find_text(repo_root, './/r3d:startDate'),
                            'languages': find_all_text(repo_root, './/r3d:repositoryLanguage'),
                            'subjects': find_all_text(repo_root, './/r3d:subject'),
                            'mission_statement_url': find_text(repo_root, './/r3d:missionStatementURL'),
                            'content_types': find_all_text(repo_root, './/r3d:contentType'),
                            'provider_types': find_all_text(repo_root, './/r3d:providerType'),
                            'keywords': find_all_text(repo_root, './/r3d:keyword'),
                            'institutions': institutions,
                            'policies': policies,
                            'database_access_type': find_text(repo_root, './/r3d:databaseAccess/r3d:databaseAccessType'),
                            'data_access_type': find_text(repo_root, './/r3d:dataAccess/r3d:dataAccessType'),
                            'data_upload_type': find_text(repo_root, './/r3d:dataUpload/r3d:dataUploadType'),
                            'versioning': find_text(repo_root, './/r3d:versioning'),
                            'pid_systems': find_all_text(repo_root, './/r3d:pidSystem'),
                            'citation_guideline_url': find_text(repo_root, './/r3d:citationGuidelineURL'),
                            'author_id_systems': find_all_text(repo_root, './/r3d:aidSystem'),
                            'quality_management': find_text(repo_root, './/r3d:qualityManagement'),
                            'certificates': find_all_text(repo_root, './/r3d:certificate'),
                            'apis': apis,
                            'metadata_standards': metadata_standards,
                            'syndication': syndications,
                            'remarks': find_text(repo_root, './/r3d:remarks'),
                            'entry_date': find_text(repo_root, './/r3d:entryDate'),
                            'last_update': find_text(repo_root, './/r3d:lastUpdate'),
                        }
                        
                        return {k: v for k, v in metadata.items() if v}

                except Exception as e:
                    print(f"Could not parse XML for re3data repo {repo_id}: {e}")
                    continue
        return None

    def _harvest_fairsharing(self, repository_hostname):
        """
        Harvest metadata from fairsharing.org using the correct search endpoint.
        """
        if not self.fairsharing_jwt:
            return None

        domain_parts = repository_hostname.split('.')
        search_query = domain_parts[-2] if len(domain_parts) > 1 else domain_parts[0]

        # Corrected to use the POST /search/fairsharing_records/ endpoint
        search_url = f"{self.fairsharing_api_url}/search/fairsharing_records/"
        headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Authorization': f"Bearer {self.fairsharing_jwt}"
        }
        payload = {"q": search_query}

        try:
            response = requests.post(search_url, headers=headers, data=json.dumps(payload))
            response.raise_for_status()
            # The response from this endpoint is a list directly
            results = response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error querying FAIRsharing search API: {e}")
            return None

        matching_results = []
        normalized_repo_hostname = repository_hostname.lower().replace('www.', '', 1)
        # The structure of the response from this endpoint might be different.
        # Assuming it's a list of objects, each with an 'attributes' dictionary.
        for result in results:
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
            return None

        active_result = None
        for result in matching_results:
            if result.get('attributes', {}).get('status') == 'ready':
                active_result = result
                break
        
        if not active_result:
            for result in matching_results:
                if result.get('attributes', {}).get('status') != 'deprecated':
                    active_result = result
                    break
        
        if not active_result:
            print(f"Found {len(matching_results)} match(es) on FAIRsharing for {repository_hostname}, but none were active or ready.")
            return None

        attributes = active_result.get('attributes', {})
        metadata = {
            'name': attributes.get('name'),
            'homepage': attributes.get('homepage'),
            'description': attributes.get('description'),
            'keywords': attributes.get('keywords'),
            'fairsharing_id': active_result.get('id')
        }
        return {k: v for k, v in metadata.items() if v}
