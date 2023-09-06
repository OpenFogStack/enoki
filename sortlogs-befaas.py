#!/usr/bin/env python3

import datetime
import enum
import os
import sys
import typing


# enum for event types
class EventType(enum.Enum):
    START = 0
    END = 1
    CALL_START = 2
    CALL_END = 3
    DB_GET_START = 4
    DB_GET_END = 5
    DB_SET_START = 6
    DB_SET_END = 7


class FunctionCall:
    def __init__(self, function: str, xexecution: str, xcontext: str):
        self.function = function
        self.xexecution = xexecution
        self.xcontext = xcontext

        self.start_time: typing.Optional[datetime.datetime] = None
        self.end_time: typing.Optional[datetime.datetime] = None
        self.total_time: typing.Optional[float] = None
        self.proc_time: typing.Optional[float] = None
        self.calls: typing.Dict[
            str, typing.Dict[str, typing.Union[datetime.datetime, float, str]]
        ] = {}
        self.db_calls: typing.Dict[
            str, typing.Dict[str, typing.Union[datetime.datetime, float, str]]
        ] = {}

    def _update(self) -> None:
        # update the total time
        if self.start_time is not None and self.end_time is not None:
            self.total_time = (self.end_time - self.start_time).total_seconds()

        # update the function call times
        for call in self.calls:
            if "start" in self.calls[call] and "end" in self.calls[call]:
                self.calls[call]["total"] = (
                    self.calls[call]["end"] - self.calls[call]["start"]  # type: ignore
                ).total_seconds()

        # for a client, also check to update total time
        if self.function == "client" and len(self.calls) > 0:
            # assume that the first call is the start of the client
            if "total" in self.calls[list(self.calls.keys())[0]]:
                self.total_time = self.calls[list(self.calls.keys())[0]]["total"]  # type: ignore
                self.proc_time = self.total_time
                self.xpair = self.calls[list(self.calls.keys())[0]]["xpair"]

        # update the db call times
        for call in self.db_calls:
            if "start" in self.db_calls[call] and "end" in self.db_calls[call]:
                self.db_calls[call]["total"] = (
                    self.db_calls[call]["end"] - self.db_calls[call]["start"]  # type: ignore
                ).total_seconds()

        # update the processing time
        # processing time is the total time minus the time spent in function calls and db calls
        self.proc_time = self.total_time

        if self.proc_time is None:
            return

        self.proc_time -= sum(  # type: ignore
            [
                self.calls[call]["total"]  # type: ignore
                for call in self.calls
                if "total" in self.calls[call]
            ]
        )
        self.proc_time -= sum(  # type: ignore
            [
                self.db_calls[call]["total"]  # type: ignore
                for call in self.db_calls
                if "total" in self.db_calls[call]
            ]
        )

    def add_event(
        self,
        xpair: str,
        event: EventType,
        timestamp: datetime.datetime,
        targetfunc: typing.Optional[str] = None,
    ) -> None:
        if event == EventType.START:
            self.start_time = timestamp
            self.xpair = xpair
        elif event == EventType.END:
            self.end_time = timestamp
        elif event == EventType.CALL_START:
            if targetfunc is None:
                raise ValueError("Target function must be specified")

            if not targetfunc in self.calls:
                self.calls[targetfunc] = {}

            self.calls[targetfunc]["start"] = timestamp
            self.calls[targetfunc]["xpair"] = xpair

        elif event == EventType.CALL_END:
            if targetfunc is None:
                raise ValueError("Target function must be specified")

            if not targetfunc in self.calls:
                self.calls[targetfunc] = {}

            self.calls[targetfunc]["end"] = timestamp
            self.calls[targetfunc]["xpair"] = xpair

        elif event == EventType.DB_GET_START:
            if not xpair in self.db_calls:
                self.db_calls[xpair] = {}

            self.db_calls[xpair]["start"] = timestamp
            self.db_calls[xpair]["xpair"] = xpair
            self.db_calls[xpair]["type"] = "get"

        elif event == EventType.DB_GET_END:
            if not xpair in self.db_calls:
                self.db_calls[xpair] = {}

            self.db_calls[xpair]["end"] = timestamp
            self.db_calls[xpair]["xpair"] = xpair
            self.db_calls[xpair]["type"] = "get"

        elif event == EventType.DB_SET_START:
            if not xpair in self.db_calls:
                self.db_calls[xpair] = {}

            self.db_calls[xpair]["start"] = timestamp
            self.db_calls[xpair]["xpair"] = xpair
            self.db_calls[xpair]["type"] = "set"

        elif event == EventType.DB_SET_END:
            if not xpair in self.db_calls:
                self.db_calls[xpair] = {}

            self.db_calls[xpair]["end"] = timestamp
            self.db_calls[xpair]["xpair"] = xpair
            self.db_calls[xpair]["type"] = "set"

        else:
            raise ValueError("Unknown event type")

        self._update()

    def report_string(self) -> str:
        # string representation of a function call as multiple lines
        # function,xcontext,xpair,time_type,time
        if self.total_time is None or self.proc_time is None:
            print("Warning: total time or proc time is None", file=sys.stderr)
            print(self.__dict__, file=sys.stderr)
            return ""

        s = f"{self.function},{self.xcontext},{self.xexecution},{self.xpair},total,{self.total_time}"
        s += f"\n{self.function},{self.xcontext},{self.xexecution},{self.xpair},proc,{self.proc_time}"

        for call in self.calls:
            if "total" in self.calls[call]:
                s += f"\n{self.function},{self.xcontext},{self.xexecution},{self.calls[call]['xpair']},call-{call},{self.calls[call]['total']}"
            else:
                print(self.calls[call], file=sys.stderr)
                print("Warning: call without total time", file=sys.stderr)

        for call in self.db_calls:
            if "total" in self.db_calls[call]:
                s += f"\n{self.function},{self.xcontext},{self.xexecution},{self.db_calls[call]['xpair']},db-{self.db_calls[call]['type']},{self.db_calls[call]['total']}"
            else:
                print(self.db_calls[call], file=sys.stderr)
                print("Warning: db call without total time", file=sys.stderr)

        return s


