import json
import re
from urllib.parse import urlparse, urljoin
import requests
from lxml import etree, html
import rdflib
from rdflib import RDF, DCAT, SDO, DC, DCTERMS, FOAF
import logging
import os

# Suppress the specific rdflib warning about URL templates
logging.getLogger('rdflib.term').setLevel(logging.ERROR)
VCARD = rdflib.Namespace("http://www.w3.org/2006/vcard/ns#")

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

    def get_links(self, rel='describedby', type=None):
        if isinstance(rel, str):
            rel = [rel]
        if type is None:
            return [l for l in self.links if l.get('rel') in rel]
        else:
            if isinstance(type, str):
                type = [type]
            return [l for l in self.links if l.get('rel') in rel and l.get('type') in type]

    def set_links(self):
        self.set_html_links()
        self.set_header_links()
        unique_links = list({d["link"]: d for d in self.links}.values())
        self.links = unique_links
        print('LINKS: ', self.links)

    def set_html_links(self):
        if isinstance(self.html, str) and self.html:
            try:
                dom = html.fromstring(self.html.encode("utf8"))
                links = dom.xpath("/*/head/link")
                for link in links:
                    href = link.attrib.get("href")
                    rel = link.attrib.get("rel")
                    type = link.attrib.get("type")
                    title = link.attrib.get("title")
                    profile = link.attrib.get("profile")
                    # handle relative paths
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
        harvester_dir = os.path.dirname(os.path.abspath(__file__))
        self.xslt_path = os.path.normpath(os.path.join(harvester_dir, '..', 'xslt', 'rdf2json.xslt'))

    def get_html_meta_tags_metadata(self, html_content):
        metadata = {}
        if not isinstance(html_content, str) or not html_content:
            return metadata
        try:
            doc = html.fromstring(html_content)
            description = doc.xpath('//meta[@name="description"]/@content')
            if description:
                metadata['description'] = description[0].strip()
            keywords = doc.xpath('//meta[@name="keywords"]/@content')
            if keywords:
                metadata['keywords'] = [k.strip() for k in keywords[0].split(',')]
            author = doc.xpath('//meta[@name="author"]/@content')
            if author:
                metadata['publisher'] = [author[0].strip()]
        except Exception as e:
            print(f"Error parsing HTML meta tags: {e}")
        return {k: v for k, v in metadata.items() if v}

    def get_jsonld_metadata(self, jstr):
        metadata = {}
        if not isinstance(jstr, str):
            print('Expecting JSON-LD string not: ', type(jstr))
            return metadata
        try:
            cg = rdflib.ConjunctiveGraph()
            jg = cg.parse(data=jstr, format='json-ld')
            
            rdf_xml = jg.serialize(format='pretty-xml')
            rdf_doc = etree.fromstring(rdf_xml.encode('utf-8'))
            xslt_doc = etree.parse(self.xslt_path)
            transform = etree.XSLT(xslt_doc)
            json_result_str = str(transform(rdf_doc))
            metadata = json.loads(json_result_str)
            print('JSON DATA from XSLT: ', metadata)

        except Exception as e:
            print(f"Error processing JSON-LD: {e}")
        return metadata

    def get_linked_jsonld_metadata(self, typed_link):
        metadata = {}
        if 'http' in str(typed_link):
            try:
                response = requests.get(typed_link)
                response.raise_for_status()
                metadata = self.get_jsonld_metadata(response.text)
            except requests.exceptions.RequestException as e:
                print(f"Loading linked JSON-LD Error: {e}")
            except Exception as e:
                print(f"Processing linked JSON-LD Error: {e}")
        return metadata

    def get_embedded_jsonld_metadata(self, html_content):
        metadata = {}
        jsp = r"<script\s+type=\"application\/ld\+json\">(.*?)<\/script>"
        if isinstance(html_content, str):
            try:
                match = re.search(jsp, html_content, re.DOTALL)
                if match:
                    json_str = match.group(1)
                    metadata = self.get_jsonld_metadata(json_str)
            except Exception as e:
                print(f'Loading embedded JSON-LD Error: {e}')
        return metadata
