from typing import Any, Mapping, Sequence

import requests

from dagster_dlift.gql_queries import VERIFICATION_QUERY

ENVIRONMENTS_SUBPATH = "environments/"


class DbtCloudInstance:
    def __init__(
        self,
        # Can be found on the Account Info page of dbt.
        account_id: str,
        # Can be either a personal token or a service token.
        token: str,
        # Can be found on the
        access_url: str,
        discovery_api_url: str,
    ):
        self.account_id = account_id
        self.token = token
        self.access_url = access_url
        self.discovery_api_url = discovery_api_url

    def get_api_v2_url(self) -> str:
        return f"{self.access_url}/api/v2/accounts/{self.account_id}"

    def get_discovery_api_url(self) -> str:
        return f"{self.discovery_api_url}/graphql"

    def get_session(self) -> requests.Session:
        session = requests.Session()
        session.headers.update(
            {
                "Accept": "application/json",
                "Authorization": f"Token {self.token}",
            }
        )
        return session

    def make_access_api_request(self, subpath: str) -> Mapping[str, Any]:
        session = self.get_session()
        return self.ensure_valid_response(session.get(f"{self.get_api_v2_url()}/{subpath}")).json()

    def ensure_valid_response(self, response: requests.Response) -> requests.Response:
        if response.status_code != 200:
            raise Exception(f"Request to DBT Cloud failed: {response.text}")
        return response

    def make_discovery_api_query(self, query: str, variables: Mapping[str, Any]):
        session = self.get_session()
        return self.ensure_valid_response(
            session.post(
                self.get_discovery_api_url(),
                json={"query": query, "variables": variables},
            )
        ).json()

    def list_environment_ids(self) -> Sequence[int]:
        return [
            environment["id"]
            for environment in self.make_access_api_request(ENVIRONMENTS_SUBPATH)["data"]
        ]

    def verify_connections(self) -> None:
        # Verifies connection to both the access and discovery APIs.
        for environment_id in self.list_environment_ids():
            response = self.make_discovery_api_query(
                VERIFICATION_QUERY, {"environmentId": environment_id}
            )
            try:
                if response["data"]["environment"]["__typename"] != "Environment":
                    raise Exception(
                        f"Failed to verify connection to environment {environment_id}. Response: {response}"
                    )
            except KeyError:
                raise Exception(
                    f"Failed to verify connection to environment {environment_id}. Response: {response}"
                )
