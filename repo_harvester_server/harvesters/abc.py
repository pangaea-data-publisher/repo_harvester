from abc import ABC, abstractmethod

class Harvester(ABC):
    """
    An abstract base class for all harvesters.
    It defines the common interface that every harvester must implement.
    """

    def __init__(self, repository_url):
        """
        Initializes the harvester with the URL of the repository to be harvested.

        :param repository_url: The URL of the repository.
        """
        self.repository_url = repository_url
        self.metadata = {}

    @abstractmethod
    def harvest(self):
        """
        The main method to perform the harvesting.
        This method must be implemented by all concrete harvester classes.
        It should populate the self.metadata dictionary.
        """
        pass

class Authenticator(ABC):
    """
    An abstract base class for authentication mechanisms.
    It defines the common interface for acquiring authentication credentials,
    such as tokens or headers.
    """

    @abstractmethod
    def get_auth_headers(self):
        """
        This method should perform the authentication and return the
        necessary HTTP headers for subsequent authenticated requests.

        :return: A dictionary of HTTP headers, or None if authentication fails.
        """
        pass

class Parser(ABC):
    """
    An abstract base class for all parsers.
    It defines the common interface for parsing raw data from a harvester
    into a structured metadata dictionary.
    """

    def __init__(self, raw_data):
        """
        Initializes the parser with the raw data to be processed.

        :param raw_data: The raw data (e.g., XML string, JSON object) from a harvester.
        """
        self.raw_data = raw_data
        self.metadata = {}

    @abstractmethod
    def parse(self):
        """
        The main method to perform the parsing.
        This method must be implemented by all concrete parser classes.
        It should process self.raw_data and populate the self.metadata dictionary.
        """
        pass
