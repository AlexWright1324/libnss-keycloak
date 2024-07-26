from dataclasses import dataclass
from keycloak import KeycloakAdmin

from .env import validChars, IDString, Default
from .kc import getIDSet, getNextAvailableID


@dataclass
class Group:
    gid: int
    name: str
    members: list[str]

    def toGroup(self, config: Default):
        # name:password:gid:members
        return ":".join([self.name, "!", str(self.gid), ",".join(self.members)])


class GroupList:
    def __init__(self):
        self.group: list[Group] = []

    def sanitise(self, value: str) -> str:
        return "".join(char for char in value if char in validChars)

    def add(self, gid: int, name: str, members: list[str]):
        sanName = self.sanitise(name)

        if len(sanName) == 0:
            print("Group name cannot be empty")
            return

        if (check := self.getByID(gid)) is not None:
            print(f"GID {gid} already exists for {check.name} when adding {sanName}")
            return

        if self.getByName(sanName) is not None:
            print(f"Group name {sanName} already exists")
            return

        self.group.append(Group(gid, sanName, members))

    def getAll(self) -> list[Group]:
        return self.group

    def getByID(self, gid: str | int) -> Group | None:
        for group in self.group:
            if str(group.gid) == str(gid):
                return group
        return None

    def getByName(self, username: str) -> Group | None:
        for group in self.group:
            if group.name == username:
                return group
        return None

    async def populate(self, ka: KeycloakAdmin):
        kgroups = await ka.a_get_groups()
        IDSet = getIDSet(kgroups)
        for datalessGroup in kgroups:
            group = await ka.a_get_group(datalessGroup["id"])
            if {"name", "id"} <= group.keys():
                gid = None
                if "attributes" in group and IDString in group["attributes"]:
                    if group["attributes"][IDString][0].isdigit():
                        gid = int(group["attributes"][IDString][0])

                if gid is None:
                    gid = getNextAvailableID(IDSet)
                    IDSet.add(gid)

                    # Update in Keycloak
                    if "attributes" not in group:
                        group["attributes"] = {}
                    group["attributes"][IDString] = [str(gid)]
                    await ka.a_update_group(group["id"], group)

                members = []
                for user in await ka.a_get_group_members(group["id"]):
                    if "username" in user:
                        members.append(user["username"])

                self.add(gid, group["name"], members)
