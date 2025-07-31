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

from typing import (
    List,
    Optional,
)

from m5.objects import (
    AddrRange,
    IOXBar,
    Port,
)

from ...components.boards.se_binary_workload import SEBinaryWorkload
from ...utils.override import overrides
from ..cachehierarchies.abstract_cache_hierarchy import AbstractCacheHierarchy
from ..cachehierarchies.hybrid.abstract_classic_cache_hierarchy import (
    AbstractHybridCacheHierarchy,
)
from ..memory.abstract_memory_system import AbstractMemorySystem
from ..processors.abstract_generator import AbstractGenerator
from ..processors.abstract_processor import AbstractProcessor
from .abstract_board import AbstractBoard
from .abstract_system_board import AbstractSystemBoard


class HybridBoard(AbstractSystemBoard, SEBinaryWorkload):
    """This is a Testing Board used to run traffic generators on a simple
    architecture.

    To work as a traffic generator board, pass a generator as a processor.

    This board does not require a cache hierarchy (it can be ``none``) in which
    case the processor (generator) will be directly connected to the memory.
    The clock frequency is only used if there is a cache hierarchy or when
    using the GUPS generators.
    """

    def __init__(
        self,
        clk_freq: str,
        processor: AbstractProcessor,
        generator: AbstractGenerator,
        memory: AbstractMemorySystem,
        cache_hierarchy: Optional[AbstractCacheHierarchy],
    ) -> None:
        super().__init__(
            clk_freq=clk_freq,  # Only used if cache hierarchy or GUPS-gen
            processor=processor,
            memory=memory,
            cache_hierarchy=cache_hierarchy,
        )
        self.generator = generator
        self._set_fullsystem(False)

    def get_generator(self) -> "AbstractGenerator":
        return self.generator

    @overrides(AbstractSystemBoard)
    def _setup_memory_ranges(self) -> None:
        memory = self.get_memory()
        data_range = AddrRange(memory.get_size())
        memory.set_memory_range([data_range])

        # Add the address range for the IO
        self.mem_ranges = [data_range]  # All data

    @overrides(AbstractSystemBoard)
    def _setup_board(self) -> None:
        pass

    @overrides(AbstractSystemBoard)
    def has_io_bus(self) -> bool:
        return False

    @overrides(AbstractSystemBoard)
    def get_io_bus(self) -> IOXBar:
        raise NotImplementedError(
            "The TestBoard does not have an IO Bus. "
            "Use `has_io_bus()` to check this."
        )

    @overrides(AbstractSystemBoard)
    def get_dma_ports(self) -> List[Port]:
        return False

    @overrides(AbstractSystemBoard)
    def get_dma_ports(self) -> List[Port]:
        raise NotImplementedError(
            "The TestBoard does not have DMA Ports. "
            "Use `has_dma_ports()` to check this."
        )

    @overrides(AbstractSystemBoard)
    def has_coherent_io(self) -> bool:
        return False

    @overrides(AbstractSystemBoard)
    def get_mem_side_coherent_io_port(self):
        raise NotImplementedError(
            "SimpleBoard does not have any I/O ports. Use has_coherent_io to "
            "check this."
        )

    @overrides(AbstractSystemBoard)
    def _setup_memory_ranges(self) -> None:
        memory = self.get_memory()

        # The simple board just has one memory range that is the size of the
        # memory.
        self.mem_ranges = [AddrRange(memory.get_size())]
        memory.set_memory_range(self.mem_ranges)

    @overrides(AbstractSystemBoard)
    def has_dma_ports(self) -> bool:
        return False

    @overrides(AbstractBoard)
    def _connect_things(self) -> None:
        """Connects all the components to the board.

        The order of this board is always:

        1. Connect the memory.
        2. Connect the cache hierarchy.
        3. Connect the processor.

        Developers may build upon this assumption when creating components.

        .. note::

            * The processor is incorporated after the cache hierarchy due to a bug
            noted here: https://gem5.atlassian.net/browse/GEM5-1113. Until this
            bug is fixed, this ordering must be maintained.
            * Once this function is called ``_connect_things_called`` *must* be set
            to ``True``.
        """
        if not isinstance(
            self.get_cache_hierarchy(), AbstractHybridCacheHierarchy
        ):
            raise Exception(
                "The Hybrid board should use hybrid cache hierarchy"
            )
        super()._connect_things()

        if not self.get_cache_hierarchy():
            # If we have no caches, then there must be a one-to-one
            # connection between the generators and the memories.
            assert len(self.get_processor().get_cores()) == 1
            assert len(self.get_memory().get_mem_ports()) == 1
            self.get_processor().get_cores()[0].connect_dcache(
                self.get_memory().get_mem_ports()[0][1]
            )
        self._connect_things_called = True

    @overrides(AbstractBoard)
    def _post_instantiate(self):
        """Called to set up anything needed after ``m5.instantiate``."""
        super()._post_instantiate()
        self.get_generator()._post_instantiate()

    @overrides(AbstractBoard)
    def _pre_instantiate(self, full_system: Optional[bool] = None):
        """To be called immediately before ``m5.instantiate``. This is where
        ``_connect_things`` is executed by default and the root object is Root
        object is created and returned.

        :param full_system: Used to pass the full system flag to the board from
                            the Simulator module. **Note**: This was
                            implemented solely to maintain backawards
                            compatibility with while the Simululator module's
                            `full_system` flag is in state of deprecation. This
                            parameter will be removed when it is. When this
                            occurs whether a simulation is to be run in FS or
                            SE mode will be determined by the board set."""
        root = super()._pre_instantiate()
        # 1. Connect the memory, processor, and cache hierarchy.
        # 2. Create the root object
        # 3. Call any of the components' `_pre_instantiate` functions.
        # add generator setup

        # 4. Return the root object.
        return root
