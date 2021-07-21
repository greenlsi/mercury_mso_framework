from typing import Tuple


class NodeLocation:
    def __init__(self, node_id: str, location: Tuple[float, ...]):
        """
        Message containing the new location of a node.
        :param node_id: ID of the node that change its location
        :param location: new location of the node
        """
        self.node_id: str = node_id
        self.location: Tuple[float, ...] = location
