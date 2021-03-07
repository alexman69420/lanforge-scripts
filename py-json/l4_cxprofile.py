
#!/usr/bin/env python3
import re
from LANforge.lfcli_base import LFCliBase
from pprint import pprint
import pprint
import time
import datetime
import csv
import os

class L4CXProfile(LFCliBase):
    def __init__(self, lfclient_host, lfclient_port, local_realm, debug_=False):
        super().__init__(lfclient_host, lfclient_port, debug_, _halt_on_error=True)
        self.lfclient_url = "http://%s:%s" % (lfclient_host, lfclient_port)
        self.debug = debug_
        self.url = "http://localhost/"
        self.requests_per_ten = 600
        self.local_realm = local_realm
        self.created_cx = {}
        self.created_endp = []
        self.lfclient_port = lfclient_port
        self.lfclient_host = lfclient_host

    def check_errors(self, debug=False):
        fields_list = ["!conn", "acc.+denied", "bad-proto", "bad-url", "other-err", "total-err", "rslv-p", "rslv-h",
                       "timeout", "nf+(4xx)", "http-r", "http-p", "http-t", "login-denied"]
        endp_list = self.json_get("layer4/list?fields=%s" % ','.join(fields_list))
        debug_info = {}
        if endp_list is not None and endp_list['endpoint'] is not None:
            endp_list = endp_list['endpoint']
            expected_passes = len(endp_list)
            passes = len(endp_list)
            for item in range(len(endp_list)):
                for name, info in endp_list[item].items():
                    for field in fields_list:
                        if info[field.replace("+", " ")] > 0:
                            passes -= 1
                            debug_info[name] = {field: info[field.replace("+", " ")]}
            if debug:
                print(debug_info)
            if passes == expected_passes:
                return True
            else:
                print(list(debug_info), " Endps in this list showed errors getting to %s " % self.url)
                return False

    def start_cx(self):
        print("Starting CXs...")
        for cx_name in self.created_cx.keys():
            self.json_post("/cli-json/set_cx_state", {
                "test_mgr": "default_tm",
                "cx_name": self.created_cx[cx_name],
                "cx_state": "RUNNING"
            }, debug_=self.debug)
            print(".", end='')
        print("")

    def stop_cx(self):
        print("Stopping CXs...")
        for cx_name in self.created_cx.keys():
            self.json_post("/cli-json/set_cx_state", {
                "test_mgr": "default_tm",
                "cx_name": self.created_cx[cx_name],
                "cx_state": "STOPPED"
            }, debug_=self.debug)
            print(".", end='')
        print("")

    def check_request_rate(self):
        endp_list = self.json_get("layer4/list?fields=urls/s")
        expected_passes = 0
        passes = 0
        # TODO: this might raise a nameerror lower down
        #  if self.target_requests_per_ten is None:
        #    raise NameError("check request rate: missing self.target_requests_per_ten")
        if endp_list is not None and endp_list['endpoint'] is not None:
            endp_list = endp_list['endpoint']
            for item in endp_list:
                for name, info in item.items():
                    if name in self.created_cx.keys():
                        expected_passes += 1
                        if info['urls/s'] * self.requests_per_ten >= self.target_requests_per_ten * .9:
                            print(name, info['urls/s'], info['urls/s'] * self.requests_per_ten, self.target_requests_per_ten * .9)
                            passes += 1

        return passes == expected_passes


    def cleanup(self):
        print("Cleaning up cxs and endpoints")
        if len(self.created_cx) != 0:
            for cx_name in self.created_cx.keys():
                req_url = "cli-json/rm_cx"
                data = {
                    "test_mgr": "default_tm",
                    "cx_name": self.created_cx[cx_name]
                }
                self.json_post(req_url, data)
                # pprint(data)
                req_url = "cli-json/rm_endp"
                data = {
                    "endp_name": cx_name
                }
                self.json_post(req_url, data)
                # pprint(data)

    def create(self, ports=[], sleep_time=.5, debug_=False, suppress_related_commands_=None):
        cx_post_data = []
        for port_name in ports:
            if len(self.local_realm.name_to_eid(port_name)) == 3:
                shelf = self.local_realm.name_to_eid(port_name)[0]
                resource = self.local_realm.name_to_eid(port_name)[1]
                name = self.local_realm.name_to_eid(port_name)[2]
            else:
                raise ValueError("Unexpected name for port_name %s" % port_name)
            endp_data = {
                "alias": name + "_l4",
                "shelf": shelf,
                "resource": resource,
                "port": name,
                "type": "l4_generic",
                "timeout": 10,
                "url_rate": self.requests_per_ten,
                "url": self.url,
                "proxy_auth_type": 0x200
            }
            url = "cli-json/add_l4_endp"
            self.local_realm.json_post(url, endp_data, debug_=debug_,
                                       suppress_related_commands_=suppress_related_commands_)
            time.sleep(sleep_time)

            endp_data = {
                "alias": "CX_" + name + "_l4",
                "test_mgr": "default_tm",
                "tx_endp": name + "_l4",
                "rx_endp": "NA"
            }
            cx_post_data.append(endp_data)
            self.created_cx[name + "_l4"] = "CX_" + name + "_l4"

        for cx_data in cx_post_data:
            url = "/cli-json/add_cx"
            self.local_realm.json_post(url, cx_data, debug_=debug_,
                                       suppress_related_commands_=suppress_related_commands_)
            time.sleep(sleep_time)

    def monitor(self,
                duration_sec=60,
                monitor_interval=1,
                col_names=None,
                created_cx=None,
                monitor=True,
                report_file=None,
                output_format=None,
                script_name=None,
                arguments=None,
                iterations=0,
                debug=False):
        try:
            duration_sec = Realm.parse_time(duration_sec).seconds
        except:
            if (duration_sec is None) or (duration_sec <= 1):
                raise ValueError("L4CXProfile::monitor wants duration_sec > 1 second")
            if (duration_sec <= monitor_interval):
                raise ValueError("L4CXProfile::monitor wants duration_sec > monitor_interval")
        if report_file == None:
            raise ValueError("Monitor requires an output file to be defined")
        if created_cx == None:
            raise ValueError("Monitor needs a list of Layer 4 connections")
        if (monitor_interval is None) or (monitor_interval < 1):
            raise ValueError("L4CXProfile::monitor wants monitor_interval >= 1 second")
        if output_format is not None:
            if output_format.lower() != report_file.split('.')[-1]:
                raise ValueError('Filename %s does not match output format %s' % (report_file, output_format))
        else:
            output_format = report_file.split('.')[-1]

        # Step 1 - Assign column names 

        if col_names is not None and len(col_names) > 0:
            header_row=col_names
        else:
            header_row=list((list(self.json_get("/layer4/all")['endpoint'][0].values())[0].keys()))
        if debug:
            print(header_row)

        # Step 2 - Monitor columns

        start_time = datetime.datetime.now()
        end_time = start_time + datetime.timedelta(seconds=duration_sec)
        sleep_interval =  round(duration_sec // 5)
        if debug:
            print("Sleep_interval is %s ", sleep_interval)
            print("Start time is %s " , start_time)
            print("End time is %s " ,end_time)
        value_map = dict()
        passes = 0
        expected_passes = 0
        timestamps = []
        for test in range(1+iterations):
            while datetime.datetime.now() < end_time:
                if col_names is None:
                    response = self.json_get("/layer4/all")
                else:
                    fields = ",".join(col_names)
                    response = self.json_get("/layer4/%s?fields=%s" % (created_cx, fields))
                if debug:
                    print(response)
                if response is None:
                    print(response)
                    raise ValueError("Cannot find any endpoints")
                if monitor:
                    if debug:
                        print(response)

                time.sleep(sleep_interval)
                t = datetime.datetime.now()
                timestamps.append(t)
                value_map[t] = response
                expected_passes += 1
                if self.check_errors(debug):
                    if self.check_request_rate():
                        passes += 1
                    else:
                        self._fail("FAIL: Request rate did not exceed 90% target rate")
                        self.exit_fail()
                else:
                    self._fail("FAIL: Errors found getting to %s " % self.url)
                    self.exit_fail()
                time.sleep(monitor_interval)
        print(value_map)

    #[further] post-processing data, after test completion
        full_test_data_list = []
        for test_timestamp, data in value_map.items():
            #reduce the endpoint data to single dictionary of dictionaries
            for datum in data["endpoint"]:
                for endpoint_data in datum.values():
                    if debug:
                        print(endpoint_data)
                    endpoint_data["Timestamp"] = test_timestamp
                    full_test_data_list.append(endpoint_data)


        header_row.append("Timestamp")
        header_row.append('Timestamp milliseconds')
        df = pd.DataFrame(full_test_data_list)

        df["Timestamp milliseconds"] = [self.get_milliseconds(x) for x in df["Timestamp"]]
        #round entire column
        df["Timestamp milliseconds"]=df["Timestamp milliseconds"].astype(int)
        df["Timestamp"]=df["Timestamp"].apply(lambda x:x.strftime("%m/%d/%Y %I:%M:%S"))
        df=df[["Timestamp","Timestamp milliseconds", *header_row[:-2]]]
        #compare previous data to current data

        systeminfo = ast.literal_eval(requests.get('http://'+str(self.lfclient_host)+':'+str(self.lfclient_port)).text)

        if output_format == 'hdf':
            df.to_hdf(report_file, 'table', append=True)
        if output_format == 'parquet':
            df.to_parquet(report_file, engine='pyarrow')
        if output_format == 'png':
            fig = df.plot().get_figure()
            fig.savefig(report_file)
        if output_format.lower() in ['excel', 'xlsx'] or report_file.split('.')[-1] == 'xlsx':
            df.to_excel(report_file, index=False)
        if output_format == 'df':
            return df
        supported_formats = ['csv', 'json', 'stata', 'pickle','html']
        for x in supported_formats:
            if output_format.lower() == x or report_file.split('.')[-1] == x:
                exec('df.to_' + x + '("'+report_file+'")')