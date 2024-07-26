from dataclasses import dataclass
from keycloak import KeycloakAdmin

from .env import validChars, IDString, Default
from .kc import getIDSet, getNextAvailableID


@dataclass
class User:
    uid: int
    username: str
    firstName: str
    lastName: str

    def toPasswd(self, config: Default):
        # username:passwordEncrypted:uid:gid:GECOS:homeDir:shell
        return ":".join(
            [
                self.username,
                "x",
                str(self.uid),
                str(config.gid),
                " ".join(filter(None, [self.firstName, self.lastName])),
                f"{config.home}{self.username}",
                config.shell,
            ]
        )


class UserList:
    def __init__(self):
        self.users: list[User] = []

    def sanitise(self, value: str) -> str:
        return "".join(char for char in value if char in validChars)

    def add(self, uid: int, username: str, firstName: str, lastName: str):
        # TODO: Check sanUsername != username???
        sanUsername = self.sanitise(username)
        sanFirstName = self.sanitise(firstName)
        sanLastName = self.sanitise(lastName)

        if len(sanUsername) == 0:
            print("Username cannot be empty")
            return

        if (check := self.getByID(uid)) is not None:
            print(
                f"UID {uid} already exists for {check.username} when adding {sanUsername}"
            )
            return

        if self.getByUsername(sanUsername) is not None:
            print(f"Username {sanUsername} already exists")
            return

        self.users.append(User(uid, sanUsername, sanFirstName, sanLastName))

    def getAll(self) -> list[User]:
        return self.users

    def getByID(self, uid: str | int) -> User | None:
        for user in self.users:
            if str(user.uid) == str(uid):
                return user
        return None

    def getByUsername(self, username: str) -> User | None:
        for user in self.users:
            if user.username == username:
                return user
        return None

    async def populate(self, ka: KeycloakAdmin):
        kusers = await ka.a_get_users()
        IDSet = getIDSet(kusers)
        for user in kusers:
            if {"username", "firstName", "lastName"} <= user.keys():
                uid = None
                if "attributes" in user and IDString in user["attributes"]:
                    if user["attributes"][IDString][0].isdigit():
                        uid = int(user["attributes"][IDString][0])

                if uid is None:
                    uid = getNextAvailableID(IDSet)
                    IDSet.add(uid)

                    if "attributes" not in user:
                        user["attributes"] = {}
                    user["attributes"][IDString] = [str(uid)]
                    user["attributes"].pop("libnss-keycloak-unixUID", None)
                    await ka.a_update_user(user["id"], user)

                self.add(uid, user["username"], user["firstName"], user["lastName"])
