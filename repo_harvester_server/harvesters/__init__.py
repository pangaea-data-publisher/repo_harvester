import json
import os
import requests
from .self_hosted import SignPostingHelper, MetadataHelper
from .re3data import Re3DataHarvester
from .fairsharing import FAIRsharingHarvester
from .Mapper import Mapper

class CatalogMetadataHarvester:
    def __init__(self, catalog_url, output_dir=None):
        self.catalog_url = catalog_url
        self.output_dir = output_dir
        self.catalog_html = None
        self.signposting_links = []
        self.metadata = {}

        if self.output_dir:
            os.makedirs(self.output_dir, exist_ok=True)

    def _write_output(self, filename, data):
        """Helper function to write data to a JSON file in the output directory."""
        if self.output_dir and data:
            filepath = os.path.join(self.output_dir, filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)

    def merge_metadata(self, new_metadata):
        """
        Merges a new metadata dictionary into the main one.
        It does not overwrite existing keys, unless the existing value is empty.
        """
        for key, value in new_metadata.items():
            if key not in self.metadata or not self.metadata[key]:
                self.metadata[key] = value

    def harvest(self):
        """
        Orchestrates the entire harvesting process, including the final mapping.
        """
        # 1. Harvest all raw metadata
        self.harvest_self_hosted_metadata()
        self.harvest_registry_metadata()
        
        print('FINAL HARVESTED METADATA: ', json.dumps(self.metadata, indent=4))
        self._write_output('final_harvested_metadata.json', self.metadata)

        # 2. Map the harvested data to the final RepositoryInfo structure
        mapper = Mapper(self.metadata)
        repository_info = mapper.map()

        print('FINAL MAPPED REPOSITORY INFO: ', json.dumps(repository_info, indent=4))
        self._write_output('repository_info.json', repository_info)


    def harvest_registry_metadata(self):
        """
        Initializes and runs all registry harvesters.
        """
        registry_harvesters = [Re3DataHarvester, FAIRsharingHarvester]

        for harvester_class in registry_harvesters:
            harvester = harvester_class(self.catalog_url)
            harvester.harvest()
            if harvester.metadata:
                registry_key = harvester_class.__name__.replace("Harvester", "").lower()
                wrapped_metadata = {registry_key: harvester.metadata}
                
                print(f"{registry_key.upper()} METADATA: ", json.dumps(wrapped_metadata, indent=4))
                self._write_output(f'{registry_key}_metadata.json', wrapped_metadata)
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
        
        html_meta_metadata = metadata_helper.get_html_meta_tags_metadata(self.catalog_html)
        self._write_output('html_meta_metadata.json', html_meta_metadata)
        self.merge_metadata(html_meta_metadata)
        print('HTML META TAG METADATA: ', html_meta_metadata)

        embedded_jsonld_metadata = metadata_helper.get_embedded_jsonld_metadata(self.catalog_html)
        self._write_output('embedded_jsonld_metadata.json', embedded_jsonld_metadata)
        self.merge_metadata(embedded_jsonld_metadata)
        print('EMBEDDED JSONLD METADATA: ', embedded_jsonld_metadata)

        linked_jsonld_metadata = {}
        for i, jsonld_link in enumerate(signposting_helper.get_links('describedby', 'application/ld+json')):
            data = metadata_helper.get_linked_jsonld_metadata(jsonld_link.get('link'))
            linked_jsonld_metadata.update(data)
            self._write_output(f'linked_jsonld_metadata_{i}.json', data)
        self.merge_metadata(linked_jsonld_metadata)
        print('LINKED JSONLD METADATA: ', linked_jsonld_metadata)

        fairicat_metadata = signposting_helper.get_fairicat_metadata()
        self._write_output('fairicat_metadata.json', fairicat_metadata)
        self.merge_metadata(fairicat_metadata)
