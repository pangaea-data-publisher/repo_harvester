import json
import re
from urllib.parse import urlparse, urljoin

import rdflib
from lxml import html
import requests
from rdflib import RDF, DCAT, SDO, DC, DCTERMS, FOAF

from repo_harvester_server.helper.SignPostingHelper import SignPostingHelper
from repo_harvester_server.helper.MetadataHelper import MetadataHelper
from repo_harvester_server.helper.RegistryHarvester import RegistryHarvester


class CatalogMetadataHarvester:
    def __init__(self, catalog_url):
        self.catalog_url = catalog_url
        self.catalog_html = None
        self.signposting_links = []
        self.metadata = {}
        self.registry_harvester = RegistryHarvester()

    def merge_metadata(self, new_metadata):
        if new_metadata:
            for key, value in new_metadata.items():
                if key not in self.metadata:
                    self.metadata[key] = new_metadata[key]

    def harvest(self):
        self.harvest_self_hosted_metadata()
        self.harvest_registry_metadata()
        print('FINAL MERGED METADATA: ', json.dumps(self.metadata, indent=4))


    def harvest_registry_metadata(self):
        """
        Harvests metadata from external registries, prints them individually, and merges them.
        """
        registry_metadata = self.registry_harvester.harvest(self.catalog_url)
        
        if registry_metadata.get('re3data'):
            re3data_meta = {'re3data': registry_metadata.get('re3data')}
            print('RE3DATA METADATA: ', json.dumps(re3data_meta, indent=4))
            self.merge_metadata(re3data_meta)

        if registry_metadata.get('fairsharing'):
            fairsharing_meta = {'fairsharing': registry_metadata.get('fairsharing')}
            print('FAIRSHARING METADATA: ', json.dumps(fairsharing_meta, indent=4))
            self.merge_metadata(fairsharing_meta)


    def harvest_self_hosted_metadata(self):
        # TODO: add browser like Agent info
        if str(self.catalog_url).startswith('http'):
            # try:
            if 1 == 1:
                response = requests.get(self.catalog_url)
                self.catalog_html = response.text
                self.catalog_header = response.headers
                signposting_helper = SignPostingHelper(self.catalog_url, self.catalog_html, self.catalog_header)
                metadata_helper = MetadataHelper()
                self.signposting_links = signposting_helper.links
                
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
                    print('LINKED JSONLD METADATA: ',linked_jsonld_metadata)

                # 4. Harvest from FAIRiCat endpoint
                fairicat_metadata = signposting_helper.get_fairicat_metadata()
                self.merge_metadata(fairicat_metadata)
        else:
            print('Invalid repo URI', self.catalog_url)
