import json
import re
import rdflib
import requests
from rdflib import RDF, DCAT, SDO, DC, DCTERMS, FOAF
from lxml import etree
from lxml import html as lxml_html
import logging
import os

#SMA = rdflib.Namespace("http://schema.org/")
VCARD = rdflib.Namespace("http://www.w3.org/2006/vcard/ns#")
# Suppress the specific rdflib warning about URL templates
logging.getLogger('rdflib.term').setLevel(logging.ERROR)


class MetadataHelper:
    def __init__(self):
        # Get the directory where the current script is located
        helper_dir = os.path.dirname(os.path.abspath(__file__))
        # Construct the absolute path to the xslt file
        self.xslt_path = os.path.normpath(os.path.join(helper_dir, '..', 'xslt', 'rdf2json.xslt'))

    def get_html_meta_tags_metadata(self, html_content):
        """
        Parses standard HTML meta tags (description, keywords, author) from HTML content.
        """
        metadata = {}
        if not isinstance(html_content, str) or not html_content:
            return metadata

        try:
            doc = lxml_html.fromstring(html_content)

            description = doc.xpath('//meta[@name="description"]/@content')
            if description:
                metadata['description'] = description[0].strip()

            keywords = doc.xpath('//meta[@name="keywords"]/@content')
            if keywords:
                # Keywords are often comma-separated
                metadata['keywords'] = [k.strip() for k in keywords[0].split(',')]

            author = doc.xpath('//meta[@name="author"]/@content')
            if author:
                # Assuming the author of the site can be considered a publisher
                metadata['publisher'] = [author[0].strip()]

        except Exception as e:
            print(f"Error parsing HTML meta tags: {e}")

        # Filter out any keys with empty values
        return {k: v for k, v in metadata.items() if v}
    def _is_in_catalog_path(self, g, node):
        """
        Return True if this node or ANY ancestor node upward
        (following any predicate) has rdf:type in target_types.
        """
        target_types = [DCAT.Catalog, SDO.DataCatalog]  # faster membership test
        visited = set()
        def dfs(n):
            # Check if this node has any of the target types
            for t in target_types:
                if (n, RDF.type, t) in g:
                    return True
            # Traverse upward: (?parent, ?p, n)
            for parent, _, _ in g.triples((None, None, n)):
                if parent not in visited:
                    visited.add(parent)
                    if dfs(parent):
                        return True
            return False
        return dfs(node)

    def _get_jsonld_service_metadata(self, g):
        services = []
        for service in list(g[: RDF.type: SDO.Service]) + list(g[: RDF.type: DCAT.DataService]):
            if self._is_in_catalog_path(g, service):
                endpoint_uri = g.value(service, DCAT.endpointURL)
                conforms_to = g.value(service, DCTERMS.conformsTo)
                title = g.value(service, DCTERMS.title)
                endpoint_desc = g.value(service, DCAT.endpointDescription)
                output_format = g.value(service, DCTERMS.format) #DCAT-AP 3.0.0
                service_meta = {'endpoint_uri': str(endpoint_uri), 'conforms_to': str(conforms_to)}
                if endpoint_desc:
                    service_meta['endpoint_desc'] = str(endpoint_desc)
                if title:
                    service_meta['title'] = str(title)
                if output_format:
                    service_meta['output_format'] = str(output_format)
                services.append(service_meta)
                print(services)
        return services

    def _get_jsonld_descriptive_metadata(self, jg):
        metadata = {}
        for catalog in list(jg[: RDF.type: DCAT.Catalog]) + list(jg[: RDF.type: SDO.DataCatalog]) + list(jg[: RDF.type: SDO.DataCatalog]):
            metadata["resource_type"] = []
            resourcetypes = jg.objects(catalog, RDF.type)
            for resourcetype in resourcetypes:
                metadata["resource_type"].append(str(resourcetype))
            metadata["title"] = str(
                jg.value(catalog, DCTERMS.title) or
                jg.value(catalog, SDO.name) or
                jg.value(catalog, FOAF.name) or ''
            )
            metadata["description"] = str(
                jg.value(catalog, DCTERMS.description) or
                jg.value(catalog, SDO.description) or
                jg.value(catalog, SDO.disambiguatingDescription) or ''
            )
            metadata["language"] = str(
                jg.value(catalog, DCTERMS.language) or
                jg.value(catalog, SDO.inLanguage) or ''
            )
            metadata["accessterms"] = str(

            )
            metadata["url"] = str(
                jg.value(catalog, SDO.url) or
                jg.value(catalog) or
                jg.value(catalog, FOAF.homepage) or
                jg.value(catalog, DC.identifier) or ''
            )
            publishers = (list(jg.objects(catalog, DCTERMS.publisher)) or list(jg.objects(catalog, SDO.publisher)))
            metadata["publisher"] = []
            metadata["country"] = []
            for publisher in publishers:
                publisher_name = str(
                    jg.value(publisher, FOAF.name) or
                    jg.value(publisher, SDO.name) or ''
                )
                publisher_address = (
                        jg.value(publisher, SDO.address) or publisher)
                publisher_country = str(
                    jg.value(publisher_address, VCARD['country-name']) or
                    jg.value(publisher_address, SDO.addressCountry)  or ''
                )
                if publisher_country:
                    metadata["country"].append(publisher_country)
                if publisher_name:
                    metadata["publisher"].append(publisher_name)
        return metadata

    def _fix_schemaorg_namespace_jsonld(self, g):
        #See: https://github.com/RDFLib/rdflib/issues/1120
        for s, p, o in g.triples(None):
            changed = False
            new_s = s
            if str(s).startswith("http://schema.org"):
                new_s = rdflib.URIRef(str(s).replace("http", "https"))
                changed = True
            new_p = p
            if str(p).startswith("http://schema.org"):
                new_p = rdflib.URIRef(str(p).replace("http", "https"))
                changed = True
            new_o = o
            if isinstance(o, rdflib.URIRef):
                if str(o).startswith("http://schema.org"):
                    new_o = rdflib.URIRef(str(o).replace("http", "https"))
                    changed = True
            if changed:
                g.remove((s, p, o))
                g.add((new_s, new_p, new_o))
            return g

    def get_jsonld_metadata(self, jstr):
        metadata = {}
        if isinstance(jstr, str):
            # print(jstr[:1000])
            cg = rdflib.ConjunctiveGraph()
            jg = cg.parse(data=jstr, format='json-ld')
            jg = self._fix_schemaorg_namespace_jsonld(jg)
            metadata = self._get_jsonld_descriptive_metadata(jg)
            metadata['services'] = self._get_jsonld_service_metadata(jg)
        else:
            print('Expecting JSON-LD string not: ', type(jstr))
        return metadata

    def get_linked_jsonld_metadata(self, typed_link):
        ljson = None
        metadata = {}
        if 'http' in str(typed_link):
            try:
                ljson = requests.get(typed_link).json()
                ljson = json.dumps(ljson)
                metadata = self.get_jsonld_metadata(ljson)
            except json.JSONDecodeError as je:
                print('Loading malformed linked JSON-LD Error: ', je)
            except Exception as e:
                print('Loading linked JSON-LD Error: ', e)
        return metadata

    def get_embedded_jsonld_metadata(self, html ):
        ejson = None
        metadata = {}
        jsp = r"<script\s+type=\"application\/ld\+json\">(.*?)<\/script>"
        if isinstance(html, str):
            try:
                jsr = re.search(jsp, html, re.DOTALL)
                if jsr:
                    ejson = jsr[1]
                    json.loads(ejson)
                    metadata = self.get_jsonld_metadata(ejson)
            except Exception as e:
                print('Loading embedded JSON-LD Error: ', e)
        return metadata