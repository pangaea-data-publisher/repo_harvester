import json
import re
from urllib.parse import urlparse, urljoin

import rdflib
from lxml import html
import requests
from rdflib import RDF, DCAT, SDO, DC, DCTERMS, FOAF

from repo_harvester_server.helper.SignPostingHelper import SignPostingHelper
from repo_harvester_server.helper.MetadataHelper import MetadataHelper


class CatalogMetadataHarvester:
    def __init__(self, catalog_url):
        self.catalog_url = catalog_url
        self.catalog_html = None
        self.signposting_links = []
        self.metadata = {}

    def merge_metadata(self, new_metadata):
        for key, value in new_metadata.items():
            if key not in self.metadata:
                self.metadata[key] = new_metadata[key]

    def harvest(self):
        self.harvest_self_hosted_metadata()
        self.harvest_registry_metadata()

    def harvest_registry_metadata(self, registry='re3data'):
        print()

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
                #embedded
                embedded_jsonld_metadata = metadata_helper.get_embedded_jsonld_metadata(self.catalog_html)
                self.merge_metadata(embedded_jsonld_metadata)
                print('EMBEDDED JSONLD METADATA: ', embedded_jsonld_metadata)
                #linked
                for jsonld_link in signposting_helper.get_links('describedby', 'application/ld+json'):
                    linked_jsonld_metadata = metadata_helper.get_linked_jsonld_metadata(jsonld_link.get('link'))
                    self.merge_metadata(linked_jsonld_metadata)
                    print('LINKED JSONLD METADATA: ',linked_jsonld_metadata)
                #signposting api catalog
                fairicat_metadata = signposting_helper.get_fairicat_metadata()
                self.merge_metadata(fairicat_metadata)
                print('MERGED METADATA: ', json.dumps(self.metadata, indent=4))
        else:
            print('Invalid repo URI', self.catalog_url)



