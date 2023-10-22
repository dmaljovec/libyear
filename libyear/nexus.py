import bisect
import os
import sys
from datetime import datetime

import requests
from packaging.version import parse


NEXUS_URL = os.environ.get("NEXUS_URL", "")
NEXUS_REPOSITORY = os.environ.get("NEXUS_PYPI_REPOSITORY", "pypi-hosted")


def get_package_details(
    name, version=None, host=NEXUS_URL, repository=NEXUS_REPOSITORY
):
    continuation_token = None
    items = []
    while True:
        url = (
            f"{host}/service/rest/v1/search/assets?repository={repository}&name={name}"
        )
        if version:
            url += f"&version={version}"
        if continuation_token:
            url += f"&continuationToken={continuation_token}"

        r = requests.get(url)

        if r.status_code < 400:
            data = r.json()
            for item in data.get("items", []):
                pypi_data = item.get("pypi", {})
                if pypi_data.get("name") == name:
                    if version is None or pypi_data.get("version") == version:
                        items.append(
                            (
                                item.get("id"),
                                pypi_data.get("name"),
                                parse(pypi_data.get("version")),
                            )
                        )
            if "continuationToken" not in data or data["continuationToken"] is None:
                break
            continuation_token = data.get("continuationToken")
    return sorted(items, key=lambda v: v[2])


def get_nexus_timestamp(
    name,
    version,
    host=NEXUS_URL,
    repository=NEXUS_REPOSITORY,
):
    continuation_token = None
    while True:
        url = (
            f"{host}/service/rest/v1/search/assets?repository={repository}&name={name}"
        )
        if continuation_token:
            url += f"&continuationToken={continuation_token}"

        r = requests.get(url)

        if r.status_code < 400:
            data = r.json()
            for item in data.get("items", []):
                pypi_data = item.get("pypi", {})
                if (
                    pypi_data.get("name", "") == name
                    and pypi_data.get("version", "") == version
                ):
                    return datetime.strptime(
                        item.get("lastModified"),
                        "%Y-%m-%dT%H:%M:%S.%f%z",
                    )
            if "continuationToken" not in data or data["continuationToken"] is None:
                break
            continuation_token = data.get("continuationToken")
    return None


def get_version_release_dates(
    name, version, version_lt, host=NEXUS_URL, repository=NEXUS_REPOSITORY
):
    available_versions = [
        v[2]
        for v in get_package_details(
            name=name,
            host=host,
            repository=repository,
        )
    ]
    if len(available_versions) == 0:
        return None, None, None, None

    # retrieve latest_version
    latest_version = str(available_versions[-1])

    # retrieve version
    if version_lt:
        version_lt = parse(version_lt)
        idx = bisect.bisect_left(available_versions, version_lt)
        if idx > 0:
            version = str(available_versions[idx - 1])
        else:
            print(
                f"Unsatisfiable constraint: {name}<{str(version_lt)}", file=sys.stderr
            )
            version = None

    if version is None:
        return None, None, None, None

    version_date = get_nexus_timestamp(name, version, host, repository)
    latest_version_date = get_nexus_timestamp(name, latest_version, host, repository)
    return version, version_date, latest_version, latest_version_date


def get_lib_days(
    name, version, version_lt, host=NEXUS_URL, repository=NEXUS_REPOSITORY
):
    v, cr, lv, lr = get_version_release_dates(
        name, version, version_lt, host, repository
    )
    libdays = (lr - cr).days if cr else 0
    return v, lv, libdays
