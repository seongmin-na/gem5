# gem5/src/mem/Ramulator2.py
from m5.objects.AbstractMemory import *
from m5.params import *
from m5.SimObject import *


class Ramulator2(AbstractMemory):
    type = "Ramulator2"
    cxx_class = "gem5::memory::Ramulator2"
    cxx_header = "mem/ramulator2/ramulator2.hh"
    port = ResponsePort(
        "The port for receiving memory requests and sending responses"
    )
    # NOTE newly added to accommodate config file
    config_path = Param.String("", "--ramulator-config")
    output_dir = Param.String("", "--outdir")