class Operation:
    def __init__(
        self,
        function: str,
        xpair: str,
        xexecution: str,
        xcontext: str,
        event: str,
        timestamp: datetime.datetime,
    ):
        self.function = function
        self.xpair = xpair
        self.xexecution = xexecution
        self.xcontext = xcontext
        self.event = event
        self.timestamp = timestamp

    def __str__(self) -> str:
        # string representation of a line
        s = f"{self.timestamp.isoformat()},{self.function},{self.xpair},{self.xexecution},{self.xcontext},{self.event}"
        return s


def getop(line: str) -> typing.Optional[Operation]:
    # split the line into its components
    try:
        function, handler, stream, timestamp, linetype, content = line.split(" ", 5)

    except ValueError as e:
        # if the line is not formatted correctly
        # print(f"Line is not formatted correctly: {line}")
        # print(e)
        return None

    if linetype != "perf":
        # if the line is not a performance line
        # print(f"Line is not a performance line: {line} (type {linetype})")
        return None

    # parse timestamp of format 2023-08-23T09:16:15.408602142Z
    t = datetime.datetime.fromisoformat(timestamp)

    # parse content
    xpair, xexecution, xcontext, event = content.split(" ", 3)

    return Operation(function, xpair, xexecution, xcontext, event, t)


class LogLine:
    def __init__(self, line: str):
        # logic to make a line
        try:
            function, handler, stream, timestamp, content = line.split(" ", 4)
        except ValueError:
            # if the line is not formatted correctly
            raise ValueError(f"Line is not formatted correctly: {line}")

        self.function = function.split("=")[1]
        self.handler = handler.split("=")[1]
        self.stream = stream.split("=")[1]

        # parse timestamp of format 2023-08-23T09:16:15.408602142Z
        self.timestamp = datetime.datetime.fromisoformat(timestamp)

        # parse content
        # type can be "perf", "debug", or "other"
        if content.startswith("BEFAAS"):
            self.type = "perf"
            try:
                _, timestamp, _, xpair, xexecution, xcontext, event = content.split(
                    ";", 6
                )
                self.timestamp = datetime.datetime.fromisoformat(timestamp)
            except ValueError:
                # if the line is not formatted correctly
                raise ValueError(f"Line is not formatted correctly: {line}")

            self.xpair = xpair
            self.xexecution = xexecution
            self.xcontext = xcontext
            self.event = event

        elif content.startswith("DEBUG"):
            self.type = "debug"
            try:
                _, _, _, event = content.split(";", 3)
            except ValueError:
                # if the line is not formatted correctly
                raise ValueError(f"Line is not formatted correctly: {line}")
            self.event = event

        else:
            self.type = "other"
            self.event = content

    def __str__(self) -> str:
        # string representation of a line
        s = f"{self.function} {self.handler} {self.stream} {self.timestamp.isoformat()} {self.type}"

        if "xpair" in self.__dict__:
            s += f" {self.xpair}"

        if "xexecution" in self.__dict__:
            s += f" {self.xexecution}"

        if "xcontext" in self.__dict__:
            s += f" {self.xcontext}"

        # truncate event if it is too long
        # max_len = 100
        max_len = 100000000000
        if len(self.event) > max_len:
            s += f" {self.event[:max_len]}..."
        else:
            s += f" {self.event}"

        return s

    def __lt__(self, other: "LogLine") -> bool:
        # compare two lines
        # by timestamp
        if self.timestamp < other.timestamp:
            return True

        return False


