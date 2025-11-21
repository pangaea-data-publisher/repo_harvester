from repo_harvester_server.harvesters import CatalogMetadataHarvester


#repouri = 'https://doi.pangaea.de/10.1594/PANGAEA.986961'
#repouri = 'https://doi.pangaea.de/'
#repouri = 'https://dummyrepository.org/'

#repouri = 'https://www.pangaea.de/'
repouri = 'https://flybase.org/'

harvester = CatalogMetadataHarvester(repouri)

harvester.harvest()
