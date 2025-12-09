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
        self.repository_info['FAIRsharingID'] = self.harvested_data.get('fairsharing', {}).get('fairsharing_id')

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
        self_hosted = self.harvested_data.get('self_hosted', {})
        
        # Combine keywords from all sources and remove duplicates
        all_keywords = set(re3data.get('keywords', []))
        all_keywords.update(fairsharing.get('subjects', [])) # FAIRsharing uses 'subjects' for keywords
        all_keywords.update(fairsharing.get('domains', [])) # FAIRsharing also has 'domains'
        all_keywords.update(self_hosted.get('keywords', []))

        # Logic to select the best description
        description = (
            re3data.get('description') or
            fairsharing.get('description') or
            self_hosted.get('description') or
            ""
        )

        name = (
            re3data.get('name') or
            fairsharing.get('name') or
            self_hosted.get('name') or
            ""
        )

        publisher = list(set(re3data.get('publisher', []) + fairsharing.get('publisher', []) + self_hosted.get('publisher', [])))
        country = list(set(re3data.get('country', []) + fairsharing.get('countries', []) + self_hosted.get('country', [])))
        
        # Combine publications, prioritizing re3data and then fairsharing
        publications = re3data.get('publications', []) + fairsharing.get('publications', [])

        # Combine grants, prioritizing re3data and then fairsharing
        grants = re3data.get('grants', []) + fairsharing.get('grants', [])

        # Combine support links
        support_links = fairsharing.get('support_links', [])

        # Combine cross-references
        cross_references = fairsharing.get('cross_references', [])

        # Combine associated tools
        associated_tools = fairsharing.get('associated_tools', [])

        return {
            'name': name,
            'description': description,
            'keywords': list(all_keywords),
            'url': self._get_best_url(), # Use the canonical URL
            'publisher': publisher,
            'country': country,
            'language': re3data.get('language') or self_hosted.get('language'),
            'resource_type': re3data.get('resource_type') or fairsharing.get('fairsharing_registry') or self_hosted.get('resource_type'),
            'publications': publications,
            'grants': grants,
            'licence_links': fairsharing.get('licence_links', []),
            'object_types': fairsharing.get('object_types', []),
            'internal_identifiers': fairsharing.get('internal_identifiers'),
            'status': fairsharing.get('status'),
            'contacts': fairsharing.get('contacts', []),
            'citations': fairsharing.get('citations', []),
            'identifier': fairsharing.get('identifier'),
            'data_curation': fairsharing.get('data_curation', {}),
            'support_links': support_links,
            'year_creation': fairsharing.get('year_creation'),
            'data_versioning': fairsharing.get('data_versioning'),
            'associated_tools': associated_tools,
            'cross_references': cross_references,
            'data_access_condition': fairsharing.get('data_access_condition', {}),
            'resource_sustainability': fairsharing.get('resource_sustainability', {}),
            'data_contact_information': fairsharing.get('data_contact_information'),
            'data_preservation_policy': fairsharing.get('data_preservation_policy', {}),
            'data_deposition_condition': fairsharing.get('data_deposition_condition', {}),
            'citation_to_related_publications': fairsharing.get('citation_to_related_publications'),
            'data_access_for_pre_publication_review': fairsharing.get('data_access_for_pre_publication_review'),
            'legacy_ids': fairsharing.get('legacy_ids', []),
            'abbreviation': fairsharing.get('abbreviation'),
            'url_for_logo': fairsharing.get('url_for_logo'),
            'exhaustive_licences': fairsharing.get('exhaustive_licences'),
            'record_type': fairsharing.get('record_type'),
            'taxonomies': fairsharing.get('taxonomies', []),
            'linking_records': fairsharing.get('linking_records', []),
            'linked_records': fairsharing.get('linked_records', []),
            'created_at': fairsharing.get('created_at'),
            'updated_at': fairsharing.get('updated_at'),
        }

    def _map_services(self):
        """
        Combines service information from all sources.

        ASSUMPTION: For now, we are just taking the services found in the
        self-hosted metadata (from JSON-LD). We may need to merge this
        with API information found in re3data or FAIRsharing in the future.
        """
        self_hosted_services = self.harvested_data.get('self_hosted', {}).get('services', [])
        fairsharing_services = self.harvested_data.get('fairsharing', {}).get('services', [])
        
        # Simple concatenation for now, more sophisticated merging might be needed
        # based on unique service identifiers or endpoints.
        return self_hosted_services + fairsharing_services

    def _map_policies(self):
        """
        Combines policy information from all sources.

        ASSUMPTION: We are prioritizing the structured policy information
        from re3data. This is a good starting point for creating a
        unified policy view.
        """
        re3data_policies = self.harvested_data.get('re3data', {}).get('policies', [])
        
        # FAIRsharing has policy-related fields under metadata, not a separate 'policies' key
        fairsharing_policies = {}
        if self.harvested_data.get('fairsharing'):
            fs_data_access_condition = self.harvested_data['fairsharing'].get('data_access_condition')
            if fs_data_access_condition:
                fairsharing_policies['data_access_condition'] = fs_data_access_condition
            
            fs_data_deposition_condition = self.harvested_data['fairsharing'].get('data_deposition_condition')
            if fs_data_deposition_condition:
                fairsharing_policies['data_deposition_condition'] = fs_data_deposition_condition
            
            fs_data_preservation_policy = self.harvested_data['fairsharing'].get('data_preservation_policy')
            if fs_data_preservation_policy:
                fairsharing_policies['data_preservation_policy'] = fs_data_preservation_policy
            
            fs_resource_sustainability = self.harvested_data['fairsharing'].get('resource_sustainability')
            if fs_resource_sustainability:
                fairsharing_policies['resource_sustainability'] = fs_resource_sustainability
            
            fs_citation_to_related_publications = self.harvested_data['fairsharing'].get('citation_to_related_publications')
            if fs_citation_to_related_publications:
                fairsharing_policies['citation_to_related_publications'] = fs_citation_to_related_publications
            
            fs_data_access_for_pre_publication_review = self.harvested_data['fairsharing'].get('data_access_for_pre_publication_review')
            if fs_data_access_for_pre_publication_review:
                fairsharing_policies['data_access_for_pre_publication_review'] = fs_data_access_for_pre_publication_review

        # For now, prioritize re3data policies, and then add FAIRsharing policies if not already covered
        # This is a simplified merge, a more complex merge might be needed based on specific policy types
        merged_policies = list(re3data_policies) # Convert to list to allow appending
        if fairsharing_policies:
            merged_policies.append({'fairsharing_policy_details': fairsharing_policies}) # Wrap FAIRsharing policies in a dict

        return merged_policies
