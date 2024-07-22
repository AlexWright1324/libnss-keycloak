import os, toml
from dataclasses import dataclass

configFile = os.getenv("configFile", "config.toml")

@dataclass
class Group:
    name: str
    gid: int

@dataclass
class Config:
    server: str
    username: str
    password: str
    realm: str
    groups: list[Group]

def getConfig() -> Config:
    configDict = toml.load(configFile)

    groups = []
    for groupName, groupDict in configDict["group"].items():
        groups.append(Group(groupName, groupDict["gid"]))

    return Config(
        configDict["server"],
        configDict["username"],
        configDict["password"],
        configDict["realm"],
        groups
    )