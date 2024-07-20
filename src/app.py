import time
import logging
from kubernetes import client, config
import base64
import traceback
import collections
import json

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load Kubernetes configuration
try:
    config.load_incluster_config()
    logging.info("Successfully loaded in-cluster configuration.")
except Exception as e:
    logging.error(f"Failed to load in-cluster configuration: {e}")
    raise

# Create API clients
v1 = client.CoreV1Api()
crd_api = client.CustomObjectsApi()

# Define the CRD resource details
GROUP = "fleet.cattle.io"
VERSION = "v1alpha1"
PLURAL = "clusters"

SECRET_PREFIX = "secret.fleet-secrets.deltachaos.de/"

logging.info("Starting the script.")

# Main loop
while True:
    try:
        logging.info("Fetching all secrets.")
        # Get all secrets in all namespaces
        secrets = v1.list_secret_for_all_namespaces()

        cluster_annotations = {}
        all_clusters_annotations = {}

        for secret in secrets.items:
            annotations = secret.metadata.annotations

            # Check if the secret has the desired annotation
            if annotations is not None and "fleet-secrets.alpha.deltachaos.de/replicate" in annotations:
                logging.info(f"Processing secret: {secret.metadata.name} in namespace: {secret.metadata.namespace}")

                cluster_annotation = annotations.get("fleet-secrets.alpha.deltachaos.de/clusters", "")
                clusters = cluster_annotation.split(",")

                replicate_annotation = annotations["fleet-secrets.alpha.deltachaos.de/replicate"]
                replicate_keys = replicate_annotation.split(",")

                for key in replicate_keys:
                    # TODO split by =
                    targetKey = key
                    if key in secret.data:
                        value = base64.b64decode(secret.data[key]).decode('utf-8')
                        logging.info(f"Found key '{key}' in secret. Preparing to annotate clusters.")

                        if cluster_annotation != "":
                            # Collect annotations for each cluster
                            for cluster_identifier in clusters:
                                if cluster_identifier not in cluster_annotations:
                                    cluster_annotations[cluster_identifier] = {}
                                cluster_annotations[cluster_identifier][SECRET_PREFIX + targetKey] = value
                        else:
                            all_clusters_annotations[SECRET_PREFIX + targetKey] = value


        logging.info("Fetching all namespaces.")
        # Get all namespaces
        namespaces = v1.list_namespace()
        for ns in namespaces.items:
            namespace = ns.metadata.name
            # Get all Cluster resources in the current namespace
            cluster_resources = crd_api.list_namespaced_custom_object(
                group=GROUP, version=VERSION, plural=PLURAL, namespace=namespace
            )

            for cluster_resource in cluster_resources['items']:
                cluster_name = cluster_resource['metadata']['name']
                cluster_namespace = cluster_resource['metadata']['namespace']

                logging.info(f"Process cluster {cluster_name} in namespace: {cluster_namespace}")

                cluster_identifier = f"{cluster_namespace}/{cluster_name}"

                annotations = all_clusters_annotations.copy()
                if cluster_identifier in annotations:
                    annotations.update(cluster_annotations[cluster_identifier])

                new_annotations = cluster_resource['metadata'].get('annotations', {})

                new_annotations_copy = new_annotations.copy()
                updated = False
                for new_annotation in new_annotations_copy:
                    if new_annotation.startswith(SECRET_PREFIX) and not new_annotation in annotations:
                        updated = True
                        del new_annotations[new_annotation]

                new_annotations.update(annotations)

                if new_annotations != annotations or updated:
                    logging.info(f"Annotating cluster: {cluster_identifier} with {new_annotations}")
                    # Update the Cluster resource with the collected annotations
                    body = {
                        "metadata": {
                            "annotations": new_annotations
                        }
                    }

                    crd_api.patch_namespaced_custom_object(
                        group=GROUP,
                        version=VERSION,
                        namespace=cluster_namespace,
                        plural=PLURAL,
                        name=cluster_name,
                        body=body
                    )
                    logging.info(f"Successfully patched cluster: {cluster_identifier}")
                else:
                    logging.info(f"Cluster already up to date: {cluster_identifier}")

        logging.info("Sleeping for 15 seconds.")
        # Sleep for 15 seconds
        time.sleep(15)
    except Exception as e:
        logging.error(f"An error occurred: {e}\n" + traceback.format_exc())
        # Optionally add a sleep or retry mechanism in case of failure
        time.sleep(15)