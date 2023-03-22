# merakiLiveDashboard
Create a live Dashboard from your Meraki networks using the Meraki Dashboard API, InfluxDB and Grafana. Based on previous work by rharami in https://github.com/rharami/API-Workshop

# Table of Contents

* [Introduction](#intro)

* [Prerequisites](#prereq)

* [How to use](#howtouse)

* [Connecting to InfluxDB](#influxdb)

* [Connecting to Grafana](#grafana)

<a id="intro"></a>

# Introduction

The Cisco Meraki Dashboard offers great visibility into many IT- and business-relevant metrics, including total utilization, client and network health, number of visitors and security incidents. In addition, the Cisco Meraki API allows extracting the specific bits of data you're interested in, for the creation of custom live Dashboards for specific use cases.

This tool and guide offers the means to:
* Extract certain metrics from the Meraki Dashboard
* Parse those metrics and send them to a cloud database in InfluxDB
* Create live graphs and dashboards from this data in InfluxDB and Grafana

The metrics extracted are:
* MX Performance
* MX Uplink Loss and Latency
* Wireless Connection Statistics
* Wireless Latency Statistics
* Wireless Client Counts

<a id="prereq"></a>

## Prerequisites

1. Active Cisco Meraki subscriptions in the orgs where the script will be run
2. API access enabled for these organizations, as well as an API Key with access to them. See how to enable [here](https://documentation.meraki.com/General_Administration/Other_Topics/Cisco_Meraki_Dashboard_API)
3. A working Python 3.0 environment
4. Install libraries in `requirements.txt`
5. Have some deployed organizations and networks
6. Create a free InfluxDB cloud account https://cloud2.influxdata.com
7. Create a free Grafana cloud account https://grafana.com/get

<a id="howtouse"></a>

## How to Use

1. Clone repo to your working directory with `git clone https://github.com/Francisco-1088/merakiLiveDashboard.git`
2. Edit `config.py`
* Add your API Key under `api_key` in line 2
* Add your Organization ID under `org_id` in line 3
You can find your Org ID easily by right clicking anywhere in the screen while logged in to your organization, and clicking "View Page Source". In the resulting page use "Find" to look for the keyword `Mkiconf.org_id`
* Define a `data_logging_tag` for networks that will be queried (`influx` by default)
* Define a list of wireless bands of interest (`all`, `2.4`, `5` and `6` by default)
* Define a list of AP tags of interest under `ap_tags` (this is needed for granularity of metrics, default includes `all` and a set of bogus tags that should be replaced
* Add your Influx parameters as explained in the `Connecting to InfluxDB` section, 1-4

3. Run `pip install -r requirements.txt` from your terminal
4. [Tag networks](https://documentation.meraki.com/General_Administration/Organizations_and_Networks/Organization_Menu/Manage_Tags) you want to work on with the same tag you defined in `config.py` under `data_logging_tag`. 
5. [Tag Wireless APs](https://documentation.meraki.com/MR/Monitoring_and_Reporting/Using_Tags_to_Manage_MR_Access_Points#Tagging_APs) using the tags listed under `ap_tags`.
6. Run the script with `python main.py`
7. Follow the steps under `Connecting to InfluxDB` to start shaping the data
8. Follow the steps under `Connecting to Grafana` to create a Dashboard

<a name="influxdb"></a>

## Connecting to InfluxDB

1. Login to your InfluxDB Cloud 2.0 account

2. Navigate to the “Data” menu on the left hand side of the page, and select the Buckets tab. Click Create Bucket. Name the bucket `live-dashboard` and set the retention policy for 14 days. This bucket is where all your Meraki API data will live within the database. The bucket name is the value you need in `influx_bucket_name` in the `How to Use` section.

3. Navigate to the Tokens tab, click Generate Token, and choose All Access Token. Give the token a name. We will come back to this token in the steps below as this is required in order to give our API script authorization to write data to this database. This is the value you need for `influx_token` in the `How to Use` section.

4. For the steps below, you will need two other pieces of information from InfluxDB, the url and the organization ID. If you look at the URL when logged into Influx, it will look something like this: `https://us-west-2-1.aws.cloud2.influxdata.com/orgs/xYYYYYYYYxYYxYYx` . In this case, `https://us-west-2-1.aws.cloud2.influxdata.com` is your influx URL, and `xYYYYYYYYxYYxYYx` is your influx Org id. These are the two remaining values you need in the `How to Use` section.

5. Now it’s time to build your dashboard using the data being sent to the database. Navigate back to your InfluxDB cloud dashboard. Select “Boards” and “Create Dashboard.” 

6. Click “Add Cell”

7. Under `From` select the `live-dashboard` bucket

8. Under `Filter` select the desired Network names, metric and selections like apTag, band or MX Uplink that you want in this specific visualization

9. Under the graph style select `Graph`

10. Double-click on the Title and give it a name

11. Click `Submit`

12. Repeat this process for each set of data you wish to visualize

<a name="grafana"></a>

## Connecting to Grafana

1. Follow the instructions [here](https://docs.influxdata.com/influxdb/cloud/tools/grafana/) to link your InfluxDB as a data source for your Grafana account

2. From Grafana, go to Dashboards --> New Dashboard

3. Click on Add Panel

4. Under Query --> Data Source, pick InfluxDB

5. Go to your Influx Dashboard, select any of the created panels and click `Configure` from the gear dropdown

6. Click on `Script Editor` to the right

7. Copy the text of the query

8. Go back to Grafana, and paste it in the box

9. Give your panel a Title, and optionally configure some thresholds at the bottom, and click Apply

10. Repeat this process for any additional panels you wish to port from InfluxDB

