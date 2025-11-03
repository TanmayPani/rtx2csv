import os
import shutil
from glob import iglob
from copy import deepcopy 
from itertools import zip_longest
from statistics import mean
from math import ceil

from datetime import datetime
from dataclasses import dataclass, field, asdict

import json
import csv

import argparse
from time import time

def grouper(iterable, n, *, incomplete='fill', fillvalue=None):
    "Collect data into non-overlapping fixed-length chunks or blocks."
    # grouper('ABCDEFG', 3, fillvalue='x') → ABC DEF Gxx
    # grouper('ABCDEFG', 3, incomplete='strict') → ABC DEF ValueError
    # grouper('ABCDEFG', 3, incomplete='ignore') → ABC DEF
    iterators = [iter(iterable)] * n
    match incomplete:
        case 'fill':
            return zip_longest(*iterators, fillvalue=fillvalue)
        case 'strict':
            return zip(*iterators, strict=True)
        case 'ignore':
            return zip(*iterators)
        case _:
            raise ValueError('Expected fill, strict, or ignore')


@dataclass
class RTXData:
    file_path : str
    #file_name : str = ""
    owner : str = ""
    version_number : str = ""
    file_type : str = ""
    velocity : float = 0.
    sample_rate : float = 0.
    sample_number : float = 0. 
    trigger_point : float = 0.
    trigger_interval : float = 0.
    actual_sample_rate : float = 0.
    flags : list[int] = field(default_factory = list, init=False)
    machine : str = ""
    serial_number : str = ""
    date : datetime = field(default_factory = datetime.now, init=False)
    by : str = ""
    axis : str = ""
    location : str = ""
    data : list[float] = field(default_factory = list, init=False)

    def get_data_interval(self):
        return 1./self.actual_sample_rate

    def read_header_dict(self, kv_map):
        self.owner = kv_map["Owner"]
        self.version_number    = kv_map["Version no"        ]
        self.file_type         = kv_map["File Type"         ]
        self.velocity            = float(kv_map["Velocity"          ])
        self.sample_rate         = float(kv_map["Sample rate"       ])
        self.sample_number       = float(kv_map["Sample no"         ])
        self.actual_sample_rate  = float(kv_map["Actual sample rate"])
        self.trigger_point       = float(kv_map["Trigger point"     ])
        self.trigger_interval    = float(kv_map["Trigger interval"  ])
        self.machine           = kv_map["Machine"           ]
        self.serial_number     = kv_map["Serial No"         ]
        self.by                = kv_map["By"                ]
        self.axis              = kv_map["Axis"              ]
        self.location          = kv_map["Location"          ]
        self.date              = datetime.strptime(kv_map["Date"], "%d/%m/%Y %I:%M:%S")
        self.flags             = [int(f) for f in kv_map["Flags"].split()]

    def header_dict(self):
        return {
            k : deepcopy(v) if not isinstance(v, datetime) else v.strftime("%d/%m/%Y %I:%M:%S")
            for k, v in self.__dict__.items() if k != "data"
        }

    def add(self, *args):
        self.data.extend(args)

    def __getitem__(self, i):
        return self.data[i]

    def __len__(self):
        return len(self.data)

def read_header_data(buffer, start_pos=0):
    header_dict = {}
    #start_pos = len(header_start)
    start_idx = start_pos 
    key = ""
    data_found = False
    while start_pos < len(buffer):
        if buffer[start_pos:start_pos+2] == b"::":
            start_pos+=2
            start_idx = start_pos 
            continue
        
        if buffer[start_pos:start_pos+2] == b": ":
            key = buffer[start_idx:start_pos].decode("utf-8").strip()
            start_pos += 2 
            start_idx=start_pos 
            continue
    
        if buffer[start_pos:start_pos+2] == b"\r\n":
            if key not in header_dict:
                val = str(buffer[start_idx:start_pos], "utf-8").strip()
                header_dict[key] = val
            start_pos += 2 
            start_idx=start_pos 
            continue

        if buffer[start_pos:start_pos+7] == b"Data:\r\n":
            start_pos += 7
            start_idx = start_pos
            data_found = True
            break

        start_pos += 1

    if not data_found:
        raise ValueError(
            "Please ensure chunk size >= header size !!"
            " increase chunk_size and try again."
        )

    return header_dict, start_pos

