import requests
from urllib.parse import urlparse
import xml.etree.ElementTree as ET
from .abc import Harvester, Parser

class Re3DataParser(Parser):
    """
    A parser for processing XML data from the re3data.org API.
    """
    def __init__(self, raw_data):
        super().__init__(raw_data)
        self.ns = {'r3d': 'http://www.re3data.org/schema/2-2'}

    def parse(self):
        """
        Parses the re3data XML and populates the metadata dictionary.
        """
        try:
            repo_root = ET.fromstring(self.raw_data)
            self.metadata = self._parse_record(repo_root)
        except ET.ParseError as e:
            print(f"Error parsing re3data XML: {e}")

    def _parse_record(self, repo_root):
        """
        Parses the main re3data XML record.
        """
        def find_text(element, path):
            el = element.find(path, self.ns)
            return el.text.strip() if el is not None and el.text else None

        def find_all_text(element, path):
            return [el.text.strip() for el in element.findall(path, self.ns) if el.text is not None]

        institutions = []
        for el in repo_root.findall('.//r3d:institution', self.ns):
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
        for el in repo_root.findall('.//r3d:policy', self.ns):
            policy = {
                'name': find_text(el, 'r3d:policyName'),
                'url': find_text(el, 'r3d:policyURL')
            }
            policies.append({k: v for k, v in policy.items() if v})
        
        apis = []
        for el in repo_root.findall('.//r3d:api', self.ns):
            api = {
                'type': el.get('apiType'),
                'url': el.text.strip() if el.text else None
            }
            apis.append({k: v for k, v in api.items() if v})

        metadata_standards = []
        for el in repo_root.findall('.//r3d:metadataStandard', self.ns):
            standard = {
                'name': find_text(el, 'r3d:metadataStandardName'),
                'url': find_text(el, 'r3d:metadataStandardURL')
            }
            metadata_standards.append({k: v for k, v in standard.items() if v})

        syndications = []
        for el in repo_root.findall('.//r3d:syndication', self.ns):
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


class Re3DataHarvester(Harvester):
    """
    A harvester for fetching metadata from the re3data.org registry.
    """
    def __init__(self, repository_url):
        super().__init__(repository_url)
        self.re3data_api_url = "https://www.re3data.org/api/v1"

    def harvest(self):
        """
        Harvests metadata from re3data.org by searching for the repository's hostname.
        The harvested metadata is stored in self.metadata.
        """
        print("Harvesting from re3data...")
        repository_hostname = urlparse(self.repository_url).hostname
        if not repository_hostname:
            return

        try:
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
                    re3data_hostname = urlparse(repo_main_url_element.text).hostname
                    if re3data_hostname and re3data_hostname.lower() == repository_hostname.lower():
                        # Delegate parsing to the Re3DataParser
                        parser = Re3DataParser(repo_response.content)
                        parser.parse()
                        self.metadata = parser.metadata
                        # Found the correct record, so we can stop
                        return
        except requests.exceptions.RequestException as e:
            print(f"Error querying re3data API: {e}")
        except ET.ParseError as e:
            print(f"Error parsing XML from re3data: {e}")
