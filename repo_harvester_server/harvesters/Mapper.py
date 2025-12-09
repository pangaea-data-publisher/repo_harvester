import json

class Mapper:
    """
    Transforms the harvested, namespaced metadata into the final,
    flat RepositoryInfo structure required by the API.
    """
    def __init__(self, harvested_data):
        self.harvested_data = harvested_data
        self.repository_info = {}

    def map(self):
        """
        Performs the mapping and reconciliation logic.
        """
        self.repository_info['repoURI'] = self._get_best_url()
        self.repository_info['re3dataID'] = self.harvested_data.get('re3data', {}).get('re3data_id')

        # The following methods contain the core reconciliation logic
        # that should be reviewed and adjusted based on business requirements.
        self.repository_info['metadata'] = self._map_metadata()
        self.repository_info['services'] = self._map_services()
        self.repository_info['policies'] = self._map_policies()

        return self.repository_info

    def _get_best_url(self):
        """
        Selects the best, most canonical URL from the available sources.
        
        ASSUMPTION: The priority for the URL is:
        1. re3data URL
        2. FAIRsharing homepage
        3. Self-hosted metadata URL
        This is based on the idea that curated registries are more authoritative.
        """
        re3data = self.harvested_data.get('re3data', {})
        fairsharing = self.harvested_data.get('fairsharing', {})
        
        # Prioritize re3data as the most authoritative source
        if re3data.get('url'):
            return re3data.get('url')
        
        # Fallback to FAIRsharing
        if fairsharing.get('homepage'):
            return fairsharing.get('homepage')
            
        # Final fallback to the self-hosted metadata
        return self.harvested_data.get('url', '')

    def _map_metadata(self):
        """
        Merges descriptive metadata from all sources into a single object.

        ASSUMPTION: For fields like 'description' and 'keywords', we are
        prioritizing the richer data from the registries (re3data, then FAIRsharing)
        over the self-hosted metadata. For lists like 'keywords', we will
        combine and deduplicate them.
        """
        re3data = self.harvested_data.get('re3data', {})
        fairsharing = self.harvested_data.get('fairsharing', {})
        
        # Combine keywords from all sources and remove duplicates
        all_keywords = set(re3data.get('keywords', []))
        all_keywords.update(fairsharing.get('keywords', []))
        all_keywords.update(self.harvested_data.get('keywords', []))

        # Logic to select the best description
        description = (
            re3data.get('description') or
            fairsharing.get('description') or
            self.harvested_data.get('description') or
            ""
        )

        return {
            'name': re3data.get('name') or fairsharing.get('name') or self.harvested_data.get('name', ''),
            'description': description,
            'keywords': list(all_keywords),
            # ... other metadata fields would be mapped here ...
        }

    def _map_services(self):
        """
        Combines service information from all sources.

        ASSUMPTION: For now, we are just taking the services found in the
        self-hosted metadata (from JSON-LD). We may need to merge this
        with API information found in re3data or FAIRsharing in the future.
        """
        return self.harvested_data.get('services', [])

    def _map_policies(self):
        """
        Combines policy information from all sources.

        ASSUMPTION: We are prioritizing the structured policy information
        from re3data. This is a good starting point for creating a
        unified policy view.
        """
        return self.harvested_data.get('re3data', {}).get('policies', [])
