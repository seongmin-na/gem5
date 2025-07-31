# Copyright (c) 2021 The Regents of the University of California
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

from typing import List

from ...utils.override import overrides
from .abstract_generator import (
    AbstractGenerator,
    partition_range,
)
from .trace_generator_core import TraceGeneratorCore


class TraceGenerator(AbstractGenerator):
    def __init__(
        self,
        num_cores: int = 1,
        duration: str = "1ms",
        block_size: int = 64,
        addr_offset: int = 0,
        trace_file: str = "",
        max_outstanding_reqs: int = 64,
    ) -> None:
        if num_cores > 1:
            raise ValueError("Current trace generator only support 1 core")
        super().__init__(
            cores=self._create_cores(
                num_cores=num_cores,
                duration=duration,
                block_size=block_size,
                addr_offset=addr_offset,
                trace_file=trace_file,
                max_outstanding_reqs=max_outstanding_reqs,
            )
        )
        """The Trace generator

        This class defines an external interface to create a list of Trace
        generator cores that could replace the processing cores in a board.

        :param num_cores: The number of Trace generator cores to create.
        :param duration: The duration of time for which the generator generates
                         traffic. Must be a string containing a positive number
                         and some unit. For example, "1ms".
        :param block_size: The number of bytes to be read/written with each
                           request.
        """

    def _create_cores(
        self,
        num_cores: int,
        duration: str,
        block_size: int,
        addr_offset: int,
        trace_file: str = "",
        max_outstanding_reqs: int = 64,
    ) -> List[TraceGeneratorCore]:
        return [
            TraceGeneratorCore(
                duration=duration,
                block_size=block_size,
                addr_offset=addr_offset,
                trace_file=trace_file,
                max_outstanding_reqs=max_outstanding_reqs,
            )
            for i in range(num_cores)
        ]

    @overrides(AbstractGenerator)
    def start_traffic(self) -> None:
        for core in self.cores:
            core.start_traffic()
