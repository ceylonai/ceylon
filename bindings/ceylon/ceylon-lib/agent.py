from ceylon import *
class Agent():
    def __init__(self, name, is_leader, id, workspace_id):
        self._name = name
        self._is_leader = is_leader
        self._id = id
        self._workspace_id = workspace_id