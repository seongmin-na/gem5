#include "mem/ramulator2/ramulator2.hh"

#include "base/callback.hh"
#include "base/trace.hh"
#include "debug/Drain.hh"
#include "debug/Ramulator2.hh"
#include "sim/system.hh"

// spdlog collides with gem5...
#pragma push_macro("warn")
#undef warn

#include "ramulator2/src/base/base.h"
#include "ramulator2/src/base/config.h"
#include "ramulator2/src/base/request.h"
#include "ramulator2/src/frontend/frontend.h"
#include "ramulator2/src/memory_system/memory_system.h"

namespace gem5
{

namespace memory
{

PIMCommandType
Ramulator2::getPIMCommandType(const PacketPtr pkt)
  {

      if (pkt->cmd == CmdPimReadReq)      return PIMCommandType::PimRead;
      if (pkt->cmd == CmdPimReadReqAP)    return PIMCommandType::PimReadAP;
      if (pkt->cmd == CmdPimWriteReq)     return PIMCommandType::PimWrite;
      if (pkt->cmd == CmdPimWriteReqAP)   return PIMCommandType::PimWriteAP;
      if (pkt->cmd == CmdPimIvReadReqAP)  return PIMCommandType::PimIvRead4A;
      if (pkt->cmd == CmdPimOvReadReqAP)  return PIMCommandType::PimOvRead4A;
      if (pkt->cmd == CmdPimOvWriteReqAP) return PIMCommandType::PimOvWrite4A;
      if (pkt->cmd == CmdPimMacPb8)       return PIMCommandType::PimMacPb8;

      return PIMCommandType::Invalid;
  }

Ramulator2::Ramulator2(const Params &p) :
    AbstractMemory(p),
    port(name() + ".port", *this),
    config_path(p.config_path),
    output_dir(p.output_dir),
    retryReq(false), retryResp(false), startTick(0),
    nbrOutstandingReads(0), nbrOutstandingWrites(0),
    sendResponseEvent([this]{ sendResponse(); }, name()+".sendResponseEvent"),
    tickEvent([this]{ tick(); }, name()+".tickEvent")
{
    DPRINTF_F(Ramulator2, "Instantiated Ramulator2 \n");
    printf("[ramulator2.cc] config_path=%s\n",
            config_path.c_str());

    registerExitCallback([this]() {
        ramulator2_frontend->finalize();
        ramulator2_memorysystem->finalize();
    });
}

void
Ramulator2::init()
{
    AbstractMemory::init();

    if (!port.isConnected()) {
        fatal("Ramulator2 %s is unconnected!\n", name());
    } else {
        port.sendRangeChange();
    }

    YAML::Node config = Ramulator::Config::parse_config_file(config_path, {});
    ramulator2_frontend = Ramulator::Factory::create_frontend(config);
    ramulator2_memorysystem = Ramulator::Factory::create_memory_system(config);

    ramulator2_frontend->connect_memory_system(ramulator2_memorysystem);
    ramulator2_memorysystem->connect_frontend(ramulator2_frontend);

    // if (system()->cacheLineSize() != wrapper.burstSize())
    //    fatal("Ramulator2 burst size %d
    //    does not match cache line size %d\n",
    //           wrapper.burstSize(), system()->cacheLineSize());
}

void
Ramulator2::startup()
{
    startTick = curTick();
    DPRINTF_F(Ramulator2, "startup and schedule tickEvent\n");
    //kick off the clock ticks
    schedule(tickEvent, clockEdge());
    // schedule(tickEvent, 13121004000177);
    // schedule(tickEvent, 0);
}

void
Ramulator2::resetStats() {
    // wrapper.resetStats();
}

void
Ramulator2::sendResponse()
{
    assert(!responseQueue.empty());
    
    DPRINTF_F(Ramulator2, "Attempting to send response addr=0x%x pkt=%p\n", responseQueue.front()->getAddr(),responseQueue.front());;

    bool success = port.sendTimingResp(responseQueue.front());
    if (success) {
        responseQueue.pop_front();
        DPRINTF_F(Ramulator2, "Have %d read, %d write, \\
                                % d responses outstanding\n ",
                nbrOutstandingReads,
                nbrOutstandingWrites,
                responseQueue.size());

        if (!responseQueue.empty() && !sendResponseEvent.scheduled())
            schedule(sendResponseEvent, curTick());

        if (nbrOutstanding() == 0)
            signalDrainDone();
    } else {
        retryResp = true;

        DPRINTF_F(Ramulator2, "Waiting for response retry\n");

        assert(!sendResponseEvent.scheduled());
    }
}

unsigned int
Ramulator2::nbrOutstanding() const
{
    return nbrOutstandingReads + nbrOutstandingWrites +nbrOutstandingPIMs + responseQueue.size() +responseQueue.size();
}

void
Ramulator2::tick()
{
    // Only tick when it's timing mode
    if (system()->isTimingMode()) {
        ramulator2_memorysystem->tick();

        // is the connected port waiting for a retry, if so check the
        // state and send a retry if conditions have changed
        if (retryReq) {
            retryReq = false;
            port.sendRetryReq();
        }
    }

    schedule(tickEvent,
             curTick() +
                 ramulator2_memorysystem->get_tCK() * sim_clock::as_float::ns);
}

Tick
Ramulator2::recvAtomic(PacketPtr pkt)
{
    panic_if(pkt->cacheResponding(), "Should not see packets where cache "
             "is responding");

    access(pkt);
    return 50000;   // Arbitary latency of 50ns
}

void
Ramulator2::recvFunctional(PacketPtr pkt)
{
    pkt->pushLabel(name());
    functionalAccess(pkt);

    for (auto i = responseQueue.begin(); i != responseQueue.end(); ++i)
        pkt->trySatisfyFunctional(*i);

    pkt->popLabel();
}

bool
Ramulator2::recvTimingReq(PacketPtr pkt)
{
    DPRINTF_F(Ramulator2, "recvTimingReq: request %s addr %#x size %d, pkt %p\n",
            pkt->cmdString(), pkt->getAddr(), pkt->getSize(), pkt);

    panic_if(pkt->cacheResponding(), "Should not see packets where cache is responding");

    if (retryReq)
        return false;

    int cmd = static_cast<int>(getPIMCommandType(pkt));
    bool enqueue_success = false;

    // --- 일반 PIM READ ---
    if (pkt->isPIM() && !pkt->isPIMCtrl() && pkt->isRead()) {
        enqueue_success = ramulator2_frontend->
            receive_external_requests(cmd, pkt->getAddr(), 0,
            [this](Ramulator::Request& req) {
                auto& pkt_q = outstandingReads.find(req.addr)->second;
                PacketPtr pkt = pkt_q.front();
                pkt_q.pop_front();
                if (pkt_q.empty())
                    outstandingReads.erase(req.addr);
                --nbrOutstandingReads;
                accessAndRespond(pkt);
            });

        if (enqueue_success) {
            outstandingReads[pkt->getAddr()].push_back(pkt);
            ++nbrOutstandingReads;
        } else {
            retryReq = true;
        }

        return enqueue_success;
    }

    // --- 일반 PIM WRITE ---
    if (pkt->isPIM() && !pkt->isPIMCtrl() && pkt->isWrite()) {
        enqueue_success = ramulator2_frontend->
            receive_external_requests(cmd, pkt->getAddr(), 0,
            [this](Ramulator::Request& req) {
                auto& pkt_q = outstandingWrites.find(req.addr)->second;
                PacketPtr pkt = pkt_q.front();
                pkt_q.pop_front();
                if (pkt_q.empty())
                    outstandingWrites.erase(req.addr);
                --nbrOutstandingWrites;
                accessAndRespond(pkt);
            });

        if (enqueue_success) {
            outstandingWrites[pkt->getAddr()].push_back(pkt);
            ++nbrOutstandingWrites;
        } else {
            retryReq = true;
        }

        return enqueue_success;
    }

    // --- 제어성 PIM 명령 ---
    if (pkt->isPIM() && pkt->isPIMCtrl()) {
        enqueue_success = ramulator2_frontend->
            receive_external_requests(cmd, pkt->getAddr(), 0,
            [this](Ramulator::Request& req) {
                auto& pkt_q = outstandingPIMs.find(req.addr)->second;
                PacketPtr pkt = pkt_q.front();
                pkt_q.pop_front();
                if (pkt_q.empty())
                    outstandingPIMs.erase(req.addr);
                --nbrOutstandingPIMs;
                accessAndRespond(pkt);
            });

        if (enqueue_success) {
            outstandingPIMs[pkt->getAddr()].push_back(pkt);
            ++nbrOutstandingPIMs;
        } else {
            retryReq = true;
        }

        return enqueue_success;
    }

    // --- 일반 DRAM Read ---
    if (pkt->isRead()) {
        enqueue_success = ramulator2_frontend->
            receive_external_requests(cmd, pkt->getAddr(), 0,
            [this](Ramulator::Request& req) {
                auto& pkt_q = outstandingReads.find(req.addr)->second;
                PacketPtr pkt = pkt_q.front();
                pkt_q.pop_front();
                if (pkt_q.empty())
                    outstandingReads.erase(req.addr);
                --nbrOutstandingReads;
                accessAndRespond(pkt);
            });

        if (enqueue_success) {
            outstandingReads[pkt->getAddr()].push_back(pkt);
            ++nbrOutstandingReads;
        } else {
            retryReq = true;
        }

        return enqueue_success;
    }

    // --- 일반 DRAM Write ---
    if (pkt->isWrite()) {
        enqueue_success = ramulator2_frontend->
            receive_external_requests(cmd, pkt->getAddr(), 0,
            [this](Ramulator::Request& req) {
                auto& pkt_q = outstandingWrites.find(req.addr)->second;
                PacketPtr pkt = pkt_q.front();
                pkt_q.pop_front();
                if (pkt_q.empty())
                    outstandingWrites.erase(req.addr);
                --nbrOutstandingWrites;
                accessAndRespond(pkt);
            });

        if (enqueue_success) {
            outstandingWrites[pkt->getAddr()].push_back(pkt);
            ++nbrOutstandingWrites;
        } else {
            retryReq = true;
        }

        return enqueue_success;
    }

    // --- 예외: 지원하지 않는 명령 ---
    panic("Unsupported command: %s at 0x%x\n", pkt->cmdString(), pkt->getAddr());
}

void
Ramulator2::recvRespRetry()
{
    DPRINTF_F(Ramulator2, "Retrying\n");

    assert(retryResp);
    retryResp = false;
    sendResponse();
}

void
Ramulator2::accessAndRespond(PacketPtr pkt)
{
    DPRINTF_F(Ramulator2, "Access for address 0x%x pkt:%p\n", pkt->getAddr(),pkt);

    bool needsResponse = pkt->needsResponse();

    access(pkt);

    // turn packet around to go back to requestor if response expected
    if (needsResponse) {
        // access already turned the packet into a response
        assert(pkt->isResponse());

        // Assume frontend latency = 0
        Tick time = curTick() + pkt->headerDelay + pkt->payloadDelay;
        // Here we reset the timing of the packet before sending it out.
        pkt->headerDelay = pkt->payloadDelay = 0;

        DPRINTF_F(Ramulator2, "Queuing response for address 0x%x ptr:%p\n",
                pkt->getAddr(),pkt);

        // queue it to be sent back
        responseQueue.push_back(pkt);

        // if we are not already waiting for a retry, or are scheduled
        // to send a response, schedule an event
        if (!retryResp && !sendResponseEvent.scheduled())
            schedule(sendResponseEvent, time);
    } else {
        // queue the packet for deletion
        pendingDelete.reset(pkt);
    }
}


Port&
Ramulator2::getPort(const std::string &if_name, PortID idx)
{
    if (if_name != "port") {
        return ClockedObject::getPort(if_name, idx);
    } else {
        return port;
    }
}

DrainState
Ramulator2::drain()
{
    // check our outstanding reads and writes and if any they need to
    // drain
    return nbrOutstanding() != 0 ? DrainState::Draining : DrainState::Drained;
}

Ramulator2::MemorySystemPort::MemorySystemPort(const std::string& _name,
                                 Ramulator2& _ramulator2)
    : ResponsePort(_name), ramulator2(_ramulator2)
{ }


} // namespace memory
} // namespace gem5

#pragma pop_macro("warn")
