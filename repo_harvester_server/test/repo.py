import os
from repo_harvester_server.harvesters import CatalogMetadataHarvester

# Define the repository to be harvested
#repouri = 'https://www.pangaea.de/'
#repouri = 'https://doi.pangaea.de/10.1594/PANGAEA.986961'
repouri = 'https://www.dummyrepository.org/'
#repouri = 'https://flybase.org/'



# Define the output directory for the results
output_dir = os.path.join(os.path.dirname(__file__), 'results')

# Initialize and run the harvester
harvester = CatalogMetadataHarvester(repouri, output_dir=output_dir)
harvester.harvest()
