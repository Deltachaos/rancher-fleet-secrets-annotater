import time
import logging
from kubernetes import client, config

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load Kubernetes configuration
config.load_kube_config()

# Create API clients
v1 = client.CoreV1Api()
crd_api = client.CustomObjectsApi()

# Define the CRD resource details
GROUP = "fleet.cattle.io"
VERSION = "v1alpha1"
PLURAL = "clusters"

logging.info("Starting the script.")

# Main loop
while True:
    try:
        logging.info("Fetching all secrets.")
        # Get all secrets in all namespaces
        secrets = v1.list_secret_for_all_namespaces()

        cluster_annotations = {}

        for secret in secrets.items:
            annotations = secret.metadata.annotations

            # Check if the secret has the desired annotation
            if "rancher-fleet-secrets.alpha.deltachaos.de/replicate" in annotations:
                logging.info(f"Processing secret: {secret.metadata.name} in namespace: {secret.metadata.namespace}")

                cluster_annotation = annotations.get("rancher-fleet-secrets.alpha.deltachaos.de/clusters", "")
                clusters = cluster_annotation.split(",")

                replicate_annotation = annotations["rancher-fleet-secrets.alpha.deltachaos.de/replicate"]
                replicate_keys = replicate_annotation.split(",")

                for key in replicate_keys:
                    if key in secret.data:
                        value = secret.data[key]
                        logging.info(f"Found key '{key}' in secret. Preparing to annotate clusters.")

                        # Collect annotations for each cluster
                        for cluster_identifier in clusters:
                            if cluster_identifier not in cluster_annotations:
                                cluster_annotations[cluster_identifier] = {}
                            cluster_annotations[cluster_identifier][f"rancher-fleet-secrets.deltachaos.de/secret/{key}"] = value

        logging.info("Fetching all cluster resources.")
        # Get all Cluster resources
        cluster_resources = crd_api.list_cluster_custom_object(
            group=GROUP, version=VERSION, plural=PLURAL, namespace=""
        )

        for cluster_resource in cluster_resources['items']:
            cluster_name = cluster_resource['metadata']['name']
            cluster_namespace = cluster_resource['metadata']['namespace']
            cluster_identifier = f"{cluster_namespace}/{cluster_name}"

            if cluster_identifier in cluster_annotations:
                logging.info(f"Annotating cluster: {cluster_identifier}")
                annotations = cluster_resource['metadata'].get('annotations', {})
                annotations.update(cluster_annotations[cluster_identifier])

                # Update the Cluster resource with the collected annotations
                body = {
                    "metadata": {
                        "annotations": annotations
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

        logging.info("Sleeping for 15 seconds.")
        # Sleep for 15 seconds
        time.sleep(15)
    except Exception as e:
        logging.error(f"An error occurred: {e}")
        # Optionally add a sleep or retry mechanism in case of failure
        time.sleep(15)