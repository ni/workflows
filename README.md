# workflows
Reusable GitHub Actions workflows

## Available workflows

## sign-chart

The `sign-chart` reusable workflow is used to sign a helm chart and publish the signature to the
specified artifact repository. Helm charts are signed using GPG keys. The chart is first
downloaded from the specified repository, the signature is generated and the signature is then
uploaded adjacent to the specified artifact.

The reusable workflow is located at: `.github/workflows/sign-chart.yml`.

### Inputs

| Name                | Description                                                              |
|---------------------|--------------------------------------------------------------------------|
| `chart`             | The name of the chart to be signed                                       |
| `gpg_key_id` (Optional) | The id to use for signing, defaults to `security@ni.com`             |  
| `repository_name`   | The name of the helm repository (e.g. `rds-helm`)                        |
| `repository_path` (Optional) | The path within the repository where the chart is stored, defaults to `/` |
| `repository_url` (Optional) | The URL to the helm repository, defaults to `https://niartifacts.jfrog.io/artifactory/api/helm/rds-hlm` |
| `repository_user`   | The user to connect to the helm repository                               |
| `version`           | The version of the helm chart to sign                                    |

### Secrets
Secrets must be defined in the calling repository or organization and then provided to this reusable workflow.

| Name                  | Description                                                            |
|-----------------------|------------------------------------------------------------------------|
| `GPG_PRIVATE_KEY`     | A base64 encoded gpg private key to use for signing                    |
| `REPOSITORY_PASSWORD` | The password to use to connect to the helm repository                  |

### Usage

First define the needed secrets `GPG_PRIVATE_KEY` and `REPOSITORY_PASSWORD` in
the repo or organization of the workflow caller. The calling workflow should look something like:

```yaml
on:
  push:

jobs:
  build-publish-chart:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Build chart package
        run: helm package test-chart --destination ${{ runner.temp }} --version '0.1.${{ github.run_id }}'
      - name: Publish chart
        run: curl -H "X-JFrog-Art-Api:${{ secrets.REPOSITORY_PASSWORD }}" -T ${{ runner.temp }}/test-chart-0.1.${{ github.run_id }}.tgz "https://niartifacts.jfrog.io/artifactory/rds-hlm/ni/test-chart/test-chart-0.1.${{ github.run_id }}.tgz"

  sign-chart:
    uses: ni/workflows/.github/workflows/sign-chart.yml@main
    needs: build-publish-chart
    with:
      chart: test-chart
      repository_name: rds-hlm
      repository_path: /ni/test-chart/
      repository_user: neil.stoddard@ni.com
      version: '0.1.${{ github.run_id }}'
    secrets:
      GPG_PRIVATE_KEY: ${{ secrets.GPG_PRIVATE_KEY }}
      REPOSITORY_PASSWORD: ${{ secrets.REPOSITORY_PASSWORD }
```

## `sign-container`

The `sign-container` reusable workflow is used to sign a container tag and publish the signature
to the specified signature store (an s3 bucket). Container tag manifests are signed using GPG keys
using [`podman`](https://github.com/containers/podman/blob/main/docs/tutorials/image_signing.md).
The signatures are then published to the specified s3 bucket which can be used to verify the
providence of a tag using [podman policy](https://docs.podman.io/en/latest/markdown/podman.1.html?highlight=policy.json#configuration-files).

The reusable workflow is located at: `.github/workflows/sign-container.yml`.

### Inputs

| Name                | Description                                                              |
|---------------------|--------------------------------------------------------------------------|
| `gpg_key_id` (Optional) | The id to use for signing, defaults to `security@ni.com`             |
| `image_tag`         | The tag of the image to be signed                                        |
| `registry` (Optional) | The name of the image repository, defaults to `niartifacts.jfrog.io`   |
| `registry_username` | The username to connect to the registry.                                 |
| `signature_store_bucket` | The s3 bucket to upload signatures (e.g. `s3://signing-web-demo-bucket-1neyh347t53dt`) |
| `signature_store_region` | The region of the s3 bucket                                         |

### Secrets
Secrets must be defined in the calling repository or organization and then provided to this reusable workflow.

| Name                  | Description                                                            |
|-----------------------|------------------------------------------------------------------------|
| `AWS_ACCESS_KEY_ID`   | The AWS access key id to connect to the s3 bucket                      |
| `AWS_SECRET_ACCESS_KEY` | The AWS secret access key to connect to the s3 bucket                |
| `GPG_PRIVATE_KEY`     | A base64 encoded gpg private key to use for signing                    |
| `REGISTRY_PASSWORD`   | The password to connect to the container registry                      |

### Usage

First define the needed secrets `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `GPG_PRIVATE_KEY`, 
and `REGISTRY_PASSWORD` in the repo or organization of the workflow caller. The calling workflow
should look something like:

```yaml
on:
  push:

jobs:
  build-publish-container:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Log into Registry
        uses: redhat-actions/podman-login@v1
        with:
          username: user.name@domain.com
          password: ${{ secrets.REGISTRY_PASSWORD }}
          registry: niartifacts.jfrog.io
      - name: Build container
        run: podman build -t niartifacts.jfrog.io/rdsdck/test-image:${{ github.run_id }} .
      - name: Push container
        run: podman push niartifacts.jfrog.io/rdsdck/test-image:${{ github.run_id }}
        
  sign-container:
    uses: ni/workflows/.github/workflows/sign-container.yml@main
    needs: build-publish-container
    with:
      image_tag: niartifacts.jfrog.io/rdsdck/test-image:${{ github.run_id }}
      registry_username: user.name@domain.com
      signature_store_bucket: s3://signing-web-demo-bucket-1neyh347t53dt
    secrets:
      AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
      AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
      GPG_PRIVATE_KEY: ${{ secrets.GPG_PRIVATE_KEY }}
      GPG_PUBLIC_KEY: ${{ secrets.GPG_PUBLIC_KEY }}
      REGISTRY_PASSWORD: ${{ secrets.REGISTRY_PASSWORD }}
```