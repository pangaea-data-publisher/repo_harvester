import connexion
import six

from swagger_server.models.repository_info import RepositoryInfo  # noqa: E501
from swagger_server import util


def get_repo_info(url):  # noqa: E501
    """get_repo_info

    Return the repo info as a dictionary # noqa: E501

    :param url: A repository URL
    :type url: str

    :rtype: RepositoryInfo
    """
    return 'do some magic!'
