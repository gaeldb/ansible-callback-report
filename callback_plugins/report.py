import json
import csv
import os

from ansible.plugins.callback import CallbackBase
from ansible import constants as C


class CallbackModule(CallbackBase):
    CALLBACK_VERSION = 2.0
    CALLBACK_TYPE = 'aggregate'
    CALLBACK_NAME = 'gaeldb.callback.host_report'
    CALLBACK_NEEDS_ENABLED = True

    def __init__(self):
        super(CallbackModule, self).__init__()
        # can be json or csv
        self.CALLBACK_REPORT_FORMAT = os.getenv('CALLBACK_REPORT_FORMAT', 'csv').lower()
        self.CALLBACK_REPORT_FILENAME = os.getenv('CALLBACK_REPORT_FILENAME', f'result.{self.CALLBACK_REPORT_FORMAT}')
        self.CALLBACK_REPORT_DUMP = os.getenv('CALLBACK_REPORT_DUMP', 'True').lower()
        self.CALLBACK_REPORT_PRINT = os.getenv('CALLBACK_REPORT_PRINT', 'False').lower()
        self.fail_report = {}
        print("[INFO]: Callback report activated.")
        print(f"   → Callback dump is '{self.CALLBACK_REPORT_DUMP}' in '{self.CALLBACK_REPORT_FILENAME}'")
        print(f"   → Callback print is '{self.CALLBACK_REPORT_PRINT}'")

    def v2_runner_on_unreachable(self, result):
        self._fill_error_report(result)

    def v2_runner_on_failed(self, result, ignore_errors):
        self._fill_error_report(result)

    def v2_playbook_on_stats(self, stats):
        hosts = sorted(stats.processed.keys())
        summary = {}
        for h in hosts:
            t = stats.summarize(h)
            summary[h] = t
            if h in self.fail_report:
                summary[h].update(self.fail_report[h])
            else:
                summary[h].update({'fail_action': '', 'fail_report': ''})
        if self.CALLBACK_REPORT_FORMAT == 'csv':
            self._report_csv(summary)
        else:
            self._report_json(summary)

    def _fill_error_report(self, result):
        host = self.host_label(result)
        fail_result = result._result['msg']
        fail_ip = result._host.vars.get('ansible_host', result._host.address)
        fail_action = result.task_name
        self.fail_report[host] = {
            'fail_action': fail_action,
            'fail_result': fail_result,
            'fail_ip': fail_ip,
        }

    def _report_csv(self, summary):
        fields = [
            "hostname",
            "ok",
            "failures",
            "unreachable",
            "changed",
            "skipped",
            "rescued",
            "ignored",
            "fail_action",
            "fail_report",
            "fail_ip",
        ]
        list_ = []
        for k, v in summary.items():
            line = {"hostname": k}
            line.update(v)
            list_.append(line)

        if self.CALLBACK_REPORT_PRINT == 'true':
            header = ''
            for f in fields:
                header += f'{f},'
            print(header[:-1])
            for res in list_:
                row = []
                for k,v in res.items():
                    row.append(str(v))
                print(*row, sep=",")

        if self.CALLBACK_REPORT_DUMP == 'true':
            with open(self.CALLBACK_REPORT_FILENAME, 'w') as fd:
                writer = csv.writer(fd)
                writer.writerow(fields)
                for res in list_:
                    row = []
                    for k,v in res.items():
                        row.append(str(v))
                    writer.writerow(row)

    def _report_json(self, summary):
        if self.CALLBACK_REPORT_PRINT == 'true':
            print(summary)
        if self.CALLBACK_REPORT_DUMP == 'true':
            with open(self.CALLBACK_REPORT_FILENAME, 'w') as fd:
                json.dump(summary, fd, indent=2)
