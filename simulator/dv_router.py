"""
Your awesome Distance Vector router for CS 168
"""

import sim.api as api
import sim.basics as basics


# We define infinity as a distance of 16.
INFINITY = 16


class DVRouter (basics.DVRouterBase):
  #NO_LOG = True # Set to True on an instance to disable its logging
  #POISON_MODE = True # Can override POISON_MODE here
  #DEFAULT_TIMER_INTERVAL = 5 # Can override this yourself for testing

  def __init__ (self):
    """
    Called when the instance is initialized.

    You probably want to do some additional initialization here.
    """
    self.portsToLatency = {} # For a given port, returns the latency - basically a list of connected edges
    self.routersToPort = {} # For a given router, returns the port that reaches the router with the lowest latency
    self.start_timer() # Starts calling handle_timer() at correct rate

  def handle_link_up (self, port, latency):
    """
    Called by the framework when a link attached to this Entity goes up.

    The port attached to the link and the link latency are passed in.
    """
    self.portsToLatency[port] = latency
    

  def handle_link_down (self, port):
    """
    Called by the framework when a link attached to this Entity does down.

    The port number used by the link is passed in.
    """
    self.portsToLatency.pop(port)
    
  def handle_rx (self, packet, port):
    """
    Called by the framework when this Entity receives a packet.

    packet is a Packet (or subclass).
    port is the port number it arrived on.

    You definitely want to fill this in.
    """
    #self.log("RX %s on %s (%s)", packet, port, api.current_time())
    if isinstance(packet, basics.RoutePacket):
          if packet.destination != None:
            if packet.destination not in self.routersToPorts or packet.latency + self.portsToLatency[port] < self.portsToLatency[self.routersToPort[packet.destination]]:
                self.routersToPorts[packet.destination] = port
                    
          else:
            self.routersToPorts[packet.src] = port
            self.portsToLatency[port] = packet.latency
        
    elif isinstance(packet, basics.HostDiscoveryPacket):
      pass
    else:
      # Totally wrong behavior for the sake of demonstration only: send
      # the packet back to where it came from!
      self.send(packet, port=port)

  def handle_timer (self):
    """
    Called periodically.

    When called, your router should send tables to neighbors.  It also might
    not be a bad place to check for whether any entries have expired.
    """
    for port in self.portsToLatency:
        if self.routersToPort:
            for router in self.routersToPort:
                destinationPort = self.routersToPort[router]
                latency = self.portsToLatency[destinationPort]
                self.send(RoutePacket(router, latency), destinationPort)
        else:
            latency = portsToLatency[port]
            self.send(RoutePacket(None, latency), port)

            
            