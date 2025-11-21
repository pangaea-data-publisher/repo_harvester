#!/usr/bin/env python3

import connexion
from flask import current_app
from repo_harvester_server.harvesters import CatalogMetadataHarvester
#from repo_harvester_server import encoder

def create_app():
    app = connexion.App(__name__, specification_dir='swagger/')
    app.add_api('swagger.yaml', arguments={'title': 'RepoInfoHarvester'}, pythonic_params=True)
    foo = 'bar' # needs to be declared and initialized here
    with app.app.app_context():
        current_app.termtagger = CatalogMetadataHarvester('https://www.pangaea.de')
    return app

def main():
    app = create_app()
    # app.app.jso
    app.run(port=8080)


if __name__ == '__main__':
    main()