def read_rtx_file(file_path, chunk_size=8192, header_only=False):
    header_stub = b"HEADER::\r\n"
    eof_stub = b"EOF::\r\n"
    eof_found = False
    rtx_data = RTXData(file_path)
    with open(file_path, "rb") as f:
        last_pos = f.tell()
        ichunk = 0
        while chunk := f.read(chunk_size):
            ichunk += 1

            if chunk[:len(header_stub)] == header_stub:
                header_data, header_end_pos = read_header_data(
                    chunk, start_pos=len(header_stub),
                )

                rtx_data.read_header_dict(header_data)
                last_pos = f.seek(header_end_pos, last_pos)
                if header_only:
                    print(rtx_data)
                    break

                continue

            if chunk[:len(eof_stub)] == eof_stub:
                if eof_found:
                    break
                else:
                    raise IOError(
                        f"Found EOF stub {eof_stub} in chunk {ichunk}"
                        " before actually reaching EOF!"
                    )

            try:
                rtx_data.add(*memoryview(chunk).cast("d"))
                last_pos = f.tell()
            except TypeError:
                rtx_data.add(*memoryview(chunk[:-len(eof_stub)]).cast("d"))
                eof_found = True
                last_pos = f.seek(-len(eof_stub), os.SEEK_END)

    return rtx_data

def rtx_to_csv(
    rtx_file : str, 
    output_dir : str,
    *,
    reduce_factor : int = 1,
    reduction : str = "mean",
    chunk_size : int = 8192,
):
    file_name = os.path.basename(rtx_file)
    file_name_no_ext, ext = os.path.splitext(file_name)
    if ext != ".rtx":
        raise ValueError("Provided file is not an .rtx file")

    rtx_data = read_rtx_file(rtx_file, chunk_size)

    out_dir =  os.path.join(output_dir, file_name_no_ext)

    if os.path.isdir(out_dir):
        shutil.rmtree(out_dir)

    os.makedirs(out_dir)

    header_file = os.path.join(out_dir, "header.json")
    csv_file = os.path.join(out_dir, "data.csv")
    
    if reduce_factor > 1:
        groups = grouper(rtx_data.data, reduce_factor, fillvalue=None)
        match reduction:
            case "mean":
                rtx_data.data = [mean([d for d in group if d is not None]) for group in groups]
            case "drop":
                rtx_data.data = [group[0] for group in groups]
            case _:
                raise ValueError("Expected mean or drop")
        
        rtx_data.actual_sample_rate /= reduce_factor

    with open(header_file, "w") as hout:
        header = rtx_data.header_dict()
        header["file_type"] = "csv"
        header["file_path"] = csv_file
        
        json.dump(header, hout, indent=4)



    with open(csv_file, "w") as fout:
        writer = csv.writer(fout)
        #time_interval = rtx_data.get_data_interval()
        num_rows = len(rtx_data)
        timestamps =[row/rtx_data.actual_sample_rate for row in range(num_rows)] 
        writer.writerows([*zip(timestamps, rtx_data.data)])


def main(
    input, 
    output_dir, 
    **kwargs,
):
    nfiles = 0
    for file in iglob(input):
        rtx_to_csv(file, output_dir, **kwargs) 
        nfiles += 1
    return nfiles
    
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="convert .rtx files into .csv files")
    parser.add_argument("input", help="path to an .rtx file or a glob expression", type=str)
    parser.add_argument("output_dir", help="path to folder to store the output files in", type=str)
    parser.add_argument(
        "--reduceby", 
        help="factor to reduce sampling rate by", 
        type=int, default=1,
    )
    parser.add_argument(
        "--reduction", 
        help="how to apply reduction to sampling rate", 
        type=str, choices=["mean", "drop"], default="mean"
    )
    parser.add_argument(
        "--chunk_size", 
        help="amount of data (in bytes) to read at once from a .rtx file", 
        type=int, default=8192,
    )


    args = parser.parse_args()
    
    start_time = time()
    nfiles = main(
        args.input, 
        args.output_dir, 
        reduce_factor = args.reduceby, 
        reduction = args.reduction, 
        chunk_size = args.chunk_size, 
    )
    end_time = time()
    elapsed_time = end_time - start_time

    print(f"Converted {nfiles} files in {elapsed_time} time!")
 
        
        
        
