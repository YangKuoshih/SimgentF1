import base64
import json
import logging
import os
from google.protobuf.field_mask_pb2 import FieldMask
import functions_framework
from google.cloud import run_v2

logging.basicConfig(level=logging.INFO)

PROJECT_ID = os.environ.get("PROJECT_ID", "f1-simgent")
REGION = os.environ.get("REGION", "us-central1")
SERVICE_NAME = os.environ.get("SERVICE_NAME", "f1-simgent")


@functions_framework.cloud_event
def handle_budget_alert(cloud_event):
    """
    Triggered when Google Cloud Billing publishes a budget alert message to Pub/Sub.
    Decodes costAmount and budgetAmount. If costAmount >= budgetAmount ($1.00),
    disables the Cloud Run service using manual scaling with zero instances.
    Budget notifications are delayed and do not guarantee a hard spending cap.
    """
    try:
        data = cloud_event.data
        if not data or "message" not in data:
            logging.warning("No message payload found in cloud event.")
            return

        message_bytes = base64.b64decode(data["message"]["data"])
        payload = json.loads(message_bytes.decode("utf-8"))

        cost_amount = float(payload.get("costAmount", 0.0))
        budget_amount = float(payload.get("budgetAmount", 1.0))
        budget_display_name = payload.get("budgetDisplayName", "Budget")

        logging.info(
            f"Budget Notification: '{budget_display_name}' | "
            f"Current Spend: ${cost_amount:.2f} | Target Budget: ${budget_amount:.2f}"
        )

        if cost_amount >= budget_amount:
            logging.error(
                f"🚨 CRITICAL FINOPS ALERT: Spend (${cost_amount:.2f}) has reached or exceeded "
                f"budget threshold (${budget_amount:.2f}). TRIGGERING EMERGENCY SHUTDOWN!"
            )

            client = run_v2.ServicesClient()
            service_path = f"projects/{PROJECT_ID}/locations/{REGION}/services/{SERVICE_NAME}"

            # Fetch current service definition
            service = client.get_service(name=service_path)

            # Zero max_instance_count does not disable autoscaling. Use the
            # documented service-level MANUAL mode with zero running instances.
            if not (service.scaling.scaling_mode == run_v2.ServiceScaling.ScalingMode.MANUAL
                    and service.scaling.manual_instance_count == 0):
                service.scaling.scaling_mode = run_v2.ServiceScaling.ScalingMode.MANUAL
                service.scaling.manual_instance_count = 0
                operation = client.update_service(
                    service=service, update_mask=FieldMask(paths=["scaling"]))
                operation.result(timeout=120)
                logging.warning("Budget threshold reached; service disabled via manual scaling.")
            else:
                logging.info("Service already disabled via manual scaling.")
        else:
            logging.info(
                f"✅ Spend (${cost_amount:.2f}) is safely below budget (${budget_amount:.2f}). "
                "No action required."
            )

    except Exception:
        logging.error("Budget-alert handling failed; retry required.")
        raise
