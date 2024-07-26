from keycloak import KeycloakAdmin, KeycloakOpenIDConnection
from .env import KeycloakAdminConfig, IDString, initialUID


def initKeycloakAdmin(config: KeycloakAdminConfig) -> KeycloakAdmin:
    keycloak_connection = KeycloakOpenIDConnection(
        server_url=config.server,
        username=config.username,
        password=config.password,
        realm_name="master",
    )
    keycloak_admin = KeycloakAdmin(connection=keycloak_connection)
    keycloak_admin.connection.get_token()
    keycloak_admin.change_current_realm(config.realm)
    return keycloak_admin


def getIDSet(reps) -> set[int]:
    idSet = set()
    for rep in reps:
        if "attributes" in rep:
            attributes = rep["attributes"]
            if IDString in attributes:
                idSet.add(int(attributes[IDString][0]))

    return idSet


def getNextAvailableID(idSet: set[int]) -> int:
    # TODO Check unix uid availability
    if len(idSet) == 0:
        return initialUID
    return max(idSet) + 1
