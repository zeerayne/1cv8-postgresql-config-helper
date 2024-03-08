import argparse
import os
import time

from enum import Enum


class StorageType(Enum):
    ssd = "ssd"
    hdd = "hdd"

    def __str__(self):
        return self.value


parser = argparse.ArgumentParser(
    description="Appends additional keyboard layout shortcuts to kitty.conf"
)
parser.add_argument(
    "--config",
    type=str,
    dest="config",
    help="Config file to edit",
)
parser.add_argument(
    "--mem",
    type=str,
    dest="mem",
    help="Amount of RAM dedicated to PostgreSQL. Accepted in PostgreSQL-like notation i.e. 4096MB, 4GB ...",
)
parser.add_argument(
    "--cpu",
    type=int,
    dest="cpu",
    default=os.cpu_count(),
    help="CPU core count dedicated to PostgreSQL. Default to all available cores",
)
parser.add_argument(
    "--storage",
    type=StorageType,
    choices=list(StorageType),
    dest="storage",
    default=StorageType.ssd,
    help="Storage type used for PostgreSQL. Default is ssd",
)
parser.add_argument(
    "--disable-synchronous-commit",
    dest="synchronous_commit",
    action="store_false",
    help="Disabling synchronous commit increase performance in risk of data loss",
)
parser.add_argument(
    "--enable-group-commit",
    dest="group_commit",
    action="store_true",
    help="Enable group commits. Use for >= 1000 TPS instances",
)
parser.add_argument(
    "--no-backup",
    dest="backup",
    action="store_false",
    help="No backup file will be created",
)

args = parser.parse_args()


def unit_list(radix_suffix: str = ""):
    return list(
        map(lambda item: item + radix_suffix, ["K", "M", "G", "T", "P", "E", "Z"])
    )


def sizeof_fmt(
    value: int, suffix: str = "B", radix: int = 1024, radix_suffix: str = ""
):
    for unit in [""] + unit_list(radix_suffix):
        if abs(value) < radix:
            return f"{value:.0f}{unit}{suffix}"
        value /= radix
    return f'{value:.0f}{"Y"+ radix_suffix}{suffix}'


def sizeof_parse(
    value: str, suffix: str = "B", radix: int = 1024, radix_suffix: str = ""
):
    wo_suffix = value.replace(suffix, "")
    if wo_suffix.isnumeric():
        return int(wo_suffix)
    rank = 1
    for unit in unit_list(radix_suffix):
        if unit in wo_suffix:
            return int(wo_suffix.replace(unit, "")) * (radix**rank)
        rank += 1
    raise ValueError(f"Couldn't parse value to int: {value}")


config_file_path = args.config
config_directory, config_file_name = os.path.split(config_file_path)

mem = sizeof_parse(args.mem)
cpu = args.cpu
storage = args.storage

enable_group_commit = args.group_commit
disable_synchronous_commit = not args.synchronous_commit

shared_buffers = mem / 4
random_page_cost = 1.1 if storage == StorageType.ssd else 2.0
effective_io_concurrency = 2 if storage == StorageType.ssd else 1

configmap = {
    "row_security": "off",
    "ssl": "off",
    "shared_buffers": sizeof_fmt(shared_buffers),
    "temp_buffers": "256MB",
    "work_mem": sizeof_fmt(mem / 64),
    "maintenance_work_mem": sizeof_fmt(mem / 16),
    "fsync": "on",
    "synchronous_commit": "on",
    "checkpoint_completion_target": 0.9,
    "min_wal_size": "2GB",
    "max_wal_size": "4GB",
    "commit_delay": 0,
    "commit_siblings": 5,
    "bgwriter_delay": "20ms",
    "bgwriter_lru_multiplier": 4.0,
    "bgwriter_lru_maxpages": 400,
    "autovacuum": "on",
    "autovacuum_max_workers": max(cpu / 4, 4),
    "autovacuum_naptime": "20s",
    "max_files_per_process": 8000,
    "effective_cache_size": sizeof_fmt(mem - shared_buffers),
    "random_page_cost": random_page_cost,
    "from_collapse_limit": 20,
    "join_collapse_limit": 20,
    "geqo": "on",
    "geqo_threshold": 12,
    "effective_io_concurrency": effective_io_concurrency,
    "standard_conforming_strings": "off",
    "escape_string_warning": "off",
    "max_locks_per_transaction": 1000,
    "max_connections": 500,
}

if enable_group_commit:
    configmap.update(
        {
            "commit_delay": 1000,
        }
    )

if disable_synchronous_commit:
    configmap.update(
        {
            "synchronous_commit": "off",
        }
    )

# read config file all lines
with open(config_file_path) as f:
    lines = f.readlines()
# for each line search mapping line and add additional line with mapping
new_lines = []
for line in lines:
    # if line doesn't contain known parameter
    if not any(line.replace("#", "").startswith(f"{key} = ") for key in configmap.keys()):
        new_lines.append(line)
        continue
    # remove comment from line
    if line.startswith("#"):
        line = line[1:]
    # line contains map the first thing is to find mapping parts
    line_parts = line.split(" ")
    parameter_name = line_parts[0]
    new_line = f"{parameter_name} = {configmap[parameter_name]}{os.linesep}"
    new_lines.append(new_line)
# create backup
if args.backup:
    with open(
        os.path.join(config_directory, f"{config_file_name}.{time.time()}.backup"), "w"
    ) as f:
        f.writelines(lines)
# write new config file
with open(config_file_path, "w") as f:
    f.writelines(new_lines)
    