if __name__ == "__main__":
    # two positional arguments: input folder and output folder
    if len(sys.argv) != 3:
        print("Usage: sortlogs-befaas.py <input dir> <output dir>")
        sys.exit(1)

    input_dir = sys.argv[1]
    output_dir = sys.argv[2]

    # create output dir if it does not exist
    os.makedirs(output_dir, exist_ok=True)

    # get all files in the input dir
    input_files = os.listdir(input_dir)

    for input_f in input_files:
        # get the full path of the input file
        input_file = os.path.join(input_dir, input_f)

        # add "-sorted" to the filename
        input_filename, input_fileext = os.path.splitext(input_f)
        output_file = os.path.join(
            output_dir, input_filename + "-sorted" + input_fileext
        )

        print(f"Processing {input_file}")

        # read the file
        with open(input_file) as f:
            logs = f.readlines()

        original_length = len(logs)

        # remove whitespace characters like `\n` at the end of each line
        logs = [x.strip() for x in logs]

        # remove empty lines
        logs = list(filter(None, logs))

        # remove unreadable lines
        # everything that has NULL bytes in it
        logs = [x for x in logs if "\x00" not in x]

        # parse the lines
        parsed_logs = [LogLine(line) for line in logs]

        new_length = len(parsed_logs)

        print(f"Removed {original_length - new_length} lines")

        # sort the lines
        sorted_logs = sorted(parsed_logs)

        printed_logs = [str(line) + "\n" for line in sorted_logs]

        print(f"Done sorting logs, have {len(printed_logs)} lines")

        # remove whitespace characters like `\n` at the end of each line
        trim_logs = [x.strip() for x in printed_logs]

        # remove empty lines
        trim_logs = list(filter(None, trim_logs))

        # remove unreadable lines
        # everything that has NULL bytes in it
        trim_logs = [x for x in trim_logs if "\x00" not in x]

        # parse the lines
        parsed_trim_logs = [getop(line) for line in trim_logs]

        # remove None
        parsed_trim_logs = [x for x in parsed_trim_logs if x is not None]

        printed_trim_logs = [str(line) + "\n" for line in parsed_trim_logs]

        ## calclogs.py
        # trim whitespace
        calc_lines = [x.strip() for x in printed_trim_logs]

        # create a dict of function calls
        # key is the xcontext and the function name

        calls: typing.Dict[str, FunctionCall] = {}

        for line in calc_lines:
            # split the line into its components
            try:
                timestamp, function, xpair, xexecution, xcontext, event = line.split(
                    ",", 5
                )

            except ValueError as e:
                # if the line is not formatted correctly
                print(f"Line is not formatted correctly: {line}")
                continue

            # parse timestamp of format 2023-08-23T09:16:15.408602142Z
            t = datetime.datetime.fromisoformat(timestamp)

            et: EventType = EventType.START
            tf: typing.Optional[str] = None
            # get the event type
            if event.startswith("start-call"):
                et = EventType.CALL_START
                tf = event.split("-")[2]
            elif event.startswith("end-call"):
                et = EventType.CALL_END
                tf = event.split("-")[2]
            elif event.startswith("start-db-get"):
                et = EventType.DB_GET_START
            elif event.startswith("end-db-get"):
                et = EventType.DB_GET_END
            elif event.startswith("start-db-set"):
                et = EventType.DB_SET_START
            elif event.startswith("end-db-set"):
                et = EventType.DB_SET_END
            elif event == "start":
                et = EventType.START
            elif event == "end":
                et = EventType.END
            else:
                print(f"Unknown event type: {event}")
                continue

            # create a key for the function call
            key = f"{function} {xexecution}"

            # create a new function call if it does not exist
            if not key in calls:
                calls[key] = FunctionCall(function, xexecution, xcontext)

            # add the event to the function call
            calls[key].add_event(xpair, et, t, targetfunc=tf)

        # print the results
        # print("function,xcontext,xexecution,xpair,time_type,time")

        calls_list = list(calls.keys())
        formated_calls = [calls[call].report_string() + "\n" for call in calls]
        formated_calls = [x for x in formated_calls if x.strip() != ""]

        print(
            f"Removed {len(calls_list) - len(formated_calls)} calls with None total time",
            file=sys.stderr,
        )

        # for call in formated_calls:
        # print(call)

        with open(output_file, "w") as f:
            print("function,xcontext,xexecution,xpair,time_type,time", file=f)
            f.writelines(formated_calls)
