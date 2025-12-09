import json
import re
from urllib.parse import urlparse, urljoin
import requests
from lxml import etree, html as lxml_html # Renamed html to lxml_html to avoid conflict with rdflib.html
import rdflib
from rdflib import RDF, DCAT, SDO, DC, DCTERMS, FOAF
import logging
import os

#SMA = rdflib.Namespace("http://schema.org/") # This is defined within rdflib.SDO now
VCARD = rdflib.Namespace("http://www.w3.org/2006/vcard/ns#")
# Suppress the specific rdflib warning about URL templates
logging.getLogger('rdflib.term').setLevel(logging.ERROR)


class SignPostingHelper:
    def __init__(self, url , html=None, headers=None):
        self.url = url
        if html is None or headers is None:
            response = requests.get(self.url)
            html = response.text
            headers = response.headers
        self.html = html
        self.headers = headers
        self.links = []
        self.set_links()

    def get_fairicat_metadata(self):
        metadata = {}
        services = {}
        fairicat_api_links = self.get_links(rel=['service-doc', 'service-meta'])
        for api_link in fairicat_api_links:
            if api_link.get('anchor') not in services:
                services[api_link.get('anchor')] = {'endpoint_uri' : api_link.get('anchor'), 'source': 'fairicat'}
            if api_link.get('rel') == 'service-doc':
                services[api_link.get('anchor')]['conforms_to'] = api_link.get('link')
                if api_link.get('title'):
                    services[api_link.get('anchor')]['title'] = api_link.get('title')
            if api_link.get('rel') == 'service-meta':
                services[api_link.get('anchor')]['service_desc'] = api_link.get('link')
                if api_link.get('type'):
                    services[api_link.get('anchor')]['output_format'] = api_link.get('type')
        if services:
            metadata['services'] = list(services.values())
        return metadata

    def get_linksets(self):
        return self.get_links('linkset')

    def get_api_linksets(self):
        return self.get_links('api-catalog')

    def set_linkset_links(self, linksets):
        for linksetlink in linksets:
            try:
                if linksetlink.get('type') == 'application/linkset+json':
                    response = requests.get(linksetlink.get('link'))
                    response.raise_for_status()
                    link_dict = response.json()
                    if isinstance(link_dict.get('linkset'), list):
                        for linkset in link_dict.get('linkset'):
                            if isinstance(linkset, dict):
                                anchor = linkset.get("anchor")
                                for linktype, links in linkset.items():
                                    if linktype != "anchor":
                                        if not isinstance(links, list):
                                            links = [links]
                                        for link in links:
                                            self.links.append({
                                                "anchor": anchor, "link": link.get("href"),
                                                "type": link.get("type"), "rel": linktype,
                                                "profile": link.get("profile"), "title": link.get("title"),
                                            })
                elif linksetlink.get('type') == 'application/linkset':
                    response = requests.get(linksetlink.get('link'))
                    response.raise_for_status()
                    self.links.extend(self.parse_link_string(response.text))
            except Exception as e:
                print(f"Error processing linkset {linksetlink.get('link')}: {e}")

    def set_links(self):
        self.set_html_links()
        self.set_header_links()
        self.set_linkset_links(self.get_linksets())
        self.set_linkset_links(self.get_api_linksets())
        unique_links = list({(d["link"], d["rel"]): d for d in self.links}.values())
        self.links = unique_links
        print('LINKS: ', self.links)

    def get_links(self, rel='describedby', type=None):
        if isinstance(rel, str):
            rel = [rel]
        if type is None:
            return [l for l in self.links if l.get('rel') in rel]
        else:
            if isinstance(type, str):
                type = [type]
            return [l for l in self.links if l.get('rel') in rel and l.get('type') in type]

    def set_html_links(self):
        if isinstance(self.html, str) and self.html:
            try:
                dom = lxml_html.fromstring(self.html.encode("utf8"))
                links = dom.xpath("/*/head/link")
                for link in links:
                    href = link.attrib.get("href")
                    rel = link.attrib.get("rel")
                    type = link.attrib.get("type")
                    title = link.attrib.get("title")
                    profile = link.attrib.get("profile")
                    linkparts = urlparse(href)
                    if not linkparts.scheme:
                        href = urljoin(self.url, href)
                    self.links.append({
                        "anchor": self.url, "link": href, "type": str(type).strip().lower() if type else None,
                        "rel": str(rel).strip().lower() if rel else None, "profile": profile, "title": title,
                    })
            except Exception as e:
                print('Signposting detection in HTML Error: ', e)

    def set_header_links(self):
        header_link_str = self.headers.get('Link') or self.headers.get('link')
        if header_link_str:
            self.links.extend(self.parse_link_string(header_link_str))

    def parse_link_string(self, link_str):
        links = []
        if isinstance(link_str, str):
            for preparsed_link in link_str.split(","):
                link_dict = {}
                parts = preparsed_link.strip().split(";")
                if not parts or not parts[0]: continue
                link_dict["link"] = parts[0].strip().lstrip('<').rstrip('>')
                for part in parts[1:]:
                    match = re.match(r'\s*(\w+)\s*=\s*"?([^"]+)"?', part)
                    if match:
                        key, value = match.groups()
                        link_dict[key] = value.lower()
                if 'anchor' not in link_dict:
                    link_dict['anchor'] = self.url
                links.append(link_dict)
        return links

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
                # print(services) # Removed this print statement to reduce console noise
        return services

    def _get_jsonld_descriptive_metadata(self, jg):
        metadata = {}
        # Iterate over both DCAT.Catalog and SDO.DataCatalog types
        for catalog in list(jg[: RDF.type: DCAT.Catalog]) + list(jg[: RDF.type: SDO.DataCatalog]):
            metadata["resource_type"] = []
            resourcetypes = jg.objects(catalog, RDF.type)
            for resourcetype in resourcetypes:
                metadata["resource_type"].append(str(resourcetype))
            
            # Use DCTERMS.title or SDO.name or FOAF.name
            metadata["title"] = str(
                jg.value(catalog, DCTERMS.title) or
                jg.value(catalog, SDO.name) or jg.value(catalog, FOAF.name) or ''
            )
            # Use DCTERMS.description or SDO.description or SDO.disambiguatingDescription
            metadata["description"] = str(
                jg.value(catalog, DCTERMS.description) or
                jg.value(catalog, SDO.description) or
                jg.value(catalog, SDO.disambiguatingDescription) or ''
            )
            # Use DCTERMS.language or SDO.inLanguage
            metadata["language"] = str(
                jg.value(catalog, DCTERMS.language) or
                jg.value(catalog, SDO.inLanguage) or ''
            )
            metadata["accessterms"] = str(
                # This field was empty in the original, keeping it as is
            )
            # Use SDO.url or FOAF.homepage or DC.identifier
            metadata["url"] = str(
                jg.value(catalog, SDO.url) or
                jg.value(catalog, FOAF.homepage) or
                jg.value(catalog, DC.identifier) or ''
            )
            # Publishers can be from DCTERMS or SDO
            publishers = (list(jg.objects(catalog, DCTERMS.publisher)) or list(
                jg.objects(catalog, SDO.publisher)))
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
        # Iterate over all triples and replace http://schema.org with https://schema.org
        for s, p, o in list(g): # Create a list to iterate over as we modify the graph
            changed = False
            new_s, new_p, new_o = s, p, o

            if isinstance(s, rdflib.URIRef) and str(s).startswith("http://schema.org"):
                new_s = rdflib.URIRef(str(s).replace("http://schema.org", "https://schema.org"))
                changed = True
            if isinstance(p, rdflib.URIRef) and str(p).startswith("http://schema.org"):
                new_p = rdflib.URIRef(str(p).replace("http://schema.org", "https://schema.org"))
                changed = True
            if isinstance(o, rdflib.URIRef) and str(o).startswith("http://schema.org"):
                new_o = rdflib.URIRef(str(o).replace("http://schema.org", "https://schema.org"))
                changed = True
            
            if changed:
                g.remove((s, p, o))
                g.add((new_s, new_p, new_o))
        return g

    def get_jsonld_metadata(self, jstr):
        metadata = {}
        if isinstance(jstr, str):
            cg = rdflib.ConjunctiveGraph()
            jg = cg.parse(data=jstr, format='json-ld')
            jg = self._fix_schemaorg_namespace_jsonld(jg) # Apply the fix
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

    def get_embedded_jsonld_metadata(self, html_content ):
        ejson = None
        metadata = {}
        jsp = r"<script\s+type=\"application\/ld\+json\">(.*?)<\/script>"
        if isinstance(html_content, str):
            try:
                jsr = re.search(jsp, html_content, re.DOTALL)
                if jsr:
                    ejson = jsr[1]
                    json.loads(ejson) # Validate JSON before passing to rdflib
                    metadata = self.get_jsonld_metadata(ejson)
            except Exception as e:
                print('Loading embedded JSON-LD Error: ', e)
        return metadata
