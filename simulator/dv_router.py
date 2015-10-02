"""
Your awesome Distance Vector router for CS 168
"""

import sim.api as api
import sim.basics as basics


# We define infinity as a distance of 16.
INFINITY = 16

class DVRouter (basics.DVRouterBase):
  #NO_LOG = True # Set to True on an instance to disable its logging
  POISON_MODE = True # Can override POISON_MODE here
  DEFAULT_TIMER_INTERVAL = 5 # Can override this yourself for testing

  def __init__ (self):
    """
    Called when the instance is initialized.

    You probably want to do some additional initialization here.
    """
    self.distanceVectors = {} # Contains a list of distance vectors; {Node: {Via Node: [Distance, TimeLastUpdated]}}

    self.portsToLatencies = {} # Contains a list of ports mapped to their latencies (neighboring ports only!)
    self.portsToEnts = {} # Contains a list of ports mapped to the entities they lead to (neighboring entities only!)
    self.entsToPorts = {} # Given an neighboring entity, returns the port that leads to it from the current entity.

    self.start_timer() # Starts calling handle_timer() at correct rate

  def handle_link_up (self, port, latency):
    """
    Called by the framework when a link attached to this Entity goes up.

    The port attached to the link and the link latency are passed in.
    """
    # Notify the entity on the other side that we exist - the other entity will do the same for us.
    # Also set up our port latencies here. We're assuming that they won't change midway (unless the port expires, at which point they'll be INFINITY)
    self.portsToLatencies[port] = latency
    self.send(basics.RoutePacket(None, latency), port)

  def nullify_port (self, port):
    """
    Turns a port's latency to INFINITY if appropriate and updates the distance matrix and sends updates if we want to poison the route
    """
    self.portsToLatencies[port] = INFINITY
    affectedEntity = self.portsToEnts[port]
    self.set_distance_vectors(affectedEntity, affectedEntity, INFINITY)

    # We need to modify all of the paths that use affected entity as an intermediary node as well.
    for destination in self.distanceVectors:
      distanceVector = self.distanceVectors[destination]
      for viaEntity, distanceList in distanceVector.iteritems():
        if viaEntity == affectedEntity:
          self.set_distance_vectors(destination, affectedEntity, INFINITY)

  def handle_link_down (self, port):
    """
    Called by the framework when a link attached to this Entity does down.

    The port number used by the link is passed in.
    """
    # Set this port's latency to INFINITY as well as our distance matrix
    self.nullify_port(port)

  def handle_rx (self, packet, port):
    """
    Called by the framework when this Entity receives a packet.

    packet is a Packet (or subclass).
    port is the port number it arrived on.

    You definitely want to fill this in.
    """
    #self.log("RX %s on %s (%s)", packet, port, api.current_time())
    if isinstance(packet, basics.RoutePacket):
      # If we get a packet with no destination, we know it comes from handle_link_up and can establish neighborly relations
      if packet.destination == None:
        self.set_distance_vectors(packet.src, packet.src, packet.latency)
        self.portsToEnts[port] = packet.src
        self.entsToPorts[packet.src] = port
      elif packet.destination != packet.src: # Useless information... this is always 0
        # Always update our distance vector table - we can figure out the best path later
        print("Destination: " + str(packet.destination) + " Source: " + str(packet.src))
        totalLatency = packet.latency + self.portsToLatencies[port]
        self.set_distance_vectors(packet.destination, packet.src, totalLatency)
    elif isinstance(packet, basics.HostDiscoveryPacket):

      self.set_distance_vectors(packet.src, packet.src, 0)
      self.portsToEnts[port] = packet.src
      self.entsToPorts[packet.src] = port
    else:
      # Totally wrong behavior for the sake of demonstration only: send
      # the packet back to where it came from!
      bestPort = self.get_best_port_to_entity(packet.dst)
      if self.is_valid_port(bestPort):
        self.send(packet, port=bestPort)

  def set_distance_vectors(self, destination, viaEntity, distance):
    """
    Sets distanceVector[destination][viaEntity] = distance if the table exists.
    Creates the table if it doesn't. Also sends out updates where necessary.
    """
    if destination not in self.distanceVectors:
        self.distanceVectors[destination] = {}

    previousMinDistance = self.min_distance_to(destination)
    self.distanceVectors[destination][viaEntity] = [distance, api.current_time()]
    newMinDistance = self.min_distance_to(destination)

    # If the routing table changes, we want to send out the corresponding updates
    if previousMinDistance != newMinDistance:
        #print("Self: " + str(self) + "Destination: " + str(destination) + "; viaEntity: " + str(viaEntity) + str(previousMinDistance) + " is now " + str(newMinDistance))
        if self.POISON_MODE or not self.is_infinity(distance):
            self.send_packet_to_all_valid_neighbors(basics.RoutePacket(destination, distance))

  def handle_timer (self):
    """
    Called periodically.

    When called, your router should send tables to neighbors.  It also might
    not be a bad place to check for whether any entries have expired.
    """
    self.send_all_vectors_to_all_valid_neighbors()
    self.check_times()

  def check_times(self):
    """
    Expires all ports whose time last updated is 15 seconds between then and now.
    """
    for destination in self.distanceVectors:
        distanceVector = self.distanceVectors[destination]
        for viaEntity in distanceVector:
            # Don't expire host links or distances to yourself (who cares about that)
            if not isinstance(viaEntity, basics.BasicHost) and api.current_time() - distanceVector[viaEntity][1] >= 15 and destination != viaEntity:
                self.set_distance_vectors(destination, viaEntity, INFINITY)

  def send_all_vectors_to_all_valid_neighbors(self):
    """
    Sends the all distance vectors to all valid (non-host) neighbors
    """
    for port, entity in self.portsToEnts.iteritems():
        if not isinstance(entity, basics.BasicHost): # We don't want to send this information to hosts
            self.send_all_vectors_to(port)

  def send_packet_to_all_valid_neighbors(self, packet):
    """
    Sends the specified packet to all valid (non-host) neighbors
    """
    for port, entity in self.portsToEnts.iteritems():
        if not isinstance(entity, basics.BasicHost): # We don't want to send this information to hosts
            self.send(packet, port)

  def send_all_vectors_to(self, port):
    """
    Sends all current distance vector information to the specified port
    """
    for destination in self.distanceVectors:
        minDistance = self.min_distance_to(destination)
        if (self.POISON_MODE or not self.is_infinity(minDistance)) and (self.portsToEnts[port] not in self.distanceVectors[destination] or self.distanceVectors[destination][self.portsToEnts[port]][0] != minDistance):
            self.send(basics.RoutePacket(destination, minDistance), port)

  def get_best_port_to_entity(self, entity):
    """
    Returns the best port to reach the destination with the minimum distance

    Returns -1 if there are no valid ports (all are INFINITY or none exist)
    """
    if entity in self.distanceVectors:
        distanceVector = self.distanceVectors[entity]
        # Here we pull out the entity whose stored distance is the lowest
        if distanceVector:
            minDistanceKey = min(distanceVector, key=lambda x: distanceVector[x][0])
            minDistance = distanceVector[minDistanceKey][0]
            if not self.is_infinity(minDistance):
                bestPort = self.entsToPorts[minDistanceKey]
                return bestPort
    else:
        return -1

  def min_distance_to(self, destination):
    """
    Returns the min_distance_to a given destination or INFINITY if one cannot be found
    """
    minDistance = INFINITY
    if destination in self.distanceVectors:
        distanceVector = self.distanceVectors[destination]
        if distanceVector:
            minDistanceKey = min(self.distanceVectors[destination], key=lambda x: distanceVector[x][0])
            minDistance = distanceVector[minDistanceKey][0]
    return minDistance

  def is_valid_port(self, port):
    return port > -1

  def is_infinity(self, value):
    """
    Called to determine if a value is infinity or greater.
    """
    return value >= 16
