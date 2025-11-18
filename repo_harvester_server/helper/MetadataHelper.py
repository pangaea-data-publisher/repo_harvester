import json
import re
import rdflib
import requests
from rdflib import RDF, DCAT, SDO, DC, DCTERMS, FOAF
from lxml import etree



class MetadataHelper:
    def __init__(self):
        1==1




    def get_jsonld_metadata(self, jstr):
        metadata = {}
        SMA = rdflib.Namespace("http://schema.org/")
        VCARD = rdflib.Namespace("http://www.w3.org/2006/vcard/ns#")
        if isinstance(jstr, str):
            # print(jstr[:1000])
            cg = rdflib.ConjunctiveGraph()

            jg = cg.parse(data=jstr, format='json-ld')
            cg.bind("sdo", SMA, override=True)
            cg.bind("dcat", DCAT, override=True)
            rdf_xml = cg.default_context.serialize(format='pretty-xml')
            rdf_doc = etree.fromstring(rdf_xml.encode('utf-8'))
            xslt_doc = etree.parse("../xslt/rdf2json.xslt")
            transform = etree.XSLT(xslt_doc)
            json_result_str = str(transform(rdf_doc))
            json_data = json.loads(json_result_str)
            print('JSON DATA: ', json_data)
            print('Checking for Catalog entries...')
            # for catalog in list(jg.objects(RDF.type, DCAT.Catalog)) \
            for catalog in list(jg[: RDF.type: DCAT.Catalog]) + list(jg[: RDF.type: SMA.DataCatalog]):

                metadata["resource_type"] = []
                resourcetypes = jg.objects(catalog, RDF.type)
                for resourcetype in resourcetypes:
                    metadata["resource_type"].append(str(resourcetype))
                metadata["title"] = str(
                    jg.value(catalog, DCTERMS.title) or
                    jg.value(catalog, SDO.name) or jg.value(catalog, SMA.name) or
                    jg.value(catalog, FOAF.name) or ''
                )
                metadata["description"] = str(
                    jg.value(catalog, DCTERMS.description) or
                    jg.value(catalog, SDO.description) or jg.value(catalog, SMA.description) or
                    jg.value(catalog, SDO.disambiguatingDescription) or jg.value(catalog,
                                                                                 SMA.disambiguatingDescription) or ''
                )
                metadata["language"] = str(
                    jg.value(catalog, DCTERMS.language) or
                    jg.value(catalog, SDO.inLanguage) or jg.value(catalog, SMA.inLanguage) or ''
                )
                metadata["accessterms"] = str(

                )
                metadata["url"] = str(
                    jg.value(catalog, SDO.url) or jg.value(catalog, SMA.url) or
                    jg.value(catalog) or
                    jg.value(catalog, FOAF.homepage) or
                    jg.value(catalog, DC.identifier) or ''
                )
                publishers = (list(jg.objects(catalog, DCTERMS.publisher)) or list(
                    jg.objects(catalog, SDO.publisher)) or list(jg.objects(catalog, SMA.publisher)))
                metadata["publisher"] = []
                metadata["country"] = []
                for publisher in publishers:
                    publisher_name = str(
                        jg.value(publisher, FOAF.name) or
                        jg.value(publisher, SDO.name) or jg.value(publisher, SMA.name) or ''
                    )
                    publisher_address = (
                                jg.value(publisher, SDO.address) or jg.value(publisher, SMA.address) or publisher)
                    publisher_country = str(
                        jg.value(publisher_address, VCARD['country-name']) or
                        jg.value(publisher_address, SDO.addressCountry) or jg.value(publisher_address,
                                                                                    SMA.addressCountry) or ''
                    )
                    if publisher_country:
                        metadata["country"].append(publisher_country)
                    if publisher_name:
                        metadata["publisher"].append(publisher_name)
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