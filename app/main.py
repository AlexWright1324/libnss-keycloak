import sys, os, json
from keycloak import KeycloakAdmin, KeycloakOpenIDConnection

from .log import DebugLogger
from .env import getConfig, Config

UIDSet = None
UIDString = "libnss-keycloak-unixUID"
defaultShell = "/run/current-system/sw/bin/bash"
initialUID = 1000000

def main():
    with DebugLogger() as log:

        config = getConfig()

        if len(sys.argv) <= 1:
            return
        
        match sys.argv[1]:
            case "passwdAll":
                keycloak_admin = initConnection(config)
                passwdAll(ka=keycloak_admin, log=log)
            case "passwdID":
                if (userID := os.getenv("userID")) is not None:
                    keycloak_admin = initConnection(config)
                    passwdID(int(userID), ka=keycloak_admin, log=log)
            case "passwdName":
                if (userName := os.getenv("userName")) is not None:
                    keycloak_admin = initConnection(config)
                    passwdName(userName, ka=keycloak_admin, log=log)
            
            case "groupAll":
                keycloak_admin = initConnection(config)
                group(ka=keycloak_admin, config=config, log=log)
            case "groupID":
                if (groupID := os.getenv("groupID")) is not None:
                    keycloak_admin = initConnection(config)
                    group(GID=int(groupID), ka=keycloak_admin, config=config, log=log)
            case "groupName":
                if (groupName := os.getenv("groupName")) is not None:
                    keycloak_admin = initConnection(config)
                    group(name=groupName, ka=keycloak_admin, config=config, log=log)
            
            case _default:
                print(f"Invalid command {_default}")

def initConnection(config: Config) -> KeycloakAdmin:
    keycloak_connection = KeycloakOpenIDConnection(
                                server_url=config.server,
                                username=config.username,
                                password=config.password,
                                realm_name="master")
    keycloak_admin = KeycloakAdmin(connection=keycloak_connection)

    keycloak_admin.connection.get_token() # HAVE TO DO THIS BEFORE ANYTHING
    keycloak_admin.change_current_realm(config.realm)
    return keycloak_admin


def passwd(users: list[dict], ka: KeycloakAdmin, log: DebugLogger):
    usersDict = {}
    for user in users:
        tup = userToPasswd(user, ka)
        if tup is not None:
            username, userDict = tup
            usersDict[username] = userDict
    
    log.output(json.dumps(usersDict))

def passwdAll(ka: KeycloakAdmin, log: DebugLogger):
    users = ka.get_users()
    passwd(users, ka, log)

def passwdID(UID: int, ka: KeycloakAdmin, log: DebugLogger):
    users = ka.get_users()
    
    for user in users:
        if "attributes" in user:
            attributes = user["attributes"]
            if UIDString in attributes:
                userUID = attributes[UIDString][0]
                if str(UID) == userUID:
                    passwd([user], ka, log)
                    return

def passwdName(username: str, ka: KeycloakAdmin, log: DebugLogger):
    users = ka.get_users({"username": username, "exact": True})
    passwd(users, ka, log)

def group(ka: KeycloakAdmin, config: Config, log: DebugLogger, GID: int | None = None, name: str | None = None):
    groups = {}
    for group in config.groups:
        if GID is not None and group.gid != GID:
            continue
        if name is not None and group.name != name:
            continue

        groupID = ka.get_group_by_path(group.name)
        users = ka.get_group_members(groupID["id"])
        members = []
        for user in users:
            if "username" in user:
                members.append(user["username"])
        
        groupDict = {
            "gid": group.gid,
            "members": members
            #"passwd": "x"
        }

        groups[group.name] = groupDict
    
    log.output(json.dumps(groups))

def userToPasswd(user: dict, ka: KeycloakAdmin) -> tuple[str, dict] | None:
    global UIDSet

    # Check data exists
    if {"id", "username", "firstName", "lastName", "attributes"} <= user.keys():
        if UIDString in user["attributes"]:
            # TODO int check
            UID = int(user["attributes"][UIDString][0])
        else:
            if UIDSet is None:
                UIDSet = getUIDSet(ka.get_users())
            UID = getNextAvailableUID(UIDSet)
            # TODO Store uid on user in keycloak
            user["attributes"][UIDString] = str(UID)
            ka.update_user(user_id=user["id"], payload=user)
            UIDSet.add(UID)
        
        username = user["username"]
        firstName = user["firstName"]
        lastName = user["lastName"]
        userDict = {
            "uid": UID, # int
            "gid": 100, # int
            "gecos": f"{firstName} {lastName}",
            "dir": f"/home/{username}",
            "shell": defaultShell,
            "passwd": "!"
        }
        return username, userDict
    
    return None

def getUIDSet(users) -> set[int]:
    uidSet = set()
    for user in users:
        attributes = user["attributes"]
        if UIDString in attributes:
            uidSet.add(int(attributes[UIDString][0]))
    
    return uidSet

def getNextAvailableUID(uidSet: set[int]) -> int:
    # TODO Check unix uid availability
    if len(uidSet) == 0:
        return initialUID
    return max(uidSet) + 1