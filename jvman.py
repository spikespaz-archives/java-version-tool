from collections import namedtuple
from datetime import datetime

import requests


class AdoptAPI:
    api_base_url = "https://api.adoptopenjdk.net/v2"
    datetime_format = r"%Y-%m-%dT%H:%M:%SZ"

    @staticmethod
    def search_releases(version, nightly=False, **kwargs):
        api_url = "{api_base_url}/info/{release_type}/{openjdk_version}".format(
            api_base_url=AdoptAPI.api_base_url,
            release_type="nightly" if nightly else "releases",
            openjdk_version=version,
        )
        release_data_list = requests.get(api_url, params=kwargs).json()

        for release_data in release_data_list:
            yield AdoptAPI.Release(**release_data)

    class Release:
        def __init__(self, **kwargs):
            self.release_name = kwargs.get("release_name", None)
            self.release_link = kwargs.get("release_link", None)
            self.timestamp = wrap_throwable(
                lambda: datetime.strptime(kwargs["timestamp"], AdoptAPI.datetime_format), KeyError
            )()
            self.release = kwargs.get("release", None)
            self.binaries = [
                AdoptAPI.ReleaseAsset(**data) for data in kwargs.get("binaries", list())
            ]
            self.download_count = kwargs.get("download_count", None)

    class ReleaseAsset:
        VersionData = namedtuple("VersionData", "openjdk_version semver optional")

        def __init__(self, **kwargs):
            self.os = kwargs.get("os", None)
            self.architecture = kwargs.get("architecture", None)
            self.binary_type = kwargs.get("binary_type", None)
            self.openjdk_impl = kwargs.get("openjdk_impl", None)
            self.binary_name = kwargs.get("binary_name", None)
            self.binary_link = kwargs.get("binary_link", None)
            self.binary_size = kwargs.get("binary_size", None)
            self.checksum_link = kwargs.get("checksum_link", None)
            self.version = kwargs.get("version", None)
            self.version_data = AdoptAPI.ReleaseAsset.VersionData(
                openjdk_version=kwargs.get("version_data", dict()).get("openjdk_version", None),
                semver=kwargs.get("version_data", dict()).get("semver", None),
                optional=kwargs.get("version_data", dict()).get("optional", None),
            )
            self.heap_size = kwargs.get("heap_size", None)
            self.download_count = kwargs.get("download_count", None)
            self.updated_at = wrap_throwable(
                lambda: datetime.strptime(kwargs["updated_at"], AdoptAPI.datetime_format), KeyError
            )()
            self.timestamp = wrap_throwable(
                lambda: datetime.strptime(kwargs["timestamp"], AdoptAPI.datetime_format), KeyError
            )()
            self.release_name = kwargs.get("release_name", None)
            self.release_link = kwargs.get("release_link", None)

        def display(self):
            return "{openjdk_impl}-{version_data.semver}-{architecture}-{binary_type}".format(
                **self.__dict__
            )


def wrap_throwable(func, *exc):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except exc:
            return None

    return wrapper