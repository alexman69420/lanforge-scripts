#!/usr/bin/env python3
'''
This script loads and builds a Chamber View Scenario, runs WiFi Capacity Test, runs Dataplane Test,
and posts the results to Influx.
There are optional arguments which will create a Grafana dashboard which will import the data posted to
Influx from this script.
./cv_to_grafana.py
--mgr 192.168.1.4
--influx_host 192.168.100.201
--influx_token TOKEN
--influx_tag testbed Stidmatt-01
--influx_bucket stidmatt
--influx_org Candela
--pull_report
--ssid_dut "ssid_idx=0 ssid=lanforge security=WPA2 password=password bssid=04:f0:21:2c:41:84"
--line "Resource=1.1 Profile=default Amount=4 Uses-1=wiphy1 DUT=DUT_TO_GRAFANA_DUT Traffic=wiphy1 Freq=-1"
--line "Resource=1.1 Profile=upstream Amount=1 Uses-1=eth1 DUT=DUT_TO_GRAFANA_DUT Traffic=eth1 Freq=-1"
--dut DUT_TO_GRAFANA
--test_rig Stidmatt-01
--create_scenario DUT_TO_GRAFANA_SCENARIO
--station 1.1.sta00002
--duration 15s
--upstream 1.1.eth1

OPTIONAL GRAFANA ARGUMENTS
--grafana_token TOKEN
--grafana_host 192.168.100.201
--title "Grafana Dashboard"

The Grafana arguments are only required once. After the Grafana dashboard is built it will automatically update
as more data is added to the Influx database. Running the Grafana arguments to create a dashboard will do nothing.

The pull_report flag is to be used when running this on a computer which is different from the LANforge Manager.
It downloads the reports to the device which is running the script.

Each line argument adds a line to the Chamber View Scenario which you create in the script.

DUT flag gives the name of the DUT which is created by this script. It can be found in the DUT tab in LANforge Manager.

The station flag tells Dataplane test which station to test with.
'''
import sys
import os
import argparse
import time

if sys.version_info[0] != 3:
    print("This script requires Python 3")
    exit(1)

if 'py-json' not in sys.path:
    sys.path.append(os.path.join(os.path.abspath('..'), 'py-json'))
    sys.path.append(os.path.join(os.path.abspath('..'), 'py-dashboard'))

from lf_wifi_capacity_test import WiFiCapacityTest
from cv_test_manager import *
from create_chamberview_dut import DUT
from create_chamberview import CreateChamberview
from lf_dataplane_test import DataplaneTest
from grafana_profile import UseGrafana

