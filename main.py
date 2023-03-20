import getopt
import sys
import jsonpickle
import config
import time
import datetime
import meraki
from influxdb_client import InfluxDBClient
from datetime import datetime
from pytz import timezone

def main():
    # Environmental variables - Defined in config.py file
    api_key = config.api_key
    org_id = config.org_id
    data_logging_tag = config.data_logging_tag
    influx_org_id = config.influx_org_id
    influx_url = config.influx_url
    influx_token = config.influx_token
    influx_bucket_name = config.influx_bucket_name

    # initialize API keys for meraki and influx
    dashboard = meraki.DashboardAPI(api_key=api_key, output_log=False)
    client = InfluxDBClient(url=influx_url, token=influx_token, debug=True)
    write_api = client.write_api()

    # pull list of organization networks make a dict of networks containing the tag specified in data_logging_tag and its name
    networks_in_scope = []
    try:
        networks = dashboard.organizations.getOrganizationNetworks(org_id)
    except meraki.APIError as e:
        print(f'Meraki API error: {e}')
    except Exception as e:
        print(f'some other error: {e}')

    for net in networks:
        if net['tags'] == None:
            continue
        elif data_logging_tag in net['tags']:
            networks_in_scope.append(net)
        else:
            continue

    run = True
    while run==True:
        data_to_db = []

        # get organizations uplink loss and latency - pulls all active MXs
        try:
            org_latency_loss = dashboard.organizations.getOrganizationDevicesUplinksLossAndLatency(organizationId=org_id,
                                                                                             timespan=60)
        except meraki.APIError as e:
            print(f'Meraki API error: {e}')
        except Exception as e:
            print(f'some other error: {e}')
            # get organizations uplink loss and latency - pulls all active MXs
        try:
            org_uplink_statuses = dashboard.organizations.getOrganizationUplinksStatuses(
                organizationId=org_id,
                timespan=60)
        except meraki.APIError as e:
            print(f'Meraki API error: {e}')
        except Exception as e:
            print(f'some other error: {e}')

        # get performance score for each MX, security events etc in a network that had the logging tag, and build the database write sequence
        if org_latency_loss:
            for network in org_latency_loss:
                # check to see if the network has the logging tag
                if network['networkId'] in [net['id'] for net in networks_in_scope]:
                    net_name = [net['name'] for net in networks_in_scope if net['id']==network['networkId']][0].replace(" ","")
                    uplink = network['uplink']
                    latency = network['timeSeries'][0]['latencyMs']
                    loss = network['timeSeries'][0]['lossPercent']

                    data_to_db.append(f"{net_name},wan={uplink} latency={latency}")
                    data_to_db.append(f"{net_name},wan={uplink} loss={loss}")
                    # get the MX performance score
                    try:
                        perf_score = dashboard.appliance.getDeviceAppliancePerformance(serial=network['serial'])
                    except meraki.APIError as e:
                        print(f'Meraki API error: {e}')
                    except Exception as e:
                        print(f'some other error: {e}')

                    perfscore = perf_score['perfScore']
                    data_to_db.append(f"{net_name} perf_score={perfscore}")

                    # get security events from MX
                    try:
                        net_sec_events = dashboard.appliance.getNetworkApplianceSecurityEvents(
                            networkId=network['networkId'], timespan=3600)
                    except meraki.APIError as e:
                        print(f'Meraki API error: {e}')
                    except Exception as e:
                        print(f'some other error: {e}')

                    num_sec_events = len(net_sec_events)
                    data_to_db.append(f"{net_name} sec_events={num_sec_events}")
                else:
                    continue

        # Uplink statuses
        if org_uplink_statuses:
            for network in org_uplink_statuses:
                # check to see if the network has the logging tag
                if network['networkId'] in [net['id'] for net in networks_in_scope]:
                    for i in range(len(network['uplinks'])):
                        net_name = [net['name'] for net in networks_in_scope if net['id']==network['networkId']][0].replace(" ","")
                        uplink = network['uplinks'][i]['interface']
                        if network['uplinks'][i]['status']=='active':
                            status_up_down=1
                        elif network['uplinks'][i]['status']=='ready':
                            status_up_down=1
                        elif network['uplinks'][i]['status']=='failed':
                            status_up_down=0
                        elif network['uplinks'][i]['status']=='not connected':
                            status_up_down=0
                        elif network['uplinks'][i]['status']=='connecting':
                            status_up_down=0
                        data_to_db.append(f"{net_name},wan={uplink} status_up_down={status_up_down}")
                else:
                    continue

        # Loop through networks in scope
        for net in networks_in_scope:
            if 'wireless' in net['productTypes']:
                # get wireless health events for last hour
                net_name = net['name'].replace(" ","")
                try:
                    mr_health_events = dashboard.wireless.getNetworkWirelessFailedConnections(networkId=net['id'],
                                                                                             timespan=3600)
                except meraki.APIError as e:
                    print(f'Meraki API error: {e}')
                except Exception as e:
                    print(f'some other error: {e}')
                for band in config.bands:
                    for tag in config.ap_tags:
                        try:
                            if band=='all' and tag=='all':
                                client_count = dashboard.wireless.getNetworkWirelessClientCountHistory(networkId=net['id'], timespan=300, resolution=300)[0]['clientCount']
                            elif band=='all' and tag!='all':
                                client_count = dashboard.wireless.getNetworkWirelessClientCountHistory(networkId=net['id'], timespan=300, resolution=300, apTag=tag)[0]['clientCount']
                            elif band!='all' and tag=='all':
                                client_count = dashboard.wireless.getNetworkWirelessClientCountHistory(networkId=net['id'], timespan=300, resolution=300, band=band)[0]['clientCount']
                            else:
                                client_count = dashboard.wireless.getNetworkWirelessClientCountHistory(networkId=net['id'], timespan=300, resolution=300, band=band, apTag=tag)[0]['clientCount']
                            if client_count == None:
                                client_count=0
                            data_to_db.append(f'{net_name},band={band},apTag={tag} client_count={client_count}')
                        except meraki.APIError as e:
                            print(f'Meraki API error: {e}')
                        except Exception as e:
                            print(f'some other error: {e}')
                        try:
                            if band=='all' and tag=='all':
                                latency_stats = dashboard.wireless.getNetworkWirelessLatencyStats(networkId=net['id'], timespan=600)
                            elif band=='all' and tag!='all':
                                latency_stats = dashboard.wireless.getNetworkWirelessLatencyStats(networkId=net['id'], timespan=600, apTag=tag)
                            elif band!='all' and tag=='all':
                                latency_stats = dashboard.wireless.getNetworkWirelessLatencyStats(networkId=net['id'], timespan=600, band=band)
                            else:
                                latency_stats = dashboard.wireless.getNetworkWirelessLatencyStats(networkId=net['id'], timespan=600, band=band, apTag=tag)
                            if latency_stats !=None:
                                data_to_db.append(f'{net_name},band={band},apTag={tag} background_latency={latency_stats["backgroundTraffic"]["avg"]}')
                                data_to_db.append(f'{net_name},band={band},apTag={tag} best_effort_latency={latency_stats["bestEffortTraffic"]["avg"]}')
                                data_to_db.append(f'{net_name},band={band},apTag={tag} video_latency={latency_stats["videoTraffic"]["avg"]}')
                                data_to_db.append(f'{net_name},band={band},apTag={tag} voice_latency={latency_stats["voiceTraffic"]["avg"]}')
                        except meraki.APIError as e:
                            print(f'Meraki API error: {e}')
                        except Exception as e:
                            print(f'some other error: {e}')
                        try:
                            if band=='all' and tag=='all':
                                conn_stats = dashboard.wireless.getNetworkWirelessConnectionStats(networkId=net['id'], timespan=1200)
                            elif band=='all' and tag!='all':
                                conn_stats = dashboard.wireless.getNetworkWirelessLatencyStats(networkId=net['id'], timespan=1200, apTag=tag)
                            elif band!='all' and tag=='all':
                                conn_stats = dashboard.wireless.getNetworkWirelessLatencyStats(networkId=net['id'], timespan=1200, band=band)
                            else:
                                conn_stats = dashboard.wireless.getNetworkWirelessLatencyStats(networkId=net['id'], timespan=1200, band=band, apTag=tag)
                            print(conn_stats)
                            if conn_stats != None:
                                if 'assoc' in conn_stats.keys():
                                    data_to_db.append(f'{net_name},band={band},apTag={tag} assoc_failures={conn_stats["assoc"]}')
                                if 'auth' in conn_stats.keys():
                                    data_to_db.append(f'{net_name},band={band},apTag={tag} auth_failures={conn_stats["auth"]}')
                                if 'dhcp' in conn_stats.keys():
                                    data_to_db.append(f'{net_name},band={band},apTag={tag} dns_failures={conn_stats["dhcp"]}')
                                if 'dns' in conn_stats.keys():
                                    data_to_db.append(f'{net_name},band={band},apTag={tag} dhcp_failures={conn_stats["dns"]}')
                                if 'success' in conn_stats.keys():
                                    data_to_db.append(f'{net_name},band={band},apTag={tag} successful={conn_stats["success"]}')
                        except meraki.APIError as e:
                            print(f'Meraki API error: {e}')
                        except Exception as e:
                            print(f'some other error: {e}')

                if mr_health_events:
                    num_mr_events = float(len(mr_health_events))
                else:
                    num_mr_events = float(0)

                data_to_db.append(f"{net_name} wififails={num_mr_events}")

            # get date of last change in the change log
            try:
                last_change_details = dashboard.organizations.getOrganizationConfigurationChanges(organizationId=org_id,
                                                                                               networkId=net['id'])
            except meraki.APIError as e:
                print(f'Meraki API error: {e}')
            except Exception as e:
                print(f'some other error: {e}')

            # get timezone of network
            try:
                time_zone = dashboard.networks.getNetwork(net['id'])
            except meraki.APIError as e:
                print(f'Meraki API error: {e}')
            except Exception as e:
                print(f'some other error: {e}')

            last_change_time = last_change_details[0]['ts']
            last_change_name = last_change_details[0]['adminName']
            conv_time = datetime.strptime(last_change_time, "%Y-%m-%dT%H:%M:%S.%fZ")
            conv_time_utc = conv_time.replace(tzinfo=timezone('UTC'))
            conv_time_translated = conv_time_utc.astimezone(timezone(time_zone['timeZone']))
            output_time = conv_time_translated.strftime("%b %d, %Y - %I:%M %p")

            data_to_db.append(f'{net_name} lastchange="{output_time} - {last_change_name}"')

        # write the data we have gathered to the database
        for item in data_to_db:
            print(item)
        write_api.write(influx_bucket_name, influx_org_id, data_to_db)

        # wait 15 seconds before gathering the next set of data
        time.sleep(15)


if __name__ == '__main__':
    main()