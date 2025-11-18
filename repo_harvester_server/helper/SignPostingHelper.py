import json
import re
from urllib.parse import urlparse, urljoin

import requests
from lxml import html

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
            # services
            if api_link.get('anchor') not in services:
                services[api_link.get('anchor')] = {'endpoint_uri' : api_link.get('anchor'),
                                                    'source': 'fairicat'}
            if api_link.get('rel') == 'service-doc':
                services[api_link.get('anchor')]['conforms_to'] = api_link.get('link')
                if api_link.get('title'):
                    services[api_link.get('anchor')]['title'] = api_link.get('title')
            if api_link.get('rel') == 'service-meta':
                if api_link.get('type'):
                    services[api_link.get('anchor')]['output_format'] = api_link.get('type')
        if services:
            metadata['services'] = list(services.values())
        return metadata

    def get_linksets(self):
        linksets =  self.get_links('linkset')
        return linksets

    def get_api_linksets (self):
        linksets = self.get_links('api-catalog')
        return linksets

    def set_linkset_links(self, linksets):
        links = []
        for linksetlink in linksets:
            if linksetlink.get('type') == 'application/linkset+json':
                response = requests.get(linksetlink.get('link'))
                link_dict = response.json()
                if isinstance(link_dict.get('linkset'), list):
                    for linkset in link_dict.get('linkset'):
                        if isinstance(linkset, dict):
                            print(linkset)
                            for linktype, links in linkset.items():
                                if linktype == "anchor":
                                    anchor = links
                                else:
                                    if not isinstance(links, list):
                                        links = [links]
                                    for link in links:
                                        liksetlink_dict = {
                                            "anchor": anchor,
                                            "link": link.get("href"),
                                            "type": link.get("type"),
                                            "rel": linktype,
                                            "profile": link.get("profile"),
                                            "title": link.get("title"),
                                        }
                                        self.links.append(liksetlink_dict)
                else:
                    print('Unexpected linkset type: ', type(link_dict.get('linkset')))
                break
            elif linksetlink.get('type') == 'application/linkset':
                response = requests.get(linksetlink.get('link'))
                link_string = response.text
                self.links.extend(self.parse_link_string(link_string))
            else:
                print('Unknown Linkset Format', linksetlink.get('type'))

    def set_links(self):
        self.set_html_links()
        self.set_header_links()
        self.set_linkset_links(self.get_linksets())
        self.set_linkset_links(self.get_api_linksets())
        unique_links =list({d["link"]: d for d in self.links}.values())
        self.links = unique_links
        print('LINKS: ', self.links)

    def get_links(self, rel='describedby', type=None):
        if isinstance(rel, str):
            rel = [rel]
        if type is None:
            return  [l for l in self.links if l.get('rel') in rel]
        else:
            if isinstance(type, str):
                type = [type]
            return  [l for l in self.links if l.get('rel') in rel and l.get('type') in type]

    def set_html_links(self):
        if isinstance(self.html, str):
            if self.html:
                try:
                    dom = html.fromstring(self.html.encode("utf8"))
                    links = dom.xpath("/*/head/link")
                    for link in links:
                        href = link.attrib.get("href")
                        rel = link.attrib.get("rel")
                        type = link.attrib.get("type")
                        title = link.attrib.get("title")
                        profile = link.attrib.get("profile")
                        type = str(type).strip().lower()
                        rel = str(rel).strip().lower()
                        # handle relative paths
                        linkparts = urlparse(href)
                        if linkparts.scheme == "":
                            href = urljoin(self.url, href)
                        self.links.append({
                            "anchor": self.url,
                            "link": href,
                            "type": type,
                            "rel": rel,
                            "profile": profile,
                            "title" :title,
                        })
                except Exception as e:
                    print('Signposting detection in HTML Error: ', e)

    def parse_link_string(self, link_str):
        links = []
        if isinstance(link_str, str):
            if 1==1:
            #try:
                for preparsed_link in link_str.split(","):
                    found_type, type_match, anchor_match = None, None, None
                    found_rel, rel_match = None, None
                    found_formats, formats_match = None, None
                    parsed_link = preparsed_link.strip().split(";")
                    found_link = parsed_link[0].strip()
                    link_dict = {"link": found_link[1:-1]}
                    for link_prop in parsed_link[1:]:
                        link_prop = str(link_prop).strip()
                        for attribute_type in ['rel', 'type', 'profile','anchor']:
                            if link_prop.startswith(attribute_type):
                                rel_match = re.search(attribute_type+r'\s*=\s*\"?([^,;"]+)\"?', link_prop)
                                attribute_value = rel_match.group(1)
                                if rel_match:
                                    link_dict[attribute_type] = str(attribute_value).strip().lower()
                                break
                    if link_dict.get('anchor') is None:
                        link_dict['anchor'] = self.url

                    links.append(link_dict)
            #except Exception as e:
                #print('Link detection in Link String Error: ', e, link_str)
        return links

    def set_header_links(self):
        header_link_str = self.headers.get('Link') or self.headers.get('link') or None
        self.links.extend(self.parse_link_string(header_link_str))



