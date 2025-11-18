from repo_harvester_server.helper.RepositoryHarvester import CatalogMetadataHarvester


repouri = 'https://doi.pangaea.de/10.1594/PANGAEA.986961'
repouri = 'https://dummyrepository.org/'

#repouri = 'https://www.pangaea.de/'

harvester = CatalogMetadataHarvester(repouri)

harvester.harvest()