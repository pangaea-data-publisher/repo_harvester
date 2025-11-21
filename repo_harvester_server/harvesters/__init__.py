import json
import requests
from .self_hosted import SignPostingHelper, MetadataHelper
from .re3data import Re3DataHarvester
from .fairsharing import FAIRsharingHarvester

class CatalogMetadataHarvester:
    def __init__(self, catalog_url):
        self.catalog_url = catalog_url
        self.catalog_html = None
        self.signposting_links = []
        self.metadata = {}

    def merge_metadata(self, new_metadata):
        """
        Merges a new metadata dictionary into the main one.
        It does not overwrite existing keys.
        """
        for key, value in new_metadata.items():
            if key not in self.metadata:
                self.metadata[key] = value

    def harvest(self):
        """
        Orchestrates the entire harvesting process.
        """
        self.harvest_self_hosted_metadata()
        self.harvest_registry_metadata()
        print('FINAL MERGED METADATA: ', json.dumps(self.metadata, indent=4))

    def harvest_registry_metadata(self):
        """
        Initializes and runs all registry harvesters.
        """
        # List of registry harvester classes to run
        registry_harvesters = [Re3DataHarvester, FAIRsharingHarvester]

        for harvester_class in registry_harvesters:
            harvester = harvester_class(self.catalog_url)
            harvester.harvest()
            if harvester.metadata:
                # Wrap the metadata in a key named after the harvester's class
                registry_key = harvester_class.__name__.replace("Harvester", "").lower()
                wrapped_metadata = {registry_key: harvester.metadata}
                
                print(f"{registry_key.upper()} METADATA: ", json.dumps(wrapped_metadata, indent=4))
                self.merge_metadata(wrapped_metadata)

    def harvest_self_hosted_metadata(self):
        """
        Harvests metadata from the repository's own website (signposting, embedded JSON-LD, etc.).
        """
        if not str(self.catalog_url).startswith('http'):
            print('Invalid repo URI', self.catalog_url)
            return

        try:
            response = requests.get(self.catalog_url)
            response.raise_for_status()
            self.catalog_html = response.text
            self.catalog_header = response.headers
        except requests.exceptions.RequestException as e:
            print(f"Could not fetch catalog URL {self.catalog_url}: {e}")
            return

        signposting_helper = SignPostingHelper(self.catalog_url, self.catalog_html, self.catalog_header)
        metadata_helper = MetadataHelper()
        
        # 1. Harvest from standard HTML meta tags (as a fallback)
        html_meta_metadata = metadata_helper.get_html_meta_tags_metadata(self.catalog_html)
        self.merge_metadata(html_meta_metadata)
        print('HTML META TAG METADATA: ', html_meta_metadata)

        # 2. Harvest embedded JSON-LD
        embedded_jsonld_metadata = metadata_helper.get_embedded_jsonld_metadata(self.catalog_html)
        self.merge_metadata(embedded_jsonld_metadata)
        print('EMBEDDED JSONLD METADATA: ', embedded_jsonld_metadata)

        # 3. Harvest linked JSON-LD
        for jsonld_link in signposting_helper.get_links('describedby', 'application/ld+json'):
            linked_jsonld_metadata = metadata_helper.get_linked_jsonld_metadata(jsonld_link.get('link'))
            self.merge_metadata(linked_jsonld_metadata)
            print('LINKED JSONLD METADATA: ', linked_jsonld_metadata)

        # 4. Harvest from FAIRiCat endpoint
        fairicat_metadata = signposting_helper.get_fairicat_metadata()
        self.merge_metadata(fairicat_metadata)
