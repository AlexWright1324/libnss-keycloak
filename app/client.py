import asyncio
from keycloak import KeycloakAdmin

from .env import Config
from .kc import initKeycloakAdmin
from .user import UserList
from .group import GroupList


class ClientContext:
    def __init__(self, config: Config):
        self.config = config
        self.users = UserList()
        self.groups = GroupList()
        self.ka: KeycloakAdmin = initKeycloakAdmin(config.keycloak)

    async def handler(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        message = (await reader.read(1024)).decode().split(" ", 1)

        command = message[0]
        arg = message[1] if len(message) > 1 else None

        if command == "passwdAll":
            users = "\n".join(
                [user.toPasswd(self.config.default) for user in self.users.getAll()]
            )
            writer.write(users.encode())

        elif command == "passwdID":
            user = self.users.getByID(arg)
            if user is not None:
                writer.write(user.toPasswd(self.config.default).encode())

        elif command == "passwdName":
            user = self.users.getByUsername(arg)
            if user is not None:
                writer.write(user.toPasswd(self.config.default).encode())

        elif command == "groupAll":
            groups = "\n".join(
                [group.toGroup(self.config.default) for group in self.groups.getAll()]
            )
            writer.write(groups.encode())

        elif command == "groupID":
            group = self.groups.getByID(arg)
            if group is not None:
                writer.write(group.toGroup(self.config.default).encode())

        elif command == "groupName":
            group = self.groups.getByName(arg)
            if group is not None:
                writer.write(group.toGroup(self.config.default).encode())

        await writer.drain()
        writer.close()
        await writer.wait_closed()

    async def updater(self):
        while True:

            self.users = UserList()
            await self.users.populate(self.ka)

            self.groups = GroupList()
            await self.groups.populate(self.ka)

            print("Updated!")

            await asyncio.sleep(self.config.service.updateInterval)
