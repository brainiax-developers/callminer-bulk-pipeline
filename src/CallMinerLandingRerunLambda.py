import json
import boto3
import os
import datetime
from datetime import timedelta

# Initialize clients
sfn_client = boto3.client('stepfunctions')
cloudwatch = boto3.client('cloudwatch')
sns_client = boto3.client('sns')
step_function_arn = os.getenv("step_function_arn")
alarm_name = os.getenv("alarm_name")

def lambda_handler(event, context):
    try:
        current_time = datetime.datetime.utcnow()
        minute = current_time.minute
        print(current_time)
        start_time = current_time - timedelta(minutes=20)

        OVERRIDE_DATE = current_time.strftime('%Y-%m-%d')
        OVERRIDE_HOUR = current_time.hour

        if 0 <= minute < 20:
            OVERRIDE_MINUTE = 0
        elif 20 <= minute < 40:
            OVERRIDE_MINUTE = 20
        elif 40 <= minute < 60:
            OVERRIDE_MINUTE = 40
        else:
            OVERRIDE_MINUTE = 0

        # Fetch the alarm details using describe_alarms
        response_cloudwatch = cloudwatch.describe_alarms(
            AlarmNames=[alarm_name]
        )

        print(response_cloudwatch)

        # Check if the alarm exists and has MetricAlarms
        if 'MetricAlarms' in response_cloudwatch and len(response_cloudwatch['MetricAlarms']) > 0:
            alarm = response_cloudwatch['MetricAlarms'][0]
            print(f"Alarm Name: {alarm['AlarmName']}")
            metric_name = "num_of_records"
            namespace = 'basetier/callminer/landing'  # Default namespace

            if 'Metrics' in alarm and len(alarm['Metrics']) > 0:
                # Iterate through the metrics defined for the alarm
                for metric in alarm['Metrics']:
                    # Check if 'MetricStat' exists in the metric
                    if 'MetricStat' in metric:
                        metric_info = metric['MetricStat']['Metric']
                        # Extract the Namespace, MetricName, and Dimensions
                        namespace = metric_info.get('Namespace', namespace)  # Default if missing
                        print(f"Namespace: {namespace}")
                        break  # Stop after finding the first metric with a Namespace
        else:
            raise ValueError("No metric alarms found for the provided alarm name.")

        # Define the metric data queries for anomaly detection band based on existing alarm config
        metric_data_queries = [
            {
                'Id': 'num_records_metric',  # Query for num_of_records metric
                'MetricStat': {
                    'Metric': {
                        'Namespace': namespace,
                        'MetricName': metric_name
                    },
                    'Period': 300,  # 5 minutes period (adjust as necessary)
                    'Stat': 'Maximum'  # Example statistic
                },
                'ReturnData': True
            },
            {
                'Id': 'anomaly_detection_band',
                'Expression': 'ANOMALY_DETECTION_BAND(num_records_metric)',
                'Label': 'Threshold value (Expected)',
                'ReturnData': True
            }
        ]
        print(metric_data_queries)

        # Fetch the metric data from CloudWatch
        metric_data_response = cloudwatch.get_metric_data(
            MetricDataQueries=metric_data_queries,
            StartTime=start_time,
            EndTime=current_time
        )
        print(metric_data_response)

        low_threshold_value = None
        if 'MetricDataResults' in metric_data_response and len(metric_data_response['MetricDataResults']) > 0:
            for result in metric_data_response['MetricDataResults']:
                if result.get('Label') == 'Threshold value (Expected) num_of_records Low':
                    if 'Values' in result and len(result['Values']) > 0:
                        low_threshold_value = result['Values'][0]
                        print(f"Low Threshold Value: {low_threshold_value}")
                    else:
                        print("No values found for 'Threshold value (Expected) num_of_records Low'")
        else:
            print("No MetricDataResults returned for the metric query.")

        # Exit early if threshold is not available to avoid passing null to the workflow
        if low_threshold_value is None:
            msg = (
                "Skipping CallMiner rerun trigger: threshold is None from CloudWatch anomaly band. "
                f"date={OVERRIDE_DATE} hour={OVERRIDE_HOUR} minute={OVERRIDE_MINUTE}"
            )
            print(msg)

            try:
                cloudwatch.put_metric_data(
                    Namespace="CallMiner/Rerun",
                    MetricData=[
                        {
                            'MetricName': 'MissingThreshold',
                            'Value': 1.0,
                            'Unit': 'Count'
                        }
                    ]
                )
            except Exception as me:
                print(f"Failed to put CloudWatch metric: {me}")

            return {"status": "skipped_no_threshold", "message": msg}

        rerun_payload = {
            "detail": {
                "rerun": True,  # Indicate that this is a rerun
                "OVERRIDE_DATE": OVERRIDE_DATE,
                "OVERRIDE_HOUR": str(OVERRIDE_HOUR),
                "OVERRIDE_MINUTE": str(OVERRIDE_MINUTE),
                "PERIOD_LENGTH": str(20),
                "threshold": low_threshold_value
            }
        }
        response = sfn_client.start_execution(
            stateMachineArn=step_function_arn,
            input=json.dumps(rerun_payload)
        )
        return {"status": "success", "executionArn": response["executionArn"], "rerun_payload": rerun_payload}

    except Exception as e:
        return {"status": "error", "message": str(e)}