def main():
    parser = argparse.ArgumentParser(
        prog='cv_to_grafana.py',
        formatter_class=argparse.RawTextHelpFormatter,
        epilog='''Run Wifi Capacity and Dataplane Test and record results to Grafana''',
        description='''\
        cv_to_grafana.py
        ------------------
        ./cv_to_grafana.py
            --mgr 
            --influx_host
            --influx_token
            --influx_tag testbed
            --influx_bucket 
            --influx_org 
            --pull_report
            --ssid_dut 
            --line 
            --line
            --dut 
            --test_rig
            --create_scenario
            --station 
            --influx_tag 
            --duration 
            --upstream 
            '''
    )

    cv_add_base_parser(parser)  # see cv_test_manager.py

    parser.add_argument("-b", "--batch_size", type=str, default="",
                        help="station increment ex. 1,2,3")
    parser.add_argument("-l", "--loop_iter", type=str, default="",
                        help="Loop iteration ex. 1")
    parser.add_argument("-p", "--protocol", type=str, default="",
                        help="Protocol ex.TCP-IPv4")
    parser.add_argument("-d", "--duration", type=str, default="",
                        help="duration in ms. ex. 5000")
    parser.add_argument("--download_rate", type=str, default="1Gbps",
                        help="Select requested download rate.  Kbps, Mbps, Gbps units supported.  Default is 1Gbps")
    parser.add_argument("--upload_rate", type=str, default="10Mbps",
                        help="Select requested upload rate.  Kbps, Mbps, Gbps units supported.  Default is 10Mbps")
    parser.add_argument("--sort", type=str, default="interleave",
                        help="Select station sorting behaviour:  none | interleave | linear  Default is interleave.")
    parser.add_argument('--number_template', help='Start the station numbering with a particular number. Default is 0000',
                        default=0000)
    parser.add_argument('--mode', help='Used to force mode of stations')
    parser.add_argument('--ap', help='Used to force a connection to a particular AP')
    parser.add_argument("--num_stations", default=2)
    parser.add_argument("--mgr_port", default=8080)
    parser.add_argument("--upstream_port", default="1.1.eth1")
    parser.add_argument("--scenario", help="", default=None)
    parser.add_argument("--line", action='append', nargs='+',
                        help="line number", default=[])
    parser.add_argument("-ds", "--delete_scenario", default=False, action='store_true',
                        help="delete scenario (by default: False)")

    parser.add_argument("--create_scenario", "--create_lf_scenario", type=str,
                        help="name of scenario to be created")
    parser.add_argument("-u", "--upstream", type=str, default="",
                        help="Upstream port for wifi capacity test ex. 1.1.eth2")
    parser.add_argument("--station", type=str, default="",
                        help="Station to be used in this test, example: 1.1.sta01500")

    parser.add_argument("--dut", default="",
                        help="Specify DUT used by this test, example: linksys-8450")
    parser.add_argument("--download_speed", default="",
                        help="Specify requested download speed.  Percentage of theoretical is also supported.  Default: 85%")
    parser.add_argument("--upload_speed", default="",
                        help="Specify requested upload speed.  Percentage of theoretical is also supported.  Default: 0")
    parser.add_argument("--graph_groups", help="File to save graph_groups to", default=None)
    parser.add_argument("--ssid_dut", action='append', nargs=1, help="SSID", default=[])


    parser.add_argument("--sw_version", default="NA", help="DUT Software version.")
    parser.add_argument("--hw_version", default="NA", help="DUT Hardware version.")
    parser.add_argument("--serial_num", default="NA", help="DUT Serial number.")
    parser.add_argument("--model_num", default="NA", help="DUT Model Number.")
    parser.add_argument("--report_dir", default="")
    parser.add_argument('--grafana_token', help='token to access your Grafana database')
    parser.add_argument('--grafana_port', help='Grafana port if different from 3000', default=3000)
    parser.add_argument('--grafana_host', help='Grafana host', default='localhost')

    args = parser.parse_args()

    cv_base_adjust_parser(args)

    # Create/update new DUT
    print("Make new DUT")
    new_dut = DUT(lfmgr=args.mgr,
                  port=args.port,
                  dut_name=args.dut,
                  ssid=args.ssid_dut,
                  sw_version=args.sw_version,
                  hw_version=args.hw_version,
                  serial_num=args.serial_num,
                  model_num=args.model_num,
                  )
    new_dut.setup()
    new_dut.add_ssids()
    new_dut.cv_test.show_text_blob(None, None, True)  # Show changes on GUI
    new_dut.cv_test.sync_cv()
    time.sleep(2)
    new_dut.cv_test.sync_cv()

    print("Build Chamber View Scenario")
    Create_Chamberview = CreateChamberview(lfmgr=args.mgr,
                                           port=args.port,
                                           )
    if args.delete_scenario:
        Create_Chamberview.clean_cv_scenario(type="Network-Connectivity", scenario_name=args.create_scenario)

    Create_Chamberview.setup(create_scenario=args.create_scenario,
                             line=args.line,
                             raw_line=args.raw_line)
    Create_Chamberview.build(args.create_scenario)

    print("Run WiFi Capacity Test")
    wifi_capacity = WiFiCapacityTest(lfclient_host=args.mgr,
                                     lf_port=args.mgr_port,
                                     lf_user=args.lf_user,
                                     lf_password=args.lf_password,
                                     instance_name='testing',
                                     config_name=args.config_name,
                                     upstream=args.upstream_port,
                                     batch_size=args.batch_size,
                                     loop_iter=args.loop_iter,
                                     protocol=args.protocol,
                                     duration=args.duration,
                                     pull_report=args.pull_report,
                                     load_old_cfg=args.load_old_cfg,
                                     download_rate=args.download_rate,
                                     upload_rate=args.upload_rate,
                                     sort=args.sort,
                                     enables=args.enable,
                                     disables=args.disable,
                                     raw_lines=args.raw_line,
                                     raw_lines_file=args.raw_lines_file,
                                     sets=args.set)
    wifi_capacity.apply_cv_scenario(args.scenario)
    wifi_capacity.build_cv_scenario()
    wifi_capacity.setup()
    wifi_capacity.run()
    wifi_capacity.check_influx_kpi(args)

    print("Run Dataplane test")

    CV_Test = DataplaneTest(lf_host=args.mgr,
                            lf_port=args.port,
                            lf_user=args.lf_user,
                            lf_password=args.lf_password,
                            instance_name='dataplane-instance',
                            config_name=args.config_name,
                            upstream=args.upstream,
                            pull_report=args.pull_report,
                            load_old_cfg=args.load_old_cfg,
                            download_speed=args.download_speed,
                            upload_speed=args.upload_speed,
                            duration=args.duration,
                            dut=args.dut,
                            station=args.station,
                            enables=args.enable,
                            disables=args.disable,
                            raw_lines=args.raw_line,
                            raw_lines_file=args.raw_lines_file,
                            sets=args.set,
                            graph_groups=args.graph_groups
                            )
    CV_Test.setup()
    CV_Test.run()

    CV_Test.check_influx_kpi(args)

    if args.grafana_token:
        print("Create Grafana dashboard")
        Grafana = UseGrafana(args.grafana_token,
                             args.grafana_port,
                             args.grafana_host
                             )
        Grafana.create_custom_dashboard(scripts=args.scripts,
                                        title=args.title,
                                        bucket=args.influx_bucket,
                                        graph_groups=args.graph_groups,
                                        graph_groups_file=args.graph_groups_file,
                                        testbed=args.testbed,
                                        datasource=args.datasource,
                                        from_date=args.from_date,
                                        graph_height=args.graph_height,
                                        graph__width=args.graph_width)


if __name__ == "__main__":
    main()