import os
import re
import requests
import subprocess
import sys

from packaging.version import Version


def get_chart_attribute(chart_filepath, attribute_name, default_value):
  with open(chart_filepath) as file:
    for line in file:
      if line.startswith(f'{attribute_name}:'):
        return line.split(':')[1].strip()
  return default_value


def main():
  args = sys.argv[1:]
  chart_directory = args[0]
  working_directory = args[1]
  build_number = args[2]
  is_prerelease = args[3] == 'true'
  application_version = args[4]

  chart_filepath = chart_directory + '/Chart.yaml'

  print(f'build_number = {build_number}')
  print(f'is_prerelease = {is_prerelease}')
  print(f'application_version = {application_version}')

  username = os.getenv('ARTIFACTORY_USER')
  token = os.getenv('ARTIFACTORY_TOKEN')

  # Parse chart name from the Chart.yaml file
  chart_name = get_chart_attribute(chart_filepath, 'name', None)
  print(f'Chart name: {chart_name}')

  # Parse chart version from the Chart.yaml file
  chart_version_string = get_chart_attribute(chart_filepath, 'version', '0.0.0')
  print(f'Chart version: {chart_version_string}')

  chart_version = Version(chart_version_string)
  version_major = chart_version.major
  version_minor = chart_version.minor

  # Retrieve the list of published helm chart versions from Artifactory
  response = requests.get(
    url=f'https://niartifacts.jfrog.io/artifactory/rnd-helm-ci/ni/systemlink/{chart_name}/{version_major}/{version_minor}',
    auth=(username, token))

  # Find the highest version of the chart on Artifactory
  highest_version = chart_version
  if response.status_code == 200:
    print('Found existing charts on the repo...')
    # Parse HTTP response
    for line in response.text.splitlines():
      if line.startswith('<a href='):
        start = line.find('">') + len('">')
        end = line.find('</a>')
        package_name = line[start:end]
        print(f'Package name: {package_name}')
        # We need to parse the following:
        #  chartname-0.1.27.tgz
        #  chartname-0.1.27.tgz.prov
        #  chartname-0.1.27-pre.20220629.4.tgz
        pattern = r"(.+)-(\d+\.\d+\.\d+)(-pre\.\d+\.\d+)?\.tgz\S*$"
        result = re.match(pattern, package_name)
        groups = result.groups()

        # package_vesrion does not include prelease portion of version
        package_version = groups[1]
        print(f'Package version: {package_version}')

        current_version = Version(package_version)
        if current_version > highest_version:
          highest_version = current_version
  elif (response.status_code == 404):
    print('No charts for this major.minor version exist.  Using current chart version.')
  else:
    print(response.text)
    sys.exit(1)

  print(f'Highest version: {highest_version}')

  # Increment the Helm chart version for committed builds
  package_major_version = highest_version.major
  package_minor_version = highest_version.minor

  if is_prerelease:
    updated_version_string = f'{highest_version}-pre.{build_number}'
  else:
    updated_version_string = f'{package_major_version}.{package_minor_version}.{highest_version.micro + 1}'

  print(f'Updated version: {updated_version_string}')

  # Package the Helm chart using the newly incremented version
  # It's important to format command as a string here, as this is required for using shell=True on Linux.
  command = f'helm package {chart_directory} --version {updated_version_string} --app-version {application_version} --destination {working_directory}'
  proc = subprocess.run(command, shell=True, universal_newlines=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
  if proc.returncode != 0:
    print(f'process return code = {str(proc.returncode)}')
    print(f'stdout = {proc.stdout}')
    print(f'stderr = {proc.stderr}')
    exit(proc.returncode)

  helm_package_filename = f'{chart_name}-{updated_version_string}.tgz'
  helm_package_filepath = os.path.join(working_directory, helm_package_filename)

  print(f'::set-output name=helm_package_filename::{helm_package_filename}')
  print(f'::set-output name=helm_package_filepath::{helm_package_filepath}')
  print(f'::set-output name=helm_package_version::{updated_version_string}')
  print(f'::set-output name=helm_package_major_version::{package_major_version}')
  print(f'::set-output name=helm_package_minor_version::{package_minor_version}')

  print(f'helm_package_filename = {helm_package_filename}')
  print(f'helm_package_filepath = {helm_package_filepath}')
  print(f'helm_package_version = {updated_version_string}')
  print(f'helm_package_major_version = {package_major_version}')
  print(f'helm_package_minor_version = {package_minor_version}')

  # Publish the Helm chart package
  with open(helm_package_filepath, 'rb') as f:
    data = f.read()
    auth = (username, token)
    response = requests.put(
      url='https://niartifacts.jfrog.io/artifactory/rnd-helm-ci/ni/systemlink/{chart_name}/{package_major}/{package_minor}/{helm_package}'.format(
        chart_name=chart_name,
        package_major=package_major_version,
        package_minor=package_minor_version,
        helm_package=helm_package_filename),
      data=data,
      auth=auth)
  print(response)

  if response.status_code != 201:
    print(response.text)
    sys.exit(1)

if __name__ == "__main__":
    main()