# Copyright (c) 2022 The Regents of the University of California.
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are
# met: redistributions of source code must retain the above copyright
# notice, this list of conditions and the following disclaimer;
# redistributions in binary form must reproduce the above copyright
# notice, this list of conditions and the following disclaimer in the
# documentation and/or other materials provided with the distribution;
# neither the name of the copyright holders nor the names of its
# contributors may be used to endorse or promote products derived from
# this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
# A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
# OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
# SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
# THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""
Hands-on Session 1: Modifying the base system.
-------------------------------------------
This is a completed renscript file.

This is a simple script to run the a binary program using the SimpleBoard.
We will use x86 ISA for this example. This script is partly taken from
configs/example/app/_library/arm-hello.py

* Limitations *
---------------
1. We are only simulating workloads with one CPU core.
2. The binary cannot accept any arguments.

Usage:
------

```
scons build/X86/app/.opt -j<num_proc>
./build/X86/app/.opt base-system.py --binary <path/to/binary>
```
"""

# Importing the required python packages here

import argparse
import os
from pathlib import Path

import m5
from m5.objects import Root
from m5.util import fatal

from gem5.components.boards.hybrid_board import HybridBoard
from gem5.components.boards.test_board import TestBoard
from gem5.components.cachehierarchies.classic.no_cache import NoCache
from gem5.components.cachehierarchies.classic.private_l1_cache_hierarchy import (
    PrivateL1CacheHierarchy,
)

# We import various parameters of the machine.
from gem5.components.cachehierarchies.classic.private_l1_private_l2_cache_hierarchy import (
    PrivateL1PrivateL2CacheHierarchy,
)
from gem5.components.cachehierarchies.hybrid.no_cache import HybridNoCache
from gem5.components.cachehierarchies.hybrid.private_l1_private_l2_cache_hierarchy import (
    HybridPrivateL1PrivateL2CacheHierarchy,
)
from gem5.components.memory.ramulator_2 import Ramulator2System

# We are using argparse to supply the path to the binary.
from gem5.components.memory.single_channel import SingleChannelDDR4_2400
from gem5.components.processors.base_cpu_processor import BaseCPUProcessor
from gem5.components.processors.cpu_types import CPUTypes
from gem5.components.processors.simple_core import SimpleCore
from gem5.components.processors.simple_switchable_processor import (
    SimpleSwitchableProcessor,
)

# We need to first determine which ISA that we want to use. Then we have to
# make sure that we are using the correct ISA while executing this script.
from gem5.isas import ISA
from gem5.resources.resource import (
    BinaryResource,
    CustomResource,
    obtain_resource,
)
from gem5.simulate.exit_event import ExitEvent

# We will use the new simulator module to simulate this task.
from gem5.simulate.simulator import Simulator
from gem5.utils.requires import requires

# Use
# memory = Ramulator2System("../example/DDR4.yaml", "ramulator_out", "2GB")
# memory = SingleChannelDDR4_2400()
memory = Ramulator2System(
    "/workspace/cent/ramulator2/GEM5_LPDDR6_PIM.yaml",
    "ramulator_out",
    "16GB",
)
from gem5.components.processors.linear_generator import LinearGenerator
from gem5.components.processors.random_generator import RandomGenerator
from gem5.components.processors.trace_generator import (
    TraceGenerator,
    TraceGeneratorCore,
)

l_generator = LinearGenerator(
    num_cores=1,
    duration="1ms",
    rate="1GB/s",
    block_size=32,
    min_addr=0,
    max_addr=1 << 10,
    rd_perc=100,
    data_limit=0,
)

t_generator = TraceGenerator(
    num_cores=1,
    duration="1ms",
    block_size=32,
    addr_offset=0,
    trace_file="/workspace/gem5/configs/ramulator/trace/trace_pim.bin",
    # trace_file="/workspace/gem5/configs/ramulator/trace/trace_type.bin",
    max_outstanding_reqs=64,
)

cache_hierarchy = NoCache()

motherboard = TestBoard(
    clk_freq="1GHz",
    generator=t_generator,
    memory=memory,
    cache_hierarchy=cache_hierarchy,
)

motherboard._pre_instantiate(full_system=False)
m5.instantiate()
t_generator.start_traffic()
print("Beginning simulation!")
exit_event = m5.simulate()
print(f"Exiting @ tick {m5.curTick()} because {exit_event.getCause()}.")
