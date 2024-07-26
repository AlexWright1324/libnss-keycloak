import os
import toml
from dataclasses import dataclass

configFile = os.getenv("configFile", "config.toml")
socketPath = os.getenv("socketPath", "libnss-keycloak.sock")
validChars = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_")
IDString = "libnss-keycloak-unixID"
initialUID = 1_000_000


@dataclass
class Default:
    gid: int
    shell: str
    home: str


@dataclass
class Service:
    socketPath: str
    updateInterval: int


@dataclass
class KeycloakAdminConfig:
    server: str
    username: str
    password: str
    realm: str


@dataclass
class Config:
    service: Service
    keycloak: KeycloakAdminConfig
    default: Default


def getConfig() -> Config:
    configDict = toml.load(configFile)

    default = Default(
        configDict["default"]["gid"],
        configDict["default"]["shell"],
        configDict["default"]["home"],
    )

    service = Service(socketPath, configDict["service"]["updateInterval"])

    keycloak = KeycloakAdminConfig(
        configDict["keycloak"]["server"],
        configDict["keycloak"]["username"],
        configDict["keycloak"]["password"],
        configDict["keycloak"]["realm"],
    )

    return Config(service, keycloak, default)
