import bisect
import os
import sys

from google.cloud import artifactregistry_v1
from packaging.version import parse

GOOGLE_PROJECT = os.environ.get("GOOGLE_ARTIFACT_REGISTRY_PROJECT", "")
GOOGLE_LOCATION = os.environ.get("GOOGLE_ARTIFACT_REGISTRY_LOCATION", "us-central1")
GOOGLE_REPOSITORY = os.environ.get("GOOGLE_ARTIFACT_REGISTRY_PYPI_REPOSITORY", "python")


def get_package_details(
    name,
    version=None,
    project=GOOGLE_PROJECT,
    location=GOOGLE_LOCATION,
    repository=GOOGLE_REPOSITORY,
):
    items = []
    client = artifactregistry_v1.ArtifactRegistryClient()
    artifact_name = f"projects/{project}/locations/{location}/repositories/{repository}/packages/{name}"
    request = artifactregistry_v1.ListVersionsRequest(parent=artifact_name)
    response = client.list_versions(request=request)
    for page in response.pages:
        for item in page.versions:
            extracted_version = item.name.rsplit("/", 1)[1]
            if version is None or version == extracted_version:
                items.append(
                    (
                        name,
                        parse(extracted_version),
                        item.update_time,
                    )
                )

    return sorted(items)


def get_artifact_registry_timestamp(
    name,
    version,
    project=GOOGLE_PROJECT,
    location=GOOGLE_LOCATION,
    repository=GOOGLE_REPOSITORY,
):
    client = artifactregistry_v1.ArtifactRegistryClient()
    artifact_name = f"projects/{project}/locations/{location}/repositories/{repository}/pythonPackages/{name}:{version}"
    request = artifactregistry_v1.GetPythonPackageRequest(name=artifact_name)
    response = client.get_python_package(request)
    return response.update_time


def get_no_of_releases(
    name,
    version,
    project=GOOGLE_PROJECT,
    location=GOOGLE_LOCATION,
    repository=GOOGLE_REPOSITORY,
):
    version = parse(version)
    details = get_package_details(
        name=name, project=project, location=location, repository=repository
    )
    versions = sorted(set([v[1] for v in details]))

    return len(versions) - list(versions).index(version) - 1


def get_version_release_dates(
    name,
    version,
    version_lt,
    project=GOOGLE_PROJECT,
    location=GOOGLE_LOCATION,
    repository=GOOGLE_REPOSITORY,
):
    available_versions = [
        v[1]
        for v in get_package_details(
            name=name,
            project=project,
            location=locals,
            repository=repository,
        )
    ]

    # retrieve latest_version
    latest_version = str(available_versions[-1])

    # retrieve version
    if version_lt:
        version_lt = parse(version_lt)
        idx = bisect.bisect_left(available_versions, version_lt)
        if idx > 0:
            version = str(available_versions[idx - 1])
        else:
            print(f"Unsatisfiable constraint: {name}<{str(version_lt)}", file=sys.stderr)
            version = None

    if version is None:
        return None, None, None, None

    version_date = get_artifact_registry_timestamp(
        name,
        version,
        project=project,
        location=location,
        repository=repository,
    )
    latest_version_date = get_artifact_registry_timestamp(
        name,
        latest_version,
        project=project,
        location=location,
        repository=repository,
    )
    return version, version_date, latest_version, latest_version_date


def get_lib_days(name, version, version_lt):
    v, cr, lv, lr = get_version_release_dates(name, version, version_lt)
    libdays = (lr - cr).days if cr else 0
    return v, lv, libdays
