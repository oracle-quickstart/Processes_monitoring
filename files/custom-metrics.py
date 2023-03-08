from time import sleep
import psutil
import argparse
import socket
from oci import monitoring, auth
import datetime
from pytz import timezone
import os


def post_metrics(monitoring_client, metric_value, instanc_name, process_name, metric_name, namespace, name, compartment_id):
    dimension_key = instanc_name
    dimension_value = process_name + "_" + metric_name
    times_stamp = datetime.datetime.now(timezone('UTC'))
    timestamp = datetime.datetime.strftime(
        times_stamp, "%Y-%m-%dT%H:%M:%S.%fZ")
    try:
        monitoring_client.post_metric_data(
            post_metric_data_details=monitoring.models.PostMetricDataDetails(
                metric_data=[
                    monitoring.models.MetricDataDetails(
                        namespace=namespace,
                        compartment_id=compartment_id,
                        name=name,
                        dimensions={dimension_key: dimension_value},
                        datapoints=[
                            monitoring.models.Datapoint(
                                timestamp=timestamp,
                                value=metric_value), ],
                    )],
                batch_atomicity="NON_ATOMIC"),)
    except Exception as e:
        print(e)
        exit(1)


def create_metrics(list_of_datapoints, instance_name, namespace, name, compartment_id):

    signer = auth.signers.InstancePrincipalsSecurityTokenSigner()
    monitoring_client = monitoring.MonitoringClient(
        config={}, signer=signer, service_endpoint=telemetry_url)
    for datapoint in list_of_datapoints:
        process_name = list(datapoint.keys())[0]
        cpu_percent = datapoint[process_name][0]
        memory_usage = datapoint[process_name][1]
        is_running = datapoint[process_name][2]
        post_metrics(monitoring_client, cpu_percent, instance_name,
                     process_name, "cpu_percent", namespace, name, compartment_id)
        post_metrics(monitoring_client, memory_usage, instance_name,
                     process_name, "memory_usage", namespace, name, compartment_id)
        post_metrics(monitoring_client, is_running, instance_name,
                     process_name, "is_running", namespace, name, compartment_id)


def get_metrics(dict_of_processes):
    list_of_datapoints = []
    list_for_dupes = []
    if os.name != "nt":
        try:
            for proc in psutil.process_iter():
                if proc.cmdline() in dict_of_processes.values():
                    proc_name = [k for k, v in dict_of_processes.items()
                                 if v == proc.cmdline()][0]

                    if proc_name not in list_for_dupes:
                        list_for_dupes.append(proc_name)
                    else:
                        list_for_dupes.append(proc_name)
                        proc_name = proc_name + "_" + \
                            str(list_for_dupes.count(proc_name))

                    cpu_percent = proc.cpu_percent()
                    is_running = 1

                    memory_info = proc.memory_full_info().rss / (1024 * 1024)

                    list_of_datapoints.append(
                        {proc_name: [cpu_percent, memory_info, is_running]})

        except psutil.AccessDenied:
            print("Access denied")
            exit(1)
    else:
        try:
            for proc in psutil.process_iter():

                if proc.name() in sum(dict_of_processes.values(), []):
                    proc_name = [k for k, v in dict_of_processes.items()
                                 if v[0] == proc.name()][0]

                    if proc_name not in list_for_dupes:
                        list_for_dupes.append(proc_name)
                    else:
                        list_for_dupes.append(proc_name)
                        proc_name = proc_name + "_" + \
                            str(list_for_dupes.count(proc_name))

                    cpu_percent = proc.cpu_percent()
                    is_running = 1

                    memory_info = proc.memory_info().rss / (1024 * 1024)

                    list_of_datapoints.append(
                        {proc_name: [cpu_percent, memory_info, is_running]})

        except psutil.AccessDenied:
            print("Access denied")
            exit(1)

    list_of_running_proceses = [list(k.keys())[0] for k in list_of_datapoints]
    for proc in dict_of_processes.keys():
        if proc not in list_of_running_proceses:
            list_of_datapoints.append({proc: [0, 0, 0]})

    return list_of_datapoints


parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter,
                                 description="parsing arguments for script")


parser.add_argument("-comp", dest="comp_id", type=str,
                    required=True, help="compartment id")

parser.add_argument("-metric_nmspace", dest="metric_namespace", type=str,
                    required=True, help="metric namespace")

parser.add_argument("-metric_name", dest="metric_name", type=str,
                    required=True, help="metric names")

parser.add_argument("-proc_file", dest="processes_file", type=str,
                    required=True, help="processes file")

parser.add_argument("-telemetry", dest="telemetry", type=str,
                    required=True, help="telemetry url")


args = parser.parse_args()


instance_name = socket.gethostname()
telemetry_url = args.telemetry
name = args.metric_name
namespace = args.metric_namespace
compartment_id = args.comp_id
processes_file = args.processes_file

dict_of_processes = {}

with open(processes_file) as f:
    for line in f.readlines():
        if line != '\n':
            process_name, process_command = line.partition("=")[::2]
            dict_of_processes[process_name] = process_command.split()


while True:
    list_of_datapoints = get_metrics(dict_of_processes)
    create_metrics(list_of_datapoints, instance_name,
                   namespace, name, compartment_id)
    sleep(30)
